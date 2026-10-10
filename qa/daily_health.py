#!/usr/bin/env python3
"""
Onaro Daily Health Check — runs every day to find issues before PraBin does.

SAFETY RULES (his hard requirement: nothing breaks while live):
  1. All checks run against LOCAL files only. The live site is NEVER modified.
  2. Live verification is READ-ONLY (curl GET). No writes, no deploys.
  3. Auto-fix is limited to SAFE, REVERSIBLE local changes:
     - .surgeignore corrections (only affects the NEXT deploy, never live)
     Nothing else is auto-fixed. Everything else is REPORTED.
  4. This script NEVER deploys. Deploy stays a deliberate human action.
  5. If a check is uncertain, it reports — it never guesses.

Checks:
  1. JS syntax      — node --check on every js/*.js
  2. CSS syntax     — brace balance on every css/*.css
  3. i18n parity    — every locale has the same keys as en
  4. surgeignore    — every runtime-fetched data file is deployable
  5. data integrity — index.json files are valid JSON; per-school files exist
  6. live status    — critical files return 200 on hub-preview.surge.sh (read-only)

Exit code: 0 = all green, 1 = issues found (see report).
Report: qa/daily-reports/YYYY-MM-DD.md
"""

import os, re, json, subprocess, sys, datetime, urllib.request

HUB = os.path.expanduser('~/workspace/hub')
LIVE = 'https://onaro-web.pages.dev'  # migrated from hub-preview.surge.sh 2026-10-06
REPORT_DIR = os.path.join(HUB, 'qa', 'daily-reports')

issues = []   # (severity, check, detail) — severity: ERROR or WARN
fixed = []    # auto-fixed items
ok_counts = {}

def report(sev, check, detail):
    issues.append((sev, check, detail))

def sh(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                            timeout=timeout, cwd=HUB)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, '', 'timeout'
    except Exception as e:
        return -1, '', str(e)

# ── 1. JS syntax ──────────────────────────────────────────────────────
def check_js():
    files = [f for f in os.listdir(os.path.join(HUB, 'js')) if f.endswith('.js')]
    bad = []
    for f in sorted(files):
        rc, _, err = sh(f'node --check js/{f}', timeout=15)
        if rc != 0:
            bad.append(f'{f}: {err[:200]}')
    ok_counts['js_files'] = len(files) - len(bad)
    for b in bad:
        report('ERROR', 'js-syntax', b)

# ── 2. CSS syntax ─────────────────────────────────────────────────────
def check_css():
    cssdir = os.path.join(HUB, 'css')
    bad = []
    for f in sorted(os.listdir(cssdir)):
        if not f.endswith('.css'):
            continue
        src = open(os.path.join(cssdir, f), encoding='utf-8', errors='replace').read()
        # strip comments and strings crudely, then count braces
        src2 = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
        src2 = re.sub(r'"(?:[^"\\]|\\.)*"', '""', src2)
        src2 = re.sub(r"'(?:[^'\\]|\\.)*'", "''", src2)
        if src2.count('{') != src2.count('}'):
            bad.append(f'{f}: unbalanced braces '
                       f'({src2.count("{")} open vs {src2.count("}")} close)')
    ok_counts['css_files_checked'] = True
    for b in bad:
        report('ERROR', 'css-syntax', b)

# ── 3. i18n parity ────────────────────────────────────────────────────
def check_i18n():
    p = os.path.join(HUB, 'js', 'i18n.js')
    src = open(p, encoding='utf-8', errors='replace').read()
    # Structure: Object.assign(HUB.i18n._dict('en'),{ 'key':'val', ... });
    blocks = re.findall(
        r"Object\.assign\(HUB\.i18n\._dict\('(\w+)'\),\{(.*?)\}\);",
        src, flags=re.S)
    locales = {}
    for loc, body in blocks:
        # Keys can appear multiple per line: 'key':'val','key2':'val2'
        lk = set(re.findall(r"'([a-zA-Z0-9_.-]+)':", body))
        locales.setdefault(loc, set()).update(lk)
    if 'en' not in locales:
        report('WARN', 'i18n', 'could not parse _dict blocks — skipping parity check')
        return
    en_keys = locales['en']
    ok_counts['i18n_en_keys'] = len(en_keys)
    for loc, lk in sorted(locales.items()):
        if loc == 'en':
            continue
        missing = sorted(en_keys - lk)
        if missing:
            report('ERROR', 'i18n',
                   f'locale "{loc}" missing {len(missing)} keys, e.g. {missing[:5]}')

