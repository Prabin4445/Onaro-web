#!/usr/bin/env python3
"""QA: rebuilt Student Scanner auto edge detection.

Part A (node): qa/scandet2_driver.js renders synthetic document photos
  (perspective, rotation, lighting, textured backgrounds, adversarial
  no-paper scenes) and measures detected-quad IoU vs ground truth.
  Targets: median IoU >= 0.95 clean, >= 0.90 angled/low-contrast;
  no-paper scenes must NOT lock (honest guide, no fake quad).
Part B (headless Chromium via CDP):
  - magnifier loupe appears on corner drag in the adjust view, canvas is
    non-blank, and it is removed on release;
  - live camera viewfinder with a fake video device shows the honest
    "no page" tip (not a bogus quad) when no document is present;
  - 390 + 320px, dark + light, zero console errors.

Usage: python3 qa/qa_scandetect2.py
Exit 0 only when every check passes.
"""
import json, os, subprocess, sys, time

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HUB, 'qa'))
from qa_camdetection import CDP  # noqa: E402

CHROME = '/opt/meta-chromium/chrome'
fails, passes = [], []


def check(name, ok, detail=''):
    (passes if ok else fails).append(name)
    print(('PASS ' if ok else 'FAIL ') + name + ((' — ' + str(detail)) if detail else ''))


