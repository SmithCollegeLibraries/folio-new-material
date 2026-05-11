"""Tests for src/config_loader.py."""

import configparser
import textwrap
from pathlib import Path

import pytest

from src.config_loader import Config, ConfigError


# ── Fixtures ─────────────────────────────────────────────────────────


def _write_config(tmp_path: Path, content: str) -> str:
    """Write an INI string to a temp file and return its path."""
    p = tmp_path / "config.ini"
    p.write_text(textwrap.dedent(content))
    return str(p)


MINIMAL_CONFIG = """
    [folio]
    base_url = https://api.example.com
    username = testuser
    password = testpass
"""

FULL_CONFIG = """
    [folio]
    base_url    = https://api.example.com
    tenant      = mytenant
    username    = testuser
    password    = testpass
    edge_api    = https://edge.example.com/

    [eds]
    db_id       = abcdef
    catalog_db  = cat12345
    an_prefix   = scf.oai.edge.example.com.tenant01
    an_separator = dots

    [google]
    api_key = GOOGLE_KEY
    cx      = GOOGLE_CX

    [output]
    days            = 14
    output_file     = /tmp/new-materials.html
    title           = New Books
    institution_name = Test Library
    logo_url        = https://example.com/logo.png
    primary_color   = #cc0000
    accent_color    = #ffeeee

    [material_types]
    2d72aa13-2451-41fe-afc7-b3dc7c131389 = Books
    faa0cd0a-e408-4b57-acff-1c3f9171723d = DVD
"""


# ── Positive tests ────────────────────────────────────────────────────


class TestMinimalConfig:
    def setup_method(self, _, tmp_path=None):
        # pytest passes tmp_path via fixture, not setup_method
        pass

    def test_loads_required_values(self, tmp_path):
        cfg = Config(_write_config(tmp_path, MINIMAL_CONFIG))
        assert cfg.folio_base_url == "https://api.example.com"
        assert cfg.folio_username == "testuser"
        assert cfg.folio_password == "testpass"

    def test_default_tenant(self, tmp_path):
        cfg = Config(_write_config(tmp_path, MINIMAL_CONFIG))
        assert cfg.folio_tenant == "fs00001006"

    def test_default_days(self, tmp_path):
        cfg = Config(_write_config(tmp_path, MINIMAL_CONFIG))
        assert cfg.output_days == 30

    def test_google_disabled_when_not_configured(self, tmp_path):
        cfg = Config(_write_config(tmp_path, MINIMAL_CONFIG))
        assert not cfg.google_enabled

    def test_eds_disabled_when_not_configured(self, tmp_path):
        cfg = Config(_write_config(tmp_path, MINIMAL_CONFIG))
        assert not cfg.eds_enabled

    def test_material_types_empty_by_default(self, tmp_path):
        cfg = Config(_write_config(tmp_path, MINIMAL_CONFIG))
        assert cfg.material_types == {}


class TestFullConfig:
    def test_folio_values(self, tmp_path):
        cfg = Config(_write_config(tmp_path, FULL_CONFIG))
        assert cfg.folio_tenant == "mytenant"
        # Trailing slash on edge_api should be stripped
        assert cfg.folio_edge_api == "https://edge.example.com"

    def test_eds_values(self, tmp_path):
        cfg = Config(_write_config(tmp_path, FULL_CONFIG))
        assert cfg.eds_db_id == "abcdef"
        assert cfg.eds_catalog_db == "cat12345"
        assert cfg.eds_an_prefix == "scf.oai.edge.example.com.tenant01"
        assert cfg.eds_an_separator == "dots"
        assert cfg.eds_enabled is True

    def test_google_values(self, tmp_path):
        cfg = Config(_write_config(tmp_path, FULL_CONFIG))
        assert cfg.google_api_key == "GOOGLE_KEY"
        assert cfg.google_cx == "GOOGLE_CX"
        assert cfg.google_enabled is True

    def test_output_values(self, tmp_path):
        cfg = Config(_write_config(tmp_path, FULL_CONFIG))
        assert cfg.output_days == 14
        assert cfg.output_file == "/tmp/new-materials.html"
        assert cfg.output_title == "New Books"
        assert cfg.institution_name == "Test Library"
        assert cfg.institution_logo_url == "https://example.com/logo.png"
        assert cfg.primary_color == "#cc0000"
        assert cfg.accent_color == "#ffeeee"

    def test_material_types(self, tmp_path):
        cfg = Config(_write_config(tmp_path, FULL_CONFIG))
        types = cfg.material_types
        assert len(types) == 2
        assert types["2d72aa13-2451-41fe-afc7-b3dc7c131389"] == "Books"
        assert types["faa0cd0a-e408-4b57-acff-1c3f9171723d"] == "DVD"


# ── Error tests ───────────────────────────────────────────────────────


def test_raises_when_file_missing():
    with pytest.raises(ConfigError, match="not found"):
        Config("/nonexistent/config.ini")


def test_raises_when_base_url_missing(tmp_path):
    content = "[folio]\nusername = u\npassword = p\n"
    with pytest.raises(ConfigError, match="base_url"):
        Config(_write_config(tmp_path, content))


def test_raises_when_username_missing(tmp_path):
    content = "[folio]\nbase_url = https://x.com\npassword = p\n"
    with pytest.raises(ConfigError, match="username"):
        Config(_write_config(tmp_path, content))


def test_raises_when_password_missing(tmp_path):
    content = "[folio]\nbase_url = https://x.com\nusername = u\n"
    with pytest.raises(ConfigError, match="password"):
        Config(_write_config(tmp_path, content))


def test_invalid_days_falls_back_to_default(tmp_path):
    content = MINIMAL_CONFIG + "\n[output]\ndays = notanumber\n"
    cfg = Config(_write_config(tmp_path, content))
    assert cfg.output_days == 30
