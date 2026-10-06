#!/usr/bin/env python3
"""Calculator QA round 3: key press glow + iPhone-feel key click sound.
Fresh profile, 390x844, dark+light, zero console errors."""
import json, subprocess, time, urllib.request, os, base64, shutil

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9473
PROF = '/tmp/hubqa-calc3'
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

def main():
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
                res = (r or {}).get('result', {}); return res.get('value')
            except Exception as e: return 'JSERR:' + str(e)[:120]
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, 'zero console errors @ ' + label, json.dumps(v)[:200] if v else '')

        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        js("var p=HUB.store.state.profile; p.name='PraBin'; p.campus='Downtown'; p.audience='community'; HUB.store.save(); try{HUB.ui.closeSheet();}catch(e){} HUB.showTab('daily');")
        time.sleep(2)
        errs('load')
        note(js("!!document.getElementById('calcRoot')"), 'calculator card present')
        note(js("!!document.getElementById('calcSndBtn')"), 'sound toggle button present in header')
        js("document.getElementById('calcRoot').scrollIntoView({block:'start'})"); time.sleep(0.5)

        # --- 1. key glow on press ---
        g0 = js("document.querySelector('#calcRoot [data-ck=\"k7\"]').classList.contains('kglow')")
        note(not g0, 'no glow before press')
        js("document.querySelector('#calcRoot [data-ck=\"k7\"]').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}))")
        g1 = js("document.querySelector('#calcRoot [data-ck=\"k7\"]').classList.contains('kglow')")
        note(g1, 'pointerdown adds volt key glow')
        gbs = js("getComputedStyle(document.querySelector('#calcRoot [data-ck=\"k7\"]')).boxShadow")
        note(gbs and '198, 241, 53' in gbs, 'key glow is brand volt, not purple', (gbs or '')[:70])
        shot('calc3-keyglow-dark')
        js("document.querySelector('#calcRoot [data-ck=\"k7\"]').dispatchEvent(new PointerEvent('pointerup',{bubbles:true}))")
        g2 = js("document.querySelector('#calcRoot [data-ck=\"k7\"]').classList.contains('kglow')")
        note(not g2, 'pointerup removes key glow')
        # press() path (physical keyboard) also glows
        js("HUB.calc._press('k8','8')")
        g3 = js("document.querySelector('#calcRoot [data-ck=\"k8\"]').classList.contains('kglow')")
        note(g3, 'press() path flashes key glow (physical keyboard)')
        time.sleep(0.4)
        g4 = js("document.querySelector('#calcRoot [data-ck=\"k8\"]').classList.contains('kglow')")
        note(not g4, 'key glow clears after short timeout')
        # = key brighter variant
        js("HUB.calc._press('ac')")
        js("HUB.calc._press('k2','2');HUB.calc._press('plus','+');HUB.calc._press('k2','2');HUB.calc._press('eq')")
        ge = js("document.querySelector('#calcRoot [data-ck=\"eq\"]').classList.contains('kglow')")
        gbs2 = js("getComputedStyle(document.querySelector('#calcRoot [data-ck=\"eq\"]')).boxShadow")
        note(ge and gbs2 and '198, 241, 53' in gbs2, '= key gets brighter glow variant', (gbs2 or '')[:70])
        note(js("document.getElementById('calcExpr').value") == '4', '= evaluated fine with glow+sound wired')
        errs('glow')

        # --- 2. key click sound (WebAudio path, headless = no audible output) ---
        s0 = js("HUB.calc._sndStats()")
        note(isinstance(s0, dict) and s0.get('on') is True, 'sound toggle defaults ON', json.dumps(s0))
        note(js("document.getElementById('calcSndBtn').textContent") == '🔊', 'toggle shows 🔊 when ON')
        c0 = js("HUB.calc._sndStats().clicks")
        js("HUB.calc._press('k5','5')")
        s1 = js("HUB.calc._sndStats()")
        note(isinstance(s1, dict) and s1.get('clicks') == c0 + 1, 'keypress runs the WebAudio click path', json.dumps(s1))
        note(isinstance(s1, dict) and s1.get('ctx') in ('running', 'suspended'), 'AudioContext created without throwing', str(s1.get('ctx')))
        # DEL via pointer events also clicks
        c1 = js("HUB.calc._sndStats().clicks")
        js("var b=document.querySelector('#calcRoot [data-ck=\"del\"]');b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));b.dispatchEvent(new PointerEvent('pointerup',{bubbles:true}))")
        note(js("HUB.calc._sndStats().clicks") == c1 + 1, 'DEL press clicks too')
        errs('sound-on')

        # --- 3. toggle OFF silences + persists ---
        js("document.getElementById('calcSndBtn').click()")
        note(js("HUB.calc._sndStats().on") is False, 'toggle turns sound OFF')
        note(js("document.getElementById('calcSndBtn').textContent") == '🔇', 'toggle shows 🔇 when OFF')
        c2 = js("HUB.calc._sndStats().clicks")
        js("HUB.calc._press('k6','6')")
        note(js("HUB.calc._sndStats().clicks") == c2, 'toggle OFF: no click produced')
        c.send('Page.reload', {}); time.sleep(6)
        js("try{HUB.ui.closeSheet();}catch(e){} HUB.showTab('daily');"); time.sleep(1.5)
        note(js("HUB.calc._sndStats().on") is False, 'sound preference persists across reload')
        note(js("document.getElementById('calcSndBtn').textContent") == '🔇', 'toggle icon persists as 🔇')
        js("document.getElementById('calcSndBtn').click()")
        note(js("HUB.calc._sndStats().on") is True, 'toggle turns sound back ON')
        errs('toggle')

        # --- 4. reduced motion: glow instant, no animation ---
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
        time.sleep(0.4)
        js("HUB.calc._press('k9','9')")
        rm = js("(()=>{var k=document.querySelector('#calcRoot [data-ck=\"k9\"]');return {g:k.classList.contains('kglow'),a:getComputedStyle(k).animationName}})()")
        note(isinstance(rm, dict) and rm.get('g') and rm.get('a') == 'none', 'reduced-motion: key glow present, no animation', json.dumps(rm))
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'no-preference'}]})

        # --- 5. regression spot-checks ---
        js("HUB.calc._press('ac')")
        js("HUB.calc._press('sin','sin(');HUB.calc._press('k3','3');HUB.calc._press('k0','0');HUB.calc._press('rp',')')")
        note(js("document.getElementById('calcRes').textContent") == '= 0.5', 'sin(30)=0.5 still good')
        dg = js("document.querySelector('#calcRoot .calc-disp').classList.contains('calc-glow')")
        note(dg, 'display typing glow still works')
        js("HUB.calc._press('ac')")
        js("(function(){var s='1234567890+9876543210+1234567890'; for(var i=0;i<s.length;i++){var ch=s[i]; var map={'0':'k0','1':'k1','2':'k2','3':'k3','4':'k4','5':'k5','6':'k6','7':'k7','8':'k8','9':'k9','+':'plus'}; HUB.calc._press(map[ch], ch=='+'?'+':ch);}})()")
        sl = js("document.getElementById('calcExpr').scrollLeft")
        note(sl and sl > 0, 'long-expression caret tracking intact', str(sl))
        js("HUB.calc._press('ac');HUB.calc._press('k2','2');HUB.calc._press('plus','+');HUB.calc._press('k2','2');HUB.calc._press('eq')")
        note(js("document.querySelectorAll('#calcHist .calc-hrow').length") >= 1, 'history still records')
        first = js("document.querySelector('#calcHist .calc-hrow .calc-hexpr').textContent")
        js("document.querySelector('#calcHist .calc-hrow').click()"); time.sleep(0.3)
        note(js("document.getElementById('calcExpr').value") == first, 'history tap reloads', first)
        js("HUB.calc._press('mode')")
        note(js("document.getElementById('calcModeBtn').textContent") == 'RAD', 'DEG/RAD toggle intact')
        js("HUB.calc._press('mode')")
        note(js("document.documentElement.scrollWidth <= 390"), 'no horizontal overflow at 390px')
        errs('regression')

        # --- light theme ---
        js("HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme();")
        time.sleep(1)
        note(js("!document.body.classList.contains('dark')"), 'light theme applied')
        js("document.querySelector('#calcRoot [data-ck=\"k3\"]').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}))")
        gl = js("getComputedStyle(document.querySelector('#calcRoot [data-ck=\"k3\"]')).boxShadow")
        note(gl and '198, 241, 53' in gl, 'volt key glow in light theme', (gl or '')[:70])
        js("document.getElementById('calcRoot').scrollIntoView({block:'start'})"); time.sleep(0.4)
        shot('calc3-keyglow-light')
        js("document.querySelector('#calcRoot [data-ck=\"k3\"]').dispatchEvent(new PointerEvent('pointerup',{bubbles:true}))")
        errs('light')

        fails = [l for ok, l in checks if not ok]
        print('\n==== %d/%d passed ====' % (len(checks) - len(fails), len(checks)))
        if fails: print('FAILURES:', fails)
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
