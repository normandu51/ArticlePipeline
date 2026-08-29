# Design: Externalize NYT extraction configuration

**Date:** 2026-08-29
**Status:** Approved (user: "a, ok / b, ok")

## Goal

Make `ExtractHTML.py` generic, readable, maintainable and scalable by moving all
tunable values (extraction filters, noise patterns, body selectors, ancestor
exclusion rules, and driver/network settings) into a single config module.
Update the unit tests to match the new API and fix the four pre-existing stale
tests.

## Decisions (from brainstorming)

- Config format: **Python module** (`extract_config.py`) — native types, no parsing, no new deps.
- Scope: **filters + driver/network settings** both move to config.
- Ancestor-exclusion rule: **structured** — match by `tag`, `class`, or `name` attribute.
- Rename `is_in_interactive_body` → `is_in_excluded_container` (approved).
- Stale tests: fix the two driver/profile tests, wire `is_block_page` in as an
  advisory check, and adjust the `.txt`-writing test to assert the DB instead.

## Architecture

- `extract_config.py` — data only, no logic. Holds:
  - Driver: `CHROME_BINARY_PATHS`, `CHROMEDRIVER_PATHS`, `USER_AGENT`,
    `WINDOW_SIZE`, `LOAD_SLEEP_RANGE`, `QUIT_SLEEP_RANGE`,
    `CHROME_PROFILE_ENV_VAR`, `DEFAULT_CHROME_PROFILE_DIR`.
  - Filters: `SECTION_NAMES`, `SUBSECTIONS`, `MATERIEL_TYPES`, `NEWS_DESKS`.
  - Cleaning: `NOISE_PATTERNS`, `BODY_SELECTORS`, `EXCLUDED_ANCESTOR_RULES`.
- `ExtractHTML.py` — generic pipeline only; reads everything from `extract_config`.
  - `get_chrome_profile_dir()`: env var wins, else `DEFAULT_CHROME_PROFILE_DIR`.
  - `build_chrome_options()`: adds `--user-data-dir=<profile>`; uses config
    `USER_AGENT` / `WINDOW_SIZE`.
  - `should_exclude_document(doc)`: pure helper consolidating the inline
    metadata filter from `process_source_json`.
  - `is_in_excluded_container(paragraph)`: ancestor exclusion via config rules;
    a paragraph is excluded when any ancestor satisfies all filters of one rule.
  - `clean_article_text()`: body located via `BODY_SELECTORS`.
  - `extract_article()`: config sleep ranges; `is_block_page` used as advisory —
    only raises "Blocked page" when extraction also failed.

## Testing

- `tests/test_extract_html.py` updated to new names/API.
- New tests: `should_exclude_document` per filter category,
  `is_in_excluded_container` with configurable rules (`tag`/`class`/`name`),
  `matches_noise_pattern`, `get_chrome_profile_dir` env override,
  config-driven `BODY_SELECTORS`.
- `test_process_source_json_writes_articles_and_logs_failures` rewritten to
  assert DB rows + log lines instead of `.txt` files.
