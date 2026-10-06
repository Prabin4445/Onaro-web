#!/usr/bin/env python3
"""QA: crop/filter review screen (CamScanner-pattern rewrite) + picture export + scroll fix.

Part A (node): filter quality — bw + magic (enhance) on synthetic text pages,
  clean and with a heavy side shadow: background mean luminance > 200 (clean
  white page), text mean < 110 (crisp dark ink), background speckle < 2%.
Part B (headless Chromium via CDP):
  - default view = cropped preview hero (not the raw photo); big preview is
    the warped crop filling the frame edge-to-edge (border margin < 2%);
  - filter taps update the big preview instantly and match their thumbnails;
  - Crop toggle shows the adjust view; a corner-handle drag moves the corner
    and Done re-renders the preview;
  - session pager: 1/2 -> 2/2 -> 1/2 -> trash -> 1/1;
  - picture export: JPG+PNG yield valid decodable image bytes with the
    expected dims and the selected filter baked in;
  - scroll: .sc-body keeps touch-action pan-y (scrolls on swipe) while the
    corner handles are touch-action none (drag moves the corner, no scroll);
  - zero console errors.

Usage: python3 qa/qa_cropfilter.py
Exit 0 only when every check passes.
"""
import json, os, subprocess, sys, time, urllib.request

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = '/opt/meta-chromium/chrome'
fails, passes = [], []

def check(name, ok, detail=''):
    (passes if ok else fails).append(name)
    print(('PASS ' if ok else 'FAIL ') + name + ((' — ' + str(detail)) if detail else ''))

def part_a():
    print('== Part A: filter quality (node) ==')
    drv = os.path.join(HUB, 'qa', 'cropfilter_driver.js')
    p = subprocess.run(['node', drv], capture_output=True, text=True, timeout=300)
    if p.returncode != 0:
        check('node driver runs', False, (p.stderr or '')[-300:]); return
    n = 0
    for line in p.stdout.splitlines():
        line = line.strip()
        if not line.startswith('{'):
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        n += 1
        check('quality: ' + r['name'], bool(r.get('pass')), r.get('detail', ''))
    check('node driver produced results', n > 0, '%d checks' % n)

import threading
import websocket  # websocket-client

class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=30)
        self.i = 0
        self.resp = {}
        self.events = []
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        while True:
            try:
                m = self.ws.recv()
            except Exception:
                return
            try:
                o = json.loads(m)
            except Exception:
                continue
            with self.lock:
                if 'id' in o:
                    self.resp[o['id']] = o
                else:
                    self.events.append(o)
                self.cond.notify_all()

    def call(self, method, params=None, timeout=30):
        with self.lock:
            self.i += 1
            i = self.i
        self.ws.send(json.dumps({'id': i, 'method': method, 'params': params or {}}))
        t0 = time.time()
        with self.lock:
            while i not in self.resp and time.time() - t0 < timeout:
                self.cond.wait(timeout - (time.time() - t0))
            o = self.resp.pop(i, None)
        if o is None:
            raise RuntimeError('CDP timeout: ' + method)
        if 'error' in o:
            raise RuntimeError('CDP error %s: %s' % (method, o['error']))
        return o.get('result', {})

    def ev(self, method=None, since=0):
        out = []
        with self.lock:
            for e in self.events[since:]:
                if method and e.get('method') != method:
                    continue
                out.append(e)
        return out

