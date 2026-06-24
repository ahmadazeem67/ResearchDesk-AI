"""
db.py
-----
SQLite persistence layer for the AI Chat Assistant.

Why SQLite and not st.session_state alone?
Session state vanishes the moment the Streamlit server restarts or the
browser tab is closed. A real "ChatGPT-style" product needs chats to
survive that. SQLite gives us a single-file, zero-config database that
ships with Python's standard library (via the `sqlite3` module) — no
extra server to run, which matters a lot for a live demo.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

DB_PATH = Path(__file__).parent / "data" / "chat_assistant.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

CATEGORIES = ["General", "Coding", "Research", "Study", "Documents", "Personal"]


@dataclass
class Message:
    id: str
    chat_id: str
    role: str  # "user" | "assistant"
    content: str
    created_at: str
    liked: Optional[bool] = None  # True=liked, False=disliked, None=no reaction


@dataclass
class Chat:
    id: str
    title: str
    category: str
    pinned: bool
    created_at: str
    updated_at: str
    files: list[str] = field(default_factory=list)


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'General',
                pinned INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                files TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                liked INTEGER,
                FOREIGN KEY (chat_id) REFERENCES chats (id) ON DELETE CASCADE
            )
            """
        )


def create_chat(title: str = "New Chat", category: str = "General") -> Chat:
    now = datetime.now().isoformat(timespec="seconds")
    chat = Chat(
        id=str(uuid.uuid4()),
        title=title,
        category=category,
        pinned=False,
        created_at=now,
        updated_at=now,
        files=[],
    )
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chats (id, title, category, pinned, created_at, updated_at, files) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (chat.id, chat.title, chat.category, 0, chat.created_at, chat.updated_at, "[]"),
        )
    return chat


def list_chats() -> list[Chat]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM chats ORDER BY updated_at DESC").fetchall()
    return [
        Chat(
            id=r["id"],
            title=r["title"],
            category=r["category"],
            pinned=bool(r["pinned"]),
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            files=json.loads(r["files"] or "[]"),
        )
        for r in rows
    ]


def get_chat(chat_id: str) -> Optional[Chat]:
    with get_conn() as conn:
        r = conn.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
    if not r:
        return None
    return Chat(
        id=r["id"],
        title=r["title"],
        category=r["category"],
        pinned=bool(r["pinned"]),
        created_at=r["created_at"],
        updated_at=r["updated_at"],
        files=json.loads(r["files"] or "[]"),
    )


def rename_chat(chat_id: str, new_title: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE chats SET title = ? WHERE id = ?", (new_title, chat_id))


def set_category(chat_id: str, category: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE chats SET category = ? WHERE id = ?", (category, chat_id))


def toggle_pin(chat_id: str) -> None:
    with get_conn() as conn:
        row = conn.execute("SELECT pinned FROM chats WHERE id = ?", (chat_id,)).fetchone()
        new_val = 0 if row and row["pinned"] else 1
        conn.execute("UPDATE chats SET pinned = ? WHERE id = ?", (new_val, chat_id))


def touch_chat(chat_id: str) -> None:
    """Bump updated_at so the chat floats to the top of the recency-sorted list."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE chats SET updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), chat_id),
        )


def add_file_to_chat(chat_id: str, filename: str) -> None:
    chat = get_chat(chat_id)
    if chat is None:
        return
    files = chat.files
    if filename not in files:
        files.append(filename)
    with get_conn() as conn:
        conn.execute("UPDATE chats SET files = ? WHERE id = ?", (json.dumps(files), chat_id))


def delete_chat(chat_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))


def clear_all_history() -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM messages")
        conn.execute("DELETE FROM chats")


def add_message(chat_id: str, role: str, content: str) -> Message:
    msg = Message(
        id=str(uuid.uuid4()),
        chat_id=chat_id,
        role=role,
        content=content,
        created_at=datetime.now().isoformat(timespec="seconds"),
    )
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (id, chat_id, role, content, created_at, liked) "
            "VALUES (?, ?, ?, ?, ?, NULL)",
            (msg.id, msg.chat_id, msg.role, msg.content, msg.created_at),
        )
    touch_chat(chat_id)
    return msg


def update_message_content(message_id: str, content: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE messages SET content = ? WHERE id = ?", (content, message_id))


def set_reaction(message_id: str, liked: Optional[bool]) -> None:
    val = None if liked is None else (1 if liked else 0)
    with get_conn() as conn:
        conn.execute("UPDATE messages SET liked = ? WHERE id = ?", (val, message_id))


def get_messages(chat_id: str) -> list[Message]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at ASC", (chat_id,)
        ).fetchall()
    return [
        Message(
            id=r["id"],
            chat_id=r["chat_id"],
            role=r["role"],
            content=r["content"],
            created_at=r["created_at"],
            liked=None if r["liked"] is None else bool(r["liked"]),
        )
        for r in rows
    ]


def delete_message(message_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))


def search_chats(query: str) -> list[Chat]:
    """Search by chat title OR by any message content inside that chat."""
    query_like = f"%{query.lower()}%"
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT c.* FROM chats c
            LEFT JOIN messages m ON m.chat_id = c.id
            WHERE LOWER(c.title) LIKE ? OR LOWER(m.content) LIKE ?
            ORDER BY c.updated_at DESC
            """,
            (query_like, query_like),
        ).fetchall()
    return [
        Chat(
            id=r["id"],
            title=r["title"],
            category=r["category"],
            pinned=bool(r["pinned"]),
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            files=json.loads(r["files"] or "[]"),
        )
        for r in rows
    ]


def chat_stats() -> dict:
    with get_conn() as conn:
        total_chats = conn.execute("SELECT COUNT(*) AS c FROM chats").fetchone()["c"]
        total_messages = conn.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"]
        user_messages = conn.execute(
            "SELECT COUNT(*) AS c FROM messages WHERE role = 'user'"
        ).fetchone()["c"]
        by_category = conn.execute(
            "SELECT category, COUNT(*) AS c FROM chats GROUP BY category ORDER BY c DESC"
        ).fetchall()
        likes = conn.execute(
            "SELECT COUNT(*) AS c FROM messages WHERE liked = 1"
        ).fetchone()["c"]
        dislikes = conn.execute(
            "SELECT COUNT(*) AS c FROM messages WHERE liked = 0"
        ).fetchone()["c"]
    return {
        "total_chats": total_chats,
        "total_messages": total_messages,
        "user_messages": user_messages,
        "ai_messages": total_messages - user_messages,
        "by_category": [(r["category"], r["c"]) for r in by_category],
        "likes": likes,
        "dislikes": dislikes,
    }