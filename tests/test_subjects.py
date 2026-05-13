"""Tests for src/subjects.py — subject-heading classification."""

from src.subjects import (
    classify_subject,
    parse_groups_config,
    ungrouped_label,
    lcc_class_from_call_number,
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


# ── lcc_class_from_call_number ───────────────────────────────────────


class TestLccClass:
    def test_q_is_science(self):
        assert lcc_class_from_call_number("QA76.5 .S5 2024") == "Science"

    def test_p_is_language_and_literature(self):
        assert lcc_class_from_call_number("PS3558.E63 D8") == "Language & Literature"

    def test_lowercase_first_letter_works(self):
        assert lcc_class_from_call_number("ta330 .B57") == "Technology"

    def test_strips_leading_whitespace(self):
        assert lcc_class_from_call_number("  HF5429 .S5") == "Social Sciences"

    def test_empty_string_returns_none(self):
        assert lcc_class_from_call_number("") is None

    def test_dewey_decimal_returns_none(self):
        # Dewey starts with a digit, not an LCC letter
        assert lcc_class_from_call_number("641.5 SMI") is None

    def test_unknown_letter_returns_none(self):
        # X and Y are unassigned in LCC
        assert lcc_class_from_call_number("X999 .X") is None


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
