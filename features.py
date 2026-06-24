"""
features.py
-----------
Higher-level "study assistant" capabilities built on top of llm.invoke_once.
Each function builds a focused prompt and asks for a specific output shape.
"""

from __future__ import annotations

import json
import re

import llm


def generate_chat_title(model_label: str, first_user_message: str) -> str:
    prompt = (
        "Create a short, specific title (max 6 words, no quotes, no punctuation "
        "at the end) for a chat that starts with this message:\n\n"
        f'"{first_user_message}"\n\nRespond with ONLY the title text.'
    )
    try:
        title = llm.invoke_once(model_label, prompt, temperature=0.3, max_tokens=24)
        title = title.strip().strip('"').strip("'")
        return title[:60] if title else "New Chat"
    except Exception:
        # Title generation is a nice-to-have; never let it break the chat flow.
        return first_user_message[:40] + ("…" if len(first_user_message) > 40 else "")


def summarize_text(model_label: str, text: str, mode: str = "summary") -> str:
    instructions = {
        "summary": "Write a clear, well-organized summary of the following content in 4-8 sentences.",
        "key_points": "Extract the key points from the following content as a concise bulleted list (max 8 bullets).",
        "notes": (
            "Convert the following content into structured study notes with headings, "
            "bullet points, and bolded key terms, formatted in Markdown."
        ),
    }
    instruction = instructions.get(mode, instructions["summary"])
    prompt = f"{instruction}\n\nCONTENT:\n{text[:6000]}"
    return llm.invoke_once(model_label, prompt, temperature=0.3, max_tokens=900)


def generate_quiz(model_label: str, text: str, num_questions: int = 5) -> list[dict]:
    prompt = f"""Based on the content below, generate exactly {num_questions} multiple-choice questions.

Respond with ONLY valid JSON (no markdown fences, no preamble), in this exact shape:
[
  {{"question": "...", "options": ["A...", "B...", "C...", "D..."], "answer_index": 0}}
]

CONTENT:
{text[:6000]}"""
    raw = llm.invoke_once(model_label, prompt, temperature=0.4, max_tokens=1200)
    return _safe_parse_json_list(raw)


def generate_flashcards(model_label: str, text: str, num_cards: int = 8) -> list[dict]:
    prompt = f"""Based on the content below, generate exactly {num_cards} flashcards.

Respond with ONLY valid JSON (no markdown fences, no preamble), in this exact shape:
[
  {{"front": "term or question", "back": "definition or answer"}}
]

CONTENT:
{text[:6000]}"""
    raw = llm.invoke_once(model_label, prompt, temperature=0.4, max_tokens=1000)
    return _safe_parse_json_list(raw)


def analyze_sentiment(model_label: str, text: str) -> dict:
    prompt = f"""Analyze the overall sentiment/tone of this conversation excerpt.

Respond with ONLY valid JSON in this exact shape:
{{"sentiment": "positive|neutral|negative", "tone": "short description", "confidence": 0.0}}

TEXT:
{text[:3000]}"""
    raw = llm.invoke_once(model_label, prompt, temperature=0.1, max_tokens=120)
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        return json.loads(match.group(0)) if match else {"sentiment": "neutral", "tone": "unclear", "confidence": 0.0}
    except Exception:
        return {"sentiment": "neutral", "tone": "unclear", "confidence": 0.0}


def estimate_reading_time(text: str, wpm: int = 200) -> int:
    word_count = len(text.split())
    return max(1, round(word_count / wpm))


def _safe_parse_json_list(raw: str) -> list[dict]:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, list) else []
    except Exception:
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return []
        return []