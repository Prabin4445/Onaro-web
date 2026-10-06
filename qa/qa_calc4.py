#!/usr/bin/env python3
"""Calculator QA round 4: multi-line textarea display with vertical scroll.
Fresh profile, 390x844, dark+light, zero console errors."""
import json, subprocess, time, urllib.request, os, base64, shutil

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9474
PROF = '/tmp/hubqa-calc4'
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

TYPE_JS = ("(function(){var s=__S__;var m={'0':'k0','1':'k1','2':'k2','3':'k3','4':'k4','5':'k5',"
           "'6':'k6','7':'k7','8':'k8','9':'k9','+':'plus'};"
           "for(var i=0;i<s.length;i++){var ch=s[i];HUB.calc._press(m[ch],m[ch]==='plus'?'+':ch);}})()")

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
        note(js("document.getElementById('calcExpr').tagName") == 'TEXTAREA', 'display is now a textarea')
        note(js("document.getElementById('calcExpr').readOnly") is True, 'textarea is readonly')
        js("document.getElementById('calcRoot').scrollIntoView({block:'start'})"); time.sleep(0.5)

        # --- 1. medium expression wraps to multiple lines, display grows downward ---
        js("HUB.calc._press('ac')")
        js(TYPE_JS.replace('__S__', "'1234567890+2345678901+3456789012+4567890123+5678901234'"))
        geo = js("(()=>{var e=document.getElementById('calcExpr');var cs=getComputedStyle(e);"
                 "return {h:parseFloat(cs.height),sh:e.scrollHeight,ch:e.clientHeight,sw:e.scrollWidth,cw:e.clientWidth}})()")
        note(isinstance(geo, dict) and geo['h'] > 70, 'display grew downward past one line', json.dumps(geo))
        note(isinstance(geo, dict) and geo['sw'] <= geo['cw'] + 2, 'no horizontal clipping inside display', json.dumps(geo))
        vis = js("(()=>{var e=document.getElementById('calcExpr');return e.scrollTop+e.clientHeight>=e.scrollHeight-4})()")
        note(vis is True, 'caret/newest chars visible at end of medium expression')
        errs('multiline-medium')

        # --- 2. very long expression: capped at 4 lines, caret kept in view ---
        js("HUB.calc._press('ac')")
        js(TYPE_JS.replace('__S__', "'1234567890+2345678901+3456789012+4567890123+5678901234+6789012345+7890123456+8901234567+9012345678+0123456789'"))
        geo2 = js("(()=>{var e=document.getElementById('calcExpr');var cs=getComputedStyle(e);"
                  "return {h:parseFloat(cs.height),sh:e.scrollHeight,ch:e.clientHeight,st:e.scrollTop,v:!!e.value}})()")
        note(isinstance(geo2, dict) and geo2['h'] <= 172, 'display capped at ~4 lines', json.dumps(geo2))
        note(isinstance(geo2, dict) and geo2['sh'] > geo2['ch'], 'long expression overflows into scroll', json.dumps(geo2))
        note(isinstance(geo2, dict) and geo2['st'] > 0, 'auto-scrolled down to the caret', json.dumps(geo2))
        vis2 = js("(()=>{var e=document.getElementById('calcExpr');return e.scrollTop+e.clientHeight>=e.scrollHeight-4})()")
        note(vis2 is True, 'last line visible after long typing')
        shot('calc4-multiline-dark')
        errs('multiline-long')

        # --- 3. user can scroll up/down through the expression ---
        js("document.getElementById('calcExpr').scrollTop=0")
        note(js("document.getElementById('calcExpr').scrollTop") == 0, 'user can scroll up to the first line')
        top_txt = js("document.getElementById('calcExpr').value.slice(0,10)")
        note(top_txt == '1234567890', 'first line content reachable', top_txt)
        shot('calc4-scrolled-up-dark')
        js("HUB.calc._press('k1','1')")  # typing again snaps back to the caret
        snap = js("(()=>{var e=document.getElementById('calcExpr');return e.scrollTop+e.clientHeight>=e.scrollHeight-4})()")
        note(snap is True, 'typing after scroll-up snaps back to caret')
        errs('scroll')

        # --- 4. tap-to-place cursor mid-text keeps caret visible ---
        js("HUB.calc._press('ac')")
        js(TYPE_JS.replace('__S__', "'1234567890+2345678901+3456789012+4567890123+5678901234+6789012345+7890123456+8901234567+9012345678+0123456789'"))
        js("(()=>{var e=document.getElementById('calcExpr');e.setSelectionRange(5,5);e.dispatchEvent(new MouseEvent('click',{bubbles:true}));})()")
        time.sleep(0.4)
        caret_ok = js("(()=>{var e=document.getElementById('calcExpr');return {s:e.selectionStart,st:e.scrollTop}})()")
        note(isinstance(caret_ok, dict) and caret_ok['s'] == 5 and caret_ok['st'] == 0,
             'tap-to-place caret kept, scrolled into view', json.dumps(caret_ok))
        js("HUB.calc._press('k9','9')")  # edit mid-expression
        note(js("document.getElementById('calcExpr').value").startswith('123459'), 'mid-expression edit inserts at caret')
        errs('caret')

        # --- 5. regressions ---
        js("HUB.calc._press('ac')")
        note(js("document.getElementById('calcExpr').value") == '', 'AC clears the textarea')
        note(js("(()=>{var e=document.getElementById('calcExpr');return parseFloat(getComputedStyle(e).height)<=50})()") is True,
             'display shrinks back to one line after AC')
        js("HUB.calc._press('sin','sin(');HUB.calc._press('k3','3');HUB.calc._press('k0','0');HUB.calc._press('rp',')')")
        note(js("document.getElementById('calcRes').textContent") == '= 0.5', 'sin(30)=0.5 still good')
        note(js("document.querySelector('#calcRoot .calc-disp').classList.contains('calc-glow')") is True, 'display typing glow still works')
        c0 = js("HUB.calc._sndStats().clicks"); js("HUB.calc._press('k5','5')")
        note(js("HUB.calc._sndStats().clicks") == c0 + 1, 'click sound path still fires')
        js("document.querySelector('#calcRoot [data-ck=\"k7\"]').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}))")
        note(js("document.querySelector('#calcRoot [data-ck=\"k7\"]').classList.contains('kglow')") is True, 'key glow still works')
        js("document.querySelector('#calcRoot [data-ck=\"k7\"]').dispatchEvent(new PointerEvent('pointerup',{bubbles:true}))")
        js("HUB.calc._press('ac');HUB.calc._press('k2','2');HUB.calc._press('plus','+');HUB.calc._press('k2','2');HUB.calc._press('eq')")
        note(js("document.querySelectorAll('#calcHist .calc-hrow').length") >= 1, 'history still records')
        js("document.querySelector('#calcHist .calc-hrow').click()"); time.sleep(0.3)
        note('2+2' in (js("document.getElementById('calcExpr').value") or ''), 'history tap reloads')
        js("HUB.calc._press('mode')")
        note(js("document.getElementById('calcModeBtn').textContent") == 'RAD', 'DEG/RAD toggle intact')
        js("HUB.calc._press('mode')")
        js("HUB.calc._press('ac')")
        note(js("document.documentElement.scrollWidth <= 390") is True, 'no horizontal overflow at 390px')
        errs('regression')

        # --- 6. light theme ---
        js("HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme();")
        time.sleep(1)
        note(js("!document.body.classList.contains('dark')") is True, 'light theme applied')
        js("HUB.calc._press('ac')")
        js(TYPE_JS.replace('__S__', "'1234567890+2345678901+3456789012+4567890123+5678901234+6789012345+7890123456+8901234567+9012345678+0123456789'"))
        geo3 = js("(()=>{var e=document.getElementById('calcExpr');return {h:parseFloat(getComputedStyle(e).height),ok:e.scrollTop+e.clientHeight>=e.scrollHeight-4}})()")
        note(isinstance(geo3, dict) and geo3['h'] > 70 and geo3['ok'], 'multi-line + caret tracking in light theme', json.dumps(geo3))
        js("document.getElementById('calcRoot').scrollIntoView({block:'start'})"); time.sleep(0.4)
        shot('calc4-multiline-light')
        errs('light')

        fails = [l for ok, l in checks if not ok]
        print('\n==== %d/%d passed ====' % (len(checks) - len(fails), len(checks)))
        if fails: print('FAILURES:', fails)
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
