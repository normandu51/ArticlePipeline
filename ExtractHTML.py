"""Extract clean article text from NYT archive pages.

All tunable values — extraction filters, noise patterns, body selectors,
ancestor-exclusion rules and driver/network settings — live in
``extract_config.py``. This module only contains the generic pipeline.
"""

import argparse
import fnmatch
import json
import logging
import os
import random
import time
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

import extract_config as config
from article_store import (
    DEFAULT_DB_PATH,
    get_connection,
    has_extracted_text,
    init_db,
    is_extracted,
    mark_extracted,
    mark_failed,
    upsert_metadata,
)
from block_detection import is_block_page


def find_chrome_binary():
    """Find Chrome/Chromium binary among the configured locations."""
    for path in config.CHROME_BINARY_PATHS:
        if os.path.exists(path):
            return path
    return None


def find_chromedriver():
    """Find ChromeDriver among the configured locations."""
    for path in config.CHROMEDRIVER_PATHS:
        if os.path.exists(path):
            return path
    return None


def get_chrome_profile_dir():
    """Return the persistent Chrome profile directory.

    The environment variable ``CHROME_PROFILE_ENV_VAR`` takes precedence over
    the config default, so operators can override the profile per run.
    """
    return os.environ.get(
        config.CHROME_PROFILE_ENV_VAR, config.DEFAULT_CHROME_PROFILE_DIR
    )


def build_chrome_options(chrome_binary):
    options = Options()
    options.binary_location = chrome_binary
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(f"user-agent={config.USER_AGENT}")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--window-size={config.WINDOW_SIZE}")
    options.add_argument(f"--user-data-dir={get_chrome_profile_dir()}")
    return options


def create_driver():
    chrome_binary = find_chrome_binary()
    if not chrome_binary:
        raise RuntimeError("Chrome/Chromium not found")

    chrome_options = build_chrome_options(chrome_binary)
    chromedriver_path = find_chromedriver()
    if chromedriver_path:
        return webdriver.Chrome(
            service=Service(chromedriver_path), options=chrome_options
        )
    return webdriver.Chrome(options=chrome_options)


def matches_noise_pattern(line):
    """Return True if `line` matches any configured NOISE_PATTERNS wildcard.

    Matching is case-insensitive and supports fnmatch wildcards
    ('*' matches any run of characters, '?' matches a single character).
    """
    lowered = line.strip().lower()
    return any(
        fnmatch.fnmatchcase(lowered, pattern) for pattern in config.NOISE_PATTERNS
    )


def _matches_rule(element, rule):
    """Return True when `element` satisfies every filter in `rule`.

    A rule is a dict of attribute filters. ``tag`` compares the element name,
    ``class`` checks class-name membership, and any other key is compared by
    attribute value (e.g. ``name``).
    """
    for key, expected in rule.items():
        if key == "tag":
            if element.name != expected:
                return False
        elif key == "class":
            if expected not in (element.get("class") or []):
                return False
        else:
            if element.get(key) != expected:
                return False
    return True


def is_in_excluded_container(paragraph):
    """Return True if `paragraph` has an ancestor matching an exclusion rule.

    Exclusion rules come from ``config.EXCLUDED_ANCESTOR_RULES``. A paragraph
    is dropped when any of its ancestors satisfies all the filters of at least
    one rule — for example the default ``{'class': 'interactive-body'}``, which
    excludes widget UI from interactive articles. Only the class attribute is
    matched by default; ``name="interactive-body"`` is treated as prose.
    """
    for ancestor in paragraph.parents:
        if any(_matches_rule(ancestor, rule) for rule in config.EXCLUDED_ANCESTOR_RULES):
            return True
    return False


def clean_article_text(soup):
    article = None
    for tag, attrs in config.BODY_SELECTORS:
        article = soup.find(tag, attrs) if attrs else soup.find(tag)
        if article:
            break

    if not article:
        raise RuntimeError("Article body not found")

    content_lines = [
        paragraph.get_text().strip()
        for paragraph in article.find_all("p")
        if not is_in_excluded_container(paragraph)
    ]
    cleaned_lines = [
        line
        for line in content_lines
        if line and not matches_noise_pattern(line)
    ]
    if not cleaned_lines:
        raise RuntimeError("Article body is empty")
    return "\n".join(cleaned_lines)


