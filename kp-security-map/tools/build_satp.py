#!/usr/bin/env python3
"""Build data/satp.json — the bundled SATP snapshot that ships with the atlas.

The tables below were transcribed from the nine SATP Khyber Pakhtunkhwa
datasheets on 18 October 2026 (data current to 14 October 2026).  Rerun
`python3 serve.py --refresh` (or press "Sync SATP" in the app) to replace this
snapshot with a live download.

Every dataset is keyed by year and carries the exact published columns.
"""
import json, os, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AS_OF = '2026-10-14'
BASE = 'https://www.satp.org/datasheet-terrorist-attack/'

SOURCE = {
    'fatalities': BASE + 'fatalities/pakistan-khyberpakhtunkhwa',
    'incidents': BASE + 'incidents-data/pakistan-khyberpakhtunkhwa',
    'major': BASE + 'major-incidents/pakistan-khyberpakhtunkhwa',
    'suicide': BASE + 'suicide-attacks/pakistan-khyberpakhtunkhwa',
    'explosions': BASE + 'explosions/pakistan-khyberpakhtunkhwa',
    'arrests': BASE + 'arrest/pakistan-khyberpakhtunkhwa',
    'arms': BASE + 'recovery-of-arms/pakistan-khyberpakhtunkhwa',
    'surrender': BASE + 'surrender/pakistan-khyberpakhtunkhwa',
    'other': BASE + 'other-data/pakistan-khyberpakhtunkhwa',
    'districts': 'https://www.satp.org/datasheet/district/pakistan-khyberpakhtunkhwa',
}

# year, incidents of killing, civilians, security forces, militants, not specified, total
FATALITIES = [
    (2000, 9, 28, 0, 1, 0, 29), (2001, 9, 17, 4, 0, 30, 51), (2002, 8, 8, 12, 6, 2, 28),
    (2003, 5, 5, 3, 12, 0, 20), (2004, 41, 35, 31, 93, 9, 168), (2005, 56, 38, 36, 72, 10, 156),
    (2006, 95, 177, 117, 172, 16, 482), (2007, 281, 482, 314, 854, 272, 1922),
    (2008, 502, 816, 370, 1563, 325, 3074), (2009, 843, 1120, 494, 4122, 147, 5883),
    (2010, 260, 355, 101, 498, 215, 1169), (2011, 226, 469, 267, 372, 80, 1188),
    (2012, 192, 326, 97, 191, 30, 644), (2013, 225, 586, 181, 172, 7, 946),
    (2014, 183, 352, 108, 104, 43, 607), (2015, 105, 115, 81, 100, 2, 298),
    (2016, 93, 122, 49, 40, 4, 215), (2017, 42, 39, 26, 64, 0, 129),
    (2018, 42, 80, 52, 34, 1, 167), (2019, 61, 30, 69, 31, 0, 130),
    (2020, 78, 61, 57, 98, 0, 216), (2021, 130, 72, 108, 121, 0, 301),
    (2022, 184, 119, 173, 235, 0, 527), (2023, 312, 205, 329, 407, 0, 941),
    (2024, 487, 284, 421, 654, 4, 1363), (2025, 545, 268, 455, 1636, 0, 2359),
    (2026, 553, 260, 330, 1275, 0, 1865),
]

# year, terrorism related incidents
INCIDENTS = [
    (2000, 14), (2001, 31), (2002, 57), (2003, 33), (2004, 115), (2005, 133), (2006, 190),
    (2007, 636), (2008, 1012), (2009, 1432), (2010, 533), (2011, 506), (2012, 517),
    (2013, 504), (2014, 356), (2015, 278), (2016, 205), (2017, 86), (2018, 73), (2019, 105),
    (2020, 99), (2021, 169), (2022, 225), (2023, 472), (2024, 702), (2025, 766), (2026, 855),
]

