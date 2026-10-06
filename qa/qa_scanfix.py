#!/usr/bin/env python3
"""QA: Student Scanner bugfix round.
Bug 1: crop view (svg overlay, scanline removal, finger-sized handles).
Bug 2: PDF->Word refuses scrambled/empty text with an honest message + PDF->Images fallback.
Word->PDF: mammoth preview renders, iPhone 4-step guidance, print CSS targets .sc-printdoc.
Full 14-item conversion matrix with OUTPUT CORRECTNESS (not just zero errors).
"""
import json, subprocess, time, urllib.request, os, sys, base64, shutil, re
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
FIX = '/tmp/scan-qa'
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
fails = []
matrix = []          # (name, passed, detail)
net_urls = []

def check(n, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + n + ((' | ' + str(extra)) if extra else ''), flush=True)
    if not ok: fails.append(n)

def mrow(n, ok, detail=''):
    matrix.append((n, ok, detail))
    check('[matrix] ' + n, ok, detail)

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
    prof = '/tmp/hubqa-scanfix-' + re.sub(r'[^a-z0-9]+', '-', name)
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
    for e in c.events:
        if e.get('method') == 'Network.requestWillBeSent':
            net_urls.append(e['params']['request']['url'])
    c.events = [e for e in c.events if e.get('method') != 'Network.requestWillBeSent']

def b64file(name):
    with open(os.path.join(FIX, name), 'rb') as f:
        return base64.b64encode(f.read()).decode()

def u8js(b64):
    return ('(function(){const bin=atob(%s);const u=new Uint8Array(bin.length);'
            'for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);return u;})()' % json.dumps(b64))

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

DOCPHOTO = """()=>{
const cv=document.createElement('canvas');cv.width=800;cv.height=1000;
const x=cv.getContext('2d');
x.fillStyle='#3a3f4a';x.fillRect(0,0,800,1000);
x.save();x.translate(400,500);x.rotate(0.06);
x.fillStyle='#f8f8f5';x.fillRect(-300,-400,600,800);
x.fillStyle='#1c1c1c';
for(let i=0;i<24;i++){x.fillRect(-260,-360+i*30,520-(i%5)*40,8);}
x.fillStyle='#1c1c1c';x.font='bold 34px sans-serif';x.fillText('Test Document',-260,-330);
x.restore();
return new Promise(res=>cv.toBlob(res,'image/png'));}"""

DOCX_BUILD = """(async()=>{
if(!window.docx){await new Promise((res,rej)=>{const s=document.createElement("script");
s.src="vendor/docx.umd.js";s.onload=res;s.onerror=()=>rej(new Error("lib"));document.head.appendChild(s);});}
const D=window.docx;
const doc=new D.Document({sections:[{children:[new D.Paragraph({heading:D.HeadingLevel.HEADING_1,
children:[new D.TextRun("Hello Word")]}),new D.Paragraph("plain para for print preview")]}]});
const blob=await D.Packer.toBlob(doc);
const u=new Uint8Array(await blob.arrayBuffer());
let s="";for(let i=0;i<u.length;i++)s+=String.fromCharCode(u[i]);
return btoa(s);})()"""

def nonblank_js(varname='u'):
    return ('''(async()=>{
const bmp=await createImageBitmap(new Blob([%s],{type:"image/png"}));
const cv=document.createElement("canvas");cv.width=64;cv.height=64;
const x=cv.getContext("2d");x.drawImage(bmp,0,0,64,64);
const d=x.getImageData(0,0,64,64).data;let mn=255,mx=0;
for(let i=0;i<d.length;i+=16){const v=d[i]+d[i+1]+d[i+2];if(v<mn)mn=v;if(v>mx)mx=v;}
return {w:bmp.width,h:bmp.height,spread:mx-mn};})()''' % varname)

