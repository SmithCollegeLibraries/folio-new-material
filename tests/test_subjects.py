"""Tests for src/subjects.py — subject-heading classification."""

from src.subjects import (
    classify_subject,
    parse_groups_config,
    ungrouped_label,
    auto_classify,
    normalize_subjects,
    _flatten_subjects,
)


_GROUPS = {
    "Engineering": ["computer", "programming", "physics"],
    "Humanities":  ["literature", "philosophy", "history"],
    "Sciences":    ["biology", "chemistry"],
}


# ── classify_subject ──────────────────────────────────────────────────


class TestClassifySubject:
    def test_simple_keyword_match(self):
        subjects = ["Computer programming"]
        assert classify_subject(subjects, _GROUPS) == "Engineering"

    def test_matches_subdivision_text(self):
        # FOLIO often returns subjects like "X -- Y -- Z"; punctuation collapsed
        subjects = ["History -- 20th century"]
        assert classify_subject(subjects, _GROUPS) == "Humanities"

    def test_first_matching_group_wins(self):
        # "computer history" — Engineering comes first in dict order
        subjects = ["Computer history"]
        assert classify_subject(subjects, _GROUPS) == "Engineering"

    def test_no_match_returns_none(self):
        subjects = ["Cooking, French"]
        assert classify_subject(subjects, _GROUPS) is None

    def test_empty_subjects_returns_none(self):
        assert classify_subject([], _GROUPS) is None

    def test_empty_groups_returns_none(self):
        assert classify_subject(["Computer programming"], {}) is None

    def test_case_insensitive(self):
        subjects = ["COMPUTER SCIENCE"]
        assert classify_subject(subjects, _GROUPS) == "Engineering"

    def test_dict_shaped_subjects(self):
        # mod-search returns subjects as [{"value": "..."}]
        subjects = [{"value": "Biology textbook"}]
        assert classify_subject(subjects, _GROUPS) == "Sciences"

    def test_mixed_string_and_dict_subjects(self):
        subjects = ["History", {"value": "Philosophy"}]
        assert classify_subject(subjects, _GROUPS) == "Humanities"


# ── parse_groups_config ───────────────────────────────────────────────


class TestParseGroupsConfig:
    def test_splits_keywords(self):
        raw = {"Engineering": "computer, programming, math"}
        result = parse_groups_config(raw)
        assert result == {"Engineering": ["computer", "programming", "math"]}

    def test_strips_whitespace(self):
        raw = {"Sciences": "  biology ,  chemistry  "}
        result = parse_groups_config(raw)
        assert result == {"Sciences": ["biology", "chemistry"]}

    def test_lowercases_keywords(self):
        raw = {"Test": "Foo, BAR"}
        result = parse_groups_config(raw)
        assert result == {"Test": ["foo", "bar"]}

    def test_drops_empty_keywords(self):
        raw = {"Test": "foo, , bar,"}
        result = parse_groups_config(raw)
        assert result == {"Test": ["foo", "bar"]}

    def test_drops_groups_with_no_keywords(self):
        raw = {"Empty": "", "Has-Keywords": "foo"}
        result = parse_groups_config(raw)
        assert "Empty" not in result
        assert result["Has-Keywords"] == ["foo"]


# ── Helpers ───────────────────────────────────────────────────────────


def test_ungrouped_label():
    assert ungrouped_label() == "Other"


def test_flatten_subjects_strips_punctuation():
    blob = _flatten_subjects(["Computer programming -- Study and teaching"])
    assert "computer programming" in blob
    assert "--" not in blob  # collapsed to whitespace


# ── auto_classify ────────────────────────────────────────────────────


class TestAutoClassify:
    def test_strips_lc_subdivision(self):
        assert auto_classify(["History -- 20th century -- Sources"]) == "History"

    def test_handles_double_dash_without_spaces(self):
        assert auto_classify(["Mathematics--Study and teaching"]) == "Mathematics"

    def test_returns_full_heading_when_no_subdivision(self):
        assert auto_classify(["Mathematics"]) == "Mathematics"

    def test_picks_first_non_empty_subject(self):
        assert auto_classify(["", "  ", "Biology -- Textbooks"]) == "Biology"

    def test_returns_none_for_empty_list(self):
        assert auto_classify([]) is None

    def test_handles_dict_shape(self):
        assert auto_classify([{"value": "Physics -- Research"}]) == "Physics"

    def test_strips_trailing_punctuation(self):
        assert auto_classify(["History."]) == "History"


# ── normalize_subjects ───────────────────────────────────────────────


class TestNormalizeSubjects:
    def test_string_array(self):
        assert normalize_subjects(["A", "B"]) == ["A", "B"]

    def test_dict_array(self):
        assert normalize_subjects([{"value": "A"}, {"value": "B"}]) == ["A", "B"]

    def test_mixed_shapes(self):
        assert normalize_subjects(["A", {"value": "B"}]) == ["A", "B"]

    def test_empty_input(self):
        assert normalize_subjects([]) == []
        assert normalize_subjects(None) == []

    def test_drops_empty_strings(self):
        assert normalize_subjects(["", "A", {"value": ""}]) == ["A"]
