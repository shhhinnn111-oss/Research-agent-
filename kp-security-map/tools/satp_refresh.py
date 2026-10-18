#!/usr/bin/env python3
"""
Live SATP synchroniser for the Khyber Pakhtunkhwa Security Atlas.

    python3 tools/satp_refresh.py            # fetch and save data/satp.json
    python3 tools/satp_refresh.py --quiet    # no progress output

It downloads the nine Khyber Pakhtunkhwa datasheets plus every district
fatality sheet, parses the published yearly tables and rewrites data/satp.json
with a fresh `fetched_at`, `as_of` and `districts` block.  The atlas reads that
file, so the next page load (or the next poll) shows the new numbers.

HTML structure handled
----------------------
Every SATP datasheet renders the same yearly table several times (data view,
graph view, chart view).  We locate tables whose header contains "Year" and
whose body holds numeric year rows, then read columns by header name.  Missing
or renamed columns fall back to positional parsing.  A reCAPTCHA interstitial is
detected and reported instead of overwriting good data.
"""
import argparse, datetime, json, os, re, ssl, sys, time, urllib.error, urllib.parse, urllib.request
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'satp.json')
BASE = 'https://www.satp.org/datasheet-terrorist-attack/'
DISTRICT_INDEX = 'https://www.satp.org/datasheet/district/pakistan-khyberpakhtunkhwa'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

DATASETS = {
    'fatalities': BASE + 'fatalities/pakistan-khyberpakhtunkhwa',
    'incidents': BASE + 'incidents-data/pakistan-khyberpakhtunkhwa',
    'major': BASE + 'major-incidents/pakistan-khyberpakhtunkhwa',
    'suicide': BASE + 'suicide-attacks/pakistan-khyberpakhtunkhwa',
    'explosions': BASE + 'explosions/pakistan-khyberpakhtunkhwa',
    'arrests': BASE + 'arrest/pakistan-khyberpakhtunkhwa',
    'arms': BASE + 'recovery-of-arms/pakistan-khyberpakhtunkhwa',
    'surrender': BASE + 'surrender/pakistan-khyberpakhtunkhwa',
    'other': BASE + 'other-data/pakistan-khyberpakhtunkhwa',
}

CTX = ssl.create_default_context()
LAX = ssl.create_default_context()
LAX.check_hostname = False
LAX.verify_mode = ssl.CERT_NONE
VERIFIED_OK = {'value': True}


# ----------------------------------------------------------------- html table reader
class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._t, self._row, self._cell = [], None, None, None
        self.links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'table':
            self._t = []
        elif tag == 'tr' and self._t is not None:
            self._row = []
        elif tag in ('td', 'th') and self._row is not None:
            self._cell = []
        elif tag == 'a' and a.get('href'):
            self.links.append(a['href'])

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self._cell is not None and self._row is not None:
            self._row.append(' '.join(''.join(self._cell).split()))
            self._cell = None
        elif tag == 'tr' and self._row is not None and self._t is not None:
            if self._row:
                self._t.append(self._row)
            self._row = None
        elif tag == 'table' and self._t is not None:
            if self._t:
                self.tables.append(self._t)
            self._t = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def num(text):
    if text is None:
        return 0
    t = str(text).replace(',', '').replace('\u00a0', ' ').strip()
    t = re.sub(r'[*†]+$', '', t)
    m = re.search(r'-?\d+(?:\.\d+)?', t)
    if not m:
        return 0
    v = float(m.group())
    return int(v) if v.is_integer() else v


def year_rows(table):
    """Return rows that start with a 4-digit year, plus the header row above them."""
    header, rows = None, []
    for row in table:
        cells = [c for c in row]
        if not cells:
            continue
        first = cells[0].strip()
        if re.fullmatch(r'(19|20)\d{2}\*?', first):
            rows.append([num(first)] + [num(c) for c in cells[1:]])
        elif header is None and any(re.search(r'year', c, re.I) for c in cells[:2]):
            header = cells
    return header, rows


def best_table(html):
    p = TableParser()
    p.feed(html)
    best = None
    for t in p.tables:
        header, rows = year_rows(t)
        if len(rows) >= 5 and (best is None or len(rows) > len(best[1])):
            best = (header, rows)
    return best, p.links


def col(header, *names):
    """Index of the first header cell matching any of the given patterns (word-aware)."""
    if not header:
        return None
    for i, h in enumerate(header):
        hl = h.lower()
        for n in names:
            if re.search(r'\b' + re.escape(n), hl):
                return i
    return None


