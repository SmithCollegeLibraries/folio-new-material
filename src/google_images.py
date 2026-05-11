"""Cover-image lookup via Open Library (free) and Google Custom Search (optional)."""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_OPEN_LIBRARY_URL = "https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
_GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"

# Open Library returns a 1×1 white GIF for missing covers; anything under 1 KB
# is treated as a placeholder and skipped.
_MIN_COVER_BYTES = 1024


def fetch_cover_image(
    title: str,
    author: str,
    isbn: Optional[str],
    config,
) -> Optional[str]:
    """
    Return a URL for a cover image, or None if one cannot be found.

    Strategy:
      1. If an ISBN is available, check Open Library (free, no key required).
      2. If Google is configured, fall back to a Google Custom Search query.
    """
    if isbn:
        url = _open_library_cover(isbn)
        if url:
            return url

    if config.google_enabled:
        query = f"{title} {author} book cover".strip()
        return _google_image(query, config.google_api_key, config.google_cx)

    return None


def _open_library_cover(isbn: str) -> Optional[str]:
    """Return the Open Library cover URL if a real image exists for this ISBN."""
    clean = isbn.replace("-", "").replace(" ", "")
    url = _OPEN_LIBRARY_URL.format(isbn=clean)
    try:
        resp = requests.head(url, timeout=5, allow_redirects=True)
        content_length = int(resp.headers.get("content-length", 0))
        if resp.ok and content_length >= _MIN_COVER_BYTES:
            return url
    except requests.RequestException as exc:
        logger.debug("Open Library check failed for ISBN %s: %s", isbn, exc)
    return None


def _google_image(query: str, api_key: str, cx: str) -> Optional[str]:
    """Return the first image URL from Google Custom Search, or None."""
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "searchType": "image",
        "num": 1,
        "safe": "active",
    }
    try:
        resp = requests.get(_GOOGLE_CSE_URL, params=params, timeout=10)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if items:
            return items[0].get("link")
    except requests.RequestException as exc:
        logger.warning("Google image search failed for '%s': %s", query, exc)
    return None
