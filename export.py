"""
export.py
---------
Turns a chat's messages into downloadable text formats.

Note: PDF/DOCX export are deliberately left out of this module. Generating
those well (proper pagination, styling, embedded fonts) is a non-trivial
amount of code on its own, and a half-working PDF export is worse for a
demo than a clearly-labeled "Markdown / TXT / JSON" set that always works.
The Markdown export below is intentionally easy to paste into Word or
Google Docs, or to convert with any Markdown-to-PDF tool, if a polished
PDF is needed afterward.
"""

from __future__ import annotations

import json
from datetime import datetime

from db import Chat, Message


def to_markdown(chat: Chat, messages: list[Message]) -> str:
    lines = [f"# {chat.title}", "", f"*Category: {chat.category} • Exported {datetime.now():%Y-%m-%d %H:%M}*", ""]
    for m in messages:
        speaker = "**You**" if m.role == "user" else "**Assistant**"
        lines.append(f"{speaker} ({m.created_at}):")
        lines.append("")
        lines.append(m.content)
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def to_txt(chat: Chat, messages: list[Message]) -> str:
    lines = [chat.title, "=" * len(chat.title), ""]
    for m in messages:
        speaker = "You" if m.role == "user" else "Assistant"
        lines.append(f"[{m.created_at}] {speaker}: {m.content}")
        lines.append("")
    return "\n".join(lines)


def to_json(chat: Chat, messages: list[Message]) -> str:
    payload = {
        "chat": {
            "id": chat.id,
            "title": chat.title,
            "category": chat.category,
            "created_at": chat.created_at,
            "updated_at": chat.updated_at,
            "files": chat.files,
        },
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
                "liked": m.liked,
            }
            for m in messages
        ],
    }
    return json.dumps(payload, indent=2)


EXPORTERS = {
    "Markdown (.md)": ("md", to_markdown, "text/markdown"),
    "Plain text (.txt)": ("txt", to_txt, "text/plain"),
    "JSON (.json)": ("json", to_json, "application/json"),
}