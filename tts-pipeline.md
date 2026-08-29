# TTS Pipeline: Orchestrator (`tts/orchestrator.py`)

The TTS orchestrator turns **extracted, review-approved NYT articles** stored in
`articles.db` into **spoken audio + per-sentence timing JSON**. It is the second
half of the ArticleExtraction pipeline:

```
ExtractHTML.py  ──►  articles.db  ──►  tts/orchestrator.py  ──►  tts/Output/
  (extract text)       (SQLite)          (Kokoro TTS)           <id>_kokoro.wav
                                                                <id>_timings.json
```

---

## 1. Input Logic

### Source: `articles.db` (SQLite)

The orchestrator reads from the SQLite database written by `ExtractHTML.py`
(see `article_store.py`, default path `articles.db` in the repo root). The
database is the **single source of truth** for article text and pipeline state.

### Eligibility filter

An article is processed **only when all of the following hold**:

1. **`review_results` is not `'NA'`** — i.e. the article was reviewed and
   flagged as suitable for language learning. Note the column is called
   `review_results` (values seen in practice: `NULL` or `'NA'`); `NULL` counts
   as eligible.
   The equivalent SQL condition is `review_results IS NULL OR review_results != 'NA'`.
2. **`extracted_text` is non-empty** — the article was successfully extracted.

Articles whose `review_results = 'NA'` (e.g. containing sensitive words, judged
unsuitable for learning) are **excluded**.

The query used (`query_articles()` in the orchestrator):

```sql
SELECT id, headline, extracted_text
FROM articles
WHERE (review_results IS NULL OR review_results != 'NA')
  AND extracted_text IS NOT NULL
  AND length(trim(extracted_text)) > 0
ORDER BY id;
```

### Text format

`extracted_text` is the clean article body with **one paragraph per line**
(newline-separated). The orchestrator parses it via `parse_text()` in
`tts/Kokoro/text_processor.py`, which treats each non-empty line as a paragraph
and splits it into sentences (sentence boundary = punctuation followed by
whitespace and a capital letter). Each sentence becomes a record with
`id`, `text`, `paragraph_id`, `start_char`, `end_char`, `word_count`.

> The same parser backs `read_and_parse()` (file-based), so a temporary file is
> never needed when reading from the DB.

---

## 2. Output Logic

For every eligible article, two files are written to the output directory
(default `tts/Output/`), named after the NYT article **`id`** field:

```
tts/Output/<id>_kokoro.wav
tts/Output/<id>_timings.json
```

Example (`id = 2090e468-8163-5f8b-aeef-dba7950df018`):

```
tts/Output/2090e468-8163-5f8b-aeef-dba7950df018_kokoro.wav
tts/Output/2090e468-8163-5f8b-aeef-dba7950df018_timings.json
```

### `<id>_kokoro.wav`

Concatenated audio for the whole article, synthesized by
`tts/Kokoro/tts_synthesizer.py`:

- **24 kHz mono WAV**
- Sentence chunks concatenated in order with no silence padding
- Voice / language controlled by `--speaker` (default `am`) and `--lang`
  (default `a`, American English)

### `<id>_timings.json`

Sentence-level timing metadata used downstream (e.g. for karaoke-style
word/sentence highlighting). Schema:

```json
{
  "metadata": {
    "article_id": "2090e468-8163-5f8b-aeef-dba7950df018",
    "headline": "Judge Disqualifies Nevada's Acting U.S. Attorney",
    "source_db": "articles.db",
    "audio_file": "tts/Output/2090e468-..._kokoro.wav",
    "total_duration": 63.42,
    "sentence_count": 22,
    "paragraph_count": 12,
    "speaker": "am",
    "language": "a",
    "generated_at": "2026-08-29T15:15:00.000000+00:00"
  },
  "sentences": [
    {
      "id": 0,
      "sentence": "A federal judge on Tuesday disqualified Nevada's top federal prosecutor.",
      "paragraph_id": 0,
      "word_count": 13,
      "start_time": 0.0,
      "end_time": 2.875,
      "duration": 2.875,
      "phoneme_count": 31
    }
  ]
}
```

