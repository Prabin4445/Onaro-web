#!/usr/bin/env python3
"""Calculator QA round 7: graph in-app keypad.
Readonly function rows (no iOS keyboard) + 5-col keypad below graph.
Fresh profiles, 390x844, dark+light, zero console errors."""
import json, subprocess, time, urllib.request, os, base64, shutil

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9481
PROF = '/tmp/hubqa-calc7'
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
        def gk(label):
            # click a graph-keypad key by its data-gk insertion string
            return js(f"document.querySelector('#calcGpad [data-gk=\"{label}\"]').click(),'clicked'")

        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
           "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        js("var p=HUB.store.state.profile; p.name='PraBin'; p.campus='Downtown'; p.audience='community';"
           "HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') + ";"
           "HUB.store.save(); HUB.applyTheme(); try{HUB.ui.closeSheet();}catch(e){} HUB.showTab('daily');")
        time.sleep(2)
        errs('load')

        # enter graph view
        js("document.getElementById('calcViewBtn').click()"); time.sleep(1)
        note(js("!document.getElementById('calcGraph').hidden"), f'graph view visible [{theme}]')
        note(js("document.querySelectorAll('#calcGpad .calc-key').length") == 30, 'keypad has 30 keys (26 + tan/ln/log/e)')
        note(js("document.querySelector('#calcGpad [data-gk=\"DEL\"]')!==null"), 'DEL key present')
        note(js("document.querySelector('.calc-qchips')===null"), 'old quick chips removed')
        # rows are readonly: no iOS keyboard can summon
        note(js("[...document.querySelectorAll('.calc-fnin')].every(i=>i.readOnly&&i.getAttribute('inputmode')==='none')"),
             'rows readonly + inputmode=none (no iOS keyboard)')
        # default active row = first
        note(js("document.querySelector('.calc-fnrow.act').dataset.fi") == '0', 'row 1 active by default')
        note(js("document.documentElement.scrollWidth") <= 390, 'no horizontal overflow')

        cols = DARK_COLS if theme == 'dark' else LIGHT_COLS
        n0 = js(CURVE_JS % cols)
        note(isinstance(n0, int) and n0 > 50, 'default funcs render curves', f'pixels={n0}')

        # ---- tap row 2 -> becomes active; type 2 x + 3 via keypad ----
        # headless .click() leaves caret at 0; place it at end like a real tap-at-end
        js("(function(){const el=document.querySelector('.calc-fnin[data-fi=\"1\"]');el.click();"
           "el.setSelectionRange(el.value.length,el.value.length);})()"); time.sleep(0.4)
        note(js("document.querySelector('.calc-fnrow.act').dataset.fi") == '1', 'tap row 2 -> active')
        note(js("document.querySelector('.calc-fnrow[data-fi=\"0\"]').classList.contains('act')") == False,
             'row 1 ring cleared')
        # clear row 2 first (default x^2), then type
        for _ in range(3): gk('DEL')
        for k in ['2', '×', 'x', '+', '3']: gk(k)
        note(js("document.querySelector('.calc-fnin[data-fi=\"1\"]').value") == '2×x+3',
             'keypad typed 2×x+3 into row 2')
        time.sleep(0.9)  # debounce 220ms + render
        n1 = js(CURVE_JS % cols)
        note(isinstance(n1, int) and n1 > 50, 'canvas re-rendered with typed function', f'pixels={n1}')
        js("document.getElementById('calcRoot').scrollIntoView({block:'start'})"); time.sleep(0.6)
        shot(f'graph-keypad-{theme}')  # money shot: custom typed function plotted

        # ---- DEL removes one char ----
        gk('DEL')
        note(js("document.querySelector('.calc-fnin[data-fi=\"1\"]').value") == '2×x+',
             'DEL removes last char')

        # ---- switch active row; typing goes to the new row ----
        js("(function(){const el=document.querySelector('.calc-fnin[data-fi=\"0\"]');el.click();"
           "el.setSelectionRange(el.value.length,el.value.length);})()"); time.sleep(0.4)
        note(js("document.querySelector('.calc-fnrow.act').dataset.fi") == '0', 'switch active back to row 1')
        gk('5')
        v0 = js("document.querySelector('.calc-fnin[data-fi=\"0\"]').value")
        note(v0 == 'sin(x)5', 'typing goes to active row', v0)
        v1 = js("document.querySelector('.calc-fnin[data-fi=\"1\"]').value")
        note(v1 == '2×x+', 'inactive row untouched', v1)

        # ---- key glow on finger-down ----
        glow = js("(function(){const b=document.querySelector('#calcGpad [data-gk=\"7\"]');"
                  "b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));"
                  "const on=b.classList.contains('kglow');"
                  "b.dispatchEvent(new PointerEvent('pointerup',{bubbles:true}));return on;})()")
        note(glow == True, 'keypad key glows on pointerdown')

        # ---- + adds a row and makes it active ----
        js("document.getElementById('calcFnAdd').click()"); time.sleep(0.5)
        note(js("document.querySelectorAll('.calc-fnrow').length") == 3, 'add row -> 3 rows')
        note(js("document.querySelector('.calc-fnrow.act').dataset.fi") == '2', 'new row becomes active')
        note(js("document.activeElement && document.activeElement.dataset.fi") == '2', 'new row input focused')
        gk('x'); gk('^'); gk('3')
        note(js("document.querySelector('.calc-fnin[data-fi=\"2\"]').value") == 'x^3',
             'typing into new active row works')

        # ---- invalid input: friendly inline error, never NaN ----
        js("HUB.calc._graph.pad.active(2)"); gk('(')
        time.sleep(0.9)
        errtxt = js("document.querySelector('[data-fe=\"2\"]').textContent")
        note(isinstance(errtxt, str) and len(errtxt) > 0, 'invalid input shows friendly error', errtxt)
        errs('graph keypad')
    finally:
        proc.terminate()

for th in ['dark', 'light']:
    run_theme(th, th)
ok = sum(1 for o, _ in checks if o); tot = len(checks)
print(f'\n==== QA CALC7: {ok}/{tot} passed ====')
bad = [l for o, l in checks if not o]
if bad: print('FAILURES:', bad)
raise SystemExit(0 if ok == tot else 1)