# year, incidents, killed, injured
MAJOR = [
    (2000, 5, 24, 27), (2001, 2, 12, 1), (2002, 3, 22, 11), (2003, 3, 20, 6),
    (2004, 15, 134, 89), (2005, 16, 121, 52), (2006, 33, 427, 170), (2007, 127, 1556, 976),
    (2008, 212, 2496, 1416), (2009, 341, 4116, 2440), (2010, 102, 916, 1048),
    (2011, 85, 983, 917), (2012, 60, 444, 452), (2013, 72, 721, 1107), (2014, 47, 428, 403),
    (2015, 21, 180, 134), (2016, 19, 130, 143), (2017, 19, 94, 70), (2018, 12, 114, 123),
    (2019, 18, 73, 79), (2020, 28, 145, 152), (2021, 41, 186, 25), (2022, 56, 337, 230),
    (2023, 84, 598, 565), (2024, 140, 891, 356), (2025, 245, 1913, 540), (2026, 209, 1463, 545),
]

# year, incidents, killed, injured  (+ victim split from the published table)
SUICIDE = [
    (2005, 0, 0, 1), (2006, 5, 98, 98), (2007, 35, 366, 450), (2008, 37, 415, 701),
    (2009, 54, 661, 1506), (2010, 42, 562, 872), (2011, 24, 422, 614), (2012, 18, 127, 205),
    (2013, 20, 336, 624), (2014, 14, 207, 152), (2015, 6, 37, 64), (2016, 6, 62, 129),
    (2017, 8, 40, 84), (2018, 5, 72, 108), (2019, 1, 8, 30), (2020, 1, 1, 3), (2021, 2, 16, 4),
    (2022, 8, 87, 206), (2023, 28, 254, 461), (2024, 15, 93, 44), (2025, 18, 151, 110),
    (2026, 13, 91, 136),
]
SUICIDE_SPLIT = {  # year: [civ killed, sf killed, militant killed, ns killed, civ hurt, sf hurt, mil hurt, ns hurt]
    2005: [0, 0, 0, 0, 1, 0, 0, 0], 2006: [40, 53, 5, 0, 50, 48, 0, 0],
    2007: [230, 96, 37, 3, 330, 57, 0, 63], 2008: [276, 56, 36, 47, 530, 65, 9, 97],
    2009: [380, 144, 62, 75, 1072, 234, 6, 194], 2010: [230, 62, 46, 224, 433, 74, 0, 365],
    2011: [255, 105, 23, 39, 484, 32, 0, 98], 2012: [83, 17, 24, 3, 179, 17, 0, 9],
    2013: [262, 23, 51, 0, 600, 24, 0, 0], 2014: [166, 10, 20, 11, 87, 16, 0, 49],
    2015: [22, 4, 11, 0, 57, 7, 0, 0], 2016: [46, 5, 11, 0, 126, 3, 0, 0],
    2017: [17, 8, 15, 0, 62, 22, 0, 0], 2018: [56, 11, 4, 1, 81, 13, 0, 14],
    2019: [3, 4, 1, 0, 30, 0, 0, 0], 2020: [0, 0, 1, 0, 0, 3, 0, 0],
    2021: [12, 2, 2, 0, 4, 0, 0, 0], 2022: [71, 8, 8, 0, 202, 4, 0, 0],
    2023: [58, 142, 54, 0, 156, 85, 0, 220], 2024: [12, 41, 40, 0, 2, 37, 5, 0],
    2025: [26, 34, 91, 0, 56, 54, 0, 0], 2026: [40, 36, 15, 0, 125, 11, 0, 0],
}

