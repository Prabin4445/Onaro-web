#!/usr/bin/env python3
"""Calculator QA round 5: graphing calculator mode.
Parser x-variable + canvas plotter. Fresh profile, 390x844, dark+light, zero console errors."""
import json, subprocess, time, urllib.request, os, base64, shutil

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9475
PROF = '/tmp/hubqa-calc5'
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

def run_theme(theme, shots_prefix):
    global checks
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
        note(js("document.body.classList.contains('dark')") == (theme == 'dark'), f'theme applied [{theme}]')

        # ============ 1. parser x-variable ============
        note(js("HUB.calc._eval('x^2','rad',{x:3}).value") == 9, 'x^2 at x=3 = 9')
        note(abs(js("HUB.calc._eval('sin(x)','rad',{x:Math.PI/2}).value") - 1) < 1e-9, 'sin(x) rad at pi/2 = 1')
        note(js("HUB.calc._eval('2*x+3','rad',{x:4}).value") == 11, '2*x+3 at x=4 = 11')
        note(js("HUB.calc._eval('2x','rad',{x:3}).value") == 6, 'implicit mult 2x at x=3 = 6')
        note(js("HUB.calc._eval('x^2+2*x+1','rad',{x:2}).value") == 9, '(x+1)^2 at x=2 = 9')
        note(js("HUB.calc._eval('sqrt(x)','rad',{x:16}).value") == 4, 'sqrt(x) at x=16 = 4')
        note(js("HUB.calc._eval('1/x','rad',{x:0}).ok") == 0, '1/x at x=0 -> domain error, no crash')
        r = js("HUB.calc._eval('x','rad')")
        note(isinstance(r, dict) and r.get('ok') == 0, 'unbound x without env -> not ok (old behavior preserved)')
        # regressions: constant expressions untouched
        note(abs(js("HUB.calc._eval('sin(30)').value") - 0.5) < 1e-9, 'regression: sin(30) DEG = 0.5')
        note(js("HUB.calc._eval('(2+3)*4').value") == 20, 'regression: (2+3)*4 = 20')
        note(abs(js("HUB.calc._eval('2*3.1415926536','rad').value") - 6.2831852) < 1e-6, 'regression: 2*pi const')
        note(js("HUB.calc._eval('5P2').value") == 20, 'regression: 5P2 = 20')
        note(js("HUB.calc._graph.compile('2+*x').ok") == 0, "invalid '2+*x' -> friendly error path")

        # ============ 2. graph view toggle ============
        js("document.getElementById('calcRoot').scrollIntoView({block:'start'})"); time.sleep(0.4)
        js("document.getElementById('calcViewBtn').click()"); time.sleep(1.0)
        note(js("document.getElementById('calcGraph').hidden") is False, 'graph view shown after toggle')
        note(js("document.getElementById('calcNormal').hidden") is True, 'calc keypad hidden in graph view')
        geo = js("(()=>{var cv=document.getElementById('calcCanvas');var r=cv.getBoundingClientRect();return {w:r.width,h:r.height}})()")
        note(isinstance(geo, dict) and geo['w'] > 200 and geo['h'] >= 200, 'canvas laid out', json.dumps(geo))

        # ============ 3. curves actually render ============
        js("HUB.calc._graph.state().cx=0;HUB.calc._graph.state().cy=0;HUB.calc._graph.state().ppu=34;"
           "HUB.calc._graph.state().funcs=['sin(x)','x^2'];HUB.calc._graph.render()")
        time.sleep(0.4)
        px = js("""(()=>{var cv=document.getElementById('calcCanvas');var cx=cv.getContext('2d');
          var d=cx.getImageData(0,0,cv.width,cv.height).data;var n=0;
          for(var i=3;i<d.length;i+=16){if(d[i]>10)n++;}return n;})()""")
        note(isinstance(px, int) and px > 500, 'canvas non-blank (grid+axes+curves)', str(px))
        cols = js("HUB.calc._graph.colors()")
        note(isinstance(cols, list) and len(cols) == 4 and len(set(cols)) == 4, '4 distinct curve colors', json.dumps(cols))
        note(not any('7c3aed' in str(x).lower() or '8b5cf6' in str(x).lower() or 'a855f7' in str(x).lower() for x in (cols or [])), 'no purple in curve palette')
        # both curves drawn in their own colors: pixel-count per color
        cnt = js("""(()=>{function hx(h){return [parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),parseInt(h.slice(5,7),16)];}
          var cols=HUB.calc._graph.colors();var cv=document.getElementById('calcCanvas');
          var d=cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;
          var out=[0,0];
          for(var i=0;i<d.length;i+=4){for(var f=0;f<2;f++){var c=hx(cols[f]);
            if(Math.abs(d[i]-c[0])<50&&Math.abs(d[i+1]-c[1])<50&&Math.abs(d[i+2]-c[2])<50&&d[i+3]>40){out[f]++;break;}}}
          return out;})()""")
        note(isinstance(cnt, list) and cnt[0] > 100 and cnt[1] > 50, 'sin(x) and x^2 each drawn in own color', json.dumps(cnt))

        # ============ 4. pan / zoom ============
        before = js("({cx:HUB.calc._graph.state().cx,ppu:HUB.calc._graph.state().ppu})")
        note(js("!!document.getElementById('calcCanvas')") is True, 'pan pre: canvas in DOM')
        dr = js("""(()=>{var cv=document.getElementById('calcCanvas');var r=cv.getBoundingClientRect();
          var o={bubbles:true,cancelable:true};
          cv.dispatchEvent(new PointerEvent('pointerdown',Object.assign({pointerId:7,clientX:r.left+120,clientY:r.top+120},o)));
          cv.dispatchEvent(new PointerEvent('pointermove',Object.assign({pointerId:7,clientX:r.left+170,clientY:r.top+120},o)));
          cv.dispatchEvent(new PointerEvent('pointerup',Object.assign({pointerId:7,clientX:r.left+170,clientY:r.top+120},o)));})()""")
        note(dr is None, 'pan dispatch evaluate clean', ('got: '+str(dr)[:160]) if dr else '')
        note(js("!!document.getElementById('calcCanvas')") is True, 'pan post: canvas in DOM')
        after = js("({cx:HUB.calc._graph.state().cx,ppu:HUB.calc._graph.state().ppu})")
        note(isinstance(before, dict) and isinstance(after, dict) and abs(after['cx'] - before['cx'] + 50/before['ppu']) < 0.05,
             'drag pans the viewport', json.dumps(after))
        js("document.getElementById('calcZoomIn').click()"); time.sleep(0.3)
        zin = js("HUB.calc._graph.state().ppu")
        note(isinstance(zin, (int, float)) and abs(zin - after['ppu']*1.45) < 0.01, 'zoom-in button scales up', str(zin))
        js("document.getElementById('calcZoomReset').click()"); time.sleep(0.3)
        zr = js("({cx:HUB.calc._graph.state().cx,cy:HUB.calc._graph.state().cy,ppu:HUB.calc._graph.state().ppu})")
        note(zr == {'cx': 0, 'cy': 0, 'ppu': 34}, 'reset restores default view', json.dumps(zr))

        # ============ 5. trace ============
        js("HUB.calc._graph.state().funcs=['x+2','-x+2'];HUB.calc._graph.state().ppu=20;HUB.calc._graph.render()")
        time.sleep(0.3)
        tr = js("""(()=>{var cv=document.getElementById('calcCanvas');var W=cv.clientWidth,H=cv.clientHeight;
          var sx=(2-0)*20+W/2, sy=H/2-(4-0)*20; return HUB.calc._graph.traceAt(sx,sy);})()""")
        note(isinstance(tr, dict) and tr.get('fi') == 0 and abs(tr.get('x', 9) - 2) < 0.25 and abs(tr.get('y', 9) - 4) < 0.35,
             'trace tap finds f1 (x,y)', json.dumps(tr))
        note(js("document.getElementById('calcTrace').hidden") is False, 'trace readout chip visible')
        note('f1' in str(js("document.getElementById('calcTrace').textContent")), 'trace chip labels f1')
        tr2 = js("""(()=>{var cv=document.getElementById('calcCanvas');var W=cv.clientWidth,H=cv.clientHeight;
          var sx=(4-0)*20+W/2, sy=H/2-(-2-0)*20; return HUB.calc._graph.traceAt(sx,sy);})()""")
        note(isinstance(tr2, dict) and tr2.get('fi') == 1, 'trace tap finds f2 separately', json.dumps(tr2))

        # ============ 6. invalid function -> friendly error (keypad path: rows are readonly) ============
        js("""(()=>{var i=document.querySelector('#calcFnRows [data-fi="0"]');
          i.click(); try{i.setSelectionRange(i.value.length,i.value.length);}catch(e){}})()""")
        time.sleep(0.3)
        for _ in range(8):
            js("document.querySelector('#calcGpad [data-gk=\"DEL\"]').click()")
        for k in ['2', '+', '×', 'x']:
            js("document.querySelector('#calcGpad [data-gk=\""+k+"\"]').click()")
        time.sleep(0.8)
        note(bool(js("document.querySelector('#calcFnRows [data-fe=\"0\"]').textContent")),
             'invalid function shows friendly error', js("document.querySelector('#calcFnRows [data-fe=\"0\"]').textContent") or '')
        errs('graph-invalid')

        # screenshots (RAD mode for the classic sin wave — via the real toggle so the chip stays in sync)
        js("if(HUB.store.state.calcMode!=='rad'){document.getElementById('calcModeBtn').click();}")
        time.sleep(0.4)
        js("HUB.calc._graph.state().funcs=['sin(x)','x^2'];HUB.calc._graph.rows();"
           "HUB.calc._graph.state().cx=0;"
           "HUB.calc._graph.state().cy=0;HUB.calc._graph.state().ppu=34;"
           "HUB.calc._graph.validate()")
        time.sleep(0.3)
        js("""(()=>{var cv=document.getElementById('calcCanvas');var W=cv.clientWidth,H=cv.clientHeight;
          HUB.calc._graph.traceAt(W/2+40,H/2-20);})()""")
        time.sleep(0.3)
        js("document.getElementById('calcRoot').scrollIntoView({block:'start'})"); time.sleep(0.5)
        shot(f'{shots_prefix}-graph')
        errs('graph-shots')

        # ============ 7. regressions back in calc view ============
        js("document.getElementById('calcViewBtn').click()"); time.sleep(0.8)
        note(js("document.getElementById('calcNormal').hidden") is False, 'back to calc view')
        js("HUB.calc._press('ac')"); js("HUB.calc._press('k7','7')")
        note(js("document.getElementById('calcExpr').value") == '7', 'keypad still types')
        note(js("document.querySelector('#calcRoot .calc-disp').classList.contains('calc-glow')") is True, 'regression: display typing glow')
        js("""(()=>{var b=document.querySelector('#calcRoot [data-ck="k7"]');
          b.dispatchEvent(new PointerEvent('pointerdown',{pointerId:9,bubbles:true}));})()""")
        note(js("document.querySelector('#calcRoot [data-ck=\"k7\"]').classList.contains('kglow')") is True, 'regression: key press glow')
        c0 = js("HUB.calc._sndStats().clicks")
        js("HUB.calc._press('k8','8')")
        note(js("HUB.calc._sndStats().clicks") == c0 + 1, 'regression: click-sound path runs')
        js("HUB.calc._press('ac')")
        for ch in '2+3':
            js(f"HUB.calc._press({{'2':'k2','+':'plus','3':'k3'}}['{ch}'],'{ch}')")
        js("HUB.calc._press('eq')")
        note(js("document.getElementById('calcRes').textContent").strip() == '= 5', 'regression: 2+3=5 commit')
        note(js("document.querySelectorAll('#calcHist .calc-hrow').length") >= 1, 'regression: history row added')
        lbl0 = js("document.getElementById('calcModeBtn').textContent")
        js("document.getElementById('calcModeBtn').click()"); time.sleep(0.3)
        note(js("document.getElementById('calcModeBtn').textContent") != lbl0, 'regression: DEG/RAD toggle')
        note(js("document.documentElement.scrollWidth") <= 391, 'no horizontal overflow',
             str(js("document.documentElement.scrollWidth")))
        errs('regressions')
    finally:
        proc.terminate(); proc.wait(timeout=10)

run_theme('dark', 'calc5')
run_theme('light', 'calc5l')

fails = [l for ok, l in checks if not ok]
print(f"\n==== {len(checks)-len(fails)}/{len(checks)} checks passed ====")
if fails:
    print('FAILURES:'); [print(' -', l) for l in fails]
    raise SystemExit(1)
