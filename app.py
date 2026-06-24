# import logging
# import os
# import streamlit as st
# from dotenv import load_dotenv
# from langchain_core.messages import HumanMessage, AIMessage
# from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

# # Suppress background logs
# os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
# logging.getLogger("transformers").setLevel(logging.ERROR)
# load_dotenv()

# st.set_page_config(page_title="AI Chatbot", layout="wide")
# st.title("🤖 Pure AI Chat Interface")
# st.write("Direct connection to the model without external web tools.")

# # Initialize session state message log if it doesn't exist
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# # Display entire chat history on screen
# for message in st.session_state.messages:
#     role = "user" if isinstance(message, HumanMessage) else "assistant"
#     with st.chat_message(role):
#         st.markdown(message.content)

# # Process active chat input string
# if prompt := st.chat_input("Ask me anything..."):
#     # Append the new user prompt as a LangChain HumanMessage object
#     st.session_state.messages.append(HumanMessage(content=prompt))
#     with st.chat_message("user"):
#         st.markdown(prompt)

#     with st.chat_message("assistant"):
#         with st.spinner("Thinking..."):
#             try:
#                 # 1. Connect using the lightweight Llama-3.2-3B conversational model
#                 # 1. Connect using the universally supported Qwen model
#                 llm = HuggingFaceEndpoint(
#     repo_id="Qwen/Qwen2.5-7B-Instruct",
#     task="text-generation",  # Qwen uses text-generation for chat templates
#     temperature=0.7,
# )

# # 2. Chat wrapper maps the full message history smoothly
#                 chat_model = ChatHuggingFace(llm=llm, model_id="Qwen/Qwen2.5-7B-Instruct")

                
#                 # Invoke using the entire cumulative history list to maintain chat memory
#                 response = chat_model.invoke(st.session_state.messages)
                
#                 # Render response and commit it to session logs
#                 st.markdown(response.content)
#                 st.session_state.messages.append(AIMessage(content=response.content))
                
#             except Exception as e:
#                 st.error(f"Error: {e}")



