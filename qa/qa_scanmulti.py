#!/usr/bin/env python3
"""QA: multi-page scanning — 5-page scan -> PDF (order) / DOCX (5 images),
reorder+delete reflected in export, tap preview, add-page keeps pages,
rapid-tap guards, huge photo, corrupt photo message, resize refit, zero errors."""
import json, subprocess, time, urllib.request, os, sys, base64, shutil, re
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
fails = []
net_urls = []

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

def launch(name, w, h, dark, lang):
    port = 9480 + (abs(hash(name)) % 200)
    prof = '/tmp/hubqa-scanmulti-' + re.sub(r'[^a-z0-9]+', '-', name)
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
    c.send('Runtime.enable'); c.send('Page.enable'); c.send('Network.enable')
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': w, 'height': h, 'deviceScaleFactor': 2, 'mobile': True})
    c.send('Page.navigate', {'url': BASE})
    return proc, c, prof

def js(c, expr, await_promise=False, timeout=120):
    r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True,
                                    'awaitPromise': await_promise}, wait=True, timeout=timeout)
    res = (r or {}).get('result', {})
    if res.get('subtype') == 'error':
        return {'__err': res.get('description')}
    if (r or {}).get('exceptionDetails'):
        return {'__err': json.dumps((r or {})['exceptionDetails'])[:300]}
    return res.get('value')

def wait_js(c, expr, timeout=30):
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
    for e in c.events:
        if e.get('method') == 'Network.requestWillBeSent':
            net_urls.append(e['params']['request']['url'])
    c.events = [e for e in c.events if e.get('method') != 'Network.requestWillBeSent']

def inject_files(c, input_sel, blobs):
    expr = ('(async()=>{const inp=document.querySelector(%s);if(!inp)return "no-input";'
            'const dt=new DataTransfer();' % json.dumps(input_sel))
    for b64, name, mime in blobs:
        expr += ('{const bin=atob(%s);const u=new Uint8Array(bin.length);'
                 'for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);'
                 'dt.items.add(new File([u],%s,{type:%s}));}' % (json.dumps(b64), json.dumps(name), json.dumps(mime)))
    expr += ('inp.files=dt.files;inp.dispatchEvent(new Event("change",{bubbles:true}));'
             'return "injected:"+dt.files.length;})()')
    return js(c, expr, await_promise=True)

# 5 visually distinct photos: solid color + small number in a corner (kept small and
# off-center so the edge detector doesn't lock onto the digit; order sampled at 8%,8%)
COLORPHOTO = """(i)=>{
const cols=[["#d43a2f","1"],["#2f9e4f","2"],["#2f6fd4","3"],["#d4a72f","4"],["#a03fd4","5"]];
const cv=document.createElement('canvas');cv.width=800;cv.height=1000;
const x=cv.getContext('2d');
x.fillStyle=cols[i][0];x.fillRect(0,0,800,1000);
x.fillStyle='rgba(255,255,255,.95)';x.font='bold 110px sans-serif';
x.textAlign='right';x.textBaseline='alphabetic';x.fillText(cols[i][1],760,950);
return new Promise(res=>cv.toBlob(b=>{const fr=new FileReader();
fr.onload=()=>res(fr.result.split(',')[1]);fr.readAsDataURL(b);},'image/png'));}"""

def page_colors(c, pdf_u8_js):
    """render exported PDF pages, sample a corner patch (away from the centered
    digit) -> average rgb per page, so export order is checkable"""
    return js(c, '''(async()=>{
const u=%s;
const a=await HUB.scan._t.pdfToImages(u,0.6,"image/png");
const out=[];
for(const p of a){
const bmp=await createImageBitmap(new Blob([p],{type:"image/png"}));
const cv=document.createElement("canvas");cv.width=bmp.width;cv.height=bmp.height;
const x=cv.getContext("2d");x.drawImage(bmp,0,0);
const sx=Math.floor(bmp.width*0.08),sy=Math.floor(bmp.height*0.08);
const d=x.getImageData(sx-6,sy-6,12,12).data;
let r=0,g=0,b=0,n=0;
for(let i=0;i<d.length;i+=4){r+=d[i];g+=d[i+1];b+=d[i+2];n++;}
out.push([Math.round(r/n),Math.round(g/n),Math.round(b/n)]);}
return out;})()''' % pdf_u8_js, await_promise=True, timeout=180)

