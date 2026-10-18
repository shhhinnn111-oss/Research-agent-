# Data pipeline

`build_data.py` merges the two compiled inputs into everything under `../data/`:

- the GTD-based Pakistan incident extract (2004–2020), joined to the curated recent layer;
- the OCHA administrative polygons (`kp_districts.geojson`, `kp_outline.geojson`).

It writes `incidents.json`, `district_stats.json`, `meta.json`, `kp_districts.geojson`,
`kp_outline.geojson`, `neighbours.geojson` and `kp_incidents.csv`.

`recent.py` holds the curated 2021–2026 records, each with its own source name and URL.
It is imported by `build_data.py`; edit it to add or correct a recent incident, then rerun
the build from this directory.

The raw GTD/PTD join table and the original OCHA shapefiles are not redistributed here;
obtain them from START (GTD), the Open Society Pakistan Terrorism Database extract, and
HDX/OCHA. The scripts document the expected columns and include the district aliasing,
HQ coordinates and SATP reference tables used by the interface.

Leaflet and Leaflet.heat are vendored under `../vendor/leaflet/` (BSD-2-Clause / MIT).