"""
app.py
------
The Research Desk — an AI chat assistant with persistent multi-chat
history, document Q&A, streaming responses, and study tools.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta

import streamlit as st

import db
import export
import features
import llm
from documents import ParsedFile, build_context_block, parse_uploaded_file
from styles import build_css

# ---------------------------------------------------------------------------
# Page config + one-time init
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="The Research Desk — AI Assistant",
    page_icon="🪶",
    layout="wide",
    initial_sidebar_state="expanded",
)
db.init_db()

DEFAULTS = {
    "theme": "light",
    "active_chat_id": None,
    "model_label": list(llm.AVAILABLE_MODELS.keys())[0],
    "response_style": "Balanced",
    "temperature": 0.6,
    "top_p": 0.9,
    "max_tokens": 1024,
    "search_query": "",
    "parsed_files": {},  # chat_id -> list[ParsedFile]
    "pending_prompt": None,
    "renaming_chat_id": None,
    "hf_token_override": "",
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

st.markdown(build_css(st.session_state.theme), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def ensure_active_chat() -> db.Chat:
    if st.session_state.active_chat_id:
        chat = db.get_chat(st.session_state.active_chat_id)
        if chat:
            return chat
    chats = db.list_chats()
    if chats:
        st.session_state.active_chat_id = chats[0].id
        return chats[0]
    new_chat_obj = db.create_chat()
    st.session_state.active_chat_id = new_chat_obj.id
    return new_chat_obj


def new_chat(category: str = "General") -> None:
    chat = db.create_chat(title="New Chat", category=category)
    st.session_state.active_chat_id = chat.id
    st.session_state.parsed_files[chat.id] = []


def group_chats_by_recency(chats: list[db.Chat]) -> dict[str, list[db.Chat]]:
    now = datetime.now()
    groups = {"Pinned": [], "Today": [], "Yesterday": [], "Previous 7 Days": [], "Older": []}
    for chat in chats:
        if chat.pinned:
            groups["Pinned"].append(chat)
            continue
        updated = datetime.fromisoformat(chat.updated_at)
        delta = now.date() - updated.date()
        if delta.days == 0:
            groups["Today"].append(chat)
        elif delta.days == 1:
            groups["Yesterday"].append(chat)
        elif delta.days <= 7:
            groups["Previous 7 Days"].append(chat)
        else:
            groups["Older"].append(chat)
    return groups


def render_user_bubble(content: str) -> str:
    return f'<div class="msg-row user"><div class="bubble-user">{content}</div></div>'


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="brand-title"><span class="brand-mark">🪶</span> The Research Desk</div>',
        unsafe_allow_html=True,
    )
    st.caption("Your AI study & research companion")

    col_new, col_theme = st.columns([3, 1])
    with col_new:
        if st.button("➕ New Chat", use_container_width=True, type="primary"):
            new_chat()
            st.rerun()
    with col_theme:
        if st.button("🌓", help="Toggle dark / light theme", use_container_width=True):
            st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
            st.rerun()

    search_query = st.text_input(
        "Search chats", placeholder="🔍 Search by title or content…", label_visibility="collapsed"
    )

    st.markdown('<div class="sidebar-eyebrow">Conversations</div>', unsafe_allow_html=True)

    chats = db.search_chats(search_query) if search_query else db.list_chats()

    if not chats:
        st.caption("No chats yet — start a new one above." if not search_query else "No matches found.")
    else:
        groups = group_chats_by_recency(chats) if not search_query else {"Results": chats}
        for group_name, group_chats in groups.items():
            if not group_chats:
                continue
            st.markdown(f'<div class="sidebar-eyebrow">{group_name}</div>', unsafe_allow_html=True)
            for chat in group_chats:
                is_active = chat.id == st.session_state.active_chat_id
                row_class = "chat-row chat-row-active" if is_active else "chat-row"

                if st.session_state.renaming_chat_id == chat.id:
                    new_title = st.text_input(
                        "Rename", value=chat.title, key=f"rename_input_{chat.id}",
                        label_visibility="collapsed",
                    )
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        if st.button("Save", key=f"save_rename_{chat.id}", use_container_width=True):
                            db.rename_chat(chat.id, new_title or "Untitled Chat")
                            st.session_state.renaming_chat_id = None
                            st.rerun()
                    with rc2:
                        if st.button("Cancel", key=f"cancel_rename_{chat.id}", use_container_width=True):
                            st.session_state.renaming_chat_id = None
                            st.rerun()
                    continue

                st.markdown(f'<div class="{row_class}">', unsafe_allow_html=True)
                pin_icon = "📌 " if chat.pinned else ""
                btn_label = f"{pin_icon}{chat.title}"
                main_col, menu_col = st.columns([5, 1])
                with main_col:
                    if st.button(btn_label, key=f"open_{chat.id}", use_container_width=True):
                        st.session_state.active_chat_id = chat.id
                        st.rerun()
                    st.markdown(
                        f'<div class="chat-meta-text">{chat.category} · '
                        f'{datetime.fromisoformat(chat.updated_at):%b %d, %H:%M}</div>',
                        unsafe_allow_html=True,
                    )
                with menu_col:
                    with st.popover("⋯", use_container_width=True):
                        if st.button("✏️ Rename", key=f"rn_{chat.id}", use_container_width=True):
                            st.session_state.renaming_chat_id = chat.id
                            st.rerun()
                        pin_label = "📌 Unpin" if chat.pinned else "📌 Pin"
                        if st.button(pin_label, key=f"pin_{chat.id}", use_container_width=True):
                            db.toggle_pin(chat.id)
                            st.rerun()
                        new_cat = st.selectbox(
                            "Category", db.CATEGORIES,
                            index=db.CATEGORIES.index(chat.category) if chat.category in db.CATEGORIES else 0,
                            key=f"cat_{chat.id}",
                        )
                        if new_cat != chat.category:
                            db.set_category(chat.id, new_cat)
                            st.rerun()
                        st.divider()
                        if st.button("🗑️ Delete", key=f"del_{chat.id}", use_container_width=True):
                            db.delete_chat(chat.id)
                            if st.session_state.active_chat_id == chat.id:
                                st.session_state.active_chat_id = None
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown('<div class="sidebar-eyebrow">Library</div>', unsafe_allow_html=True)
    if st.button("📊 Analytics Dashboard", use_container_width=True):
        st.session_state.show_analytics = not st.session_state.get("show_analytics", False)
        st.rerun()
    if st.button("🧹 Clear All History", use_container_width=True):
        st.session_state.confirm_clear = True
    if st.session_state.get("confirm_clear"):
        st.warning("This permanently deletes every chat. Are you sure?")
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("Yes, clear everything", type="primary", use_container_width=True):
                db.clear_all_history()
                st.session_state.active_chat_id = None
                st.session_state.confirm_clear = False
                st.rerun()
        with cc2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_clear = False
                st.rerun()


# ---------------------------------------------------------------------------
# ACTIVE CHAT
# ---------------------------------------------------------------------------
active_chat = ensure_active_chat()
st.session_state.parsed_files.setdefault(active_chat.id, [])

# ---------------------------------------------------------------------------
# TOP BAR
# ---------------------------------------------------------------------------
top_left, top_right = st.columns([3, 2])
with top_left:
    st.markdown(
        f"""<div class="brand-bar">
            <div class="brand-title"><span class="brand-mark">🪶</span> The Research Desk</div>
            <div class="chat-name-pill">{active_chat.title} · {active_chat.category}</div>
        </div>""",
        unsafe_allow_html=True,
    )
with top_right:
    tb1, tb2, tb3 = st.columns(3)
    with tb1:
        if st.button("➕ New", use_container_width=True):
            new_chat()
            st.rerun()
    with tb2:
        with st.popover("📤 Export", use_container_width=True):
            messages_for_export = db.get_messages(active_chat.id)
            for label, (ext, fn, mime) in export.EXPORTERS.items():
                content = fn(active_chat, messages_for_export)
                st.download_button(
                    f"Download {label}",
                    data=content,
                    file_name=f"{active_chat.title.replace(' ', '_')}.{ext}",
                    mime=mime,
                    use_container_width=True,
                    key=f"export_{ext}",
                )
    with tb3:
        with st.popover("⚙️ Settings", use_container_width=True):
            st.markdown("**Model**")
            st.session_state.model_label = st.selectbox(
                "Model", list(llm.AVAILABLE_MODELS.keys()),
                index=list(llm.AVAILABLE_MODELS.keys()).index(st.session_state.model_label),
                label_visibility="collapsed",
            )
            st.markdown("**Response style**")
            style = st.radio(
                "Style", list(llm.RESPONSE_STYLE_PRESETS.keys()),
                index=list(llm.RESPONSE_STYLE_PRESETS.keys()).index(st.session_state.response_style),
                horizontal=True, label_visibility="collapsed",
            )
            if style != st.session_state.response_style:
                st.session_state.response_style = style
                preset = llm.RESPONSE_STYLE_PRESETS[style]
                st.session_state.temperature = preset["temperature"]
                st.session_state.top_p = preset["top_p"]
            st.markdown("**Fine-tune**")
            st.session_state.temperature = st.slider(
                "Temperature", 0.0, 1.0, st.session_state.temperature, 0.05
            )
            st.session_state.top_p = st.slider("Top P", 0.1, 1.0, st.session_state.top_p, 0.05)
            st.session_state.max_tokens = st.slider(
                "Max tokens", 128, 2048, st.session_state.max_tokens, 64
            )
            st.divider()
            st.markdown("**Hugging Face API token**")
            st.caption("Set HUGGINGFACEHUB_API_TOKEN in your .env file, or paste a token here for this session only.")
            st.session_state.hf_token_override = st.text_input(
                "API token", value=st.session_state.hf_token_override, type="password",
                label_visibility="collapsed",
            )

# ---------------------------------------------------------------------------
# ANALYTICS DASHBOARD (toggleable)
# ---------------------------------------------------------------------------
if st.session_state.get("show_analytics"):
    stats = db.chat_stats()
    st.markdown("### 📊 Analytics Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    for col, number, label in [
        (c1, stats["total_chats"], "Total Chats"),
        (c2, stats["total_messages"], "Total Messages"),
        (c3, stats["user_messages"], "Messages Sent"),
        (c4, stats["likes"], "Liked Responses"),
    ]:
        with col:
            st.markdown(
                f'<div class="stat-card"><div class="stat-number">{number}</div>'
                f'<div class="stat-label">{label}</div></div>',
                unsafe_allow_html=True,
            )
    if stats["by_category"]:
        st.markdown("##### Chats by category")
        st.bar_chart({cat: count for cat, count in stats["by_category"]})
    st.divider()

# ---------------------------------------------------------------------------
# FILE UPLOAD
# ---------------------------------------------------------------------------
with st.expander("📎 Upload documents (PDF, TXT, DOCX, CSV, XLSX) for this chat", expanded=False):
    uploaded_files = st.file_uploader(
        "Drag and drop files here",
        type=["pdf", "txt", "docx", "csv", "xlsx", "xls"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if uploaded_files:
        existing_names = {pf.filename for pf in st.session_state.parsed_files[active_chat.id]}
        for uf in uploaded_files:
            if uf.name in existing_names:
                continue
            try:
                parsed = parse_uploaded_file(uf.read(), uf.name)
                st.session_state.parsed_files[active_chat.id].append(parsed)
                db.add_file_to_chat(active_chat.id, uf.name)
                st.toast(f"📄 {uf.name} uploaded and indexed", icon="✅")
            except Exception as e:
                st.error(f"Couldn't read {uf.name}: {e}")

    current_files = st.session_state.parsed_files[active_chat.id]
    if current_files:
        st.markdown("**Indexed in this chat:**")
        for pf in current_files:
            fc1, fc2, fc3 = st.columns([4, 2, 1])
            with fc1:
                icon = {"pdf": "📄", "docx": "📃", "txt": "📝", "csv": "📊", "xlsx": "📈"}.get(pf.file_type, "📎")
                st.markdown(f"{icon} **{pf.filename}** — {pf.char_count:,} characters")
            with fc2:
                action = st.selectbox(
                    "Action", ["—", "Summarize", "Key points", "Generate notes", "Generate quiz", "Flashcards"],
                    key=f"doc_action_{pf.filename}", label_visibility="collapsed",
                )
            with fc3:
                if st.button("✕", key=f"remove_{pf.filename}", help="Remove from this chat"):
                    st.session_state.parsed_files[active_chat.id] = [
                        f for f in current_files if f.filename != pf.filename
                    ]
                    st.rerun()
            if action != "—":
                with st.spinner(f"Running '{action}' on {pf.filename}…"):
                    try:
                        if action == "Summarize":
                            result = features.summarize_text(st.session_state.model_label, pf.text, "summary")
                            st.info(result)
                        elif action == "Key points":
                            result = features.summarize_text(st.session_state.model_label, pf.text, "key_points")
                            st.info(result)
                        elif action == "Generate notes":
                            result = features.summarize_text(st.session_state.model_label, pf.text, "notes")
                            st.markdown(result)
                        elif action == "Generate quiz":
                            quiz = features.generate_quiz(st.session_state.model_label, pf.text)
                            if not quiz:
                                st.warning("Couldn't generate a quiz from this document. Try again.")
                            for i, q in enumerate(quiz, 1):
                                st.markdown(f"**{i}. {q.get('question', '')}**")
                                for j, opt in enumerate(q.get("options", [])):
                                    marker = "✅" if j == q.get("answer_index") else "▫️"
                                    st.markdown(f"{marker} {opt}")
                        elif action == "Flashcards":
                            cards = features.generate_flashcards(st.session_state.model_label, pf.text)
                            if not cards:
                                st.warning("Couldn't generate flashcards from this document. Try again.")
                            for card in cards:
                                with st.expander(f"🃏 {card.get('front', '')}"):
                                    st.write(card.get("back", ""))
                    except Exception as e:
                        st.error(str(e))

# ---------------------------------------------------------------------------
# CHAT HISTORY DISPLAY
# ---------------------------------------------------------------------------
messages = db.get_messages(active_chat.id)

chat_container = st.container()
with chat_container:
    if not messages:
        st.markdown(
            '<div class="marginalia" style="font-size:0.95rem; margin-top:2rem;">'
            "Begin a new line of inquiry — ask a question, or upload a document above."
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("**Try asking:**")
        suggestion_cols = st.columns(4)
        suggestions = ["Summarize this", "Explain simply", "Generate code", "Create a quiz"]
        for col, sug in zip(suggestion_cols, suggestions):
            with col:
                if st.button(sug, use_container_width=True, key=f"sugg_{sug}"):
                    st.session_state.pending_prompt = sug
                    st.rerun()

    for msg in messages:
        if msg.role == "user":
            st.markdown(render_user_bubble(msg.content), unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="msg-row assistant"><div class="card-assistant">'
                f'<div class="marginalia">The Research Desk</div>'
                f'<div class="card-assistant-body">{msg.content}</div>'
                f"</div></div>",
                unsafe_allow_html=True,
            )
            ac1, ac2, ac3, ac4, ac5 = st.columns([1, 1, 1, 1, 6])
            with ac1:
                if st.button("👍", key=f"like_{msg.id}", help="Good response"):
                    db.set_reaction(msg.id, True if msg.liked is not True else None)
                    st.rerun()
            with ac2:
                if st.button("👎", key=f"dislike_{msg.id}", help="Not helpful"):
                    db.set_reaction(msg.id, False if msg.liked is not False else None)
                    st.rerun()
            with ac3:
                if st.button("🔄", key=f"regen_{msg.id}", help="Regenerate"):
                    st.session_state.regen_message_id = msg.id
                    st.rerun()
            with ac4:
                if st.button("💾", key=f"save_{msg.id}", help="Save to notes"):
                    st.toast("Saved to this chat's notes", icon="💾")
            if msg.liked is True:
                st.caption("👍 Marked helpful")
            elif msg.liked is False:
                st.caption("👎 Marked unhelpful")

# ---------------------------------------------------------------------------
# REGENERATE HANDLING
# ---------------------------------------------------------------------------
if st.session_state.get("regen_message_id"):
    target_id = st.session_state.pop("regen_message_id")
    all_msgs = db.get_messages(active_chat.id)
    idx = next((i for i, m in enumerate(all_msgs) if m.id == target_id), None)
    if idx is not None and idx > 0:
        history_for_regen = [(m.role, m.content) for m in all_msgs[:idx]]
        db.delete_message(target_id)
        with st.spinner("Regenerating…"):
            try:
                full_text = ""
                for chunk in llm.stream_response(
                    st.session_state.model_label, history_for_regen,
                    st.session_state.temperature, st.session_state.top_p, st.session_state.max_tokens,
                ):
                    full_text += chunk
                db.add_message(active_chat.id, "assistant", full_text)
            except Exception as e:
                db.add_message(active_chat.id, "assistant", f"⚠️ {e}")
        st.rerun()

# ---------------------------------------------------------------------------
# MESSAGE INPUT
# ---------------------------------------------------------------------------
prompt = st.chat_input("Ask me anything… (Shift+Enter for a new line)")
if st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if prompt:
    db.add_message(active_chat.id, "user", prompt)

    # Auto-generate a real title on the first message of a fresh chat.
    if active_chat.title == "New Chat":
        new_title = features.generate_chat_title(st.session_state.model_label, prompt)
        db.rename_chat(active_chat.id, new_title)

    history = [(m.role, m.content) for m in db.get_messages(active_chat.id)]

    system_prompt = None
    parsed_files = st.session_state.parsed_files.get(active_chat.id, [])
    if parsed_files:
        context = build_context_block(parsed_files, prompt)
        if context:
            system_prompt = (
                "You are a careful research assistant. Use the following document "
                "excerpts to answer the user's question when relevant. If the "
                "excerpts don't contain the answer, say so honestly rather than "
                f"guessing.\n\nDOCUMENT EXCERPTS:\n{context}"
            )

    placeholder_container = st.empty()
    with placeholder_container.container():
        st.markdown(
            '<div class="msg-row assistant"><div class="card-assistant">'
            '<div class="marginalia">The Research Desk</div>'
            '<div class="thinking-dots"><span>●</span><span>●</span><span>●</span></div>'
            "</div></div>",
            unsafe_allow_html=True,
        )

    full_response = ""
    try:
        for chunk in llm.stream_response(
            st.session_state.model_label,
            history,
            temperature=st.session_state.temperature,
            top_p=st.session_state.top_p,
            max_tokens=st.session_state.max_tokens,
            system_prompt=system_prompt,
        ):
            full_response += chunk
            with placeholder_container.container():
                st.markdown(
                    f'<div class="msg-row assistant"><div class="card-assistant">'
                    f'<div class="marginalia">The Research Desk</div>'
                    f'<div class="card-assistant-body">{full_response}▌</div>'
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
        db.add_message(active_chat.id, "assistant", full_response)
        st.toast("Response complete", icon="✅")
    except Exception as e:
        placeholder_container.empty()
        st.error(str(e))
        db.add_message(active_chat.id, "assistant", f"⚠️ I ran into an error: {e}")

    st.rerun()