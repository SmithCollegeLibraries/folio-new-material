"""Tests for src/html_generator.py."""

from unittest.mock import MagicMock

import pytest

from src.html_generator import (
    build_items,
    generate_html,
    _eds_url,
    _primary_author,
    _publisher,
    _pub_year,
    _isbn,
    _oclc,
    _format_date,
    _material_uuid_from_line,
)


# ── Fixtures ──────────────────────────────────────────────────────────


def _config(
    primary_color="#003366",
    accent_color="#ffffff",
    eds_enabled=True,
    eds_db_id="4e4lys",
    eds_catalog_db="cat09206a",
    eds_an_prefix="scf.oai.edge.example.com.tenant01",
    eds_an_separator="dots",
    output_title="New Materials",
    institution_name="Test Library",
    institution_logo_url="",
    subject_groups=None,
    default_view="grid",
):
    cfg = MagicMock()
    cfg.primary_color = primary_color
    cfg.accent_color = accent_color
    cfg.eds_enabled = eds_enabled
    cfg.eds_db_id = eds_db_id
    cfg.eds_catalog_db = eds_catalog_db
    cfg.eds_an_prefix = eds_an_prefix
    cfg.eds_an_separator = eds_an_separator
    cfg.output_title = output_title
    cfg.institution_name = institution_name
    cfg.institution_logo_url = institution_logo_url
    cfg.subject_groups = subject_groups or {}
    cfg.default_view = default_view
    return cfg


SAMPLE_INSTANCE = {
    "id": "eb83a0c0-c9f8-4b09-8362-2bbcc06f0a16",
    "title": "The Great Library Book",
    "contributors": [
        {"name": "Smith, Jane", "primary": True, "contributorNameTypeId": "2b94c631-fca9-4892-a730-03ee529ffe2a"},
        {"name": "Doe, John", "primary": False, "contributorNameTypeId": "2b94c631-fca9-4892-a730-03ee529ffe2a"},
    ],
    "publication": [
        {"publisher": "Academic Press", "dateOfPublication": "2023", "place": "New York"},
    ],
    "identifiers": [
        {"value": "9780123456789", "identifierTypeId": "isbn-type-id"},
        {"value": "(OCoLC)12345678", "identifierTypeId": "oclc-type-id"},
        {"value": "SomeOtherValue", "identifierTypeId": "other-type-id"},
    ],
}

SAMPLE_ORDER_LINE = {
    "id": "order-line-uuid",
    "instanceId": "eb83a0c0-c9f8-4b09-8362-2bbcc06f0a16",
    "titleOrPackage": "Fallback Title",
    "receiptDate": "2024-03-15T00:00:00.000+00:00",
    "receiptStatus": "Fully Received",
    "physical": {
        "materialType": "2d72aa13-2451-41fe-afc7-b3dc7c131389",
    },
}


# ── Helper function tests ─────────────────────────────────────────────


def test_primary_author_picks_primary_contributor():
    assert _primary_author(SAMPLE_INSTANCE) == "Smith, Jane"


def test_primary_author_falls_back_to_first():
    instance = {
        "contributors": [
            {"name": "Doe, John", "primary": False},
        ]
    }
    assert _primary_author(instance) == "Doe, John"


def test_primary_author_empty_for_no_contributors():
    assert _primary_author({}) == ""


def test_publisher_returns_first():
    assert _publisher(SAMPLE_INSTANCE) == "Academic Press"


def test_publisher_empty_for_no_publication():
    assert _publisher({}) == ""


def test_pub_year():
    assert _pub_year(SAMPLE_INSTANCE) == "2023"


def test_isbn_extracts_numeric():
    assert _isbn(SAMPLE_INSTANCE) == "9780123456789"


def test_isbn_returns_none_when_none_present():
    assert _isbn({"identifiers": [{"value": "notanisbn", "identifierTypeId": "x"}]}) is None


def test_oclc_extracts_from_ocolc_prefix():
    assert _oclc(SAMPLE_INSTANCE) == "12345678"


def test_oclc_returns_none_when_absent():
    instance = {"identifiers": [{"value": "9780123456789", "identifierTypeId": "isbn"}]}
    assert _oclc(instance) is None


