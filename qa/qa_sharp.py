#!/usr/bin/env python3
"""QA: scanner output SHARPNESS at ~300 DPI (zoom-legibility).

Synthetic crisp text page (2333x3300, A4 ratio) -> real capture->warp->filter
pipeline via HUB.scan._t.scanMakePage in headless Chromium:
  - output long edge >= 3200px (300-DPI target 3300, tiered fallback)
  - sharpness (variance of Laplacian energy) of color warp >= 80% of input
  - ZOOM legibility: 2x-upscaled text region from the BW output keeps >= 80%
    of the sharpness of the same 2x zoom on the synthetic input
  - BW: background mean luminance > 200, text stays dark
  - Enhance (magic): clean background, dark text
  - perspective capture case: completes, long edge >= 2900, BW clean
  - zero console errors

Usage: python3 qa/qa_sharp.py
Exit 0 only when every check passes.
"""
import json, os, subprocess, sys, time, urllib.request

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = '/opt/meta-chromium/chrome'
fails, passes = [], []

def check(name, ok, detail=''):
    (passes if ok else fails).append(name)
    print(('PASS ' if ok else 'FAIL ') + name + ((' — ' + str(detail)) if detail else ''))

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

TEST_JS = r"""
(function(){
  var R = {};
  try {
    /* ---- synthetic SHARP text page, 2333x3300 (A4 @ ~280dpi) ---- */
    var PW = 2333, PH = 3300;
    var src = document.createElement('canvas'); src.width = PW; src.height = PH;
    var c = src.getContext('2d');
    c.fillStyle = '#ffffff'; c.fillRect(0, 0, PW, PH);
    c.fillStyle = '#111111'; c.textBaseline = 'top';
    c.font = 'bold 96px sans-serif';
    c.fillText('MANJURINAMA', 300, 200);
    c.font = '44px sans-serif';
    var y = 400, i;
    for (i = 0; i < 26; i++){ c.fillText('Crisp sample document line number ' + (i+1) + ' for sharpness.', 300, y); y += 76; }
    c.font = 'bold 56px sans-serif';
    c.fillText('TABLE OF RECORDS', 300, y + 30); y += 130;
    c.strokeStyle = '#111'; c.lineWidth = 5;
    for (var r = 0; r < 6; r++){
      c.strokeRect(300, y + r*90, 1733, 90);
      c.beginPath(); c.moveTo(1150, y + r*90); c.lineTo(1150, y + r*90 + 90); c.stroke();
    }
    c.strokeStyle = '#a00'; c.lineWidth = 10;
    c.strokeRect(1450, 2900, 550, 260);   // stamp box
    c.font = '40px sans-serif'; c.fillStyle = '#a00';
    c.fillText('STAMP', 1620, 3000);

    function sharpness(cv, rx, ry, rw, rh){
      // variance of Laplacian edge energy over a region (default: whole canvas)
      rx = rx||0; ry = ry||0; rw = rw||cv.width; rh = rh||cv.height;
      var d = cv.getContext('2d').getImageData(rx, ry, rw, rh).data;
      var n = rw*rh, sum = 0, sum2 = 0, cnt = 0, x, yy, idx;
      for (yy = 1; yy < rh-1; yy++){
        for (x = 1; x < rw-1; x++){
          idx = yy*rw + x; var o = idx*4;
          var cc = d[o]+d[o+1]+d[o+2];
          var nb = (d[o-4]+d[o-3]+d[o-2])+(d[o+4]+d[o+5]+d[o+6])+
                   (d[o-rw*4]+d[o-rw*4+1]+d[o-rw*4+2])+(d[o+rw*4]+d[o+rw*4+1]+d[o+rw*4+2]);
          var v = Math.abs(4*cc - nb);
          sum += v; sum2 += v*v; cnt++;
        }
      }
      var mean = sum/cnt; return sum2/cnt - mean*mean;
    }
    function regionMean(cv, rx, ry, rw, rh){
      var d = cv.getContext('2d').getImageData(rx, ry, rw, rh).data, s = 0, n = rw*rh;
      for (var k = 0; k < n; k++) s += (d[k*4]+d[k*4+1]+d[k*4+2])/3;
      return s/n;
    }
    function darkFrac(cv, rx, ry, rw, rh, th){
      // fraction of pixels darker than th (proves glyphs exist and are dark)
      var d = cv.getContext('2d').getImageData(rx, ry, rw, rh).data, n = rw*rh, c = 0;
      for (var k = 0; k < n; k++)
        if ((d[k*4]+d[k*4+1]+d[k*4+2])/3 < th) c++;
      return c/n;
    }
    function zoom2x(cv, rx, ry, rw, rh){
      var t = document.createElement('canvas'); t.width = rw*2; t.height = rh*2;
      var tc = t.getContext('2d');
      tc.imageSmoothingEnabled = true; tc.imageSmoothingQuality = 'high';
      tc.drawImage(cv, rx, ry, rw, rh, 0, 0, rw*2, rh*2);
      return t;
    }

    var quadFull = [{x:0,y:0},{x:PW,y:0},{x:PW,y:PH},{x:0,y:PH}];
    var t0 = performance.now();
    var outC = HUB.scan._t.scanMakePage(src, quadFull, 'color', 'a4');
    R.msColor = Math.round(performance.now() - t0);
    t0 = performance.now();
    var outB = HUB.scan._t.scanMakePage(src, quadFull, 'bw', 'a4');
    R.msBw = Math.round(performance.now() - t0);
    t0 = performance.now();
    var outM = HUB.scan._t.scanMakePage(src, quadFull, 'magic', 'a4');
    R.msMagic = Math.round(performance.now() - t0);

    R.outW = outC.width; R.outH = outC.height;
    R.outBW = outB.width; R.outBH = outB.height;
    R.longEdge = Math.max(outC.width, outC.height);

    // sharpness: same text band in input vs color-warped output
    var band = {x:280, y:380, w:1800, h:2100};
    var sx = outC.width / PW, sy = outC.height / PH;
    var sIn = sharpness(src, band.x, band.y, band.w, band.h);
    var sOut = sharpness(outC, Math.round(band.x*sx), Math.round(band.y*sy),
                         Math.round(band.w*sx), Math.round(band.h*sy));
    R.sharpIn = Math.round(sIn); R.sharpOut = Math.round(sOut);
    R.sharpRatio = +(sOut/Math.max(1, sIn)).toFixed(3);

    // ZOOM legibility: 2x upscale of a text region, output vs input
    var zr = {x:300, y:200, w:900, h:170};   // the header text
    var zIn = zoom2x(src, zr.x, zr.y, zr.w, zr.h);
    var zOut = zoom2x(outB, Math.round(zr.x*sx), Math.round(zr.y*sy),
                      Math.round(zr.w*sx), Math.round(zr.h*sy));
    var zsIn = sharpness(zIn), zsOut = sharpness(zOut);
    R.zoomIn = Math.round(zsIn); R.zoomOut = Math.round(zsOut);
    R.zoomRatio = +(zsOut/Math.max(1, zsIn)).toFixed(3);

    // BW quality: clean margin background, dark header glyphs present
    R.bwBg = +regionMean(outB, 40, 40, 160, 160).toFixed(1);
    R.bwDark = +darkFrac(outB, Math.round(300*sx), Math.round(200*sy),
                         Math.round(900*sx), Math.round(140*sy), 100).toFixed(3);
    R.magicBg = +regionMean(outM, 40, 40, 160, 160).toFixed(1);
    R.magicDark = +darkFrac(outM, Math.round(300*sx), Math.round(200*sy),
                            Math.round(900*sx), Math.round(140*sy), 110).toFixed(3);

    /* ---- perspective capture case: page drawn smaller+rotated in a photo ---- */
    var FW = 3000, FH = 3800;
    var photo = document.createElement('canvas'); photo.width = FW; photo.height = FH;
    var pc = photo.getContext('2d');
    pc.fillStyle = '#3a3b3e'; pc.fillRect(0, 0, FW, FH);   // desk
    pc.save();
    pc.translate(230, 330); pc.rotate(0.055); pc.scale(0.86, 0.86);
    pc.drawImage(src, 0, 0);
    pc.restore();
    function xf(px, py){
      // same affine the canvas used: translate(230,330) rotate(0.055) scale(0.86)
      var s = 0.86, a = 0.055, ca = Math.cos(a), sa = Math.sin(a);
      var X = px*s, Y = py*s;
      return {x: 230 + X*ca - Y*sa, y: 330 + X*sa + Y*ca};
    }
    var q2 = [xf(0,0), xf(PW,0), xf(PW,PH), xf(0,PH)];
    t0 = performance.now();
    var outP = HUB.scan._t.scanMakePage(photo, q2, 'bw', 'a4');
    R.msPersp = Math.round(performance.now() - t0);
    R.perspW = outP.width; R.perspH = outP.height;
    R.perspLong = Math.max(outP.width, outP.height);
    R.perspBg = +regionMean(outP, 30, 30, 120, 120).toFixed(1);

    R.ok = true;
  } catch(e){ R.ok = false; R.err = String((e && e.stack) || e).slice(0, 500); }
  return R;
})()
"""

