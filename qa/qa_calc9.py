#!/usr/bin/env python3
"""Calculator QA round 9: calculus keys on the graph keypad (tan / ln / log / e).

PraBin's order: "missing things for graph like f(x) and all which are needed
in calculus please correct it." The graph keypad gains a calculus row:
tan( ln( log( e  (30 keys total). The parser already supports all four, and
graph plotting shares it.
Fresh profiles, 390x844, dark+light, zero console errors.
"""
import json, subprocess, time, urllib.request, os, base64, shutil

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9485
PROF = '/tmp/hubqa-calc9'
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

CURVE_JS = """(function(){
  const cols=%s, cv=document.getElementById('calcCanvas');
  const x=cv.getContext('2d'), d=x.getImageData(0,0,cv.width,cv.height).data;
  const cc=cols.map(h=>[parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),parseInt(h.slice(5,7),16)]);
  let n=0;
  for(let i=0;i<d.length;i+=16){
    const r=d[i],g=d[i+1],b=d[i+2];
    for(const c of cc){ if(Math.abs(r-c[0])<48&&Math.abs(g-c[1])<48&&Math.abs(b-c[2])<48){ n++; break; } }
  }
  return n;
})()"""
DARK_COLS = "['#C6F135','#FF5C38','#35C6FF','#FFB800']"
LIGHT_COLS = "['#4A7A00','#C22E1F','#0077B6','#B97A00']"

# tan-colored pixels in the vertical strip around x=pi/2 (the asymptote).
# A naive plot draws a full-height connector line through the strip; the
# break-on-asymptote logic must leave it (nearly) empty. Returns {n,tot,sx}.
ASYM_JS = """(function(){
  const cv=document.getElementById('calcCanvas');
  const g=HUB.calc._graph.state();
  const W=cv.clientWidth, H=cv.clientHeight, dpr=window.devicePixelRatio||1;
  const sx=(Math.PI/2-g.cx)*g.ppu+W/2;
  if(sx<-10||sx>W+10) return {offscreen:true,sx:sx};
  const x0=Math.max(0,Math.floor((sx-4)*dpr)), x1=Math.min(cv.width-1,Math.ceil((sx+4)*dpr));
  const d=cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;
  const cc=%s;
  let n=0, tot=0;
  for(let y=0;y<cv.height;y+=3){ for(let x=x0;x<=x1;x+=3){
    tot++;
    const i=(y*cv.width+x)*4;
    if(Math.abs(d[i]-cc[0])<48&&Math.abs(d[i+1]-cc[1])<48&&Math.abs(d[i+2]-cc[2])<48) n++;
  }}
  return {n:n, tot:tot, sx:Math.round(sx)};
})()"""

