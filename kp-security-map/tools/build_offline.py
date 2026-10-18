#!/usr/bin/env python3
"""Build the single-file, fully offline edition of the Khyber Pakhtunkhwa Security Atlas.

    python3 tools/build_offline.py [--out PATH]

The output is one self-contained .html file: CSS, Leaflet, Leaflet.heat, the
application and every data file are inlined. Double-click it — no server, no
network, no install.

What works offline: the full SATP yearly record (all eight series), the year
matrix, the timeline and playback, the district choropleth, the district
dossiers, the GTD incident log with category and severity filters, search and
CSV export. The basemap is a drawn vector map — district outlines, the province
boundary, neighbouring regions, a graticule and place labels — because tile
imagery lives on the network. Live sync is disabled; the edition carries the
snapshot timestamp it was built from.
"""
import argparse, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(os.path.dirname(ROOT), 'kp-security-atlas-offline.html')

# Every data file the live app fetches, and the key it is handed to on
# window.__ATLAS__. Keep this list in step with js/app.js.
DATA = [
    ('satp',             'data/satp.json'),
    ('districts',        'data/kp_districts.geojson'),
    ('outline',          'data/kp_outline.geojson'),
    ('neighbours',       'data/neighbours.geojson'),
    ('gtdStats',         'data/district_stats.json'),
    ('incidents',        'data/incidents.json'),
]


def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


def guard(text):
    """Neutralise anything that could close an inline <script> block."""
    return text.replace('</script', '<\\/script').replace('<!--', '<\\!--')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=DEFAULT_OUT)
    args = ap.parse_args()

    for key, rel in DATA:
        if not os.path.exists(os.path.join(ROOT, rel)):
            sys.exit('missing data file: %s' % rel)

    html = read('index.html')
    css = read('vendor/leaflet/leaflet.css') + '\n' + read('css/app.css')
    leaflet = read('vendor/leaflet/leaflet.js')
    heat = read('vendor/leaflet/leaflet-heat.js')
    app = read('js/app.js')

    parts = []
    for key, rel in DATA:
        payload = json.loads(read(rel))
        parts.append('  %s: %s' % (key, json.dumps(payload, separators=(',', ':'), ensure_ascii=False)))
    data_js = 'window.__ATLAS__ = {\n' + ',\n'.join(parts) + '\n};'

    # Strip the external references (assert so a markup change cannot silently
    # leave the offline copy loading missing files).
    for needle in (
        '<link rel="stylesheet" href="vendor/leaflet/leaflet.css">',
        '<link rel="stylesheet" href="css/app.css">',
        '<script src="vendor/leaflet/leaflet.js"></script>',
        '<script src="vendor/leaflet/leaflet-heat.js"></script>',
        '<script src="js/app.js"></script>',
    ):
        if needle not in html:
            sys.exit('index.html no longer contains %r — update build_offline.py' % needle)
        html = html.replace(needle, '')

    html = html.replace(
        '<title>Khyber Pakhtunkhwa Security Atlas',
        '<title>Offline · Khyber Pakhtunkhwa Security Atlas'
    )
    html = html.replace(
        '<meta name="description"',
        '<meta name="offline-edition" content="single file, no server required">\n<meta name="description"'
    )
    html = html.replace('</head>', '<style>\n' + css + '\n</style>\n</head>')

    scripts = (
        '<script>\n' + guard(data_js) + '\n</script>\n'
        '<script>\n' + guard(leaflet) + '\n</script>\n'
        '<script>\n' + guard(heat) + '\n</script>\n'
        '<script>\n' + guard(app) + '\n</script>\n'
    )
    html = html.replace('</body>', scripts + '</body>')

    out = os.path.abspath(args.out)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    mb = os.path.getsize(out) / 1048576
    print('wrote %s (%.1f MB)' % (out, mb))
    if mb > 14:
        print('warning: large for a browser tab', file=sys.stderr)


if __name__ == '__main__':
    main()
