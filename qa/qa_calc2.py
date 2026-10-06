#!/usr/bin/env python3
"""Calculator refinement QA: bigger display, volt typing glow, long-expression
caret visibility. Fresh profile, 390x844, dark+light, zero console errors."""
import json, subprocess, time, urllib.request, os, base64, shutil

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9472
PROF = '/tmp/hubqa-calc2'
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

CARET_JS = """(()=>{var el=document.getElementById('calcExpr');
var c=document.createElement('canvas').getContext('2d');
var cs=getComputedStyle(el); c.font=(cs.fontWeight||'700')+' '+cs.fontSize+' '+cs.fontFamily;
var pos=(el.selectionStart==null)?el.value.length:el.selectionStart;
var total=c.measureText(el.value).width, head=c.measureText(el.value.slice(0,pos)).width;
var cx=Math.max(0,el.scrollWidth-total)+head;
return {cx:Math.round(cx), sl:el.scrollLeft, cw:el.clientWidth,
  inView: cx>=el.scrollLeft-1 && cx<=el.scrollLeft+el.clientWidth+1}})()"""

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
        note(js("!!document.getElementById('calcRoot')"), 'calculator card present on Daily tab')
        js("document.getElementById('calcRoot').scrollIntoView({block:'start'})"); time.sleep(0.5)

        # --- 1. bigger display ---
        fs = js("getComputedStyle(document.getElementById('calcExpr')).fontSize")
        mh = js("getComputedStyle(document.getElementById('calcExpr')).minHeight")
        dh = js("document.querySelector('#calcRoot .calc-disp').getBoundingClientRect().height")
        note(fs == '32px', 'display type enlarged to 32px (was 24px)', str(fs))
        note(mh == '44px', 'display min-height 44px (was 32px)', str(mh))
        note(dh and dh > 90, 'display box taller', str(round(dh or 0)) + 'px')
        rfs = js("getComputedStyle(document.getElementById('calcRes')).fontSize")
        note(rfs == '17px', 'result line enlarged to 17px', str(rfs))

        # --- 2. volt glow on typing ---
        js("HUB.calc._press('k7','7')")
        g = js("document.querySelector('#calcRoot .calc-disp').classList.contains('calc-glow')")
        note(g, 'typing adds volt glow to display')
        glow_shot = js("(()=>{var d=document.querySelector('#calcRoot .calc-disp');var b=getComputedStyle(d).boxShadow;return b.indexOf('198, 241, 53')>=0})()")
        note(glow_shot, 'glow is brand volt (198,241,53), not purple')
        time.sleep(1.0)
        g2 = js("document.querySelector('#calcRoot .calc-disp').classList.contains('calc-glow')")
        note(not g2, 'glow settles (class removed) after typing stops')
        shot('calc2-glow-dark')
        errs('glow')

        # --- 3. long expression: caret always visible ---
        js("HUB.calc._press('ac')")
        long_expr = '1234567890+9876543210+1234567890+9876543210'
        js("(function(){var s=%s; for(var i=0;i<s.length;i++){var ch=s[i]; var map={'0':'k0','1':'k1','2':'k2','3':'k3','4':'k4','5':'k5','6':'k6','7':'k7','8':'k8','9':'k9','+':'plus'}; HUB.calc._press(map[ch], ch=='+'?'+':ch);}})()" % json.dumps(long_expr))
        v = js("document.getElementById('calcExpr').value")
        note(v == long_expr, '40+ char expression typed fully', str(len(v or '')) + ' chars')
        ovf = js("(()=>{var el=document.getElementById('calcExpr'); return el.scrollWidth>el.clientWidth+1})()")
        note(ovf, 'expression overflows display (scrollable)')
        sl = js("document.getElementById('calcExpr').scrollLeft")
        note(sl and sl > 0, 'display auto-scrolled to tail (scrollLeft>0)', str(sl))
        sfs = js("getComputedStyle(document.getElementById('calcExpr')).fontSize")
        note(sfs != '32px', 'type auto-shrunk for long expression', str(sfs))
        ci = js(CARET_JS)
        note(isinstance(ci, dict) and ci.get('inView'), 'caret/tail visible in viewport', json.dumps(ci))
        shot('calc2-long-dark')

        # --- mid-expression edit: caret stays visible ---
        js("(()=>{var el=document.getElementById('calcExpr'); el.setSelectionRange(5,5)})()")
        js("HUB.calc._press('k9','9')")
        v2 = js("document.getElementById('calcExpr').value")
        note(v2 == long_expr[:5] + '9' + long_expr[5:], 'mid-expression insert at caret', (v2 or '')[:12] + '...')
        ci2 = js(CARET_JS)
        note(isinstance(ci2, dict) and ci2.get('inView'), 'caret visible after mid-expression edit', json.dumps(ci2))
        errs('long-expr')

        # --- 4. regression spot-checks (old 47-check battery key paths) ---
        js("HUB.calc._press('ac')")
        js("HUB.calc._press('sin','sin(');HUB.calc._press('k3','3');HUB.calc._press('k0','0');HUB.calc._press('rp',')')")
        note(js("document.getElementById('calcRes').textContent") == '= 0.5', 'sin(30)=0.5 still good')
        js("HUB.calc._press('mode')")
        note(js("document.getElementById('calcModeBtn').textContent") == 'RAD', 'DEG/RAD toggle still works')
        js("HUB.calc._press('mode')")
        js("HUB.calc._press('ac');HUB.calc._press('k2','2');HUB.calc._press('plus','+');HUB.calc._press('k2','2');HUB.calc._press('eq')")
        n = js("document.querySelectorAll('#calcHist .calc-hrow').length")
        note(n >= 1, 'history recorded', str(n))
        first = js("document.querySelector('#calcHist .calc-hrow .calc-hexpr').textContent")
        js("document.querySelector('#calcHist .calc-hrow').click()"); time.sleep(0.3)
        note(js("document.getElementById('calcExpr').value") == first, 'history tap reloads', first)
        js("HUB.calc._press('ac');HUB.calc._press('k1','1');HUB.calc._press('kdiv','\u00f7');HUB.calc._press('k0','0');HUB.calc._press('eq')")
        note('divide by zero' in (js("document.getElementById('calcRes').textContent") or '').lower(), 'friendly div0 error intact')
        ovf2 = js("document.documentElement.scrollWidth <= 390")
        note(ovf2, 'no horizontal overflow at 390px')
        errs('regression')

        # --- 5. reduced motion: no pulse animation ---
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
        time.sleep(0.4)
        js("HUB.calc._press('k5','5')")
        anim = js("(()=>{var d=document.querySelector('#calcRoot .calc-disp');return {pulse:d.classList.contains('calc-pulse'), glow:d.classList.contains('calc-glow'), anim:getComputedStyle(d).animationName}})()")
        note(isinstance(anim, dict) and anim.get('glow') and anim.get('anim') == 'none',
             'reduced-motion: instant glow state, no pulse animation', json.dumps(anim))
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'no-preference'}]})

        # --- light theme ---
        js("HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme();")
        time.sleep(1)
        note(js("!document.body.classList.contains('dark')"), 'light theme applied')
        js("HUB.calc._press('ac')")
        js("(function(){var s='9876543210+1234567890+9876543210+1234567890'; for(var i=0;i<s.length;i++){var ch=s[i]; var map={'0':'k0','1':'k1','2':'k2','3':'k3','4':'k4','5':'k5','6':'k6','7':'k7','8':'k8','9':'k9','+':'plus'}; HUB.calc._press(map[ch], ch=='+'?'+':ch);}})()")
        ci3 = js(CARET_JS)
        note(isinstance(ci3, dict) and ci3.get('inView'), 'long expression caret visible (light)', json.dumps(ci3))
        js("document.getElementById('calcRoot').scrollIntoView({block:'start'})"); time.sleep(0.4)
        shot('calc2-long-light')
        errs('light')

        fails = [l for ok, l in checks if not ok]
        print('\n==== %d/%d passed ====' % (len(checks) - len(fails), len(checks)))
        if fails: print('FAILURES:', fails)
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