# ---------------------------------------------------------------- run A: 390 dark
print('=== run A: 390 dark en — crop, bug2, matrix ===')
proc, c, prof = launch('a-390-dark', 390, 844, True, 'en')
try:
    wait_js(c, '!!(window.HUB&&HUB.scan&&HUB.scan._t)', 30)
    js(c, 'document.body.classList.add("dark")')
    wait_js(c, '!document.getElementById("splash")', 15)

    S = b64file('structured.pdf'); C = b64file('cipher.pdf'); E = b64file('empty.pdf')

    # ---- Bug 1: crop view ----
    js(c, 'HUB.scan.tool("scan")')
    wait_js(c, '!!document.querySelector("[data-m=take]")')
    blob_b64 = js(c, '(%s)().then(b=>new Promise(res=>{const fr=new FileReader();'
                      'fr.onload=()=>res(fr.result.split(",")[1]);fr.readAsDataURL(b);}))' % DOCPHOTO,
                  await_promise=True)
    js(c, 'window.__cap=[];const _c=URL.createObjectURL.bind(URL);'
           'URL.createObjectURL=function(b){window.__cap.push(b);return _c(b);};')
    r = inject_files(c, '.scroot [data-choose]', [(blob_b64, 'doc.png', 'image/png')])
    check('A crop view rendered', bool(wait_js(c, '!!document.querySelector(".sc-cropwrap")', 30)), str(r))

    geo = js(c, '''(()=>{const w=document.querySelector(".sc-cropwrap");if(!w)return null;
const cv=w.querySelector("canvas"),svg=w.querySelector("svg");
const a=cv.getBoundingClientRect(),b=svg.getBoundingClientRect(),cc=w.getBoundingClientRect();
return {cls:svg.getAttribute("class")||"",dTop:Math.abs(a.top-b.top),dW:Math.abs(a.width-b.width),
band:cc.height-a.height,handles:document.querySelectorAll("circle.sc-handle").length};})()''')
    check('A svg overlays canvas (class+geometry)', isinstance(geo, dict) and 'sc-svg' in geo['cls']
          and geo['dTop'] < 3 and geo['dW'] < 3, str(geo))
    check('A no dark band below image', isinstance(geo, dict) and geo['band'] < 10, str(geo and geo['band']))

    handles = js(c, '''[...document.querySelectorAll("circle.sc-handle")].map(h=>({
r:+h.getAttribute("r"),fill:getComputedStyle(h).fill}))''')
    ok_h = isinstance(handles, list) and len(handles) == 4 and all(
        h['r'] >= 28 and h['fill'].startswith('rgb') for h in handles)
    check('A 4 finger-sized painted handles', ok_h, str(handles))

    gone = wait_js(c, '!document.querySelector(".sc-scanline")', 14)
    check('A scanline removed after sweep', bool(gone))
    time.sleep(0.6)
    shot(c, 'scanfix-crop-390-dark.png')

    # ---- Scan -> PDF (matrix 1) ----
    js(c, 'document.querySelector("[data-apply]").click()')
    check('A page added', bool(wait_js(c, 'document.querySelectorAll(".sc-page").length===1' if False else '!!document.querySelector("[data-exp]")', 20)))
    js(c, 'document.querySelector("[data-exp]").click()')
    check('A scan exported -> done', bool(wait_js(c, '!!document.querySelector(".sc-done")', 30)))
    head = js(c, '''(async()=>{const b=window.__cap[window.__cap.length-1];
const u=new Uint8Array(await b.arrayBuffer());
return {h:String.fromCharCode(u[0],u[1],u[2],u[3],u[4]),len:u.length};})()''', await_promise=True)
    pg1 = js(c, '''(async()=>{const b=window.__cap[window.__cap.length-1];
const u=new Uint8Array(await b.arrayBuffer());
const d=await window.PDFLib.PDFDocument.load(u);return d.getPageCount();})()''', await_promise=True)
    mrow('1 Scan -> PDF (valid, 1 page)', isinstance(head, dict) and head.get('h') == '%PDF-' and pg1 == 1,
         'head=%s pages=%s' % (head.get('h') if isinstance(head, dict) else head, pg1))

    # ---- Bug 2: engine-level ----
    w = js(c, '(async()=>{const u=%s;const bl=await HUB.scan._t.pdfToWord(u);'
               'const a=new Uint8Array(await bl.arrayBuffer());'
               'return String.fromCharCode(a[0],a[1]);})()' % u8js(S), await_promise=True)
    mrow('3a PDF->Word engine: structured -> PK zip', w == 'PK', repr(w))

    bc = js(c, '(async()=>{try{await HUB.scan._t.pdfToWord(%s);return "NO-REJECT";}'
               'catch(e){return e&&e.code||String(e);}})()' % u8js(C), await_promise=True)
    check('A cipher PDF rejected with BADTEXT', bc == 'BADTEXT', repr(bc))
    be = js(c, '(async()=>{try{await HUB.scan._t.pdfToWord(%s);return "NO-REJECT";}'
               'catch(e){return e&&e.code||String(e);}})()' % u8js(E), await_promise=True)
    check('A empty-text PDF rejected with BADTEXT', be == 'BADTEXT', repr(be))

    # ---- Bug 2: view-level honest message ----
    js(c, 'HUB.scan.tool("pdf2word")')
    wait_js(c, '!!document.querySelector(".scroot .sc-pick input")')
    r = inject_files(c, '.scroot .sc-pick input', [(C, 'cipher.pdf', 'application/pdf')])
    ok = wait_js(c, '!!document.querySelector(".scroot .sc-note.sc-err")', 60)
    msg = js(c, '(document.querySelector(".scroot .sc-note.sc-err")||{}).textContent') if ok else None
    btn = js(c, '!!document.querySelector(".scroot [data-alt]")') if ok else False
    check('A cipher PDF -> honest message, no .docx', bool(ok) and 'read as text' in (msg or '') and btn,
          repr((msg or '')[:80]))
    nodocx = js(c, '!document.querySelector(".scroot .sc-done")')
    check('A no done block for cipher PDF', bool(nodocx))
    time.sleep(0.5)
    shot(c, 'scanfix-badpdf-390-dark.png')
    js(c, 'document.querySelector(".scroot [data-alt]").click()')
    check('A fallback button opens PDF->Images tool',
          bool(wait_js(c, 'document.querySelectorAll(".scroot [data-s]").length===3', 10)))

    # normal PDF still converts via the view
    js(c, 'HUB.scan.tool("pdf2word")')
    wait_js(c, '!!document.querySelector(".scroot .sc-pick input")')
    inject_files(c, '.scroot .sc-pick input', [(S, 'structured.pdf', 'application/pdf')])
    ok = wait_js(c, '!!document.querySelector(".scroot .sc-done")', 60)
    fn = js(c, '(document.querySelector(".scroot .sc-donefn")||{}).textContent') if ok else None
    check('A structured PDF -> .docx done block', bool(ok) and (fn or '').endswith('.docx'), repr(fn))

    # ---- matrix: structure survives (mammoth round-trip) ----
    html = js(c, '''(async()=>{const u=%s;const bl=await HUB.scan._t.pdfToWord(u);
const du=new Uint8Array(await bl.arrayBuffer());
return await HUB.scan._t.wordToHtml(du);})()''' % u8js(S), await_promise=True, timeout=120)
    ok_s = isinstance(html, str) and 'Photosynthesis' in html and re.search(r'<h1', html, re.I) \
        and re.search(r'<(ul|ol)', html, re.I) and re.search(r'<table', html, re.I) and 'Leaf A' in html
    mrow('3 PDF -> Word (headings/lists/table survive)', bool(ok_s),
         ('h1/ul/table found' if ok_s else repr((html or '')[:120])))

    # ---- matrix 2: photos -> pdf (multi) ----
    p2 = js(c, '''(async()=>{const mk=%s;
const b1=await mk(),b2=await mk();
const f=async b=>{const u=new Uint8Array(await b.arrayBuffer());return {bytes:u,png:true};};
const out=await HUB.scan._t.imagesToPdf([await f(b1),await f(b2)]);
const d=await window.PDFLib.PDFDocument.load(out);return d.getPageCount();})()''' % DOCPHOTO,
        await_promise=True, timeout=120)
    mrow('2 Photos -> PDF (2 photos -> 2 pages)', p2 == 2, repr(p2))

    # ---- matrix 5: pdf -> images, non-blank ----
    im = js(c, '(async()=>{const a=await HUB.scan._t.pdfToImages(%s,1.0,"image/png");return a.length;})()' % u8js(S),
            await_promise=True, timeout=120)
    nb = js(c, '''(async()=>{
const a=await HUB.scan._t.pdfToImages(%s,1.0,"image/png");
const out=[];
for(const u of a){
const bmp=await createImageBitmap(new Blob([u],{type:"image/png"}));
const cv=document.createElement("canvas");cv.width=64;cv.height=64;
const x=cv.getContext("2d");x.drawImage(bmp,0,0,64,64);
const d=x.getImageData(0,0,64,64).data;let mn=1e9,mx=-1e9;
for(let i=0;i<d.length;i+=16){const v=d[i]+d[i+1]+d[i+2];if(v<mn)mn=v;if(v>mx)mx=v;}
out.push({w:bmp.width,spread:mx-mn});}
return out;})()''' % u8js(S), await_promise=True, timeout=180)
    ok5 = im == 3 and isinstance(nb, list) and len(nb) == 3 and all(
        x['w'] > 0 and x['spread'] > 12 for x in nb)
    mrow('5 PDF -> Images (3 pages, all non-blank)', ok5, 'count=%s spreads=%s' % (im, [x.get('spread') for x in nb] if isinstance(nb, list) else nb))

    # ---- matrix 6: pdf -> text ----
    tx = js(c, '(async()=>{const t=await HUB.scan._t.pdfText(%s);return t.join("\\n").length+"|"+t[0].slice(0,14);})()' % u8js(S),
            await_promise=True)
    ok6 = isinstance(tx, str) and '|' in tx and 'Photosynthesis' in tx and int(tx.split('|')[0]) > 200
    mrow('6 PDF -> Text (readable)', ok6, repr(tx)[:60])

    # ---- matrix 7: pdf -> excel ----
    xl = js(c, '''(async()=>{const x=await HUB.scan._t.pdfToExcel(%s);
const u=new Uint8Array(x);const head=String.fromCharCode(u[0],u[1]);
const wb=window.XLSX.read(u,{type:"array"});
const rows=window.XLSX.utils.sheet_to_json(wb.Sheets["Page 2"],{header:1});
const flat=JSON.stringify(rows);
return {head:head,sheets:wb.SheetNames.length,hasLeafA:flat.indexOf("Leaf A")>=0,n:rows.length};})()''' % u8js(S),
            await_promise=True, timeout=120)
    mrow('7 PDF -> Excel (real .xlsx, table data in cells)',
         isinstance(xl, dict) and xl.get('head') == 'PK' and xl.get('hasLeafA') and xl.get('n', 0) >= 4, str(xl))

    # ---- matrix 8: jpg<->png ----
    cv = js(c, '''(async()=>{const b=await (%s)();
const u=new Uint8Array(await b.arrayBuffer());
const j=await HUB.scan._t.convertImage(u,"image/jpeg",0.9);
const p=await HUB.scan._t.convertImage(j.bytes,"image/png");
const bj=await createImageBitmap(new Blob([j.bytes],{type:"image/jpeg"}));
const bp=await createImageBitmap(new Blob([p.bytes],{type:"image/png"}));
return [j.bytes[0],j.bytes[1],p.bytes[0],p.bytes[1],p.bytes[2],bj.width>0,bp.width>0];})()''' % DOCPHOTO,
            await_promise=True, timeout=120)
    mrow('8 JPG<->PNG (valid, correct format)', cv == [255, 216, 137, 80, 78, True, True], str(cv))

    # ---- matrix 9: heic -> jpg (real sample) ----
    H = b64file('sample.heic')
    he = js(c, '''(async()=>{const j=await HUB.scan._t.heicToJpg(%s);
const bmp=await createImageBitmap(new Blob([j],{type:"image/jpeg"}));
return [j[0],j[1],j[2],bmp.width,bmp.height];})()''' % u8js(H), await_promise=True, timeout=180)
    mrow('9 HEIC -> JPG (real sample)', isinstance(he, list) and he[0] == 255 and he[1] == 216 and he[3] > 0,
         'magic=FFD8 size=%sx%s' % (he[3], he[4]) if isinstance(he, list) else repr(he))

    # ---- matrix 10/11/12: merge / split / rotate ----
    mg = js(c, '(async()=>{const u=%s;const m=await HUB.scan._t.mergePdfs([u,u]);'
               'const d=await window.PDFLib.PDFDocument.load(m);return d.getPageCount();})()' % u8js(S), await_promise=True)
    mrow('10 Merge PDFs (3+3=6)', mg == 6, repr(mg))
    sp = js(c, '(async()=>{const u=%s;const outs=await HUB.scan._t.splitPdf(u,[[1,2],[3]]);const r=[];'
               'for(const o of outs){const d=await window.PDFLib.PDFDocument.load(o);r.push(d.getPageCount());}'
               'return r;})()' % u8js(S), await_promise=True)
    mrow('11 Split [1,2],[3] -> 2+1 pages', sp == [2, 1], repr(sp))
    ro = js(c, '(async()=>{const u=%s;const r=await HUB.scan._t.rotatePdf(u,90);'
               'const d=await window.PDFLib.PDFDocument.load(r);'
               'return d.getPages().map(p=>p.getRotation().angle);})()' % u8js(S), await_promise=True)
    mrow('12 Rotate 90deg all pages', ro == [90, 90, 90], repr(ro))

    # ---- matrix 13: reorder + delete ----
    rd = js(c, '(async()=>{const u=%s;const r=await HUB.scan._t.reorderPdf(u,[1,3]);'
               'const d=await window.PDFLib.PDFDocument.load(r);'
               'const t=await HUB.scan._t.pdfText(r);'
               'return [d.getPageCount(),t[0].slice(0,14),t[1].slice(0,10)];})()' % u8js(S), await_promise=True)
    mrow('13 Reorder+delete engine ([1,3] drops p2)', isinstance(rd, list) and rd[0] == 2
         and rd[1].startswith('Photosynthesis') and rd[2].startswith('Conclusion'), repr(rd))
    js(c, 'HUB.scan.tool("reorder")')
    wait_js(c, '!!document.querySelector(".scroot .sc-pick input")')
    inject_files(c, '.scroot .sc-pick input', [(S, 'structured.pdf', 'application/pdf')])
    ok = wait_js(c, 'document.querySelectorAll(".scroot .sc-rpage").length===3', 30)
    tops = js(c, '[...document.querySelectorAll(".scroot .sc-rpage")].map(e=>{const r=e.getBoundingClientRect();return Math.round(r.top)+":"+Math.round(r.left);})') if ok else None
    distinct = isinstance(tops, list) and len(set(tops)) == 3
    check('A reorder view: 3 thumbnails laid out (not stacked)', bool(ok) and distinct, str(tops))
    if ok:
        js(c, 'document.querySelectorAll(".scroot .sc-rpage .sc-pgx")[0].click()')
        time.sleep(0.4)
        n2 = js(c, 'document.querySelectorAll(".scroot .sc-rpage").length')
        check('A reorder view: delete button removes a page', n2 == 2, str(n2))
        time.sleep(0.4)
        shot(c, 'scanfix-reorder-390-dark.png')
        js(c, 'document.querySelector(".scroot .sc-btn.sc-wide.sc-primary").click()')
        okd = wait_js(c, '!!document.querySelector(".scroot .sc-done")', 60)
        fnd = js(c, '(document.querySelector(".scroot .sc-donefn")||{}).textContent') if okd else None
        check('A reorder apply -> reordered PDF done', bool(okd) and (fnd or '').endswith('_reordered.pdf'), repr(fnd))

    # ---- matrix 14: compress ----
    cp = js(c, '''(async()=>{const mk=%s;
const b1=await mk(),b2=await mk();
const fj=async b=>{const cv=document.createElement("canvas");const bmp=await createImageBitmap(b);
cv.width=bmp.width;cv.height=bmp.height;cv.getContext("2d").drawImage(bmp,0,0);
const jb=await new Promise(r=>cv.toBlob(r,"image/jpeg",0.95));
return {bytes:new Uint8Array(await jb.arrayBuffer()),png:false};};
const big=await HUB.scan._t.imagesToPdf([await fj(b1),await fj(b2)]);
const small=await HUB.scan._t.compressPdf(big,0.3);
const h=String.fromCharCode(small[0],small[1],small[2],small[3],small[4]);
const d=await window.PDFLib.PDFDocument.load(small);
return {big:big.length,small:small.length,h:h,pages:d.getPageCount()};})()''' % DOCPHOTO,
            await_promise=True, timeout=240)
    ok14 = isinstance(cp, dict) and cp.get('h') == '%PDF-' and cp.get('pages') == 2 and cp['small'] < cp['big']
    mrow('14 Compress (smaller, valid, pages kept)',
         ok14, ('%d -> %d bytes' % (cp['big'], cp['small']) if isinstance(cp, dict) and 'big' in cp else repr(cp)))

    errs = js(c, 'window.__scanerr') or []
    check('A zero console errors', len(errs) == 0, str(errs[:5]))
    drain_net(c)
    ext = [u for u in net_urls if u.startswith('http')]
    check('A zero http(s) requests', len(ext) == 0, str(ext[:5]))
