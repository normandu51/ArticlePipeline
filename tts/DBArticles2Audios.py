"""CLI for generating article audio and sentence timing JSON from articles.db.

Input
-----
``articles.db`` (SQLite) produced by ``ExtractHTML.py``. Only articles whose
``review_results`` is not 'NA' — i.e. flagged as suitable for language
learning — and that have non-empty ``extracted_text`` are processed.

audio
------
For every processed article, two files named after the NYT article ``id``:

    <output_dir>/<id>_kokoro.wav     concatenated audio, 24 kHz mono
    <output_dir>/<id>_timings.json   per-sentence timing metadata

Already-existing outputs are skipped so the batch can be re-run safely.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from PipelineConfig import *


try:
    from tts.Kokoro.text_processor import parse_text
    from tts.Kokoro.timing_extractor import extract_timings
    from tts.Kokoro.tts_synthesizer import synthesize_sentences
except ImportError:  # fallback for running as a plain script from inside tts/
    _KOKORO_DIR = str(Path(__file__).resolve().parent / "Kokoro")
    if _KOKORO_DIR not in sys.path:
        sys.path.insert(0, _KOKORO_DIR)
    from text_processor import parse_text
    from timing_extractor import extract_timings
    from tts_synthesizer import synthesize_sentences

def _ensure_articles_table(conn, db_path):
    """Raise a clear error when the DB has no articles table."""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='articles'"
    ).fetchone()
    if not row:
        raise RuntimeError(
            f"Database '{db_path}' has no 'articles' table. "
            "Run ExtractHTML.py first to populate it, or point --db at the "
            "correct database."
        )

def get_connection(db_path=DEFAULT_DB_PATH):
    """Open a SQLite connection with row access by column name."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def query_articles(conn):
    """Return eligible articles, ordered by id.

    An article is eligible when its ``review_results`` is not 'NA' (a NULL
    value counts as eligible) and it has non-empty ``extracted_text``.
    """
    return conn.execute(
        """
        SELECT id, headline, extracted_text
        FROM articles
        WHERE (review_results IS NULL OR review_results != 'NA')
          AND extracted_text IS NOT NULL
          AND length(trim(extracted_text)) > 0
        ORDER BY id
        """
    ).fetchall()


def build_timings_data(article, db_path, audio_file, sentences, timings, speaker, lang):
    total_duration = timings[-1]["end_time"] if timings else 0.0
    return {
        "metadata": {
            "article_id": article["id"],
            "headline": article["headline"],
            "source_db": db_path,
            "audio_file": str(audio_file),
            "total_duration": total_duration,
            "sentence_count": len(timings),
            "paragraph_count": len({item["paragraph_id"] for item in sentences}),
            "speaker": speaker,
            "language": lang,
            "generated_at": datetime.now().isoformat(),
        },
        "sentences": timings,
    }


def synthesize_article(article, output_dir, db_path=DEFAULT_DB_PATH, speaker="am", lang="a"):
    """Synthesize one article row into WAV + timings JSON named by article id."""
    sentences = parse_text(article["extracted_text"])
    if not sentences:
        raise ValueError(f"No sentences found for article {article['id']}")

    output_path = Path(output_dir)
    audio_file = output_path / f"{article['id']}_kokoro.wav"
    timings_file = output_path / f"{article['id']}_timings.json"

    synthesis = synthesize_sentences(sentences, str(audio_file), speaker=speaker, lang=lang)
    timings = extract_timings(sentences, synthesis["sentences"])
    data = build_timings_data(article, db_path, audio_file, sentences, timings, speaker, lang)
    timings_file.parent.mkdir(parents=True, exist_ok=True)
    with timings_file.open("w", encoding="utf-8") as timing_file:
        json.dump(data, timing_file, indent=2)
    return str(audio_file), str(timings_file)


def generate_from_db(
    db_path=DEFAULT_DB_PATH,
    output_dir=DEFAULT_OUTPUT_DIR,
    speaker="am",
    lang="a",
    article_id=None,
    limit=None,
):
    """Synthesize every eligible article in the DB into the output directory.

    Returns ``(generated, skipped, failed)``. Articles whose WAV and timings
    files already exist are skipped, so re-running the batch is safe.
    """
    conn = get_connection(db_path)
    try:
        _ensure_articles_table(conn, db_path)
        articles = query_articles(conn)
        if article_id:
            articles = [row for row in articles if row["id"] == article_id]
            if not articles:
                raise ValueError(f"Article id {article_id} not found or not eligible")

        generated = skipped = failed = 0
        for article in (articles[:limit] if limit else articles):
            current_id = article["id"]
            audio_file = Path(output_dir) / f"{current_id}_kokoro.wav"
            timings_file = Path(output_dir) / f"{current_id}_timings.json"
            if audio_file.exists() and timings_file.exists():
                print(f"SKIP article_id={current_id} outputs exist")
                skipped += 1
                continue
            try:
                audio, timings = synthesize_article(
                    article, output_dir, db_path, speaker, lang
                )
                print(f"SUCCESS article_id={current_id} audio={audio} timings={timings}")
                generated += 1
            except Exception as error:
                print(f"ERROR article_id={current_id} message={error}", file=sys.stderr)
                failed += 1
        print(f"DONE generated={generated} skipped={skipped} failed={failed}")
        return generated, skipped, failed
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate Kokoro audio and timings from eligible articles in articles.db"
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help=f"Path to the SQLite database (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for WAV and timings JSON files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--speaker", default="am", help="Kokoro voice prefix (default: am)"
    )
    parser.add_argument(
        "--lang",
        default="a",
        help="Kokoro language code (default: a = American English)",
    )
    parser.add_argument(
        "--id", dest="article_id", default=None, help="Process only this article id"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Process at most N articles"
    )
    args = parser.parse_args()
    generate_from_db(
        REPO_ROOT+"/"+args.db, REPO_ROOT+"/"+args.output_dir, args.speaker, args.lang, args.article_id, args.limit
    )


if __name__ == "__main__":
    main()