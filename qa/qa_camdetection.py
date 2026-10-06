#!/usr/bin/env python3
"""QA: Student Scanner live paper detection + CamScanner-style crop screen.

Part A (node): synthetic frames through CV.detectLive — paper lock accuracy
  (IoU vs ground truth), no wild quads on textured backgrounds, guide fallback,
  temporal stability, legacy still-photo path intact, per-frame perf budget.
Part B (headless Chromium via CDP): the crop/adjust screen —
  4 live filter thumbnails (each visibly different, each matching the big
  preview when tapped), Retake returns to the live viewfinder, Rotate flips
  orientation in 90-degree steps, zero console errors.

Usage: python3 qa/qa_camdetection.py
Exit 0 only when every check passes.
"""
import json, os, subprocess, sys, time, urllib.request

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = '/opt/meta-chromium/chrome'
fails, passes = [], []

def check(name, ok, detail=''):
    (passes if ok else fails).append(name)
    print(('PASS ' if ok else 'FAIL ') + name + ((' — ' + str(detail)) if detail else ''))

# ---------------- Part A: node detection driver ----------------
def part_a():
    print('== Part A: live paper detection (node) ==')
    drv = os.path.join(HUB, 'qa', 'camdet_driver.js')
    p = subprocess.run(['node', drv], capture_output=True, text=True, timeout=300)
    if p.returncode != 0:
        check('node driver runs', False, (p.stderr or '')[-300:])
        return
    n = 0
    for line in p.stdout.splitlines():
        line = line.strip()
        if not line.startswith('{'):
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if 'fatal' in r:
            check('node driver fatal', False, r['fatal']); return
        n += 1
        check('det: ' + r['name'], bool(r.get('pass')), r.get('detail', ''))
    check('node driver produced results', n > 0, '%d checks' % n)

# ---------------- Part B: CDP DOM tests ----------------
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

    def ev(self, method=None, text=None, since=0):
        out = []
        with self.lock:
            for e in self.events[since:]:
                if method and e.get('method') != method:
                    continue
                if text and text not in json.dumps(e):
                    continue
                out.append(e)
        return out

EVAL_JS = r"""
(function(){
  var out = {};
  try {
    // build a synthetic "photo": gray desk, white paper with text lines
    var src = document.createElement('canvas'); src.width = 480; src.height = 360;
    var c = src.getContext('2d');
    c.fillStyle = '#5a5c60'; c.fillRect(0,0,480,360);
    c.fillStyle = '#f4f4f2'; c.fillRect(60,40,360,280);       // the paper
    c.fillStyle = '#2a2a2a';
    for (var y = 70; y < 300; y += 18) c.fillRect(80, y, 320, 5); // text lines
    c.fillStyle = '#1a56c9'; c.fillRect(60,40,360,44);          // blue header band
    c.fillStyle = '#c91a1a'; c.fillRect(280,180,120,80);          // a red stamp
    c.fillStyle = '#8a8f96'; c.fillRect(300,300,60,14);        // a gray stamp
    var quad = [{x:60,y:40},{x:420,y:40},{x:420,y:320},{x:60,y:320}];
    var body = document.createElement('div'); body.id = 'scTestBody';
    document.body.appendChild(body);
    window.__t = { src: src, quad: quad, body: body };
    HUB.scan._t.scanCropView(body, src, quad, 'cam');
    out.ok = true;
  } catch(e){ out.ok = false; out.err = String(e && e.stack || e); }
  return out;
})()
"""

