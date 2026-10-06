#!/usr/bin/env python3
"""QA: Student Scanner CamScanner rebuild (live camera + crop/adjust screen).
- Live viewfinder: overlay draws, shutter captures -> crop screen.
- Crop screen: 4 big handles (>=44px), dim-outside mask (no green tint), volt border.
- Filters: Color / Enhance / Grayscale / Black & White — each visibly changes the
  live preview; switching is synchronous (instant, no spinner).
- Page sizes: Auto / A4 / Letter / Legal change output aspect + dims label.
- Handle drag updates the quad; "Use this page" -> multi-page view.
- dark+light, 390px+320px, zero console errors, zero network requests.
- Saves per-filter screenshots for human visual verification.
"""
import json, subprocess, time, urllib.request, os, sys, base64, shutil, re
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
fails = []
net_urls = []
all_errs = []

def check(n, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + n + ((' | ' + str(extra)) if extra else ''), flush=True)
    if not ok: fails.append(n)

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl); self.id = 0; self.events = []
    def send(self, method, params=None, wait=True, timeout=90):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        if not wait: return None
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = json.loads(self.ws.recv())
            if msg.get('id') == self.id: return msg.get('result')
            self.events.append(msg)
        raise TimeoutError(method)
    def close(self):
        try: self.ws.close()
        except Exception: pass

def port_open(port):
    import socket
    s = socket.socket(); s.settimeout(1)
    try: s.connect(('localhost', port)); return True
    except OSError: return False

HOOKS = ("window.__scanerr=[];"
         "window.__gateSkip=true;"
         "window.addEventListener('error',function(e){window.__scanerr.push('ERR:'+(e.message||e.error));});"
         "window.addEventListener('unhandledrejection',function(e){window.__scanerr.push('REJ:'+((e.reason&&e.reason.message)||e.reason));});")

def launch(name, w, h, lang):
    port = 9510 + (abs(hash(name)) % 150)
    prof = '/tmp/hubqa-scancam-' + re.sub(r'[^a-z0-9]+', '-', name)
    # wait for a previous run's port to fully free
    t0 = time.time()
    while time.time() - t0 < 15:
        if not port_open(port): break
        time.sleep(0.5)
    shutil.rmtree(prof, ignore_errors=True)
    proc = subprocess.Popen(
        [CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
         '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
         f'--remote-debugging-port={port}', '--remote-allow-origins=*',
         '--hide-scrollbars', '--allow-file-access-from-files',
         f'--user-data-dir={prof}', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while time.time() - t0 < 20:
        if port_open(port): break
        time.sleep(0.4)
    # port can be open before targets are listed — poll for the page target
    tgt = None
    t0 = time.time()
    while time.time() - t0 < 20 and tgt is None:
        try:
            with urllib.request.urlopen(f'http://localhost:{port}/json/list', timeout=5) as r:
                pages = [t for t in json.load(r) if t['type'] == 'page' and 'devtools' not in t['url']]
                if pages: tgt = pages[0]
        except Exception:
            pass
        if tgt is None: time.sleep(0.5)
    if tgt is None:
        proc.terminate()
        raise RuntimeError('no page target on port %d' % port)
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source': HOOKS +
        "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'%s',country:'US'}));}catch(e){}" % lang})
    c.send('Runtime.enable'); c.send('Page.enable'); c.send('Network.enable')
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': w, 'height': h, 'deviceScaleFactor': 2, 'mobile': True})
    c.send('Page.navigate', {'url': BASE})
    return proc, c, prof

def js(c, expr, await_promise=False, timeout=90):
    r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True,
                                    'awaitPromise': await_promise}, wait=True, timeout=timeout)
    res = (r or {}).get('result', {})
    if res.get('subtype') == 'error':
        return {'__err': res.get('description')}
    if (r or {}).get('exceptionDetails'):
        return {'__err': json.dumps((r or {})['exceptionDetails'])[:300]}
    return res.get('value')

def wait_js(c, expr, timeout=25):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v = js(c, expr)
        if v: return v
        time.sleep(0.5)
    return None

