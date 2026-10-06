#!/usr/bin/env python3
"""Degree Plan Tracker — seed -> runtime data pipeline.

Reads collector JSON files from ~/workspace/degree-tracker/seed/*.json,
validates them, computes TCCNS-based transfer mappings, and writes:
  data/degrees/index.json        (plan catalog)
  data/degrees/<slug>.json       (full plans, with per-course xfer lists)

Honesty rules: official catalogs only (enforced by collectors); this script
never invents data — it only validates, normalizes, and cross-links.
Usage: python3 build.py [seed_dir]
"""
import json, os, re, sys, datetime, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/workspace/degree-tracker/seed')
warns = []

def warn(msg):
    warns.append(msg); print('WARN:', msg)

def norm_tccns(s):
    if not s: return ''
    return re.sub(r'\s+', ' ', str(s).upper().strip())

def load_seeds():
    plans = []
    # top-level seed/*.json plus seed/plans/*.json (collector convention)
    for sdir in [SEED, os.path.join(SEED, 'plans')]:
        if not os.path.isdir(sdir):
            continue
        for fn in sorted(os.listdir(sdir)):
            if not fn.endswith('.json'):
                continue
            p = os.path.join(sdir, fn)
            rel = fn if sdir == SEED else 'plans/' + fn
            try:
                jd = json.load(open(p, encoding='utf-8'))
            except Exception as e:
                warn(f'{rel}: unreadable ({e}) — skipped'); continue
            jd['_file'] = rel
            jd = normalize_flat(jd)
            plans.append(jd)
    return plans
    return plans

def prereq_codes(p):
    """Extract course codes from a prereq entry (string or rich object)."""
    if isinstance(p, str): return [p]
    if isinstance(p, dict):
        codes = list(p.get('one_of') or [])
        if p.get('course'): codes.append(p['course'])
        return codes
    return []

KNOWN_SCHOOLS = {
    'The University of Texas at Arlington': {'city': 'Arlington, TX', 'state': 'TX', 'kind': 'public4yr'},
    'The University of Texas at Dallas': {'city': 'Richardson, TX', 'state': 'TX', 'kind': 'public4yr'},
    'Dallas College': {'city': 'Dallas, TX', 'state': 'TX', 'kind': 'community'},
    'Oakland University': {'city': 'Rochester Hills, MI', 'state': 'MI', 'kind': 'public4yr'},
}
CAT_MAP = {'major_required': 'major', 'major_elective': 'major',
           'core': 'core', 'elective': 'elective'}

def degree_level(deg):
    d = (deg or '').upper().replace(' ', '').replace('-', '')
    # AS-T / AA-T / AST are transfer associate degrees, not bachelor
    if d.startswith('AA') or d.startswith('AS'):
        return 'associate'
    return 'bachelor'

def normalize_flat(d):
    """Convert the flat collector shape (plan_id/school/program/...) to the
    canonical nested {institution, plan} shape."""
    if isinstance(d.get('plan'), dict):
        return d  # already canonical
    school = d.get('school', '')
    info = KNOWN_SCHOOLS.get(school, {})
    if school and not info:
        warn(f'{d.get("_file")}: unknown school {school!r} — city/kind left blank')
    notes = d.get('notes')
    if isinstance(notes, list):
        notes = '\n'.join(str(x) for x in notes)
    if d.get('tccns_source_url'):
        notes = (notes + '\n' if notes else '') + 'TCCNS source: ' + d['tccns_source_url']
    sems = []
    for s in d.get('semesters') or []:
        cs = []
        for c in s.get('courses') or []:
            nc = dict(c)
            nc['category'] = CAT_MAP.get(c.get('category'), c.get('category') or 'elective')
            if 'prerequisites' in nc and 'prereq' not in nc:
                nc['prereq'] = nc.pop('prerequisites')
            nc.setdefault('prereq', [])
            nc.setdefault('choice', False)
            nc.setdefault('choice_note', '')
            nc.setdefault('options', [])
            cs.append(nc)
        n = s.get('semester') or s.get('n')
        term = s.get('term', '')
        yl = s.get('year_label', '') or s.get('label', '')
        label = ' · '.join(x for x in (yl, term) if x) or f'Semester {n}'
        sems.append({'n': n, 'label': label, 'term': term, 'year_label': yl,
                     'declared_credits': s.get('total_credits'), 'courses': cs})
    return {
        '_file': d.get('_file'),
        'institution': {'name': school, 'city': info.get('city', ''),
                        'state': info.get('state', ''), 'kind': info.get('kind', '')},
        'plan': {'id': d.get('plan_id'), 'degree': d.get('degree'),
                 'major': d.get('program'), 'total_credits': d.get('total_credits'),
                 'catalog_year': d.get('catalog_year'), 'source_url': d.get('source_url'),
                 'transfer_confidence': d.get('transfer_confidence', ''),
                 'notes': notes or '', 'semesters': sems,
                 'content_hash': d.get('content_hash', ''),
                 'last_verified': d.get('last_verified', ''),
                 'source_hash': d.get('source_hash', '')},
    }

