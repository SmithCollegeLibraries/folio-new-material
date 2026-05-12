"""HTML5 output generation for FOLIO New Materials."""

import logging
import re
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from src.subjects import classify_subject, ungrouped_label

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# Identifier type names that indicate an ISBN
_ISBN_TYPE_NAMES = {"isbn", "isbn-10", "isbn-13"}

# Key used internally to tag an order line with the material UUID we queried
# with.  Lets us filter reliably even when /orders does not echo back
# physical.materialType in the response payload.
_QUERIED_TYPE_KEY = "_queried_material_uuid"

# Curated palette for placeholder covers — picked for legibility on white text
# and reasonable colour-blind separation.  Items get a stable colour derived
# from their material-type UUID so the same format always looks the same.
_PLACEHOLDER_PALETTE = [
    "#2a5e8c",  # deep blue
    "#7d3f5d",  # plum
    "#3a6b50",  # forest
    "#8a5a2b",  # russet
    "#5a4b8a",  # indigo
    "#0f6e6e",  # teal
    "#8a4040",  # brick
    "#4a4a4a",  # graphite
]


def build_items(
    order_lines: list[dict],
    instances: dict[str, dict],
    material_types: dict[str, str],
    config,
) -> list[dict]:
    """
    Merge order-line and instance data into a flat list of display items.

    Args:
        order_lines:    Raw poLines records from the FOLIO orders API.
        instances:      Map of instance UUID → instance record from mod-search.
        material_types: UUID → label map from config (empty = all types).
        config:         Application config object.

    Returns:
        List of item dicts ready for the HTML template.
    """
    items = []
    for line in order_lines:
        instance_id = line.get("instanceId") or line.get("instanceid")
        if not instance_id:
            logger.debug("Skipping order line %s — no instanceId", line.get("id"))
            continue

        instance = instances.get(instance_id, {})

        type_uuid = _material_uuid_from_line(line)
        type_label = (
            material_types.get(type_uuid)
            or _infer_type_label(instance)
            or "Other"
        )
        configured_groups = getattr(config, "subject_groups", {}) or {}
        subject_group = classify_subject(
            instance.get("subjects") or [],
            configured_groups,
        )
        # When subject-grouping is enabled but the item matches no group,
        # tag it as "Other" so it can be filtered/displayed as such.
        if not subject_group and configured_groups:
            subject_group = ungrouped_label()

        item = {
            "id": line.get("id", instance_id),
            "instance_id": instance_id,
            "title": instance.get("title") or line.get("titleOrPackage", "Unknown title"),
            "author": _primary_author(instance),
            "publisher": _publisher(instance),
            "year": _pub_year(instance),
            "receipt_date": _format_date(line.get("receiptDate", "")),
            "type_uuid": type_uuid,
            "type_label": type_label,
            "subject_group": subject_group or "",
            "call_number": _call_number(line, instance),
            "cover_url": None,  # populated later by generate.py if images enabled
            "placeholder_color": _placeholder_color(type_uuid or type_label),
            "eds_url": _eds_url(instance_id, config),
            "isbn": _isbn(instance),
            "oclc": _oclc(instance),
        }
        items.append(item)

    return items


def generate_html(
    items: list[dict],
    material_types: dict[str, str],
    start_date: str,
    end_date: str,
    generated_at: str,
    config,
) -> str:
    """
    Render the HTML5 output from the Jinja2 template.

    Returns:
        Rendered HTML string.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=True,  # all templates are HTML; escape everything by default
    )
    template = env.get_template("new_materials.html.j2")

    # Build the set of types that actually appear in the item list
    seen_types: dict[str, str] = {}
    for item in items:
        uuid = item["type_uuid"]
        if uuid and uuid not in seen_types:
            seen_types[uuid] = item["type_label"]

    # If configured types were given, keep their order; otherwise sort by label
    if material_types:
        active_types = {
            uuid: label
            for uuid, label in material_types.items()
            if uuid in seen_types
        }
    else:
        active_types = dict(sorted(seen_types.items(), key=lambda kv: kv[1]))

    counts = {
        uuid: sum(1 for i in items if i["type_uuid"] == uuid)
        for uuid in active_types
    }

    # Subject groups that actually appear in the item list, in config order.
    # This keeps the dropdown predictable for staff (matches their config).
    configured_groups = getattr(config, "subject_groups", None) or {}
    active_subject_groups: dict[str, int] = {}
    if configured_groups:
        for name in configured_groups:
            count = sum(1 for i in items if i.get("subject_group") == name)
            if count > 0:
                active_subject_groups[name] = count
        other_count = sum(1 for i in items if i.get("subject_group") == ungrouped_label())
        if other_count > 0:
            active_subject_groups[ungrouped_label()] = other_count

    return template.render(
        title=config.output_title,
        institution_name=config.institution_name,
        logo_url=config.institution_logo_url,
        primary_color=config.primary_color,
        accent_color=config.accent_color,
        start_date=start_date,
        end_date=end_date,
        generated_at=generated_at,
        items=items,
        active_types=active_types,
        counts=counts,
        subject_groups=active_subject_groups,
        subject_grouping_enabled=bool(getattr(config, "subject_groups", None)),
        ungrouped_label=ungrouped_label(),
        default_view=getattr(config, "default_view", "grid"),
        total_count=len(items),
    )


def write_output(html: str, output_path: str) -> None:
    """Write the rendered HTML to disk, creating parent directories as needed."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    logger.info("Output written to %s", path.resolve())


