#!/usr/bin/env python3
"""
FOLIO New Materials — HTML generator.

Queries the FOLIO orders API for recently received items and writes a
self-contained HTML5 file that library staff can open in any browser.

Usage:
    python generate.py [options]

Options:
    --config PATH     Path to config.ini  (default: config.ini)
    --start DATE      Start date YYYY-MM-DD  (overrides --days)
    --end   DATE      End date YYYY-MM-DD    (overrides --days)
    --days  N         Days to look back from today  (overrides config)
    --output PATH     Output HTML file  (overrides config)
    --no-images       Skip cover-image lookup

Run this script from *outside* the project directory so that config.ini
is not accidentally exposed by a web server:

    cd /some/other/dir && python /opt/folio-new-books/generate.py \\
        --config /opt/folio-new-books/config.ini \\
        --output /var/www/html/new-materials.html
"""

import argparse
import logging
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from src.config_loader import Config, ConfigError
from src.folio_client import FolioClient, FolioAuthError
from src.google_images import fetch_cover_image
from src.html_generator import build_items, generate_html, write_output


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=level,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a new-materials HTML page from FOLIO.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config",
        default="config.ini",
        metavar="PATH",
        help="Path to config.ini (default: config.ini)",
    )
    parser.add_argument(
        "--start",
        metavar="YYYY-MM-DD",
        help="Start date (overrides --days)",
    )
    parser.add_argument(
        "--end",
        metavar="YYYY-MM-DD",
        help="End date (default: today)",
    )
    parser.add_argument(
        "--days",
        type=int,
        metavar="N",
        help="Days to look back from today (overrides config setting)",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Output HTML file (overrides config setting)",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Skip all cover-image lookups",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def _resolve_dates(args: argparse.Namespace, config: Config) -> tuple[str, str]:
    """Return (start_date, end_date) as YYYY-MM-DD strings."""
    today = date.today()
    end = date.fromisoformat(args.end) if args.end else today

    if args.start:
        start = date.fromisoformat(args.start)
    else:
        lookback = args.days if args.days is not None else config.output_days
        start = end - timedelta(days=lookback)

    return start.isoformat(), end.isoformat()


def _fetch_all_order_lines(client: FolioClient, start: str, end: str, config: Config) -> list[dict]:
    """
    Retrieve order lines from FOLIO for each configured material type.

    If no material types are configured, a single query fetches all types.
    Paginates automatically if there are more results than the default page size.
    """
    material_types = config.material_types  # UUID → label; empty = all
    queries = list(material_types.keys()) if material_types else [None]

    page_size = 200
    all_lines: list[dict] = []
    seen_ids: set[str] = set()

    for mat_uuid in queries:
        offset = 0
        while True:
            data = client.get_new_orders(
                start, end,
                material_uuid=mat_uuid,
                limit=page_size,
                offset=offset,
            )
            lines = data.get("poLines") or []
            total = data.get("totalRecords", 0)

            for line in lines:
                lid = line.get("id")
                if lid and lid not in seen_ids:
                    seen_ids.add(lid)
                    all_lines.append(line)

            offset += len(lines)
            if offset >= total or not lines:
                break

    return all_lines


def _enrich_with_images(items: list[dict], config: Config, skip: bool) -> None:
    """
    Fetch cover images via Google Books for each item in-place.

    Rate-limited to one request per second to be polite to Google's servers.
    Skips items that have neither an ISBN nor an OCLC number.
    """
    if skip or not config.google_enabled:
        return

    eligible = [i for i in items if i.get("isbn") or i.get("oclc")]
    if not eligible:
        return

    logging.getLogger(__name__).info(
        "Fetching cover images for %d items …", len(eligible)
    )
    for idx, item in enumerate(eligible):
        url = fetch_cover_image(
            isbn=item.get("isbn"),
            oclc=item.get("oclc"),
            config=config,
        )
        item["cover_url"] = url
        if idx > 0 and idx % 10 == 0:
            time.sleep(1)  # be polite to external APIs


def main() -> int:
    args = _parse_args()
    _setup_logging(args.verbose)
    log = logging.getLogger(__name__)

    # Load config
    try:
        config = Config(args.config)
    except ConfigError as exc:
        log.error("Configuration error: %s", exc)
        return 1

    # Resolve date window
    start_date, end_date = _resolve_dates(args, config)
    log.info("Date range: %s → %s", start_date, end_date)

    # Connect to FOLIO
    client = FolioClient(config)
    try:
        order_lines = _fetch_all_order_lines(client, start_date, end_date, config)
    except FolioAuthError as exc:
        log.error("FOLIO authentication failed: %s", exc)
        return 1
    except Exception as exc:
        log.error("Error fetching orders from FOLIO: %s", exc)
        return 1

    log.info("Retrieved %d order lines", len(order_lines))
    if not order_lines:
        log.warning("No order lines found for this date range — HTML will show an empty state.")

    # Fetch instance details
    instance_ids = [
        ln.get("instanceId") or ln.get("instanceid")
        for ln in order_lines
        if ln.get("instanceId") or ln.get("instanceid")
    ]
    try:
        instances = client.get_instances(list(set(instance_ids)))
    except Exception as exc:
        log.warning("Instance lookup failed: %s — titles from order lines will be used.", exc)
        instances = {}

    log.info("Fetched details for %d instances", len(instances))

    # Build display items
    items = build_items(order_lines, instances, config.material_types, config)

    # Optionally enrich with cover images
    _enrich_with_images(items, config, skip=args.no_images)

    # Render HTML
    from datetime import datetime
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = generate_html(
        items=items,
        material_types=config.material_types,
        start_date=start_date,
        end_date=end_date,
        generated_at=generated_at,
        config=config,
    )

    # Write output
    output_path = args.output or config.output_file
    try:
        write_output(html, output_path)
    except OSError as exc:
        log.error("Failed to write output: %s", exc)
        return 1

    log.info("Done — %d items written to %s", len(items), output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
