#!/usr/bin/env python3
"""QA: GPA Edit-button tap fix — tapping Edit/Delete in an open swipe tray must
work (iOS Safari retargets the synthesized click if pointerup closes the tray
first, stripping pointer-events from the button). Regression: pointerup on a
tray button must NOT close the tray; elementFromPoint (iOS click proxy) must
still hit the button. Keeps all swipe-fix behavior. Mobile 390x844, touch,
iPhone UA. Fresh profiles, zero console errors, dark + light."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9525
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

GESTURE_STATE_JS = """(()=>{
var row=document.querySelectorAll('#gpaCard [data-gswipe]')[0]; if(!row) return 'no-row';
var inner=row.querySelector('.gpa-inner'), tray=row.querySelector('.gpa-swactions');
var cs=getComputedStyle(tray);
return JSON.stringify({cls:row.className, tx:inner.style.transform||'(none)',
  vis:cs.visibility, op:cs.opacity, pe:cs.pointerEvents});
})()"""

# pointer gestures on row index idx: 'tap' | 'swipe' (150px left)
GESTURE_JS = """((kind,idx)=>{
var rows=document.querySelectorAll('#gpaCard [data-gswipe]');
var row=rows[idx||0]; if(!row) return 'no-row';
var r=row.getBoundingClientRect(), cx=r.left+r.width*0.6, cy=r.top+r.height/2;
function pe(type,x){row.dispatchEvent(new PointerEvent(type,{bubbles:true,cancelable:true,clientX:x,clientY:cy,pointerId:7,isPrimary:true,pointerType:'touch'}));}
pe('pointerdown',cx);
if(kind==='swipe'){pe('pointermove',cx-30);pe('pointermove',cx-90);pe('pointermove',cx-150);}
pe('pointerup',kind==='swipe'?cx-150:cx);
if(kind==='tap'){row.querySelector('.gpa-inner').dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));}
var inner=row.querySelector('.gpa-inner'), tray=row.querySelector('.gpa-swactions');
var cs=getComputedStyle(tray);
return JSON.stringify({cls:row.className, tx:inner.style.transform||'(none)',
  vis:cs.visibility, op:cs.opacity, pe:cs.pointerEvents});
})"""

# tap a tray button (Edit/Delete) with pointer events targeted AT the button,
# exactly like a real iPhone tap: pointerdown+pointerup bubble to the row.
# Returns tray state + what elementFromPoint (iOS synthesized-click proxy) hits.
BTNTAP_JS = """((idx,sel)=>{
var row=document.querySelectorAll('#gpaCard [data-gswipe]')[idx||0]; if(!row) return 'no-row';
var b=row.querySelector(sel); if(!b) return 'no-btn';
var r=b.getBoundingClientRect(), cx=r.left+r.width/2, cy=r.top+r.height/2;
function pe(type,x){b.dispatchEvent(new PointerEvent(type,{bubbles:true,cancelable:true,clientX:x,clientY:cy,pointerId:9,isPrimary:true,pointerType:'touch'}));}
pe('pointerdown',cx); pe('pointerup',cx);
var tray=row.querySelector('.gpa-swactions'), cs=getComputedStyle(tray);
var hit=document.elementFromPoint(cx,cy);
return JSON.stringify({cls:row.className, vis:cs.visibility, op:cs.opacity, pe:cs.pointerEvents,
  hitEdit:!!(hit&&hit.closest&&hit.closest('[data-gpa-edit]')),
  hitDel:!!(hit&&hit.closest&&hit.closest('[data-gpa-del]')),
  hitTag:hit?String(hit.tagName).toLowerCase():'none'});
})"""

def run(theme):
    shutil.rmtree(f'/tmp/hubqa-gpa5-{theme}', ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=390,844',
        f'--user-data-dir=/tmp/hubqa-gpa5-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        def add_course(subj, cr, grade):
            js("document.querySelector('[data-gpa-add]').click()"); time.sleep(0.5)
            js(f"document.querySelector('[data-ggrade=\"{grade}\"]').click()")
            js(f"document.getElementById('gpaSubj').value='{subj}';document.getElementById('gpaCr').value='{cr}';"
               "document.getElementById('gpaSave').click()"); time.sleep(1.0)
        def gesture(kind, idx=0):
            return json.loads(js(f"({GESTURE_JS})('{kind}',{idx})"))
        def btntap(idx, sel):
            return json.loads(js(f"({BTNTAP_JS})({idx},'{sel}')"))

        time.sleep(4)
        errs('boot')
        js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.showTab('home');")
        time.sleep(1)

        add_course('Math 201', '3', 'A')
        add_course('English', '4', 'B')
        note(js("document.querySelector('#gpaCard .gpa-num').textContent") == '3.43', f'{theme}: seeded GPA 3.43')
        errs('seed')
        js("document.getElementById('gpaCard').scrollIntoView({block:'center'})"); time.sleep(0.5)

        # --- swipe opens tray (existing behavior) ---
        g = gesture('swipe')
        for _ in range(20):
            time.sleep(0.25)
            g = json.loads(js(GESTURE_STATE_JS))
            if g['op'] == '1': break
        note('gpa-open' in g['cls'] and g['pe'] == 'auto', f'{theme}: swipe opens tray', g['cls'])

        # --- REGRESSION: pointerup ON the Edit button must NOT close the tray ---
        t = btntap(0, '[data-gpa-edit]')
        note('gpa-open' in t['cls'], f'{theme}: button-tap pointerup keeps tray open', t['cls'])
        note(t['pe'] == 'auto' and t['vis'] == 'visible',
             f'{theme}: tray still hit-testable after button pointerup', f"{t['vis']}/{t['pe']}")
        # --- iOS proxy: WebKit hit-tests the synthesized click at dispatch time ---
        note(t['hitEdit'], f"{theme}: elementFromPoint still hits the Edit button (iOS click lands)", f"hit={t['hitTag']}")

        # --- tap Edit -> prefilled sheet opens ---
        js("document.querySelector('#gpaCard [data-gpa-edit]').click()"); time.sleep(0.7)
        subj = js("var el=document.getElementById('gpaSubj'); el?el.value:'NO-SHEET'")
        cr = js("var el=document.getElementById('gpaCr'); el?el.value:'?'")
        on = js("var b=document.querySelector('[data-ggrade].on'); b?b.dataset.ggrade:'?'")
        note(subj == 'Math 201', f'{theme}: edit sheet prefilled subject', subj)
        note(cr == '3', f'{theme}: edit sheet prefilled credits', cr)
        note(on == 'A', f'{theme}: edit sheet prefilled grade A', on)
        gg = js("var f=document.querySelector('.gpa-form'); f?f.className:'?'")
        note('gg-A' in gg, f'{theme}: grade-reactive sheet bg opens on A', gg)
        shot(f'gpa5-edit-{theme}.png')
        errs('edit-open')

        # --- change grade A->C -> save -> GPA recalcs live ---
        js("document.querySelector('[data-ggrade=\"C\"]').click()"); time.sleep(0.3)
        gg2 = js("var f=document.querySelector('.gpa-form'); f?f.className:'?'")
        note('gg-C' in gg2, f'{theme}: sheet bg reacts live to grade C', gg2)
        js("document.getElementById('gpaSave').click()"); time.sleep(1.2)
        note(js("document.querySelector('#gpaCard .gpa-num').textContent") == '2.57',
             f'{theme}: edit recalc GPA 2.57')
        errs('edit-save')

        # --- Delete: pointerup on button keeps tray open, click -> confirm -> removed ---
        js("window.confirm=function(){return true;}")
        n0 = js("document.querySelectorAll('#gpaCard [data-gswipe]').length")
        gesture('swipe', 0); time.sleep(0.5)
        t = btntap(0, '[data-gpa-del]')
        note('gpa-open' in t['cls'] and t['hitDel'], f'{theme}: delete-button tap keeps tray open + hittable')
        js("document.querySelector('#gpaCard [data-gpa-del]').click()"); time.sleep(1.2)
        n1 = js("document.querySelectorAll('#gpaCard [data-gswipe]').length")
        note(n1 == n0 - 1, f'{theme}: delete removes row', f'{n0}->{n1}')
        note(js("document.querySelector('#gpaCard .gpa-num').textContent") == '3.00',
             f'{theme}: GPA 3.00 after delete')
        errs('delete')

        # --- preserved: tap on open row body snaps shut ---
        gesture('swipe', 0); time.sleep(0.5)
        g = gesture('tap', 0); time.sleep(0.6)
        vis = js("getComputedStyle(document.querySelectorAll('#gpaCard .gpa-swactions')[0]).visibility")
        note(vis == 'hidden' and 'gpa-open' not in g['cls'], f'{theme}: tap on row body snaps tray shut')

        # --- preserved: plain tap on closed row never opens ---
        g = gesture('tap', 0); time.sleep(0.5)
        vis = js("getComputedStyle(document.querySelectorAll('#gpaCard .gpa-swactions')[0]).visibility")
        note(vis == 'hidden' and 'gpa-open' not in g['cls'], f'{theme}: plain tap never opens tray')

        # --- preserved: closed trays fully hidden ---
        st = js("""JSON.stringify(Array.from(document.querySelectorAll('#gpaCard .gpa-swactions')).map(function(x){
          var cs=getComputedStyle(x); return cs.visibility+'/'+cs.opacity+'/'+cs.pointerEvents;}))""")
        note(all(v == 'hidden/0/none' for v in json.loads(st)), f'{theme}: closed trays hidden/0/none', st)

        # --- preserved: ⋯ fallback ---
        js("document.querySelector('#gpaCard .gpa-more').click()"); time.sleep(0.6)
        note(js("!!document.getElementById('gmEdit') && !!document.getElementById('gmDel')"), f'{theme}: ⋯ fallback sheet')
        js("document.getElementById('gmEdit').click()"); time.sleep(0.7)
        note(js("document.getElementById('gpaSubj').value") == 'English', f'{theme}: ⋯ Edit opens prefilled')
        js("HUB.ui.closeSheet()"); time.sleep(0.4)
        shot(f'gpa5-open-{theme}.png')
        errs('final')
    finally:
        proc.terminate()

for th in ['dark', 'light']:
    run(th)
ok = sum(1 for o, _ in checks if o); tot = len(checks)
print(f'\n==== {ok}/{tot} passed ====')
bad = [l for o, l in checks if not o]
if bad: print('FAILURES:', bad)
