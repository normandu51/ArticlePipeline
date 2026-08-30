import pytest
from bs4 import BeautifulSoup

import ArticleExtraction.extract_config as config
from ArticleExtraction.block_detection import is_block_page
from ArticleExtraction.ExtractHTML import (
    article_id_from_uri,
    article_output_path,
    build_chrome_options,
    clean_article_text,
    extract_article,
    get_chrome_profile_dir,
    is_in_excluded_container,
    matches_noise_pattern,
    output_directory,
    process_source_json,
    should_exclude_document,
)


def test_build_chrome_options_uses_persistent_profile(monkeypatch):
    from selenium.webdriver.chrome.options import Options

    monkeypatch.setenv("NYT_CHROME_PROFILE_DIR", "/tmp/nyt-profile")
    options = build_chrome_options(
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    )

    assert isinstance(options, Options)
    assert any(
        "--user-data-dir=/tmp/nyt-profile" in arg for arg in options.arguments
    )


def test_get_chrome_profile_dir_defaults_to_config_default(monkeypatch):
    from ArticleExtraction.extract_config import DEFAULT_CHROME_PROFILE_DIR

    monkeypatch.delenv(config.CHROME_PROFILE_ENV_VAR, raising=False)
    assert get_chrome_profile_dir() == DEFAULT_CHROME_PROFILE_DIR


def test_get_chrome_profile_dir_prefers_env_var(monkeypatch):
    monkeypatch.setenv(config.CHROME_PROFILE_ENV_VAR, "/tmp/nyt-profile")
    assert get_chrome_profile_dir() == "/tmp/nyt-profile"


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


def test_clean_article_text_removes_noise_lines_with_wildcards():
    soup = BeautifulSoup(
        """
        <article>
            <p>First paragraph.</p>
            <p>Subscribe to The Times today!</p>
            <p>Subscribe to The Times to read as many articles as you like.</p>
            <p>Advertisement</p>
            <p>Second paragraph.</p>
        </article>
        """,
        "html.parser",
    )

    assert clean_article_text(soup) == "First paragraph.\nSecond paragraph."


def test_clean_article_text_keeps_lines_that_only_contain_noise_words():
    soup = BeautifulSoup(
        """
        <article>
            <p>Readers can read more about this topic in our guide.</p>
            <p>The article discusses the follow us phenomenon.</p>
        </article>
        """,
        "html.parser",
    )

    assert clean_article_text(soup) == (
        "Readers can read more about this topic in our guide.\n"
        "The article discusses the follow us phenomenon."
    )


def test_clean_article_text_keeps_paragraphs_under_name_interactive_body():
    soup = BeautifulSoup(
        """
        <article>
            <p>First paragraph.</p>
            <section name="interactive-body">
                <p>Drag the slider to compare.</p>
                <p>Quiz question one.</p>
            </section>
            <p>Second paragraph.</p>
        </article>
        """,
        "html.parser",
    )

    # Only the class attribute triggers exclusion; name="interactive-body" is kept.
    assert clean_article_text(soup) == (
        "First paragraph.\n"
        "Drag the slider to compare.\n"
        "Quiz question one.\n"
        "Second paragraph."
    )


def test_clean_article_text_excludes_paragraphs_under_class_interactive_body():
    soup = BeautifulSoup(
        """
        <article>
            <p>First paragraph.</p>
            <div class="interactive-body">
                <p>Click to see the chart.</p>
            </div>
            <p>Second paragraph.</p>
        </article>
        """,
        "html.parser",
    )

    assert clean_article_text(soup) == "First paragraph.\nSecond paragraph."


def test_clean_article_text_excludes_paragraphs_without_words():
    soup = BeautifulSoup(
        """
        <article>
            <p>First paragraph.</p>
            <p>   </p>
            <p>—</p>
            <p>12345</p>
            <p>·</p>
            <p>Second paragraph.</p>
        </article>
        """,
        "html.parser",
    )

    assert clean_article_text(soup) == "First paragraph.\nSecond paragraph."


def test_clean_article_text_keeps_paragraphs_with_accented_words():
    soup = BeautifulSoup(
        """
        <article>
            <p>First paragraph.</p>
            <p>José visited São Paulo.</p>
            <p>Second paragraph.</p>
        </article>
        """,
        "html.parser",
    )

    assert clean_article_text(soup) == (
        "First paragraph.\nJosé visited São Paulo.\nSecond paragraph."
    )


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


