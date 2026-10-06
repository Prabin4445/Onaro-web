#!/usr/bin/env python3
"""3D map QA: fallback path, injected-lib path, dark style URL, geolocation paths."""
import json, subprocess, time, urllib.request, os, base64, sys
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors, checks = [], []
def note(ok, label, detail=''):
    checks.append((ok, label)); print(('PASS' if ok else 'FAIL'), label, str(detail)[:160])

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12); self.id = 0
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 15
        while time.time() < deadline:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:80])
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)

def launch(port, profile, inject_lib=False, extra_args=()):
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox',
        f'--remote-debugging-port={port}', '--remote-allow-origins=*', '--window-size=414,900',
        f'--user-data-dir={profile}', '--hide-scrollbars', '--allow-file-access-from-files',
        '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] + list(extra_args) + [BASE],
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
    c.send('Network.enable')
    if inject_lib:
        # inject after boot via Runtime.evaluate (addScriptToEvaluateOnNewDocument+reload was flaky)
        src = open(os.path.expanduser('~/workspace/hub/qa/vendor/maplibre-gl.js')).read()
        v, e = js(c, src + "\n;'injected:'+typeof maplibregl")
        print('inject result:', v, e)
    # wait for app scripts to boot
    for _ in range(25):
        v, _ = js(c, "typeof HUB")
        if v != 'undefined': break
        time.sleep(1)
    if inject_lib:
        # re-render discover now that the lib is present
        js(c, "HUB.showTab('discover')"); time.sleep(3)
    return proc, c

def js(c, expr):
    try:
        r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': False})
        res = (r or {}).get('result', {})
        return res.get('value'), (res.get('exceptionDetails') or {}).get('text')
    except Exception as e: return None, str(e)[:160]

def errhook(c):
    js(c, "window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")

def errs(c, label):
    v, _ = js(c, "window.__huberr.splice(0)")
    if v:
        errors.append((label, v)); print('CONSOLE-ERRORS @', label, ':', json.dumps(v)[:400])
    return v

def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)

mode = sys.argv[1] if len(sys.argv) > 1 else 'fallback'

if mode == 'fallback':
    proc, c = launch(9431, '/tmp/hubqa3d-fb')
    errhook(c)
    js(c, "HUB.showTab('discover')"); time.sleep(2)
    v, _ = js(c, "typeof maplibregl")
    note(v == 'undefined', 'fallback: maplibregl undefined (CDN blocked in sandbox)', v)
    v, _ = js(c, "!!document.querySelector('.map-fallback')")
    note(bool(v), 'fallback: honest fallback note rendered')
    v, _ = js(c, "document.querySelector('.map-fallback p') && document.querySelector('.map-fallback p').textContent")
    note('3D map unavailable' in (v or ''), 'fallback: honest copy present', (v or '')[:80])
    v, _ = js(c, "document.querySelectorAll('#dvList .item').length")
    note((v or 0) > 5, 'fallback: clean list view with items', v)
    v, _ = js(c, "document.querySelector('#dvSeg button[data-mode=\"list\"]') && (document.querySelector('#dvSeg button[data-mode=\"list\"]').click(), true)")
    time.sleep(1)
    v2, _ = js(c, "!!document.querySelector('#dvList')")
    note(bool(v2), 'fallback: Map/List toggle still works')
    shot(c, 'w3d-fallback')
    errs(c, 'fallback')
    proc.terminate()

