import argparse
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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

from block_detection import is_block_page
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
SECTION_NAMES = ["Gameplay","Corrections","Style","T Magazine"]
MATERIEL_TYPES = ["Review", "Correction", "Quote", "Live Blog Post"]
NEWS_DESKS = ["TStyle","Projects and Initiatives","Podcasts","Games"]

NOISE_PATTERNS = {
    "advertisement",
    "subscribe to",
    "sign up",
    "get our free",
    "daily newsletter",
    "follow us",
    "share this article",
    "read more",
    "continue reading",
    "log in",
    "register",
    "members-only",
    "articles left",
    "subscribe to the times to read as many articles as you like.",
}


def find_chrome_binary():
    """Find Chrome/Chromium binary in common locations."""
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
    ]
    for path in chrome_paths:
        if os.path.exists(path):
            return path
    return None


def find_chromedriver():
    """Find ChromeDriver in common locations."""
    driver_paths = [
        "/usr/local/bin/chromedriver",
        "/opt/homebrew/bin/chromedriver",
        str(Path.home() / ".wdm" / "chromedriver"),
        "./chromedriver",
    ]
    for path in driver_paths:
        if os.path.exists(path):
            return path
    return None


def build_chrome_options(chrome_binary):
    options = Options()
    options.binary_location = chrome_binary
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
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


def clean_article_text(soup):
    selectors = [
        ("section", {"name": "articleBody"}),
        ("section", {"class": "meteredContent"}),
        ("main", None),
        ("article", None),
    ]
    article = None
    for tag, attrs in selectors:
        article = soup.find(tag, attrs) if attrs else soup.find(tag)
        if article:
            break

    if not article:
        raise RuntimeError("Article body not found")

    content_lines = [paragraph.get_text().strip() for paragraph in article.find_all("p")]
    cleaned_lines = [
        line
        for line in content_lines
        if line and line.lower() not in NOISE_PATTERNS
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
        time.sleep(random.uniform(7, 11))

        soup = BeautifulSoup(driver.page_source, "html.parser")
        try:
            return clean_article_text(soup)
        except RuntimeError as extraction_error:
            pass
    finally:
        time.sleep(random.uniform(2, 5))
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
            if (document.get("section_name") in SECTION_NAMES or document.get("document_type")!="Article") or document.get("type_of_material") in MATERIEL_TYPES or document.get("news_desk") in NEWS_DESKS:
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
