from bs4 import BeautifulSoup

from block_detection import is_block_page
from ExtractHTML import (
    article_id_from_uri,
    article_output_path,
    clean_article_text,
    extract_article,
    output_directory,
    process_source_json,
)


def test_article_words_do_not_trigger_block_detection():
    soup = BeautifulSoup(
        """
        <html>
            <body>
                <article>
                    <p>The robot was suspended from the experiment.</p>
                    <p>The article continues with additional reporting.</p>
                </article>
            </body>
        </html>
        """,
        "html.parser",
    )

    assert is_block_page(soup) is False


def test_access_denied_page_triggers_block_detection():
    soup = BeautifulSoup(
        "<html><head><title>Access Denied</title></head><body>Request denied.</body></html>",
        "html.parser",
    )

    assert is_block_page(soup) is True


def test_clean_article_text_removes_noise_lines():
    soup = BeautifulSoup(
        """
        <article>
            <p>First paragraph.</p>
            <p>Advertisement</p>
            <p>Second paragraph.</p>
            <p>Subscribe to The Times to read as many articles as you like.</p>
        </article>
        """,
        "html.parser",
    )

    assert clean_article_text(soup) == "First paragraph.\nSecond paragraph."


def test_extract_article_accepts_content_when_block_detector_is_false_positive(monkeypatch):
    class FakeDriver:
        page_source = "<article><p>Valid article content.</p></article>"

        def execute_cdp_cmd(self, *_args):
            pass

        def get(self, _url):
            pass

        def find_element(self, *_selector):
            raise LookupError("no slider")

        def quit(self):
            self.closed = True

    driver = FakeDriver()
    monkeypatch.setattr("ExtractHTML.create_driver", lambda: driver)
    monkeypatch.setattr("ExtractHTML.is_block_page", lambda _soup: True)
    monkeypatch.setattr("ExtractHTML.time.sleep", lambda _seconds: None)

    assert extract_article("https://example.test/article") == "Valid article content."
    assert driver.closed is True


def test_article_output_path_uses_source_stem_and_article_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source_json = tmp_path / "2025_10.json"

    assert output_directory(source_json) == tmp_path / "nyt_output" / "2025_10"
    assert article_output_path(source_json, "article-123") == (
        tmp_path / "nyt_output" / "2025_10" / "article-123.txt"
    )


def test_article_id_from_uri_returns_last_path_segment():
    assert article_id_from_uri("nyt://article/2090e468-8163-5f8b-aeef-dba7950df018") == (
        "2090e468-8163-5f8b-aeef-dba7950df018"
    )


def test_process_source_json_writes_articles_and_logs_failures(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source_json = tmp_path / "2025_10.json"
    source_json.write_text(
        '{"response": {"docs": ['
        '{"_id": "first", "document_type": "Article", "web_url": "https://example.test/first"},'
        '{"_id": "second", "document_type": "Article", "web_url": "https://example.test/second"},'
        '{"_id": "invalid", "document_type": "Article"}'
        ']}}',
        encoding="utf-8",
    )

    def fake_extract(url):
        if url.endswith("second"):
            raise RuntimeError("blocked")
        return "First article"

    monkeypatch.setattr("ExtractHTML.extract_article", fake_extract)
    process_source_json(source_json)

    output_dir = tmp_path / "nyt_output" / "2025_10"
    assert (output_dir / "first.txt").read_text(encoding="utf-8") == "First article\n"
    log = (output_dir / "process.log").read_text(encoding="utf-8")
    assert "SUCCESS article_id=first" in log
    assert "ERROR article_id=second" in log
    assert "blocked" in log
    assert "ERROR article_id=invalid" in log


def test_process_source_json_skips_article_with_existing_text_in_db(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    source_json = tmp_path / "2025_10.json"
    source_json.write_text(
        '{"response": {"docs": [{"_id": "nyt://article/hastext", '
        '"document_type": "Article", "web_url": "https://example.test/hastext"}]}}',
        encoding="utf-8",
    )

    from article_store import get_connection, init_db, upsert_metadata

    conn = get_connection("articles.db")
    init_db(conn)
    upsert_metadata(
        conn,
        {"_id": "nyt://article/hastext", "web_url": "https://example.test/hastext"},
        "hastext",
        "2025_10",
    )
    # Legacy row: has extracted text but a non-processed status.
    conn.execute(
        "UPDATE articles SET extracted_text = 'Existing text' "
        "WHERE id = 'hastext'"
    )
    conn.commit()
    conn.close()

    def unexpected_extract(_url):
        raise AssertionError("articles with extracted text should not be extracted")

    monkeypatch.setattr("ExtractHTML.extract_article", unexpected_extract)
    process_source_json(source_json)

    log = (tmp_path / "nyt_output" / "2025_10" / "process.log").read_text(
        encoding="utf-8"
    )
    assert "SKIP article_id=hastext" in log


def test_process_source_json_skips_article_already_in_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source_json = tmp_path / "2025_10.json"
    source_json.write_text(
        '{"response": {"docs": [{"_id": "nyt://article/dbid", '
        '"document_type": "Article", "web_url": "https://example.test/dbid"}]}}',
        encoding="utf-8",
    )

    from article_store import get_connection, init_db, mark_extracted, upsert_metadata

    conn = get_connection("articles.db")
    init_db(conn)
    upsert_metadata(
        conn,
        {"_id": "nyt://article/dbid", "web_url": "https://example.test/dbid"},
        "dbid",
        "2025_10",
    )
    mark_extracted(conn, "dbid", "Already in db")
    conn.close()

    def unexpected_extract(_url):
        raise AssertionError("articles already in DB should not be extracted")

    monkeypatch.setattr("ExtractHTML.extract_article", unexpected_extract)
    process_source_json(source_json)

    log = (tmp_path / "nyt_output" / "2025_10" / "process.log").read_text(
        encoding="utf-8"
    )
    assert "SKIP article_id=dbid" in log