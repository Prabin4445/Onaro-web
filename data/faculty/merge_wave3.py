#!/usr/bin/env python3
"""Wave 3 merge: validate worker files, rename to canonical slugs, update index.json,
ATTRIBUTION.txt, master-list.json statuses (coordinator-only)."""
import json, os, shutil, datetime

FAC = os.path.expanduser('~/workspace/hub/data/faculty')
TODAY = '2026-09-23'

# file-on-disk -> canonical master-list slug
RENAME = {
    'university-of-melbourne.json': 'the-university-of-melbourne',
    'university-of-sydney.json': 'the-university-of-sydney',
    'unsw.json': 'the-university-of-new-south-wales',
    'university-of-queensland.json': 'the-university-of-queensland',
}
# manifest slug -> (canonical slug, batch, country)
LANDED = [
    ('australian-national-university', 'wave3-au0', 'AU'),
    ('university-of-melbourne', 'wave3-au0', 'AU'),
    ('university-of-sydney', 'wave3-au0', 'AU'),
    ('unsw', 'wave3-au0', 'AU'),
    ('university-of-queensland', 'wave3-au0', 'AU'),
    ('adelaide-university', 'wave3-au0', 'AU'),
    ('curtin-university', 'wave3-au1', 'AU'),
    ('queensland-university-of-technology', 'wave3-au1', 'AU'),
    ('rmit-university', 'wave3-au1', 'AU'),
    ('flinders-university', 'wave3-au1', 'AU'),
    ('university-of-technology-sydney', 'wave3-au1', 'AU'),
    ('deakin-university', 'wave3-au2', 'AU'),
    ('james-cook-university', 'wave3-au2', 'AU'),
    ('university-of-wollongong', 'wave3-au2', 'AU'),
    ('edith-cowan-university', 'wave3-au2', 'AU'),
    ('university-of-canberra', 'wave3-au2', 'AU'),
    ('swinburne-university-of-technology', 'wave3-au2', 'AU'),
    ('central-michigan-university', 'wave3-usretry', 'US'),
    ('cleveland-state-university', 'wave3-usretry', 'US'),
    ('college-of-charleston', 'wave3-usretry', 'US'),
]
BLOCKED = [  # (slug, reason) -> master-list status 'blocked'
    ('monash-university', 'research.monash.edu 403 on /en/persons/ + monash.edu 403 on radiography staff page (2026-09-23); hard stop'),
    ('the-university-of-western-australia', 'research.uwa.edu.au unreachable (000), research-repository.uwa.edu.au 403 on /en/persons/ (2026-09-23); hard stop'),
    ('macquarie-university', 'researchers.mq.edu.au 403 on /en/persons/ (2026-09-23); hard stop'),
    ('griffith-university', 'www.griffith.edu.au 403 incl. robots.txt (2026-09-23); hard stop'),
    ('la-trobe-university', 'www.latrobe.edu.au 403 on staff page (2026-09-23); hard stop'),
    ('the-university-of-newcastle', 'www.newcastle.edu.au 403 on /profile/staff-list (2026-09-23); hard stop'),
    ('university-of-tasmania', 'utas.edu.au 403 (2026-09-23); hard stop'),
    ('coastal-carolina-university', 'coastal.edu robots.txt: User-agent * Disallow / (bot allowlist only); hard stop, no collection (2026-09-23)'),
]

def canon_of(fname):
    return RENAME.get(fname, fname[:-5])

os.chdir(FAC)
for src, dst in RENAME.items():
    s, d = os.path.join(FAC, src), os.path.join(FAC, dst + '.json')
    if os.path.exists(s) and not os.path.exists(d):
        shutil.move(s, d)
        print('renamed', src, '->', dst + '.json')

master = json.load(open('master-list.json'))
idx = json.load(open('index.json'))
existing = {c['slug'] for c in idx['colleges']}
mlookup = {}
for cc, cols in master['countries'].items():
    for c in cols:
        mlookup[c['slug']] = (cc, c)

# manifest source urls
sources = {}
for b in ['_batch-wave3-au0.json', '_batch-wave3-au1.json', '_batch-wave3-au2.json', '_batch-wave3-usretry.json']:
    d = json.load(open(b))
    for c in d['colleges']:
        sources[c['slug']] = c.get('sources', [])

new_entries = []
attr_lines = []
total_prof = 0
for mslug, batch, country in LANDED:
    fn = (RENAME.get(mslug + '.json', mslug) ) + '.json'
    d = json.load(open(fn, encoding='utf-8'))
    assert isinstance(d.get('professors'), list) and d['professors'], f'empty {fn}'
    bad = [p for p in d['professors'] if not isinstance(p.get('name'), str) or not p['name'].strip()]
    assert not bad, f'{fn}: {len(bad)} nameless records'
    for p in d['professors']:
        assert 'title' in p and 'dept' in p, f'{fn}: missing title/dept keys'
    assert d.get('country') == country, f'{fn}: country {d.get("country")} != {country}'
    n = len(d['professors'])
    total_prof += n
    canon = canon_of(mslug + '.json')
    cc, mrow = mlookup.get(canon, (None, None))
    name = (mrow or {}).get('name') or d.get('college') or canon
    aliases = (mrow or {}).get('aliases') or []
    match = [canon, name] + aliases
    seen = set(); match = [x for x in match if x and not (x in seen or seen.add(x))]
    src_urls = sources.get(mslug, [])
    source = '; '.join(src_urls[:4]) if src_urls else 'official university faculty/staff directory'
    if not src_urls:
        source = 'official university faculty/staff directory (per-file source URL not recorded in ' + batch + ' manifest)'
    assert canon not in existing, f'duplicate index slug {canon}'
    new_entries.append({
        'slug': canon, 'name': name, 'country': country, 'match': match,
        'source': source, 'retrieved': TODAY, 'count': n,
    })
    existing.add(canon)
    attr_lines.append(f"{name} ({canon}): {n} professors. Source: {source} (retrieved {TODAY}). Public university faculty directory.\n")
    if mrow is not None:
        mrow['status'] = 'done'
    else:
        print('WARN: slug not in master-list:', canon)

for slug, reason in BLOCKED:
    cc, mrow = mlookup.get(slug, (None, None))
    if mrow is not None:
        mrow['status'] = 'blocked'
        mrow['blocked_reason'] = reason
        print('blocked:', slug)
    else:
        print('WARN blocked slug not in master-list:', slug)

idx['colleges'].extend(new_entries)
json.dump(idx, open('index.json', 'w'), ensure_ascii=False)
with open('ATTRIBUTION.txt', 'a') as f:
    f.writelines(attr_lines)

# recompute stats
import collections
stats = collections.Counter()
for cc, cols in master['countries'].items():
    stats.update((cc, c['status']) for c in cols)
master['stats'] = {
    'total': sum(1 for cols in master['countries'].values() for c in cols),
    'done': sum(v for (k, v) in stats.items() if k[1] == 'done'),
    'blocked': sum(v for (k, v) in stats.items() if k[1] == 'blocked'),
    'no-directory': sum(v for (k, v) in stats.items() if k[1] == 'no-directory'),
    'pending': sum(v for (k, v) in stats.items() if k[1] == 'pending'),
}
json.dump(master, open('master-list.json', 'w'), ensure_ascii=False, indent=1)

print(f'merged {len(new_entries)} colleges, {total_prof} professors')
print('master stats:', master['stats'])
