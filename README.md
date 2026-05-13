# FOLIO New Materials

Generates an accessible HTML5 page listing recently received library materials from
FOLIO's orders API.  Designed to be run as an overnight cron job that publishes a
small static site (HTML + CSS + JS + JSON) library staff can drop on any web server
or open directly via `file://`.

## Features

- Queries FOLIO `/orders/order-lines` for items with receipt status *Fully Received*
- Auto-discovers material-type names from FOLIO when not configured manually
- Cover images via the free Google Books viewapi (ISBN / OCLC lookup, no API key)
- Optional TMDB poster fallback for DVDs and video recordings
- Color-coded placeholder covers when no image is available (material type + title)
- EDS OpenURL deep links to each title's discovery page
- Subject-area grouping via keyword-based classification (`[subject_groups]` config)
- Grid view (6 columns at natural cover size) and a table view, toggled by the user
  and remembered in localStorage
- Title / author search, format filter, subject filter, sort (newest / alphabetical)
- Active-filter chips with one-click "clear all"
- Call-number display when present in holdings
- JSON data feed (`data/items.json`) emitted alongside the HTML for RSS bridges,
  dashboards, and other programmatic consumers
- A11Y: semantic HTML5, ARIA live region for filter results, skip-to-content link,
  40px touch targets, strong `:focus-visible` indicators, full keyboard navigation
- Print-friendly stylesheet (3-column grid, plain borders, no printed URLs)
- `<noscript>` fallback links users without JavaScript to the JSON data feed

---

## Quick start

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

Python 3.9 or newer is required (uses `dict[str, str]` PEP-585 annotations).

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

The generator writes three things into the same parent directory as the
configured `output_file` (default `output/`):

- `new-materials.html` — the page shell with embedded item data
- `assets/styles.css` and `assets/app.js` — copied from `static/`
- `data/items.json` — the same item data as a standalone feed

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
| `edge_api` | — | Optional Edge API base URL — enables RTAC holdings lookup |
| `edge_api_key` | — | API key for the Edge endpoint (paired with `edge_api`) |

#### `[eds]`
Used to build EDS OpenURL deep links. Leave blank to disable links.

| Key | Description |
|-----|-------------|
| `db_id` | Path component in `/c/{db_id}/openurl` |
| `catalog_db` | e.g. `cat09206a` |
| `an_prefix` | e.g. `scf.oai.edge.fivecolleges.folio.ebsco.com.fs00001006` |
| `an_separator` | `dots` (default) or `dashes` — how the UUID is formatted |

#### `[google]`
Cover image lookups via the free Google Books viewapi.  No API key required.
Lookup keys are ISBN first, then OCLC if available.

| Key | Default | Description |
|-----|---------|-------------|
| `enabled` | `true` | Set to `false` to disable Google Books lookups entirely |

#### `[tmdb]`
Optional TMDB (The Movie Database) poster fallback for DVDs / video recordings.
Tried only when Google Books returns no cover.  Get a free API key at
<https://www.themoviedb.org/settings/api>.

| Key | Default | Description |
|-----|---------|-------------|
| `api_key` | — | Leave blank to disable TMDB lookups |
| `poster_size` | `w500` | One of `w185`, `w342`, `w500`, `w780`, `original` |

#### `[output]`
| Key | Default | Description |
|-----|---------|-------------|
| `days` | `30` | Lookback window when no `--start`/`--end` given |
| `output_file` | `output/new-materials.html` | Output path for the HTML; assets/ and data/ are written alongside it |
| `title` | `New Materials` | Page heading |
| `institution_name` | `Library` | Shown in header and footer |
| `logo_url` | — | URL (or data: URI) of your logo image |
| `primary_color` | `#003366` | Header/link colour |
| `accent_color` | `#ffffff` | Text on primary background |
| `default_view` | `grid` | Initial view (`grid` or `table`); per-user choice is then saved to localStorage |
| `holdings_display` | `summary` | How to render multi-holding items: `none`, `compact`, `summary`, `detailed` |
| `pages_per_type` | `false` | When `true`, write one HTML page per material type (e.g. `new-books.html`) instead of a single combined page |

#### `[material_types]`
Maps FOLIO material-type UUIDs to display labels for the format dropdown.