elif mode == 'inject':
    proc, c = launch(9432, '/tmp/hubqa3d-inj', inject_lib=True)
    errhook(c)
    style_urls = []
    # poll network via performance entries instead
    js(c, "HUB.showTab('discover')"); time.sleep(3)
    v, _ = js(c, "typeof maplibregl")
    note(v != 'undefined', 'inject: maplibre lib present', v)
    v, _ = js(c, "(()=>{const t=document.createElement('canvas');return !!(t.getContext('webgl2')||t.getContext('webgl'));})()")
    note(bool(v), 'inject: WebGL available for canvas', v)
    v, _ = js(c, "document.querySelectorAll('#dvMap canvas').length")
    note((v or 0) >= 1, 'inject: map canvas initialized', v)
    v, _ = js(c, "document.querySelectorAll('.orbit-pin').length")
    exp, _ = js(c, "document.querySelectorAll('.orbit-pin').length")
    note((v or 0) > 5, 'inject: pins rendered as markers', v)
    v, _ = js(c, "document.getElementById('dvGeoChip') && document.getElementById('dvGeoChip').textContent")
    note('Locating' in (v or '') or 'campus area' in (v or '') or 'community area' in (v or '') or 'Your location' in (v or ''), 'inject: geo status chip present (incl. honest community-area fallback)', (v or '')[:90])
    # click first pin -> should navigate to market or work tab or open sheet
    v, _ = js(c, "(()=>{const p=document.querySelector('.orbit-pin'); if(!p) return 'no-pin'; p.click(); return 'clicked';})()")
    time.sleep(1)
    v2, _ = js(c, "(()=>{const on=document.querySelector('.tab.active'); return on?on.dataset.tab:'?';})()")
    v3, _ = js(c, "!document.getElementById('sheetHost').hidden")
    note(v2 in ('market', 'work') or v3, 'inject: pin tap opens detail destination', f'tab={v2} sheet={v3}')
    shot(c, 'w3d-inject')
    errs(c, 'inject')
    proc.terminate()

elif mode == 'dark':
    proc, c = launch(9433, '/tmp/hubqa3d-dark', inject_lib=True)
    errhook(c)
    c.send('Network.enable')
    js(c, "document.body.classList.add('dark'); HUB.showTab('discover')"); time.sleep(3)
    v, _ = js(c, "performance.getEntriesByType('resource').map(r=>r.name).filter(u=>u.includes('openfreemap.org/styles')).join('|')")
    note('styles/dark' in (v or ''), 'dark: dark planet style requested', (v or '')[:100])
    shot(c, 'w3d-dark')
    errs(c, 'dark')
    proc.terminate()

elif mode == 'geo':
    proc, c = launch(9434, '/tmp/hubqa3d-geo', inject_lib=True)
    errhook(c)
    # force geolocation success
    c.send('Browser.grantPermissions', {'origin': 'file://', 'permissions': ['geolocation']})
    c.send('Emulation.setGeolocationOverride', {'latitude': 32.72, 'longitude': -117.16, 'accuracy': 20})
    js(c, "HUB.showTab('discover')"); time.sleep(7)
    v, _ = js(c, "document.getElementById('dvGeoChip') && document.getElementById('dvGeoChip').textContent")
    note('Your location' in (v or ''), 'geo: live location label on success', (v or '')[:70])
    v, _ = js(c, "document.querySelectorAll('.orbit-loc').length")
    note((v or 0) >= 1, 'geo: pulsing location dot rendered', v)
    shot(c, 'w3d-geo')
    errs(c, 'geo')
    proc.terminate()


elif mode == 'world':
    CITIES = [('Kathmandu',27.7172,85.3240),('London',51.5074,-0.1278),('SaoPaulo',-23.5558,-46.6396),('Tokyo',35.6762,139.6503)]
    proc, c = launch(9435, '/tmp/hubqa3d-world', inject_lib=True)
    errhook(c)
    for name, lat, lng in CITIES:
        js(c, f"HUB.store.state.profile.campus=[{name!r},][0];HUB.store.state.profile.campusCoords=[{lat},{lng}];HUB.store.save();HUB.showTab('discover')")
        time.sleep(2.5)
        v, _ = js(c, "HUB.discover&&HUB.discover.mapCenter()")
        ok = bool(v) and abs(v[0]-lat)<0.1 and abs(v[1]-lng)<0.1
        note(ok, f'world: {name} camera centers on campus', f'{v}')
        mc, _ = js(c, "(()=>{try{return document.querySelectorAll('#dvMap canvas').length}catch(e){return -1}})()")
        note(mc>=1, f'world: {name} map canvas live', mc)
        shot(c, 'w3d-'+name.lower())
    # also confirm the map label reads the campus name
    lb, _ = js(c, "HUB.discover&&HUB.discover.mapLabel()")
    note('Tokyo' in (lb or ''), 'world: map label shows picked campus', (lb or '')[:60])
    errs(c, 'world')
    proc.terminate()

print('----')
print('checks:', sum(1 for ok, _ in checks if ok), '/', len(checks), 'passed')
print('console-error rounds with errors:', len(errors))