def test_process_source_json_marks_success_and_failure_in_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source_json = tmp_path / "2025_10.json"
    source_json.write_text(
        '{"response": {"docs": ['
        '{"_id": "nyt://article/first", "document_type": "Article", '
        '"web_url": "https://example.test/first"},'
        '{"_id": "nyt://article/second", "document_type": "Article", '
        '"web_url": "https://example.test/second"},'
        '{"_id": "nyt://article/invalid", "document_type": "Article"}'
        ']}}',
        encoding="utf-8",
    )

    def fake_extract(url):
        if url.endswith("second"):
            raise RuntimeError("blocked")
        return "First article"

    monkeypatch.setattr("ExtractHTML.extract_article", fake_extract)
    process_source_json(source_json)

    from ArticleExtraction.article_store import get_connection

    conn = get_connection("articles.db")
    first = conn.execute("SELECT * FROM articles WHERE id = 'first'").fetchone()
    second = conn.execute("SELECT * FROM articles WHERE id = 'second'").fetchone()
    invalid = conn.execute("SELECT * FROM articles WHERE id = 'invalid'").fetchone()
    conn.close()

    assert first["status"] == "extracted"
    assert first["extracted_text"] == "First article"
    assert second["status"] == "failed"
    assert "blocked" in second["error"]
    # A doc without web_url is logged but never inserted.
    assert invalid is None

    log = (tmp_path / "nyt_output" / "2025_10" / "process.log").read_text(
        encoding="utf-8"
    )
    assert "SUCCESS article_id=first" in log
    assert "ERROR article_id=second" in log
    assert "blocked" in log
    assert "missing _id or web_url" in log


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

    from ArticleExtraction.article_store import get_connection, init_db, upsert_metadata

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

    from ArticleExtraction.article_store import get_connection, init_db, mark_extracted, upsert_metadata

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


def test_should_exclude_document_keeps_plain_article():
    doc = {
        "document_type": "Article",
        "section_name": "U.S.",
        "subsection_name": "Politics",
        "type_of_material": "News",
        "news_desk": "National",
    }
    assert should_exclude_document(doc) is False


def test_should_exclude_document_filters_non_article_types():
    assert should_exclude_document({"document_type": "Blog"}) is True
    assert should_exclude_document({"document_type": None}) is True


def test_should_exclude_document_filters_by_section():
    doc = {"document_type": "Article", "section_name": "T Magazine"}
    assert should_exclude_document(doc) is True


def test_should_exclude_document_filters_by_subsection():
    doc = {"document_type": "Article", "subsection_name": "Book Review"}
    assert should_exclude_document(doc) is True


def test_should_exclude_document_filters_by_material_type():
    doc = {"document_type": "Article", "type_of_material": "Review"}
    assert should_exclude_document(doc) is True


def test_should_exclude_document_filters_by_news_desk():
    doc = {"document_type": "Article", "news_desk": "Games"}
    assert should_exclude_document(doc) is True


def test_matches_noise_pattern_matches_configured_patterns():
    assert matches_noise_pattern("Advertisement") is True
    assert matches_noise_pattern("Subscribe to The Times today!") is True
    assert matches_noise_pattern("The article discusses follow us.") is False


def test_is_in_excluded_container_matches_default_class_rule():
    soup = BeautifulSoup(
        '<article><div class="interactive-body"><p>widget</p></div></article>',
        "html.parser",
    )
    assert is_in_excluded_container(soup.find("p")) is True


def test_is_in_excluded_container_keeps_name_attribute_by_default():
    soup = BeautifulSoup(
        '<article><section name="interactive-body"><p>text</p></section></article>',
        "html.parser",
    )
    assert is_in_excluded_container(soup.find("p")) is False


def test_is_in_excluded_container_configurable_tag_rule(monkeypatch):
    monkeypatch.setattr(config, "EXCLUDED_ANCESTOR_RULES", [{"tag": "aside"}])
    soup = BeautifulSoup(
        "<article><aside><p>widget</p></aside></article>", "html.parser"
    )
    assert is_in_excluded_container(soup.find("p")) is True


def test_is_in_excluded_container_configurable_name_rule(monkeypatch):
    monkeypatch.setattr(config, "EXCLUDED_ANCESTOR_RULES", [{"name": "widget"}])
    soup = BeautifulSoup(
        '<article><div name="widget"><p>widget</p></div></article>', "html.parser"
    )
    assert is_in_excluded_container(soup.find("p")) is True


def test_clean_article_text_uses_config_body_selectors(monkeypatch):
    monkeypatch.setattr(config, "BODY_SELECTORS", [("main", None)])
    soup = BeautifulSoup(
        "<main><p>Body paragraph.</p></main>"
        "<article><p>Ignored article.</p></article>",
        "html.parser",
    )
    assert clean_article_text(soup) == "Body paragraph."


def test_clean_article_text_raises_when_no_configured_selector_matches(monkeypatch):
    monkeypatch.setattr(config, "BODY_SELECTORS", [("main", None)])
    soup = BeautifulSoup("<article><p>No main here.</p></article>", "html.parser")
    with pytest.raises(RuntimeError):
        clean_article_text(soup)