EVAL_JS = r"""
(function(){
  var out = {};
  try {
    var st = document.createElement('style');
    st.textContent = window.__SCAN_CSS;
    document.head.appendChild(st);
    var src = document.createElement('canvas'); src.width = 480; src.height = 360;
    var c = src.getContext('2d');
    c.fillStyle = '#5a5c60'; c.fillRect(0,0,480,360);            // desk
    c.fillStyle = '#f4f4f2'; c.fillRect(60,40,360,280);          // the paper
    c.fillStyle = '#2a2a2a';
    for (var y = 70; y < 300; y += 18) c.fillRect(80, y, 320, 5); // text lines
    c.fillStyle = '#1a56c9'; c.fillRect(60,40,360,44);            // blue header
    c.fillStyle = '#c91a1a'; c.fillRect(280,180,120,80);          // red stamp
    var quad = [{x:60,y:40},{x:420,y:40},{x:420,y:320},{x:60,y:320}];
    var body = document.createElement('div'); body.id = 'scTestBody';
    body.className = 'sc-body';
    body.style.cssText = 'height:420px;overflow-y:auto;';
    document.body.appendChild(body);
    HUB.scan._t.scanCropView(body, src, quad, 'cam');
    window.__t = { src: src, quad: quad, body: body };
    out.ok = true;
  } catch(e){ out.ok = false; out.err = String(e && e.stack || e); }
  return out;
})()
"""

CHECKS_JS = r"""
(function(){
  var T = window.__t, R = {};
  function sig(canvas){
    var t = document.createElement('canvas'); t.width = 16; t.height = 16;
    var x = t.getContext('2d'); x.drawImage(canvas, 0, 0, 16, 16);
    var d = x.getImageData(0,0,16,16).data, s = [];
    for (var i = 0; i < 256; i++) s.push(Math.round((d[i*4]+d[i*4+1]+d[i*4+2])/3));
    return s;
  }
  function sigDiff(a, b){ var acc = 0; for (var i = 0; i < 256; i++) acc += Math.abs(a[i]-b[i]); return acc/256; }
  function cornerMean(canvas){
    // the 4 canvas corners map exactly to the 4 paper corners -> must be paper, not desk
    var w = canvas.width, h = canvas.height;
    var d = canvas.getContext('2d').getImageData(0,0,w,h).data, s = 0, n = 0;
    [[3,3],[w-4,3],[3,h-4],[w-4,h-4]].forEach(function(pt){
      for (var dy = -1; dy <= 1; dy++) for (var dx = -1; dx <= 1; dx++){
        var o = ((pt[1]+dy)*w + pt[0]+dx)*4;
        s += (d[o]+d[o+1]+d[o+2])/3; n++;
      }
    });
    return s/n;
  }
  function srcQuadCornerMean(){
    // 3x3 blocks around the quad corners in the RAW photo, inset 3px so the
    // blocks sit fully inside the paper (not straddling the desk edge)
    var d = T.src.getContext('2d').getImageData(0,0,T.src.width,T.src.height).data;
    var s = 0, n = 0, cx = 240, cy = 180;
    T.quad.forEach(function(q){
      var ix = Math.round(q.x) + (q.x < cx ? 3 : -3),
          iy = Math.round(q.y) + (q.y < cy ? 3 : -3);
      for (var dy = -1; dy <= 1; dy++) for (var dx = -1; dx <= 1; dx++){
        var o = ((iy+dy)*T.src.width + ix+dx)*4;
        s += (d[o]+d[o+1]+d[o+2])/3; n++;
      }
    });
    return s/n;
  }
  var pv = T.body.querySelector('[data-prev]');
  var prevWrap = T.body.querySelector('[data-prevw]');
  var adj = T.body.querySelector('[data-adj]');
  R.defaultPreviewMode = !prevWrap.hidden && !!adj.hidden;
  R.pvW = pv.width; R.pvH = pv.height;   // warped crop: 480 x 373 (not raw 480x360)
  R.pvVsSrc = +sigDiff(sig(pv), sig(T.src)).toFixed(2);
  R.cornerMean = +cornerMean(pv).toFixed(1);  // paper corners fill the frame (margin ~0)
  R.srcCornerMean = +srcQuadCornerMean().toFixed(1);
  R.indicator = T.body.querySelector('[data-pgnum]').textContent;
  R.trashBtn = !!T.body.querySelector('[data-del]');
  R.bottomRow = ['[data-back]','[data-rot]','[data-cropbtn]','[data-apply]'].every(function(s){
    return !!T.body.querySelector(s); });
  // touch-action scoping: page scrolls, handles don't
  R.bodyTouch = getComputedStyle(T.body).touchAction;
  R.adjTouch = getComputedStyle(adj).touchAction;
  R.thumbStripTouch = getComputedStyle(T.body.querySelector('[data-thumbs]')).touchAction;
  R.handleTouch = getComputedStyle(T.body.querySelectorAll('[data-h]')[0]).touchAction;
  // filter taps: big preview must match the tapped thumbnail, instantly
  var thumbs = Array.prototype.slice.call(T.body.querySelectorAll('.sc-fthumb'));
  R.matchDiff = {}; R.pairDiff = {}; R.thumbSig = {};
  thumbs.forEach(function(b){
    var f = b.getAttribute('data-f'); R.thumbSig[f] = sig(b.querySelector('canvas'));
  });
  thumbs.forEach(function(b){
    var f = b.getAttribute('data-f'); b.click();
    R.matchDiff[f] = +sigDiff(sig(pv), R.thumbSig[f]).toFixed(2);
    R['sel_'+f] = b.classList.contains('on');
  });
  var fs = Object.keys(R.thumbSig);
  for (var a = 0; a < fs.length; a++) for (var b2 = a+1; b2 < fs.length; b2++)
    R.pairDiff[fs[a]+'/'+fs[b2]] = +sigDiff(R.thumbSig[fs[a]], R.thumbSig[fs[b2]]).toFixed(2);
  // adjust toggle: Crop -> adjust view; drag handle 0; Done -> preview re-renders
  var sigBeforeAdjust = sig(pv);
  T.body.querySelector('[data-cropbtn]').click();
  R.adjustShown = !adj.hidden && !!prevWrap.hidden;
  var h0 = T.body.querySelectorAll('[data-h]')[0];
  var r0 = h0.getBoundingClientRect(), before = h0.style.left;
  var cx = r0.left + r0.width/2, cy = r0.top + r0.height/2;
  h0.dispatchEvent(new PointerEvent('pointerdown',{clientX:cx,clientY:cy,bubbles:true,cancelable:true,pointerType:'touch'}));
  window.dispatchEvent(new PointerEvent('pointermove',{clientX:cx+40,clientY:cy+30,bubbles:true,cancelable:true,pointerType:'touch'}));
  window.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,cancelable:true,pointerType:'touch'}));
  R.dragMovedHandle = h0.style.left !== before;
  T.body.querySelector('[data-cropbtn]').click();   // Done
  R.backToPreview = !prevWrap.hidden && !!adj.hidden;
  R.previewChangedAfterDrag = sigDiff(sigBeforeAdjust, sig(pv)) > 2;
  // rotate still flips orientation in 90-degree steps
  var rb = { w: pv.width, h: pv.height };
  T.body.querySelector('[data-rot]').click();
  R.rotFlip = (rb.w > rb.h) !== (pv.width > pv.height);
  return R;
})()
"""