# ── 4. surgeignore audit ──────────────────────────────────────────────
# The bug class that broke degree plans AND professors on live:
# a runtime-fetched data file blocked by .surgeignore → 404 on live.
def check_surgeignore(autofix=False):
    # Collect every data/ path the app fetches at runtime
    fetched = set()
    jsdir = os.path.join(HUB, 'js')
    pat = re.compile(r"""['"](data/[a-zA-Z0-9_./-]+?)['"]""")
    for f in os.listdir(jsdir):
        if not f.endswith('.js'):
            continue
        src = open(os.path.join(jsdir, f), encoding='utf-8', errors='replace').read()
        for m in pat.finditer(src):
            p = m.group(1)
            if '.json' in p or '/data/' in p or p.startswith('data/'):
                fetched.add(p)
    # Expand dynamic patterns the code builds at runtime
    dyn = set()
    for p in list(fetched):
        if '<slug>' in p or "'+slug+'" in p or '+slug+' in p:
            dyn.add(p)
    # Known dynamic fetch patterns (from code audit):
    dynamic_patterns = [
        'data/degrees/<slug>.json',      # js/degree.js degFile()
        'data/degrees/inventory/p-<ST>.json',  # js/degree.js national dir
        'data/faculty/<slug>.json',      # js/professors.js facFile()
    ]
    # Read .surgeignore rules (simple glob support: *, !negation)
    ig_path = os.path.join(HUB, '.surgeignore')
    rules = []
    if os.path.exists(ig_path):
        for line in open(ig_path):
            line = line.strip()
            if line and not line.startswith('#'):
                rules.append(line)
    import fnmatch
    # gitignore-faithful matching: '*' does NOT cross '/' (fnmatch's '*' does,
    # which falsely flagged data/degrees/inventory/* as blocked by
    # data/degrees/*.json — real Surge deploys never excluded it).
    def _glob_re(pat):
        out = []
        for c in pat:
            if c == '*':
                out.append('[^/]*')
            elif c == '?':
                out.append('[^/]')
            else:
                out.append(re.escape(c))
        return '^' + ''.join(out) + '$'
    def is_ignored(path):
        ignored = False
        for r in rules:
            neg = r.startswith('!')
            rx = _glob_re(r[1:] if neg else r)
            if re.match(rx, path):
                ignored = not neg
        return ignored

    # Concrete files that MUST be deployable
    must_ship = [
        'data/degrees/index.json',
        'data/degrees/inventory/dir.json',
        'data/faculty/index.json',
        'data/colleges.json',
        'data/horoscopes.json',
        'data/quotes.json',
        'data/schools_us.json',
    ]
    blocked = [p for p in must_ship if is_ignored(p)]
    # Check dynamic patterns: does any rule block data/degrees/*.json style?
    # 2026-10-07: per-school degree slugs are API-served by design —
    # window.__ONARO_API_BASE is hardcoded in index.html and js/degree.js
    # tries the API first (/api/degrees/<slug>), static file is fallback-only.
    # The ~13k-file bundle is deliberately excluded from Surge deploys (the
    # host structurally fails past ~13k files, 2026-10-03/06). Exempt here.
    API_SERVED = ['data/degrees/<slug>.json']
    dyn_blocked = []
    for dp in dynamic_patterns:
        if dp in API_SERVED:
            continue
        probe = dp.replace('<slug>', 'probe-test-slug').replace('<ST>', 'CA')
        if is_ignored(probe):
            dyn_blocked.append(dp)
    ok_counts['surgeignore_rules'] = len(rules)
    for p in blocked:
        report('ERROR', 'surgeignore', f'runtime file blocked from deploy: {p}')
    for dp in dyn_blocked:
        report('ERROR', 'surgeignore',
               f'runtime fetch pattern blocked from deploy: {dp} — per-school files will 404 on live')

    # ── SAFE AUTO-FIX ──
    # Only touches .surgeignore (affects next deploy, never live).
    # Removes/negates rules that block runtime data. Never touches app code.
    if autofix and (blocked or dyn_blocked):
        with open(ig_path) as f:
            content = f.read()
        orig = content
        # Drop blanket blocks on runtime data dirs; keep narrow excludes.
        # NOTE 2026-10-07: data/degrees/*.json is a DELIBERATE exclusion, never
        # auto-removed — per-school plans are API-served (/api/degrees/<slug>)
        # and Surge structurally fails past ~13k files (2026-10-03/06).
        for bad_rule in ['data/faculty/*.json']:
            if bad_rule in content:
                content = content.replace(bad_rule + '\n', '')
                content = content.replace(bad_rule, '')
        # Ensure the concrete files are explicitly allowed
        for p in blocked:
            neg = '!' + p
            if neg not in content:
                content = content.rstrip('\n') + '\n' + neg + '\n'
        if content != orig:
            with open(ig_path, 'w') as f:
                f.write(content)
            fixed.append(f'.surgeignore: unblocked {len(blocked)+len(dyn_blocked)} '
                         f'runtime data pattern(s) — takes effect on next deploy, live untouched')

