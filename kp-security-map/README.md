# Khyber Pakhtunkhwa Security Atlas

An explorable, year-by-year map of terrorism in Khyber Pakhtunkhwa — all 35 current
districts, including the seven erstwhile FATA agencies — built directly on the
South Asia Terrorism Portal's (SATP) Khyber Pakhtunkhwa datasheets and kept in step
with them by a local synchroniser.

No build step, no API keys, no database. Plain HTML, CSS, JavaScript and Leaflet,
one JSON snapshot, and a 160-line Python server that can re-download the source
tables on demand.

---

## Run it

```bash
cd kp-security-map
python3 serve.py            # http://127.0.0.1:8080, opens your browser
```

`serve.py` serves the folder *and* exposes the sync endpoints. Use it whenever you
want live updates. `--port`, `--host`, `--no-sync` and `--no-browser` are available.

Any static file server also works (`python3 -m http.server`, `npx serve`, nginx,
GitHub Pages) — you just lose the in-app **Sync SATP** button, because a static
host cannot write `data/satp.json`. Opening `index.html` straight from disk does
not work: browsers block `fetch()` on `file://`. Use the single-file edition below
for that.

---

## What the map shows

**The SATP record is the spine.** Eight published series, 2000–2026, read from the
portal's yearly tables — never estimated, never modelled:

| Series | Detail carried |
|---|---|
| Fatalities | killing incidents, civilians, security forces, militants, not specified, total |
| Terrorism-related incidents | yearly incident count |
| Major incidents | incidents, killed, injured |
| Suicide attacks | incidents, killed/injured split by victim class |
| Explosions | incidents, killed/injured split by victim class |
| Arrests | arrest incidents, persons arrested |
| Arms recovery | recoveries |
| Surrenders | incidents, persons surrendered |

Cumulative to 14 October 2026: **10,104 terrorism-related incidents**, **5,567
killing incidents**, **24,878 people killed** (6,469 civilians · 4,285 security
forces · 12,927 militants · 1,197 not specified) and **18,192 injured**.

**Districts.** All 35 shapes are drawn from the 2018 delimitation, with the seven
merged tribal agencies hatched so the erstwhile FATA is visible at a glance. A
choropleth shades them by SATP fatalities, civilians, security forces, militants or
killing incidents, or by the GTD incident record. When the district sheets have not
been synced yet the legend says so and shades from the GTD record rather than
pretending the SATP numbers are there.

**Incident layer.** 6,544 georeferenced incidents (GTD plus curated records,
2004–2020) as proportional circles and an optional heat surface. Nine attack
categories toggle independently, a five-step minimum-fatality filter thins them,
and clicking one opens its full record.

**Year control.** One slider drives everything: the map, the headline figures, the
year matrix, the timeline and the inspector. Cumulative mode aggregates 2000 → the
chosen year; single-year mode isolates it. **Play** animates the whole span at
850 ms per year. The timeline draws bars for incidents and lines for fatalities,
with peak values labelled.

**Deconflicted layout.** A fixed three-column grid — controls, map, inspector —
with the legend strip and the timeline inside the map column. Nothing floats over
the map except the small scale note, the map tag and the basemap credit, and those
sit in reserved corners. Panels scroll inside their own column; no figure is ever
covered by another panel. The grid collapses to two columns at 1240 px and to one
at 980 px, where the rail and the inspector become drawers.

**Linked.** Click a district on the map or in a ranking, and the inspector switches
to its dossier, the map zooms, and the incident list filters to it. Click a year in
the matrix or a bar in the timeline and the whole view moves. The URL hash records
year, cumulative/single, tab and district, so any view can be bookmarked.

---

## Keeping it current

SATP republishes its datasheets as new violence is recorded. The atlas follows them:

- `serve.py` refreshes the snapshot in the background when it is more than twelve
  hours old.
- **Sync SATP** re-downloads the nine province sheets and the 32 per-district
  fatality sheets, parses them, rewrites `data/satp.json` and hot-reloads the page.
- The header chip shows the snapshot date and whether the copy is live, stale,
  offline or failed. The **Sources** tab lists every URL used, the fetch time, and
  how many district sheets are loaded.
- If a sheet fails to parse, the previous values for that series are carried
  forward and the failure is recorded in `warnings` — a partial outage never
  blanks the atlas.
- A reCAPTCHA interstitial is detected and reported instead of overwriting good
  data.

Run it by hand when you prefer:

```bash
python3 tools/satp_refresh.py                 # all sheets + districts
python3 tools/satp_refresh.py --no-districts  # province sheets only (fast)
```

### API

| Route | Purpose |
|---|---|
| `GET /api/satp/status` | snapshot date, fetch time, district count, warnings, last error, busy flag |
| `GET /api/satp/data` | the current `satp.json`, no cache |
| `POST /api/satp/refresh` | start a sync (`?districts=0` to skip the 32 district sheets) |

---

## Offline editions