def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    with open(os.path.join(QA, name), 'wb') as f:
        f.write(base64.b64decode(r['data']))

def drain_net(c):
    global net_urls
    for e in c.events:
        if e.get('method') == 'Network.requestWillBeSent':
            net_urls.append(e['params']['request']['url'])
    c.events = [e for e in c.events if e.get('method') != 'Network.requestWillBeSent']

def scan_errors(c):
    return js(c, 'window.__scanerr||[]') or []
MAKEDOC = """()=>{
const cv=document.createElement('canvas');cv.width=800;cv.height=1000;
const x=cv.getContext('2d');
x.fillStyle='#e8d9ae';x.fillRect(0,0,800,1000);
x.fillStyle='#c0392b';x.fillRect(90,46,200,44);
x.fillStyle='#2471a3';x.fillRect(310,46,200,44);
x.fillStyle='#1e8449';x.fillRect(530,46,180,44);
x.fillStyle='#2a2a2a';x.font='bold 30px sans-serif';x.fillText('Test Document',90,140);
for(let i=0;i<26;i++){x.fillRect(90,180+i*30,620-(i%7)*36,7);}
return cv;}"""

PREVSTATS = """(f)=>{
const pv=document.querySelector('[data-prev]');if(!pv)return null;
const d=pv.getContext('2d').getImageData(0,0,pv.width,pv.height).data;
const n=pv.width*pv.height;let eq=0,bw=0,cast=0,m=0;
for(let i=0;i<n;i+=7){const o=i*4;m++;
 if(d[o]===d[o+1]&&d[o+1]===d[o+2])eq++;
 if((d[o]===0||d[o]===255)&&d[o+1]===d[o]&&d[o+2]===d[o])bw++;
 cast+=Math.abs(d[o]-d[o+2]);}
return {w:pv.width,h:pv.height,eq:eq/m,bw:bw/m,cast:cast/m};}"""

def open_crop(c, quad_expr=None):
    """Drive the real cropView with the synthetic doc; returns True when ready."""
    q = quad_expr or "[{x:0,y:0},{x:800,y:0},{x:800,y:1000},{x:0,y:1000}]"
    r = js(c, """(function(){
try{
 HUB.scan.studio();
 const body=document.querySelector('.sc-body');
 const cv=(%s)();
 HUB.scan._t.scanCropView(body,cv,%s);
 return !!document.querySelector('.sc-adjust');
}catch(e){return 'ex:'+e.message;}})()""" % (MAKEDOC, q))
    return r is True

