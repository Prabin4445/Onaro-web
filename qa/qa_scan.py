#!/usr/bin/env python3
"""QA: Student Scanner (js/scan.js + css/scan.css).

Card placement (DAILY directly above Gym Fuel), 14 labeled tiles, scan flow
(capture -> crop quad + filters -> pages -> PDF bytes), all conversions via the
real ENG engines, IDB persistence across reload, zero http(s) requests,
390+320px, dark+light, en+ne, zero console errors, screenshots.
"""
import json, subprocess, time, urllib.request, os, sys, base64, shutil, re, zipfile
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
os.makedirs(QA, exist_ok=True)
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
    prof = '/tmp/hubqa-scan-' + re.sub(r'[^a-z0-9]+', '-', name)
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
    return proc, c

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

def net_ok(n):
    drain_net(None) if False else None
    return True

# ---------- shared JS snippets ----------
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

def inject_files(c, input_sel, blobs):
    """blobs: list of (b64, name, mime) -> sets input.files via DataTransfer"""
    items = []
    for b64, name, mime in blobs:
        items.append((b64, name, mime))
    expr = ('(async()=>{const inp=document.querySelector(%s);if(!inp)return "no-input";'
            'const dt=new DataTransfer();' % json.dumps(input_sel))
    for b64, name, mime in items:
        expr += ('{const bin=atob(%s);const u=new Uint8Array(bin.length);'
                 'for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);'
                 'dt.items.add(new File([u],%s,{type:%s}));}' % (json.dumps(b64), json.dumps(name), json.dumps(mime)))
    expr += ('const n=dt.files.length;'
             'inp.files=dt.files;inp.dispatchEvent(new Event("change",{bubbles:true}));'
             'return "injected:"+n;})()')
    return js(c, expr, await_promise=True)

