#!/usr/bin/env python3
"""QA: Pulse overlay — glass rows, event rows open the full detail sheet
(links + photo strip + lightbox), other rows keep their targets,
X/backdrop/Escape dismissal."""
import json, subprocess, time, urllib.request, os, base64, shutil, re
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9465
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors, checks = [], []
def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, detail)
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

def run(theme, full):
    shutil.rmtree(f'/tmp/hubqa-pulse-{theme}', ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-pulse-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        c.send('Runtime.enable'); c.send('Page.enable')
        def js(expr):
            r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
            return (r or {}).get('result', {}).get('value')
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name), 'wb').write(base64.b64decode(r['data']))
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'{theme}: {label} zero errors', json.dumps(v)[:200] if v else '')
        def esc_key():
            c.send('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(4)
        errs('boot')
        js("try{HUB.store.state.profile.name='QA';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        time.sleep(0.5)

        # lazy locale kh check for the new daily keys
        js("HUB.i18n.setLang('de')"); time.sleep(2.5)
        v = js("HUB.i18n._dict('de')['daily.evPhotos']")
        note(v == 'Photos', f'{theme}: lazy de locale loads new keys (kh ok)', str(v))
        js("HUB.i18n.setLang('en')"); time.sleep(1.5)

        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.pulse.open();")
        time.sleep(1.2)
        errs('pulse open')
        v = js("!!document.getElementById('hubPulseRoot')")
        note(v, f'{theme}: Pulse overlay opens', str(v))
        v = js("document.querySelectorAll('#hubPulseRows .prow').length")
        note(v and v > 0, f'{theme}: glass rows rendered', f'found={v}')
        v = js("document.querySelector('#hubPulseRows .prow .prow-art')!==null")
        note(v, f'{theme}: art tile on rows', str(v))
        v = js("document.querySelector('#hubPulseRows').textContent")
        txt = str(v)
        note('Free pizza' in txt and 'Sample' in txt, f'{theme}: event rows keep badges', txt[:60])
        v = js("document.querySelector('#hubPulseRows .prow[data-ev]')!==null")
        note(v, f'{theme}: event rows carry data-ev', str(v))
        shot(f'pulse-board-{theme}.png')

        if not full:
            # dismissal checks on the light run too
            js("document.getElementById('hubPulseClose').click()"); time.sleep(0.5)
            v = js("!document.getElementById('hubPulseRoot')")
            note(v, f'{theme}: X closes Pulse', str(v))
            js("HUB.pulse.open()"); time.sleep(0.8)
            js("document.getElementById('hubPulseRoot').click()"); time.sleep(0.5)
            v = js("!document.getElementById('hubPulseRoot')")
            note(v, f'{theme}: backdrop tap closes Pulse', str(v))
            js("HUB.pulse.open()"); time.sleep(0.8)
            esc_key(); time.sleep(0.5)
            v = js("!document.getElementById('hubPulseRoot')")
            note(v, f'{theme}: Escape closes Pulse', str(v))
            errs('final'); return

        # ---- event row -> full detail sheet ----
        js("document.querySelector('#hubPulseRows .prow[data-ev]').click()"); time.sleep(1.0)
        v = js("!document.getElementById('hubPulseRoot') && document.getElementById('sheetHost').hidden===false")
        note(v, f'{theme}: event tap closes Pulse, opens detail sheet', str(v))
        v = js("document.getElementById('sheetBox').textContent")
        txt = str(v)
        ok = all(k in txt for k in ['Free pizza', 'Today', 'Student Union lobby', 'Community',
               'Free pizza for all students', 'Photos', 'Links', 'More info'])
        note(ok, f'{theme}: detail shows full info + desc + cat', txt[:80])
        v = js("document.querySelectorAll('#sheetBox .evphotostrip img').length")
        note(v == 2, f'{theme}: photo strip has 2 seeded photos', f'found={v}')
        v = js("(()=>{const a=document.querySelector('#sheetBox .evlink');return a?{href:a.href,target:a.target,host:a.textContent}:null;})()")
        note(v and v.get('href') == 'https://example.com/' and v.get('target') == '_blank',
             f'{theme}: link is tappable (new tab)', str(v)[:70])
        shot(f'pulse-detail-{theme}.png')
        errs('detail')

        # ---- photo -> pinch-zoom lightbox ----
        js("document.querySelector('#sheetBox .evphotostrip img').click()"); time.sleep(0.8)
        v = js("!!document.querySelector('.mkzoom')")
        note(v, f'{theme}: photo tap opens lightbox', str(v))
        shot(f'pulse-lightbox-{theme}.png')
        esc_key(); time.sleep(0.5)
        v = js("!document.querySelector('.mkzoom') && document.getElementById('sheetHost').hidden===false")
        note(v, f'{theme}: Escape closes lightbox, sheet stays', str(v))
        js("document.querySelector('#sheetBox .sheetx').click()"); time.sleep(0.5)

        # ---- non-event row keeps its target (market listing row) ----
        js("HUB.pulse.open()"); time.sleep(1.0)
        v = js("(()=>{const r=document.querySelector('#hubPulseRows .prow[data-tab=\"market\"]:not([data-ev])');return r?r.textContent.slice(0,40):null;})()")
        note(v, f'{theme}: non-event row exists', str(v))
        js("document.querySelector('#hubPulseRows .prow[data-tab=\"market\"]:not([data-ev])').click()"); time.sleep(1.0)
        v = js("!document.getElementById('hubPulseRoot') && document.querySelector('#tabbar .tab[data-tab=\"market\"]').classList.contains('active')")
        note(v, f'{theme}: listing row navigates to market tab', str(v))
        errs('navigation')

        # ---- dismissal ----
        js("HUB.pulse.open()"); time.sleep(0.8)
        js("document.getElementById('hubPulseClose').click()"); time.sleep(0.5)
        v = js("!document.getElementById('hubPulseRoot')")
        note(v, f'{theme}: X closes Pulse', str(v))
        js("HUB.pulse.open()"); time.sleep(0.8)
        js("document.getElementById('hubPulseRoot').click()"); time.sleep(0.5)
        v = js("!document.getElementById('hubPulseRoot')")
        note(v, f'{theme}: backdrop tap closes Pulse', str(v))
        js("HUB.pulse.open()"); time.sleep(0.8)
        esc_key(); time.sleep(0.5)
        v = js("!document.getElementById('hubPulseRoot')")
        note(v, f'{theme}: Escape closes Pulse', str(v))
        errs('final')
    finally:
        proc.terminate()

run('dark', full=True)
run('light', full=False)
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