# ================================================================ run A: camera
print('=== run A: 390 dark en — live camera viewfinder ===', flush=True)
proc, c, prof = launch('a-390-dark', 390, 844, 'en')
try:
    wait_js(c, '!!(window.HUB&&HUB.scan&&HUB.scan._t)', 30)
    js(c, 'document.body.classList.add("dark")')
    wait_js(c, '!document.getElementById("splash")', 15)
    js(c, 'HUB.scan.tool("scan")')
    wait_js(c, '!!document.querySelector("[data-m=take]")', 15)
    # click "Take photo" -> live viewfinder (real user path)
    js(c, 'document.querySelector("[data-m=take]").click()')
    cam = wait_js(c, '!!(document.querySelector(".sc-camwrap")&&document.querySelector(".sc-camwrap video"))', 15)
    check('A viewfinder opened from Take photo', bool(cam))
    has_stream = wait_js(c, '(function(){const v=document.querySelector(".sc-camwrap video");return v&&v.videoWidth>0;})()', 20)
    check('A camera stream live (fake device)', bool(has_stream))
    ov = js(c, """(function(){const ov=document.querySelector('.sc-camov');
if(!ov)return null;const d=ov.getContext('2d').getImageData(0,0,ov.width,ov.height).data;
let nz=0;for(let i=3;i<d.length;i+=40){if(d[i]>10)nz++;}return {nz:nz,w:ov.width};})()""")
    check('A overlay draws dim+border (non-blank canvas)', isinstance(ov, dict) and ov.get('nz', 0) > 50, str(ov))
    check('A shutter button present', bool(js(c, '!!document.querySelector(".sc-shutter")')))
    time.sleep(1.0)
    shot(c, 'scancam-cam-390-dark.png')
    # capture -> crop screen
    js(c, 'document.querySelector(".sc-shutter").click()')
    crop = wait_js(c, '!!document.querySelector(".sc-adjust")', 15)
    check('A shutter capture -> crop/adjust screen', bool(crop))
    check('A stream stopped after capture',
          bool(js(c, '(function(){const v=document.querySelector("video");return !v;})()')))
    handles = js(c, '[...document.querySelectorAll(".sc-chandle")].map(h=>{const r=h.getBoundingClientRect();return Math.round(Math.min(r.width,r.height));})')
    check('A 4 corner handles >=44px', isinstance(handles, list) and len(handles) == 4 and all(x >= 44 for x in handles), str(handles))
    maskfill = js(c, '(function(){const p=document.querySelector(".sc-maskpath");return p?getComputedStyle(p).fill:"none";})()')
    check('A mask dims OUTSIDE (dark fill, no green tint)', isinstance(maskfill, str) and 'rgba(0, 0, 0, 0.55)' in maskfill, str(maskfill))
    borderstroke = js(c, '(function(){const p=document.querySelector(".sc-borderpoly");return p?getComputedStyle(p).stroke:"none";})()')
    check('A border is volt (not green fill)', isinstance(borderstroke, str) and '0, 0, 0' not in borderstroke, str(borderstroke))
    flabels = js(c, '[...document.querySelectorAll("[data-f]")].map(b=>b.textContent.trim())')
    check('A standard 4-filter bar', flabels == ['Color', 'Enhance', 'Grayscale', 'Black & White'], str(flabels))
    slabels = js(c, '[...document.querySelectorAll("[data-s]")].map(b=>b.textContent.trim())')
    check('A page-size bar (Auto/A4/Letter/Legal)', slabels == ['Auto', 'A4', 'Letter', 'Legal'], str(slabels))
    check('A live preview canvas + dims label',
          bool(js(c, '!!document.querySelector("[data-prev]")')) and bool(js(c, '!!document.querySelector("[data-dims]")')))
    check('A "Use this page" primary button', bool(js(c, '!!document.querySelector("[data-apply]")')))
    time.sleep(0.8)
    shot(c, 'scancam-crop-390-dark.png')
    drain_net(c)
finally:
    all_errs += scan_errors(c)
    try: proc.terminate(); proc.wait(timeout=10)
    except Exception: pass
    shutil.rmtree(prof, ignore_errors=True)

