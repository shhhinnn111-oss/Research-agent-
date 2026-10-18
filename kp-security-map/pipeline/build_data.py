#!/usr/bin/env python3
"""Merge GTD + curated incidents, compute district-year aggregates, emit app data."""
import json, csv, re, collections, os, math, sys
from shapely.geometry import shape, Point

WORK = '/home/user/.cache/work'
OUT = '/home/user/Research-agent-/kp-security-map/data'
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, WORK)
from recent import RECENT

districts = json.load(open(f'{WORK}/out/kp_districts.geojson'))
DIST = {f['properties']['name']: f['properties'] for f in districts['features']}
DISPLAY_TO_NAME = {p['display']: n for n, p in DIST.items()}

HQ = {
 'Abbottabad':'Abbottabad','Bajaur':'Khar','Bannu':'Bannu','Batagram':'Battagram','Buner':'Daggar','Charsadda':'Charsadda',
 'Chitral Lower':'Chitral','Chitral Upper':'Mastuj','D. I. Khan':'Dera Ismail Khan','Hangu':'Hangu','Haripur':'Haripur',
 'Karak':'Karak','Khyber':'Landi Kotal','Kohat':'Kohat','Kohistan Lower':'Pattan','Kohistan Upper':'Dassu',
 'Kolai Palas Kohistan':'Kolai','Kurram':'Parachinar','Lakki Marwat':'Lakki Marwat','Lower Dir':'Timergara',
 'Malakand':'Batkhela','Mansehra':'Mansehra','Mardan':'Mardan','Mohmand':'Ghalanai','North Waziristan':'Miranshah',
 'Nowshera':'Nowshera','Orakzai':'Kalaya','Peshawar':'Peshawar','Shangla':'Alpuri','South Waziristan':'Wana',
 'Swabi':'Swabi','Swat':'Mingora','Tank':'Tank','Tor Ghar':'Judba','Upper Dir':'Dir',
}
for n, p in DIST.items():
    p['hq'] = HQ.get(n, p['display'])

# ---------------------------------------------------------------- GTD
inc = json.load(open(f'{WORK}/out/gtd_incidents.json'))
poly = {f['properties']['name']: shape(f['geometry']) for f in districts['features']}

def clean_text(s):
    s = (s or '').replace('\u201a\u00c4\u00f4', "'").replace('\u201a\u00c4\u00fa', '"')
    s = s.replace('\u00e2\u0080\u0099', "'").replace('â€™', "'").replace('â€œ', '"').replace('â€\x9d', '"')
    s = re.sub(r'[^\x00-\x7F]', '', s)
    return re.sub(r'\s+', ' ', s).strip()

for i in inc:
    i['summary'] = clean_text(i['summary'])[:260]
    if i['loc_quality'] == 'reported':
        pt = Point(i['lng'], i['lat'])
        if not poly[i['district']].contains(pt):
            i['lng'], i['lat'] = DIST[i['district']]['cx'], DIST[i['district']]['cy']
            i['loc_quality'] = 'district'
    # tags
    s = (i['summary'] + ' ' + i.get('target','')).lower()
    tags = []
    if i['suicide']: tags.append('suicide')
    if re.search(r'shia|sunni|sectarian|imambargah|ahmadi|christian|hindu|mosque|temple', s): tags.append('sectarian')
    if re.search(r'polio|vaccinat', s): tags.append('polio')
    if re.search(r'chinese|china', s): tags.append('chinese')
    if re.search(r'school|college|universit|student|education', s): tags.append('education')
    if re.search(r'market|bazaar|bazar|shop', s): tags.append('market')
    if i['killed'] == 0 and i['injured'] == 0: tags.append('no-casualty')
    i['tags'] = tags
    i['foiled'] = ('defused' in s or 'discovered' in s) and i['killed'] == 0 and i['injured'] == 0
    i['src_name'] = 'Global Terrorism Database (START, UMD)'
    i['url'] = ''

# ---------------------------------------------------------------- curated
def victim_class(target):
    t = (target or '').lower()
    if re.search(r'police|security|military|fc|army|soldier|forces', t): return 'security'
    if 'government' in t or 'official' in t or 'assistant commissioner' in t or 'customs' in t: return 'government'
    return 'civilian'