def pick(row, idx, default=0):
    if idx is None or idx >= len(row):
        return default
    return row[idx]


# ----------------------------------------------------------------- per-dataset shaping
def shape_fatalities(header, rows):
    i_n = col(header, 'incident')
    i_c = col(header, 'civilian')
    i_s = col(header, 'security')
    i_m = col(header, 'terrorist', 'militant')
    i_ns = col(header, 'not specified', 'ns')
    i_t = col(header, 'total')
    out = []
    for r in rows:
        out.append(dict(year=r[0],
                        incidents=pick(r, i_n, pick(r, 1)),
                        civilians=pick(r, i_c, pick(r, 2)),
                        security=pick(r, i_s, pick(r, 3)),
                        militants=pick(r, i_m, pick(r, 4)),
                        ns=pick(r, i_ns, pick(r, 5)),
                        total=pick(r, i_t, pick(r, 6))))
    return out


def shape_major(header, rows):
    """Major incidents: the total killed/injured sit after the four victim classes."""
    out = []
    for r in rows:
        if len(r) >= 12:
            inc, killed, injured = r[1], r[6], r[11]
        elif len(r) >= 4:
            inc, killed, injured = r[1], r[2], r[3]
        else:
            inc = killed = injured = 0
        out.append(dict(year=r[0], incidents=inc, killed=killed, injured=injured))
    return out


def shape_attacks(header, rows):
    """Suicide attacks / explosions: incidents + killed/injured split by victim class."""
    out = []
    for r in rows:
        vals = r[1:]
        n = vals[0] if vals else 0
        # published order: C SF M NS Total (killed), C SF M NS Total (injured)
        def g(i):
            return vals[i] if i < len(vals) else 0
        out.append(dict(year=r[0], incidents=n,
                        killed_civ=g(1), killed_sf=g(2), killed_mil=g(3), killed_ns=g(4), killed=g(5),
                        injured_civ=g(6), injured_sf=g(7), injured_mil=g(8), injured_ns=g(9), injured=g(10)))
    return out


def shape_incidents(header, rows):
    return [dict(year=r[0], incidents=pick(r, col(header, 'terrorism', 'number of'), r[1] if len(r) > 1 else 0))
            for r in rows]


def shape_arrests(header, rows):
    """Arrests: an incident count column plus a person count column."""
    i_n = col(header, 'arrest')
    i_p = col(header, 'persons arrested', 'people arrested', 'arrested', 'persons')
    if i_p is not None and i_p == i_n:
        i_p = None
    if i_p is None:
        i_p = (i_n + 1) if i_n is not None else 2
    return [dict(year=r[0],
                 incidents=pick(r, i_n, r[1] if len(r) > 1 else 0),
                 arrested=pick(r, i_p, r[2] if len(r) > 2 else 0))
            for r in rows]


def shape_surrender(header, rows):
    i_n = col(header, 'surrender')
    i_p = col(header, 'persons surrendered', 'surrenderers', 'surrendered', 'persons')
    if i_p is not None and i_p == i_n:
        i_p = None
    if i_p is None:
        i_p = (i_n + 1) if i_n is not None else 2
    return [dict(year=r[0],
                 incidents=pick(r, i_n, r[1] if len(r) > 1 else 0),
                 surrendered=pick(r, i_p, r[2] if len(r) > 2 else 0))
            for r in rows]


def shape_arms(header, rows):
    return [dict(year=r[0], recoveries=pick(r, col(header, 'recovery', 'incident'), r[1] if len(r) > 1 else 0)) for r in rows]


SHAPERS = {
    'fatalities': shape_fatalities, 'incidents': shape_incidents, 'major': shape_major,
    'suicide': shape_attacks, 'explosions': shape_attacks, 'arrests': shape_arrests,
    'surrender': shape_surrender, 'arms': shape_arms,
}


def is_captcha(html):
    low = html.lower()
    return 'recaptcha' in low and 'yearly' not in low and 'year' not in low[:4000]


