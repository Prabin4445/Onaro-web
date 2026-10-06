#!/usr/bin/env python3
"""Welcome-flow fit probe: fresh profile, real 3-step onboarding @390.
Asserts each step fits the viewport (no page-level horizontal overflow)."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9473
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []
def note(ok, label, detail=''):
    checks.append(ok); print(('PASS' if ok else 'FAIL'), label, detail[:140], flush=True)

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
    def js(self, expr):
        r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
        return (r or {}).get('result', {}).get('value')

def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data']))

def fit(c):
    return c.js("({sw:document.documentElement.scrollWidth,iw:window.innerWidth,sx:window.scrollX})")

for theme in ['dark', 'light']:
    prof = '/tmp/hubqa-fitwlcm-%s' % theme
    shutil.rmtree(prof, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--disable-dev-shm-usage', '--remote-debugging-port=%d' % PORT, '--remote-allow-origins=*',
        '--user-data-dir=' + prof, '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        tgt = None
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen('http://localhost:%d/json/list' % PORT, timeout=3) as r:
                    ts = json.load(r)
                tgt = next(x for x in ts if x['type'] == 'page' and 'devtools' not in x['url'])
                break
            except Exception: continue
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable')
        c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        time.sleep(5)
        c.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message))")
        c.js("document.body.classList.%s('dark')" % ('add' if theme == 'dark' else 'remove'))
        time.sleep(1.5)
        vis = c.js("(()=>{var w=document.getElementById('wlcmHost');return w&&!w.hidden;})()")
        note(bool(vis), '[%s] welcome step1 visible on fresh profile' % theme)
        m = fit(c); note(m['sw'] <= m['iw'], '[%s] welcome step1 fits' % theme, str(m))
        shot(c, 'wlcm-fit-step1-%s' % theme)
        # pick a language -> step 2 (country)
        c.js("(()=>{var b=[...document.querySelectorAll('#wlcmHost button')].find(x=>/Deutsch|Espa\u00f1ol|Nederlands/i.test(x.textContent));if(b)b.click();})()")
        time.sleep(1.2)
        m = fit(c); note(m['sw'] <= m['iw'], '[%s] welcome step2 (country) fits' % theme, str(m))
        shot(c, 'wlcm-fit-step2-%s' % theme)
        # back -> step 1 again
        c.js("(()=>{var b=document.querySelector('.wlcm-back');if(b)b.click();})()")
        time.sleep(1.0)
        # pick language again -> step2 -> pick country -> step3
        c.js("(()=>{var b=[...document.querySelectorAll('#wlcmHost button')].find(x=>/English/i.test(x.textContent));if(b)b.click();})()")
        time.sleep(1.0)
        c.js("(()=>{var b=[...document.querySelectorAll('#wlcmHost button')].find(x=>/United States|Nepal/i.test(x.textContent));if(b)b.click();})()")
        time.sleep(1.2)
        m = fit(c); note(m['sw'] <= m['iw'], '[%s] welcome step3 (continue+disclaimer) fits' % theme, str(m))
        shot(c, 'wlcm-fit-step3-%s' % theme)
        errs = c.js("window.__huberr.splice(0)")
        note(not errs, '[%s] zero console errors' % theme, str(errs[:3]) if errs else '')
    finally:
        proc.terminate()
print('WELCOME FIT: %d/%d' % (sum(checks), len(checks)), flush=True)
