"""Tests for src/google_images.py."""

from unittest.mock import MagicMock

import pytest
import responses as resp_lib

from src.google_images import (
    fetch_cover_image,
    _open_library_cover,
    _google_image,
    _OPEN_LIBRARY_URL,
    _GOOGLE_CSE_URL,
    _MIN_COVER_BYTES,
)


# ── Fixtures ──────────────────────────────────────────────────────────


def _config(google_enabled=False, api_key="KEY", cx="CX"):
    cfg = MagicMock()
    cfg.google_enabled = google_enabled
    cfg.google_api_key = api_key
    cfg.google_cx = cx
    return cfg


# ── Open Library ─────────────────────────────────────────────────────


class TestOpenLibraryCover:
    @resp_lib.activate
    def test_returns_url_when_image_exists(self):
        url = _OPEN_LIBRARY_URL.format(isbn="9781234567890")
        resp_lib.add(
            resp_lib.HEAD, url,
            headers={"content-length": str(_MIN_COVER_BYTES + 100)},
            status=200,
        )
        result = _open_library_cover("9781234567890")
        assert result == url

    @resp_lib.activate
    def test_returns_none_for_placeholder_image(self):
        url = _OPEN_LIBRARY_URL.format(isbn="0000000000")
        resp_lib.add(
            resp_lib.HEAD, url,
            headers={"content-length": "807"},  # < _MIN_COVER_BYTES
            status=200,
        )
        result = _open_library_cover("0000000000")
        assert result is None

    @resp_lib.activate
    def test_returns_none_on_http_error(self):
        url = _OPEN_LIBRARY_URL.format(isbn="9999999999999")
        resp_lib.add(resp_lib.HEAD, url, status=404)
        result = _open_library_cover("9999999999999")
        assert result is None

    @resp_lib.activate
    def test_strips_hyphens_from_isbn(self):
        clean = "9781234567890"
        url = _OPEN_LIBRARY_URL.format(isbn=clean)
        resp_lib.add(
            resp_lib.HEAD, url,
            headers={"content-length": str(_MIN_COVER_BYTES + 1)},
            status=200,
        )
        result = _open_library_cover("978-1-234-56789-0")
        assert result is not None


# ── Google Custom Search ──────────────────────────────────────────────


class TestGoogleImage:
    @resp_lib.activate
    def test_returns_first_image_link(self):
        resp_lib.add(
            resp_lib.GET, _GOOGLE_CSE_URL,
            json={"items": [{"link": "https://example.com/cover.jpg"}]},
            status=200,
        )
        result = _google_image("Some Title author", "API_KEY", "CX")
        assert result == "https://example.com/cover.jpg"

    @resp_lib.activate
    def test_returns_none_when_no_items(self):
        resp_lib.add(
            resp_lib.GET, _GOOGLE_CSE_URL,
            json={"items": []},
            status=200,
        )
        result = _google_image("No Cover Book", "API_KEY", "CX")
        assert result is None

    @resp_lib.activate
    def test_returns_none_on_api_error(self):
        resp_lib.add(resp_lib.GET, _GOOGLE_CSE_URL, status=403)
        result = _google_image("Title", "BADKEY", "CX")
        assert result is None


# ── Orchestration ─────────────────────────────────────────────────────


class TestFetchCoverImage:
    @resp_lib.activate
    def test_open_library_used_when_isbn_available(self):
        isbn = "9781234567890"
        url = _OPEN_LIBRARY_URL.format(isbn=isbn)
        resp_lib.add(
            resp_lib.HEAD, url,
            headers={"content-length": str(_MIN_COVER_BYTES + 100)},
            status=200,
        )
        result = fetch_cover_image("Title", "Author", isbn, _config())
        assert result == url

    @resp_lib.activate
    def test_google_fallback_when_no_isbn(self):
        resp_lib.add(
            resp_lib.GET, _GOOGLE_CSE_URL,
            json={"items": [{"link": "https://example.com/img.jpg"}]},
            status=200,
        )
        result = fetch_cover_image("Title", "Author", None, _config(google_enabled=True))
        assert result == "https://example.com/img.jpg"

    def test_returns_none_when_nothing_configured(self):
        result = fetch_cover_image("Title", "Author", None, _config(google_enabled=False))
        assert result is None