def validate(d):
    fn = d['_file']; errs = []
    inst = d.get('institution') or {}
    plan = d.get('plan') or {}
    for k in ('name',):
        if not inst.get(k): errs.append(f'missing institution.{k}')
    for k in ('id', 'degree', 'major', 'total_credits', 'catalog_year', 'source_url'):
        if not plan.get(k): errs.append(f'missing plan.{k}')
    # content_hash / last_verified: auto-generate if missing (collector contract:
    # "omit them, pipeline adds them"). Computed here so seeds stay simple.
    if not plan.get('content_hash'):
        canon = {'id': plan.get('id'), 'degree': plan.get('degree'), 'major': plan.get('major'),
                 'total_credits': plan.get('total_credits'), 'catalog_year': plan.get('catalog_year'),
                 'semesters': plan.get('semesters')}
        plan['content_hash'] = hashlib.sha256(json.dumps(canon, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    if not plan.get('last_verified'):
        plan['last_verified'] = datetime.date.today().isoformat()
    # content_hash must match the canonical plan content (detects tampering/drift)
    ch = plan.get('content_hash')
    if ch:
        canon = {'id': plan.get('id'), 'degree': plan.get('degree'), 'major': plan.get('major'),
                 'total_credits': plan.get('total_credits'), 'catalog_year': plan.get('catalog_year'),
                 'semesters': plan.get('semesters')}
        expect = hashlib.sha256(json.dumps(canon, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
        if ch != expect:
            errs.append('content_hash does not match plan content (stale or tampered)')
    sems = plan.get('semesters') or []
    if not sems: errs.append('no semesters')
    # Semester-number gate (NEW 2026-10-01): every semester MUST carry a numeric
    # n. Older seeds omit it, so normalize to 1-based catalog order first (this
    # runs AFTER the content_hash check above, so stored hashes stay valid).
    # slot_id is derived as s{n}-{course_index}, so a numeric, unique n per
    # plan guarantees globally-unique slot_ids within the plan by construction.
    for si, s in enumerate(sems):
        n = s.get('n')
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            s['n'] = si + 1
    seen_n = set()
    for s in sems:
        n = s.get('n')
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            errs.append('semester has non-numeric n (must be a positive integer)')
        elif n in seen_n:
            errs.append(f'duplicate semester n={n} (would produce duplicate slot_ids)')
        else:
            seen_n.add(n)
    seen, total, codes = set(), 0, set()
    for s in sems:
        for c in s.get('courses') or []:
            code = c.get('code', ''); title = c.get('title', ''); cr = c.get('credits')
            if not code or not title: errs.append(f'semester {s.get("n")}: course missing code/title')
            if not isinstance(cr, (int, float)) or cr < 0:
                errs.append(f'{code}: bad credits {cr!r}')
            elif cr == 0 and not (c.get('choice') or c.get('required_zero')):
                # VARIABLE-CREDIT CONVENTION (coordinator decision 2026-10-05,
                # BACKLOG-18 wave 32, Maricopa dental-hygiene precedent):
                # courses the official source lists with a credit range whose
                # minimum is 0 (e.g. 0-3, 0-2) are transcribed at the catalog
                # minimum and marked required_zero:true, with the notes
                # documenting the official range. They are excluded from sums
                # (transcribed at 0 anyway) but must not be dropped: they are
                # required by the official sequence.
                errs.append(f'{code}: 0 credits on a non-choice, non-required_zero course')
            elif cr == 0:
                warn(f'{fn}: {code} is 0-credit ({"required" if c.get("required_zero") else "variable/choice slot"}) — excluded from sums')
            else: total += cr
            if not c.get('choice'):
                if code in codes and not plan.get('allow_repeated_courses'):
                    errs.append(f'duplicate course code {code}')
                elif code in codes:
                    warn(f'{fn}: {code} repeats (allow_repeated_courses) — must be documented in notes')
                codes.add(code)
            seen.add(code)
    tc = plan.get('total_credits')
    if isinstance(tc, (int, float)) and abs(total - tc) > 0.01:
        errs.append(f'credit sum {total} != declared total {tc} (must match exactly)')
    # semester-count gate: associate 4-8 (genuine 8-term health/consortium AAS
    # sequences are published, e.g. Maricopa dental-hygiene pathway maps;
    # coordinator decision 2026-10-05, BACKLOG-18 wave 32), bachelor 7-12
    # (TCCNS advising guides publish genuine 7-semester sequences, e.g.
    # Tarleton BA Music; coordinator decision 2026-10-05, BACKLOG-18).
    # Extended plans (dual-degree, combined BS+MS, professional-phase,
    # officially published block/term structures beyond 12 terms) allow up
    # to 15 (Tarleton BS Kinesiology/MSAT combined: 15 terms; Troy Dothan
    # BS Elementary Education: 15 official terms/blocks; 2026-10-05).
    # Outside that range the plan is incomplete or malformed.
    #
    # TERM-SYSTEM RULE (coordinator decision 2026-10-02, Foothill case):
    # Plans from quarter/trimester-system schools carry term_system='quarter' or
    # 'trimester' (must be justified by the official source in plan notes; Foothill
    # College is an official quarter-system school). Term-count gates scale by the
    # terms-per-year ratio (quarter x1.5, trimester x4/3) because e.g. 8 quarters
    # ~= 5.3 semesters — normal for a 2-year AS, especially full-time lockstep
    # health cohorts (Radiologic Tech, Vet Tech run year-round incl. summers).
    # The gate catches malformed plans, not term systems.
    deg = str(plan.get('degree') or '').upper()
    nsem = len(sems)
    term_system = str(plan.get('term_system') or 'semester').lower()
    if term_system not in ('semester', 'quarter', 'trimester'):
        errs.append(f"unknown term_system {term_system!r} (expected semester|quarter|trimester)")
        term_system = 'semester'
    def scale(lo, hi):
        if term_system == 'quarter':
            return (int(lo * 1.5), int(hi * 1.5 + 0.999))
        if term_system == 'trimester':
            return (int(lo * 4 / 3), int(hi * 4 / 3 + 0.999))
        return (lo, hi)
    is_extended = plan.get('extended') is True
    prog_type = str(plan.get('program_type') or '')
    # Special program models with legitimately non-standard term counts.
    # program_type MUST be justified by the official source in the plan notes:
    # - professional-phase: only the professional phase is sequenced (prereqs
    #   live in external_prereqs, e.g. nursing/health programs, CJI partnerships)
    # - completion: degree-completion/completer programs (AAS-to-BS, RN-to-BSN,
    #   block-transfer-in completion degrees like Bryan University's)
    # - accelerated: accelerated second-degree / LPN-to-RN tracks
    # - 3-plus-2: 3+2 dual programs (only the home-institution years sequenced)
    # - part-time: officially published part-time cohort tracks (more, lighter
    #   terms than the full-time sequence, e.g. UA-PTC HIT AAS part-time: 8 terms)
    if prog_type in ('professional-phase', 'completion', 'accelerated', '3-plus-2') and (
        deg.startswith('AA') or deg.startswith('AS') or deg.startswith('B')
    ):
        # cap 9 (was 7): genuine 9-term health completion/professional-phase
        # sequences exist (Baptist Health MLT-AAS-to-MLS-BHS, 9 terms,
        # coordinator decision 2026-10-05, BACKLOG-18 wave 32).
        lo, hi = scale(2, 9)
        if not (lo <= nsem <= hi):
            errs.append(f'{prog_type} plan has {nsem} {term_system} terms (expected {lo}-{hi})')
    elif prog_type == 'part-time' and (
        deg.startswith('AA') or deg.startswith('AS') or deg.startswith('B')
    ):
        lo, hi = scale(2, 10)
        if not (lo <= nsem <= hi):
            errs.append(f'part-time plan has {nsem} {term_system} terms (expected {lo}-{hi})')
    elif is_extended and (deg.startswith('AA') or deg.startswith('AS')):
        # extended-phase associate (coordinator decision 2026-10-05, BACKLOG-18
        # wave 32, Pima Medical Institute Vet Tech precedent): modular /
        # phase-structured health associate programs whose official catalog
        # outline exceeds 7 terms (11 terms incl. VA phase, 2026-2027
        # catalog p.159 cross-verified vs system catalog). Only with
        # extended=True AND notes documenting the official phase structure.
        lo, hi = scale(4, 12)
        if not (lo <= nsem <= hi):
            errs.append(f'extended-phase associate plan has {nsem} {term_system} terms (expected {lo}-{hi})')
    elif deg.startswith('AA') or deg.startswith('AS'):
        # 4-8 (was 4-7): health-science/consortium AS programs can run 8
        # (e.g. Maricopa dental-hygiene AAS pathway maps; COC sonography AS;
        # coordinator decision 2026-10-05, BACKLOG-18 wave 32).
        lo, hi = scale(4, 8)
        if not (lo <= nsem <= hi):
            errs.append(f'associate plan has {nsem} {term_system} terms (expected {lo}-{hi})')
    elif deg.startswith('B'):
        max_sem = 15 if is_extended else 12
        lo, hi = scale(7, max_sem)
        if not (lo <= nsem <= hi):
            errs.append(f'bachelor plan has {nsem} {term_system} terms (expected {lo}-{hi})')
    # per-semester declared totals (flat collector shape carries them)
    for s in sems:
        dc = s.get('declared_credits')
        if isinstance(dc, (int, float)):
            stot = sum(c.get('credits') or 0 for c in s.get('courses') or [])
            if abs(stot - dc) > 0.01:
                errs.append(f'semester {s.get("n")} sum {stot} != declared {dc} (must match exactly)')
    # prereq existence: every prereq must name a real course in the plan,
    # or be listed in plan.external_prereqs (placement/TSI courses).
    external = set(plan.get('external_prereqs') or [])
    for s in sems:
        for c in s.get('courses') or []:
            for p in c.get('prereq') or []:
                for code in prereq_codes(p):
                    if code not in seen and code not in external:
                        errs.append(f'{c.get("code")} prereq {code!r} names no course in plan (add to external_prereqs if placement)')
    return errs

def load_inventory():
    """Program inventories: seed/inventory/<school>.json -> schools array."""
    inv_dir = os.path.join(SEED, 'inventory')
    schools = []
    if not os.path.isdir(inv_dir):
        return schools
    for fn in sorted(os.listdir(inv_dir)):
        if not fn.endswith('.json'):
            continue
        p = os.path.join(inv_dir, fn)
        try:
            d = json.load(open(p, encoding='utf-8'))
        except Exception as e:
            warn(f'inventory/{fn}: unreadable ({e}) — skipped'); continue
        progs = d.get('programs') or []
        if not progs:
            warn(f'inventory/{fn}: no programs listed — skipped'); continue
        collected = sum(1 for x in progs if x.get('status') == 'collected')
        schools.append({
            'slug': fn[:-5], 'name': d.get('school', ''),
            'catalog': d.get('catalog_year', ''),
            'inventory_source': d.get('source_url', ''),
            'programs_total': len(progs), 'programs_collected': collected,
            'programs': progs,
        })
    return schools

def main():
    seeds = load_seeds()
    if not seeds:
        print('No seed files in', SEED); sys.exit(1)
    ok, index_plans = [], []
    slug_seen = set()
    for d in seeds:
        errs = validate(d)
        if errs:
            warn(f'{d["_file"]}: INVALID — ' + '; '.join(errs) + ' — skipped')
            continue
        plan = d['plan']; inst = d['institution']
        slug = plan['id']
        if slug in slug_seen:
            warn(f'{d["_file"]}: duplicate plan id {slug} — skipped'); continue
        slug_seen.add(slug)
        ok.append(d)
        index_plans.append({
            'slug': slug, 'school': inst['name'], 'city': inst.get('city', ''),
            'state': inst.get('state', ''), 'kind': inst.get('kind', ''),
            'degree': plan['degree'], 'major': plan['major'],
            'credits': plan['total_credits'], 'semesters': len(plan['semesters']),
            'catalog': plan['catalog_year'], 'source': plan['source_url'],
            'transfer_confidence': plan.get('transfer_confidence', ''),
            'level': degree_level(plan['degree']),
        })
    # TCCNS cross-link: tccns -> [slugs]. Only EXPLICIT tccns values link —
    # no code fallback (a university-local code that merely resembles a TCCNS
    # number must not claim transferability without a published equivalency).
    tmap = {}
    for d in ok:
        slug = d['plan']['id']
        for s in d['plan']['semesters']:
            for c in s['courses']:
                t = norm_tccns(c.get('tccns'))
                if t: tmap.setdefault(t, set()).add(slug)
    # embed xfer lists + stable slot_ids. Semester n was normalized to a
    # positive int (unique per plan) in validate(), so s{n}-{i} is unique
    # within the plan by construction. The defensive duplicate check below
    # rejects the plan if that invariant is ever violated (0 tolerance).
    dropped = set()
    for d in ok:
        slug = d['plan']['id']
        seen_ids = set()
        dup = False
        for s in d['plan']['semesters']:
            for i, c in enumerate(s['courses']):
                sid = f"s{s['n']}-{i}"
                if sid in seen_ids:
                    dup = True
                seen_ids.add(sid)
                c['slot_id'] = sid
                t = norm_tccns(c.get('tccns'))
                others = sorted(x for x in tmap.get(t, set()) if x != slug) if t else []
                c['xfer'] = others
                c['tccns'] = t
        if dup:
            warn(f'{d["_file"]}: duplicate slot_ids after normalization — skipped')
            dropped.add(slug)
    if dropped:
        ok = [d for d in ok if d['plan']['id'] not in dropped]
        index_plans = [p for p in index_plans if p['slug'] not in dropped]
    # write runtime files
    os.makedirs(HERE, exist_ok=True)
    today = datetime.date.today().isoformat()
    schools = load_inventory()
    # Build the picker school list from validated plans (9 schools), merging
    # inventory program lists where available. The picker groups by school.
    from collections import OrderedDict as _OD
    plan_schools = _OD()
    for d in ok:
        inst = d['institution']; plan = d['plan']
        name = inst['name']
        if name not in plan_schools:
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
            plan_schools[name] = {
                'slug': slug, 'name': name,
                'city': inst.get('city', ''), 'state': inst.get('state', ''),
                'kind': inst.get('kind', ''),
                'catalog': plan.get('catalog_year', ''),
                'inventory_source': plan.get('source_url', ''),
                'programs': [],
            }
        plan_schools[name]['programs'].append({
            'plan_id': plan['id'],
            'degree': plan['degree'],
            'major': plan['major'],
            'status': 'collected',
        })
    inv_by_slug = {s['slug']: s for s in schools}
    for name, ps in plan_schools.items():
        inv = inv_by_slug.get(ps['slug'])
        if inv and inv.get('programs'):
            collected_ids = {p['plan_id'] for p in ps['programs']}
            for p in inv['programs']:
                if p.get('plan_id') in collected_ids:
                    p['status'] = 'collected'
            ps['programs'] = inv['programs']
            ps['programs_total'] = inv.get('programs_total', len(inv['programs']))
            ps['programs_collected'] = len(collected_ids)
        else:
            ps['programs_total'] = len(ps['programs'])
            ps['programs_collected'] = len(ps['programs'])
    schools = list(plan_schools.values())
    # soft cross-check: collected plans should appear in some inventory
    if schools:
        inv_ids = set()
        for s in schools:
            for p in s['programs']:
                if p.get('plan_id'): inv_ids.add(p['plan_id'])
        for d in ok:
            if d['plan']['id'] not in inv_ids:
                warn(f'{d["_file"]}: plan id not listed in any inventory')
    # national inventory totals for the honest subtitle ("17 plans · 4,025 schools")
    national_schools, national_programs = 0, 0
    try:
        _dir = json.load(open(os.path.join(HERE, 'inventory', 'dir.json'), encoding='utf-8'))
        national_schools = _dir.get('count') or len(_dir.get('schools', []))
    except Exception:
        pass
    json.dump({'updated': today, 'count': len(ok), 'plans': index_plans,
               'schools': schools,
               'national_schools': national_schools,
               'national_programs': national_programs},
              open(os.path.join(HERE, 'index.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    for d in ok:
        slug = d['plan']['id']
        out = {'institution': d['institution'], 'plan': d['plan']}
        json.dump(out, open(os.path.join(HERE, slug + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    # hygiene: remove stale runtime files left by pulled/renamed plans
    # (never in the index, never loaded by the app, but shipped to preview)
    live = set(d['plan']['id'] for d in ok)
    for fn in os.listdir(HERE):
        if fn.endswith('.json') and fn != 'index.json' and fn[:-5] not in live:
            os.remove(os.path.join(HERE, fn))
            warn(f'removed stale runtime file {fn} (not in index)')
    n_courses = sum(len(s['courses']) for d in ok for s in d['plan']['semesters'])
    print(f'Wrote {len(ok)} plans, {n_courses} courses -> {HERE}')
    print(f'{len(warns)} warnings')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