def dom_color(px):
    r, g, b = px
    if r < 40 and g < 40 and b < 40: return 'K'  # black/blank page = failure mode
    if r > 150 and g < 130 and b < 130: return 'R'
    if g > 110 and r < 130 and b < 130: return 'G'
    if b > 120 and r < 130 and g < 130: return 'B'
    if r > 150 and g > 120 and b < 130: return 'Y'
    if r > 110 and b > 120 and g < 120: return 'M'
    return '?'

print('=== multi-page: 390 dark en ===')
proc, c, prof = launch('multi-390-dark', 390, 844, True, 'en')
try:
    wait_js(c, '!!(window.HUB&&HUB.scan&&HUB.scan._t)', 30)
    js(c, 'document.body.classList.add("dark")')
    wait_js(c, '!document.getElementById("splash")', 15)
    js(c, 'window.__cap=[];const _c=URL.createObjectURL.bind(URL);'
           'URL.createObjectURL=function(b){window.__cap.push(b);return _c(b);};')

    # build 5 distinct photos in-page
    photos = []
    for i in range(5):
        b64 = js(c, '(%s)(%d)' % (COLORPHOTO, i), await_promise=True)
        photos.append(b64)
    check('M 5 distinct photos generated', all(isinstance(p, str) and len(p) > 5000 for p in photos))

    # multi-select -> auto pages (no per-file crop stop)
    js(c, 'HUB.scan.tool("scan")')
    wait_js(c, '!!document.querySelector("[data-m=take]")')
    r = inject_files(c, '.scroot [data-choose]',
                     [(photos[i], 'p%d.png' % (i + 1), 'image/png') for i in range(5)])
    ok = wait_js(c, 'document.querySelectorAll(".scroot .sc-rpage").length===5', 60)
    check('M 5 photos -> 5 page thumbnails', bool(ok), 'inject:' + str(r))
    nums = js(c, '[...document.querySelectorAll(".scroot .sc-rpage .sc-pgnum")].map(e=>e.textContent.trim())') if ok else None
    check('M thumbnails numbered Page 1..5', nums == ['Page 1', 'Page 2', 'Page 3', 'Page 4', 'Page 5'], str(nums))
    tops = js(c, '[...document.querySelectorAll(".scroot .sc-rpage")].map(e=>Math.round(e.getBoundingClientRect().top))') if ok else None
    check('M thumbnails laid out (not stacked)', isinstance(tops, list) and len(set(tops)) > 1, str(tops))
    blk = js(c, '''(()=>{const out=[];
document.querySelectorAll(".scroot .sc-rpage canvas").forEach(cv=>{
const x=cv.getContext("2d");const sx=Math.floor(cv.width*0.08),sy=Math.floor(cv.height*0.08);
const d=x.getImageData(sx-4,sy-4,8,8).data;let r=0,g=0,b=0,n=0;
for(let i=0;i<d.length;i+=4){r+=d[i];g+=d[i+1];b+=d[i+2];n++;}
out.push([Math.round(r/n),Math.round(g/n),Math.round(b/n)]);});
return out;})()''') if ok else None
    seq0 = ''.join(dom_color(p) for p in blk) if isinstance(blk, list) else '?'
    check('M no silent black pages (quad validation)', isinstance(blk, list) and 'K' not in seq0 and '?' not in seq0, seq0)
    note = js(c, '(document.querySelector(".scroot .sc-note")||{}).textContent')
    check('M honest docx note shown', bool(note) and 'not editable' in note, repr((note or '')[:70]))
    time.sleep(0.6)
    js(c, 'document.querySelector(".scroot .sc-grid").scrollIntoView({block:"center"})')
    time.sleep(0.4)
    shot(c, 'scanfix-multipage-390-dark.png')

    # tap preview
    js(c, 'document.querySelectorAll(".scroot .sc-rpage")[0].click()')
    pv = wait_js(c, '!!document.querySelector(".scroot [data-pv]")', 10)
    pvt = js(c, '(document.querySelector(".scroot .sc-sect")||{}).textContent') if pv else None
    check('M tap -> page preview', bool(pv) and pvt and 'Page 1 / 5' in pvt, repr(pvt))
    js(c, 'document.querySelector(".scroot [data-pvback]").click()')
    check('M preview back -> pages', bool(wait_js(c, 'document.querySelectorAll(".scroot .sc-rpage").length===5', 10)))

    # export PDF: 5 pages, correct order (color sequence R G B Y M)
    js(c, 'document.querySelector(".scroot [data-exp]").click()')
    check('M export PDF -> done', bool(wait_js(c, '!!document.querySelector(".scroot .sc-done")', 120)))
    pdfinfo = js(c, '''(async()=>{const b=window.__cap[window.__cap.length-1];
const u=new Uint8Array(await b.arrayBuffer());window.__lastPdf=u;
const d=await window.PDFLib.PDFDocument.load(u);
return {pages:d.getPageCount(),h:String.fromCharCode(u[0],u[1],u[2],u[3],u[4])};})()''', await_promise=True)
    check('M exported PDF: 5 pages', isinstance(pdfinfo, dict) and pdfinfo.get('pages') == 5, str(pdfinfo))
    cols = page_colors(c, 'window.__lastPdf')
    seq = ''.join(dom_color(p) for p in cols) if isinstance(cols, list) else '?'
    check('M page order correct (R G B Y M)', seq == 'RGBYM', seq + ' ' + str(cols))

    # export DOCX: valid, 5 images
    js(c, 'HUB.scan.tool("scan")')
    wait_js(c, '!!document.querySelector("[data-m=take]")')
    inject_files(c, '.scroot [data-choose]',
                 [(photos[i], 'p%d.png' % (i + 1), 'image/png') for i in range(5)])
    wait_js(c, 'document.querySelectorAll(".scroot .sc-rpage").length===5', 60)
    js(c, 'document.querySelector(".scroot [data-expw]").click()')
    check('M export Word -> done', bool(wait_js(c, '!!document.querySelector(".scroot .sc-done")', 180)))
    dxb64 = js(c, '''(async()=>{const b=window.__cap[window.__cap.length-1];
const u=new Uint8Array(await b.arrayBuffer());
let s="";for(let i=0;i<u.length;i++)s+=String.fromCharCode(u[i]);
return {head:String.fromCharCode(u[0],u[1]),b64:btoa(s),len:u.length};})()''',
               await_promise=True, timeout=60)
    import zipfile, io
    dxok = False
    dxinfo = 'nodict'
    if isinstance(dxb64, dict):
        dxinfo = 'head=%s len=%s' % (dxb64.get('head'), dxb64.get('len'))
        if dxb64.get('head') == 'PK':
            try:
                zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(dxb64['b64'])))
                media = [n for n in zf.namelist()
                         if n.startswith('word/media/') and not n.endswith('/')]
                dxinfo += ' media=%d' % len(media)
                dxok = len(media) == 5
            except Exception as e:
                dxinfo += ' ziperr=' + str(e)[:80]
    check('M .docx valid with 5 page images', dxok, dxinfo)
    dxfn = js(c, '(document.querySelector(".scroot .sc-donefn")||{}).textContent')
    check('M .docx filename', bool(dxfn) and dxfn.endswith('.docx'), repr(dxfn))

    # reorder reflected in export: move page 1 to the end via UI
    js(c, 'HUB.scan.tool("scan")')
    wait_js(c, '!!document.querySelector("[data-m=take]")')
    inject_files(c, '.scroot [data-choose]',
                 [(photos[i], 'p%d.png' % (i + 1), 'image/png') for i in range(5)])
    wait_js(c, 'document.querySelectorAll(".scroot .sc-rpage").length===5', 60)
    # move page 1 right step by step: each click targets the thumb now holding page 1
    for i in range(4):
        js(c, 'document.querySelectorAll(".scroot .sc-rpage")[%d].querySelector("[data-m=\\"1\\"]").click()' % i)
        time.sleep(0.4)
    # page identity is the color (labels are positional); red page moved to end => green first
    fc = js(c, '''(()=>{const cv=document.querySelector(".scroot .sc-rpage canvas");
const x=cv.getContext("2d");const sx=Math.floor(cv.width*0.08),sy=Math.floor(cv.height*0.08);
const d=x.getImageData(sx-4,sy-4,8,8).data;let r=0,g=0,b=0,n=0;
for(let i=0;i<d.length;i+=4){r+=d[i];g+=d[i+1];b+=d[i+2];n++;}
return [Math.round(r/n),Math.round(g/n),Math.round(b/n)];})()''')
    check('M reorder UI: red page moved to end (first thumb now green)',
          isinstance(fc, list) and dom_color(fc) == 'G', str(fc))
    js(c, 'document.querySelector(".scroot [data-exp]").click()')
    wait_js(c, '!!document.querySelector(".scroot .sc-done")', 120)
    js(c, '''(async()=>{const b=window.__cap[window.__cap.length-1];
window.__lastPdf=new Uint8Array(await b.arrayBuffer());})()''', await_promise=True)
    cols = page_colors(c, 'window.__lastPdf')
    seq = ''.join(dom_color(p) for p in cols) if isinstance(cols, list) else '?'
    check('M export reflects reorder (G B Y M R)', seq == 'GBYMR', seq)

    # delete reflected in export
    js(c, 'HUB.scan.tool("scan")')
    wait_js(c, '!!document.querySelector("[data-m=take]")')
    inject_files(c, '.scroot [data-choose]',
                 [(photos[i], 'p%d.png' % (i + 1), 'image/png') for i in range(5)])
    wait_js(c, 'document.querySelectorAll(".scroot .sc-rpage").length===5', 60)
    js(c, 'document.querySelectorAll(".scroot .sc-rpage")[2].querySelector("[data-x]").click()')
    n = js(c, 'document.querySelectorAll(".scroot .sc-rpage").length')
    check('M delete removes page 3', n == 4, str(n))
    js(c, 'document.querySelector(".scroot [data-exp]").click()')
    wait_js(c, '!!document.querySelector(".scroot .sc-done")', 120)
    pg = js(c, '''(async()=>{const b=window.__cap[window.__cap.length-1];
const u=new Uint8Array(await b.arrayBuffer());
const d=await window.PDFLib.PDFDocument.load(u);return d.getPageCount();})()''', await_promise=True)
    check('M export reflects delete (4 pages)', pg == 4, str(pg))

    # add-page keeps existing pages (the critical SCAN.start fix)
    js(c, 'HUB.scan.tool("scan")')
    wait_js(c, '!!document.querySelector("[data-m=take]")')
    inject_files(c, '.scroot [data-choose]', [(photos[0], 'p1.png', 'image/png')])
    wait_js(c, '!!document.querySelector(".scroot .sc-cropwrap")', 60)
    js(c, 'document.querySelector(".scroot [data-apply]").click()')
    wait_js(c, 'document.querySelectorAll(".scroot .sc-rpage").length===1', 20)
    js(c, 'document.querySelector(".scroot [data-add]").click()')
    back = wait_js(c, '!!document.querySelector(".scroot [data-m=take]")', 10)
    check('M add-page returns to capture', bool(back))
    inject_files(c, '.scroot [data-choose]', [(photos[1], 'p2.png', 'image/png')])
    wait_js(c, '!!document.querySelector(".scroot .sc-cropwrap")', 60)
    js(c, 'document.querySelector(".scroot [data-apply]").click()')
    n = wait_js(c, 'document.querySelectorAll(".scroot .sc-rpage").length===2', 20)
    check('M add-page keeps page 1 (2 pages total)', bool(n))

    # back from crop keeps pages
    js(c, 'document.querySelector(".scroot [data-add]").click()')
    wait_js(c, '!!document.querySelector(".scroot [data-m=take]")', 10)
    inject_files(c, '.scroot [data-choose]', [(photos[2], 'p3.png', 'image/png')])
    wait_js(c, '!!document.querySelector(".scroot .sc-cropwrap")', 60)
    js(c, 'document.querySelector(".scroot [data-back]").click()')
    n = wait_js(c, 'document.querySelectorAll(".scroot .sc-rpage").length===2', 10)
    check('M back from crop keeps 2 pages', bool(n))

    # rapid-tap export guard: only one done block
    js(c, '''(()=>{const b=document.querySelector(".scroot [data-exp]");b.click();b.click();})()''')
    wait_js(c, '!!document.querySelector(".scroot .sc-done")', 120)
    time.sleep(1.5)
    nd = js(c, 'document.querySelectorAll(".scroot .sc-done").length')
    check('M rapid double-tap export -> single done', nd == 1, str(nd))

    # huge photo (4000x5000, real file bytes) downscales safely, quad detected
    js(c, 'HUB.scan.tool("scan")')
    wait_js(c, '!!document.querySelector("[data-m=take]")', 10)
    with open('/tmp/huge.jpg', 'rb') as f:
        big = base64.b64encode(f.read()).decode()
    inject_files(c, '.scroot [data-choose]', [(big, 'huge.jpg', 'image/jpeg')])
    ok = wait_js(c, '!!document.querySelector(".scroot .sc-cropwrap")', 90)
    det = js(c, '!!document.querySelector(".scroot polygon.sc-quad")') if ok else False
    vb = js(c, '(document.querySelector(".scroot svg.sc-svg")||{}).getAttribute("viewBox")') if ok else None
    small = False
    if vb:
        try: small = max(int(float(vb.split()[2])), int(float(vb.split()[3]))) <= 1600
        except Exception: pass
    check('M huge photo handled, downscaled, quad detected', bool(ok) and bool(det) and small,
          'viewBox=' + str(vb))

    # corrupt image -> clear message, no dead screen
    js(c, 'HUB.scan.tool("scan")')
    wait_js(c, '!!document.querySelector("[data-m=take]")', 10)
    bad = base64.b64encode(b'this is not an image at all' * 100).decode()
    inject_files(c, '.scroot [data-choose]', [(bad, 'bad.png', 'image/png')])
    msg = wait_js(c, '''(()=>{const n=document.querySelector(".scroot .sc-note.sc-err");
return n?n.textContent:null;})()''', 30)
    check('M corrupt photo -> clear message', bool(msg) and "Couldn't read" in msg, repr((msg or '')[:60]))
    alive = js(c, '!!document.querySelector(".scroot [data-m=take]")')
    check('M corrupt photo -> capture screen still alive', bool(alive))

    # resize refit in crop view
    inject_files(c, '.scroot [data-choose]', [(photos[0], 'p1.png', 'image/png')])
    wait_js(c, '!!document.querySelector(".scroot .sc-cropwrap")', 60)
    w0 = js(c, 'document.querySelector(".scroot svg.sc-svg").style.width')
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': 500, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    js(c, 'window.dispatchEvent(new Event("resize"))')
    time.sleep(0.8)
    w1 = js(c, 'document.querySelector(".scroot svg.sc-svg").style.width')
    check('M rotation/resize refits crop view', w0 and w1 and w0 != w1, '%s -> %s' % (w0, w1))
    c.send('Emulation.setDeviceMetricsOverride',
           {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})

    errs = js(c, 'window.__scanerr') or []
    check('M zero console errors', len(errs) == 0, str(errs[:5]))
    drain_net(c)
    ext = [u for u in net_urls if u.startswith('http')]
    check('M zero http(s) requests', len(ext) == 0, str(ext[:5]))
finally:
    try: c.close()
    except Exception: pass
    proc.terminate()
    shutil.rmtree(prof, ignore_errors=True)

print('\n%d FAILURES' % len(fails))
sys.exit(1 if fails else 0)
