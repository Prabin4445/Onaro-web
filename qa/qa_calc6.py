#!/usr/bin/env python3
"""Calculator QA round 6: advanced-function regression battery.
Casio-class features: integral, derivative, summation, solve, log-base,
x^3 / cbrt / nth-root, sinh/cosh/tanh, M+/M-/MR, Pol/Rec, base conversion,
REPLAY, MODE/SETUP (Fix/Sci/Norm). Fresh profiles, 390x844, dark+light, zero errors.
"""
import json, subprocess, time, urllib.request, os, base64, shutil

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9487
PROF = '/tmp/hubqa-calc6'
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

def run_theme(theme):
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=390,844',
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

        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
           "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        js("var p=HUB.store.state.profile; p.name='PraBin'; p.campus='Downtown'; p.audience='community';"
           "HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') + ";"
           "HUB.store.save(); HUB.applyTheme(); try{HUB.ui.closeSheet();}catch(e){} HUB.showTab('daily');")
        time.sleep(2)
        errs('load')
        note(js("!!document.getElementById('calcExpr')"), 'calc card rendered')
        # RAD mode for trig-sensitive known values
        js("HUB.store.state.calcMode='rad'; HUB.store.save();")
        note(js("document.documentElement.scrollWidth") <= 390, 'no horizontal overflow')

        A = "HUB.calc._adv"
        EV = "HUB.calc._eval"

        # ---- definite integral: the Casio photo's own example ----
        v = js(f"{A}.integ('sin(x)',0,Math.PI/3)")
        note(isinstance(v, (int, float)) and abs(v - 0.5) < 1e-6, 'integral sin(x) 0..pi/3 = 0.5', f'v={v}')
        # ---- numeric derivative ----
        v = js(f"{A}.deriv('x^2',3)")
        note(isinstance(v, (int, float)) and abs(v - 6) < 1e-4, 'd/dx(x^2)@3 = 6', f'v={v}')
        # ---- summation ----
        v = js(f"{A}.sigma('x',1,5)")
        note(v == 15, 'Sigma x, 1..5 = 15', f'v={v}')
        # ---- equation solver ----
        r = js(f"{A}.solve('x^2-4')")
        ok = isinstance(r, list) and any(abs(x - 2) < 1e-6 for x in r) and any(abs(x + 2) < 1e-6 for x in r)
        note(ok, 'SOLVE x^2-4 -> +-2', f'roots={r}')
        r = js(f"{A}.solve('x^2+1')")
        note(isinstance(r, list) and len(r) == 0, 'SOLVE x^2+1 -> no roots (not NaN)', f'roots={r}')
        # friendly no-solution UI message (never raw NaN)
        js(f"{A}.lab('sol'); document.getElementById('labF0').value='x^2+1'; document.getElementById('labGo').click();")
        time.sleep(0.5)
        want = js("HUB.i18n.t('calc.noSolution')")
        got = js("document.getElementById('labRes').textContent")
        note(isinstance(got, str) and got == want, 'no-solution shows friendly message', f'got={got!r}')
        js("try{HUB.ui.closeSheet();}catch(e){}")

        # ---- log with custom base ----
        v = js(f"{EV}('logb(2,8)','rad').value")
        note(v == 3, 'logb(2,8)=3', f'v={v}')
        # ---- powers & roots ----
        note(js(f"{EV}('2^3','rad').value") == 8, 'x^3: 2^3=8')
        note(js(f"{EV}('cbrt(27)','rad').value") == 3, 'cbrt(27)=3')
        note(js(f"{EV}('root(4,16)','rad').value") == 2, 'root(4,16)=2 (4th root)')
        # ---- hyperbolic ----
        note(js(f"{EV}('sinh(0)','rad').value") == 0, 'sinh(0)=0')
        note(js(f"{EV}('cosh(0)','rad').value") == 1, 'cosh(0)=1')
        note(js(f"{EV}('tanh(0)','rad').value") == 0, 'tanh(0)=0')

        # ---- M+ / M- / MR ----
        js("HUB.store.state.calcMem=0; HUB.store.save();"
           "var e=document.getElementById('calcExpr'); e.value='5'; HUB.calc._press('eq');")
        js("HUB.calc._press('mplus')")
        note(js(f"{A}.mem()") == 5, 'M+ stores 5')
        js("e.value='2'; HUB.calc._press('eq'); HUB.calc._press('mminus')")
        note(js(f"{A}.mem()") == 3, 'M- leaves 3')
        js("HUB.calc._press('ac'); HUB.calc._press('mr')")
        note(js("document.getElementById('calcExpr').value") == '3', 'MR recalls 3 into display')

        # ---- Pol/Rec ----
        p = js(f"{A}.polrec('pol',1,0)")
        note(isinstance(p, dict) and abs(p.get('a', 9) - 1) < 1e-9 and abs(p.get('b', 9)) < 1e-9,
             'Pol(1,0) = (1, 0)', f'{p}')
        p = js(f"{A}.polrec('rec',1,0)")
        note(isinstance(p, dict) and abs(p.get('a', 9) - 1) < 1e-9 and abs(p.get('b', 9)) < 1e-9,
             'Rec(1,0) = (1, 0)', f'{p}')

        # ---- base conversions (incl. the 0b/0o prefix bug fix) ----
        B = f"{A}.base"
        note(js(f"{B}('0b101',10)") == '5', '0b101 -> 5')
        note(js(f"{B}('0o17',10)") == '15', '0o17 -> 15')
        note(js(f"{B}('0xFF',10)") == '255', '0xFF -> 255')
        note(js(f"{B}('255',16)") == 'FF', '255 -> FF')
        note(js(f"{B}('255',2)") == '11111111', '255 -> 11111111')

        # ---- REPLAY up/down ----
        js("HUB.store.state.calcHist=[]; HUB.store.save();"
           "var e=document.getElementById('calcExpr');"
           "e.value='5'; HUB.calc._press('eq'); e.value='2'; HUB.calc._press('eq'); e.value='7'; HUB.calc._press('eq');")
        vals = js("(function(){var o=[];"
                  "HUB.calc._adv.replay(true); o.push(document.getElementById('calcExpr').value);"
                  "HUB.calc._adv.replay(true); o.push(document.getElementById('calcExpr').value);"
                  "HUB.calc._adv.replay(true); o.push(document.getElementById('calcExpr').value);"
                  "HUB.calc._adv.replay(false); o.push(document.getElementById('calcExpr').value);"
                  "HUB.calc._adv.replay(false); o.push(document.getElementById('calcExpr').value);"
                  "return o;})()")
        note(vals == ['7', '2', '5', '2', '7'], 'REPLAY up/down recalls history', f'{vals}')

        # ---- ADV bank toggle ----
        js("document.getElementById('calcAdvBtn').click()")
        for ck in ['lab-int', 'sinh', 'mplus', 'lab-base']:
            note(js(f"!!document.querySelector('#calcRoot [data-ck=\"{ck}\"]')"),
                 f'ADV bank shows {ck}')
        # REPLAY lives as header chips (#calcRpUp/#calcRpDown), not in the ADV bank
        for cid in ['calcRpUp', 'calcRpDown']:
            note(js(f"!!document.getElementById('{cid}')"),
                 f'REPLAY chip {cid} present')
        js("document.getElementById('calcAdvBtn').click()")
        note(js("document.querySelector('#calcRoot [data-ck=\"lab-int\"]')") is None,
             'ADV bank toggles back off')

        # ---- MODE/SETUP: Fix / Sci / Norm ----
        js("HUB.store.state.calcFmt='fix'; HUB.store.state.calcFixN=2; HUB.store.save();")
        note(js("HUB.calc._fmt(1/3)") == '0.33', 'Fix 2 -> 1/3 shows 0.33')
        js("HUB.store.state.calcFmt='sci'; HUB.store.save();")
        note(isinstance(js("HUB.calc._fmt(1/3)"), str) and 'e' in js("HUB.calc._fmt(1/3)").lower(),
             'Sci shows exponent form', js("HUB.calc._fmt(1/3)"))
        js("HUB.store.state.calcFmt='norm'; HUB.store.save();")
        note(js("HUB.calc._fmt(1/3)") != '0.33', 'Norm back to default')
        # settings sheet UI
        js(f"{A}.settings()"); time.sleep(0.4)
        note(js("!!document.querySelector('.calc-set')"), 'settings sheet opens')
        js("document.querySelector('#setFmt [data-v=\"fix\"]').click()")
        note(js("HUB.store.state.calcFmt") == 'fix', 'settings FIX segment works')
        js("document.querySelector('#setFmt [data-v=\"norm\"]').click()")
        note(js("HUB.store.state.calcFmt") == 'norm', 'settings NORM segment works')
        js("try{HUB.ui.closeSheet();}catch(e){}")

        # ---- regression spot-checks ----
        v = js(f"{EV}('sin(30)','deg').value")
        note(isinstance(v, (int, float)) and abs(v - 0.5) < 1e-9, 'regression: sin(30)=0.5 DEG', f'v={v}')
        note(js(f"{EV}('x^2','deg',{{x:3}}).value") == 9, 'regression: x^2 @ x=3 = 9')
        js("HUB.calc._graph.setView('graph')"); time.sleep(0.6)
        note(js("!document.getElementById('calcGraph').hidden"), 'regression: graph view opens')
        js("HUB.calc._graph.setView('calc')"); time.sleep(0.4)
        note(js("document.getElementById('calcGraph').hidden"), 'regression: back to calc view')

        # ---- display glow on typing ----
        js("HUB.calc._press('7','7')")
        note(js("document.querySelector('#calcRoot .calc-disp').classList.contains('calc-glow')"),
             'display glows on typing')

        # ---- money shot: integral lab sheet (Casio photo's example) ----
        js("HUB.store.state.calcMode='rad'; HUB.store.save();"
           f"{A}.lab('int'); document.getElementById('labGo').click();")
        time.sleep(0.6)
        res = js("document.getElementById('labRes').textContent")
        note(isinstance(res, str) and '0.5' in res, 'lab integral shows 0.5', res[:60])
        js("document.getElementById('calcRoot').scrollIntoView({block:'start'})"); time.sleep(0.5)
        shot(f'calc6-integral-{theme}')
        js("try{HUB.ui.closeSheet();}catch(e){}")

        errs('final')
    finally:
        proc.terminate()

for th in ['dark', 'light']:
    run_theme(th)
ok = sum(1 for o, _ in checks if o); tot = len(checks)
print(f'\n==== QA CALC6: {ok}/{tot} passed ====')
bad = [lbl for o, lbl in checks if not o]
if bad: print('FAILURES:', bad)
raise SystemExit(0 if ok == tot else 1)
