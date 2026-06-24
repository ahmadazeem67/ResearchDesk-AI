"""
llm.py
------
Wraps the Hugging Face Inference API behind a small, cached interface.

Key fix vs. the original script: the original created a brand-new
HuggingFaceEndpoint + ChatHuggingFace object on every single message,
which re-opens a connection each turn and is needlessly slow. Streamlit's
@st.cache_resource keeps one client alive per (model, temperature,
max_tokens) combination for the life of the server process.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator, Optional

import streamlit as st
from dotenv import load_dotenv, dotenv_values, find_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

# Load the project .env file explicitly so Streamlit can pick up HUGGINGFACEHUB_API_TOKEN
dotenv_path = find_dotenv() or Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path)

# A handful of well-supported instruct/chat models on the HF Inference API.
# Swap or extend this dict freely — the rest of the app just reads from it.
AVAILABLE_MODELS = {
    "Qwen 2.5 7B Instruct": "Qwen/Qwen2.5-7B-Instruct",
    "Llama 3.1 8B Instruct": "meta-llama/Llama-3.1-8B-Instruct",
    "Flan-T5 Large": "google/flan-t5-large",
    "Flan-T5 Base": "google/flan-t5-base",
    "BLOOM 3B": "bigscience/bloom-3b",
    "GPT-J 6B": "EleutherAI/gpt-j-6B",
    "Pythia 3B": "EleutherAI/pythia-3b",
    "StableLM Alpha 3B": "stabilityai/stablelm-tuned-alpha-3b",
}

RESPONSE_STYLE_PRESETS = {
    "Creative": {"temperature": 0.9, "top_p": 0.95},
    "Balanced": {"temperature": 0.6, "top_p": 0.9},
    "Precise": {"temperature": 0.2, "top_p": 0.85},
}


class LLMConfigError(RuntimeError):
    """Raised when the API token is missing or invalid."""


def get_api_token() -> Optional[str]:
    return os.environ.get("HUGGINGFACEHUB_API_TOKEN") or st.session_state.get(
        "hf_token_override"
    )


@st.cache_resource(show_spinner=False)
def _build_chat_model(
    repo_id: str, temperature: float, top_p: float, max_tokens: int, token: str
) -> ChatHuggingFace:
    llm = HuggingFaceEndpoint(
        repo_id=repo_id,
        task="text-generation",
        temperature=max(temperature, 0.01),  # HF API rejects an exact 0.0
        top_p=top_p,
        max_new_tokens=max_tokens,
        huggingfacehub_api_token=token,
    )
    return ChatHuggingFace(llm=llm, model_id=repo_id)


def get_chat_model(
    model_label: str, temperature: float, top_p: float, max_tokens: int
) -> ChatHuggingFace:
    token = get_api_token()
    if not token:
        raise LLMConfigError(
            "No Hugging Face API token found. Add HUGGINGFACEHUB_API_TOKEN to your "
            ".env file, or enter one in the Settings panel."
        )
    repo_id = AVAILABLE_MODELS.get(model_label, model_label)
    return _build_chat_model(repo_id, temperature, top_p, max_tokens, token)


def to_lc_messages(
    history: list[tuple[str, str]], system_prompt: Optional[str] = None
) -> list[BaseMessage]:
    """Convert a list of (role, content) tuples into LangChain message objects."""
    messages: list[BaseMessage] = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    for role, content in history:
        if role == "user":
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))
    return messages


def stream_response(
    model_label: str,
    history: list[tuple[str, str]],
    temperature: float = 0.6,
    top_p: float = 0.9,
    max_tokens: int = 1024,
    system_prompt: Optional[str] = None,
) -> Iterator[str]:
    """
    Yields response text incrementally. Falls back to a single chunk if the
    endpoint doesn't support token streaming for a given model.
    """
    chat_model = get_chat_model(model_label, temperature, top_p, max_tokens)
    messages = to_lc_messages(history, system_prompt)

    try:
        streamed_any = False
        for chunk in chat_model.stream(messages):
            text = getattr(chunk, "content", "")
            if text:
                streamed_any = True
                yield text
        if not streamed_any:
            # Some endpoints ignore .stream() and need a direct invoke.
            response = chat_model.invoke(messages)
            yield response.content
    except Exception as exc:
        raise RuntimeError(_friendly_error(exc)) from exc


def invoke_once(
    model_label: str,
    prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 512,
    system_prompt: Optional[str] = None,
) -> str:
    """Single-shot, non-streaming call — used for titles, summaries, quizzes, etc."""
    chat_model = get_chat_model(model_label, temperature, 0.9, max_tokens)
    messages = to_lc_messages([("user", prompt)], system_prompt)
    try:
        response = chat_model.invoke(messages)
        return response.content
    except Exception as exc:
        raise RuntimeError(_friendly_error(exc)) from exc


def _friendly_error(exc: Exception) -> str:
    msg = str(exc)
    if "401" in msg or "Unauthorized" in msg:
        return "Your Hugging Face API token was rejected (401). Check it in Settings."
    if "404" in msg:
        return "That model isn't available on the Inference API right now. Try another model in Settings."
    if "503" in msg or "loading" in msg.lower():
        return "The model is warming up on Hugging Face's servers. Wait ~20s and try again."
    if "rate limit" in msg.lower() or "429" in msg:
        return "Rate limit hit on the Hugging Face API. Wait a moment and try again."
    return f"Model request failed: {msg}"