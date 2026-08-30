"""Configuration for the NYT article extraction pipeline.

Edit values here to tune filtering, cleaning and driver behaviour without
touching code in ``ExtractHTML.py``. This module is data-only; it contains no
pipeline logic.

Supported naming conventions:

* ``NOISE_PATTERNS`` uses fnmatch wildcards — ``*`` matches any run of
  characters, ``?`` matches a single character. Matching is case-insensitive.
* ``BODY_SELECTORS`` is an ordered list of ``(tag_name, attrs_or_None)``; the
  first tag found in the page wins.
* ``EXCLUDED_ANCESTOR_RULES`` is a list of dicts. Each dict is a set of
  attribute filters that must ALL match on a single ancestor element before its
  contained paragraphs are dropped. Supported keys: ``tag`` (element name),
  ``class`` (class-name membership) and any other attribute by name (e.g.
  ``name``).
"""

from pathlib import Path

# --- Driver / network settings ---------------------------------------------

# Candidate locations for the Chrome/Chromium binary (first match wins).
CHROME_BINARY_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/chromium-browser",
    "/snap/bin/chromium",
]

# Candidate locations for ChromeDriver (first match wins).
CHROMEDRIVER_PATHS = [
    "/usr/local/bin/chromedriver",
    "/opt/homebrew/bin/chromedriver",
    str(Path.home() / ".wdm" / "chromedriver"),
    "./chromedriver",
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

WINDOW_SIZE = "1920,1080"

# Randomised delays (seconds) used to look like a human reader.
LOAD_SLEEP_RANGE = (7, 11)  # after page load
QUIT_SLEEP_RANGE = (2, 5)   # before closing the driver

# Persistent Chrome profile. The environment variable takes precedence over the
# default when both are set.
CHROME_PROFILE_ENV_VAR = "NYT_CHROME_PROFILE_DIR"
DEFAULT_CHROME_PROFILE_DIR = str(Path(__file__).resolve().parent / ".chrome_profile")

# --- Article exclusion filters (archive metadata) ---------------------------

# Documents matching any of these are skipped by the pipeline.
SECTION_NAMES = ["Gameplay", "Corrections", "Style", "T Magazine"]
SUBSECTIONS = ["Book Review"]
MATERIEL_TYPES = ["Review", "Correction", "Quote", "Live Blog Post", "Letter"]
NEWS_DESKS = ["TStyle", "Projects and Initiatives", "Podcasts", "Games", "BookReview"]

# --- Body text cleaning -----------------------------------------------------

# Lines matching any of these fnmatch wildcard patterns are dropped.
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
    "subscribe to the times*",
}

# Ordered candidates for locating the article body.
BODY_SELECTORS = [
    ("section", {"name": "articleBody"}),
    ("section", {"class": "meteredContent"}),
    ("main", None),
    ("article", None),
]

# Ancestor exclusion rules for body paragraphs. Paragraphs inside a matching
# ancestor (e.g. interactive widgets) are treated as UI, not article prose.
EXCLUDED_ANCESTOR_RULES = [
    {"class": "interactive-body"},
]
