#!/usr/bin/env python3
"""Calculator QA round 8: graph keypad cursor keys (◀ ▶) + custom caret.

PraBin's iPhone bug: readonly function rows can't be touch-edited AND iOS
won't render a native caret in them, so he can't see where he is. The keypad
gains ◀ ▶ keys that move the caret in the ACTIVE row; keypad typing inserts
AT the caret and DEL deletes BEFORE it; a custom blinking volt caret bar
(.calc-fncaret) is drawn at the text caret via canvas measurement.
Fresh profiles, 390x844, dark+light, zero console errors.
"""
import json, subprocess, time, urllib.request, os, base64, shutil

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9484
PROF = '/tmp/hubqa-calc8'
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
LEFT = '\u25C0'; RIGHT = '\u25B6'

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
            # click a graph-keypad key by its data-gk insertion string
            return js(f"document.querySelector('#calcGpad [data-gk=\"{label}\"]').click(),'clicked'")
        def rowval(i): return js(f"document.querySelector('.calc-fnin[data-fi=\"{i}\"]').value")
        def rowcaret(i): return js(f"document.querySelector('.calc-fnin[data-fi=\"{i}\"]').selectionStart")
        def setrow(i, v):
            # set a row's text directly, caret at end, make it active (headless helper)
            return js(f"(function(){{const el=document.querySelector('.calc-fnin[data-fi=\"{i}\"]');"
                       f"el.value={json.dumps(v)};el.setSelectionRange(el.value.length,el.value.length);"
                       f"HUB.calc._graph.pad.active({i});return el.value;}})()")
        def caretx(i):
            # offsetLeft of the custom caret bar in row i, or -1 if hidden
            return js("(function(){const cd=document.querySelector('.calc-fncaret[data-fc=\"" + str(i) + "\"]');"
                      "if(!cd||cd.hidden||!cd.offsetWidth)return -1;return cd.offsetLeft;})()")

        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
           "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        js("var p=HUB.store.state.profile; p.name='PraBin'; p.campus='Downtown'; p.audience='community';"
           "HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') + ";"
           "HUB.store.save(); HUB.applyTheme(); try{HUB.ui.closeSheet();}catch(e){} HUB.showTab('daily');")
        time.sleep(2)
        errs('load')

        js("document.getElementById('calcViewBtn').click()"); time.sleep(1)
        note(js("!document.getElementById('calcGraph').hidden"), f'graph view visible [{theme}]')
        note(js("document.querySelectorAll('#calcGpad .calc-key').length") == 30, 'keypad has 30 keys')
        note(js(f"document.querySelector('#calcGpad [data-gk=\"{LEFT}\"]')!==null"), '◀ key present')
        note(js(f"document.querySelector('#calcGpad [data-gk=\"{RIGHT}\"]')!==null"), '▶ key present')
        note(js("document.documentElement.scrollWidth") <= 390, 'no horizontal overflow')
        note(js("[...document.querySelectorAll('.calc-fnin')].every(i=>i.readOnly&&i.getAttribute('inputmode')==='none')"),
             'rows still readonly + inputmode=none (no iOS keyboard)')

        cols = DARK_COLS if theme == 'dark' else LIGHT_COLS

        # ---- custom caret: visible on the active row, hidden elsewhere ----
        setrow(0, 'sin(x)')
        cx0 = caretx(0)
        row0 = js("(function(){const r=document.querySelector('.calc-fnrow[data-fi=\"0\"]');"
                  "return {l:r.getBoundingClientRect().left,w:r.getBoundingClientRect().width};})()")
        note(isinstance(cx0, (int, float)) and cx0 > 10 and cx0 < row0['w'] - 5,
             'custom caret visible inside active row', f'offsetLeft={cx0}')
        note(caretx(1) == -1, 'inactive row caret hidden')
        # caret color is volt
        cc = js("(function(){const cd=document.querySelector('.calc-fncaret[data-fc=\"0\"]');"
                "return getComputedStyle(cd).backgroundColor;})()")
        note(cc in ('rgb(198, 241, 53)', 'rgb(212, 245, 63)'), 'caret bar is volt', cc)

        # ---- ◀ moves caret left AND the bar follows ----
        gk(LEFT); gk(LEFT); gk(LEFT)   # caret 6 -> 3
        note(rowcaret(0) == 3, '◀◀◀ moves caret left by 3', f"caret={rowcaret(0)}")
        cx1 = caretx(0)
        note(isinstance(cx1, (int, float)) and cx1 > 0 and cx1 < cx0,
             'caret bar shifted left', f'{cx0} -> {cx1}')

        # ---- typing inserts AT the caret (caret 3 = between 'n' and '(') ----
        gk('2')
        note(rowval(0) == 'sin2(x)', 'keypad inserts AT the caret', rowval(0))

        # ---- DEL removes the char BEFORE the caret ----
        gk('DEL')
        note(rowval(0) == 'sin(x)', 'DEL removes char before caret', rowval(0))
        note(rowcaret(0) == 3, 'caret lands after deleted char', f"caret={rowcaret(0)}")

        # ---- ▶ at end is a no-op; ◀ at 0 is a no-op ----
        js("(function(){const el=document.querySelector('.calc-fnin[data-fi=\"0\"]');"
           "el.setSelectionRange(el.value.length,el.value.length);HUB.calc._graph.pad.active(0);})()")
        gk(RIGHT)
        note(rowcaret(0) == 6, '▶ at end is a no-op', f"caret={rowcaret(0)}")
        js("(function(){const el=document.querySelector('.calc-fnin[data-fi=\"0\"]');el.setSelectionRange(0,0);})()")
        gk(LEFT)
        note(rowcaret(0) == 0, '◀ at start is a no-op', f"caret={rowcaret(0)}")

        # ---- arrows + caret follow the ACTIVE row ----
        js("(function(){const el=document.querySelector('.calc-fnin[data-fi=\"1\"]');el.click();"
           "el.setSelectionRange(2,2);})()"); time.sleep(0.4)
        note(js("document.querySelector('.calc-fnrow.act').dataset.fi") == '1', 'tap row 2 -> active')
        gk(LEFT)
        note(rowcaret(1) == 1, '◀ affects active row 2', f"caret={rowcaret(1)}")
        note(rowcaret(0) == 0, 'row 1 caret untouched', f"caret={rowcaret(0)}")
        note(caretx(0) == -1, 'row 1 caret bar hidden after switch')
        cx2 = caretx(1)
        note(isinstance(cx2, (int, float)) and cx2 > 0, 'row 2 caret bar visible', f'offsetLeft={cx2}')
        gk('9')
        note(rowval(1) == 'x9^2', 'insert at row-2 caret', rowval(1))

        # ---- key glow on an arrow key ----
        glow = js(f"(function(){{const b=document.querySelector('#calcGpad [data-gk=\"{LEFT}\"]');"
                  "b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));"
                  "const on=b.classList.contains('kglow');"
                  "b.dispatchEvent(new PointerEvent('pointerup',{bubbles:true}));return on;})()")
        note(glow == True, '◀ glows on pointerdown')

        # ---- repair job: 'x)sin((' -> 'sin(x)' via ◀/▶ + DEL + typing ----
        # (place caret at end first: DEL at caret 0 is correctly a no-op)
        js("HUB.calc._graph.pad.active(0);"
           "(function(){const el=document.querySelector('.calc-fnin[data-fi=\"0\"]');"
           "el.setSelectionRange(el.value.length,el.value.length);})()")
        for _ in range(6): gk('DEL')     # clear row (was 'sin(x)')
        for k in ['x', ')', 'sin(', '(']: gk(k)
        note(rowval(0) == 'x)sin((', 'typed invalid x)sin((', rowval(0))
        time.sleep(0.9)
        err0 = js("document.querySelector('[data-fe=\"0\"]').textContent")
        note(isinstance(err0, str) and len(err0) > 0, 'invalid shows friendly error', err0[:60])
        gk(LEFT)                          # caret 7 -> 6
        gk('DEL')                         # remove trailing '(' -> 'x)sin('
        note(rowval(0) == 'x)sin(', 'DEL removed trailing paren', rowval(0))
        for _ in range(3): gk(LEFT)       # caret 5 -> 2
        gk('DEL'); gk('DEL')              # remove ')' then 'x' -> 'sin('
        note(rowval(0) == 'sin(', 'DEL x2 removed leading x)', rowval(0))
        for _ in range(4): gk(RIGHT)      # caret 0 -> 4 (end)
        gk('x'); gk(')')
        note(rowval(0) == 'sin(x)', 'repaired to sin(x)', rowval(0))
        time.sleep(0.9)  # debounce + re-plot
        err1 = js("document.querySelector('[data-fe=\"0\"]').textContent")
        note(err1 == '', 'error clears after repair', repr(err1))
        n = js(CURVE_JS % cols)
        note(isinstance(n, int) and n > 50, 'repaired function plots', f'pixels={n}')

        anim = js("(function(){const cd=document.querySelector('.calc-fnrow.act .calc-fncaret');"
                  "return cd?getComputedStyle(cd).animationName:'';})()")
        note(anim == 'fnblink', 'caret bar blinks', anim)
        # freeze the blink so the money shot clearly shows the | bar
        js("document.querySelectorAll('.calc-fncaret').forEach(function(cd){cd.style.animation='none';})")
        time.sleep(0.2)
        js("document.getElementById('calcRoot').scrollIntoView({block:'start'})"); time.sleep(0.6)
        shot(f'graph-cursor-{theme}')  # money shot: volt | caret bar + keypad with ◀ ▶
        errs('graph cursor keys')
    finally:
        proc.terminate()

for th in ['dark', 'light']:
    run_theme(th)
ok = sum(1 for o, _ in checks if o); tot = len(checks)
print(f'\n==== QA CALC8: {ok}/{tot} passed ====')
bad = [l for o, l in checks if not o]
if bad: print('FAILURES:', bad)
raise SystemExit(0 if ok == tot else 1)