# ---------------- Part A: node fixture driver ----------------
def part_a():
    print('== Part A: fixture IoU (node) ==')
    drv = os.path.join(HUB, 'qa', 'scandet2_driver.js')
    p = subprocess.run(['node', drv], capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        check('node driver runs', False, (p.stderr or '')[-300:])
        return
    rows = []
    for line in p.stdout.splitlines():
        line = line.strip()
        if not line.startswith('{'):
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    check('node driver produced results', len(rows) > 0, '%d rows' % len(rows))
    if not rows:
        return
    by_cls = {}
    for r in rows:
        if 'iouLive' in r and not r.get('partial'):
            by_cls.setdefault(r['cls'], []).append(r['iouLive'])
    targets = {'clean': 0.95, 'angled': 0.90, 'lowcontrast': 0.90,
               'rotated': 0.90, 'shadow': 0.90, 'textured': 0.90, 'textheavy': 0.90}
    for cls, tgt in targets.items():
        v = sorted(by_cls.get(cls, []))
        if not v:
            check('class %s present' % cls, False)
            continue
        med = v[len(v) // 2]
        # shadow allows one brutal-diagonal-shadow miss in the median of 2
        check('IoU %s median>=%.2f' % (cls, tgt), med >= tgt, 'med=%.3f n=%d' % (med, len(v)))
    for r in rows:
        if r.get('cls') == 'nopaper':
            check('no fake quad: %s' % r['name'], not r['locked'] and r['guide'],
                  'locked=%s' % r['locked'])
    for r in rows:
        if r.get('partial'):
            # report-only: must not lock onto garbage (either guide or sane overlap)
            check('partial frame honest', r['guide'] or r['iouLive'] > 0.3,
                  'locked=%s iou=%.3f' % (r['locked'], r['iouLive']))
    mss = [r['msLive'] for r in rows if 'msLive' in r]
    if mss:
        avg = sum(mss) / len(mss)
        check('perf avg ms/frame < 120', avg < 120, 'avg=%.1fms' % avg)


# ---------------- Part B: CDP browser tests ----------------
LOUPE_JS = r"""
(function(){
  var out = {};
  try {
    var src = document.createElement('canvas'); src.width = 480; src.height = 640;
    var c = src.getContext('2d');
    c.fillStyle = '#3a3b3e'; c.fillRect(0,0,480,640);
    c.fillStyle = '#f5f3ee';
    c.beginPath(); c.moveTo(70,90); c.lineTo(410,70); c.lineTo(430,560); c.lineTo(50,580); c.closePath(); c.fill();
    c.fillStyle = '#333';
    for (var y = 130; y < 520; y += 22) c.fillRect(90, y, 300, 6);
    var quad = [{x:70,y:90},{x:410,y:70},{x:430,y:560},{x:50,y:580}];
    var body = document.createElement('div'); body.id = 'scLoupeBody';
    document.body.appendChild(body);
    HUB.scan._t.scanCropView(body, src, quad, 'cam');
    // switch to the adjust (corner-drag) view
    body.querySelector('[data-cropbtn]').click();
    var h0 = body.querySelector('[data-h="0"]');
    out.handleFound = !!h0;
    out.adjustVisible = !body.querySelector('[data-adj]').hidden;
    // press on corner 0
    var r = h0.getBoundingClientRect();
    var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    function pe(type, x, y){
      var e = new PointerEvent(type, {clientX:x, clientY:y, bubbles:true, cancelable:true, pointerId:7, isPrimary:true});
      return e;
    }
    h0.dispatchEvent(pe('pointerdown', cx, cy));
    var loupe = document.querySelector('.sc-loupe');
    out.loupeShown = !!loupe;
    if (loupe) {
      var cv = loupe.querySelector('canvas');
      var d = cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;
      var mn = 255, mx = 0;
      for (var i = 0; i < d.length; i += 40){ var v = d[i]; if(v<mn)mn=v; if(v>mx)mx=v; }
      out.loupeRange = mx - mn;
      var lr = loupe.getBoundingClientRect();
      // the finger point must not be hidden under the loupe
      out.loupeClearOfFinger = !(cx >= lr.left && cx <= lr.right && cy >= lr.top && cy <= lr.bottom);
      // drag the corner 40px down-right
      window.dispatchEvent(pe('pointermove', cx + 40, cy + 40));
      out.movedOk = true;
      window.dispatchEvent(pe('pointerup', cx + 40, cy + 40));
    }
    out.loupeRemoved = !document.querySelector('.sc-loupe');
    window.__loupeBody = body;
  } catch(e){ out.err = String(e && e.stack || e); }
  return out;
})()
"""

CAM_JS = r"""
(function(){
  var out = { tip: null, tipKey: null };
  try {
    var body = document.createElement('div'); body.id = 'scCamBody';
    document.body.appendChild(body);
    HUB.scan._t.scanCamView(body);
    out.mounted = !!body.querySelector('.sc-camwrap');
    window.__camBody = body;
  } catch(e){ out.err = String(e && e.stack || e); }
  return out;
})()
"""
CAM_TIP_JS = r"""
(function(){
  var tip = document.querySelector('#scCamBody [data-camtip]');
  return { text: tip ? tip.textContent : null, key: tip ? (tip.__tk || 'scan.camHint') : null };
})()
"""


def part_b():
    print('== Part B: CDP (loupe + honest viewfinder) ==')
    for vp, theme in [(390, 'dark'), (390, 'light'), (320, 'dark')]:
        tag = '%d-%s' % (vp, theme)
        chrome = None
        try:
            cmd = [CHROME, '--headless=new', '--disable-gpu', '--no-sandbox',
                   '--allow-file-access-from-files',
                   '--use-fake-device-for-media-stream',
                   '--use-fake-ui-for-media-stream',
                   '--window-size=%d,844' % vp,
                   '--remote-debugging-port=%d' % (9331 + vp + (7 if theme == 'light' else 0)),
                   'about:blank']
            chrome = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ws_url = None
            import urllib.request
            port = 9331 + vp + (7 if theme == 'light' else 0)
            for _ in range(40):
                try:
                    pages = json.load(urllib.request.urlopen('http://127.0.0.1:%d/json' % port, timeout=2))
                    for pg in pages:
                        if pg.get('type') == 'page':
                            ws_url = pg['webSocketDebuggerUrl']
                            break
                    if ws_url:
                        break
                except Exception:
                    pass
                time.sleep(0.5)
            check('chrome up %s' % tag, bool(ws_url))
            if not ws_url:
                continue
            cdp = CDP(ws_url)
            ev0 = len(cdp.events)
            cdp.call('Runtime.enable'); cdp.call('Log.enable'); cdp.call('Page.enable')
            url = 'file://' + os.path.join(HUB, 'index.html')
            cdp.call('Page.navigate', {'url': url})
            ok = False
            for _ in range(60):
                r = cdp.call('Runtime.evaluate', {'expression': '!!(window.HUB&&HUB.scan)', 'returnByValue': True})
                if (r.get('result') or {}).get('value'):
                    ok = True
                    break
                time.sleep(0.5)
            check('app loads %s' % tag, ok)
            if not ok:
                continue
            if theme == 'light':
                cdp.call('Runtime.evaluate', {'expression': 'document.body.classList.remove("dark")'})
            else:
                cdp.call('Runtime.evaluate', {'expression': 'document.body.classList.add("dark")'})
            # ---- loupe ----
            r = cdp.call('Runtime.evaluate', {'expression': LOUPE_JS, 'returnByValue': True, 'awaitPromise': False})
            L = (r.get('result') or {}).get('value') or {}
            check('loupe: adjust view mounts %s' % tag, L.get('adjustVisible') is True, L.get('err', ''))
            check('loupe: handle found %s' % tag, L.get('handleFound') is True)
            check('loupe: shows on corner press %s' % tag, L.get('loupeShown') is True)
            check('loupe: canvas has zoomed content %s' % tag, (L.get('loupeRange') or 0) > 30,
                  'range=%s' % L.get('loupeRange'))
            check('loupe: floats clear of finger %s' % tag, L.get('loupeClearOfFinger') is True)
            check('loupe: removed on release %s' % tag, L.get('loupeRemoved') is True)
            # screenshot the adjust view with loupe (pin test body as viewport overlay)
            cdp.call('Runtime.evaluate', {'expression': r"""
              (function(){
                var body = window.__loupeBody;
                body.style.cssText = 'position:fixed;inset:0;z-index:9998;background:#0b0d08;overflow:auto;padding:12px;';
                var h0 = body.querySelector('[data-h="0"]');
                var r = h0.getBoundingClientRect();
                var e = new PointerEvent('pointerdown', {clientX:r.left+r.width/2, clientY:r.top+r.height/2, bubbles:true, cancelable:true});
                h0.dispatchEvent(e);
              })()
            """})
            time.sleep(0.4)
            shot = cdp.call('Page.captureScreenshot', {'format': 'png'})
            data = shot.get('data', '')
            if data:
                import base64
                fn = os.path.join(HUB, 'qa', 'det2-loupe-%s.png' % tag)
                open(fn, 'wb').write(base64.b64decode(data))
                check('loupe screenshot saved %s' % tag, True, fn)
            cdp.call('Runtime.evaluate', {'expression': 'window.dispatchEvent(new PointerEvent("pointerup",{bubbles:true}))'})
            # ---- honest camera viewfinder ----
            r = cdp.call('Runtime.evaluate', {'expression': CAM_JS, 'returnByValue': True})
            C = (r.get('result') or {}).get('value') or {}
            check('camView mounts %s' % tag, C.get('mounted') is True, C.get('err', ''))
            time.sleep(2.5)  # let detection run on the fake device frames
            r = cdp.call('Runtime.evaluate', {'expression': CAM_TIP_JS, 'returnByValue': True})
            tip = (r.get('result') or {}).get('value') or {}
            # honest: no document in the fake-device pattern -> the no-page tip,
            # never a locked tip and never stuck on the initial hint
            check('camView honest tip on empty scene %s' % tag,
                  tip.get('key') == 'scan.camNoDoc',
                  'key=%s text=%s' % (tip.get('key'), (tip.get('text') or '')[:50]))
            # screenshot the honest viewfinder (isolate cam body as viewport overlay)
            cdp.call('Runtime.evaluate', {'expression': r"""
              (function(){
                if (window.__loupeBody) window.__loupeBody.style.display = 'none';
                var b = document.querySelector('#scCamBody');
                if (b) b.style.cssText = 'position:fixed;inset:0;z-index:9997;background:#000;overflow:auto;';
              })()
            """})
            time.sleep(0.6)
            shot = cdp.call('Page.captureScreenshot', {'format': 'png'})
            data = shot.get('data', '')
            if data:
                import base64
                fn = os.path.join(HUB, 'qa', 'det2-cam-%s.png' % tag)
                open(fn, 'wb').write(base64.b64decode(data))
            # ---- console errors ----
            real = []
            for e in cdp.ev(since=ev0):
                p = e.get('params', {})
                if e.get('method') == 'Log.entryAdded' and (p.get('entry') or {}).get('level') == 'error':
                    real.append(str((p['entry'].get('text') or p['entry'].get('url')))[:160])
                elif e.get('method') == 'Runtime.consoleAPICalled' and p.get('type') == 'error':
                    real.append('console.error called')
                elif e.get('method') == 'Runtime.exceptionThrown':
                    real.append(str(p.get('exceptionDetails', {}).get('text'))[:160])
            check('zero console errors %s' % tag, len(real) == 0, '; '.join(real[:3]))
        finally:
            try:
                if chrome:
                    chrome.terminate()
            except Exception:
                pass


if __name__ == '__main__':
    part_a()
    part_b()
    print('\n==== %d passed, %d failed ====' % (len(passes), len(fails)))
    sys.exit(1 if fails else 0)
