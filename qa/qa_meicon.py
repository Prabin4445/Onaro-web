#!/usr/bin/env python3
"""Gender-aware ME tab icon QA (PraBin's ask).

- female -> nav-me-girl, other -> nav-me-rainbow, na -> nav-me-ninja, male/unset -> nav-me
- Gender settable in onboarding (stepPick) and ME > Edit profile; tab icon repaints live.
- New icons resolve at both resolutions; i18n (de) really loads with the new keys.
Fresh profiles, 390x844, dark+light, zero console errors.
"""
import json, subprocess, time, urllib.request, os, base64, shutil

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9489
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []

def note(ok, label, detail=''):
    checks.append((ok, label)); print(('PASS' if ok else 'FAIL'), label, detail)

import websocket
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

MEICON_JS = """(function(){const b=document.querySelector('#tabbar .tab[data-tab="me"]');
const img=b?b.querySelector('.tab-ico img'):null;
return img?{d:img.getAttribute('data-icon'),src:img.getAttribute('src'),cur:img.currentSrc,w:img.naturalWidth}:null;})()"""
GSEG_JS = """(function(){const r=document.getElementById(%s);if(!r)return null;
return [...r.querySelectorAll('button')].map(b=>({g:b.dataset.g,label:b.textContent.trim(),on:b.classList.contains('on')}));})()"""