SESSION_JS = r"""
(function(){
  var R = {};
  try {
    function mkPhoto(light){
      var cv = document.createElement('canvas'); cv.width = 480; cv.height = 360;
      var c = cv.getContext('2d');
      c.fillStyle = '#5a5c60'; c.fillRect(0,0,480,360);
      c.fillStyle = light ? '#fbfbf8' : '#f4f4f2'; c.fillRect(60,40,360,280);
      c.fillStyle = '#222';
      for (var y = 70; y < 300; y += 18) c.fillRect(80, y, 320, 5);
      return cv;
    }
    var q = [{x:60,y:40},{x:420,y:40},{x:420,y:320},{x:60,y:320}];
    var body = document.createElement('div'); body.id = 'scSessBody';
    document.body.appendChild(body);
    var ses = HUB.scan._t.cropMkSession([{cv:mkPhoto(false),q:q},{cv:mkPhoto(true),q:q}]);
    HUB.scan._t.scanCropView(body, mkPhoto(false), q, 'lib', ses, 0);
    var pg = function(){ return body.querySelector('[data-pgnum]').textContent; };
    R.ind1 = pg();
    body.querySelector('[data-pgnext]').click(); R.ind2 = pg();
    body.querySelector('[data-pgprev]').click(); R.ind3 = pg();
    R.prevDisabledAtStart = body.querySelector('[data-pgprev]').disabled === true;
    body.querySelector('[data-pgnext]').click();
    R.nextDisabledAtEnd = body.querySelector('[data-pgnext]').disabled === true;
    body.querySelector('[data-del]').click(); R.indAfterDel = pg();
    R.ok = true;
  } catch(e){ R.ok = false; R.err = String(e && e.stack || e); }
  return R;
})()
"""