def main():
    prof = '/tmp/hubqa-sharp'
    os.makedirs(prof, exist_ok=True)
    chrome = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox',
                               '--disable-gpu', '--remote-debugging-port=9224',
                               '--user-data-dir=' + prof, 'about:blank'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws_url = None
        for _ in range(60):
            try:
                with urllib.request.urlopen('http://127.0.0.1:9224/json/list', timeout=2) as r:
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
        r = cdp.call('Runtime.evaluate', {'expression': src, 'returnByValue': False}, timeout=60)
        check('scan.js injects without exception', 'exceptionDetails' not in r,
              (r.get('exceptionDetails', {}) or {}).get('text', ''))
        r = cdp.call('Runtime.evaluate', {'expression': TEST_JS, 'returnByValue': True}, timeout=300)
        R = (r.get('result') or {}).get('value') or {}
        check('pipeline completes without exceptions', R.get('ok') is True, R.get('err', ''))
        if not R.get('ok'):
            return
        le = R.get('longEdge') or 0
        check('output long edge >= 3200px (300-DPI target)', le >= 3200,
              'got %sx%s (color %sms, bw %sms, magic %sms)' % (
                  R.get('outW'), R.get('outH'), R.get('msColor'), R.get('msBw'), R.get('msMagic')))
        sr = R.get('sharpRatio') or 0
        check('warp preserves sharpness >= 80% of input', sr >= 0.8,
              'ratio=%s (in=%s out=%s)' % (sr, R.get('sharpIn'), R.get('sharpOut')))
        zr_ = R.get('zoomRatio') or 0
        check('ZOOM legibility: 2x text region keeps >= 80% of input zoom sharpness', zr_ >= 0.8,
              'ratio=%s (in=%s out=%s)' % (zr_, R.get('zoomIn'), R.get('zoomOut')))
        check('BW background clean (> 200)', (R.get('bwBg') or 0) > 200, 'bg=%s' % R.get('bwBg'))
        check('BW keeps dark glyphs (> 3% pixels < 100 in header)', (R.get('bwDark') or 0) > 0.03,
              'darkfrac=%s' % R.get('bwDark'))
        check('Enhance background clean (> 190)', (R.get('magicBg') or 0) > 190, 'bg=%s' % R.get('magicBg'))
        check('Enhance keeps dark glyphs (> 3% pixels < 110 in header)', (R.get('magicDark') or 0) > 0.03,
              'darkfrac=%s' % R.get('magicDark'))
        pl = R.get('perspLong') or 0
        check('perspective capture: long edge >= 2900px', pl >= 2900,
              'got %sx%s in %sms' % (R.get('perspW'), R.get('perspH'), R.get('msPersp')))
        check('perspective capture: BW background clean (> 200)', (R.get('perspBg') or 0) > 200,
              'bg=%s' % R.get('perspBg'))
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
    main()
    print('\n==== %d passed, %d failed ====' % (len(passes), len(fails)))
    sys.exit(1 if fails else 0)
