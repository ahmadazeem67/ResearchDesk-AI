"""
documents.py
------------
File parsing + a lightweight retrieval layer for "chat with your document".

Design choice: rather than pulling in a full vector database (FAISS/Chroma)
which adds install weight and failure points right before a demo, this uses
simple keyword-overlap scoring over text chunks. It's transparent, has zero
extra dependencies, and is good enough for the document sizes a student
project will realistically upload (a few dozen pages).
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

import pandas as pd
from docx import Document as DocxDocument
from pypdf import PdfReader

CHUNK_SIZE = 900  # characters per chunk
CHUNK_OVERLAP = 150


@dataclass
class ParsedFile:
    filename: str
    file_type: str
    text: str
    chunks: list[str]
    char_count: int
    page_or_row_count: int


def _chunk_text(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - CHUNK_OVERLAP
    return chunks


def parse_pdf(file_bytes: bytes, filename: str) -> ParsedFile:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text = []
    for page in reader.pages:
        pages_text.append(page.extract_text() or "")
    full_text = "\n".join(pages_text)
    return ParsedFile(
        filename=filename,
        file_type="pdf",
        text=full_text,
        chunks=_chunk_text(full_text),
        char_count=len(full_text),
        page_or_row_count=len(reader.pages),
    )


def parse_docx(file_bytes: bytes, filename: str) -> ParsedFile:
    doc = DocxDocument(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    full_text = "\n".join(paragraphs)
    return ParsedFile(
        filename=filename,
        file_type="docx",
        text=full_text,
        chunks=_chunk_text(full_text),
        char_count=len(full_text),
        page_or_row_count=len(paragraphs),
    )


def parse_txt(file_bytes: bytes, filename: str) -> ParsedFile:
    full_text = file_bytes.decode("utf-8", errors="ignore")
    return ParsedFile(
        filename=filename,
        file_type="txt",
        text=full_text,
        chunks=_chunk_text(full_text),
        char_count=len(full_text),
        page_or_row_count=full_text.count("\n") + 1,
    )


def parse_csv(file_bytes: bytes, filename: str) -> ParsedFile:
    df = pd.read_csv(io.BytesIO(file_bytes))
    summary = (
        f"CSV with {len(df)} rows and {len(df.columns)} columns: "
        f"{', '.join(map(str, df.columns))}.\n\n"
        f"First rows:\n{df.head(10).to_string(index=False)}"
    )
    return ParsedFile(
        filename=filename,
        file_type="csv",
        text=summary,
        chunks=_chunk_text(summary),
        char_count=len(summary),
        page_or_row_count=len(df),
    )


def parse_excel(file_bytes: bytes, filename: str) -> ParsedFile:
    df = pd.read_excel(io.BytesIO(file_bytes))
    summary = (
        f"Excel sheet with {len(df)} rows and {len(df.columns)} columns: "
        f"{', '.join(map(str, df.columns))}.\n\n"
        f"First rows:\n{df.head(10).to_string(index=False)}"
    )
    return ParsedFile(
        filename=filename,
        file_type="xlsx",
        text=summary,
        chunks=_chunk_text(summary),
        char_count=len(summary),
        page_or_row_count=len(df),
    )


PARSERS = {
    "pdf": parse_pdf,
    "txt": parse_txt,
    "docx": parse_docx,
    "csv": parse_csv,
    "xlsx": parse_excel,
    "xls": parse_excel,
}


def parse_uploaded_file(file_bytes: bytes, filename: str) -> ParsedFile:
    ext = filename.rsplit(".", 1)[-1].lower()
    parser = PARSERS.get(ext)
    if parser is None:
        raise ValueError(f"Unsupported file type: .{ext}")
    return parser(file_bytes, filename)


def _score_chunk(chunk: str, query_words: set[str]) -> int:
    chunk_words = set(re.findall(r"[a-z0-9]+", chunk.lower()))
    return len(query_words & chunk_words)


def retrieve_relevant_chunks(
    parsed_files: list[ParsedFile], query: str, top_k: int = 4
) -> list[tuple[str, str]]:
    """Returns [(filename, chunk_text), ...] ranked by keyword overlap with the query."""
    query_words = set(re.findall(r"[a-z0-9]+", query.lower()))
    query_words -= {"the", "a", "an", "is", "of", "to", "and", "in", "on", "for", "what", "how"}

    scored: list[tuple[int, str, str]] = []
    for pf in parsed_files:
        for chunk in pf.chunks:
            score = _score_chunk(chunk, query_words)
            if score > 0:
                scored.append((score, pf.filename, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        # No keyword overlap at all — fall back to the first chunk of each file
        # so the model still has *some* grounding context.
        return [(pf.filename, pf.chunks[0]) for pf in parsed_files if pf.chunks][:top_k]
    return [(fname, chunk) for _, fname, chunk in scored[:top_k]]


def build_context_block(parsed_files: list[ParsedFile], query: str) -> str:
    relevant = retrieve_relevant_chunks(parsed_files, query)
    if not relevant:
        return ""
    parts = [f"[From {fname}]\n{chunk}" for fname, chunk in relevant]
    return "\n\n---\n\n".join(parts)