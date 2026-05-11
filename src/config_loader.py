"""Configuration loading and validation for FOLIO New Materials."""

import configparser
from pathlib import Path


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
    def google_api_key(self) -> str:
        return self._get("google", "api_key")

    @property
    def google_cx(self) -> str:
        return self._get("google", "cx")

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_api_key and self.google_cx)

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
