# Batch HTML Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Process every article in a NYT archive JSON file and save each extracted article plus a per-article process log.

**Architecture:** Keep the utility in `ExtractHTML.py`, but move import-time execution into explicit functions. Pure helpers handle document validation, HTML-to-text cleaning, and output paths; Selenium is created per article and always closed; the batch runner catches failures and logs them before continuing.

**Tech Stack:** Python, Selenium, BeautifulSoup, pytest, standard-library `json`, `argparse`, `logging`, and `pathlib`.

## Global Constraints

- Read articles from `response.docs`.
- Read article URLs from `web_url` and names from `_id`.
- Save results under `nyt_output/<source-json-stem>/`.
- Save article text as `<_id>.txt`.
- Append timestamped `SUCCESS` or `ERROR` records to `process.log`.
- Continue processing after individual failures.

---

### Task 1: Add pure extraction and output helpers

**Files:**
- Modify: `ExtractHTML.py`
- Test: `tests/test_extract_html.py`

**Interfaces:**
- Produce `clean_article_text(soup) -> str`.
- Produce `output_directory(source_json) -> Path`.
- Produce `article_output_path(source_json, article_id) -> Path`.

- [ ] **Step 1: Write failing tests** for noise filtering, source-stem output directories, and `_id.txt` naming.
- [ ] **Step 2: Run `pytest tests/test_extract_html.py -q` and verify the new tests fail.**
- [ ] **Step 3: Implement the helpers without browser startup at import time.**
- [ ] **Step 4: Run the focused tests and verify they pass.**

### Task 2: Implement one-article Selenium extraction

**Files:**
- Modify: `ExtractHTML.py`
- Test: `tests/test_extract_html.py`

**Interfaces:**
- Produce `extract_article(url) -> str`, which creates a driver, loads the URL, extracts text, and calls `quit()` in `finally`.

- [ ] **Step 1: Add a test using mocked Selenium/HTML to verify extraction and driver cleanup.**
- [ ] **Step 2: Run the focused test and verify it fails.**
- [ ] **Step 3: Move the existing browser setup and selector logic into `extract_article`.**
- [ ] **Step 4: Run the focused test and verify it passes.**

### Task 3: Implement JSON batch processing and logging

**Files:**
- Modify: `ExtractHTML.py`
- Test: `tests/test_extract_html.py`

**Interfaces:**
- Produce `process_source_json(source_json) -> None`.
- CLI calls `process_source_json` from `main()` using one positional path.

- [ ] **Step 1: Add tests for successful writes, failure logging, and continuing after a failed document using mocked `extract_article`.**
- [ ] **Step 2: Run the focused tests and verify they fail.**
- [ ] **Step 3: Load `response.docs`, validate `_id` and `web_url`, write article files, and configure append-mode logging to `process.log`.**
- [ ] **Step 4: Run the focused tests and verify they pass.**
- [ ] **Step 5: Run `pytest -q` to verify the full suite.**
