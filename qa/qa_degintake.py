#!/usr/bin/env python3
"""QA: degree plan start-intake selector (js/degree.js + css/degree.css).

- Selector exists: Fall/Spring/Summer + year stepper, defaults Fall + current year.
- Semester labels rotate from intake with correct years (Fall / Spring / Summer starts).
- Changing intake mid-progress keeps completed courses; persists across reload.
- 390px dark en + 320px light en + 390px dark ne; zero console errors; screenshots.
"""
import json, subprocess, time, urllib.request, os, sys, base64, shutil, re
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
os.makedirs(QA, exist_ok=True)
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
SLUG = 'dallas-college-aa-business'  # 4 semesters
fails = []

def check(n, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + n + ((' | ' + str(extra)) if extra else ''))
    if not ok: fails.append(n)

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl); self.id = 0
    def send(self, method, params=None, wait=True):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        if not wait: return None
        deadline = time.time() + 25
        while time.time() < deadline:
            msg = json.loads(self.ws.recv())
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)
    def close(self):
        try: self.ws.close()
        except Exception: pass

def port_open(port):
    import socket
    s = socket.socket(); s.settimeout(1)
    try: s.connect(('localhost', port)); return True
    except OSError: return False

HOOKS = ("window.__degerr=[];"
         "window.__gateSkip=true;"
         "window.addEventListener('error',function(e){window.__degerr.push('ERR:'+(e.message||e.error));});"
         "window.addEventListener('unhandledrejection',function(e){window.__degerr.push('REJ:'+((e.reason&&e.reason.message)||e.reason));});")

def launch(name, w, h, dark=True, lang='en', rose=False):
    port = 9360 + (abs(hash(name)) % 300)
    prof = '/tmp/hubqa-degintake-' + re.sub(r'[^a-z0-9]+', '-', name)
    shutil.rmtree(prof, ignore_errors=True)
    proc = subprocess.Popen(
        [CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
         f'--remote-debugging-port={port}', '--remote-allow-origins=*',
         '--hide-scrollbars', '--allow-file-access-from-files',
         f'--user-data-dir={prof}', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while time.time() - t0 < 20:
        if port_open(port): break
        time.sleep(0.4)
    with urllib.request.urlopen(f'http://localhost:{port}/json/list') as r:
        tgt = [t for t in json.load(r) if t['type'] == 'page' and 'devtools' not in t['url']][0]
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source': HOOKS +
        "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'%s',country:'US'}));}catch(e){}" % lang})
    c.send('Runtime.enable'); c.send('Page.enable')
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': w, 'height': h, 'deviceScaleFactor': 2, 'mobile': True})
    c.send('Page.navigate', {'url': BASE})
    return proc, c

def js(c, expr):
    r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True}, wait=True)
    res = (r or {}).get('result', {})
    return res.get('value')

def wait_js(c, expr, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if js(c, expr): return True
        time.sleep(0.4)
    return False

def boot(c, rose=False):
    wait_js(c, "document.readyState==='complete'", 25)
    wait_js(c, "!document.getElementById('splash')", 20)
    js(c, """(()=>{try{const p=HUB.store.state.profile;p.name='QA Tester';
        p.campus='QA Campus';HUB.store.save();}catch(e){}
        try{HUB.ui.closeSheet();}catch(e){}
        const w=document.getElementById('wlcmHost');if(w)w.remove();
        try{HUB.showTab('home');}catch(e){}return 'seeded'})()""")
    time.sleep(1.0)
    if rose:
        js(c, """(()=>{HUB.store.state.profile.gender='female';HUB.store.save();
            HUB.theme.apply(false);return 1})()""")
        time.sleep(0.6)

def errs(c):
    return js(c, "window.__degerr.splice(0)") or []

def labels(c):
    return js(c, """Array.from(document.querySelectorAll('.deg-sem .t')).map(e=>e.textContent.trim())""") or []

def shot(c, tag):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, 'degintake-%s.png' % tag), 'wb').write(base64.b64decode(r['data']))

def open_plan(c):
    js(c, "HUB.degree.open(%s)" % json.dumps(SLUG))
    return wait_js(c, "!!document.querySelector('.deg-intake')", 20)

# ================= 390px dark en =================
proc, c = launch('intake-390-dark', 390, 844, dark=True, lang='en')
boot(c)
check('plan opens with intake selector', open_plan(c))
Y = 2026  # will be read live below
Y = js(c, "new Date().getFullYear()")
check('selector: 3 term buttons + year stepper',
      js(c, "document.querySelectorAll('[data-intake-term]').length===3 && !!document.querySelector('[data-intake-yr=\"1\"]')") is True)