# year, incidents, killed, injured  (+ victim split)
EXPLOSIONS = [
    (2000, 7, 26, 32), (2001, 3, 2, 18), (2002, 10, 9, 40), (2003, 5, 4, 14),
    (2004, 51, 58, 169), (2005, 42, 84, 122), (2006, 84, 149, 238), (2007, 330, 819, 1231),
    (2008, 353, 960, 1485), (2009, 278, 1560, 2432), (2010, 136, 609, 1172),
    (2011, 205, 524, 955), (2012, 186, 248, 719), (2013, 198, 628, 1397),
    (2014, 102, 217, 510), (2015, 50, 91, 183), (2016, 35, 78, 231), (2017, 24, 44, 145),
    (2018, 25, 76, 185), (2019, 32, 41, 118), (2020, 25, 45, 184), (2021, 33, 53, 60),
    (2022, 45, 129, 269), (2023, 110, 296, 589), (2024, 142, 207, 309), (2025, 159, 327, 421),
    (2026, 163, 246, 508),
]
EXPLOSION_SPLIT = {
    2000: [21, 0, 5, 0, 32, 0, 0, 0], 2001: [2, 0, 0, 0, 8, 0, 0, 10],
    2002: [7, 0, 0, 2, 28, 0, 0, 12], 2003: [4, 0, 0, 0, 14, 0, 0, 0],
    2004: [24, 19, 12, 3, 100, 60, 0, 9], 2005: [23, 14, 45, 2, 60, 54, 0, 8],
    2006: [57, 82, 9, 1, 132, 101, 2, 3], 2007: [320, 181, 213, 105, 592, 335, 92, 212],
    2008: [460, 142, 210, 148, 991, 238, 46, 210], 2009: [671, 249, 540, 100, 1711, 447, 23, 251],
    2010: [255, 67, 39, 248, 662, 99, 0, 411], 2011: [313, 131, 22, 58, 671, 98, 0, 186],
    2012: [168, 35, 42, 3, 557, 125, 14, 23], 2013: [471, 86, 69, 2, 1302, 85, 0, 10],
    2014: [118, 55, 15, 29, 290, 103, 0, 117], 2015: [64, 9, 18, 0, 148, 35, 0, 0],
    2016: [57, 13, 8, 0, 161, 45, 0, 25], 2017: [22, 8, 14, 0, 118, 27, 0, 0],
    2018: [62, 10, 3, 1, 140, 30, 1, 14], 2019: [14, 25, 2, 0, 80, 37, 0, 1],
    2020: [27, 17, 1, 0, 162, 22, 0, 0], 2021: [32, 18, 3, 0, 29, 31, 0, 0],
    2022: [87, 27, 15, 0, 227, 37, 5, 0], 2023: [95, 161, 40, 0, 239, 130, 0, 220],
    2024: [60, 87, 60, 0, 122, 179, 7, 1], 2025: [87, 78, 162, 0, 220, 183, 18, 0],
    2026: [100, 110, 36, 0, 299, 206, 3, 0],
}

# year, incidents, arrests
ARRESTS = [
    (2000, 2, 4), (2001, 15, 105), (2002, 36, 972), (2003, 21, 226), (2004, 30, 169),
    (2005, 45, 222), (2006, 21, 94), (2007, 68, 384), (2008, 137, 1321), (2009, 492, 3106),
    (2010, 159, 3740), (2011, 63, 237), (2012, 85, 687), (2013, 77, 1354), (2014, 63, 458),
    (2015, 124, 3093), (2016, 84, 1076), (2017, 26, 138), (2018, 8, 58), (2019, 18, 164),
    (2020, 9, 32), (2021, 19, 39), (2022, 13, 29), (2023, 30, 97), (2024, 15, 49),
    (2025, 15, 94), (2026, 18, 50),
]

# year, incident(s) of recovery
ARMS = [(2000, 2), (2001, 10), (2002, 23), (2003, 6), (2004, 12), (2005, 22), (2006, 8),
        (2007, 48), (2008, 89), (2009, 193), (2010, 104), (2011, 65), (2012, 95), (2013, 89),
        (2014, 58), (2015, 80), (2016, 63), (2017, 26), (2018, 6), (2019, 22), (2020, 18),
        (2021, 33), (2022, 51), (2023, 92), (2024, 61), (2025, 72), (2026, 91)]

# year, incidents, persons surrendered
SURRENDER = [(2004, 4, 9), (2007, 1, 40), (2008, 13, 316), (2009, 117, 719), (2010, 19, 311),
             (2011, 1, 1), (2012, 2, 11), (2017, 1, 1), (2018, 1, 1), (2022, 2, 8), (2023, 2, 5)]