def test_format_date_trims_to_date():
    assert _format_date("2024-03-15T00:00:00.000+00:00") == "2024-03-15"


def test_format_date_handles_empty():
    assert _format_date("") == ""


def test_material_uuid_from_line():
    assert _material_uuid_from_line(SAMPLE_ORDER_LINE) == "2d72aa13-2451-41fe-afc7-b3dc7c131389"


def test_material_uuid_empty_when_no_physical():
    assert _material_uuid_from_line({}) == ""


def test_material_uuid_prefers_queried_tag():
    """generate.py tags lines with the queried UUID; that should win."""
    line = {
        "_queried_material_uuid": "queried-uuid",
        "physical": {"materialType": "other-uuid"},
    }
    assert _material_uuid_from_line(line) == "queried-uuid"


# ── EDS URL ───────────────────────────────────────────────────────────


class TestEdsUrl:
    def test_builds_correct_url_with_dots(self):
        cfg = _config(eds_an_separator="dots")
        url = _eds_url("eb83a0c0-c9f8-4b09-8362-2bbcc06f0a16", cfg)
        assert "openurl.ebsco.com/c/4e4lys/openurl" in url
        assert "eb83a0c0.c9f8.4b09.8362.2bbcc06f0a16" in url
        assert "ebsco:plink" in url
        assert "ebsco:cat09206a" in url

    def test_builds_correct_url_with_dashes(self):
        cfg = _config(eds_an_separator="dashes")
        url = _eds_url("eb83a0c0-c9f8-4b09-8362-2bbcc06f0a16", cfg)
        assert "eb83a0c0-c9f8-4b09-8362-2bbcc06f0a16" in url

    def test_returns_none_when_eds_disabled(self):
        cfg = _config(eds_enabled=False)
        assert _eds_url("some-uuid", cfg) is None


# ── build_items ───────────────────────────────────────────────────────


class TestBuildItems:
    def test_merges_order_and_instance_data(self):
        instances = {SAMPLE_INSTANCE["id"]: SAMPLE_INSTANCE}
        types = {"2d72aa13-2451-41fe-afc7-b3dc7c131389": "Books"}
        items = build_items([SAMPLE_ORDER_LINE], instances, types, _config())

        assert len(items) == 1
        item = items[0]
        assert item["title"] == "The Great Library Book"
        assert item["author"] == "Smith, Jane"
        assert item["publisher"] == "Academic Press"
        assert item["year"] == "2023"
        assert item["receipt_date"] == "2024-03-15"
        assert item["type_label"] == "Books"
        assert item["isbn"] == "9780123456789"
        assert item["oclc"] == "12345678"
        assert item["eds_url"] is not None

    def test_uses_titleOrPackage_when_no_instance(self):
        items = build_items([SAMPLE_ORDER_LINE], {}, {}, _config())
        assert items[0]["title"] == "Fallback Title"

    def test_skips_lines_without_instance_id(self):
        line = {"id": "no-instance", "receiptDate": "2024-01-01"}
        items = build_items([line], {}, {}, _config())
        assert len(items) == 0

    def test_assigns_placeholder_color(self):
        instances = {SAMPLE_INSTANCE["id"]: SAMPLE_INSTANCE}
        items = build_items([SAMPLE_ORDER_LINE], instances, {}, _config())
        assert items[0]["placeholder_color"].startswith("#")

    def test_subject_classification_when_groups_configured(self):
        cfg = _config(subject_groups={"Sciences": ["chemistry", "biology"]})
        instance = dict(SAMPLE_INSTANCE, subjects=["Inorganic chemistry"])
        items = build_items([SAMPLE_ORDER_LINE], {instance["id"]: instance}, {}, cfg)
        assert items[0]["subject_group"] == "Sciences"

    def test_subject_group_empty_when_no_groups(self):
        items = build_items(
            [SAMPLE_ORDER_LINE],
            {SAMPLE_INSTANCE["id"]: SAMPLE_INSTANCE},
            {},
            _config(),
        )
        assert items[0]["subject_group"] == ""

    def test_call_number_from_holdings(self):
        instance = dict(SAMPLE_INSTANCE, holdings=[{"callNumber": "QA76.5"}])
        items = build_items([SAMPLE_ORDER_LINE], {instance["id"]: instance}, {}, _config())
        assert items[0]["call_number"] == "QA76.5"


