from bs4 import BeautifulSoup


def is_block_page(soup: BeautifulSoup) -> bool:
    """Return whether a page has strong evidence of being a block response."""
    page_text = soup.get_text(" ", strip=True).lower()
    title = soup.title.get_text(" ", strip=True).lower() if soup.title else ""

    challenge_selectors = (
        "[id*='captcha']",
        "[class*='captcha']",
        "[id*='challenge']",
        "[class*='challenge']",
        "iframe[src*='captcha']",
    )
    if any(soup.select_one(selector) for selector in challenge_selectors):
        return True

    title_markers = (
        "access denied",
        "request denied",
        "unusual traffic",
        "security check",
        "verify you are human",
        "automated access",
        "temporarily blocked",
    )
    if any(marker in title for marker in title_markers):
        return True

    article = (
        soup.find("section", {"name": "articleBody"})
        or soup.find("section", {"class": "meteredContent"})
        or soup.find("article")
    )
    has_article_content = bool(article and article.find("p"))

    body_markers = title_markers + ("captcha", "robot", "suspended")
    return not has_article_content and any(marker in page_text for marker in body_markers)
