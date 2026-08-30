"""Download article image variants from NYT archive metadata.

Kept in its own module so the extraction pipeline in ``ExtractHTML.py`` stays
focused on text. All tunable values (image fields, timeout, user agent) live in
``extract_config.py``.
"""

import shutil
import urllib.request
from pathlib import Path

import extract_config as config
from PipelineConfig import DEFAULT_IMAGE_DIR, REPO_ROOT


def images_directory(month):
    """Return the per-month image output directory (REPO_ROOT/DEFAULT_IMAGE_DIR/<month>)."""
    return (Path(REPO_ROOT) / DEFAULT_IMAGE_DIR).resolve() / month


def image_output_path(month, article_id, field):
    """Return the destination path for one image variant of an article.

    Files are named ``<article_id>_<field>.jpg``, e.g.
    ``61b49ae0-9e37-5b3c-b04a-d8a92d951a02_jumbo.jpg``, under
    ``nyt_output/images/<month>/``.
    """
    return images_directory(month) / f"{article_id}_{field}.jpg"


def _download_image(url, destination):
    """Download `url` into `destination`, creating parent directories as needed."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
    with urllib.request.urlopen(
        request, timeout=config.IMAGE_DOWNLOAD_TIMEOUT
    ) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)


def download_images(doc, month, article_id, logger):
    """Download every image variant of an archive doc to nyt_output/images/<month>/.

    One file per ``config.IMAGE_FIELDS`` entry that has a URL, named
    ``<article_id>_<field>.jpg``. Files that already exist (non-empty) are
    skipped, so the download is idempotent and resume-safe. Returns a
    ``(downloaded, skipped, failed)`` tuple; individual failures are logged via
    `logger`.
    """
    multimedia = doc.get("multimedia") or {}
    downloaded = skipped = failed = 0
    for field in config.IMAGE_FIELDS:
        url = (multimedia.get(field) or {}).get("url")
        if not url:
            continue
        destination = image_output_path(month, article_id, field)
        if destination.exists() and destination.stat().st_size > 0:
            skipped += 1
            continue
        try:
            _download_image(url, destination)
            downloaded += 1
        except Exception as error:
            failed += 1
            logger.error(
                "IMAGE_ERROR article_id=%s field=%s url=%s message=%s",
                article_id,
                field,
                url,
                error,
            )
    return downloaded, skipped, failed