# ── 5. data integrity ─────────────────────────────────────────────────
def check_data():
    # index.json files must be valid JSON with expected shape
    checks = [
        ('data/degrees/index.json', ['plans', 'schools']),
        ('data/faculty/index.json', ['colleges']),
    ]
    for rel, expected_keys in checks:
        p = os.path.join(HUB, rel)
        if not os.path.exists(p):
            report('ERROR', 'data', f'missing {rel}')
            continue
        try:
            d = json.load(open(p))
        except Exception as e:
            report('ERROR', 'data', f'{rel} is not valid JSON: {e}')
            continue
        for k in expected_keys:
            if k not in d:
                report('ERROR', 'data', f'{rel} missing key "{k}"')
    # per-school files referenced by degree index must exist locally
    try:
        idx = json.load(open(os.path.join(HUB, 'data/degrees/index.json')))
        missing = 0
        for pl in idx.get('plans', [])[:50]:  # sample 50
            slug = pl.get('slug', '')
            if slug and not os.path.exists(os.path.join(HUB, 'data/degrees', slug + '.json')):
                missing += 1
        if missing:
            report('ERROR', 'data', f'{missing}/50 sampled degree plan files missing locally')
        ok_counts['degree_plans'] = len(idx.get('plans', []))
    except Exception:
        pass
    try:
        fidx = json.load(open(os.path.join(HUB, 'data/faculty/index.json')))
        ok_counts['faculty_colleges'] = len(fidx.get('colleges', []))
    except Exception:
        pass

# ── 6. live status (READ-ONLY) ────────────────────────────────────────
def check_live():
    urls = [
        'data/degrees/index.json',
        'data/degrees/inventory/dir.json',
        'data/faculty/index.json',
        'data/colleges.json',
        'data/horoscopes.json',
        'data/quotes.json',
        'data/schools_us.json',
        'js/app.js',
        'index.html',
    ]
    def curl_status(u):
        # curl is the reliable path in this sandbox; urllib's connection gets
        # intermittently killed by the egress proxy while curl succeeds.
        try:
            p = subprocess.run(
                ['curl', '-s', '-L', '-o', '/dev/null', '-w', '%{http_code}',
                 '--max-time', '25', '-A', 'OnaroHealthCheck/1.0',
                 LIVE + '/' + u],
                capture_output=True, text=True, timeout=40)
            code = p.stdout.strip()
            return int(code) if code.isdigit() else None
        except Exception:
            return None

    bad = []
    for u in urls:
        code = curl_status(u)
        if code is None:
            bad.append(f'{u}: curl fetch failed (transient)')
        elif code != 200:
            bad.append(f'{u}: http {code}')
    ok_counts['live_files_ok'] = len(urls) - len(bad)
    for b in bad:
        # WARN not ERROR: live blips can be transient; recheck next run
        report('WARN', 'live', b)
    # spot-check one per-school degree file + one faculty file on live
    for probe in ['data/degrees/dallas-college-aa-business.json',
                  'data/faculty/alberta-university-of-the-arts.json']:
        code = curl_status(probe)
        if code is None:
            # WARN not ERROR: a connection exception proves nothing about the live
            # site — sandbox egress is flaky. Only an actual non-200 response
            # proves a live-site problem.
            report('WARN', 'live', f'{probe}: fetch failed — transient, site not proven down')
        elif code != 200:
            report('ERROR', 'live', f'{probe}: http {code} — per-school data not serving on live')

def write_report():
    os.makedirs(REPORT_DIR, exist_ok=True)
    day = datetime.date.today().isoformat()
    errs = [i for i in issues if i[0] == 'ERROR']
    warns = [i for i in issues if i[0] == 'WARN']
    status = 'GREEN' if not issues else ('RED' if errs else 'YELLOW')
    lines = [f'# Onaro Daily Health — {day}', '', f'**Status: {status}**', '']
    lines.append('## Counts')
    for k, v in sorted(ok_counts.items()):
        lines.append(f'- {k}: {v}')
    lines.append('')
    if fixed:
        lines.append('## Auto-fixed (safe, local only — live untouched)')
        for f in fixed:
            lines.append(f'- {f}')
        lines.append('')
    if errs:
        lines.append(f'## Errors ({len(errs)}) — need attention')
        for _, chk, det in errs:
            lines.append(f'- [{chk}] {det}')
        lines.append('')
    if warns:
        lines.append(f'## Warnings ({len(warns)})')
        for _, chk, det in warns:
            lines.append(f'- [{chk}] {det}')
        lines.append('')
    if not issues:
        lines.append('All checks green. No action needed.')
    p = os.path.join(REPORT_DIR, day + '.md')
    open(p, 'w').write('\n'.join(lines) + '\n')
    # keep only last 30 reports
    reps = sorted(os.listdir(REPORT_DIR))
    for old in reps[:-30]:
        os.remove(os.path.join(REPORT_DIR, old))
    return status, p, errs, warns

def main():
    autofix = '--autofix' in sys.argv
    check_js()
    check_css()
    check_i18n()
    check_surgeignore(autofix=autofix)
    check_data()
    check_live()
    status, path, errs, warns = write_report()
    print(f'status={status} report={path} errors={len(errs)} warnings={len(warns)} fixed={len(fixed)}')
    for s, c, d in issues:
        print(f'[{s}] {c}: {d}')
    sys.exit(0 if status == 'GREEN' else 1)

if __name__ == '__main__':
    main()
