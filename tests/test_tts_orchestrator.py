"""Tests for the tts orchestrator's DB-driven input and resume logic.

Synthesis is monkeypatched so these tests never touch the real Kokoro model.
"""

import json
import os
import sqlite3

import pytest

from tts.Kokoro.text_processor import parse_text, read_and_parse
from tts.DBArticles2Audios import DEFAULT_DB, DEFAULT_OUTPUT_DIR, generate_from_db, query_articles


def test_default_paths_are_repo_root_absolute():
    # Defaults must not depend on the current working directory, otherwise the
    # script creates an empty DB next to wherever it is invoked from.
    assert os.path.isabs(DEFAULT_DB)
    assert os.path.isabs(DEFAULT_OUTPUT_DIR)
    assert DEFAULT_DB.endswith("articles.db")
    assert DEFAULT_OUTPUT_DIR.endswith(os.path.join("tts", "audio"))

ELIGIBLE_TEXT = "First paragraph. It has two sentences.\nSecond paragraph."


def _make_db(tmp_path, rows):
    """Create a minimal articles table and return its path."""
    db_path = tmp_path / "articles.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE articles (
            id TEXT PRIMARY KEY,
            headline TEXT,
            review_results TEXT,
            extracted_text TEXT
        );
        """
    )
    conn.executemany(
        "INSERT INTO articles (id, headline, review_results, extracted_text) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    return str(db_path)


def _fake_synthesize(sentences, output_path, speaker="am", lang="a"):
    """Stand-in for synthesize_sentences: one second per sentence, no audio."""
    return {
        "audio_file": str(output_path),
        "sentences": [
            {"phoneme_duration": 1.0, "phoneme_count": 4} for _ in sentences
        ],
    }


def test_query_articles_filters_by_review_results_and_text(tmp_path):
    db_path = _make_db(
        tmp_path,
        [
            ("aaa", "Good one", None, ELIGIBLE_TEXT),
            ("bbb", "NA one", "NA", ELIGIBLE_TEXT),
            ("ccc", "No text", None, ""),
            ("ddd", "NA no text", "NA", ""),
        ],
    )
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = query_articles(conn)
    finally:
        conn.close()
    assert [row["id"] for row in rows] == ["aaa"]


def test_parse_text_matches_read_and_parse(tmp_path):
    article = tmp_path / "article.txt"
    article.write_text(ELIGIBLE_TEXT + "\n", encoding="utf-8")
    assert parse_text(ELIGIBLE_TEXT + "\n") == read_and_parse(str(article))


def test_generate_from_db_skips_existing_outputs(tmp_path, monkeypatch):
    db_path = _make_db(tmp_path, [("aaa", "Good one", None, ELIGIBLE_TEXT)])
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "aaa_kokoro.wav").write_bytes(b"fake")
    (output_dir / "aaa_timings.json").write_text("{}", encoding="utf-8")

    def _fail(*args, **kwargs):
        raise AssertionError("synthesize_sentences should not be called")

    monkeypatch.setattr("tts.orchestrator.synthesize_sentences", _fail)
    generated, skipped, failed = generate_from_db(db_path, str(output_dir))
    assert (generated, skipped, failed) == (0, 1, 0)


def test_generate_from_db_creates_timings(tmp_path, monkeypatch):
    db_path = _make_db(tmp_path, [("aaa", "Good one", None, ELIGIBLE_TEXT)])
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    monkeypatch.setattr("tts.orchestrator.synthesize_sentences", _fake_synthesize)
    generated, skipped, failed = generate_from_db(db_path, str(output_dir))
    assert (generated, skipped, failed) == (1, 0, 0)

    timings_file = output_dir / "aaa_timings.json"
    assert timings_file.exists()
    data = json.loads(timings_file.read_text(encoding="utf-8"))
    assert data["metadata"]["article_id"] == "aaa"
    assert data["metadata"]["headline"] == "Good one"
    assert len(data["sentences"]) == 3  # 2 in first paragraph + 1 in second
    assert data["sentences"][-1]["end_time"] == 3.0


def test_generate_from_db_single_eligible_id(tmp_path, monkeypatch):
    db_path = _make_db(
        tmp_path,
        [
            ("aaa", "Good one", None, ELIGIBLE_TEXT),
            ("bbb", "NA one", "NA", ELIGIBLE_TEXT),
        ],
    )
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    monkeypatch.setattr("tts.orchestrator.synthesize_sentences", _fake_synthesize)
    generated, skipped, failed = generate_from_db(db_path, str(output_dir), article_id="aaa")
    assert (generated, skipped, failed) == (1, 0, 0)
    assert (output_dir / "aaa_timings.json").exists()
    assert not (output_dir / "bbb_timings.json").exists()


def test_generate_from_db_unknown_or_ineligible_id_raises(tmp_path, monkeypatch):
    db_path = _make_db(
        tmp_path,
        [
            ("aaa", "Good one", None, ELIGIBLE_TEXT),
            ("bbb", "NA one", "NA", ELIGIBLE_TEXT),
        ],
    )
    with pytest.raises(ValueError):
        generate_from_db(db_path, str(tmp_path / "out"), article_id="nope")
    with pytest.raises(ValueError):
        generate_from_db(db_path, str(tmp_path / "out"), article_id="bbb")