Both are built from this folder; the single file also sits beside it in the delivered set.

| File | What it is |
|---|---|
| `kp-security-atlas-offline.html` | **One file, no install.** Double-click it. 4.5 MB. |
| `kp-security-atlas.zip` | The whole folder with `serve.py`, for running locally with real basemap imagery. |

The single file embeds the CSS, Leaflet, Leaflet.heat, the application and all six
data files. Everything works from `file://`: the SATP series and year controls, the
choropleth, the incident log, search, timeline playback and CSV export. The basemap
is drawn in the browser — district outlines, province boundary, neighbouring
regions, graticule and labels — because tile imagery lives on the network. Live sync
is absent from this edition, and the header chip says so.

Rebuild both after changing data or code:

```bash
python3 tools/build_offline.py     # rewrites ../kp-security-atlas-offline.html
```

---

## Basemaps

The "Google Maps" options draw Google tile imagery through Leaflet's tile layer
(`mt0–mt3.google.com/vt`, roadmap / satellite / hybrid / terrain). That is Google
cartography, but it is **not** the paid Google Maps JavaScript API: there is no key,
no quota and no support, and Google may throttle it. If tiles start failing the
atlas switches itself to OpenStreetMap after a handful of errors. CARTO light and
dark are offered for data work, OSM as the neutral fallback, and the vector basemap
for offline use. Basemap credits are always printed in the map corner.

---

## Honest limits

- **SATP is provisional.** It compiles figures from news reports and revises them;
  the snapshot date is in the header for exactly that reason.
- **Province and district, not address.** SATP publishes a yearly number per
  district, not coordinates. The pins are a separate GTD layer and are never mixed
  into the SATP totals. District shading uses SATP's own per-district sheets.
- **Boundaries move.** SATP still publishes Chitral and Kohistan as single districts;
  the map uses the five post-2018 units and shows the parent total on each part,
  labelled in the dossier.
- **No reconciliation.** Where SATP and GTD disagree, both are shown with their
  provenance. Nothing is averaged.
- **`other-data` is a catalogue.** SATP's ninth sheet is an index of some 200
  sub-datasheets (attacks on police, mosques, schools, Shias, Hazaras, polio
  workers, and so on), not a single table. The Sources tab links the catalogue
  rather than pretending it is a series.

---

## Layout of the folder

```
index.html              the page: header, rail, map column, inspector, method modal
css/app.css             the whole design system and the three-column grid
js/app.js               state, Leaflet layers, charts, inspector, sync, export
data/satp.json          the authoritative SATP snapshot (province series + districts)
data/kp_districts.geojson   35 district shapes (2018 delimitation)
data/kp_outline.geojson     province boundary
data/neighbours.geojson     Afghanistan, Punjab, Sindh, Balochistan, Gilgit-Baltistan
data/district_stats.json    GTD district aggregates (incidents, killed, injured, by year)
data/incidents.json     6,544 georeferenced incident records
data/meta.json          provenance for the GTD build
vendor/leaflet/         Leaflet 1.9.4, Leaflet.heat, marker images
tools/satp_refresh.py   live synchroniser and table parser
tools/build_satp.py     rebuilds satp.json from transcribed tables (no network)
tools/build_offline.py  single-file builder
serve.py                static server + sync API
pipeline/               GTD ingest, joins, dedupe and QA scripts
```

---

## Sources

- SATP, Khyber Pakhtunkhwa datasheets —
  [fatalities](https://www.satp.org/datasheet-terrorist-attack/fatalities/pakistan-khyberpakhtunkhwa),
  [incidents](https://www.satp.org/datasheet-terrorist-attack/incidents-data/pakistan-khyberpakhtunkhwa),
  [major incidents](https://www.satp.org/datasheet-terrorist-attack/major-incidents/pakistan-khyberpakhtunkhwa),
  [suicide attacks](https://www.satp.org/datasheet-terrorist-attack/suicide-attacks/pakistan-khyberpakhtunkhwa),
  [explosions](https://www.satp.org/datasheet-terrorist-attack/explosions/pakistan-khyberpakhtunkhwa),
  [arrests](https://www.satp.org/datasheet-terrorist-attack/arrest/pakistan-khyberpakhtunkhwa),
  [arms recovery](https://www.satp.org/datasheet-terrorist-attack/recovery-of-arms/pakistan-khyberpakhtunkhwa),
  [surrenders](https://www.satp.org/datasheet-terrorist-attack/surrender/pakistan-khyberpakhtunkhwa),
  [other data](https://www.satp.org/datasheet-terrorist-attack/other-data/pakistan-khyberpakhtunkhwa),
  [district index](https://www.satp.org/datasheet/district/pakistan-khyberpakhtunkhwa)
- Global Terrorism Database (START, University of Maryland) for the georeferenced
  incident layer, with the joins, dedupe and QA documented in `pipeline/`.

Boundaries are simplified from public administrative geodata for cartographic
display; they are not a legal statement about any boundary.