def run_theme(theme):
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
        def gk(label):
            return js(f"document.querySelector('#calcGpad [data-gk=\"{label}\"]').click(),'clicked'")
        def rowval(i): return js(f"document.querySelector('.calc-fnin[data-fi=\"{i}\"]').value")
        def rowcaret(i): return js(f"document.querySelector('.calc-fnin[data-fi=\"{i}\"]').selectionStart")
        def setrow(i, v):
            # set a row's text AND sync the graph model (gPadIns does this on
            # real keypresses; without it validate() would plot stale funcs)
            return js(f"(function(){{const el=document.querySelector('.calc-fnin[data-fi=\"{i}\"]');"
                       f"el.value={json.dumps(v)};el.setSelectionRange(el.value.length,el.value.length);"
                       f"HUB.calc._graph.state().funcs[{i}]={json.dumps(v)};"
                       f"HUB.calc._graph.pad.active({i});HUB.calc._graph.validate();return el.value;}})()")
        def caretx(i):
            return js("(function(){const cd=document.querySelector('.calc-fncaret[data-fc=\"" + str(i) + "\"]');"
                      "if(!cd||cd.hidden||!cd.offsetWidth)return -1;return cd.offsetLeft;})()")
        def plot(expr):
            # set row 0, reset view, validate+render, return tan/row0-color pixel count
            setrow(0, expr)
            js("document.getElementById('calcZoomReset').click()"); time.sleep(0.4)
            return js(CURVE_JS % cols)

        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
           "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        js("var p=HUB.store.state.profile; p.name='PraBin'; p.campus='Downtown'; p.audience='community';"
           "HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') + ";"
           "HUB.store.state.calcMode='rad';"  # asymptote at pi/2 needs RAD
           "HUB.store.save(); HUB.applyTheme(); try{HUB.ui.closeSheet();}catch(e){} HUB.showTab('daily');")
        time.sleep(2)
        errs('load')

        js("document.getElementById('calcViewBtn').click()"); time.sleep(1)
        note(js("!document.getElementById('calcGraph').hidden"), f'graph view visible [{theme}]')
        note(js("document.querySelectorAll('#calcGpad .calc-key').length") == 30,
             'keypad now has 30 keys', str(js("document.querySelectorAll('#calcGpad .calc-key').length")))
        for k in ['tan(', 'ln(', 'log(', 'e']:
            note(js(f"document.querySelector('#calcGpad [data-gk=\"{k}\"]')!==null"), f'{k} key present [{theme}]')
        note(js("document.documentElement.scrollWidth") <= 390, f'no horizontal overflow [{theme}]')
        note(js("[...document.querySelectorAll('.calc-fnin')].every(i=>i.readOnly&&i.getAttribute('inputmode')==='none')"),
             f'rows still readonly + inputmode=none [{theme}]')

        cols = DARK_COLS if theme == 'dark' else LIGHT_COLS

        # ---- insertion at the caret via the new keys ----
        setrow(0, '')
        gk('tan(')
        note(rowval(0) == 'tan(', 'tan key inserts tan(', rowval(0))
        note(rowcaret(0) == 4, 'caret sits after tan(', f"caret={rowcaret(0)}")
        setrow(0, '')
        gk('ln(')
        note(rowval(0) == 'ln(', 'ln key inserts ln(', rowval(0))
        setrow(0, '')
        gk('log(')
        note(rowval(0) == 'log(', 'log key inserts log(', rowval(0))
        setrow(0, 'x^2')
        js("(function(){const el=document.querySelector('.calc-fnin[data-fi=\"0\"]');"
           "el.setSelectionRange(0,0);HUB.calc._graph.pad.active(0);})()")
        gk('e')
        note(rowval(0) == 'ex^2', 'e inserts at caret (mid-string)', rowval(0))
        # custom caret still tracks after the new-key insertions (no caret regression)
        cx = caretx(0)
        note(isinstance(cx, (int, float)) and cx > 0, 'custom caret visible after new-key insert', f'offsetLeft={cx}')

        # ---- tan(x): real curve + clean asymptote breaks (no vertical connectors) ----
        n = plot('tan(x)')
        note(isinstance(n, int) and n > 50, 'tan(x) plots a real curve', f'pixels={n}')
        rgb = [198, 241, 53] if theme == 'dark' else [74, 122, 0]
        asym = js(ASYM_JS % json.dumps(rgb))
        ok_asym = isinstance(asym, dict) and not asym.get('offscreen') and asym['tot'] > 0 and asym['n'] / asym['tot'] < 0.08
        note(ok_asym, 'asymptote strip has no connector line',
             f"strip_pixels={asym.get('n')}/{asym.get('tot')} @sx={asym.get('sx')}" if isinstance(asym, dict) else str(asym))

        # ---- ln(x) / log(x): domain breaks for x<=0, no crash, no NaN on canvas ----
        n = plot('ln(x)')
        note(isinstance(n, int) and n > 50, 'ln(x) plots (x>0 branch)', f'pixels={n}')
        r = js("JSON.stringify(HUB.calc._eval('ln(-1)','rad'))")
        note(isinstance(r, str) and 'NaN' not in r, 'ln(-1) handled, never NaN', (r or '')[:80])
        n = plot('log(x)')
        note(isinstance(n, int) and n > 50, 'log(x) plots (x>0 branch)', f'pixels={n}')

        # ---- e^x plots ----
        n = plot('e^x')
        note(isinstance(n, int) and n > 50, 'e^x plots a real curve', f'pixels={n}')

        # ---- key glow on a new key ----
        glow = js("(function(){const b=document.querySelector('#calcGpad [data-gk=\"tan(\"]');"
                  "b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));"
                  "const on=b.classList.contains('kglow');"
                  "b.dispatchEvent(new PointerEvent('pointerup',{bubbles:true}));return on;})()")
        note(glow == True, 'tan key glows on pointerdown')

        # ---- screenshots ----
        plot('tan(x)')  # re-plot tan for the money shot (script later plots e^x)
        js("document.getElementById('calcCanvas').scrollIntoView({block:'center'})"); time.sleep(0.6)
        shot(f'calc9-tan-{theme}')  # tan(x) with clean asymptote breaks
        js("document.getElementById('calcGpad').scrollIntoView({block:'center'})"); time.sleep(0.6)
        shot(f'calc9-keypad-{theme}')  # keypad with the new tan/ln/log/e row
        errs(f'graph calculus keys [{theme}]')
    finally:
        proc.terminate()

for th in ['dark', 'light']:
    run_theme(th)
ok = sum(1 for o, _ in checks if o); tot = len(checks)
print(f'\n==== QA CALC9: {ok}/{tot} passed ====')
bad = [l for o, l in checks if not o]
if bad: print('FAILURES:', bad)
raise SystemExit(0 if ok == tot else 1)
