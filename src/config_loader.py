"""Configuration loading and validation for FOLIO New Materials."""

import configparser
from pathlib import Path

from src.subjects import parse_groups_config


class ConfigError(Exception):
    """Raised when a required configuration value is missing or invalid."""


class Config:
    """
    Loads and exposes settings from a .ini file.

    Required sections and keys:
        [folio] base_url, username, password
    All other values have defaults documented in config.ini.example.
    """

    def __init__(self, config_path: str = "config.ini") -> None:
        path = Path(config_path)
        if not path.exists():
            raise ConfigError(
                f"Config file not found: {config_path}\n"
                "Copy config.ini.example to config.ini and fill in your values."
            )
        self._parser = configparser.ConfigParser()
        # Preserve case in keys so subject-group names like "Engineering"
        # are not lowercased.  Standard config keys (base_url, etc.) are
        # written lowercase by convention, so this is safe.
        self._parser.optionxform = str
        self._parser.read(config_path)
        self._validate()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        required = [
            ("folio", "base_url"),
            ("folio", "username"),
            ("folio", "password"),
        ]
        for section, key in required:
            if not self._get(section, key):
                raise ConfigError(f"Missing required config: [{section}] {key}")

    def _get(self, section: str, key: str, fallback: str = "") -> str:
        return self._parser.get(section, key, fallback=fallback).strip()

    # ------------------------------------------------------------------
    # FOLIO
    # ------------------------------------------------------------------

    @property
    def folio_base_url(self) -> str:
        return self._get("folio", "base_url").rstrip("/")

    @property
    def folio_tenant(self) -> str:
        return self._get("folio", "tenant", "fs00001006")

    @property
    def folio_username(self) -> str:
        return self._get("folio", "username")

    @property
    def folio_password(self) -> str:
        return self._get("folio", "password")

    @property
    def folio_edge_api(self) -> str:
        return self._get("folio", "edge_api").rstrip("/")

    @property
    def folio_edge_api_key(self) -> str:
        return self._get("folio", "edge_api_key")

    @property
    def edge_enabled(self) -> bool:
        """Edge RTAC is only used when both the URL and API key are set."""
        return bool(self.folio_edge_api and self.folio_edge_api_key)

    # ------------------------------------------------------------------
    # EDS
    # ------------------------------------------------------------------

    @property
    def eds_db_id(self) -> str:
        return self._get("eds", "db_id")

    @property
    def eds_catalog_db(self) -> str:
        return self._get("eds", "catalog_db")

    @property
    def eds_an_prefix(self) -> str:
        return self._get("eds", "an_prefix")

    @property
    def eds_an_separator(self) -> str:
        """Either 'dots' (default) or 'dashes' for UUID formatting in EDS links."""
        return self._get("eds", "an_separator", "dots")

    @property
    def eds_enabled(self) -> bool:
        return bool(self.eds_db_id and self.eds_catalog_db and self.eds_an_prefix)

    # ------------------------------------------------------------------
    # Google
    # ------------------------------------------------------------------

    @property
    def google_enabled(self) -> bool:
        """True unless explicitly set to false/0/no in [google] enabled."""
        raw = self._get("google", "enabled", "true").lower()
        return raw not in ("false", "0", "no")

    # ------------------------------------------------------------------
    # TMDB
    # ------------------------------------------------------------------

    @property
    def tmdb_api_key(self) -> str:
        return self._get("tmdb", "api_key")

    @property
    def tmdb_poster_size(self) -> str:
        """TMDB image size slug: w185, w342, w500, w780, original."""
        return self._get("tmdb", "poster_size", "w500")

    @property
    def tmdb_enabled(self) -> bool:
        return bool(self.tmdb_api_key)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    @property
    def output_days(self) -> int:
        try:
            return int(self._get("output", "days", "30"))
        except ValueError:
            return 30

    @property
    def output_file(self) -> str:
        return self._get("output", "output_file", "output/new-materials.html")

    @property
    def output_title(self) -> str:
        return self._get("output", "title", "New Materials")

    @property
    def institution_name(self) -> str:
        return self._get("output", "institution_name", "Library")

    @property
    def institution_logo_url(self) -> str:
        return self._get("output", "logo_url")

    @property
    def primary_color(self) -> str:
        return self._get("output", "primary_color", "#003366")

    @property
    def accent_color(self) -> str:
        return self._get("output", "accent_color", "#ffffff")

    @property
    def default_view(self) -> str:
        """Initial view when the user has no saved preference: 'grid' or 'table'."""
        raw = self._get("output", "default_view", "grid").lower()
        return raw if raw in ("grid", "table") else "grid"

    @property
    def holdings_display(self) -> str:
        """How richly to render multi-holding items: none | compact | summary | detailed."""
        raw = self._get("output", "holdings_display", "summary").lower()
        return raw if raw in ("none", "compact", "summary", "detailed") else "summary"

    @property
    def pages_per_type(self) -> bool:
        """
        When true, generate one HTML page per material type instead of one
        combined page with a format dropdown.  Useful for staff who want
        a shareable per-format list (e.g. new-books.html, new-dvds.html).
        Uses [material_types] when set; otherwise the types discovered in
        the data.
        """
        raw = self._get("output", "pages_per_type", "false").lower()
        return raw in ("true", "1", "yes")

    # ------------------------------------------------------------------
    # Material types
    # ------------------------------------------------------------------

    @property
    def material_types(self) -> dict[str, str]:
        """
        Returns an ordered dict mapping material-type UUID to display label.
        An empty dict means: query all types without UUID filtering.
        """
        if not self._parser.has_section("material_types"):
            return {}
        return {
            k: v
            for k, v in self._parser.items("material_types")
            if k and v and not k.startswith("#")
        }

    # ------------------------------------------------------------------
    # Subject groups
    # ------------------------------------------------------------------

    @property
    def subject_groups(self) -> dict[str, list[str]]:
        """
        Returns a map of group name → list of keywords.
        Used to classify items by subject heading for grouped display.

        The reserved key ``lcc_grouping`` is filtered out — it toggles the
        call-number-based grouping mode (see ``lcc_grouping``) rather than
        defining a real keyword group.
        """
        if not self._parser.has_section("subject_groups"):
            return {}
        raw = {
            k: v for k, v in self._parser.items("subject_groups")
            if k.lower() != "lcc_grouping"
        }
        return parse_groups_config(raw)

    @property
    def lcc_grouping(self) -> bool:
        """
        When true and no manual subject_groups are defined, derive subject
        groups from the Library of Congress top-level class encoded in each
        item's call number (e.g. "QA76" → "Q" → "Science").

        Reliable for LCC-using libraries; libraries on Dewey or other
        schemes will see all items in "Other" and should prefer manual
        groups instead.
        """
        if not self._parser.has_section("subject_groups"):
            return False
        raw = self._parser.get("subject_groups", "lcc_grouping", fallback="").strip().lower()
        return raw in ("true", "1", "yes")