# ================================================================ run B: filters+dark
print('=== run B: 390 dark en — filters, sizes, drag, export ===', flush=True)
proc, c, prof = launch('b-390-dark', 390, 844, 'en')
try:
    wait_js(c, '!!(window.HUB&&HUB.scan&&HUB.scan._t)', 30)
    js(c, 'document.body.classList.add("dark")')
    wait_js(c, '!document.getElementById("splash")', 15)
    check('B crop view opens on synthetic doc', open_crop(c), '')
    time.sleep(0.5)

    stats = {}
    js(c, 'document.querySelector(\'[data-f="gray"]\').click()')
    time.sleep(0.3)
    for f in ['color', 'magic', 'gray', 'bw']:
        # instant-switch check: pixels must change SYNCHRONOUSLY inside click()
        r = js(c, """(function(){
const sig=()=>{const pv=document.querySelector('[data-prev]');
 const d=pv.getContext('2d').getImageData(0,0,pv.width,pv.height).data;
 let s=0;for(let i=0;i<d.length;i+=997)s=(s*31+d[i])>>>0;return s;};
const before=sig();
const t0=performance.now();
document.querySelector('[data-f="%s"]').click();
const dt=performance.now()-t0;
const after=sig();
return {changed:before!==after,ms:Math.round(dt*10)/10};})()""" % f)
        ok = isinstance(r, dict) and r.get('changed') and r.get('ms', 999) < 100
        check('B filter "%s" switches instantly+synchronously' % f, ok, str(r))
        stats[f] = js(c, '(' + PREVSTATS + ')()')
        shot(c, 'scancam-filter-%s-390-dark.png' % f)
        time.sleep(0.3)

    check('B gray is truly grayscale (R==G==B)',
          stats['gray']['eq'] > 0.99, str(round(stats['gray']['eq'], 4)))
    check('B bw is pure black/white',
          stats['bw']['bw'] > 0.99, str(round(stats['bw']['bw'], 4)))
    check('B color keeps color (not gray)',
          stats['color']['eq'] < 0.9, str(round(stats['color']['eq'], 4)))
    check('B enhance reduces warm cast vs color',
          stats['magic']['cast'] < stats['color']['cast'], 'color cast=%.1f magic cast=%.1f' % (stats['color']['cast'], stats['magic']['cast']))
    # pairwise visible difference
    diffs = js(c, """(function(){
const shotF=f=>{document.querySelector('[data-f="'+f+'"]').click();
 const pv=document.querySelector('[data-prev]');
 return Array.from(pv.getContext('2d').getImageData(0,0,pv.width,pv.height).data);};
const imgs={};['color','magic','gray','bw'].forEach(f=>imgs[f]=shotF(f));
const md=(a,b)=>{let s=0;for(let i=0;i<a.length;i+=13)s+=Math.abs(a[i]-b[i]);return s/(a.length/13);};
const ks=Object.keys(imgs),out={};
for(let i=0;i<ks.length;i++)for(let j=i+1;j<ks.length;j++)out[ks[i]+'/'+ks[j]]=Math.round(md(imgs[ks[i]],imgs[ks[j]])*10)/10;
return out;})()""")
    okd = isinstance(diffs, dict) and all(v > 8 for v in diffs.values())
    check('B every filter pair visibly differs', okd, str(diffs))
    check('B no spinner/busy element during switches',
          bool(js(c, '!document.querySelector(".sc-busy,.sc-spinner")')))

    # page sizes
    dims = {}
    for s, exp in [('auto', '1240 × 1550 px'), ('a4', '1240 × 1754 px'), ('letter', '1240 × 1605 px'), ('legal', '1065 × 1754 px')]:
        js(c, 'document.querySelector(\'[data-s="%s"]\').click()' % s)
        time.sleep(0.4)
        dims[s] = js(c, 'document.querySelector("[data-dims]").textContent')
        check('B size %s dims label' % s, dims[s] == exp, str(dims[s]))
    asp = js(c, """(function(){const pv=document.querySelector('[data-prev]');return pv.width/pv.height;})()""")
    check('B legal preview aspect ~ 8.5/14', abs(asp - 8.5/14) < 0.02, str(round(asp, 4)))
    js(c, 'document.querySelector(\'[data-s="auto"]\').click()'); time.sleep(0.3)

    # drag a corner handle
    d0 = js(c, 'document.querySelector("[data-mask] path").getAttribute("d")')
    drag = js(c, """(function(){
const h=document.querySelector('[data-h="0"]');if(!h)return 'no-handle';
const r=h.getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2;
h.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,clientX:cx,clientY:cy}));
window.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,clientX:cx+40,clientY:cy+40}));
window.dispatchEvent(new PointerEvent('pointerup',{bubbles:true}));
return 'ok';})()""")
    time.sleep(0.6)
    d1 = js(c, 'document.querySelector("[data-mask] path").getAttribute("d")')
    check('B corner drag updates the quad mask', drag == 'ok' and d0 != d1)
    shot(c, 'scancam-drag-390-dark.png')

    # use this page -> multi-page view
    js(c, 'document.querySelector("[data-f=color]").click()')
    js(c, 'document.querySelector("[data-apply]").click()')
    pg = wait_js(c, 'document.querySelectorAll(".sc-grid .sc-rpage").length>0', 15)
    check('B "Use this page" -> pages view with 1 page', bool(pg))
    shot(c, 'scancam-pages-390-dark.png')
    drain_net(c)