# other-data is a catalogue of ~100 sub-datasheets rather than a series
OTHER_HIGHLIGHTS = [
    ('Attacks on Police Personnel', 'security-force-data-details/Police'),
    ('Attacks on Army Personnel', 'security-force-data-details/Attacks-on-Army-Personnel'),
    ('Attacks on Police Check-posts', 'type-of-attack/Attacks-on-Police-Check-posts'),
    ('Attacks on Police Stations', 'type-of-attack/Attacks-on-Police-Stations'),
    ('Attacks on Military Check-posts', 'type-of-attack/Attacks-on-Military-Check-posts'),
    ('Attacks on Mosques', 'type-of-attack/Attacks-on-Mosque'),
    ('Attacks on Shias', 'civilian-data-details/Shia'),
    ('Attacks on Christians', 'civilian-data-details/Christians'),
    ('Attacks on Hindus', 'civilian-data-details/Hindus'),
    ('Attacks on Hazaras', 'civilian-data-details/Hazaras'),
    ('Attacks on Educational Institutions', 'type-of-attack/Attacks-on-Schools'),
    ('Attacks on Polio Workers', 'civilian-data-details/Attack-on-Polio-workers'),
    ('Attacks on Foreigners', 'civilian-data-details/Attack-on-Foreigners'),
    ('Attacks on Journalists', 'civilian-data-details/Journalist'),
    ('Attacks on Banks/Robbery', 'type-of-attack/Attacks-on-Banks'),
    ('Attacks on Gas Pipelines', 'type-of-attack/Attack-on-Gas-Pipelines'),
]


def main():
    out = {
        'source': 'South Asia Terrorism Portal (SATP)',
        'source_short': 'SATP',
        'province': 'Khyber Pakhtunkhwa',
        'as_of': AS_OF,
        'fetched_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'fetched_by': 'bundled snapshot',
        'source_urls': SOURCE,
        'districts': {},
        'province_data': {
            'fatalities': [
                dict(year=y, incidents=n, civilians=c, security=s, militants=m, ns=ns, total=t)
                for (y, n, c, s, m, ns, t) in FATALITIES
            ],
            'incidents': [dict(year=y, incidents=n) for (y, n) in INCIDENTS],
            'major': [dict(year=y, incidents=n, killed=k, injured=j) for (y, n, k, j) in MAJOR],
            'suicide': [
                dict(year=y, incidents=n, killed=k, injured=j,
                     killed_civ=c[0], killed_sf=c[1], killed_mil=c[2], killed_ns=c[3],
                     injured_civ=c[4], injured_sf=c[5], injured_mil=c[6], injured_ns=c[7])
                for (y, n, k, j), c in zip(SUICIDE, (SUICIDE_SPLIT[y] for y, *_ in SUICIDE))
            ],
            'explosions': [
                dict(year=y, incidents=n, killed=k, injured=j,
                     killed_civ=c[0], killed_sf=c[1], killed_mil=c[2], killed_ns=c[3],
                     injured_civ=c[4], injured_sf=c[5], injured_mil=c[6], injured_ns=c[7])
                for (y, n, k, j), c in zip(EXPLOSIONS, (EXPLOSION_SPLIT[y] for y, *_ in EXPLOSIONS))
            ],
            'arrests': [dict(year=y, incidents=n, arrested=a) for (y, n, a) in ARRESTS],
            'arms': [dict(year=y, recoveries=n) for (y, n) in ARMS],
            'surrender': [dict(year=y, incidents=n, surrendered=s) for (y, n, s) in SURRENDER],
            'other': [
                dict(name=name, url='https://www.satp.org/' + path + '/pakistan-khyberpakhtunkhwa')
                for name, path in OTHER_HIGHLIGHTS
            ],
        },
    }
    os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
    path = os.path.join(ROOT, 'data', 'satp.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print('wrote', path, os.path.getsize(path) // 1024, 'KB')


if __name__ == '__main__':
    main()
