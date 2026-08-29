# How HTML Article Extraction Works

> Source: `ExtractHTML.py`
> This document explains how article content is extracted from NYT article HTML and the rules used to pick the "right" content.

## Overview

The extraction pipeline has two stages:

1. **`extract_article(url)`** — loads the rendered page via Selenium (headless Chrome) and hands the parsed DOM to the extractor.
2. **`clean_article_text(soup)`** — the actual HTML → text rule: pick the right container, pull out the paragraphs, and filter noise.

---

## Stage 1: Loading the rendered HTML — `extract_article()`

```python
driver.get(url)
time.sleep(random.uniform(7, 11))
soup = BeautifulSoup(driver.page_source, "html.parser")
```

- Uses a **real headless Chrome** (via Selenium), so the JavaScript-rendered DOM is present in `page_source` (NYT content is JS-rendered, so a plain HTTP fetch would miss most of it).
- **Anti-detection setup** so NYT's bot / paywall detection does not block the page:
  - Spoofs `navigator.webdriver`, `navigator.plugins`, `navigator.languages` via CDP (`Page.addScriptToEvaluateOnNewDocument`).
  - Sets a realistic Chrome user-agent.
  - Disables automation flags (`excludeSwitches: enable-automation`, `useAutomationExtension: false`).
- **Random sleeps** (`config.LOAD_SLEEP_RANGE` 7–11s after load, `config.QUIT_SLEEP_RANGE` 2–5s before quit) to look human and let ads / content settle.

---

## Stage 2: The rule for picking the right content — `clean_article_text()`

### Container selection (priority list)

The core rule is a **priority list of container selectors**; the **first match wins**:

```python
# extract_config.py
BODY_SELECTORS = [
    ("section", {"name": "articleBody"}),      # 1. NYT's semantic article body
    ("section", {"class": "meteredContent"}),  # 2. paywall-metered wrapper (fallback)
    ("main", None),                            # 3. semantic <main>
    ("article", None),                         # 4. semantic <article>
]
```

| Priority | Selector | Notes |
|----------|----------|-------|
| 1 | `section[name="articleBody"]` | Primary target; NYT tags the article body with the `name="articleBody"` attribute. |
| 2 | `section.meteredContent` | NYT's metered-paywall wrapper; used when selector #1 is missing. |
| 3 | `<main>` | Generic HTML5 semantic element (last-resort fallback). |
| 4 | `<article>` | Generic HTML5 semantic element (last-resort fallback). |

If **no** selector matches → raises `RuntimeError("Article body not found")`.

### Paragraph extraction

Once the container is found, all `<p>` elements inside it are extracted — **except** paragraphs inside a container matched by an exclusion rule:

```python
# extract_config.py — ancestor exclusion rules (configurable)
EXCLUDED_ANCESTOR_RULES = [
    {"class": "interactive-body"},
]

def is_in_excluded_container(paragraph):
    for ancestor in paragraph.parents:
        if any(_matches_rule(ancestor, rule) for rule in config.EXCLUDED_ANCESTOR_RULES):
            return True
    return False

content_lines = [
    p.get_text().strip()
    for p in article.find_all("p")
    if not is_in_excluded_container(p)
]
```

- Collects **every `<p>` paragraph** inside the container.
- **Excludes** paragraphs that have an ancestor matching any configured rule. The default rule matches the class `interactive-body` — NYT interactive articles wrap embeddable widgets (sliders, quizzes, charts) in such a container, so their text is widget UI, not article prose. Rules are a list of dicts that can match by `tag`, `class`, or any other attribute (e.g. `name`); by default only `class` is matched (`name`/`id` are ignored).
- This naturally drops images, sidebars, links, scripts — only paragraph text is kept.
- Each line is stripped of surrounding whitespace.

### Noise filtering

Noise matching uses **`fnmatch` wildcards** (case-insensitive), so one pattern can match many variants:

