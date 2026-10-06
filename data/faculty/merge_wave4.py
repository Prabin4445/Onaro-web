#!/usr/bin/env python3
"""Wave 4 merge: validate worker files, merge into index.json + ATTRIBUTION.txt + master-list.json."""
import json, os, shutil, sys

F = os.path.dirname(os.path.abspath(__file__))
BATCH_IDS = ['w4-us0', 'w4-us1', 'w4-us2', 'w4-us3', 'w4-cmx', 'w4-au']
TODAY = '2026-09-23'

# backups
shutil.copy(f'{F}/index.json', '/tmp/w4-index.json.bak')
shutil.copy(f'{F}/master-list.json', '/tmp/w4-master-list.json.bak')
shutil.copy(f'{F}/ATTRIBUTION.txt', '/tmp/w4-attribution.txt.bak')

ml = json.load(open(f'{F}/master-list.json'))
idx = json.load(open(f'{F}/index.json'))
by_slug = {e['slug']: e for cc in ml['countries'].values() for e in cc}
existing_slugs = {c['slug'] for c in idx['colleges']}

done, blocked_hosts, no_dir = [], [], []
errors = []

for wid in BATCH_IDS:
    mp = f'{F}/_batch-wave4-{wid}.json'
    b = json.load(open(mp))
    for c in b.get('colleges', []):
        slug = c.get('slug')
        status = str(c.get('status', 'complete')).lower()
        fp = f'{F}/{slug}.json' if slug else None
        # blocked entries: count 0 / file null / status blocked -> skip college merge
        if status in ('blocked',) or c.get('count') in (0, None) or c.get('file') is None and not (fp and os.path.exists(fp)):
            if c.get('count', 0) == 0:
                continue
        if not (fp and os.path.exists(fp)):
            errors.append(f'{wid}: MISSING FILE {slug}'); continue
        d = json.load(open(fp))
        if set(d.keys()) != {'college', 'country', 'professors'}:
            errors.append(f'{slug}: bad top keys {sorted(d.keys())}'); continue
        mcc = (by_slug.get(slug, {}) or {}).get('country')
        if c.get('country') and mcc and c['country'] != d['country']:
            errors.append(f'{slug}: country mismatch manifest={c["country"]} file={d["country"]}'); continue
        profs = d['professors']
        bad = [p for p in profs if set(p.keys()) != {'name', 'title', 'dept', 'courses'} or not p['name']]
        if bad:
            errors.append(f'{slug}: {len(bad)} bad professor records'); continue
        n = len(profs)
        if c.get('count') is not None and c['count'] != n:
            print(f'  count fix: {slug} manifest={c["count"]} -> file={n}')
        name = c.get('name') or c.get('college') or slug
        sources = c.get('sources') or [c.get('source')] or []
        sources = [s for s in sources if s]
        done.append({'slug': slug, 'name': name, 'country': d['country'],
                     'count': n, 'source': sources[0] if sources else '',
                     'sources': sources,
                     'retrieved': c.get('retrieved', TODAY), 'note': c.get('note') or c.get('notes', ''),
                     'spot_check': c.get('spot_check', '')})
    for bl in b.get('blocked', []):
        blocked_hosts.append({**bl, 'worker': wid})
    for nd in b.get('no_directory', b.get('no-directory', [])):
        no_dir.append({**nd, 'worker': wid})

if errors:
    print('VALIDATION ERRORS:'); [print(' ', e) for e in errors]; sys.exit(1)

print(f'validated: {len(done)} colleges, {sum(d["count"] for d in done)} professors')
print(f'blocked hosts: {len(blocked_hosts)}, no-directory: {len(no_dir)}')

# dedupe done by slug (last wins)
seen = {}
for d in done: seen[d['slug']] = d
done = list(seen.values())

# 1) index.json
for d in done:
    if d['slug'] in existing_slugs:
        print(f'  SKIP (already in index): {d["slug"]}'); continue
    m = by_slug.get(d['slug'], {})
    match = [d['slug'], d['name']] + [a for a in m.get('aliases', []) if a and a != d['name']]
    idx['colleges'].append({'slug': d['slug'], 'name': d['name'], 'country': d['country'],
                            'match': match, 'source': d['source'],
                            'retrieved': d['retrieved'], 'count': d['count']})
    existing_slugs.add(d['slug'])

json.dump(idx, open(f'{F}/index.json', 'w'), ensure_ascii=False, indent=1)

# 2) ATTRIBUTION.txt
with open(f'{F}/ATTRIBUTION.txt', 'a') as f:
    for d in done:
        srcs = '; '.join(d['sources'])
        line = f"{d['name']} ({d['slug']}): {d['count']} professors. Source: {srcs} (retrieved {d['retrieved']}). Public university faculty directory."
        if d['note']: line += f" Note: {d['note']}"
        f.write(line + '\n')

# 3) master-list.json
stats = {'done': 0, 'blocked': 0, 'no-directory': 0}
for d in done:
    e = by_slug.get(d['slug'])
    if e and e['status'] != 'done':
        e['status'] = 'done'
        if e['slug'] != d['slug']: e['done_slug'] = d['slug']
        stats['done'] += 1
done_slugs = {d['slug'] for d in done}
for bl in blocked_hosts:
    e = by_slug.get(bl.get('slug', ''))
    if e and e['status'] not in ('done', 'blocked'):
        e['status'] = 'blocked'
        e['note'] = bl['reason']
        stats['blocked'] += 1
for nd in no_dir:
    e = by_slug.get(nd['slug'])
    if e and e['status'] not in ('done', 'blocked', 'no-directory'):
        e['status'] = 'no-directory'
        e['reason'] = nd['reason']
        stats['no-directory'] += 1

json.dump(ml, open(f'{F}/master-list.json', 'w'), ensure_ascii=False, indent=1)

total = sum(c['count'] for c in idx['colleges'])
print(f'index now: {len(idx["colleges"])} colleges / {total} professors')
print(f'master-list updates: {stats}')

# write merge summary for PIPELINE.md
out = {
  'done': [{'slug': d['slug'], 'name': d['name'], 'country': d['country'], 'count': d['count']} for d in done],
  'blocked_hosts': blocked_hosts,
  'no_directory': [{'slug': n['slug'], 'name': n.get('name',''), 'reason': n.get('reason',''), 'worker': n['worker']} for n in no_dir],
  'index_colleges': len(idx['colleges']), 'index_professors': total,
}
json.dump(out, open('/tmp/w4-merge-summary.json', 'w'), indent=1)
print('summary -> /tmp/w4-merge-summary.json')
