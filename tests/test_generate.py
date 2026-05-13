"""Tests for the entry-point helpers in generate.py."""

from unittest.mock import MagicMock

from generate import _slugify, _write_per_type_pages


# ── _slugify ─────────────────────────────────────────────────────────


class TestSlugify:
    def test_simple_lowercase(self):
        assert _slugify("Books") == "books"

    def test_space_to_hyphen(self):
        assert _slugify("Music CD") == "music-cd"

    def test_strips_punctuation(self):
        assert _slugify("Audio/Visual Material!") == "audiovisual-material"

    def test_collapses_consecutive_separators(self):
        assert _slugify("Foo   Bar___Baz") == "foo-bar-baz"

    def test_empty_falls_back_to_other(self):
        assert _slugify("") == "other"
        assert _slugify(None) == "other"


# ── per-type fan-out ──────────────────────────────────────────────────


def _config_for_per_type():
    cfg = MagicMock()
    cfg.primary_color = "#003366"
    cfg.accent_color = "#ffffff"
    cfg.eds_enabled = False
    cfg.output_title = "New Materials"
    cfg.institution_name = "Test Library"
    cfg.institution_logo_url = ""
    cfg.subject_groups = {}
    cfg.lcc_grouping = False
    cfg.default_view = "grid"
    cfg.holdings_display = "summary"
    cfg.material_types = {}
    return cfg


def _item(type_uuid, type_label):
    return {
        "id": "i", "instance_id": "x", "title": "T",
        "author": "A", "publisher": "", "year": "",
        "receipt_date": "2026-04-01",
        "type_uuid": type_uuid, "type_label": type_label,
        "subject_group": "", "subjects": [],
        "call_number": "", "holdings": [],
        "cover_url": None, "placeholder_color": "#2a5e8c",
        "eds_url": None, "isbn": None, "oclc": None,
    }


class TestWritePerTypePages:
    def test_writes_one_file_per_type(self, tmp_path):
        items = [
            _item("uuid-books", "Books"),
            _item("uuid-books", "Books"),
            _item("uuid-dvd",   "DVD"),
        ]
        cfg = _config_for_per_type()
        out = tmp_path / "out" / "new-materials.html"

        envelope = {"items": items, "total_count": 3,
                    "generated_at": "now",
                    "date_range": {"start": "2026-04-01", "end": "2026-05-01"},
                    "institution": "Test Library"}

        count = _write_per_type_pages(
            items=items, config=cfg, material_type_map={},
            output_path=str(out),
            start_date="2026-04-01", end_date="2026-05-01",
            generated_at="now", envelope_full=envelope,
            log=MagicMock(),
        )
        assert count == 2

        out_dir = out.parent
        assert (out_dir / "new-books.html").exists()
        assert (out_dir / "new-dvd.html").exists()
        # Shared assets and data feed written exactly once
        assert (out_dir / "assets" / "styles.css").exists()
        assert (out_dir / "data" / "items.json").exists()

    def test_combined_data_feed_has_all_items(self, tmp_path):
        import json
        items = [_item("uuid-books", "Books"), _item("uuid-dvd", "DVD")]
        cfg = _config_for_per_type()
        out = tmp_path / "out" / "new-materials.html"
        envelope = {"items": items, "total_count": 2,
                    "generated_at": "now",
                    "date_range": {"start": "2026-04-01", "end": "2026-05-01"},
                    "institution": "Test Library"}

        _write_per_type_pages(
            items=items, config=cfg, material_type_map={},
            output_path=str(out),
            start_date="2026-04-01", end_date="2026-05-01",
            generated_at="now", envelope_full=envelope,
            log=MagicMock(),
        )
        data = json.loads((out.parent / "data" / "items.json").read_text())
        assert data["total_count"] == 2
