#!/usr/bin/env python3
"""Build data/faculty/master-list.json from USA (IPEDS), Canada, Mexico lists.
Usage: python3 build-master-list.py
Reads: /tmp/usa-colleges.json, /tmp/canada-colleges.json, /tmp/mexico-colleges.json
Writes: data/faculty/master-list.json
Marks already-landed colleges (from data/faculty/index.json) as done.
"""
import json, re, unicodedata, os, datetime

HUB = os.path.expanduser('~/workspace/hub')

def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','',s)

# landed slugs/names from current index.json
idx = json.load(open(f'{HUB}/data/faculty/index.json'))['colleges']
landed = {}  # norm(name) -> slug
for c in idx:
    landed[norm(c['name'])] = c['slug']

def mark_done(entries):
    n_done = 0
    for e in entries:
        if e.get('status') == 'done':
            n_done += 1
            continue
        key = norm(e['name'])
        if key in landed:
            e['status'] = 'done'
            e['done_slug'] = landed[key]
            n_done += 1
        # also try alias match
        elif any(norm(a) in landed for a in e.get('aliases', [])):
            e['status'] = 'done'
            e['done_slug'] = landed[norm(e['aliases'][0])]
            n_done += 1
    return n_done

countries = {}
usa = json.load(open('/tmp/usa-colleges.json'))
d = mark_done(usa)
countries['US'] = usa
print(f'US: {len(usa)} entries, {d} done')

for code, path in (('CA','/tmp/canada-colleges.json'), ('MX','/tmp/mexico-colleges.json')):
    entries = json.load(open(path))
    # ensure required fields
    for e in entries:
        e.setdefault('country', code)
        e.setdefault('status', 'pending')
        e.setdefault('aliases', [])
    d = mark_done(entries)
    countries[code] = entries
    print(f'{code}: {len(entries)} entries, {d} done')

total = sum(len(v) for v in countries.values())
done = sum(1 for v in countries.values() for e in v if e.get('status')=='done')
out = {
    'generated': datetime.date.today().isoformat(),
    'mandate': "PraBin 2026-09-23: every college/university in USA, Canada, Mexico. Nothing dropped.",
    'sources': {
        'US': 'IPEDS HD2024 (nces.ed.gov), degree-granting, active, sorted by enrollment size tier',
        'CA': 'Universities Canada + CICan + provincial ministry lists (see /tmp/canada-colleges-NOTES.md)',
        'MX': 'ANUIES + SEP listings (see /tmp/mexico-colleges-NOTES.md)',
    },
    'stats': {'total': total, 'done': done, 'pending': total-done},
    'countries': countries,
}
json.dump(out, open(f'{HUB}/data/faculty/master-list.json','w'), ensure_ascii=False)
print(f'WROTE master-list.json: {total} total, {done} done, {total-done} pending')