`start_time` / `end_time` are **cumulative seconds** from the start of the
article audio; `duration` is the sentence's own length.

### Resume / idempotency

If **both** `<id>_kokoro.wav` **and** `<id>_timings.json` already exist for an
article, the orchestrator **skips** it (`SKIP` line). This makes re-runs safe:
you can interrupt and restart a large batch without regenerating finished
articles.

---

## 3. How to Use

### Prerequisites

- Python environment with Kokoro TTS installed and working offline — see
  `KOKORO_SETUP.md` (model at `tts/Kokoro/Kokoro-82M/`).
- English G2P dependency `en_core_web_sm` installed once (see
  `KOKORO_SETUP.md` / repo notes) for American English synthesis.
- `articles.db` populated by `ExtractHTML.py` (or `--db` pointing at one).

### CLI

```bash
# Activate the project virtual environment
source .venv/bin/activate

# Process ALL eligible articles -> tts/Output/
python tts/orchestrator.py

# Custom DB / output directory
python tts/orchestrator.py --db articles.db --output-dir tts/Output

# Voice and language
python tts/orchestrator.py --speaker af --lang a        # American Female

# Process a single article by id
python tts/orchestrator.py --id 2090e468-8163-5f8b-aeef-dba7950df018

# Smoke-test on the first N articles
python tts/orchestrator.py --limit 5
```

| Argument        | Default        | Description                                   |
|-----------------|----------------|-----------------------------------------------|
| `--db`          | `<repo>/articles.db` | SQLite database produced by `ExtractHTML.py` (resolved against the repo root, independent of the shell's cwd) |
| `--output-dir`  | `<repo>/tts/Output` | Where `<id>_kokoro.wav` + `<id>_timings.json` go |
| `--speaker`     | `am`           | Kokoro voice prefix (`af`, `am`, `bf`, `bm`)  |
| `--lang`        | `a`            | Kokoro language code (`a`, `b`, `es`, ...)    |
| `--id`          | *(all)*        | Process only this article id                  |
| `--limit`       | *(all)*        | Process at most N articles                    |

### Troubleshooting

- **`sqlite3.OperationalError: no such table: articles`** — the script opened a
  DB that has not been populated. Defaults are resolved against the repo root,
  so this usually means `ExtractHTML.py` has not been run, or `--db` points at
  the wrong/empty file. The orchestrator now raises a clear message telling you
  which DB it looked at. Delete any accidentally created empty
  `<something>/articles.db` files (e.g. a stray `tts/articles.db` created by
  earlier runs from the wrong working directory).

### Programmatic API

```python
from tts.orchestrator import generate_from_db, query_articles

# Batch-generate, returns (generated, skipped, failed)
generated, skipped, failed = generate_from_db(
    db_path="articles.db", output_dir="tts/Output", speaker="am", lang="a"
)

# Inspect what would be processed
from article_store import get_connection
conn = get_connection("articles.db")
rows = query_articles(conn)   # list of sqlite3.Row (id, headline, extracted_text)
conn.close()
```

### Example run output

```
SUCCESS article_id=2090e468-8163-5f8b-aeef-dba7950df018 audio=tts/Output/2090e468-..._kokoro.wav timings=tts/Output/2090e468-..._timings.json
SKIP    article_id=2f40871a-2a54-59e1-9ef6-d144993a72c1 outputs exist
ERROR   article_id=... message=<exception>
DONE generated=210 skipped=1 failed=0
```

`SUCCESS` = synthesized, `SKIP` = outputs already present, `ERROR` = failed for
this article (run continues), and a final `DONE` summary line.

---

## 4. Running the Tests

```bash
# Activate the venv first, then:
.venv/bin/python -m pytest tests/test_tts_orchestrator.py tests/test_tts_pipeline.py -v
```

The orchestrator tests monkeypatch the synthesizer, so they never load the
Kokoro model and can run on any machine.
