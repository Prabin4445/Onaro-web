#!/usr/bin/env python3
"""Merge worker batch manifests into index.json + ATTRIBUTION.txt + PIPELINE.md + master-list.json.
Usage: python3 merge-wave.py <manifest-glob-suffix>
  e.g. python3 merge-wave.py wave1   (merges data/faculty/_batch-wave1-*.json not yet merged)
Idempotent: skips manifests already recorded in PIPELINE.md.
"""
import json, glob, os, sys, datetime

HUB = os.path.expanduser('~/workspace/hub')
FAC = f'{HUB}/data/faculty'
suffix = sys.argv[1] if len(sys.argv) > 1 else 'wave1'
today = datetime.date.today().isoformat()

pipe = open(f'{FAC}/PIPELINE.md').read()
idx_path = f'{FAC}/index.json'
idx = json.load(open(idx_path))
existing = {c['slug'] for c in idx['colleges']}

ml_path = f'{FAC}/master-list.json'
ml = json.load(open(ml_path)) if os.path.exists(ml_path) else None
ml_by_slug = {}
if ml:
    for code, arr in ml['countries'].items():
        for e in arr:
            ml_by_slug[e['slug']] = e

merged_files, total_profs, new_blocks, no_dir = [], 0, [], []
attr_lines = []

for mpath in sorted(glob.glob(f'{FAC}/_batch-{suffix}*.json')):
    m = json.load(open(mpath))
    batch = m.get('batch', os.path.basename(mpath))
    if f'_batch-{batch}' in pipe and f'batch {batch}' in pipe:
        print(f'skip {batch}: already in PIPELINE.md')
        continue
    # normalize: files may be a list [{slug,name,source,...}] or a dict {slug:{college,name?,sources[],source?,...}}
    raw_files = m.get('files', [])
    files = []
    if isinstance(raw_files, dict):
        for slug, f in raw_files.items():
            files.append({
                'slug': slug,
                'name': f.get('name') or f.get('college') or slug,
                'source': f.get('source') or (f.get('sources') or [''])[0],
                'retrieved': f.get('retrieved') or m.get('retrieved') or m.get('date') or today,
                'count': f.get('count', 0),
                'departments': f.get('departments', []),
                'notes': f.get('notes',''),
            })
    else:
        files = raw_files
    raw_nodir = m.get('noDirectory', [])
    nodir = []
    if isinstance(raw_nodir, dict):
        nodir = [f"{k} — {v}" for k, v in raw_nodir.items()]
    else:
        nodir = raw_nodir
    for f in files:
        slug = f['slug']
        jpath = f'{FAC}/{slug}.json'
        if not os.path.exists(jpath):
            print(f'WARN {batch}: manifest lists {slug} but file missing — skipped')
            continue
        d = json.load(open(jpath))
        profs = d.get('professors', [])
        # honesty validation
        bad = [p for p in profs if not p.get('name') or not str(p['name']).strip()]
        if bad:
            print(f'WARN {batch}/{slug}: {len(bad)} nameless entries dropped')
            profs = [p for p in profs if p.get('name') and str(p['name']).strip()]
            d['professors'] = profs
            json.dump(d, open(jpath,'w'), ensure_ascii=False)
        # dedupe by normalized name within file
        seen, clean = set(), []
        import re, unicodedata
        for p in profs:
            k = unicodedata.normalize('NFKD', p['name']).encode('ascii','ignore').decode().lower().strip()
            k = re.sub(r'\s+',' ',k)
            if k not in seen:
                seen.add(k); clean.append(p)
        if len(clean) != len(profs):
            print(f'note {slug}: {len(profs)-len(clean)} dupes removed')
            d['professors'] = clean
            json.dump(d, open(jpath,'w'), ensure_ascii=False)
            profs = clean
        count = len(profs)
        if slug not in existing:
            match = [slug, d.get('college','')]
            for a in (ml_by_slug.get(slug,{}).get('aliases') or [])[:4]:
                if a not in match: match.append(a)
            idx['colleges'].append({
                'slug': slug, 'name': d.get('college', f.get('name', slug)),
                'country': d.get('country','US'), 'match': match,
                'source': f.get('source',''), 'retrieved': f.get('retrieved', today),
                'count': count,
            })
            existing.add(slug)
            merged_files.append(slug)
        total_profs += count
        attr_lines.append(f"{d.get('college', slug)} ({slug}): {count} professors. Source: {f.get('source','')} (retrieved {f.get('retrieved', today)}). Public university faculty directory." + (f" Note: {f['notes']}" if f.get('notes') else ""))
        if slug in ml_by_slug:
            ml_by_slug[slug]['status'] = 'done'
            ml_by_slug[slug]['done_slug'] = slug
    raw_blocks = m.get('blockedHosts', [])
    blocks = []
    for b in raw_blocks:
        if isinstance(b, dict):
            blocks.append(f"{b.get('host','?')} — {b.get('reason','')} ({b.get('college','')}, {m.get('date', today)})".strip())
        else:
            blocks.append(str(b))
    for b in blocks:
        if b not in pipe and b not in new_blocks:
            new_blocks.append(b)
    for n in nodir:
        no_dir.append(f"{batch}: {n}")

json.dump(idx, open(idx_path,'w'), ensure_ascii=False)
with open(f'{FAC}/ATTRIBUTION.txt','a') as fh:
    fh.write(f'\n## Batch {suffix} ({today})\n' + '\n'.join(attr_lines) + '\n')

# PIPELINE.md landed section
landed = f"\n- **{suffix} batch ({today})**: {len(merged_files)} colleges merged, {total_profs} professors. " + \
         (f"Blocked: {'; '.join(new_blocks)}. " if new_blocks else '') + \
         (f"No public directory: {'; '.join(no_dir)}. " if no_dir else '')
pipe = pipe.replace('## Todo queue (next daily runs)', landed + '\n## Todo queue (next daily runs)')
if new_blocks:
    pipe = pipe.replace('## Blocked hosts\n(none yet)', '## Blocked hosts\n' + '\n'.join(f'- {b}' for b in new_blocks))
    # append to existing list if section already has entries
    if '## Blocked hosts\n(none yet)' not in open(f'{FAC}/PIPELINE.md').read():
        pipe = pipe.replace('## Blocked hosts', '## Blocked hosts\n' + '\n'.join(f'- {b}' for b in new_blocks))
open(f'{FAC}/PIPELINE.md','w').write(pipe)

if ml:
    ml['stats'] = {
        'total': sum(len(a) for a in ml['countries'].values()),
        'done': sum(1 for a in ml['countries'].values() for e in a if e.get('status')=='done'),
    }
    ml['stats']['pending'] = ml['stats']['total'] - ml['stats']['done']
    json.dump(ml, open(ml_path,'w'), ensure_ascii=False)

import subprocess
sz = subprocess.run(['du','-sh',FAC],capture_output=True,text=True).stdout.strip()
print(f'MERGED {len(merged_files)} new colleges, {total_profs} professors this wave')
print(f'index.json now: {len(idx["colleges"])} colleges; faculty dir size: {sz}')
if new_blocks: print('new blocked:', new_blocks)