# ------------------------------------------------------------------
# Private extraction helpers
# ------------------------------------------------------------------


def _material_uuid_from_line(line: dict) -> str:
    """
    Return the material-type UUID for an order line.

    Prefers the queried UUID tagged by generate.py (always set when we asked
    for a specific type) so filtering stays accurate even when /orders does
    not echo physical.materialType in its response.
    """
    queried = line.get(_QUERIED_TYPE_KEY)
    if queried:
        return queried
    physical = line.get("physical") or {}
    return physical.get("materialType") or physical.get("materialTypeId") or ""


def _call_number(line: dict, instance: dict) -> str:
    """
    Best-effort call number lookup for display.

    Falls back through the most reliable sources first:
      1. The order line's physical.location.callNumber
      2. The instance's first holdings record's callNumber
      3. Empty string when nothing is available
    """
    physical = line.get("physical") or {}
    loc = physical.get("location") or {}
    cn = loc.get("callNumber")
    if cn:
        return cn
    for holding in instance.get("holdings") or []:
        cn = holding.get("callNumber")
        if cn:
            return cn
    return ""


def _primary_author(instance: dict) -> str:
    contributors = instance.get("contributors") or []
    primary = next((c for c in contributors if c.get("primary")), None)
    chosen = primary or (contributors[0] if contributors else None)
    return chosen.get("name", "") if chosen else ""


def _publisher(instance: dict) -> str:
    pubs = instance.get("publication") or []
    return pubs[0].get("publisher", "") if pubs else ""


def _pub_year(instance: dict) -> str:
    pubs = instance.get("publication") or []
    return pubs[0].get("dateOfPublication", "") if pubs else ""


def _isbn(instance: dict) -> Optional[str]:
    """Return the first ISBN-looking identifier from the instance record."""
    for ident in instance.get("identifiers") or []:
        value = ident.get("value", "").replace("-", "").replace(" ", "")
        if re.fullmatch(r"\d{10}|\d{13}", value):
            return value
    return None


def _oclc(instance: dict) -> Optional[str]:
    """
    Return the OCLC number from instance identifiers if present.

    FOLIO stores OCLC numbers either as bare digits or with an "(OCoLC)" prefix.
    Returns the bare numeric string so it can be passed directly to the Google Books API.
    """
    for ident in instance.get("identifiers") or []:
        value = ident.get("value", "").strip()
        match = re.match(r"^\(OCoLC\)(\d+)$", value)
        if match:
            return match.group(1)
    return None


def _format_date(iso_date: str) -> str:
    """Return the date portion of an ISO datetime string (YYYY-MM-DD)."""
    return iso_date[:10] if iso_date else ""


def _placeholder_color(seed: str) -> str:
    """
    Pick a consistent placeholder-cover background colour for a given seed.

    Uses a stable hash of the seed (typically the material-type UUID) so the
    same format gets the same colour every time the page is regenerated.
    """
    if not seed:
        return _PLACEHOLDER_PALETTE[-1]
    digest = sum(ord(c) for c in seed)
    return _PLACEHOLDER_PALETTE[digest % len(_PLACEHOLDER_PALETTE)]


def _infer_type_label(instance: dict) -> str:
    """Best-effort label when the material type UUID is not in config."""
    formats = instance.get("instanceFormats") or []
    if formats:
        return formats[0].get("name", "Other")
    return "Other"


def _eds_url(instance_id: str, config) -> Optional[str]:
    """Build an EDS OpenURL deep link for a FOLIO instance UUID."""
    if not config.eds_enabled:
        return None

    sep = "-" if config.eds_an_separator == "dashes" else "."
    formatted_id = instance_id.replace("-", sep)
    an_value = f"{config.eds_an_prefix}.{formatted_id}"
    id_param = f"ebsco:{config.eds_catalog_db}:{an_value}"

    return (
        f"https://openurl.ebsco.com/c/{config.eds_db_id}/openurl"
        f"?sid=ebsco:plink&id={id_param}&crl=f&prompt=none"
    )