def extract_article(url):
    driver = create_driver()
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', { get: () => false });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                """
            },
        )
        driver.get(url)
        time.sleep(random.uniform(*config.LOAD_SLEEP_RANGE))

        soup = BeautifulSoup(driver.page_source, "html.parser")
        try:
            return clean_article_text(soup)
        except RuntimeError as extraction_error:
            # Block detection is advisory: a false positive must not discard
            # content that was successfully extracted, so it only changes the
            # error message when extraction already failed.
            if is_block_page(soup):
                raise RuntimeError(f"Blocked page for {url}: {extraction_error}")
            raise RuntimeError(f"Failed to extract article {url}: {extraction_error}")
    finally:
        time.sleep(random.uniform(*config.QUIT_SLEEP_RANGE))
        driver.quit()


def output_directory(source_json):
    return Path("nyt_output").resolve() / Path(source_json).stem


def article_output_path(source_json, article_id):
    return output_directory(source_json) / f"{article_id}.txt"


def article_id_from_uri(article_uri):
    article_id = article_uri.rstrip("/").rsplit("/", 1)[-1]
    if not article_id:
        raise ValueError(f"Invalid article URI: {article_uri}")
    return article_id


def configure_logger(log_path):
    logger = logging.getLogger(f"ExtractHTML:{log_path}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def should_exclude_document(doc):
    """Return True when an archive doc should be skipped by the pipeline.

    A doc is excluded when it matches any configured filter: its
    ``document_type`` is not 'Article', or its section / subsection /
    type_of_material / news_desk is in the corresponding config list.
    """
    if doc.get("document_type") != "Article":
        return True
    if doc.get("section_name") in config.SECTION_NAMES:
        return True
    if doc.get("subsection_name") in config.SUBSECTIONS:
        return True
    if doc.get("type_of_material") in config.MATERIEL_TYPES:
        return True
    if doc.get("news_desk") in config.NEWS_DESKS:
        return True
    return False


def process_source_json(source_json, db_path=DEFAULT_DB_PATH):
    source_path = Path(source_json)
    month = source_path.stem
    destination = output_directory(source_path)
    destination.mkdir(parents=True, exist_ok=True)
    logger = configure_logger(destination / "process.log")
    conn = get_connection(db_path)
    try:
        init_db(conn)
        with source_path.open("r", encoding="utf-8") as input_file:
            documents = json.load(input_file)["response"]["docs"]

        for document in documents:
            if should_exclude_document(document):
                continue
            article_uri = document.get("_id")
            url = document.get("web_url")
            if not article_uri or not url:
                logger.error(
                    "ERROR article_id=%s url=%s missing _id or web_url",
                    article_uri,
                    url,
                )
                continue

            article_id = None
            try:
                article_id = article_id_from_uri(article_uri)
                upsert_metadata(conn, document, article_id, month)
                article_path = article_output_path(source_path, article_id)

                if is_extracted(conn, article_id) or has_extracted_text(
                    conn, article_id
                ):
                    logger.info("SKIP article_id=%s", article_id)
                    continue

                content = extract_article(url)
                # article_path.write_text(content + "\n", encoding="utf-8")
                mark_extracted(conn, article_id, content)
                logger.info(
                    "SUCCESS article_id=%s url=%s path=%s",
                    article_id,
                    url,
                    article_path,
                )
            except Exception as error:
                if article_id is not None:
                    mark_failed(conn, article_id, str(error))
                logger.error(
                    "ERROR article_id=%s url=%s message=%s",
                    article_id,
                    url,
                    error,
                )
    finally:
        conn.close()
        for handler in logger.handlers:
            handler.close()
            logger.removeHandler(handler)


def main():
    parser = argparse.ArgumentParser(
        description="Extract NYT articles from an archive JSON file"
    )
    parser.add_argument("source_json", help="Path to a JSON file containing response.docs")
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help=f"Path to the SQLite database (default: {DEFAULT_DB_PATH})",
    )
    args = parser.parse_args()
    process_source_json(args.source_json, db_path=args.db)


if __name__ == "__main__":
    main()