check('default: Fall selected', js(c, "document.querySelector('[data-intake-term=\"fall\"]').classList.contains('on')") is True)
check('default year = current year', js(c, "document.querySelector('.deg-yrval').textContent.trim()") == str(Y), Y)
check('label says "I started in"', 'I started in' in (js(c, "document.querySelector('.deg-intake-lab').textContent") or ''))
lb = labels(c)
check('fall rotation labels', lb == ['Fall %d' % Y, 'Spring %d' % (Y+1), 'Fall %d' % (Y+1), 'Spring %d' % (Y+2)], lb)
shot(c, '390-fall')

# spring
js(c, "document.querySelector('[data-intake-term=\"spring\"]').click()")
time.sleep(0.6)
lb = labels(c)
check('spring rotation labels', lb == ['Spring %d' % Y, 'Fall %d' % Y, 'Spring %d' % (Y+1), 'Fall %d' % (Y+1)], lb)
shot(c, '390-spring')

# year +1
js(c, "document.querySelector('[data-intake-yr=\"1\"]').click()")
time.sleep(0.6)
lb = labels(c)
check('year stepper shifts years', lb[0] == 'Spring %d' % (Y+1) and lb[2] == 'Spring %d' % (Y+2), lb)
js(c, "document.querySelector('[data-intake-yr=\"-1\"]').click()")
time.sleep(0.6)

# summer
js(c, "document.querySelector('[data-intake-term=\"summer\"]').click()")
time.sleep(0.6)
lb = labels(c)
check('summer rotation labels', lb == ['Summer %d' % Y, 'Fall %d' % Y, 'Spring %d' % (Y+1), 'Fall %d' % (Y+1)], lb)
shot(c, '390-summer')

# complete a course, then change intake -> progress must survive
slot = js(c, "document.querySelector('.deg-tile').dataset.slot")
js(c, "document.querySelector('[data-check]').click()")
time.sleep(0.8)
done1 = js(c, "document.querySelector('.deg-tile.done')!==null")
js(c, "document.querySelector('[data-intake-term=\"fall\"]').click()")
time.sleep(0.6)
done2 = js(c, "document.querySelector('.deg-tile.done')!==null")
same = js(c, "(()=>{const t2=document.querySelector('.deg-tile.done');return t2&&t2.dataset.slot===%s})()" % json.dumps(slot))
check('course completed', done1 is True)
check('progress survives intake change', done2 is True and same is True, slot)
lb = labels(c)
check('labels re-rotated after change', lb[0] == 'Fall %d' % Y, lb)

# persistence across reload
c.send('Page.reload')
wait_js(c, "document.readyState==='complete'", 25)
wait_js(c, "!document.getElementById('splash')", 20)
time.sleep(0.8)
js(c, "HUB.degree.open(%s)" % json.dumps(SLUG))
ok = wait_js(c, "!!document.querySelector('.deg-intake')", 20)
time.sleep(0.5)
check('intake persists across reload (fall kept)',
      ok and js(c, "document.querySelector('[data-intake-term=\"fall\"]').classList.contains('on')") is True)
check('progress persists across reload',
      js(c, "document.querySelector('.deg-tile.done')!==null") is True)
e = errs(c); check('390 dark en: zero console errors', not e, e[:3])
proc.terminate()

# ================= 320px light en =================
proc, c = launch('intake-320-light', 320, 568, dark=False, lang='en')
boot(c)
check('320: plan opens with selector', open_plan(c))
time.sleep(0.5)
over = js(c, "document.documentElement.scrollWidth<=320")
check('320: no page overflow', over is True, js(c, "document.documentElement.scrollWidth"))
js(c, "document.querySelector('[data-intake-term=\"spring\"]').click()")
time.sleep(0.6)
Y = js(c, "new Date().getFullYear()")
lb = labels(c)
check('320: spring rotation', lb == ['Spring %d' % Y, 'Fall %d' % Y, 'Spring %d' % (Y+1), 'Fall %d' % (Y+1)], lb)
shot(c, '320-spring')
e = errs(c); check('320 light en: zero console errors', not e, e[:3])
proc.terminate()

# ================= 390px dark ne =================
proc, c = launch('intake-390-ne', 390, 844, dark=True, lang='ne')
boot(c)
check('ne: plan opens with selector', open_plan(c))
time.sleep(0.5)
lab = js(c, "document.querySelector('.deg-intake-lab').textContent.trim()")
check('ne: intake label translated', lab == 'मैले सुरु गरेको', lab)
terms = js(c, "Array.from(document.querySelectorAll('[data-intake-term]')).map(b=>b.textContent.trim())")
check('ne: term buttons translated', terms == ['शरद', 'वसन्त', 'ग्रीष्म'], terms)
js(c, "document.querySelector('[data-intake-term=\"summer\"]').click()")
time.sleep(0.6)
Y = js(c, "new Date().getFullYear()")
lb = labels(c)
check('ne: summer rotation w/ translated summer', lb[0] == 'ग्रीष्म %d' % Y, lb)
shot(c, '390-ne-summer')
e = errs(c); check('390 dark ne: zero console errors', not e, e[:3])
proc.terminate()

print('fails=%d' % len(fails))
sys.exit(1 if fails else 0)