CHECKS_JS = r"""
(function(){
  var T = window.__t, R = {};
  function sig(canvas){ // 16x16 gray signature of a canvas
    var t = document.createElement('canvas'); t.width = 16; t.height = 16;
    var x = t.getContext('2d'); x.drawImage(canvas, 0, 0, 16, 16);
    var d = x.getImageData(0,0,16,16).data, s = [];
    for (var i = 0; i < 256; i++) s.push(Math.round((d[i*4]+d[i*4+1]+d[i*4+2])/3));
    return s;
  }
  function nonblank(canvas){
    var d = canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
    var mn = 255, mx = 0;
    for (var i = 0; i < d.length; i += 16){ var v = d[i]; if(v<mn)mn=v; if(v>mx)mx=v; }
    return mx - mn;
  }
  var thumbs = Array.prototype.slice.call(T.body.querySelectorAll('.sc-fthumb'));
  R.nThumbs = thumbs.length;
  R.thumbSig = {}; R.thumbRange = {};
  thumbs.forEach(function(b){
    var f = b.getAttribute('data-f'), cv = b.querySelector('canvas');
    R.thumbSig[f] = sig(cv); R.thumbRange[f] = nonblank(cv);
  });
  // tap each thumbnail; big preview must then match that filter's rendering
  R.matchDiff = {}; R.bigSigAfter = {};
  var pv = T.body.querySelector('[data-prev]');
  thumbs.forEach(function(b){
    var f = b.getAttribute('data-f');
    b.click();
    var ps = sig(pv), ts = R.thumbSig[f], acc = 0;
    for (var i = 0; i < 256; i++) acc += Math.abs(ps[i]-ts[i]);
    R.matchDiff[f] = +(acc/256).toFixed(2);
    R.bigSigAfter[f] = ps;
    R['sel_'+f] = b.classList.contains('on');
  });
  // pairwise thumbnail differences (they must visibly differ)
  R.pairDiff = {};
  var fs = Object.keys(R.thumbSig);
  for (var a = 0; a < fs.length; a++) for (var b2 = a+1; b2 < fs.length; b2++){
    var acc2 = 0;
    for (var i = 0; i < 256; i++) acc2 += Math.abs(R.thumbSig[fs[a]][i]-R.thumbSig[fs[b2]][i]);
    R.pairDiff[fs[a]+'/'+fs[b2]] = +(acc2/256).toFixed(2);
  }
  // rotate: orientation must flip
  var before = { w: pv.width, h: pv.height };
  T.body.querySelector('[data-rot]').click();
  R.rotBefore = before; R.rotAfter = { w: pv.width, h: pv.height };
  R.rotFlip = (before.w > before.h) !== (pv.width > pv.height);
  return R;
})()
"""

RETAKE_JS = r"""
(function(){
  var R = {};
  try {
    // fake camera: resolve an empty MediaStream so camView mounts its DOM
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: function(){ return Promise.resolve(new MediaStream()); } },
      configurable: true
    });
    var T = window.__t;
    var body2 = document.createElement('div'); body2.id = 'scTestBody2';
    document.body.appendChild(body2);
    HUB.scan._t.scanCropView(body2, T.src, T.quad, 'cam');
    body2.querySelector('[data-back]').click();
    R.backLabel = body2.querySelector('[data-back]') ? 'gone' : 'n/a';
    R.camwrap = !!document.querySelector('#scTestBody2 .sc-camwrap');
    R.video = !!document.querySelector('#scTestBody2 video[data-vid]');
    R.ok = true;
  } catch(e){ R.ok = false; R.err = String(e && e.stack || e); }
  return R;
})()
"""

def part_b():
    print('== Part B: crop screen DOM (headless Chromium) ==')
    prof = '/tmp/hubqa-camdet'
    os.makedirs(prof, exist_ok=True)
    chrome = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox',
                               '--disable-gpu', '--remote-debugging-port=9222',
                               '--user-data-dir=' + prof, 'about:blank'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # wait for the debugger endpoint
        ws_url = None
        for _ in range(60):
            try:
                with urllib.request.urlopen('http://127.0.0.1:9222/json/list', timeout=2) as r:
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
        check('4 filter thumbnails', R.get('nThumbs') == 4, 'n=%s' % R.get('nThumbs'))
        for f, rng in (R.get('thumbRange') or {}).items():
            check('thumb %s renders content' % f, (rng or 0) > 20, 'range=%s' % rng)
        for pair, d in (R.get('pairDiff') or {}).items():
            check('thumbs differ: %s' % pair, (d or 0) > 1.5, 'meandiff=%s' % d)
        for f, d in (R.get('matchDiff') or {}).items():
            check('tap %s -> big preview matches thumb' % f, (d if d is not None else 999) < 12,
                  'meandiff=%s' % d)
            check('tap %s selects it' % f, R.get('sel_' + f) is True)
        rb, ra = R.get('rotBefore') or {}, R.get('rotAfter') or {}
        check('rotate flips orientation', R.get('rotFlip') is True,
              '%sx%s -> %sx%s' % (rb.get('w'), rb.get('h'), ra.get('w'), ra.get('h')))
        r = cdp.call('Runtime.evaluate', {'expression': RETAKE_JS, 'returnByValue': True})
        R2 = (r.get('result') or {}).get('value') or {}
        check('retake mounts without exception', R2.get('ok') is True, R2.get('err', ''))
        check('retake returns to live viewfinder', R2.get('camwrap') and R2.get('video'),
              'camwrap=%s video=%s' % (R2.get('camwrap'), R2.get('video')))
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
