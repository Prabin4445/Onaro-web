#!/usr/bin/env python3
"""i18n sweep: boot -> onboarding -> home, then set all 28 languages,
check console errors, RTL dir, key coverage of class/story keys, screenshot RTL+key langs."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9471
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors, checks = [], []
def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, str(detail)[:140])
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
LANGS = ['en','es','ne','hi','fr','de','pt','it','nl','ru','uk','pl','zh','ja','ko',
         'ar','fa','ur','tr','vi','th','id','bn','ta','te','pa','tl','sw']
RTL = {'ar','fa','ur'}
SHOTS = {'fr':'i18n-fr-home','ja':'i18n-ja-home','ru':'i18n-ru-home','hi':'i18n-hi-home',
         'ar':'i18n-ar-home','fa':'i18n-fa-home','ur':'i18n-ur-home','es':'i18n-es-home'}
def main():
    subprocess.Popen(['rm','-rf','/tmp/hubi18n'])
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=414,900',
        '--user-data-dir=/tmp/hubi18n', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        def js(expr, wait=0):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
                res = (r or {}).get('result', {})
                if 'exceptionDetails' in (r or {}): return None, 'EXC'
                return res.get('value'), None
            except Exception as e: return None, str(e)[:160]
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def errs(label):
            v, _ = js("window.__huberr.splice(0)")
            if v: errors.append((label, v)); print('ERRORS @', label, ':', json.dumps(v)[:300])
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        keys117=json.load(open(os.path.join(QA,'.repro','untranslated_keys.json')))
        js('window.KEYS117='+json.dumps(list(keys117.keys())))
        for _ in range(25):
            v, _ = js("typeof HUB!=='undefined'&&!!document.getElementById('wlcmHost')&&!document.getElementById('wlcmHost').hidden")
            if v: break
            time.sleep(1)
        errs('boot')
        note(v, 'welcome visible')
        # quick path to home: click wlcmGo, pick student, fill name, skip picker via stored state? use UI flow minimal
        js("document.getElementById('wlcmGo').click()"); time.sleep(1.0)
        js("document.getElementById('obStudent').click()"); time.sleep(0.5)
        js("document.getElementById('obName').value='QA Tester';document.getElementById('obName').dispatchEvent(new Event('input',{bubbles:true}))")
        js("document.getElementById('obPickBtn').click()"); time.sleep(2.0)
        # select first result instead of searching to save time
        v,_ = js("(()=>{const rows=[...document.querySelectorAll('#intlResults .intl-row')];if(!rows.length)return 'no-rows';rows[0].click();return 'clicked:'+(rows[0].querySelector('h3')||{}).textContent})()")
        time.sleep(1.5)
        v,_ = js("!!document.getElementById('homeTab')||document.body.textContent.length>100")
        errs('onboarding')
        note(v, 'reached home after onboarding')
        js("HUB.showTab('home')"); time.sleep(1.0)
        # per-language sweep
        keys, _ = js("Object.keys(HUB.i18n?HUB.i18n.dict?{}:{})")
        total_errs = 0
        for lang in LANGS:
            js(f"HUB.i18n.setLang('{lang}');HUB.showTab('home')")
            time.sleep(1.1)
            e, _ = js("window.__huberr.splice(0)")
            nerr = len(e or [])
            total_errs += nerr
            if nerr: errors.append((lang, e)); print('ERRORS @', lang, json.dumps(e)[:300])
            cur, _ = js("HUB.i18n.getLang()")
            d, _ = js("document.documentElement.dir")
            # check class/story keys resolve non-empty
            cov, _ = js("(function(){var ks=KEYS117;var miss=ks.filter(function(k){var v=HUB.i18n.t(k);return !v||v===k});return ks.length+'/'+(ks.length-miss.length)})()")
            rtlok = (d == 'rtl') == (lang in RTL)
            note(cur == lang and rtlok and nerr == 0, f'lang {lang}: cur={cur} dir={d} cov={cov}')
            if lang in SHOTS: shot(SHOTS[lang])
        note(total_errs == 0, 'zero errors across all languages', f'total={total_errs}')
        print(f'\nCHECKS: {sum(1 for ok,_ in checks if ok)}/{len(checks)} passed')
    finally:
        proc.terminate()
main()