import zlib
seen_recent = set()
for (date, dist_display, place, lat, lng, cat, killed, injured, actor, target, tags, summary, src, url) in RECENT:
    name = dist_display if dist_display in DIST else DISPLAY_TO_NAME.get(dist_display, dist_display)
    assert name in DIST, (dist_display, name)
    key = (date, name, cat, killed, injured)
    if key in seen_recent:
        continue
    seen_recent.add(key)
    tag_list = [t.strip() for t in tags.split(',') if t.strip()]
    inc.append({
        'id': 'c' + date.replace('-', '') + str(zlib.crc32((place + str(killed)).encode()) % 1000).zfill(3),
        'date': date, 'year': int(date[:4]), 'district': name,
        'place': place, 'lat': lat, 'lng': lng, 'loc_quality': 'town',
        'cat': cat, 'killed': killed, 'injured': injured,
        'actor': actor, 'target': target, 'victims': victim_class(target),
        'suicide': cat == 'suicide', 'summary': clean_text(summary),
        'src': 'CURATED', 'src_name': src, 'url': url,
        'tags': tag_list, 'foiled': False,
    })

inc.sort(key=lambda x: x['date'])
print('total incidents', len(inc), collections.Counter(i['year'] for i in inc).most_common())

# ---------------------------------------------------------------- aggregates
YEARS = list(range(2004, 2027))
stats = {}
for n in DIST:
    stats[n] = {}
for i in inc:
    d = stats[i['district']]
    y = str(i['year'])
    s = d.setdefault(y, {'n': 0, 'k': 0, 'j': 0, 's': 0, 'sec': 0, 'civ': 0, 'sev': 0, 'cats': {}})
    s['n'] += 1
    s['k'] += i['killed']; s['j'] += i['injured']
    s['sev'] += i['killed'] * 3 + i['injured']
    if i['suicide']: s['s'] += 1
    if i['victims'] == 'security': s['sec'] += i['killed']
    elif i['victims'] == 'civilian': s['civ'] += i['killed']
    s['cats'][i['cat']] = s['cats'].get(i['cat'], 0) + 1

# ---------------------------------------------------------------- meta
SATP_YEARS = {
 2004:[41,35,31,93,9,168],2005:[56,38,36,72,10,156],2006:[95,177,117,172,16,482],2007:[281,482,314,854,272,1922],
 2008:[502,816,370,1563,325,3074],2009:[843,1120,494,4122,147,5883],2010:[260,355,101,498,215,1169],
 2011:[226,469,267,372,80,1188],2012:[192,326,97,191,30,644],2013:[225,586,181,172,7,946],
 2014:[183,352,108,104,43,607],2015:[105,115,81,100,2,298],2016:[93,122,49,40,4,215],
 2017:[42,39,26,64,0,129],2018:[42,80,52,34,1,167],2019:[61,30,69,31,0,130],
 2020:[78,61,57,98,0,216],2021:[130,72,108,121,0,301],2022:[184,119,173,235,0,527],
 2023:[312,205,329,407,0,941],2024:[487,284,421,654,4,1363],2025:[545,268,455,1636,0,2359],
 2026:[553,260,330,1275,0,1865],
}
satp = [{'year': y, 'incidents': v[0], 'civilians': v[1], 'security': v[2], 'militants': v[3], 'total': v[5]} for y, v in SATP_YEARS.items()]

ref_district = {
 '2021': {'North Waziristan': 106, 'South Waziristan': 51, 'Peshawar': 25, 'Bajaur': 22},
 '2022': {'North Waziristan': 177, 'Peshawar': 87, 'Bannu': 60, 'D. I. Khan': 43},
 '2023': {'North Waziristan': 151, 'Peshawar': 122, 'D. I. Khan': 109, 'South Waziristan': 107},
 '2024': {'North Waziristan': 271, 'South Waziristan': 163, 'Khyber': 137, 'Kurram': 126},
 '2025': {'North Waziristan': 498, 'D. I. Khan': 245, 'Bannu': 234, 'South Waziristan': 225},
}