**Leave this section empty (or omit it) to fetch ALL material types from
FOLIO.**  When empty, the generator calls `/material-types` to auto-discover
type names, so the dropdown is populated from the actual types that appear in
the results.  Add entries here only when you want to restrict the listing to
specific formats.

```ini
[material_types]
2d72aa13-2451-41fe-afc7-b3dc7c131389 = Books
faa0cd0a-e408-4b57-acff-1c3f9171723d = DVD
```

#### `[subject_groups]`
Optional.  Groups items by high-level subject area, with two modes:

**Manual groups (curated):**  list group names and keywords.  An item is
placed in the first group whose keyword appears in any of its FOLIO subject
headings; unmatched items are "Other".

```ini
[subject_groups]
Engineering = engineering, computer, programming, mathematics, physics
Humanities  = literature, philosophy, history, art, music
Sciences    = biology, chemistry, geology, ecology, astronomy
```

**LCC-based groups:**  set `lcc_grouping = true`.  Each item is classified
against the LCC class map shipped at `static/lcc-classes.json` (also copied
to `output/assets/lcc-classes.json` so it's auditable next to the page).
Longest-prefix matching gives ~150 buckets rather than 20:

- `PN51 .T7` → "Literature (General); Drama; Journalism" (PN match)
- `PS3558 .E63` → "American Literature" (PS match)
- `QA76.5` → "Mathematics; Computer Science" (QA match)
- `P51 .X` → "Language and Literature" (no PX in map, falls back to P)
- `641.5 SMI` → no match (Dewey doesn't start with a letter)

The two modes compose: when both are set, manual groups match first;
items the keywords don't catch fall through to LCC instead of going
straight to "Other".  Libraries on Dewey or local schemes should
prefer manual groups.

```ini
[subject_groups]
lcc_grouping = true

# Optional: hand-curated overrides that take precedence over LCC
# Engineering = engineering, computer, programming
```

To edit or extend the class map, change `static/lcc-classes.json` —
new entries are picked up on the next run.

When either mode is active, a second filter dropdown ("Subject area")
appears in the toolbar.

#### Pages per material type

Set `[output] pages_per_type = true` to generate one HTML page per
material type instead of a single combined page:

```
output/
├── new-books.html       (only Books, no format dropdown)
├── new-dvds.html        (only DVDs)
├── new-music-cd.html
├── assets/
│   ├── styles.css
│   └── app.js
└── data/
    └── items.json       (combined feed — all items)
```

Each page embeds only its own items as JSON.  The shared `data/items.json`
still contains every item for programmatic consumers.  Useful when
different staff want shareable per-format lists ("here's the new DVDs").

#### Holdings and RTAC
When `[folio] edge_api` and `edge_api_key` are both set, the generator
calls the Edge RTAC endpoint (`/prod/rtac/folioRTAC`) once per instance to
fetch live holdings data.  This supplies:

- Authoritative call numbers
- Library / location names (consortium-aware — handles multi-branch copies)
- Status (Available, Checked out, etc.) and due date
- Material type and barcode

Each item's `holdings` array in `data/items.json` contains every copy.
The card / table view shows them according to `holdings_display`:

| Mode | Card display |
|------|--------------|
| `none` | Hide the holdings block |
| `compact` | Just the count: "3 copies" |
| `summary` (default) | First call number + library, with "+N more" hint and full list on hover |
| `detailed` | Full list of all copies with call number / library / status |

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

The generator writes a small directory tree at the output location:

```
/var/www/html/library/
├── new-materials.html
├── assets/
│   ├── styles.css
│   └── app.js
└── data/
    └── items.json
```

Point the web server at the parent directory so the HTML can resolve
`assets/…` and `data/…` as siblings.

Example `/etc/cron.d/folio-new-materials`:

```cron
0 6 * * * libuser cd /srv && python /opt/folio-new-books/generate.py \
    --config /opt/folio-new-books/config.ini \
    --output /var/www/html/library/new-materials.html
```

---

## Running tests

```bash
python -m pytest tests/

# with coverage (requires pytest-cov, already in requirements.txt)
python -m pytest --cov=src tests/
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
│   ├── folio_client.py   # FOLIO Okapi API (auth, orders, instances)
│   ├── edge_client.py    # FOLIO Edge RTAC holdings lookup
│   ├── google_images.py  # Google Books cover lookup
│   ├── tmdb_client.py    # TMDB poster lookup
│   ├── subjects.py       # Subject classification (manual + auto-grouped)
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