finally:
    try: c.close()
    except Exception: pass
    proc.terminate()
    shutil.rmtree(prof, ignore_errors=True)

# ---------------------------------------------------------------- run B: 390 light — Word->PDF
print('=== run B: 390 light en — Word->PDF ===')
proc, c, prof = launch('b-390-light', 390, 844, False, 'en')
try:
    wait_js(c, '!!(window.HUB&&HUB.scan&&HUB.scan._t)', 30)
    wait_js(c, '!document.getElementById("splash")', 15)
    # tile is easy to find: Convert section, Word -> PDF tile
    js(c, 'HUB.scan.studio()')
    tile = wait_js(c, '''(()=>{const ts=[...document.querySelectorAll(".sc-tile")];
const w=ts.find(t=>t.getAttribute("data-tool")==="word2pdf");
if(!w)return null;const r=w.getBoundingClientRect();return {t:r.top>=0&&r.bottom<=844};})()''', 15)
    check('B Word->PDF tile present in studio', isinstance(tile, dict), str(tile))
    dx = js(c, DOCX_BUILD, await_promise=True, timeout=120)
    js(c, 'HUB.scan.tool("word2pdf")')
    wait_js(c, '!!document.querySelector(".scroot .sc-pick input")')
    r = inject_files(c, '.scroot .sc-pick input', [(dx, 'hello.docx',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document')]) \
        if isinstance(dx, str) and len(dx) > 100 else 'no-docx'
    check('B docx injected into picker', r == 'injected:1', str(r)[:60])
    ok = wait_js(c, '!!document.querySelector(".scroot .sc-printdoc")', 60)
    prev = js(c, '(document.querySelector(".scroot .sc-printdoc")||{}).textContent') if ok else None
    check('B .docx renders in print preview', bool(ok) and 'Hello Word' in (prev or ''), repr((prev or '')[:60]))
    note = js(c, '(document.querySelector(".scroot .sc-note")||{}).textContent')
    check('B guidance has iPhone pinch steps', bool(note) and 'Pinch out' in note and 'Save to Files' in note,
          repr((note or '')[:90]))
    # print CSS targets .sc-printdoc (static file check)
    with open(os.path.expanduser('~/workspace/hub/css/scan.css')) as f:
        css = f.read()
    pm = css[css.find('@media print'):]
    check('B print CSS shows .sc-printdoc', '.sc-printdoc' in pm, '')
    # emulated print: only the doc preview is visible
    c.send('Emulation.setEmulatedMedia', {'media': 'print'})
    time.sleep(0.5)
    vis = js(c, '''(()=>{const d=document.querySelector(".scroot .sc-printdoc");
const tb=document.querySelector(".scroot .sc-topbar");
if(!d)return null;
return {doc:getComputedStyle(d).visibility,top:getComputedStyle(tb).visibility};})()''')
    check('B emulated print: only doc visible', isinstance(vis, dict) and vis['doc'] == 'visible' and vis['top'] == 'hidden', str(vis))
    c.send('Emulation.setEmulatedMedia', {'media': 'screen'})
    time.sleep(0.6)
    shot(c, 'scanfix-word2pdf-390-light.png')
    # crop view in light mode too
    js(c, 'HUB.scan.tool("scan")')
    wait_js(c, '!!document.querySelector("[data-m=take]")')
    blob_b64 = js(c, '(%s)().then(b=>new Promise(res=>{const fr=new FileReader();fr.onload=()=>res(fr.result.split(",")[1]);fr.readAsDataURL(b);}))' % DOCPHOTO, await_promise=True)
    inject_files(c, '.scroot [data-choose]', [(blob_b64, 'doc.png', 'image/png')])
    ok = wait_js(c, '!!document.querySelector(".sc-cropwrap")', 30)
    hh = js(c, 'document.querySelectorAll("circle.sc-handle").length') if ok else 0
    check('B crop view light: 4 handles', hh == 4, str(hh))
    time.sleep(1.2)
    js(c, 'document.querySelector(".sc-cropwrap").scrollIntoView({block:"center"})')
    time.sleep(0.5)
    shot(c, 'scanfix-crop-390-light.png')
    errs = js(c, 'window.__scanerr') or []
    check('B zero console errors', len(errs) == 0, str(errs[:5]))
finally:
    try: c.close()
    except Exception: pass
    proc.terminate()
    shutil.rmtree(prof, ignore_errors=True)

# ---------------------------------------------------------------- run C: 320 dark — compact
print('=== run C: 320 dark en — compact ===')
proc, c, prof = launch('c-320-dark', 320, 568, True, 'en')
try:
    wait_js(c, '!!(window.HUB&&HUB.scan&&HUB.scan._t)', 30)
    js(c, 'document.body.classList.add("dark")')
    wait_js(c, '!document.getElementById("splash")', 15)
    S = b64file('structured.pdf')
    C = b64file('cipher.pdf')
    bc = js(c, '(async()=>{try{await HUB.scan._t.pdfToWord(%s);return "NO-REJECT";}catch(e){return e&&e.code;}})()' % u8js(C),
            await_promise=True)
    check('C cipher rejected on 320px too', bc == 'BADTEXT', repr(bc))
    js(c, 'HUB.scan.tool("scan")')
    wait_js(c, '!!document.querySelector("[data-m=take]")')
    blob_b64 = js(c, '(%s)().then(b=>new Promise(res=>{const fr=new FileReader();fr.onload=()=>res(fr.result.split(",")[1]);fr.readAsDataURL(b);}))' % DOCPHOTO, await_promise=True)
    inject_files(c, '.scroot [data-choose]', [(blob_b64, 'doc.png', 'image/png')])
    ok = wait_js(c, '!!document.querySelector(".sc-cropwrap")', 30)
    ovf = js(c, 'document.documentElement.scrollWidth<=320') if ok else False
    check('C crop view fits 320px, no page overflow', bool(ok) and bool(ovf), str(ovf))
    errs = js(c, 'window.__scanerr') or []
    check('C zero console errors', len(errs) == 0, str(errs[:5]))
finally:
    try: c.close()
    except Exception: pass
    proc.terminate()
    shutil.rmtree(prof, ignore_errors=True)

print('\n==== CONVERSION MATRIX ====')
for n, ok, d in matrix:
    print(('PASS' if ok else 'FAIL'), '|', n, '|', d)
print('\n%d FAILURES' % len(fails))
sys.exit(1 if fails else 0)
