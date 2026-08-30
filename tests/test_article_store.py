import json

import pytest

from ArticleExtraction.article_store import (
    get_article,
    get_connection,
    has_extracted_text,
    init_db,
    is_extracted,
    mark_extracted,
    mark_failed,
    upsert_metadata,
)


def make_doc():
    return {
        "_id": "nyt://article/abc-123",
        "web_url": "https://www.nytimes.com/2025/10/01/abc-123.html",
        "headline": {"main": "Some Headline", "kicker": ""},
        "pub_date": "2025-10-01T00:17:01Z",
        "section_name": "U.S.",
        "subsection_name": "Politics",
        "abstract": "An abstract.",
        "snippet": "A snippet.",
        "byline": {"original": "By Jane Doe"},
        "word_count": 1200,
        "document_type": "article",
        "news_desk": "National",
        "type_of_material": "News",
        "source": "The New York Times",
        "keywords": [{"name": "subject", "value": "Politics"}],
    }


@pytest.fixture
def conn(tmp_path):
    db = tmp_path / "test.db"
    connection = get_connection(str(db))
    init_db(connection)
    yield connection
    connection.close()


def test_init_db_creates_articles_table(conn):
    tables = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name='articles'"
    ).fetchall()
    assert len(tables) == 1


def test_upsert_metadata_inserts_pending_row(conn):
    upsert_metadata(conn, make_doc(), "abc-123", "2025_10")
    row = get_article(conn, "abc-123")
    assert row is not None
    assert row["headline"] == "Some Headline"
    assert row["section"] == "U.S."
    assert row["subsection"] == "Politics"
    assert row["word_count"] == 1200
    assert row["status"] == "pending"
    assert row["month"] == "2025_10"
    assert json.loads(row["raw"])["web_url"].endswith("abc-123.html")


def test_upsert_metadata_does_not_reset_extracted_status(conn):
    upsert_metadata(conn, make_doc(), "abc-123", "2025_10")
    mark_extracted(conn, "abc-123", "Full text")
    upsert_metadata(conn, make_doc(), "abc-123", "2025_10")
    row = get_article(conn, "abc-123")
    assert row["status"] == "extracted"
    assert row["extracted_text"] == "Full text"


def test_is_extracted_false_when_pending(conn):
    upsert_metadata(conn, make_doc(), "abc-123", "2025_10")
    assert is_extracted(conn, "abc-123") is False


def test_mark_extracted_sets_status_and_text(conn):
    upsert_metadata(conn, make_doc(), "abc-123", "2025_10")
    mark_extracted(conn, "abc-123", "The article body.")
    row = get_article(conn, "abc-123")
    assert row["status"] == "extracted"
    assert row["extracted_text"] == "The article body."
    assert row["extracted_at"] is not None
    assert is_extracted(conn, "abc-123") is True


def test_mark_failed_sets_status_and_error(conn):
    upsert_metadata(conn, make_doc(), "abc-123", "2025_10")
    mark_failed(conn, "abc-123", "blocked by paywall")
    row = get_article(conn, "abc-123")
    assert row["status"] == "failed"
    assert row["error"] == "blocked by paywall"
    assert is_extracted(conn, "abc-123") is False


def test_mark_extracted_upserts_row_when_metadata_missing(conn):
    mark_extracted(conn, "legacy-id", "Legacy text")
    row = get_article(conn, "legacy-id")
    assert row["status"] == "extracted"
    assert row["extracted_text"] == "Legacy text"


def test_mark_extracted_clears_error_when_word_count_ok(conn):
    upsert_metadata(conn, make_doc(), "abc-123", "2025_10")  # word_count = 1200
    mark_extracted(conn, "abc-123", "word " * 10)
    row = get_article(conn, "abc-123")
    assert row["error"] is None


def test_mark_extracted_sets_error_when_word_count_exceeded(conn):
    upsert_metadata(conn, make_doc(), "abc-123", "2025_10")  # word_count = 1200
    mark_extracted(conn, "abc-123", "word " * 1201)
    row = get_article(conn, "abc-123")
    assert row["status"] == "extracted"
    assert row["extracted_text"] is not None
    assert row["error"] == "Word count exceeded"


def test_mark_extracted_no_word_count_check_without_metadata(conn):
    mark_extracted(conn, "legacy-id", "word " * 500)
    row = get_article(conn, "legacy-id")
    assert row["error"] is None


def test_has_extracted_text_false_when_no_row(conn):
    assert has_extracted_text(conn, "missing-id") is False


def test_has_extracted_text_false_when_text_empty(conn):
    upsert_metadata(conn, make_doc(), "abc-123", "2025_10")
    assert has_extracted_text(conn, "abc-123") is False


def test_has_extracted_text_true_when_text_present(conn):
    upsert_metadata(conn, make_doc(), "abc-123", "2025_10")
    conn.execute(
        "UPDATE articles SET extracted_text = 'Body text' WHERE id = 'abc-123'"
    )
    conn.commit()
    assert has_extracted_text(conn, "abc-123") is True
