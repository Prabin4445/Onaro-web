#!/usr/bin/env python3
"""Edit Profile sheet fit QA (PraBin's iPhone bug, 2026-09-23).

Root cause: .sheethost used flex centering (justify-content:center) on a
position:fixed container; iOS Safari mis-centered it and the whole sheet
rendered ~87px too far right, cut off at the screen edge. Fix: absolute
bottom-docking via left:50% + translateX(-50%) (same pattern as
.tabbar/.toasthost/.askpill), dedicated sheetUpC keyframes (shared sheetUp
left untouched for .chatpanel), and min-width:0 on .seg buttons so the
4-option gender seg can never stretch its container.

Asserts, at 390x844 and 320x568, dark+light, fresh profiles, zero console errors:
- sheet left edge ~= 0 and right edge <= viewport (stays fixed on screen)
- document has no horizontal overflow
- all 4 gender seg buttons fully inside the viewport (edit profile + onboarding)
- German long labels ("Lieber nicht sagen") also fit at 320
- no banned purple in the sheet
"""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9490
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []

def note(ok, label, detail=''):
    checks.append((ok, label)); print(('PASS' if ok else 'FAIL'), label, detail)

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

SHEET_JS = """(function(){
const sh=document.getElementById('sheetBox');if(!sh||sh.parentElement.hidden)return null;
const r=sh.getBoundingClientRect();
const seg=document.getElementById('peditGender');
const btns=seg?[...seg.querySelectorAll('button')].map(b=>{const x=b.getBoundingClientRect();
  return {l:Math.round(x.left),r:Math.round(x.right)};}):[];
return {l:Math.round(r.left),r:Math.round(r.right),w:Math.round(r.width),
  doc:document.documentElement.scrollWidth,vp:innerWidth,btns};})()"""
OBSEG_JS = """(function(){const r=document.getElementById('obGender');if(!r)return null;
return [...r.querySelectorAll('button')].map(b=>{const x=b.getBoundingClientRect();
  return {l:Math.round(x.left),r:Math.round(x.right)};});})()"""

