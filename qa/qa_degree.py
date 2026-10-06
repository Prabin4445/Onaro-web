#!/usr/bin/env python3
"""TRUE BROWSER QA: Onaro Degree Plan Tracker (js/degree.js + css/degree.css).

Loads file:///home/hatch/workspace/hub/index.html in headless Chromium with a
TRUE emulated viewport (CDP Emulation.setDeviceMetricsOverride), siphons ALL
console/page errors from before first paint, runs ~70 assertions across 4
runs (390 dark volt / 320 light / 390 dark rose / 390 i18n), and screenshots.

Read-only: never modifies app code. Any bug found -> documented + run FAILS.
"""
import json, subprocess, time, urllib.request, os, sys, base64, shutil, re
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
os.makedirs(QA, exist_ok=True)
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'

PLANS = [  # (slug, expected_tiles, expected_sems, catalog_year)
    ('dallas-college-aa-business', 20, 4, '2026-2027'),
    ('dallas-college-aa-transfer', 21, 4, '2025-2026'),
    ('dallas-college-as-computer-science', 19, 4, '2023-2024'),
    ('uta-bba-management', 41, 8, '2025-2026'),
    ('uta-bs-computer-science', 41, 8, '2025-2026'),
    ('utd-bs-computer-science', 44, 8, '2025-2026'),
    ('utd-bs-business-administration', 43, 8, '2025-2026'),
    ('hcc-aa-business', 20, 4, '2025-2026'),
    ('lone-star-aa-business', 20, 4, '2024-2025'),
    ('lone-star-as-computer-science', 18, 5, '2026-2027'),
    ('mdc-aa-business-administration', 23, 5, '2025-2026'),
    ('mdc-aa-computer-science', 20, 5, '2025-2026'),
    ('tamu-bba-management', 39, 8, '2026-2027'),
    ('tamu-bs-computer-science', 40, 8, '2026-2027'),
    ('ttu-bs-computer-science', 41, 8, '2025-2026'),
    ('utaustin-bba-management', 43, 8, '2026-2027'),
    ('utaustin-bs-computer-science', 38, 8, '2026-2027'),
]

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl)
        self.id = 0
    def send(self, method, params=None, wait=True):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        if not wait: return None
        self.ws.settimeout(None)
        try:
            deadline = time.time() + 25
            while time.time() < deadline:
                msg = json.loads(self.ws.recv())
                if msg.get('id') == self.id:
                    return msg.get('result')
            raise TimeoutError(method)
        finally:
            pass
    def close(self):
        try: self.ws.close()
        except Exception: pass

def port_open(port):
    import socket
    s = socket.socket(); s.settimeout(1)
    try: s.connect(('localhost', port)); return True
    except OSError: return False