def run_config(name, w, h, dark, lang, full):
    global net_urls
    net_urls = []
    proc, c = launch(name, w, h, dark, lang)
    try:
        ok = wait_js(c, '!!(window.HUB&&HUB.scan&&HUB.scan._t)', 30)
        check(f'[{name}] app booted, HUB.scan present', bool(ok))
        if not ok: return
        js(c, 'document.body.classList.toggle("dark",%s)' % ('true' if dark else 'false'))
        def card_visible():
            return js(c, '''(()=>{const v=document.getElementById("view-daily");
              const s=document.querySelector("[data-scan-card]");
              if(!v||v.hidden||!s)return false;
              return s.getBoundingClientRect().height>0;})()''')
        js(c, 'HUB.showTab("daily")')
        ok = None
        t0 = time.time()
        while time.time() - t0 < 30:
            if card_visible(): ok = True; break
            js(c, 'HUB.showTab("daily")')  # re-issue: boot may not have finished on the first call
            time.sleep(1.5)
        check(f'[{name}] scanner card rendered in DAILY', bool(ok))
        if not ok: return

        pos = js(c, '''(()=>{const s=document.querySelector("[data-scan-card]");
          const g=document.querySelector(".gy-hero");
          if(!s||!g)return "missing";
          const a=s.getBoundingClientRect(),b=g.getBoundingClientRect();
          if(a.height===0||b.height===0)return "noloayout";
          return {above:a.bottom<=b.top+2, st:a.top, sb:a.bottom, gt:b.top};})()''')
        if pos == 'noloayout':  # render race: layout not settled yet, poll briefly
            pos = wait_js(c, '''(()=>{const s=document.querySelector("[data-scan-card]");
              const g=document.querySelector(".gy-hero");if(!s||!g)return null;
              const a=s.getBoundingClientRect(),b=g.getBoundingClientRect();
              if(a.height===0||b.height===0)return null;
              return {above:a.bottom<=b.top+2, st:a.top, sb:a.bottom, gt:b.top};})()''', 15)
        check(f'[{name}] card directly ABOVE Gym Fuel', isinstance(pos, dict) and bool(pos['above']), str(pos))

        title = js(c, 'document.querySelector("[data-scan-card] .sc-cardtitle").textContent')
        exp_title = {'en': 'Student Scanner', 'ne': 'विद्यार्थी स्क्यानर'}[lang]
        check(f'[{name}] card title localized', title == exp_title, repr(title))

        quicks = js(c, '''[...document.querySelectorAll("[data-scan-card] .sc-qbtn")].map(b=>b.textContent.trim())''')
        check(f'[{name}] 4 quick actions labeled', isinstance(quicks, list) and len(quicks) == 4 and all(quicks),
              str(quicks))
        openbtn = js(c, '!!document.querySelector("[data-scan-card] .sc-open")')
        check(f'[{name}] Open Studio button', bool(openbtn))
        offl = js(c, 'document.querySelector("[data-scan-card] .sc-offline").textContent')
        check(f'[{name}] offline label ("on this device")', bool(offl) and 'device' in offl.lower() or 'डिभाइस' in (offl or ''),
              repr((offl or '')[:60]))
        # wait for the splash overlay to be gone before screenshotting the card
        wait_js(c, '!document.getElementById("splash")', 15)
        js(c, 'document.querySelector("[data-scan-card]").scrollIntoView({block:"center"})')
        time.sleep(0.6)
        shot(c, f'scan-card-{w}-{"dark" if dark else "light"}-{lang}.png')

        if not full:
            errs = js(c, 'window.__scanerr') or []
            check(f'[{name}] zero console errors', len(errs) == 0, str(errs[:3]))
            drain_net(c)
            ext = [u for u in net_urls if u.startswith('http')]
            check(f'[{name}] zero http(s) requests', len(ext) == 0, str(ext[:3]))
            return

        # ---------- studio: 14 labeled tiles ----------
        js(c, 'HUB.scan.studio()')
        ok = wait_js(c, 'document.querySelectorAll(".sc-tile").length===14')
        check('[full] studio shows 14 tiles', bool(ok),
              str(js(c, 'document.querySelectorAll(".sc-tile").length')))
        tiles = js(c, '''[...document.querySelectorAll(".sc-tile")].map(b=>({
          t:b.querySelector(".sc-tiletx").textContent.trim(),
          d:b.querySelector(".sc-tiledesc").textContent.trim(),
          n:b.querySelector(".sc-tilenote")?b.querySelector(".sc-tilenote").textContent.trim():""}))''')
        check('[full] every tile has title+desc', all(x['t'] and x['d'] for x in tiles),
              str([x['t'] for x in tiles]))
        notes = [x for x in tiles if x['n']]
        check('[full] honest notes on complex-layout tiles', len(notes) >= 3,
              str([x['t'] for x in notes]))
        secs = js(c, '[...document.querySelectorAll(".sc-sect")].map(s=>s.textContent.trim())')
        check('[full] 4 labeled sections + files', isinstance(secs, list) and len(secs) == 5, str(secs))
        clay = js(c, '''[...document.querySelectorAll(".sc-tile-ic img")].length''')
        check('[full] tiles render clay icons (no emoji fallback)', clay == 14, str(clay))
        cols = js(c, '''(()=>{const g=document.querySelector(".sc-grid");if(!g)return 0;
          const r=g.getBoundingClientRect();const t=g.querySelector(".sc-tile").getBoundingClientRect();
          return Math.max(1,Math.round(r.width/t.width));})()''')
        check('[full] tiles in a 2-col grid (390px)', cols == 2, str(cols))
        time.sleep(0.8)  # let entrance animations settle
        shot(c, 'scan-studio-390-dark-en.png')

        # ---------- scan flow ----------
        js(c, 'HUB.scan.tool("scan")')
        ok = wait_js(c, 'document.querySelectorAll(".sc-cropwrap").length===0 && !!document.querySelector("[data-m=take]")')
        check('[full] scan flow: 3 capture buttons', bool(ok))
        blob_b64 = js(c, '(%s)().then(b=>new Promise(res=>{const fr=new FileReader();fr.onload=()=>res(fr.result.split(",")[1]);fr.readAsDataURL(b);}))' % DOCPHOTO, await_promise=True)
        check('[full] synthetic doc photo generated', isinstance(blob_b64, str) and len(blob_b64) > 1000)
        r = inject_files(c, '.scroot [data-choose]', [(blob_b64, 'doc.png', 'image/png')])
        check('[full] photo injected into picker', r == 'injected:1', str(r))
        ok = wait_js(c, '!!document.querySelector(".sc-cropwrap")', 30)
        check('[full] crop view rendered', bool(ok))
        if ok:
            handles = js(c, 'document.querySelectorAll(".sc-handle").length')
            check('[full] 4 draggable corner handles', handles == 4, str(handles))
            quad = js(c, 'document.querySelector(".sc-quad")!==null')
            check('[full] detected quad overlay', bool(quad))
            fb = js(c, '[...document.querySelectorAll(".sc-fbtn")].map(b=>b.textContent.trim())')
            check('[full] 4 filters (color/gray/B&W/magic)', isinstance(fb, list) and len(fb) == 4, str(fb))
            js(c, 'document.querySelector("[data-f=bw]").click()')
            shot(c, 'scan-crop-390-dark-en.png')
            # capture the exported PDF blob
            js(c, 'window.__cap=[];const _c=URL.createObjectURL.bind(URL);URL.createObjectURL=function(b){window.__cap.push(b);return _c(b);};')
            js(c, 'document.querySelector("[data-apply]").click()')
            ok = wait_js(c, 'document.querySelectorAll(".sc-page").length===1')
            check('[full] page added to multi-page view', bool(ok))
            shot(c, 'scan-pages-390-dark-en.png')
            js(c, 'document.querySelector("[data-exp]").click()')
            ok = wait_js(c, '!!document.querySelector(".sc-done")', 30)
            check('[full] scan exported -> done block', bool(ok))
            pdfhead = js(c, '''(async()=>{const b=window.__cap[window.__cap.length-1];
              const u=new Uint8Array(await b.arrayBuffer());
              return String.fromCharCode(u[0],u[1],u[2],u[3],u[4]);})()''', await_promise=True)
            check('[full] exported scan is a real PDF (%PDF-)', pdfhead == '%PDF-', repr(pdfhead))

        # ---------- conversions via real engines ----------
        with open('/tmp/scan-qa/structured.pdf', 'rb') as f:
            pdfb64 = base64.b64encode(f.read()).decode()

        imgs = js(c, '(async()=>{const bin=atob(%s);const u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);'
                     'const a=await HUB.scan._t.pdfToImages(u,1.5,"image/png");'
                     'return a.length;})()' % json.dumps(pdfb64), await_promise=True)
        check('[full] PDF->images: 3 PNGs', imgs == 3, str(imgs))

        wres = js(c, '(async()=>{const bin=atob(%s);const u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);'
                     'const bl=await HUB.scan._t.pdfToWord(u);const ab=new Uint8Array(await bl.arrayBuffer());'
                     'return {h:String.fromCharCode(ab[0],ab[1]),n:ab.length};})()' % json.dumps(pdfb64), await_promise=True)
        check('[full] PDF->Word: PK zip', isinstance(wres, dict) and wres.get('h') == 'PK', str(wres))

        tres = js(c, '(async()=>{const bin=atob(%s);const u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);'
                     'const t=await HUB.scan._t.pdfText(u);return t.length+"|"+t[0].slice(0,20);})()' % json.dumps(pdfb64), await_promise=True)
        check('[full] PDF->Text extracts', isinstance(tres, str) and tres.startswith('3|Photosynthesis'), repr(tres)[:60])

        # merge
        mres = js(c, '(async()=>{const bin=atob(%s);const u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);'
                     'const m=await HUB.scan._t.mergePdfs([u,u]);'
                     'const ps=await HUB.scan._t.pdfPageItems(m);return ps.length;})()' % json.dumps(pdfb64), await_promise=True)
        check('[full] merge: 3+3=6 pages', mres == 6, str(mres))

        # split
        sres = js(c, '(async()=>{const bin=atob(%s);const u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);'
                     'const outs=await HUB.scan._t.splitPdf(u,[[1,2],[3]]);'
                     'const a=await HUB.scan._t.pdfPageItems(outs[0]);const b=await HUB.scan._t.pdfPageItems(outs[1]);'
                     'return [outs.length,a.length,b.length];})()' % json.dumps(pdfb64), await_promise=True)
        check('[full] split [1,2],[3] -> 2+1 pages', sres == [2, 2, 1], str(sres))
        pr = js(c, 'HUB.scan._t.parseRanges("1-3,5",6)')
        check('[full] parseRanges("1-3,5",6)', pr == [1, 2, 3, 5], str(pr))

        # rotate — verify via pdf-lib round-trip (output uses object streams, so no raw /Rotate text)
        rres = js(c, '(async()=>{try{const bin=atob(%s);const u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);'
                     'const r=await HUB.scan._t.rotatePdf(u,90);'
                     'const {PDFDocument}=window.PDFLib;'
                     'const d=await PDFDocument.load(r);'
                     'return d.getPages().map(p=>p.getRotation().angle);'
                     '}catch(e){return {err:String(e).slice(0,200)};}})()' % json.dumps(pdfb64), await_promise=True)
        check('[full] rotate: all pages report 90deg', rres == [90, 90, 90], str(rres))

        # reorder
        ores = js(c, '(async()=>{const bin=atob(%s);const u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);'
                     'const r=await HUB.scan._t.reorderPdf(u,[3,2,1]);'
                     'const t=await HUB.scan._t.pdfText(r);return t[0].slice(0,10);})()' % json.dumps(pdfb64), await_promise=True)
        check('[full] reorder [3,2,1]: page3 first', isinstance(ores, str) and ores.startswith('Conclusion'), repr(ores)[:30])

        # compress (image-heavy PDF shrinks); capture bigLen BEFORE compress (pdf.js neuters the input buffer)
        cres = js(c, '(async()=>{try{const bin=atob(%s);const u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);'
                     'const imgs=await HUB.scan._t.pdfToImages(u,1.5,"image/png");'
                     'const frs=await Promise.all(imgs.map(async p=>{const bl=new Blob([p],{type:"image/png"});'
                     'const cv=document.createElement("canvas");const bmp=await createImageBitmap(bl);'
                     'cv.width=bmp.width;cv.height=bmp.height;cv.getContext("2d").drawImage(bmp,0,0);'
                     'const jb=await new Promise(r=>cv.toBlob(r,"image/jpeg",0.9));'
                     'return {bytes:new Uint8Array(await jb.arrayBuffer()),png:false};}));'
                     'const big=await HUB.scan._t.imagesToPdf(frs);const bigLen=big.length;'
                     'const small=await HUB.scan._t.compressPdf(big,0.3);'
                     'return {big:bigLen,small:small.length};'
                     '}catch(e){return {err:String(e&&e.stack||e).slice(0,300)};}})()' % json.dumps(pdfb64),
                  await_promise=True, timeout=240)
        check('[full] compress shrinks PDF',
              isinstance(cres, dict) and 'small' in cres and cres['small'] < cres['big'], str(cres))

        # image convert both ways
        vres = js(c, '(async()=>{const b=await (%s)();'
                     'const j=await HUB.scan._t.convertImage(new Uint8Array(await b.arrayBuffer()),"image/jpeg",0.9);'
                     'const p=await HUB.scan._t.convertImage(j.bytes,"image/png");'
                     'return [j.bytes[0],j.bytes[1],p.bytes[0],p.bytes[1],p.bytes[2]];})()' % DOCPHOTO, await_promise=True)
        check('[full] PNG->JPG (FFD8) ->PNG (89504E)', vres == [255, 216, 137, 80, 78], str(vres))

        # heic -> jpg
        with open('/tmp/scan-qa/sample.heic', 'rb') as f:
            heicb64 = base64.b64encode(f.read()).decode()
        hres = js(c, '(async()=>{const bin=atob(%s);const u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);'
                     'const j=await HUB.scan._t.heicToJpg(u);return [j[0],j[1],j[2]];})()' % json.dumps(heicb64), await_promise=True)
        check('[full] HEIC->JPG real sample (FFD8)', hres == [255, 216, 255], str(hres))

        # pdf -> excel
        xres = js(c, '(async()=>{const bin=atob(%s);const u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);'
                     'const x=await HUB.scan._t.pdfToExcel(u);const b=new Uint8Array(x);'
                     'return [String.fromCharCode(b[0],b[1]),b.length];})()' % json.dumps(pdfb64), await_promise=True)
        check('[full] PDF->Excel: valid xlsx (PK)', isinstance(xres, list) and xres[0] == 'PK' and xres[1] > 1000, str(xres))

        # word -> html (build a docx in-page with the vendored lib)
        w2h = js(c, '''(async()=>{
          if(!window.docx){await new Promise((res,rej)=>{const s=document.createElement("script");
            s.src="vendor/docx.umd.js";s.onload=res;s.onerror=()=>rej(new Error("lib"));document.head.appendChild(s);});}
          const D=window.docx;
          const doc=new D.Document({sections:[{children:[new D.Paragraph({heading:D.HeadingLevel.HEADING_1,
            children:[new D.TextRun("Hello Word")]}),new D.Paragraph("plain para")]}]});
          const blob=await D.Packer.toBlob(doc);
          const u=new Uint8Array(await blob.arrayBuffer());
          const html=await HUB.scan._t.wordToHtml(u);
          return html.indexOf("Hello Word")>=0&&html.indexOf("plain para")>=0;})()''', await_promise=True)
        check('[full] Word->HTML via mammoth', w2h is True, str(w2h))

        # pdf2word via the VIEW (wiring incl. IDB save) — generic pick view uses .sc-pick input
        js(c, 'HUB.scan.tool("pdf2word")')
        ok = wait_js(c, '!!document.querySelector(".scroot .sc-pick input")')
        check('[full] pdf2word VIEW: file picker shown', bool(ok))
        r = inject_files(c, '.scroot .sc-pick input', [(pdfb64, 'structured.pdf', 'application/pdf')])
        check('[full] pdf2word VIEW: pdf injected', r == 'injected:1', str(r))
        ok = wait_js(c, '!!document.querySelector(".sc-done")', 60)
        fn = js(c, '(document.querySelector(".sc-donefn")||{}).textContent') if ok else None
        check('[full] pdf2word VIEW -> .docx done block', bool(ok) and (fn or '').endswith('.docx'), repr(fn))

        # ---------- IDB persistence across reload ----------
        js(c, 'HUB.scan.studio()')
        ok = wait_js(c, 'document.querySelectorAll(".sc-filerow").length>=1')
        check('[full] studio file list shows saved files', bool(ok),
              str(js(c, 'document.querySelectorAll(".sc-filerow").length')))
        nfiles = js(c, 'document.querySelectorAll(".sc-filerow").length')
        c.send('Page.reload')
        wait_js(c, 'document.readyState==="complete"', 30)
        wait_js(c, '!!(window.HUB&&HUB.scan)', 30)
        js(c, 'HUB.showTab("daily")')
        wait_js(c, '!!document.querySelector("[data-scan-card]")')
        js(c, 'HUB.scan.studio()')
        nfiles2 = wait_js(c, 'document.querySelectorAll(".sc-filerow").length>=%d' % nfiles)
        check('[full] files persist across reload (IndexedDB)', bool(nfiles2))

        errs = js(c, 'window.__scanerr') or []
        check('[full] zero console errors', len(errs) == 0, str(errs[:5]))
        drain_net(c)
        ext = [u for u in net_urls if u.startswith('http')]
        check('[full] zero http(s) requests all run', len(ext) == 0, str(ext[:5]))
    finally:
        try: c.close()
        except Exception: pass
        proc.terminate()

print('=== config: 390 dark en (full) ===')
run_config('full-390-dark-en', 390, 844, True, 'en', True)
print('=== config: 320 light en ===')
run_config('cfg-320-light-en', 320, 568, False, 'en', False)
print('=== config: 390 dark ne ===')
run_config('cfg-390-dark-ne', 390, 844, True, 'ne', False)
print('\n%d FAILURES' % len(fails))
sys.exit(1 if fails else 0)
