"""
Subject-heading classification.

Two grouping mechanisms are exposed:

  1. Keyword classification (classify_subject) — matches an item's FOLIO
     subjects against a user-defined map of group → keywords.  Curated.

  2. LCC-class lookup (lcc_class_from_call_number) — derives a high-level
     subject area from the item's call number using a longest-prefix match
     against the LCC class map shipped at static/lcc-classes.json.  Automatic.

generate.py uses these in combination: manual groups first, LCC as a
fallback when the manual groups don't match.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

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


# ─────────────────────────────────────────────────────────────────────
# Library of Congress Classification (LCC) lookup.
# The class map lives in static/lcc-classes.json so it can be audited
# and extended without code changes.  Loaded once and cached.
# ─────────────────────────────────────────────────────────────────────

_LCC_JSON_PATH = Path(__file__).parent.parent / "static" / "lcc-classes.json"
_LCC_MAP_CACHE: Optional[dict] = None
# Max alpha-prefix length to consider when matching (most LCC subclasses
# are 1-3 letters; a few use 4 but they're rare and not in our map).
_MAX_PREFIX_LEN = 3


def load_lcc_map() -> dict:
    """
    Load the LCC class map from static/lcc-classes.json (cached).

    Returns an empty dict on read error.  Comment keys starting with "_"
    are filtered out so they cannot accidentally shadow a real prefix.
    """
    global _LCC_MAP_CACHE
    if _LCC_MAP_CACHE is not None:
        return _LCC_MAP_CACHE
    try:
        with _LCC_JSON_PATH.open(encoding="utf-8") as f:
            raw = json.load(f)
        _LCC_MAP_CACHE = {
            k.upper(): v
            for k, v in raw.items()
            if not k.startswith("_") and isinstance(v, str)
        }
    except (OSError, ValueError) as exc:
        logger.warning("Could not load LCC class map from %s: %s", _LCC_JSON_PATH, exc)
        _LCC_MAP_CACHE = {}
    return _LCC_MAP_CACHE


def _reset_lcc_cache_for_tests() -> None:
    """Test helper — forces the next load_lcc_map() call to re-read from disk."""
    global _LCC_MAP_CACHE
    _LCC_MAP_CACHE = None


def lcc_class_from_call_number(call_number: str) -> Optional[str]:
    """
    Map a call number to its LCC class label via longest-prefix lookup.

    Tries the leading alpha prefix at decreasing lengths so that "PN51 .T7"
    matches "PN" → "Literature (General); Drama; Journalism" before falling
    back to "P" → "Language and Literature".

    Returns None when the call number is empty, non-LCC, or starts with a
    digit (Dewey, SuDoc, local schemes).
    """
    if not call_number:
        return None
    cn = call_number.strip().upper()
    if not cn or not cn[0].isalpha():
        return None

    # Extract the leading alpha run, capped at _MAX_PREFIX_LEN
    prefix = ""
    for ch in cn:
        if not ch.isalpha():
            break
        prefix += ch
        if len(prefix) >= _MAX_PREFIX_LEN:
            break

    lcc_map = load_lcc_map()
    # Longest-match: shrink the prefix one character at a time until we hit
    while prefix:
        match = lcc_map.get(prefix)
        if match:
            return match
        prefix = prefix[:-1]
    return None


def normalize_subjects(subjects: list) -> list[str]:
    """
    Flatten a FOLIO subjects array into a plain list of strings.

    Handles both shapes mod-search may return:
      - ["Subject A", "Subject B"]
      - [{"value": "Subject A"}, {"value": "Subject B"}]
    """
    out: list[str] = []
    for entry in subjects or []:
        if isinstance(entry, str):
            text = entry.strip()
        elif isinstance(entry, dict):
            text = (entry.get("value") or entry.get("subject") or "").strip()
        else:
            continue
        if text:
            out.append(text)
    return out


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
