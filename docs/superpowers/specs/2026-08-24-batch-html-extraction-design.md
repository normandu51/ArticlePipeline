# Batch HTML Extraction Design

## Goal

Update `ExtractHTML.py` to process a source JSON archive containing articles under `response.docs`, extract each article from its `web_url`, and save each result separately.

## Behavior

- Accept the source JSON path as one positional command-line argument.
- Create `nyt_output/<source-json-stem>/` for the results.
- Save each valid article as `<_id>.txt`.
- Use the existing Selenium and BeautifulSoup extraction flow for each URL.
- Detect blocked pages and treat them as article failures.
- Continue processing after an individual article failure.
- Always close Selenium drivers with `driver.quit()`.

## Logging

Write `nyt_output/<source-json-stem>/process.log` in append mode. Include a timestamp, level, article ID, URL, and outcome for every document:

- `SUCCESS` after the article text is written.
- `ERROR` with the exception message for extraction or file failures.
- `ERROR` for documents missing `_id` or `web_url`.

## Testing

Add focused tests for output-directory and article-file naming, JSON document iteration, text cleaning, and failure logging. Tests should not launch Chrome.