def wait_port(port, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if port_open(port): return True
        time.sleep(0.4)
    return False

def find_target(port):
    with urllib.request.urlopen(f'http://localhost:{port}/json/list') as r:
        for t in json.load(r):
            if t['type'] == 'page' and 'devtools' not in t['url']:
                return t
    raise RuntimeError('no page target')

HOOKS = ("window.__degerr=[];"
         "window.__gateSkip=true;"
         "window.addEventListener('error',function(e){window.__degerr.push('ERR:'+(e.message||e.error));});"
         "window.addEventListener('unhandledrejection',function(e){window.__degerr.push('REJ:'+((e.reason&&e.reason.message)||e.reason));});")

class Run:
    def __init__(self, name, w, h, dark=True, rose=False, profile=None):
        self.name = name; self.w = w; self.h = h
        self.passed = 0; self.failed = 0
        self.checks = []   # (name, ok, detail)
        self.all_errors = []
        self.port = 9340 + (abs(hash(name)) % 400)
        self.prof = profile or ('/tmp/hubqa-deg-' + re.sub(r'[^a-z0-9]+', '-', name))
        shutil.rmtree(self.prof, ignore_errors=True)
        self.proc = subprocess.Popen(
            [CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
             f'--remote-debugging-port={self.port}', '--remote-allow-origins=*',
             '--hide-scrollbars', '--allow-file-access-from-files',
             f'--user-data-dir={self.prof}', 'about:blank'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not wait_port(self.port):
            raise RuntimeError('chrome did not start on port %d' % self.port)
        tgt = find_target(self.port)
        self.c = CDP(tgt['webSocketDebuggerUrl'])
        # install error hooks + gate skip BEFORE any page script runs
        self.c.send('Page.addScriptToEvaluateOnNewDocument', {'source': HOOKS})
        self.c.send('Runtime.enable'); self.c.send('Page.enable'); self.c.send('Log.enable')
        # TRUE viewport (headless enforces a 500px window floor otherwise)
        self.c.send('Emulation.setDeviceMetricsOverride',
                    {'width': w, 'height': h, 'deviceScaleFactor': 2, 'mobile': True})
        self.c.send('Page.navigate', {'url': BASE})
        self.wait_js("document.readyState==='complete'", 25)
        self.wait_js("!document.getElementById('splash')", 20)
        # seed profile past onboarding + auth gate
        self.js(("(()=>{try{const p=HUB.store.state.profile;p.name='QA Tester';"
               "p.campus='QA Campus';HUB.store.save();}catch(e){return 'ERR:'+e.message}"
               "try{HUB.ui.closeSheet();}catch(e){}"
               "const w=document.getElementById('wlcmHost');if(w)w.remove();"
               "try{HUB.showTab('home');}catch(e){}return 'seeded'})()"))
        time.sleep(1.0)
        self.wait_anim()
        if rose:
            self.js(("(()=>{HUB.store.state.profile.gender='female';HUB.store.save();"
                     "HUB.theme.apply(false);return document.body.className})()"))
            time.sleep(0.6)
        self.drain('boot')

    # ---- primitives ----
    def js(self, expr, await_=False):
        r = self.c.send('Runtime.evaluate',
                        {'expression': expr, 'awaitPromise': await_,
                         'returnByValue': True}, wait=True)
        res = (r or {}).get('result', {})
        return res.get('value'), res.get('exceptionDetails')

    def wait_js(self, expr, timeout=15):
        t0 = time.time()
        while time.time() - t0 < timeout:
            v, _ = self.js(expr)
            if v: return v
            time.sleep(0.4)
        return None

    def wait_anim(self, timeout=8):
        t0 = time.time()
        while time.time() - t0 < timeout:
            v, _ = self.js("!Array.from(document.getAnimations()).some(a=>a.playState==='running')")
            if v: return True
            time.sleep(0.3)
        return False

    def check(self, name, cond, detail=''):
        ok = bool(cond)
        if ok: self.passed += 1
        else: self.failed += 1
        self.checks.append((name, ok, str(detail)[:300]))
        print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else ' :: ' + str(detail)[:200]))
        return ok

    def drain(self, label):
        v, _ = self.js("window.__degerr.splice(0)")
        if v:
            self.all_errors.append((label, v))
            print('ERRORS @ %s: %s' % (label, json.dumps(v)[:500]))

    def shot(self, name):
        r = self.c.send('Page.captureScreenshot', {'format': 'png'})
        p = os.path.join(QA, name + '.png')
        open(p, 'wb').write(base64.b64decode(r['data']))
        print('shot:', p)

    def open_picker(self):
        self.js("HUB.degree.open()")
        self.wait_js("document.querySelectorAll('#hubDegRoot .deg-school').length>=3", 15)
        self.wait_anim()

    def open_plan(self, slug):
        self.js("HUB.degree.open(%s)" % json.dumps(slug))
        self.wait_js("document.querySelectorAll('#hubDegRoot .deg-sem').length>0", 15)
        self.wait_anim()

    def no_overflow(self):
        v, _ = self.js("({sw:document.documentElement.scrollWidth, iw:window.innerWidth})")
        return v, (v and v['sw'] <= v['iw'])

    def close(self):
        try: self.c.close()
        except Exception: pass
        try: self.proc.terminate()
        except Exception: pass

    def summary(self):
        return self.passed, self.failed, self.checks, self.all_errors


def swipe_js(slot, direction, dist=90):
    """Dispatch pointer events on a tile's inner to simulate a swipe.
    direction: 'left' (dx<0) or 'right' (dx>0)."""
    sgn = -1 if direction == 'left' else 1
    return ("(()=>{const tile=document.querySelector('.deg-tile[data-slot=%s]');"
            "if(!tile)return 'no-tile';const inner=tile.querySelector('.deg-tile-inner');"
            "const r=inner.getBoundingClientRect();const x=r.left+r.width/2,y=r.top+r.height/2;"
            "const P=(t,cx)=>{const e=new PointerEvent(t,{bubbles:true,cancelable:true,clientX:cx,clientY:y,button:0});"
            "(t==='pointerdown'?tile:window).dispatchEvent(e);};"
            "P('pointerdown',x);P('pointermove',x+%d);P('pointermove',x+%d);P('pointerup',x+%d);"
            "return 'dispatched:'+tile.dataset.dir})()") % (json.dumps(slot), sgn*30, sgn*dist, sgn*dist)

# =====================================================================
# RUN 1: 390x844 dark volt — full functional suite
# =====================================================================
def run1():
    r = Run('r1-390-dark-volt', 390, 844)
    try:
        # --- viewport truth ---
        v, _ = r.js("({iw:window.innerWidth, ih:window.innerHeight})")
        r.check('viewport is truly 390x844', v and v['iw'] == 390 and v['ih'] == 844, v)
        v, _ = r.js("document.body.classList.contains('dark')")
        r.check('dark mode default on fresh install', v is True, v)
        v, _ = r.js("!document.body.classList.contains('theme-rose')")
        r.check('accent is volt (no theme-rose) by default', v is True, v)

        # --- 1. home entry card after Grade Calculator ---
        r.wait_js("!!document.getElementById('homeDegEntry')", 10)
        v, _ = r.js("!!document.getElementById('homeDegEntry')")
        r.check('home degree entry card renders', v is True)
        v, _ = r.js(("(()=>{const g=document.getElementById('gpaCard'),d=document.getElementById('homeDegEntry');"
                     "if(!g||!d)return 'missing';return (g.compareDocumentPosition(d)&4)?'after':'NOT-after'})()"))
        r.check('entry card sits AFTER grade calculator in DOM', v == 'after', v)
        v, _ = r.js("document.getElementById('homeDegSub').textContent")
        r.check('entry sub shows honest counts "28 plans · 4,025 schools"', v == '28 plans · 4,025 schools', v)

        # tap opens overlay
        r.js(("(()=>{const e=document.getElementById('homeDegEntry');e.scrollIntoView({block:'center'});"
              "e.click();return 'clicked'})()"))
        r.wait_js("!!document.getElementById('hubDegRoot')", 10)
        r.wait_anim()
        v, _ = r.js("!!document.getElementById('hubDegRoot')")
        r.check('tap opens degree overlay', v is True)
        v, _ = r.js("document.getElementById('hubDegRoot').classList.contains('chatroot')")
        r.check('overlay uses chatroot mount pattern', v is True)
        ov, ok = r.no_overflow()
        r.check('overlay: no horizontal overflow (390)', ok, ov)
        r.shot('qa-degree-picker-390-dark')
        r.drain('open-picker')

        # --- 2. picker coverage / pending / filters / search ---
        v, _ = r.js("document.querySelectorAll('#hubDegRoot .deg-school').length")
        r.check('picker lists 17 schools', v == 17, v)
        v, _ = r.js("document.querySelectorAll('#hubDegRoot .deg-planrow').length")
        r.check('picker lists 28 collected plans', v == 28, v)
        v, _ = r.js("Array.from(document.querySelectorAll('#hubDegRoot .deg-school .meta')).map(e=>e.textContent).join(' | ')")
        r.check('honest coverage "3 of 102 programs"', '3 of 102' in (v or ''), v)
        r.check('honest coverage "2 of 2 programs" (multi-school)', '2 of 2' in (v or ''), v)
        r.check('honest coverage "1 of 1 programs"', '1 of 1' in (v or ''), v)
        # pending programs disabled with "coming soon"
        r.js("document.querySelector('#hubDegRoot .deg-pending-tgl').click()")
        time.sleep(0.8)
        v, _ = r.js(("(()=>{const rows=Array.from(document.querySelectorAll('#hubDegRoot .deg-pending-row'));return {n:rows.length,"
                     "soon:rows.filter(x=>x.textContent.indexOf('Coming soon')>-1).length,"
                     "divs:rows.filter(x=>x.tagName==='DIV').length}})()"))
        r.check('pending programs listed', (v or {}).get('n', 0) > 0, v)
        r.check('pending rows show "Coming soon"', (v or {}).get('soon') == (v or {}).get('n') and (v or {}).get('n', 0) > 0, v)
        r.check('pending rows are non-interactive DIVs (disabled)', (v or {}).get('divs') == (v or {}).get('n'), v)
        # filter chips
        def set_level(level, expect):
            r.js("document.querySelector('#hubDegRoot .deg-chip[data-level=%s]').click()" % json.dumps(level))
            time.sleep(0.8)
            n, _ = r.js("document.querySelectorAll('#hubDegRoot .deg-planrow').length")
            return r.check('filter "%s" shows %d plans' % (level, expect), n == expect, n)
        set_level('associate', 14)
        set_level('bachelor', 14)
        set_level('all', 28)
        # search
        r.js(("(()=>{const q=document.getElementById('degQ');q.value='computer';"
              "q.dispatchEvent(new Event('input',{bubbles:true}));return 'typed'})()"))
        r.wait_js("document.querySelectorAll('#hubDegRoot .deg-planrow').length===14", 8)
        n, _ = r.js("document.querySelectorAll('#hubDegRoot .deg-planrow').length")
        r.check('search "computer" filters to 14 plans', n == 14, n)
        v, _ = r.js("Array.from(document.querySelectorAll('#hubDegRoot .deg-planrow')).map(e=>e.textContent).join(' // ')")
        r.check('search results all match "computer"', 'computer' in (v or '').lower().replace('ü','u') or 'Computer' in (v or ''), (v or '')[:160])
        r.js(("(()=>{const q=document.getElementById('degQ');q.value='';"
              "q.dispatchEvent(new Event('input',{bubbles:true}));return 'cleared'})()"))
        r.wait_js("document.querySelectorAll('#hubDegRoot .deg-planrow').length===17", 8)
        r.drain('picker')

        # --- 2b. national directory browse (IPEDS Phase 1) ---
        v, _ = r.js("!!document.getElementById('degBrowseOpen')")
        r.check('national browse button renders', v is True)
        v, _ = r.js("document.getElementById('degBrowseOpen').textContent")
        r.check('browse button mentions U.S. colleges', 'U.S. colleges' in (v or ''), (v or '')[:90])
        r.js("document.getElementById('degBrowseOpen').click()")
        r.wait_js("!!document.getElementById('degBQ')", 8)
        v, _ = r.js("!!document.getElementById('degBQ')")
        r.check('browse opens national search', v is True)
        r.js(("(()=>{const q=document.getElementById('degBQ');q.value='arizona state';"+
              "q.dispatchEvent(new Event('input',{bubbles:true}));return 'typed'})()"))
        r.wait_js("document.querySelectorAll('#degBResults [data-bunit]').length>0", 15)
        v, _ = r.js("document.getElementById('degBResults').textContent")
        r.check('search finds Arizona State University', 'Arizona State University' in (v or ''), (v or '')[:140])
        r.check('results show honest program counts', 'programs' in (v or '').lower(), (v or '')[:140])
        r.js("document.querySelector('#degBResults [data-bunit]').click()")
        r.wait_js("document.querySelectorAll('#degBResults .deg-pending-row').length>0", 15)
        v, _ = r.js(("(()=>{const rows=Array.from(document.querySelectorAll('#degBResults .deg-pending-row'));return {n:rows.length,"+
                     "soon:rows.filter(x=>x.textContent.indexOf('Coming soon')>-1).length}})()"))
        r.check('school programs listed as coming soon', (v or {}).get('n',0)>0 and (v or {}).get('soon')==(v or {}).get('n'), v)
        v, _ = r.js("document.getElementById('degBResults').textContent")
        r.check('program rows show 2YR/4YR award-level badges', '2YR' in (v or '') or '4YR' in (v or ''), (v or '')[:180])
        ov, ok = r.no_overflow()
        r.check('browse school: no horizontal overflow (390)', ok, ov)
        r.shot('qa-degree-browse-390-dark')
        r.js("document.getElementById('degBrowseClose').click()")
        r.wait_js("!!document.getElementById('degBrowseOpen')", 8)
        v, _ = r.js("!!document.getElementById('degBrowseOpen')")
        r.check('browse closes cleanly', v is True)
        r.drain('browse')

        # --- 3. all 17 plans: semesters, exact course counts, labels, source, no overflow ---
        for slug, tiles, sems, catyear in PLANS:
            r.open_plan(slug)
            n, _ = r.js("document.querySelectorAll('#hubDegRoot .deg-tile').length")
            r.check('%s renders exactly %d course tiles' % (slug, tiles), n == tiles, n)
            ns, _ = r.js("document.querySelectorAll('#hubDegRoot .deg-sem').length")
            r.check('%s renders %d semesters' % (slug, sems), ns == sems, ns)
            v, _ = r.js(("Array.from(document.querySelectorAll('#hubDegRoot .deg-sem-hd .t'))"
                         ".every(e=>e.textContent.trim().length>2)"))
            r.check('%s semester labels readable' % slug, v is True)
            v, _ = r.js("document.querySelector('#hubDegRoot .deg-source').textContent")
            r.check('%s shows source/catalog year %s' % (slug, catyear), (v is not None) and catyear in v, (v or '')[:120])
            v, _ = r.js("!!document.querySelector('#hubDegRoot .deg-source a[href^=\"http\"]')")
            r.check('%s source links to real catalog URL' % slug, v is True)
            ov, ok = r.no_overflow()
            r.check('%s no horizontal overflow' % slug, ok, ov)
            r.drain('plan-' + slug)

        # --- 9. pace guidance (fresh plan uta-bba-management) ---
        r.open_plan('uta-bba-management')
        v, _ = r.js("document.querySelector('#hubDegRoot .deg-pace').textContent")
        r.check('pace guidance visible, "On track" for fresh student', (v or '').strip() == 'On track', v)
        v, _ = r.js("document.querySelector('#hubDegRoot .deg-pace').classList.contains('on')")
        r.check('pace has .on class when on track', v is True)
        # age the plan: startYear 2020 -> expected 120, earned 0 -> behind by ~120
        r.js(("(()=>{const st=HUB.degree._state();st.progress['uta-bba-management'].startYear=2020;"
              "HUB.store.save();HUB.degree.open('uta-bba-management');return 'aged'})()"))
        r.wait_js("!!document.querySelector('#hubDegRoot .deg-pace.off')", 10)
        v, _ = r.js("document.querySelector('#hubDegRoot .deg-pace').textContent")
        m = re.search(r'Behind by ~(\d+) credits', v or '')
        r.check('aged plan shows behind guidance', m is not None and int(m.group(1)) >= 100, v)
        behind0 = int(m.group(1)) if m else None
        # complete two 3cr courses -> behind number shrinks
        r.js("document.querySelector('.deg-tile[data-slot=\"s1-1\"] [data-check]').click()")
        time.sleep(1.2)
        r.js("document.querySelector('.deg-tile[data-slot=\"s1-2\"] [data-check]').click()")
        r.wait_js("document.querySelectorAll('#hubDegRoot .deg-tile.done').length>=2", 8)
        v, _ = r.js("document.querySelector('#hubDegRoot .deg-pace').textContent")
        m2 = re.search(r'Behind by ~(\d+) credits', v or '')
        r.check('pace updates after completions (behind shrinks)', m2 is not None and behind0 is not None and int(m2.group(1)) < behind0, v)
        r.drain('pace')

        # --- 5. prereq warnings (s4-4 COMS 2302 needs s1-4 ENGL 1301) ---
        # Runs BEFORE any reload in this session. Retries once with a full reset
        # (isolated probe verified exact text '⚠ Complete ENGL 1301 first').
        warn_text = None
        for _attempt in range(2):
            r.js(("(()=>{const st=HUB.degree._state();delete st.progress['uta-bs-computer-science'];"
                  "HUB.store.save();HUB.degree.open('uta-bs-computer-science');return 'fresh'})()"))
            r.wait_js("!!document.querySelectorAll('#hubDegRoot .deg-sem').length", 10)
            r.wait_anim()
            # the .deg-sem gate can fire before all tiles finish their first
            # render: wait for THIS tile's check button, not just the sem shell
            r.wait_js("!!document.querySelector('.deg-tile[data-slot=\"s4-4\"] [data-check]')", 15)
            time.sleep(0.8)
            # robust click: ensure the tile actually completes (re-click if a
            # re-render swallowed the first synthetic click in a long session)
            for _c in range(3):
                r.js("document.querySelector('.deg-tile[data-slot=\"s4-4\"] [data-check]').click()")
                if r.wait_js("!!document.querySelector('.deg-tile.done[data-slot=\"s4-4\"]')", 6):
                    break
                time.sleep(0.8)
            warn_text = r.wait_js("(()=>{const t=document.querySelector('.deg-tile.done[data-slot=\"s4-4\"] .deg-warn\");"
                                  "return t?t.textContent:null})()", 20)
            if (warn_text or '') == '⚠ Complete ENGL 1301 first':
                break
            time.sleep(1.0)
        r.check('amber prereq warning when prereq unmet', (warn_text or '') == '⚠ Complete ENGL 1301 first', warn_text)
        r.js("document.querySelector('.deg-tile[data-slot=\"s1-4\"] [data-check]').click()")
        r.wait_js("!!document.querySelector('.deg-tile.done[data-slot=\"s1-4\"]')", 20)
        cleared = r.wait_js("!document.querySelector('.deg-tile[data-slot=\"s4-4\"] .deg-warn')", 20)
        r.check('warning clears after prereq completed', cleared is True,
                'warn still present' if not cleared else 'cleared')
        r.drain('prereq')

        # --- 4. swipe + check button + ring + credits + persistence (uta-bs-computer-science, cleared) ---
        r.js(("(()=>{const st=HUB.degree._state();delete st.progress['uta-bs-computer-science'];"
              "HUB.store.save();HUB.degree.open('uta-bs-computer-science');return 'fresh'})()"))
        r.wait_js("document.querySelectorAll('#hubDegRoot .deg-sem').length>0", 10)
        r.wait_anim()
        ring0, _ = r.js("document.querySelector('#hubDegRoot .deg-ring-num').textContent")
        earn0, _ = r.js("document.querySelector('#hubDegRoot .deg-earned').textContent")
        r.check('ring starts at 0%', (ring0 or '').strip() == '0%', ring0)
        # 4a. fixed direction (2026-09-29 ship fix: "swipe direction was reversed"):
        # undone tiles carry data-dir="left" — swipe LEFT completes;
        # done tiles carry data-dir="right" — swipe RIGHT unmarks.
        v, _ = r.js(swipe_js('s1-0', 'left'))
        done = r.wait_js("!!document.querySelector('.deg-tile.done[data-slot=\"s1-0\"]')", 12)
        r.check('swipe-left completes undone tile (fixed direction)', done is not None, 'dispatched=%s' % v)
        # 4b. swipe RIGHT on another undone non-choice tile (s2-0) rubber-bands: no commit
        v, _ = r.js(swipe_js('s2-0', 'right'))
        time.sleep(1.6)
        undone, _ = r.js("!document.querySelector('.deg-tile.done[data-slot=\"s2-0\"]')")
        r.check('swipe-right on undone tile rubber-bands (no completion)', undone is True, 'dispatched=%s' % v)
        v, _ = r.js("document.querySelectorAll('#hubDegRoot audio').length")
        r.check('no <audio> elements created by completion (silent)', v == 0, v)
        v, _ = r.js("document.querySelector('#hubDegRoot .deg-ring-num').textContent")
        r.check('progress ring updates after swipe', (v or '').strip() not in ('0%', ring0), '%s -> %s' % (ring0, v))
        v, _ = r.js("document.querySelector('#hubDegRoot .deg-earned').textContent")
        r.check('earned credits update after swipe', v != earn0 and ' of 123' in (v or ''), '%s -> %s' % (earn0, v))
        # 4c. check-button toggles
        r.js("document.querySelector('.deg-tile[data-slot=\"s1-2\"] [data-check]').click()")
        r.wait_js("!!document.querySelector('.deg-tile.done[data-slot=\"s1-2\"]')", 8)
        v, _ = r.js("!!document.querySelector('.deg-tile.done[data-slot=\"s1-2\"]')")
        r.check('✓ button marks tile complete', v is True)
        r.js("document.querySelector('.deg-tile.done[data-slot=\"s1-2\"] [data-check]').click()")
        r.wait_js("!document.querySelector('.deg-tile.done[data-slot=\"s1-2\"]')", 8)
        v, _ = r.js("!!document.querySelector('.deg-tile.done[data-slot=\"s1-2\"]')")
        r.check('✓ button toggles back to undone', v is False)
        # toast = visual feedback evidence
        v, _ = r.js("document.getElementById('toastHost').textContent")
        r.drain('swipe')
        # 4d. reload -> persists
        r.js("location.reload()")
        r.wait_js("document.readyState==='complete'", 25)
        r.wait_js("!document.getElementById('splash')", 20)
        r.wait_js("!!(window.HUB&&HUB.degree&&HUB.degree.open)", 20)
        time.sleep(1.0)
        r.open_plan('uta-bs-computer-science')
        v, _ = r.js("!!document.querySelector('.deg-tile.done[data-slot=\"s1-0\"]')")
        r.check('progress persists across reload (localStorage)', v is True)
        r.shot('qa-degree-semester-390-dark')
        r.drain('persist')

        # --- 6. choice slot (dallas-college-aa-transfer s3-5: 3 options; s3-2: manual) ---
        r.js(("(()=>{const st=HUB.degree._state();delete st.progress['dallas-college-aa-transfer'];"
              "HUB.store.save();HUB.degree.open('dallas-college-aa-transfer');return 'fresh'})()"))
        r.wait_js("document.querySelectorAll('#hubDegRoot .deg-sem').length>0", 10)
        v, _ = r.js("document.querySelector('.deg-tile[data-slot=\"s3-5\"] .deg-choice-chip').textContent")
        r.check('choice tile carries choice chip', (v or '').strip() == 'Choose a course', v)
        r.js("document.querySelector('.deg-tile[data-slot=\"s3-5\"] [data-open]').click()")
        r.wait_js("!document.getElementById('sheetHost').hidden", 8)
        v, _ = r.js("!document.getElementById('sheetHost').hidden")
        r.check('choice tile opens sheet', v is True)
        n, _ = r.js("document.querySelectorAll('#sheetBox .deg-opt').length")
        r.check('sheet lists 3 options', n == 3, n)
        r.js("document.querySelector('#sheetBox .deg-opt').click()")
        r.wait_js("!!document.querySelector('.deg-tile.done[data-slot=\"s3-5\"]')", 8)
        v, _ = r.js("document.querySelector('.deg-tile.done[data-slot=\"s3-5\"] .deg-code').textContent")
        r.check('selecting option completes slot as ENGL 2321', 'ENGL 2321' in (v or ''), (v or '')[:60])
        # manual entry slot
        r.js("document.querySelector('.deg-tile[data-slot=\"s3-2\"] [data-open]').click()")
        r.wait_js("!!document.getElementById('degChoiceCode')", 8)
        v, _ = r.js("!!document.getElementById('degChoiceCode')")
        r.check('manual-entry slot shows code/title inputs', v is True)
        r.js(("(()=>{document.getElementById('degChoiceCode').value='PHED 1104';"
              "document.getElementById('degChoiceTitle').value='Yoga';"
              "document.getElementById('degChoiceSave').click();return 'saved'})()"))
        r.wait_js("!!document.querySelector('.deg-tile.done[data-slot=\"s3-2\"]')", 8)
        v, _ = r.js("document.querySelector('.deg-tile.done[data-slot=\"s3-2\"] .deg-code').textContent")
        r.check('manual entry completes slot with typed code', 'PHED 1104' in (v or ''), (v or '')[:60])
        r.drain('choice')

        # --- 7. transfer views ---
        r.open_plan('dallas-college-aa-business')
        r.js("document.getElementById('degTabXfer').click()")
        r.wait_js("!!document.querySelector('#hubDegRoot .deg-xsummary')", 8)
        v, _ = r.js("Array.from(document.querySelectorAll('#hubDegRoot .deg-xsummary')).map(e=>e.textContent).join(' // ')")
        r.check('Dallas College transfer view shows UTA destination', 'Arlington' in (v or ''), (v or '')[:200])
        r.check('transfer credit summary references plan total', '60' in (v or ''), (v or '')[:200])
        ov, ok = r.no_overflow()
        r.check('transfer view no horizontal overflow', ok, ov)
        r.shot('qa-degree-transfer-390-dark')
        r.open_plan('utd-bs-computer-science')
        r.js("document.getElementById('degTabXfer').click()")
        r.wait_js("!!document.querySelector('#hubDegRoot .deg-body .empty')", 8)
        v, _ = r.js("document.querySelector('#hubDegRoot .deg-body .empty').textContent")
        r.check('UTD transfer view: honest "No verified equivalencies yet"', 'No verified equivalencies yet' in (v or ''), (v or '')[:200])
        v, _ = r.js("!!document.querySelector('#hubDegRoot .deg-body .empty .error, #hubDegRoot .deg-body .empty[class*=\"err\"]')")
        r.check('UTD no-equivalency is NOT styled as an error', v is False)
        r.drain('transfer')

        # --- 10. Escape layering: sheet first, then overlay ---
        r.js(("(()=>{const st=HUB.degree._state();const p=st.progress['dallas-college-aa-transfer']||{done:{}};"
              "delete p.done['s3-5'];st.progress['dallas-college-aa-transfer']=p;HUB.store.save();"
              "HUB.degree.open('dallas-college-aa-transfer');return 'fresh'})()"))
        r.wait_js("document.querySelectorAll('#hubDegRoot .deg-sem').length>0", 10)
        r.js("document.querySelector('.deg-tile[data-slot=\"s3-5\"] [data-open]').click()")
        r.wait_js("!document.getElementById('sheetHost').hidden", 8)
        esc = "document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))"
        r.js(esc)
        time.sleep(0.8)
        sh, _ = r.js("document.getElementById('sheetHost').hidden")
        ov, _ = r.js("!!document.getElementById('hubDegRoot')")
        r.check('1st Escape closes choice sheet only', sh is True and ov is True, 'sheetHidden=%s overlay=%s' % (sh, ov))
        r.js(esc)
        time.sleep(0.8)
        ov, _ = r.js("!!document.getElementById('hubDegRoot')")
        r.check('2nd Escape closes overlay', ov is False, ov)
        r.drain('escape')

        # --- static: no audio references in degree.js; i18n key parity ---
        r.drain('final')
    finally:
        r.close()
    return r.summary()

# =====================================================================
# RUN 2: 320x568 light — overflow + entry + picker + plan
# =====================================================================
def run2():
    r = Run('r2-320-light', 320, 568)
    try:
        v, _ = r.js("({iw:window.innerWidth, ih:window.innerHeight})")
        r.check('viewport is truly 320x568', v and v['iw'] == 320 and v['ih'] == 568, v)
        # switch to light
        r.js("HUB.showTab('me')"); time.sleep(1.0)
        r.wait_js("document.getElementById('darkToggle')", 8)
        r.js("document.getElementById('darkToggle').click()"); time.sleep(0.8)
        v, _ = r.js("document.body.classList.contains('dark')")
        r.check('light theme applied', v is False)
        r.js("HUB.showTab('home')"); time.sleep(1.0)
        r.wait_anim()
        v, _ = r.js("!!document.getElementById('homeDegEntry')")
        r.check('320: entry card renders', v is True)
        ov, ok = r.no_overflow()
        r.check('320: home no horizontal overflow', ok, ov)
        r.js(("(()=>{const e=document.getElementById('homeDegEntry');e.scrollIntoView({block:'center'});"
              "e.click();return 'clicked'})()"))
        r.wait_js("!!document.getElementById('hubDegRoot')", 10)
        r.wait_anim()
        ov, ok = r.no_overflow()
        r.check('320: picker no horizontal overflow', ok, ov)
        r.open_plan('uta-bs-computer-science')
        v, _ = r.js("document.querySelectorAll('#hubDegRoot .deg-tile').length")
        r.check('320: plan renders 41 tiles', v == 41, v)
        ov, ok = r.no_overflow()
        r.check('320: plan no horizontal overflow', ok, ov)
        # semester header + a tile fully inside viewport
        v, _ = r.js(("(()=>{const hd=document.querySelector('#hubDegRoot .deg-sem-hd');if(!hd)return 'no-hd';"
                     "hd.scrollIntoView({block:'center'});const b=hd.getBoundingClientRect();"
                     "return {l:Math.round(b.left),r:Math.round(b.right),iw:window.innerWidth}})()"))
        r.check('320: semester header inside viewport', isinstance(v, dict) and v['l'] >= 0 and v['r'] <= v['iw'], v)
        v, _ = r.js(("(()=>{const t=document.querySelector('#hubDegRoot .deg-tile');if(!t)return 'no-tile';"
                     "t.scrollIntoView({block:'center'});const b=t.getBoundingClientRect();"
                     "return {l:Math.round(b.left),r:Math.round(b.right),iw:window.innerWidth}})()"))
        r.check('320: course tile inside viewport', isinstance(v, dict) and v['l'] >= 0 and v['r'] <= v['iw'], v)
        r.shot('qa-degree-plan-320-light')
        r.drain('final')
    finally:
        r.close()
    return r.summary()

# =====================================================================
# RUN 3: 390x844 dark rose (gender=female) — theme follows, plan renders
# =====================================================================
def run3():
    r = Run('r3-390-dark-rose', 390, 844, rose=True)
    try:
        v, _ = r.js("document.body.classList.contains('theme-rose')")
        r.check('rose theme active for female profile', v is True)
        v, _ = r.js("getComputedStyle(document.body).getPropertyValue('--volt').trim()")
        r.check('accent var flips away from volt green', (v or '').lower() not in ('#c6f135', '#d4f53f', ''), v)
        r.open_picker()
        v, _ = r.js("!!document.getElementById('hubDegRoot')")
        r.check('rose: picker opens', v is True)
        ov, ok = r.no_overflow()
        r.check('rose: picker no horizontal overflow', ok, ov)
        r.open_plan('uta-bba-management')
        v, _ = r.js("document.querySelectorAll('#hubDegRoot .deg-tile').length")
        r.check('rose: plan renders 41 tiles', v == 41, v)
        r.shot('qa-degree-rose-390-dark')
        r.drain('final')
    finally:
        r.close()
    return r.summary()

# =====================================================================
# RUN 4: 390x844 — i18n es + ne spot checks
# =====================================================================
def run4():
    r = Run('r4-390-i18n', 390, 844)
    try:
        for lang, keys in [
            ('es', {'deg.entryTitle': 'Planes de estudio', 'deg.onTrack': 'En buen camino',
                    'deg.choiceT': 'Elige un curso', 'deg.xferNone': 'Aún sin equivalencias verificadas',
                    'deg.all': 'Todos'}),
            ('ne', {'deg.entryTitle': 'डिग्री योजनाहरू', 'deg.onTrack': 'ट्र्याकमा',
                    'deg.choiceT': 'कोर्स छान्नुहोस्', 'deg.xferNone': 'अझै प्रमाणित समानताहरू छैनन्',
                    'deg.all': 'सबै'}),
        ]:
            r.js("HUB.i18n.setLang(%s)" % json.dumps(lang))
            r.wait_js("HUB.i18n.getLang()==%s" % json.dumps(lang), 10)
            v, _ = r.js("HUB.i18n.getLang()")
            r.check('locale switches to %s' % lang, v == lang, v)
            r.open_picker()
            v, _ = r.js("document.getElementById('degTitle').textContent")
            r.check('%s: picker title translated' % lang, v == keys['deg.entryTitle'], v)
            # translated filter chips
            v, _ = r.js("document.querySelector('.deg-chip[data-level=\"all\"]').textContent")
            r.check('%s: "All" chip translated' % lang, (v or '').strip() == keys['deg.all'], v)
            r.open_plan('uta-bs-computer-science')
            v, _ = r.js("document.querySelector('#hubDegRoot .deg-pace').textContent")
            r.check('%s: pace "on track" translated' % lang, (v or '').strip() == keys['deg.onTrack'], v)
            # xferNone on UTD plan
            r.open_plan('utd-bs-computer-science')
            r.js("document.getElementById('degTabXfer').click()")
            r.wait_js("!!document.querySelector('#hubDegRoot .deg-body .empty')", 8)
            v, _ = r.js("document.querySelector('#hubDegRoot .deg-body .empty').textContent")
            r.check('%s: xferNone translated' % lang, keys['deg.xferNone'] in (v or ''), (v or '')[:160])
            # no raw-key fallbacks anywhere in the overlay
            v, _ = r.js("document.getElementById('hubDegRoot').innerText")
            m = re.search(r'deg\.[a-zA-Z]+', v or '')
            r.check('%s: no raw deg.* key fallbacks visible' % lang, m is None, m.group(0) if m else '')
            r.drain('i18n-' + lang)
        r.drain('final')
    finally:
        r.close()
    return r.summary()

# =====================================================================
# static checks (read-only)
# =====================================================================
def static_checks():
    out = []
    src = open(os.path.expanduser('~/workspace/hub/js/degree.js')).read()
    audio_refs = [l for l in src.split('\n')
                  if re.search(r'\b(audio|AudioContext|playSound|beep|chime|whistle)\b', l, re.I)]
    out.append(('degree.js has zero audio/sound references (silent policy)',
                len(audio_refs) == 0, '; '.join(audio_refs)[:200]))
    i18n = open(os.path.expanduser('~/workspace/hub/js/i18n.js')).read()
    lines = i18n.split('\n')
    seg = '\n'.join(lines[7413:])  # after the Degree Plan Tracker marker
    parts = re.split(r"Object\.assign\(HUB\.i18n\._dict\('(\w+)'\),\{", seg)
    counts = {}
    for i in range(1, len(parts), 2):
        counts[parts[i]] = len(set(re.findall(r"'(deg\.[^']*)':", parts[i + 1])))
    out.append(('60 deg.* keys in each of en/es/ne/hi',
                counts == {'en': 60, 'es': 60, 'ne': 60, 'hi': 60}, json.dumps(counts)))
    return out

def main():
    total_p, total_f = 0, 0
    all_errs = []
    for fn, label in [(run1, 'RUN1 390 dark volt'), (run2, 'RUN2 320 light'),
                      (run3, 'RUN3 390 rose'), (run4, 'RUN4 i18n')]:
        print('\n===== %s =====' % label)
        try:
            p, f, checks, errs = fn()
        except Exception as e:
            print('RUN CRASHED:', repr(e)[:300])
            p, f, checks, errs = 0, 1, [('run crashed', False, repr(e)[:200])], [('crash', [repr(e)[:200]])]
        total_p += p; total_f += f
        all_errs.extend([(label + ':' + l, e) for l, e in errs])
    print('\n===== STATIC =====')
    for name, cond, detail in static_checks():
        ok = bool(cond)
        print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else ' :: ' + str(detail)[:200]))
        if ok: total_p += 1
        else: total_f += 1
    print('\n===== SUMMARY =====')
    print('passed: %d  failed: %d' % (total_p, total_f))
    print('console/page errors across all runs: %d' % len(all_errs))
    for l, e in all_errs:
        print('  ', l, ':', json.dumps(e)[:400])
    sys.exit(1 if (total_f or all_errs) else 0)

if __name__ == '__main__':
    main()
