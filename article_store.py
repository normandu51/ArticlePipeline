"""SQLite-backed storage for extracted NYT articles.

The `articles` table stores every archive metadata field alongside the
extracted text and pipeline state, so the database is a single source of
truth instead of one `.txt` file per article.

Article lifecycle (the `status` column):

    pending  ->  extracted  ->  (enriched / done)
      |              ^
      +-- failed ----+
"""

import json
import sqlite3
from datetime import datetime, timezone

DEFAULT_DB_PATH = "articles.db"

# Statuses that mean "already processed, do not extract again".
PROCESSED_STATUSES = frozenset({"extracted", "enriched", "done"})

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id               TEXT PRIMARY KEY,           -- NYT article id (uuid)
    uri              TEXT,                       -- full nyt:// URI
    url              TEXT,                       -- web_url
    headline         TEXT,
    pub_date         TEXT,
    section          TEXT,                       -- section_name
    subsection       TEXT,                       -- subsection_name
    abstract         TEXT,
    snippet          TEXT,
    byline           TEXT,
    word_count       INTEGER,
    document_type    TEXT,
    news_desk        TEXT,
    type_of_material TEXT,
    source           TEXT,
    keywords         TEXT,                       -- JSON-encoded keyword list
    month            TEXT,                       -- '2025_10' (archive file stem)
    raw              TEXT,                       -- full original archive doc (JSON)
    status           TEXT NOT NULL DEFAULT 'pending',
    extracted_text   TEXT,                       -- clean article body
    error            TEXT,
    extracted_at     TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_articles_month  ON articles(month);
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
"""

_METADATA_COLUMNS = (
    "uri",
    "url",
    "headline",
    "pub_date",
    "section",
    "subsection",
    "abstract",
    "snippet",
    "byline",
    "word_count",
    "document_type",
    "news_desk",
    "type_of_material",
    "source",
    "keywords",
    "month",
    "raw",
)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_connection(db_path=DEFAULT_DB_PATH):
    """Open a SQLite connection with row access by column name."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn):
    """Create the articles table and supporting indexes if missing."""
    conn.executescript(SCHEMA + INDEXES)
    conn.commit()


def _metadata_values(doc, article_id, month):
    """Extract flat metadata values from an NYT archive doc."""
    return {
        "uri": doc.get("_id"),
        "url": doc.get("web_url"),
        "headline": (doc.get("headline") or {}).get("main"),
        "pub_date": doc.get("pub_date"),
        "section": doc.get("section_name"),
        "subsection": doc.get("subsection_name"),
        "abstract": doc.get("abstract"),
        "snippet": doc.get("snippet"),
        "byline": (doc.get("byline") or {}).get("original"),
        "word_count": doc.get("word_count"),
        "document_type": doc.get("document_type"),
        "news_desk": doc.get("news_desk"),
        "type_of_material": doc.get("type_of_material"),
        "source": doc.get("source"),
        "keywords": json.dumps(doc.get("keywords") or [], ensure_ascii=False),
        "month": month,
        "raw": json.dumps(doc, ensure_ascii=False),
    }


def upsert_metadata(conn, doc, article_id, month):
    """Insert an archive doc's metadata as a 'pending' row.

    On conflict (article already known) only metadata fields are refreshed;
    the pipeline status and extracted text are never reset.
    """
    values = _metadata_values(doc, article_id, month)
    now = now_iso()
    columns = list(_METADATA_COLUMNS)
    placeholders = ", ".join("?" for _ in columns)
    update_set = ", ".join(
        f"{col} = excluded.{col}" for col in columns if col != "month"
    )
    sql = (
        f"INSERT INTO articles "
        f"(id, {', '.join(columns)}, status, created_at, updated_at) "
        f"VALUES (?, {placeholders}, 'pending', ?, ?) "
        f"ON CONFLICT(id) DO UPDATE SET {update_set}, updated_at = excluded.updated_at"
    )
    conn.execute(
        sql,
        [article_id, *[values[col] for col in columns], now, now],
    )
    conn.commit()


def is_extracted(conn, article_id):
    """Return True when the article is already processed (skip re-extraction)."""
    row = conn.execute(
        "SELECT status FROM articles WHERE id = ?", (article_id,)
    ).fetchone()
    return bool(row and row["status"] in PROCESSED_STATUSES)


def has_extracted_text(conn, article_id):
    """Return True when a row exists for the article with a non-empty extracted_text."""
    row = conn.execute(
        "SELECT extracted_text FROM articles WHERE id = ?", (article_id,)
    ).fetchone()
    return bool(row and row["extracted_text"])


def mark_extracted(conn, article_id, text):
    """Record successful extraction (also backfills rows with no metadata)."""
    now = now_iso()
    conn.execute(
        """
        INSERT INTO articles (id, status, extracted_text, extracted_at,
                              created_at, updated_at)
        VALUES (?, 'extracted', ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status = 'extracted',
            extracted_text = excluded.extracted_text,
            extracted_at = excluded.extracted_at,
            error = NULL,
            updated_at = excluded.updated_at
        """,
        (article_id, text, now, now, now),
    )
    conn.commit()


def mark_failed(conn, article_id, error):
    """Record an extraction failure on a row (upserts if missing)."""
    now = now_iso()
    conn.execute(
        """
        INSERT INTO articles (id, status, error, created_at, updated_at)
        VALUES (?, 'failed', ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status = 'failed',
            error = excluded.error,
            updated_at = excluded.updated_at
        """,
        (article_id, error, now, now),
    )
    conn.commit()


def get_article(conn, article_id):
    """Return a single article row (as sqlite3.Row) or None."""
    return conn.execute(
        "SELECT * FROM articles WHERE id = ?", (article_id,)
    ).fetchone()