PIC_JS = r"""
(async function(){
  var T = window.__t;
  function sig(canvas){
    var t = document.createElement('canvas'); t.width = 16; t.height = 16;
    var x = t.getContext('2d'); x.drawImage(canvas, 0, 0, 16, 16);
    var d = x.getImageData(0,0,16,16).data, s = [];
    for (var i = 0; i < 256; i++) s.push(Math.round((d[i*4]+d[i*4+1]+d[i*4+2])/3));
    return s;
  }
  function sigDiff(a,b){ var acc=0; for (var i=0;i<256;i++) acc+=Math.abs(a[i]-b[i]); return acc/256; }
  function decodeInfo(f){
    return new Promise(function(res){
      var b = f.bytes;
      var magic = Array.prototype.slice.call(b.slice(0,4)).map(function(x){
        return x.toString(16).padStart(2,'0'); }).join('');
      var url = URL.createObjectURL(new Blob([b],{type:f.mime}));
      var img = new Image();
      img.onload = function(){
        var t = document.createElement('canvas'); t.width = img.naturalWidth; t.height = img.naturalHeight;
        t.getContext('2d').drawImage(img,0,0);
        res({ name:f.name, mime:f.mime, magic:magic, bytes:b.length,
              w:img.naturalWidth, h:img.naturalHeight, sig:sig(t) });
        URL.revokeObjectURL(url);
      };
      img.onerror = function(){ res({ name:f.name, err:'decode-fail' }); };
      img.src = url;
    });
  }
  var pBw = HUB.scan._t.scanMakePage(T.src, T.quad, 'bw', 'auto');
  var pMagic = HUB.scan._t.scanMakePage(T.src, T.quad, 'magic', 'auto');
  var pColor = HUB.scan._t.scanMakePage(T.src, T.quad, 'color', 'auto');
  var files = await HUB.scan._t.exportPictures([{cv:pBw},{cv:pMagic}], 'jpg');
  var pngs = await HUB.scan._t.exportPictures([{cv:pBw}], 'png');
  var infos = [];
  for (var i = 0; i < files.length; i++) infos.push(await decodeInfo(files[i]));
  infos.push(await decodeInfo(pngs[0]));
  return { infos: infos, expW: pBw.width, expH: pBw.height,
           refBwSig: sig(pBw), refColorSig: sig(pColor) };
})()
"""

