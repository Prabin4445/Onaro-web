#!/usr/bin/env python3
"""Calculator QA: UX order — no shift layers, cursor editing, long-press DEL,
live preview, tap-to-copy, DEG/RAD one-tap. Dark+light, 390x844, zero console errors."""
import json, subprocess, time, urllib.request, os, base64, shutil

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9471
PROF = '/tmp/hubqa-calc'
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
        def js(expr, await_p=False):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': await_p})
                res = (r or {}).get('result', {}); return res.get('value')
            except Exception as e: return 'JSERR:' + str(e)[:120]
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def click(sel):
            js("(()=>{const el=document.querySelector('"+sel+"'); if(!el) return 'MISSING'; el.scrollIntoView({block:'center'}); return 'ok'})()")
            time.sleep(0.25); js("document.querySelector('"+sel+"').click()"); time.sleep(0.35)
        def key(ck):
            click('#calcRoot [data-ck="'+ck+'"]')
        def tapDel(hold_ms=120):
            # DEL binds pointerdown/up (long-press detection), not click
            js("document.querySelector('#calcRoot [data-ck=\"del\"]').scrollIntoView({block:'center'})")
            time.sleep(0.2)
            js("(()=>{var b=document.querySelector('#calcRoot [data-ck=\"del\"]'); b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}))})()")
            time.sleep(hold_ms / 1000.0)
            js("(()=>{var b=document.querySelector('#calcRoot [data-ck=\"del\"]'); b.dispatchEvent(new PointerEvent('pointerup',{bubbles:true}))})()")
            time.sleep(0.35)
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

        # --- no SHIFT layers ---
        nkeys = js("document.querySelectorAll('#calcRoot [data-ck]').length")
        note(nkeys == 44, '44 keys, no INV/shift key', str(nkeys))
        noinv = js("!document.querySelector('#calcRoot [data-ck=\"inv\"]')")
        note(noinv, 'no INV key anywhere')
        for fid in ['sin','cos','tan','asin','acos','atan','log','ln','p10','pex','sqrt','sq','cb','rc']:
            note(js("!!document.querySelector('#calcRoot [data-ck=\""+fid+"\"]')"), 'dedicated one-tap key: ' + fid)
        # single-tap asin: one click inserts sin⁻¹(
        key('ac'); key('asin')
        note(js("document.getElementById('calcExpr').value") == 'sin⁻¹(', 'asin inserts sin⁻¹( in ONE tap')

        # --- key size (visible keys only: graph keypad is pre-rendered but hidden) ---
        mn = js("Math.min(...[...document.querySelectorAll('#calcRoot .calc-key')].filter(b=>b.getBoundingClientRect().height>0).map(b=>b.getBoundingClientRect().height))")
        note(mn >= 44, 'all keys >= 44px tall', 'min=' + str(mn))
        ovf = js("document.documentElement.scrollWidth <= 390")
        note(ovf, 'no horizontal overflow at 390px')

        # --- live preview on partial expression ---
        key('ac'); key('k5'); key('plus')
        note(js("document.getElementById('calcRes').textContent") == '', 'preview blank on partial "5+"')
        key('k3')
        note(js("document.getElementById('calcRes').textContent") == '= 8', 'live preview "= 8" as you type')
        key('eq')
        note(js("document.getElementById('calcExpr').value") == '8', 'commit shows result 8')
        note(js("HUB.store.state.calcAns") == 8, 'Ans persisted = 8')

        # --- cursor tap-to-place + mid-expression edit ---
        key('ac')
        for kk in ['k1','k2','plus','k3','k4']: key(kk)
        js("var el=document.getElementById('calcExpr'); el.setSelectionRange(2,2)")
        tapDel()
        v = js("document.getElementById('calcExpr').value")
        note(v == '1+34', 'DEL at cursor deletes mid-expression char', v)
        note(js("document.getElementById('calcRes').textContent") == '= 35', 'preview updates after mid-edit')
        # tap-to-place via real click coordinates (native input cursor)
        pos = js("(()=>{var el=document.getElementById('calcExpr'); el.value='12+34'; var r=el.getBoundingClientRect(); var x=r.left+8; var y=r.top+r.height/2; var ev=new MouseEvent('click',{bubbles:true,cancelable:true,clientX:x,clientY:y}); el.dispatchEvent(ev); el.focus(); el.setSelectionRange(0,0); return el.selectionStart})()")
        note(pos == 0, 'expression is a focusable input (native cursor)', str(pos))

        # --- long-press DEL = clear all ---
        key('ac')
        for kk in ['k7','k8','k9']: key(kk)
        js("(()=>{var b=document.querySelector('#calcRoot [data-ck=\"del\"]'); b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}))})()")
        time.sleep(0.8)
        js("(()=>{var b=document.querySelector('#calcRoot [data-ck=\"del\"]'); b.dispatchEvent(new PointerEvent('pointerup',{bubbles:true}))})()")
        time.sleep(0.3)
        note(js("document.getElementById('calcExpr').value") == '', 'long-press DEL clears everything')
        # short press still deletes one char
        for kk in ['k7','k8']: key(kk)
        tapDel()
        note(js("document.getElementById('calcExpr').value") == '7', 'short DEL press deletes one char')

        # --- tap-to-copy on result ---
        key('ac'); key('k2'); key('plus'); key('k2'); key('eq')
        js("document.getElementById('calcRes').click()"); time.sleep(0.6)
        toast = js("document.getElementById('toastHost').textContent")
        note('Copied' in (toast or ''), 'tap result -> Copied toast', (toast or '')[:40])
        js("document.getElementById('toastHost').innerHTML=''")

        # --- DEG/RAD one-tap toggle ---
        key('mode')
        lbl = js("document.getElementById('calcModeBtn').textContent")
        glbl = js("document.querySelector('#calcRoot [data-ck=\"mode\"]').textContent")
        note(lbl == 'RAD' and glbl == 'RAD', 'one-tap DEG->RAD updates both chips', lbl + '/' + glbl)
        r = js("HUB.calc._eval('sin(30)','rad').value")
        note(abs(r - (-0.9880316241)) < 1e-6, 'RAD mode trig correct', str(r))
        key('mode')
        note(js("document.getElementById('calcModeBtn').textContent") == 'DEG', 'one-tap back to DEG')

        # --- EXP entry, Ans chain, friendly errors ---
        key('ac')
        for kk in ['k1','dot','k5','exp','k3']: key(kk)
        note(js("document.getElementById('calcRes').textContent") == '= 1500', 'EXP entry 1.5E3 previews = 1500')
        key('eq')
        key('ans'); key('kmul'); key('k2'); key('eq')
        note(js("document.getElementById('calcExpr').value") == '3000', 'Ans chain: 1500 -> Ans*2 = 3000')
        key('ac'); key('k1'); key('kdiv'); key('k0'); key('eq')
        note(js("document.getElementById('calcRes').textContent") == "Can't divide by zero.", 'friendly div0 error')

        # --- history tap-to-reload ---
        n = js("document.querySelectorAll('#calcHist .calc-hrow').length")
        note(n >= 3, 'history tape has entries', str(n))
        first = js("document.querySelector('#calcHist .calc-hrow .calc-hexpr').textContent")
        click('#calcHist .calc-hrow')
        note(js("document.getElementById('calcExpr').value") == first, 'history tap reloads expression', first)

        # --- physical keyboard ---
        key('ac')
        js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'9',bubbles:true}))")
        time.sleep(0.3)
        note(js("document.getElementById('calcExpr').value") == '9', 'physical keyboard digit works')
        js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")
        time.sleep(0.3)
        note(js("document.getElementById('calcExpr').value") == '', 'physical Escape = AC')

        # --- parser speed (no jank) ---
        ms = js("(()=>{var t0=performance.now(); for(var i=0;i<2000;i++) HUB.calc._eval('2^3^2+sin(30)*log(100)-5P2/5C2','deg'); return performance.now()-t0})()")
        note(ms < 2000, '2000 parses < 2s (no jank)', str(round(ms)) + 'ms')

        # --- reduced motion ---
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
        time.sleep(0.4)
        tr = js("getComputedStyle(document.querySelector('#calcRoot .calc-key')).transitionDuration")
        # app global rule forces transition-duration:.01ms under reduce — effectively instant
        ok_rm = False
        try: ok_rm = float(str(tr).rstrip('s')) <= 0.001
        except Exception: ok_rm = False
        note(ok_rm, 'reduced-motion kills key transitions', str(tr))
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'no-preference'}]})

        errs('interactions')
        shot('calculator-dark')

        # --- light theme ---
        js("HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme();")
        time.sleep(1)
        note(js("!document.body.classList.contains('dark')"), 'light theme applied')
        errs('light')
        shot('calculator-light')
        js("document.getElementById('calcHist').scrollIntoView({block:'center'})"); time.sleep(0.5)
        shot('calculator-history')
        errs('final')
    finally:
        proc.terminate()

    fails = [l for ok, l in checks if not ok]
    print('\n==== %d/%d passed ====' % (len(checks) - len(fails), len(checks)))
    if fails: print('FAILURES:', fails)

main()
