#!/usr/bin/env python3
"""QA: GPA swipe iOS hardening — tray fully hidden on tap/closed rows, opens
only after a real horizontal swipe (>=24px, horizontal-dominant); explicit
tray/button dimensions; no iOS text selection. Mobile emulation 390x844,
touch enabled, iPhone UA. Fresh profiles, zero console errors, dark + light."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9524
BASE = 'file:///home/hatch/workspace/hub/index.html'
IPHONE_UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
             'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 '
             'Mobile/15E148 Safari/604.1')
checks = []
def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, detail)
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

def hook(c):
    c.send('Runtime.enable'); c.send('Page.enable')
    c.send('Emulation.setDeviceMetricsOverride', {
        'width': 390, 'height': 844, 'deviceScaleFactor': 3,
        'mobile': True, 'hasTouch': True})
    c.send('Emulation.setUserAgentOverride', {'userAgent': IPHONE_UA})
    c.send('Runtime.evaluate', {'expression':
        "window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
        "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))"})

# state reader for row 0 (after a swipe, without dispatching new events)
GESTURE_STATE_JS = """(()=>{
var row=document.querySelectorAll('#gpaCard [data-gswipe]')[0]; if(!row) return 'no-row';
var inner=row.querySelector('.gpa-inner'), tray=row.querySelector('.gpa-swactions');
var cs=getComputedStyle(tray);
return JSON.stringify({cls:row.className, tx:inner.style.transform||'(none)',
  vis:cs.visibility, op:cs.opacity, pe:cs.pointerEvents,
  trayW:Math.round(tray.getBoundingClientRect().width),
  btnW:Math.round(tray.querySelector('.gsw-edit').getBoundingClientRect().width)});
})()"""

# pointer gestures on row index idx: 'tap' | 'micromove' (10px) | 'swipe' (150px left)
GESTURE_JS = """((kind,idx)=>{
var rows=document.querySelectorAll('#gpaCard [data-gswipe]');
var row=rows[idx||0]; if(!row) return 'no-row';
var r=row.getBoundingClientRect(), cx=r.left+r.width*0.6, cy=r.top+r.height/2;
function pe(type,x){row.dispatchEvent(new PointerEvent(type,{bubbles:true,cancelable:true,clientX:x,clientY:cy,pointerId:7,isPrimary:true,pointerType:'touch'}));}
pe('pointerdown',cx);
if(kind==='swipe'){pe('pointermove',cx-30);pe('pointermove',cx-90);pe('pointermove',cx-150);}
else if(kind==='micromove'){pe('pointermove',cx-10);}
pe('pointerup',kind==='swipe'?cx-150:(kind==='micromove'?cx-10:cx));
if(kind==='tap'||kind==='micromove'){row.querySelector('.gpa-inner').dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));}
var inner=row.querySelector('.gpa-inner'), tray=row.querySelector('.gpa-swactions');
var cs=getComputedStyle(tray);
return JSON.stringify({cls:row.className, tx:inner.style.transform||'(none)',
  vis:cs.visibility, op:cs.opacity, pe:cs.pointerEvents,
  trayW:Math.round(tray.getBoundingClientRect().width),
  btnW:Math.round(tray.querySelector('.gsw-edit').getBoundingClientRect().width)});
})"""

def run(theme):
    shutil.rmtree(f'/tmp/hubqa-gpa4-{theme}', ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=390,844',
        f'--user-data-dir=/tmp/hubqa-gpa4-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as r:
                    ts = json.load(r)
                tgt = next(x for x in ts if x['type'] == 'page' and 'devtools' not in x['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        hook(c)
        def js(expr):
            r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
            return (r or {}).get('result', {}).get('value')
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name), 'wb').write(base64.b64decode(r['data']))
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'{theme}: {label} zero errors', json.dumps(v)[:200] if v else '')
        def clearToasts():
            js("var h=document.getElementById('toastHost');if(h)h.innerHTML=''")
        def add_course(subj, cr, grade):
            js("document.querySelector('[data-gpa-add]').click()"); time.sleep(0.5)
            js(f"document.querySelector('[data-ggrade=\"{grade}\"]').click()")
            js(f"document.getElementById('gpaSubj').value='{subj}';document.getElementById('gpaCr').value='{cr}';"
               "document.getElementById('gpaSave').click()"); time.sleep(1.0)
        def gesture(kind, idx=0):
            return json.loads(js(f"({GESTURE_JS})('{kind}',{idx})"))

        time.sleep(4)
        errs('boot')
        js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.showTab('home');")
        time.sleep(1)

        # seed 2 courses
        add_course('Math 201', '3', 'A')
        add_course('English', '4', 'B')
        note(js("document.querySelector('#gpaCard .gpa-num').textContent") == '3.43', f'{theme}: seeded GPA 3.43')
        errs('seed')

        js("document.getElementById('gpaCard').scrollIntoView({block:'center'})"); time.sleep(0.5)

        # --- closed rows: tray fully hidden on ALL rows ---
        st = js("""JSON.stringify(Array.from(document.querySelectorAll('#gpaCard .gpa-swactions')).map(function(t){
          var cs=getComputedStyle(t); return cs.visibility+'/'+cs.opacity+'/'+cs.pointerEvents;}))""")
        note(json.loads(st) == ['hidden/0/none', 'hidden/0/none'], f'{theme}: both closed trays hidden+opaque-0+no-events', st)
        note('gpa-live' not in str(js("document.getElementById('gpaCard').innerHTML")), f'{theme}: no gpa-live class anywhere')

        # --- plain tap: must NOT reveal the tray (PraBin's "on click it shows edit and delete") ---
        g = gesture('tap')
        time.sleep(0.5)
        vis = js("getComputedStyle(document.querySelectorAll('#gpaCard .gpa-swactions')[0]).visibility")
        note(vis == 'hidden' and 'gpa-open' not in g['cls'] and 'gpa-drag' not in g['cls'],
             f'{theme}: plain tap never opens tray', f"vis={vis} cls={g['cls']}")

        # --- 10px micro-move tap: must NOT arm a swipe ---
        g = gesture('micromove'); time.sleep(0.5)
        vis = js("getComputedStyle(document.querySelectorAll('#gpaCard .gpa-swactions')[0]).visibility")
        note(vis == 'hidden' and 'gpa-open' not in g['cls'],
             f'{theme}: 10px micro-move tap never opens tray', f"vis={vis} cls={g['cls']}")
        errs('tap-guard')

        # --- real swipe: opens, exact geometry ---
        g = gesture('swipe')
        for _ in range(20):  # wait for the opacity transition to settle
            time.sleep(0.25)
            g = json.loads(js(GESTURE_STATE_JS))  # already an IIFE — no extra () wrapper
            if g['op'] == '1': break
        note('gpa-open' in g['cls'], f'{theme}: swipe adds gpa-open', g['cls'])
        note(g['tx'] == 'translateX(-148px)', f'{theme}: inner at -148px', g['tx'])
        note(g['vis'] == 'visible' and g['op'] == '1' and g['pe'] == 'auto',
             f'{theme}: open tray visible/opaque-1/events-auto', f"{g['vis']}/{g['op']}/{g['pe']}")
        note(g['trayW'] == 148, f'{theme}: tray exactly 148px wide', g['trayW'])
        note(g['btnW'] == 74, f'{theme}: Edit button exactly 74px wide (no iOS blow-up)', g['btnW'])
        # other row stays shut
        vis1 = js("getComputedStyle(document.querySelectorAll('#gpaCard .gpa-swactions')[1]).visibility")
        note(vis1 == 'hidden', f'{theme}: second row tray still hidden')
        shot(f'gpa4-open-{theme}.png')

        # --- tap open row body: snaps shut, tray hides ---
        g = gesture('tap'); time.sleep(0.6)
        vis = js("getComputedStyle(document.querySelectorAll('#gpaCard .gpa-swactions')[0]).visibility")
        note(vis == 'hidden' and 'gpa-open' not in g['cls'], f'{theme}: tap snaps open tray shut', f"vis={vis}")
        shot(f'gpa4-closed-{theme}.png')

        # --- swipe -> Edit prefilled -> change grade -> live GPA ---
        gesture('swipe'); time.sleep(0.4)
        js("document.querySelector('#gpaCard [data-gpa-edit]').click()"); time.sleep(0.7)
        note(js("document.getElementById('gpaSubj').value") == 'Math 201', f'{theme}: edit prefilled')
        js("document.querySelector('[data-ggrade=\"C\"]').click()"); time.sleep(0.3)
        js("document.getElementById('gpaSave').click()"); time.sleep(1.2)
        note(js("document.querySelector('#gpaCard .gpa-num').textContent") == '2.57', f'{theme}: edit recalc 2.57')
        errs('edit')

        # --- swipe -> Delete (confirm stubbed) ---
        js("window.confirm=function(){return true;}")
        n0 = js("document.querySelectorAll('#gpaCard [data-gswipe]').length")
        gesture('swipe'); time.sleep(0.4)
        js("document.querySelector('#gpaCard [data-gpa-del]').click()"); time.sleep(1.0)
        n1 = js("document.querySelectorAll('#gpaCard [data-gswipe]').length")
        note(n1 == n0 - 1, f'{theme}: delete removes row', f'{n0}->{n1}')
        note(js("document.querySelector('#gpaCard .gpa-num').textContent") == '3.00', f'{theme}: GPA 3.00 after delete')
        errs('delete')

        # --- iOS selection guards on rows ---
        us = js("getComputedStyle(document.querySelector('#gpaCard .gpa-inner')).webkitUserSelect")
        note(us == 'none', f'{theme}: row user-select none (no iOS text handles)', us)
        css = open(os.path.expanduser('~/workspace/hub/css/gpa.css')).read()
        note('-webkit-touch-callout:none' in css.replace(' ', ''),
             f'{theme}: -webkit-touch-callout:none in CSS (no iOS long-press loupe; iOS-only prop, not in Blink computed style)')

        # --- ⋯ fallback still works ---
        js("document.querySelector('#gpaCard .gpa-more').click()"); time.sleep(0.6)
        note(js("!!document.getElementById('gmEdit') && !!document.getElementById('gmDel')"), f'{theme}: ⋯ fallback sheet')
        js("HUB.ui.closeSheet()"); time.sleep(0.4)
        clearToasts()
        errs('final')
    finally:
        proc.terminate()

for th in ['dark', 'light']:
    run(th)
ok = sum(1 for o, _ in checks if o); tot = len(checks)
print(f'\n==== {ok}/{tot} passed ====')
bad = [l for o, l in checks if not o]
if bad: print('FAILURES:', bad)