def part_b():
    print('== Part B: review screen + export + scroll (headless Chromium) ==')
    prof = '/tmp/hubqa-cropfilter'
    os.makedirs(prof, exist_ok=True)
    chrome = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox',
                               '--disable-gpu', '--remote-debugging-port=9223',
                               '--user-data-dir=' + prof, 'about:blank'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws_url = None
        for _ in range(60):
            try:
                with urllib.request.urlopen('http://127.0.0.1:9223/json/list', timeout=2) as r:
                    targets = json.loads(r.read().decode())
                pages = [t for t in targets if t.get('type') == 'page']
                if pages:
                    ws_url = pages[0]['webSocketDebuggerUrl']
                    break
            except Exception:
                pass
            time.sleep(0.5)
        check('chrome debugger up', bool(ws_url))
        if not ws_url:
            return
        cdp = CDP(ws_url)
        ev0 = len(cdp.events)
        cdp.call('Runtime.enable'); cdp.call('Log.enable'); cdp.call('Page.enable')
        css = open(os.path.join(HUB, 'css', 'scan.css')).read()
        cdp.call('Runtime.evaluate', {'expression': 'window.__SCAN_CSS = %s;' % json.dumps(css)})
        src = open(os.path.join(HUB, 'js', 'scan.js')).read()
        r = cdp.call('Runtime.evaluate', {'expression': src, 'returnByValue': False})
        check('scan.js injects without exception', 'exceptionDetails' not in r,
              (r.get('exceptionDetails', {}) or {}).get('text', ''))
        r = cdp.call('Runtime.evaluate', {'expression': EVAL_JS, 'returnByValue': True})
        setup = (r.get('result') or {}).get('value') or {}
        check('cropView mounts', setup.get('ok') is True, setup.get('err', ''))
        if not setup.get('ok'):
            return
        r = cdp.call('Runtime.evaluate', {'expression': CHECKS_JS, 'returnByValue': True})
        R = (r.get('result') or {}).get('value') or {}
        check('default view is the cropped preview hero', R.get('defaultPreviewMode') is True)
        check('big preview is the warped crop, not the raw photo',
              R.get('pvW') == 480 and R.get('pvH') == 373 and (R.get('pvVsSrc') or 0) > 5,
              'pv=%sx%s diff=%s' % (R.get('pvW'), R.get('pvH'), R.get('pvVsSrc')))
        cm, scm = R.get('cornerMean') or 0, R.get('srcCornerMean') or 0
        check('paper fills the preview edge-to-edge (preview corners == paper corners, no desk margin)',
              cm > 130 and abs(cm - scm) < 20,
              'preview=%s photo=%s (desk would be ~91)' % (cm, scm))
        check('page indicator shows 1/1', R.get('indicator') == '1/1', R.get('indicator'))
        check('trash button present', R.get('trashBtn') is True)
        check('bottom row: Retake | Rotate | Crop | Use this page', R.get('bottomRow') is True)
        for f, d in (R.get('matchDiff') or {}).items():
            check('tap %s -> big preview matches its thumbnail' % f, (d if d is not None else 999) < 12,
                  'meandiff=%s' % d)
            check('tap %s selects it' % f, R.get('sel_' + f) is True)
        for pair, d in (R.get('pairDiff') or {}).items():
            check('thumbs differ: %s' % pair, (d or 0) > 1.5, 'meandiff=%s' % d)
        check('Crop toggle shows the adjust view', R.get('adjustShown') is True)
        check('corner-handle drag moves the corner', R.get('dragMovedHandle') is True)
        check('Done returns to preview with re-rendered crop', R.get('backToPreview') and R.get('previewChangedAfterDrag'))
        check('rotate flips orientation', R.get('rotFlip') is True)
        # touch-action scoping (the scroll fix)
        check('page container keeps vertical panning', (R.get('bodyTouch') or '') == 'pan-y',
              'touch-action=%s' % R.get('bodyTouch'))
        check('adjust container keeps vertical panning', (R.get('adjTouch') or '') == 'pan-y',
              'touch-action=%s' % R.get('adjTouch'))
        check('filter strip allows pan-x pan-y', (R.get('thumbStripTouch') or '') == 'pan-x pan-y',
              'touch-action=%s' % R.get('thumbStripTouch'))
        check('corner handles are touch-action none', (R.get('handleTouch') or '') == 'none',
              'touch-action=%s' % R.get('handleTouch'))
        # real swipe: scrollTop must move
        r = cdp.call('Runtime.evaluate', {'expression':
            "document.querySelector('#scTestBody').scrollTop", 'returnByValue': True})
        st0 = ((r.get('result') or {}).get('value')) or 0
        r = cdp.call('Runtime.evaluate', {'expression':
            "({st: document.querySelector('#scTestBody').scrollTop, sh: document.querySelector('#scTestBody').scrollHeight})",
            'returnByValue': True})
        sm = ((r.get('result') or {}).get('value')) or {}
        for pt in [dict(type='touchStart', touchPoints=[dict(x=400, y=330, id=1)]),
                   dict(type='touchMove', touchPoints=[dict(x=400, y=250, id=1)]),
                   dict(type='touchMove', touchPoints=[dict(x=400, y=170, id=1)]),
                   dict(type='touchEnd', touchPoints=[])]:
            cdp.call('Input.dispatchTouchEvent', pt)
            time.sleep(0.08)
        r = cdp.call('Runtime.evaluate', {'expression':
            "document.querySelector('#scTestBody').scrollTop", 'returnByValue': True})
        st1 = ((r.get('result') or {}).get('value')) or 0
        check('swipe scrolls the review screen', st1 > st0,
              'scrollTop %s -> %s (scrollHeight %s)' % (st0, st1, sm.get('sh')))
        # session pager
        r = cdp.call('Runtime.evaluate', {'expression': SESSION_JS, 'returnByValue': True})
        S = (r.get('result') or {}).get('value') or {}
        check('session pager mounts', S.get('ok') is True, S.get('err', ''))
        check('pager starts at 1/2', S.get('ind1') == '1/2', S.get('ind1'))
        check('next -> 2/2', S.get('ind2') == '2/2', S.get('ind2'))
        check('prev -> 1/2', S.get('ind3') == '1/2', S.get('ind3'))
        check('prev disabled at first page', S.get('prevDisabledAtStart') is True)
        check('next disabled at last page', S.get('nextDisabledAtEnd') is True)
        check('trash removes current capture -> 1/1', S.get('indAfterDel') == '1/1', S.get('indAfterDel'))
        # picture export
        r = cdp.call('Runtime.evaluate', {'expression': PIC_JS, 'returnByValue': True,
                                          'awaitPromise': True})
        P = (r.get('result') or {}).get('value') or {}
        infos = P.get('infos') or []
        check('picture export yields 2 JPG + 1 PNG', len(infos) == 3, 'n=%d' % len(infos))
        if len(infos) == 3:
            j1, j2, pn = infos
            for inf, nm in [(j1, 'onaro-scan-p1.jpg'), (j2, 'onaro-scan-p2.jpg')]:
                ok = (inf.get('name') == nm and (inf.get('magic') or '').startswith('ffd8')
                      and (inf.get('bytes') or 0) > 1000
                      and inf.get('w') == P.get('expW') and inf.get('h') == P.get('expH')
                      and not inf.get('err'))
                check('JPG %s valid, decodable, expected dims' % nm, ok,
                      '%s %sx%s %s bytes' % (inf.get('magic'), inf.get('w'), inf.get('h'), inf.get('bytes')))
            ok = (pn.get('name') == 'onaro-scan-p1.png' and (pn.get('magic') or '') == '89504e47'
                  and (pn.get('bytes') or 0) > 1000
                  and pn.get('w') == P.get('expW') and pn.get('h') == P.get('expH'))
            check('PNG onaro-scan-p1.png valid, decodable, expected dims', ok,
                  '%s %sx%s %s bytes' % (pn.get('magic'), pn.get('w'), pn.get('h'), pn.get('bytes')))
            def sigdiff(a, b):
                return sum(abs(x - y) for x, y in zip(a or [], b or [])) / 256.0
            d_bw = sigdiff(j1.get('sig'), P.get('refBwSig'))
            d_color = sigdiff(j1.get('sig'), P.get('refColorSig'))
            check('export has the selected filter baked in (matches bw render, not color)',
                  d_bw < 8 and d_color > 10, 'vs-bw=%.1f vs-color=%.1f' % (d_bw, d_color))
        real = []
        for e in cdp.ev(since=ev0):
            p = e.get('params', {})
            if e.get('method') == 'Log.entryAdded' and (p.get('entry') or {}).get('level') == 'error':
                real.append(str((p['entry'].get('text') or p['entry'].get('url')))[:160])
            elif e.get('method') == 'Runtime.consoleAPICalled' and p.get('type') == 'error':
                real.append('console.error called')
            elif e.get('method') == 'Runtime.exceptionThrown':
                real.append(str(p.get('exceptionDetails', {}).get('text'))[:160])
        check('zero console errors', len(real) == 0, '; '.join(real[:3]))
    finally:
        try:
            chrome.terminate()
        except Exception:
            pass

if __name__ == '__main__':
    part_a()
    part_b()
    print('\n==== %d passed, %d failed ====' % (len(passes), len(fails)))
    sys.exit(1 if fails else 0)