# ── generate_html ─────────────────────────────────────────────────────


class TestGenerateHtml:
    def _sample_item(self, **kwargs):
        base = {
            "id": "item-1",
            "instance_id": "inst-1",
            "title": "Test Book",
            "author": "Author Name",
            "publisher": "Publisher",
            "year": "2024",
            "receipt_date": "2024-01-15",
            "type_uuid": "2d72aa13-2451-41fe-afc7-b3dc7c131389",
            "type_label": "Books",
            "subject_group": "",
            "call_number": "",
            "cover_url": None,
            "placeholder_color": "#2a5e8c",
            "eds_url": "https://openurl.ebsco.com/c/abc/openurl?sid=ebsco:plink&id=x",
            "isbn": None,
            "oclc": None,
        }
        base.update(kwargs)
        return base

    def test_renders_valid_html(self):
        items = [self._sample_item()]
        types = {"2d72aa13-2451-41fe-afc7-b3dc7c131389": "Books"}
        html = generate_html(items, types, "2024-01-01", "2024-01-31", "2024-02-01 06:00", _config())

        assert "<!DOCTYPE html>" in html
        assert "Test Book" in html
        assert "Author Name" in html
        assert "Books" in html

    def test_renders_empty_state_when_no_items(self):
        html = generate_html([], {}, "2024-01-01", "2024-01-31", "2024-02-01 06:00", _config())
        assert "No new materials" in html

    def test_includes_eds_link(self):
        items = [self._sample_item()]
        types = {"2d72aa13-2451-41fe-afc7-b3dc7c131389": "Books"}
        html = generate_html(items, types, "2024-01-01", "2024-01-31", "2024-02-01 06:00", _config())
        assert "openurl.ebsco.com" in html

    def test_includes_institution_name(self):
        cfg = _config(institution_name="Smith College Libraries")
        html = generate_html([], {}, "2024-01-01", "2024-01-31", "now", cfg)
        assert "Smith College Libraries" in html

    def test_contains_filter_script(self):
        html = generate_html([], {}, "2024-01-01", "2024-01-31", "now", _config())
        assert "format-filter" in html
        assert "<script>" in html

    def test_no_xss_in_title(self):
        """User-supplied config values must be escaped in HTML output."""
        cfg = _config(institution_name='<script>alert("xss")</script>')
        html = generate_html([], {}, "2024-01-01", "2024-01-31", "now", cfg)
        assert "<script>alert" not in html

    def test_renders_subject_filter_when_groups_enabled(self):
        cfg = _config(subject_groups={"Sciences": ["biology"]})
        item = self._sample_item(subject_group="Sciences")
        html = generate_html([item], {}, "2024-01-01", "2024-01-31", "now", cfg)
        assert 'id="subject-filter"' in html
        assert "Sciences" in html

    def test_omits_subject_filter_when_groups_disabled(self):
        item = self._sample_item()
        html = generate_html([item], {}, "2024-01-01", "2024-01-31", "now", _config())
        assert 'id="subject-filter"' not in html

    def test_renders_table_view_markup(self):
        item = self._sample_item()
        html = generate_html([item], {}, "2024-01-01", "2024-01-31", "now", _config())
        assert 'id="materials-table"' in html
        assert 'id="materials-grid"' in html  # both views rendered

    def test_default_view_table_hides_grid(self):
        cfg = _config(default_view="table")
        item = self._sample_item()
        html = generate_html([item], {}, "2024-01-01", "2024-01-31", "now", cfg)
        # Grid container should have the hidden attribute when table is default
        assert 'id="materials-grid"\n      class="materials-grid"\n      role="list"\n      aria-label="New materials (grid view)"\n      hidden' in html or 'aria-label="New materials (grid view)"\n      hidden' in html

    def test_placeholder_color_appears_when_no_cover(self):
        item = self._sample_item(cover_url=None, placeholder_color="#7d3f5d")
        html = generate_html([item], {}, "2024-01-01", "2024-01-31", "now", _config())
        assert "#7d3f5d" in html
