"""Parse article paragraphs into sentence records."""

import re
from pathlib import Path
from typing import Dict, List


SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def split_sentences(text: str) -> List[str]:
    """Split text at punctuation followed by whitespace and a capital letter."""
    if not text or not text.strip():
        return []
    return [part.strip() for part in SENTENCE_BOUNDARY.split(text) if part.strip()]


def parse_text(text: str) -> List[Dict]:
    """Parse an article body into sentence records.

    Each non-empty line is treated as one paragraph, mirroring the on-disk
    format produced by ``ExtractHTML.py`` (paragraphs joined by newlines).
    This lets callers parse text fetched straight from the database without
    materializing a temporary file.
    """
    sentences = []
    full_text_position = 0
    sentence_id = 0
    for paragraph_id, line in enumerate(text.split("\n")):
        paragraph = line.rstrip("\r\n")
        if not paragraph.strip():
            continue
        for part in split_sentences(paragraph):
            start_char = full_text_position
            end_char = start_char + len(part)
            sentences.append({
                "id": sentence_id,
                "text": part,
                "paragraph_id": paragraph_id,
                "start_char": start_char,
                "end_char": end_char,
                "word_count": len(part.split()),
            })
            sentence_id += 1
            full_text_position = end_char + 1
    return sentences


def read_and_parse(file_path: str) -> List[Dict]:
    """Read a UTF-8 article where each non-empty line is a paragraph."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as article_file:
        return parse_text(article_file.read())