def run_case(width, height, theme):
    prof = f'/tmp/hubqa-meicon2-{width}-{theme}'
    shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof, exist_ok=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        f'--window-size={width},{height}',
        f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tag = f'{width}x{height}-{theme}'
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as rr:
                    ts = json.load(rr)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        c.send('Emulation.setDeviceMetricsOverride', {'width': width, 'height': height,
               'deviceScaleFactor': 2, 'mobile': True})
        def js(expr):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
                if r and 'exceptionDetails' in r:
                    ed = r['exceptionDetails']
                    return 'THREW:' + str(ed.get('exception', {}).get('description', ed.get('text', '')))[:160]
                return (r or {}).get('result', {}).get('value')
            except Exception as e: return 'JSERR:' + str(e)[:120]
        def js_wait_ready(timeout=20):
            # Page.reload() returns at initiation, not completion: a js() call issued
            # too early runs in the discarded context. Poll readyState first.
            dl = time.time() + timeout
            while time.time() < dl:
                try:
                    r = c.send('Runtime.evaluate', {'expression': 'document.readyState',
                              'returnByValue': True})
                    if (r or {}).get('result', {}).get('value') == 'complete': return True
                except Exception: pass
                time.sleep(0.5)
            return False
        def arm_errs():
            js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
               "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'zero console errors @ {label} [{tag}]', json.dumps(v)[:200] if v else '')

        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        arm_errs()
        js("HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') + ";HUB.store.save();HUB.applyTheme();")
        js("HUB.store.state.profile.name='Prabin';HUB.store.state.profile.campus='Dallas College';HUB.store.save();")
        time.sleep(0.8)

        # ---- ME tab: no overflow at rest ----
        js("HUB.showTab('me')"); time.sleep(1.2)
        note(js("document.documentElement.scrollWidth") <= width, f'ME tab no h-overflow [{tag}]')

        # ---- Edit Profile sheet ----
        note(js("(function(){document.getElementById('meEditBtn').click();return true;})()") is True,
             f'edit profile opens [{tag}]')
        # wait for the sheetUpC entrance animation to finish: headless CSS clock
        # lags wall-clock, so a fixed 1.0s sleep can catch it mid-scale(.985)
        for _ in range(20):
            if js("(function(){var sh=document.getElementById('sheetBox');"
                  "return sh&&!sh.getAnimations().some(a=>a.playState==='running');})()") is True:
                break
            time.sleep(0.3)
        s = js(SHEET_JS)
        note(isinstance(s, dict), f'sheet metrics readable [{tag}]', json.dumps(s))
        if isinstance(s, dict):
            note(abs(s['l']) <= 2, f'sheet pinned at left edge (l={s["l"]}) [{tag}]')
            note(s['r'] <= width + 1, f'sheet right edge inside viewport (r={s["r"]}) [{tag}]')
            note(s['doc'] <= width, f'document no h-overflow with sheet open [{tag}]')
            btns = s['btns']
            note(isinstance(btns, list) and len(btns) == 4, f'gender seg has 4 options [{tag}]')
            if isinstance(btns, list) and len(btns) == 4:
                note(all(b['l'] >= -1 and b['r'] <= width + 1 for b in btns),
                     f'all 4 gender options fully visible [{tag}]', json.dumps(btns))
        shot(f'meicon2-pedit-{width}-{theme}')
        # gender still selectable + cancel-safe
        js("document.querySelector('#peditGender button[data-g=\"other\"]').click()"); time.sleep(0.3)
        note(js("document.querySelector('#peditGender button.on').dataset.g") == 'other',
             f'gender selectable [{tag}]')
        js("document.getElementById('peditCancel').click()"); time.sleep(0.6)
        note(js("document.getElementById('sheetHost').hidden") is True, f'sheet closes [{tag}]')
        note(js("HUB.store.state.profile.gender||''") == '', f'cancel keeps gender unset [{tag}]')

        # ---- onboarding gender seg ----
        js("localStorage.clear()"); c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        arm_errs()
        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.reload', {}); time.sleep(6)
        js_wait_ready(); arm_errs()
        js("HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') + ";HUB.store.save();HUB.applyTheme();")
        time.sleep(0.8)
        note(js("!!document.getElementById('obCommunity')"), f'onboarding shows [{tag}]')
        js("document.getElementById('obCommunity').click()"); time.sleep(1)
        ob = js(OBSEG_JS)
        note(isinstance(ob, list) and len(ob) == 4 and
             all(b['l'] >= -1 and b['r'] <= width + 1 for b in ob),
             f'onboarding gender seg fits [{tag}]', json.dumps(ob))
        shot(f'meicon2-ob-{width}-{theme}')

        # ---- German long labels at this width ----
        note(js("HUB.i18n.loadLocale('de')") is True, f'de loads [{tag}]')
        js("HUB.showTab('me')"); time.sleep(0.5)
        # seed profile directly now that onboarding is done-ish; reopen edit via API
        js("HUB.store.state.profile.name='Prabin';HUB.store.state.profile.campus='Dallas College';HUB.store.save();HUB.showTab('me')")
        time.sleep(1)
        js("document.getElementById('meEditBtn').click()")
        for _ in range(20):
            if js("(function(){var sh=document.getElementById('sheetBox');"
                  "return sh&&!sh.getAnimations().some(a=>a.playState==='running');})()") is True:
                break
            time.sleep(0.3)
        s = js(SHEET_JS)
        if isinstance(s, dict):
            btns = s['btns']
            note(isinstance(btns, list) and len(btns) == 4 and
                 all(b['l'] >= -1 and b['r'] <= width + 1 for b in btns),
                 f'de gender seg fits [{tag}]', json.dumps(btns))
            note(s['doc'] <= width, f'de sheet no h-overflow [{tag}]')
        # banned purple sweep on the sheet
        note(js("""(function(){const bad=['#7C3AED','#8B5CF6','#A855F7'];
const html=document.getElementById('sheetBox').innerHTML.toUpperCase();
return !bad.some(h=>html.includes(h));})()""") is True, f'no banned purple in sheet [{tag}]')
        errs('final')
    finally:
        proc.terminate()

for w, h in [(390, 844), (320, 568)]:
    for th in ['dark', 'light']:
        run_case(w, h, th)

n_fail = sum(1 for ok, _ in checks if not ok)
print(f'{len(checks)-n_fail}/{len(checks)} passed')
raise SystemExit(1 if n_fail else 0)