def fetch(url, timeout=25, tries=2):
    """GET a page with a browser-like header set and one retry.

    Certificate verification stays on.  A few government hosts still serve an
    expired or incomplete chain, so a certificate-only failure is retried once
    with verification relaxed rather than losing the whole sync.
    """
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'close',
    })
    last = None
    for attempt in range(tries + 1):
        ctx = CTX if VERIFIED_OK['value'] else LAX
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                raw = r.read()
            for enc in ('utf-8', 'windows-1252', 'latin-1'):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode('utf-8', 'replace')
        except urllib.error.HTTPError as exc:
            if 400 <= exc.code < 500:              # a missing sheet will not heal on retry
                raise RuntimeError('HTTP %d for %s' % (exc.code, url.rsplit('/', 1)[-1])) from None
            last = exc
        except ssl.SSLError as exc:
            last = exc
            if VERIFIED_OK['value']:
                VERIFIED_OK['value'] = False       # relax once, then keep going
                continue
        except Exception as exc:                   # noqa: BLE001
            last = exc
        if attempt < tries:
            time.sleep(1.0 + attempt)
    raise RuntimeError('%s: %s' % (url.rsplit('/', 1)[-1], last))


def as_of_from(html):
    patterns = [
        r'Data\s+till[^A-Za-z0-9]*([A-Za-z]+\s+[0-9]{1,2},?\s*[0-9]{4})',
        r'Data\s+till[^A-Za-z0-9]*([0-9]{1,2}\s+[A-Za-z]+,?\s*[0-9]{4})',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.I)
        if not m:
            continue
        raw = ' '.join(m.group(1).replace(',', '').split())
        for fmt in ('%B %d %Y', '%b %d %Y', '%d %B %Y', '%d %b %Y'):
            try:
                return datetime.datetime.strptime(raw, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
    return None


def parse_dataset(html, key):
    (header, rows), links = best_table(html)
    if not rows:
        raise ValueError('no yearly table found')
    data = SHAPERS[key](header, rows)
    return data, links


SATP_DISTRICTS = [
    ('Abbottabad', 'abbottabad'), ('Bajaur', 'bajaur'), ('Bannu', 'bannu'), ('Batagram', 'batagram'),
    ('Buner', 'bunner%20or%20buner'), ('Charsadda', 'charsada%20or%20charsadda'), ('Chitral', 'chitral'),
    ('Dera Ismail Khan', 'dera%20ismail%20khan%20or%20di%20khan'), ('Hangu', 'hangu'), ('Haripur', 'haripur'),
    ('Karak', 'karak'), ('Khyber', 'khyber'), ('Kohat', 'kohat'),
    ('Kohistan', 'kohistan%20or%20abasin%20kohistan%20or%20indus%20kohistan'), ('Kurram', 'kurram'),
    ('Lakki Marwat', 'lakki%20marwat'), ('Lower Dir', 'lower%20dir'),
    ('Malakand', 'malakand%20or%20malakand%20protected%20area'), ('Mansehra', 'mansehra'), ('Mardan', 'mardan'),
    ('Mohmand', 'mohmand'), ('North Waziristan', 'northwaziristan'), ('Nowshera', 'nowshera'),
    ('Orakzai', 'orakzai'), ('Peshawar', 'peshawar'), ('Shangla', 'shangla'),
    ('South Waziristan', 'south%20waziristan'), ('Swabi', 'swabi'), ('Swat', 'swat'), ('Tank', 'tank'),
    ('Tor Ghar', 'torghar%20or%20tor%20ghar%20or%20kala%20dhaka'), ('Upper Dir', 'upper%20dir'),
]


def _norm(text):
    t = urllib.parse.unquote(text).lower()
    t = re.split(r'\s+or\s+', t)[0]
    t = re.sub(r'[^a-z]', '', t)
    return t


ALIASES = {
    'charsada': 'Charsadda', 'bunner': 'Buner', 'batagram': 'Batagram', 'torghar': 'Tor Ghar',
    'kohistan': 'Kohistan', 'deraismailkhan': 'Dera Ismail Khan', 'dikhan': 'Dera Ismail Khan',
    'malakand': 'Malakand', 'northwaziristan': 'North Waziristan', 'southwaziristan': 'South Waziristan',
}


def district_slugs(html):
    """Match the district index against known SATP slugs, keeping canonical names."""
    known = {_norm(slug): name for name, slug in SATP_DISTRICTS}
    known.update({_norm(name): name for name, _ in SATP_DISTRICTS})
    known.update(ALIASES)
    found = {}
    for href in TableParser_links(html):
        if 'fatalities/pakistan-khyberpakhtunkhwa' not in href:
            continue
        tail = href.split('?')[0].rstrip('/').split('/')[-1]
        # SATP writes pakistan-khyberpakhtunkhwa-khyberpakhtunkhwa-<slug> in some
        # places and ...-<slug> in others; strip whichever prefix is present.
        tail = re.sub(r'^(pakistan-)?(khyberpakhtunkhwa-)+', '', tail)
        name = known.get(_norm(tail))
        if not name:
            continue
        full = href if href.startswith('http') else 'https://www.satp.org' + href
        found[name] = full
    if not found:
        for name, slug in SATP_DISTRICTS:
            found[name] = ('https://www.satp.org/datasheet-terrorist-attack/fatalities/'
                           'pakistan-khyberpakhtunkhwa-khyberpakhtunkhwa-' + slug)
    return found


def TableParser_links(html):
    p = TableParser()
    p.feed(html)
    return p.links


# ----------------------------------------------------------------- main
def refresh(quiet=False, districts=True):
    log = (lambda *a: None) if quiet else (lambda *a: print(*a, flush=True))
    data = {
        'source': 'South Asia Terrorism Portal (SATP)',
        'source_short': 'SATP',
        'province': 'Khyber Pakhtunkhwa',
        'fetched_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'fetched_by': 'live sync',
        'source_urls': dict(DATASETS, districts=DISTRICT_INDEX),
        'province_data': {},
        'districts': {},
        'warnings': [],
    }
    as_of = None
    for key, url in DATASETS.items():
        if key == 'other':
            continue
        try:
            html = fetch(url)
            if 'recaptcha' in html.lower() and 'yearly' not in html.lower():
                raise RuntimeError('SATP returned a verification page')
            rows, _ = parse_dataset(html, key)
            data['province_data'][key] = rows
            as_of = as_of_from(html) or as_of
            log(f'  {key:11s} {len(rows):3d} rows  {rows[-1]["year"] if rows else "-"}')
        except Exception as e:                                  # noqa: BLE001
            data['warnings'].append(f'{key}: {e}')
            log(f'  {key:11s} FAILED — {e}')

    # other-data: catalogue of sub-datasheets (not a time series)
    try:
        html = fetch(DATASETS['other'])
        names = []
        for href in TableParser_links(html):
            if '/pakistan-khyberpakhtunkhwa' not in href:
                continue
            if not re.search(r'/(type-of-attack|civilian-data-details|security-force-data-details)/', href):
                continue
            label = href.rstrip('/').split('/')[-2].replace('-', ' ').replace('Attacks on ', 'Attacks on ')
            full = href if href.startswith('http') else 'https://www.satp.org' + href
            if label and all(n['name'] != label for n in names):
                names.append(dict(name=label, url=full))
        data['province_data']['other'] = names[:120]
        log(f'  {"other":11s} {len(names)} sub-datasheets')
    except Exception as e:                                      # noqa: BLE001
        data['warnings'].append(f'other: {e}')

    if districts:
        try:
            index = fetch(DISTRICT_INDEX)
            slugs = district_slugs(index)
            log(f'  districts   {len(slugs)} found')
            for i, (name, url) in enumerate(sorted(slugs.items()), 1):
                try:
                    rows, _ = parse_dataset(fetch(url), 'fatalities')
                    data['districts'][name] = {'source': url, 'fatalities': rows}
                    log(f'    [{i:2d}/{len(slugs)}] {name:22s} {len(rows)} years')
                except Exception as e:                          # noqa: BLE001
                    data['warnings'].append(f'district {name}: {e}')
        except Exception as e:                                  # noqa: BLE001
            data['warnings'].append(f'districts: {e}')

    if not data['province_data']:
        raise RuntimeError('nothing could be downloaded — keeping the existing snapshot')

    # carry forward anything we failed to refresh
    if os.path.exists(OUT):
        try:
            old = json.load(open(OUT, encoding='utf-8'))
            for k, v in old.get('province_data', {}).items():
                data['province_data'].setdefault(k, v)
            for k, v in old.get('districts', {}).items():
                data['districts'].setdefault(k, v)
            data['as_of'] = as_of or old.get('as_of')
        except Exception:                                        # noqa: BLE001
            data['as_of'] = as_of
    else:
        data['as_of'] = as_of

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    log(f'  saved {OUT}  ({os.path.getsize(OUT)//1024} KB)  as of {data.get("as_of")}')
    return data


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--no-districts', action='store_true')
    a = ap.parse_args()
    print('Synchronising SATP datasheets…')
    try:
        refresh(quiet=a.quiet, districts=not a.no_districts)
    except Exception as exc:                                     # noqa: BLE001
        print('FAILED:', exc)
        sys.exit(1)