meta = {
 'title': 'Khyber Pakhtunkhwa Security Atlas',
 'years': YEARS,
 'dataYears': {'gtd': [2004, 2020], 'curated': [2021, 2026]},
 'satp': satp,
 'satpRefDistrict': ref_district,
 'counts': {
    'total': len(inc),
    'gtd': sum(1 for i in inc if i['src'] == 'GTD'),
    'curated': sum(1 for i in inc if i['src'] == 'CURATED'),
    'unlocatedExcluded': 248,
 },
 'categories': [
   {'id':'suicide','label':'Suicide bombing','color':'#ff4d6d'},
   {'id':'ied','label':'Bomb / IED attack','color':'#ff9f1c'},
   {'id':'armed','label':'Armed attack / ambush','color':'#4cc9f0'},
   {'id':'targeted','label':'Targeted killing','color':'#f72585'},
   {'id':'kidnap','label':'Kidnapping','color':'#b5179e'},
   {'id':'rocket','label':'Rocket / mortar fire','color':'#ffd166'},
   {'id':'sabotage','label':'Sabotage / arson','color':'#8ac926'},
   {'id':'drone','label':'Drone attack','color':'#a78bfa'},
   {'id':'other','label':'Other / unclassified','color':'#9aa5b1'},
 ],
 'sources': [
   {'name':'Global Terrorism Database (GTD), START – University of Maryland','note':'Incident-level attack records, 2004–2020, via the Pakistan Terrorism Database extract (OSPK).','url':'https://www.start.umd.edu/gtd/'},
   {'name':'South Asia Terrorism Portal (SATP)','note':'Province and district fatality series; New Delhi. Data compiled to 14 Oct 2026.','url':'https://www.satp.org/datasheet-terrorist-attack/fatalities/pakistan-khyberpakhtunkhwa'},
   {'name':'Dawn, Reuters, AP, Al Jazeera, Express Tribune, Arab News, PBS','note':'Verification of curated major incidents 2021–2026.','url':''},
   {'name':'Wikipedia – Terrorist incidents in Pakistan (annual lists)','note':'Cross-checking of recent incidents and casualty tolls.','url':'https://en.wikipedia.org/wiki/Terrorist_incidents_in_Pakistan_in_2025'},
   {'name':'PIPS / PICSS security reports; KP CTD & KP Police annual data','note':'Contextual totals for 2024–2026.','url':'https://pakpips.com/'},
 ],
 'notes': [
   'The map combines two datasets: the GTD incident-level attack record (2004–2020) and a curated set of major attacks and terrorism-related incidents (2021–2026). Coverage is therefore not uniform across years.',
   'Recent years (2021–2026) include major, publicly verified attacks; they are a subset of all reported incidents. SATP counts for the same years include militants killed in security-force operations and are shown as a reference series only.',
   'District shading aggregates the incidents available in this dataset. Where a district shows little activity in recent years it may reflect lower coverage, not necessarily lower violence; SATP district totals are noted in the district panel where published.',
   'Attack locations are approximate (town or district level) and are not a precise geolocation of each event. Residential areas are never plotted at street level.',
   'The seven districts of the former Federally Administered Tribal Areas (FATA) were merged into Khyber Pakhtunkhwa in 2018 and are flagged throughout the map.',
   'Casualty figures are the most widely cited figures at the time of compilation and may differ from later official revisions. Attackers killed are excluded from victim tolls where reported separately.',
 ],
}

# ---------------------------------------------------------------- write
json.dump(inc, open(f'{OUT}/incidents.json', 'w'), separators=(',', ':'))
json.dump(stats, open(f'{OUT}/district_stats.json', 'w'), separators=(',', ':'))
json.dump(meta, open(f'{OUT}/meta.json', 'w'), separators=(',', ':'))
json.dump(districts, open(f'{OUT}/kp_districts.geojson', 'w'), separators=(',', ':'))
json.dump(json.load(open(f'{WORK}/out/kp_outline.geojson')), open(f'{OUT}/kp_outline.geojson', 'w'), separators=(',', ':'))
json.dump(json.load(open(f'{WORK}/out/neighbours.geojson')), open(f'{OUT}/neighbours.geojson', 'w'), separators=(',', ':'))

# CSV export for researchers
cols = ['id','date','year','district','place','lat','lng','loc_quality','cat','killed','injured','actor','target','victims','suicide','tags','summary','src','src_name','url']
with open(f'{OUT}/kp_incidents.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
    w.writeheader()
    for i in inc:
        row = dict(i); row['tags'] = ';'.join(i['tags']); w.writerow(row)

for fn in ['incidents.json','district_stats.json','meta.json','kp_districts.geojson','kp_outline.geojson','neighbours.geojson','kp_incidents.csv']:
    print(fn, os.path.getsize(f'{OUT}/{fn}')//1024, 'KB')
print('by district', collections.Counter(i['district'] for i in inc).most_common(10))
print('killed total', sum(i['killed'] for i in inc), 'injured', sum(i['injured'] for i in inc))
