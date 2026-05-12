"""
Subject-heading classification.

Maps an item's FOLIO subjects array onto one of several user-defined subject
groups using simple keyword matching.  Each group is defined by a list of
keywords; an item is placed in the first group whose keyword appears in any
of its subject strings (case-insensitive substring match).
"""

import re
from typing import Optional

_UNGROUPED_LABEL = "Other"


def classify_subject(
    subjects: list,
    subject_groups: dict[str, list[str]],
) -> Optional[str]:
    """
    Return the first matching subject-group name for an item, or None.

    Args:
        subjects:       Instance.subjects array from FOLIO. Items may be either
                        plain strings or dicts shaped like {"value": "Engineering"}.
        subject_groups: Map of group name → list of lowercase keywords.

    Returns:
        Group name string, or None if there's no match (or no groups configured).
    """
    if not subjects or not subject_groups:
        return None

    haystack = _flatten_subjects(subjects)
    if not haystack:
        return None

    for group_name, keywords in subject_groups.items():
        for keyword in keywords:
            kw = keyword.strip().lower()
            if kw and kw in haystack:
                return group_name

    return None


def parse_groups_config(raw: dict[str, str]) -> dict[str, list[str]]:
    """
    Convert a [subject_groups] config section into a normalized dict.

    Each value is a comma-separated keyword list; whitespace and empty
    entries are stripped.

    Example input:  {"Engineering": "computer, programming, physics"}
    Example output: {"Engineering": ["computer", "programming", "physics"]}
    """
    parsed: dict[str, list[str]] = {}
    for name, value in raw.items():
        keywords = [k.strip().lower() for k in value.split(",")]
        keywords = [k for k in keywords if k]
        if name and keywords:
            parsed[name] = keywords
    return parsed


def ungrouped_label() -> str:
    """Label used in the UI for items that match no subject group."""
    return _UNGROUPED_LABEL


def _flatten_subjects(subjects: list) -> str:
    """
    Concatenate all subject strings into a single lowercase blob for matching.

    Handles both flat string lists and the FOLIO mod-search shape where each
    subject is wrapped in a dict with a "value" field.
    """
    parts: list[str] = []
    for entry in subjects:
        if isinstance(entry, str):
            parts.append(entry)
        elif isinstance(entry, dict):
            val = entry.get("value") or entry.get("subject") or ""
            if val:
                parts.append(val)
    blob = " | ".join(parts).lower()
    # Collapse punctuation so " -- " subdivisions match as plain text
    return re.sub(r"[^\w\s]", " ", blob)