```python
def matches_noise_pattern(line):
    lowered = line.strip().lower()
    return any(fnmatch.fnmatchcase(lowered, pattern) for pattern in config.NOISE_PATTERNS)

cleaned_lines = [line for line in content_lines
                 if line and not matches_noise_pattern(line)]
```

- Drops **empty lines**.
- Drops lines that match any `config.NOISE_PATTERNS` pattern (case-insensitive).
- Patterns support `*` (any run of characters) and `?` (a single character):

```
advertisement*, subscribe to*, sign up*, get our free*, daily newsletter*,
follow us*, share this article*, read more*, continue reading*, log in*,
register*, members-only*, articles left*,
subscribe to the times to read as many articles as you like.*
```

> ⚠️ **Matching semantics:** wildcards match against the **whole line** (shell-glob style), not a substring anywhere inside it. `"subscribe to*"` matches `"Subscribe to our daily newsletter."` but does **not** match `"Readers can subscribe to our newsletter."`. To match a phrase anywhere in a line, put `*` on both sides, e.g. `"*sign up*"`.

If nothing survives the filter → raises `RuntimeError("Article body is empty")`.

### Output

```python
return "\n".join(cleaned_lines)
```

All surviving paragraphs are joined with newlines into a single string.

---

## Stage 3: Storage

In `process_source_json()`:

```python
content = extract_article(url)
mark_extracted(conn, article_id, content)
```

- The extracted text is stored in the **SQLite database** via `mark_extracted()`.
- The old `article_path.write_text(...)` file-writing line is **commented out** — files are no longer written to disk.

---

## Pipeline flow (per document)

```mermaid
flowchart TD
    A[JSON archive: response.docs] --> B{Skip filters?}
    B -- yes (section/subsection/material/news_desk) --> C[continue to next doc]
    B -- no --> D[upsert_metadata]
    D --> E{Already extracted? is_extracted / has_extracted_text}
    E -- yes --> F[SKIP]
    E -- no --> G[extract_article: Selenium + anti-detect]
    G --> H[clean_article_text: pick container, grab <p>, filter noise]
    H --> I[mark_extracted into SQLite]
    G -- RuntimeError swallowed --> J[returns None, mark_extracted(None)]
```

### Skip filters (pre-extraction)

Documents are skipped when any of these hold:

- `section_name` in `SECTION_NAMES` (`Gameplay`, `Corrections`, `Style`, `T Magazine`)
- `subsection_name` in `SUBSECTIONS` (`Book Review`)
- `document_type != "Article"`
- `type_of_material` in `MATERIEL_TYPES` (`Review`, `Correction`, `Quote`, `Live Blog Post`)
- `news_desk` in `NEWS_DESKS` (`TStyle`, `Projects and Initiatives`, `Podcasts`, `Games`, `BookReview`)

---

## Known caveats / edge cases

1. **Failed extraction returns `None`.** In `extract_article()`, a `RuntimeError` from `clean_article_text()` is silently swallowed (`except RuntimeError: pass`), so the function returns `None`. `process_source_json()` then calls `mark_extracted(conn, article_id, None)` instead of raising — failed extractions get stored as `NULL` content rather than being marked failed. This may be intentional, but it is worth confirming.
2. **Noise wildcards are whole-line globs** — a pattern matches the entire line (shell-style), not a substring. Add leading/trailing `*` as needed (e.g. `"*subscribe*"`) to match a phrase mid-line.
3. **Selector order is fixed** — if a page's `section[name=articleBody]` exists but is empty/stubbed, the extractor still uses it and never falls through to `meteredContent`/`main`/`article`.
4. **Random sleeps slow throughput** — each article takes ~10–16s minimum (7–11s render + 2–5s teardown), which is deliberate to avoid bot detection.
5. **`interactive-body` exclusion is class-only and ancestry-based** — a `<p>` is skipped if *any* ancestor has the class `interactive-body` (`name`/`id` are ignored). If an interactive widget is nested deeper than a direct child of the container, it is still caught, since the whole ancestor chain is walked.
