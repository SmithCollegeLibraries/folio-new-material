# FOLIO New Materials

Generates a self-contained HTML5 page listing recently received library materials from
FOLIO's orders API. Designed to be run as an overnight cron job.

## Features

- Queries FOLIO `/orders/order-lines` for items with receipt status *Fully Received*
- Optional cover images via Open Library (free) or Google Custom Search
- EDS deep-link support for each title
- Filterable by material format (dropdown, no page reload)
- Fully accessible: semantic HTML5, ARIA live regions, skip-to-content link, keyboard navigable
- Self-contained output: one HTML file, no server needed to view it

---

## Quick start

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

Python 3.11+ is recommended.

### 2. Create your config

```bash
cp config.ini.example config.ini
```

Edit `config.ini` and fill in at minimum:

| Key | Description |
|-----|-------------|
| `[folio] base_url` | Okapi gateway URL |
| `[folio] username` | FOLIO account (needs orders + inventory read) |
| `[folio] password` | FOLIO password |

### 3. Run the generator

```bash
python generate.py
```

The output file defaults to `output/new-materials.html`.

---

## Configuration reference

See `config.ini.example` — every key is documented inline.

### Sections

#### `[folio]`
Connection settings for your FOLIO instance.

| Key | Default | Description |
|-----|---------|-------------|
| `base_url` | — | Okapi gateway (no trailing slash) |
| `tenant` | `fs00001006` | `x-okapi-tenant` header value |
| `username` | — | FOLIO username |
| `password` | — | FOLIO password |
| `edge_api` | — | Optional Edge API base URL |

#### `[eds]`
Used to build EDS OpenURL deep links. Leave blank to disable links.

| Key | Description |
|-----|-------------|
| `db_id` | Path component in `/c/{db_id}/openurl` |
| `catalog_db` | e.g. `cat09206a` |
| `an_prefix` | e.g. `scf.oai.edge.fivecolleges.folio.ebsco.com.fs00001006` |
| `an_separator` | `dots` (default) or `dashes` — how the UUID is formatted |

#### `[google]`
Optional cover images from Google Custom Search. Leave both blank to disable.

| Key | Description |
|-----|-------------|
| `api_key` | Google API key |
| `cx` | Custom Search Engine ID |

When Google is not configured, Open Library is checked automatically for ISBNs.

#### `[output]`
| Key | Default | Description |
|-----|---------|-------------|
| `days` | `30` | Lookback window when no `--start`/`--end` given |
| `output_file` | `output/new-materials.html` | Output path |
| `title` | `New Materials` | Page heading |
| `institution_name` | `Library` | Shown in header and footer |
| `logo_url` | — | URL of your logo image |
| `primary_color` | `#003366` | Header/link colour |
| `accent_color` | `#ffffff` | Text on primary background |

#### `[material_types]`
Maps FOLIO material-type UUIDs to display labels for the dropdown. Leave empty to show
all material types.

```ini
[material_types]
2d72aa13-2451-41fe-afc7-b3dc7c131389 = Books
faa0cd0a-e408-4b57-acff-1c3f9171723d = DVD
```

---

## CLI options

```
python generate.py [options]

  --config PATH     Config file (default: config.ini)
  --start DATE      Start date YYYY-MM-DD  (overrides --days)
  --end DATE        End date YYYY-MM-DD
  --days N          Lookback days (overrides config)
  --output PATH     Output file (overrides config)
  --no-images       Skip cover-image lookup
  --verbose         Debug logging
```

---

## Cron job setup

> **Security note:** Run the script from *outside* the project directory.
> This keeps `config.ini` away from any web-accessible path.

Example `/etc/cron.d/folio-new-materials`:

```cron
0 6 * * * libuser cd /srv && python /opt/folio-new-books/generate.py \
    --config /opt/folio-new-books/config.ini \
    --output /var/www/html/library/new-materials.html
```

---

## Running tests

```bash
pytest --cov=src tests/
```

---

## Project structure

```
folio-new-books/
├── config.ini.example    # Copy → config.ini and fill in credentials
├── generate.py           # Entry point
├── requirements.txt
├── src/
│   ├── config_loader.py  # INI config loading and validation
│   ├── folio_client.py   # FOLIO API auth and queries
│   ├── google_images.py  # Google Books cover lookup
│   ├── tmdb_client.py    # TMDB poster lookup
│   ├── subjects.py       # Subject-group classification
│   └── html_generator.py # Item building, HTML/JSON rendering
├── templates/
│   └── new_materials.html.j2  # Page shell (Jinja2)
├── static/               # Copied verbatim into <output>/assets/
│   ├── styles.css        # All styling
│   └── app.js            # Filter, sort, view-toggle, render
├── tests/                # pytest suite
└── output/               # Generated files (gitignored)
```

## Output layout

Each run produces a clean three-folder structure that can be served by any
static web host (or opened directly via `file://`).

```
output/
├── new-materials.html    # ~10KB shell — embedded JSON, no inline CSS/JS
├── assets/
│   ├── styles.css        # All styling
│   └── app.js            # Reads the embedded JSON, renders the views
└── data/
    └── items.json        # Same data as a standalone file (for RSS, dashboards, etc.)
```

Notes:
- **Embedded JSON.** The HTML carries the item list in a
  `<script type="application/json" id="items-data">` block so the page works
  on `file://` URLs without a CORS workaround.  `app.js` reads it once at load
  and builds both the grid and table views from the same array.
- **Parallel JSON file.** `data/items.json` contains the exact same envelope
  (generated_at, date_range, institution, total_count, items[]) so that
  programmatic consumers — RSS bridges, dashboards, the campus portal — can
  fetch the data without parsing HTML.
- **JavaScript disabled.** The page renders a `<noscript>` notice that links
  to `data/items.json` so the data is still reachable.  If serving to public
  terminals where JS may be locked down, point patrons at the JSON file or
  the printable view (built-in print stylesheet renders a clean 3-col grid).