def run_theme(theme):
    prof = f'/tmp/hubqa-meicon-{theme}'
    shutil.rmtree(prof, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=390,844',
        f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as r:
                    ts = json.load(r)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        def js(expr):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
                if r and 'exceptionDetails' in r:
                    ed = r['exceptionDetails']
                    return 'THREW:' + str(ed.get('exception', {}).get('description', ed.get('text', '')))[:160]
                res = (r or {}).get('result', {}); return res.get('value')
            except Exception as e: return 'JSERR:' + str(e)[:120]
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'zero console errors @ {label} [{theme}]', json.dumps(v)[:200] if v else '')
        def meicon():
            return js(MEICON_JS)

        # ---- onboarding: fresh profile, only language seeded ----
        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
           "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        js("HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') + ";HUB.store.save();HUB.applyTheme();")
        time.sleep(1)
        note(js("!!document.getElementById('obCommunity')"), f'onboarding role step shows [{theme}]')
        js("document.getElementById('obCommunity').click()"); time.sleep(1)
        g = js(GSEG_JS % "'obGender'")
        note(isinstance(g, list) and len(g) == 4, f'onboarding gender seg has 4 options [{theme}]', json.dumps(g))
        note(isinstance(g, list) and [x['label'] for x in g] == ['Male', 'Female', 'Other', 'Prefer not to say'],
             f'onboarding gender labels [{theme}]')
        js("document.querySelector('#obGender button[data-g=\"female\"]').click()"); time.sleep(0.4)
        g = js(GSEG_JS % "'obGender'")
        note(isinstance(g, list) and [x['g'] for x in g if x['on']] == ['female'], f'female selectable in onboarding [{theme}]')
        js("document.getElementById('obName').value='Mina'")
        js("document.getElementById('obPickBtn').click()"); time.sleep(1.2)
        note(js("document.querySelectorAll('.intl-spick').length") > 0, f'institution picker shows samples [{theme}]')
        js("document.querySelector('.intl-spick').click()"); time.sleep(1)
        g = js(GSEG_JS % "'obGender'")
        note(isinstance(g, list) and [x['g'] for x in g if x['on']] == ['female'],
             f'gender choice survives campus-picker re-render [{theme}]')
        shot(f'meicon-ob-{theme}')
        js("document.getElementById('obGo').click()"); time.sleep(1.5)
        note(js("HUB.store.state.profile.gender") == 'female', f'onboarding saves gender=female [{theme}]')
        mi = meicon()
        note(isinstance(mi, dict) and mi['d'] == 'nav-me-girl', f'tab icon -> nav-me-girl after onboarding [{theme}]', json.dumps(mi))
        # sizes="48px" @ DPR 2 -> browser picks the 96w @2x resource (currentSrc proves
        # the srcset/retina path); standalone loads decode the files at 96x96/144x144.
        note(isinstance(mi, dict) and mi['src'] == 'icons/nav-me-girl.png' and '@2x' in (mi['cur'] or '') and mi['w'] > 0,
             f'girl icon loads via @2x srcset [{theme}]', json.dumps(mi))
        errs('onboarding')

        # ---- edit profile: cycle all 4 genders ----
        js("HUB.showTab('me')"); time.sleep(1)
        cases = [('female', 'nav-me-girl'), ('other', 'nav-me-rainbow'), ('na', 'nav-me-ninja'), ('male', 'nav-me')]
        for gd, icon in cases:
            js("document.getElementById('meEditBtn').click()"); time.sleep(0.8)
            if gd == 'female':
                g = js(GSEG_JS % "'peditGender'")
                note(isinstance(g, list) and [x['g'] for x in g if x['on']] == ['female'],
                     f'edit profile preselects saved gender [{theme}]')
                shot(f'meicon-pedit-{theme}')
            ok = js(f"document.querySelector('#peditGender button[data-g=\"{gd}\"]').click(),'ok'")
            note(ok == 'ok', f'gender button {gd} clickable [{theme}]')
            js("document.getElementById('peditSave').click()"); time.sleep(1)
            note(js("HUB.store.state.profile.gender") == gd, f'profile.gender={gd} saved [{theme}]')
            mi = meicon()
            note(isinstance(mi, dict) and mi['d'] == icon and (icon + '.png') in mi['src'],
                 f'tab icon -> {icon} [{theme}]', json.dumps(mi))
            shot(f'meicon-tab-{gd}-{theme}')
        # unset legacy profile keeps the boy
        js("HUB.store.state.profile.gender='';HUB.store.save();HUB.paintChrome();"); time.sleep(0.5)
        mi = meicon()
        note(isinstance(mi, dict) and mi['d'] == 'nav-me', f'unset gender keeps boy icon [{theme}]', json.dumps(mi))

        # ---- icon registry: all 3 new icons resolve at both resolutions ----
        for nm in ['nav-me-girl', 'nav-me-rainbow', 'nav-me-ninja']:
            h = js(f"HUB.icons.icon('{nm}')")
            note(isinstance(h, str) and f'icons/{nm}.png' in h and f'icons/{nm}@2x.png' in h,
                 f'{nm} resolves src+src2x [{theme}]')
        # standalone decode: files are really 144x144 / 96x96 RGBA with transparency
        dims = js("""(async function(){
const mk=s=>new Promise(res=>{const i=new Image();i.onload=()=>res(i.naturalWidth+'x'+i.naturalHeight);i.onerror=()=>res('ERR');i.src=s;});
const out={};
for(const nm of ['nav-me-girl','nav-me-rainbow','nav-me-ninja']){
  out[nm]=await mk('icons/'+nm+'.png'); out[nm+'@2x']=await mk('icons/'+nm+'@2x.png');}
return out;})()""")
        note(isinstance(dims, dict) and all(dims.get(k) == '144x144' for k in ['nav-me-girl', 'nav-me-rainbow', 'nav-me-ninja']) and
             all(dims.get(k + '@2x') == '96x96' for k in ['nav-me-girl', 'nav-me-rainbow', 'nav-me-ninja']),
             f'icon files decode at 144/96px [{theme}]', json.dumps(dims))

        # ---- i18n: de really loads (object identity, awaited) ----
        note(js("HUB.i18n.loadLocale('de')") is True, f"de locale loads [{theme}]")
        note(js("HUB.i18n._dict('de')!==HUB.i18n._dict('en')"), f"de dict is real, not fallback [{theme}]")
        note(js("HUB.i18n._dict('de')['pedit.gender']") == 'Geschlecht', f"de pedit.gender translated [{theme}]")
        note(js("HUB.i18n._dict('de')['me.gender.na']") == 'Lieber nicht sagen', f"de me.gender.na translated [{theme}]")

        note(js("document.documentElement.scrollWidth") <= 390, f'no horizontal overflow [{theme}]')
        tb = js("(function(){const e=document.getElementById('tabbar');if(!e)return null;const r=e.getBoundingClientRect();return {w:Math.round(r.width),l:Math.round(r.left)};})()")
        note(isinstance(tb, dict) and tb['w'] <= 480 and tb['l'] >= -1, f'tabbar inside 480px column [{theme}]', json.dumps(tb))
        errs('final')
    finally:
        proc.terminate()

for th in ['dark', 'light']:
    run_theme(th)

n_fail = sum(1 for ok, _ in checks if not ok)
print(f'{len(checks)-n_fail}/{len(checks)} passed')
raise SystemExit(1 if n_fail else 0)
