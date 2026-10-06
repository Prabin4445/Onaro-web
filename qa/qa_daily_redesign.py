#!/usr/bin/env python3
"""Daily tab redesign QA (2026-10-05): glossy-3D chrome smoke test.

Fresh profiles, 390px + 320px, dark + light. Checks: zero console errors,
hero present w/ date-aware subtitle, 7 glossy section cards, all 3D badge
icons loaded (no emoji fallback), no horizontal overflow, wellness
gender-gating intact (male -> restricted, no cycle data in DOM), calc entry
opens the full-page overlay, capsule + event-add sheets open, screenshots.
"""
import json, subprocess, time, urllib.request, os, base64, shutil

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9490
PROF = '/tmp/hubqa-daily-redesign'
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

def run(theme, w):
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', f'--window-size={w},844',
        f'--user-data-dir={PROF}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        c.send('Emulation.setDeviceMetricsOverride', {'width': w, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
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
            note(not v, f'zero console errors @ {label} [{theme} {w}px]', json.dumps(v)[:200] if v else '')

        tag = f'{theme} {w}px'
        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(7)
        js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
           "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        js("var p=HUB.store.state.profile; p.name='PraBin'; p.campus='Downtown'; p.audience='community';"
           "HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') + ";"
           "HUB.store.save(); HUB.applyTheme(); try{HUB.ui.closeSheet();}catch(e){} HUB.showTab('daily');")
        time.sleep(2.5)
        errs('load')

        # hero: present + date-aware subtitle
        note(js("document.querySelector('.dly-hero')!==null"), f'hero banner present [{tag}]')
        wd = js("new Date().toLocaleDateString('en-US',{weekday:'long'})")
        note(js(f"document.querySelector('.dly-hero-s').textContent.indexOf({json.dumps(wd)})>=0"),
             f'hero subtitle is date-aware [{tag}]', wd)
        note(js("document.querySelector('.dly-hero .dly-hero-ico img')!==null"),
             f'hero clay icon present [{tag}]')

        # 7 glossy section cards, in today's order
        n = js("document.querySelectorAll('#view-daily .dly-card').length")
        note(n == 7, f'7 glossy section cards [{tag}]', f'found={n}')
        badges = js("(function(){const out=[];document.querySelectorAll('#view-daily .dly-badge img').forEach(i=>out.push(i.complete&&i.naturalWidth>0));return out;})()")
        note(isinstance(badges, list) and len(badges) == 5 and all(badges),
             f'5 floating 3D badge icons loaded [{tag}]', json.dumps(badges))
        note(js("document.querySelectorAll('#view-daily .dly-badge .ico-fb').length") == 0,
             f'no badge emoji-fallback spans [{tag}]')
        hdr_imgs = js("(function(){const out=[];document.querySelectorAll('#view-daily .dly-chead-ico img').forEach(i=>out.push(i.complete&&i.naturalWidth>0));return out;})()")
        note(isinstance(hdr_imgs, list) and len(hdr_imgs) == 1 and all(hdr_imgs),
             f'header clay icon (happening) loaded [{tag}]')

        # no horizontal overflow
        ov = js("({dw:document.documentElement.scrollWidth,vw:document.documentElement.clientWidth})")
        note(ov['dw'] <= ov['vw'], f'no page horizontal overflow [{tag}]', json.dumps(ov))

        # wellness gender-gating EXACTLY as before: no gender -> setup prompt
        note(js("document.querySelector('#wlCard .wl-nogender')!==null"),
             f'wellness: no-gender setup state [{tag}]')
        # male -> tasteful restricted, zero cycle data in DOM
        js("HUB.store.state.profile.gender='male';HUB.store.save();HUB.views.daily.render(document.getElementById('view-daily'));")
        time.sleep(1.5)
        note(js("document.querySelector('#wlCard .wl-restrict')!==null"),
             f'wellness: male sees restricted card [{tag}]')
        note(js("document.querySelector('#wlCard .wl-next')===null&&document.querySelector('#wlCard .wl-stats')===null"),
             f'wellness: no cycle data in DOM for male [{tag}]')
        note(js("document.querySelectorAll('#view-daily .dly-card').length") == 7,
             f'card count stable after gender re-render [{tag}]')
        errs('gender-rerender')

        # calculator entry -> full-page overlay opens
        js("document.getElementById('homeCalcEntry').click()"); time.sleep(1)
        note(js("document.getElementById('hubCalcRoot')!==null"), f'calc entry opens full-page overlay [{tag}]')
        shot(f'dly_{theme}_{w}_calc')
        js("HUB.calc.closeFull()"); time.sleep(0.5)

        # capsule new -> sheet opens; event add -> form sheet opens
        js("document.getElementById('dyCapNew').click()"); time.sleep(0.8)
        note(js("!document.getElementById('sheetHost').hidden"), f'capsule sheet opens [{tag}]')
        js("HUB.ui.closeSheet()"); time.sleep(0.5)
        js("document.querySelector('[data-ev-add]').click()"); time.sleep(0.8)
        note(js("document.getElementById('efTitle')!==null"), f'event form sheet opens [{tag}]')
        js("HUB.ui.closeSheet()"); time.sleep(0.5)
        errs('interactions')

        # screenshots: top (hero), middle, bottom
        js("window.scrollTo(0,0)"); time.sleep(0.6); shot(f'dly_{theme}_{w}_top')
        js("window.scrollTo(0,1400)"); time.sleep(0.6); shot(f'dly_{theme}_{w}_mid')
        js("window.scrollTo(0,document.body.scrollHeight)"); time.sleep(0.6); shot(f'dly_{theme}_{w}_bot')
    finally:
        proc.terminate()

for theme, w in [('dark', 390), ('dark', 320), ('light', 390)]:
    run(theme, w)

fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} checks passed')
if fails: print('FAILURES:', fails)