finally:
    all_errs += scan_errors(c)
    try: proc.terminate(); proc.wait(timeout=10)
    except Exception: pass
    shutil.rmtree(prof, ignore_errors=True)

# ================================================================ run C: light 390
print('=== run C: 390 light en — crop + filters ===', flush=True)
proc, c, prof = launch('c-390-light', 390, 844, 'en')
try:
    wait_js(c, '!!(window.HUB&&HUB.scan&&HUB.scan._t)', 30)
    js(c, 'document.body.classList.remove("dark")')
    wait_js(c, '!document.getElementById("splash")', 15)
    check('C crop view opens (light)', open_crop(c))
    time.sleep(0.5)
    for f in ['color', 'bw']:
        js(c, 'document.querySelector(\'[data-f="%s"]\').click()' % f)
        time.sleep(0.4)
        shot(c, 'scancam-filter-%s-390-light.png' % f)
    check('C light preview renders', bool(js(c, '(function(){const p=document.querySelector("[data-prev]");return p&&p.width>0;})()')))
    drain_net(c)
finally:
    all_errs += scan_errors(c)
    try: proc.terminate(); proc.wait(timeout=10)
    except Exception: pass
    shutil.rmtree(prof, ignore_errors=True)

# ================================================================ run D: 320px dark
print('=== run D: 320 dark en — narrow layout ===', flush=True)
proc, c, prof = launch('d-320-dark', 320, 700, 'en')
try:
    wait_js(c, '!!(window.HUB&&HUB.scan&&HUB.scan._t)', 30)
    js(c, 'document.body.classList.add("dark")')
    wait_js(c, '!document.getElementById("splash")', 15)
    check('D crop view opens (320px)', open_crop(c))
    time.sleep(0.5)
    over = js(c, 'document.documentElement.scrollWidth<=320')
    check('D no horizontal overflow at 320px', bool(over),
          str(js(c, 'document.documentElement.scrollWidth')))
    hb = js(c, '[...document.querySelectorAll(".sc-chandle")].map(h=>Math.round(h.getBoundingClientRect().width))')
    check('D handles still >=44px at 320px', isinstance(hb, list) and all(x >= 44 for x in hb), str(hb))
    shot(c, 'scancam-crop-320-dark.png')
    drain_net(c)
finally:
    all_errs += scan_errors(c)
    try: proc.terminate(); proc.wait(timeout=10)
    except Exception: pass
    shutil.rmtree(prof, ignore_errors=True)

# ================================================================ run E: es labels
print('=== run E: 390 dark es — i18n spot check ===', flush=True)
proc, c, prof = launch('e-390-es', 390, 844, 'es')
try:
    wait_js(c, '!!(window.HUB&&HUB.scan&&HUB.scan._t)', 30)
    js(c, 'document.body.classList.add("dark")')
    wait_js(c, '!document.getElementById("splash")', 15)
    js(c, 'HUB.i18n.loadLocale("es")', await_promise=True)
    check('E crop view opens (es)', open_crop(c))
    time.sleep(0.5)
    fl = js(c, '[...document.querySelectorAll("[data-f]")].map(b=>b.textContent.trim())')
    check('E es filter labels', fl == ['Color', 'Mejora', 'Grises', 'B/N'], str(fl))
    up = js(c, 'document.querySelector("[data-apply]").textContent.trim()')
    check('E es "Use this page"', up == 'Usar esta página', str(up))
    drain_net(c)
finally:
    all_errs += scan_errors(c)
    try: proc.terminate(); proc.wait(timeout=10)
    except Exception: pass
    shutil.rmtree(prof, ignore_errors=True)

print('--- network urls seen:', len(net_urls))
bad = [u for u in net_urls if u.startswith('http')]
check('zero runtime network requests', len(bad) == 0, str(bad[:3]))
check('zero console errors across runs', len(all_errs) == 0, str(all_errs[:5]))
print('RESULT', 'ALL GREEN' if not fails else ('%d FAILURES: %s' % (len(fails), fails)))
sys.exit(1 if fails else 0)
