#!/usr/bin/env python3
"""QA: choice-slot string options + pick swapping (js/degree.js).

Covers:
  1. Dallas College AS Computer Engineering ARTS 1303 choice sheet renders
     3 named rows (string options), no blank rows.
  2. Picking HUMA 1315 marks only that tile, showing code + resolved title.
  3. Detail sheet lists the options with the current pick highlighted;
     tapping MUSI 1306 SWAPS the pick (one record, credits unchanged).
  4. Mark undone from the detail sheet clears the slot fully.
  5. Object-option plans still render as before (dallas-college-aa-transfer).
  6. Zero console errors/warnings.

Headless Chromium via file:/// (repo AGENTS.md pattern). stdlib only.
"""
import json, subprocess, time, urllib.request, os, sys, shutil, socket
import base64, struct
from urllib.parse import urlparse

CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
SLUG = 'dallas-college-as-computer-engineering'
OBJSLUG = 'dallas-college-aa-transfer'
PORT = 9512
PROFILE = '/tmp/hubqa-degchoice'

# ---------------------------------------------------------------- mini ws ---
class MiniWS:
    """Minimal RFC6455 client (stdlib only): handshake, masked text sends,
    fragmented server frames, ping->pong. Enough for CDP."""
    def __init__(self, url):
        u = urlparse(url)
        host, port = u.hostname, u.port or 80
        self.sock = socket.create_connection((host, port), timeout=12)
        key = base64.b64encode(os.urandom(16)).decode()
        req = ('GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\n'
               'Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n'
               'Sec-WebSocket-Version: 13\r\n\r\n') % (u.path or '/', host, port, key)
        self.sock.sendall(req.encode())
        resp = b''
        while b'\r\n\r\n' not in resp:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError('ws handshake: connection closed')
            resp += chunk
        if b'101' not in resp.split(b'\r\n')[0]:
            raise RuntimeError('ws handshake rejected: %r' % resp[:160])
        self.buf = b''
        self.sock.settimeout(20)

    def send(self, text):
        data = text.encode('utf-8')
        mask = os.urandom(4)
        n = len(data)
        if n < 126:
            hdr = bytes([0x81, 0x80 | n])
        elif n < 65536:
            hdr = bytes([0x81, 0x80 | 126]) + struct.pack('>H', n)
        else:
            hdr = bytes([0x81, 0x80 | 127]) + struct.pack('>Q', n)
        self.sock.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _fill(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError('ws closed by peer')
            self.buf += chunk

    def _pong(self, payload):
        self.sock.sendall(bytes([0x8A, len(payload)]) + payload)

    def recv(self):
        msg = b''
        while True:
            self._fill(2)
            b1, b2 = self.buf[0], self.buf[1]
            fin, op, ln = b1 & 0x80, b1 & 0x0f, b2 & 0x7f
            idx = 2
            if ln == 126:
                self._fill(4); ln = struct.unpack('>H', self.buf[2:4])[0]; idx = 4
            elif ln == 127:
                self._fill(10); ln = struct.unpack('>Q', self.buf[2:10])[0]; idx = 10
            self._fill(idx + ln)
            payload = self.buf[idx:idx + ln]
            self.buf = self.buf[idx + ln:]
            if op == 0x8:
                raise RuntimeError('ws close frame from server')
            if op == 0x9:
                self._pong(payload); continue
            if op in (0x1, 0x0):
                msg += payload
                if fin:
                    return msg.decode('utf-8', 'replace')

    def close(self):
        try:
            self.sock.sendall(bytes([0x88, 0x80]) + os.urandom(4))
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass

# ------------------------------------------------------------------ CDP ----
class CDP:
    def __init__(self, wsurl):
        self.ws = MiniWS(wsurl)
        self.id = 0

    def send(self, method, params=None, timeout=25):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + timeout
        while time.time() - deadline < 0:
            try:
                msg = json.loads(self.ws.recv())
            except Exception as e:
                raise TimeoutError('%s: %s' % (method, str(e)[:80]))
            if msg.get('id') == self.id:
                return msg.get('result')
        raise TimeoutError(method)

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass

HOOKS = ("window.__degerr=[];"
         "window.addEventListener('error',function(e){window.__degerr.push('ERR:'+(e.message||e.error));});"
         "window.addEventListener('unhandledrejection',function(e){window.__degerr.push('REJ:'+((e.reason&&e.reason.message)||e.reason));});")

passed, failed = 0, 0
def check(name, cond, detail=''):
    global passed, failed
    ok = bool(cond)
    if ok:
        passed += 1
    else:
        failed += 1
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else ' :: ' + str(detail)[:220]))

def main():
    global passed, failed
    shutil.rmtree(PROFILE, ignore_errors=True)
    proc = subprocess.Popen(
        [CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
         '--disable-dev-shm-usage', '--hide-scrollbars',
         '--allow-file-access-from-files',
         '--remote-debugging-port=%d' % PORT, '--remote-allow-origins=*',
         '--user-data-dir=' + PROFILE, 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        tgt = None
        for _ in range(40):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen('http://localhost:%d/json/list' % PORT, timeout=3) as r:
                    for t in json.load(r):
                        if t['type'] == 'page' and 'devtools' not in t['url']:
                            tgt = t
                            break
                if tgt:
                    break
            except Exception:
                continue
        if not tgt:
            print('FAIL chrome did not start'); return 2
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Page.addScriptToEvaluateOnNewDocument', {'source': HOOKS})
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        c.send('Emulation.setDeviceMetricsOverride',
               {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})

        def js(expr, timeout=25):
            r = c.send('Runtime.evaluate',
                       {'expression': expr, 'returnByValue': True, 'awaitPromise': True},
                       timeout=timeout)
            res = (r or {}).get('result', {})
            if 'exceptionDetails' in (r or {}):
                return '__EXC__'
            return res.get('value')

        def wait_js(expr, timeout=20):
            t0 = time.time()
            while time.time() - t0 < timeout:
                v = js(expr)
                if v:
                    return v
                time.sleep(0.4)
            return None

        c.send('Page.navigate', {'url': BASE})
        wait_js("document.readyState==='complete'", 25)
        wait_js("!document.getElementById('splash')", 20)
        js(("(()=>{try{const p=HUB.store.state.profile;p.name='QA Tester';"
            "p.campus='QA Campus';HUB.store.save();}catch(e){return 'ERR:'+e.message}"
            "const w=document.getElementById('wlcmHost');if(w)w.remove();"
            "try{HUB.showTab('home');}catch(e){}return 'seeded'})()"))
        time.sleep(1.0)

        def fresh(slug):
            js("(()=>{delete HUB.degree._state().progress[%s];HUB.store.save();"
               "HUB.degree.open(%s);return 'fresh'})()" % (json.dumps(slug), json.dumps(slug)))
            return wait_js("document.querySelectorAll('#hubDegRoot .deg-sem').length>0", 20)

        # ---- 1. choice sheet renders named rows for string options ----
        check('dallas CE plan opens', fresh(SLUG))
        js("document.querySelector('.deg-tile[data-at=\"0:4\"] .deg-tile-main').click()")
        time.sleep(0.6)
        check('choice sheet opens for ARTS 1303',
              js("!document.getElementById('sheetHost').hidden"))
        rows = js("[...document.querySelectorAll('#sheetBox .deg-opt')].map(b=>({"
                  "c:b.querySelector('.c').textContent.trim(),"
                  "t:b.querySelector('.ti').textContent.trim()}))")
        check('3 option rows', isinstance(rows, list) and len(rows) == 3, rows)
        codes = [r['c'] for r in rows] if isinstance(rows, list) else []
        check('row codes ARTS 1303 / HUMA 1315 / MUSI 1306',
              codes == ['ARTS 1303', 'HUMA 1315', 'MUSI 1306'], codes)
        check('no blank code rows', all(r['c'] for r in rows), rows)
        bycode = {r['c']: r['t'] for r in rows} if isinstance(rows, list) else {}
        check('HUMA 1315 title = Fine Arts Appreciation',
              bycode.get('HUMA 1315') == 'Fine Arts Appreciation', bycode)
        check('MUSI 1306 title = Music Appreciation',
              bycode.get('MUSI 1306') == 'Music Appreciation', bycode)

        # ---- 2. pick HUMA 1315 -> only that tile marked, with resolved title ----
        js("document.querySelector('#sheetBox .deg-opt[data-opt=\"1\"]').click()")
        time.sleep(0.6)
        tile = js("(()=>{const el=document.querySelector('.deg-tile[data-at=\"0:4\"]');"
                  "return el?{done:el.classList.contains('done'),"
                  "code:el.querySelector('.deg-code').textContent.trim(),"
                  "title:el.querySelector('.deg-title').textContent.trim(),"
                  "chip:el.querySelector('.deg-choice-chip')?"
                  "el.querySelector('.deg-choice-chip').textContent.trim():''}:'missing'})()")
        check('tile 0:4 done after HUMA pick', tile.get('done') is True, tile)
        check('tile shows code HUMA 1315',
              tile.get('code', '').startswith('HUMA 1315'), tile)
        check('tile shows title Fine Arts Appreciation',
              'Fine Arts Appreciation' in tile.get('title', ''), tile)
        check('tile has Your choice chip', 'Your choice' in tile.get('chip', ''), tile)
        check('exactly one tile done overall',
              js("document.querySelectorAll('#hubDegRoot .deg-tile.done').length") == 1)
        earned_huma = js("document.querySelector('#hubDegRoot .deg-earned').textContent.trim()")
        check('earned counts the pick once', earned_huma == '3 of 60 credits', earned_huma)

        # ---- 3. detail sheet: options listed, HUMA highlighted; swap to MUSI ----
        js("document.querySelector('.deg-tile[data-at=\"0:4\"] .deg-tile-main').click()")
        time.sleep(0.6)
        check('detail sheet opens for completed choice tile',
              js("!document.getElementById('sheetHost').hidden"))
        dopts = js("[...document.querySelectorAll('#sheetBox [data-dopt]')].map(b=>({"
                   "c:b.querySelector('.c').textContent.trim(),"
                   "sel:!!b.querySelector('.deg-choice-chip')}))")
        check('detail sheet lists 3 options', isinstance(dopts, list) and len(dopts) == 3, dopts)
        sel = [d['c'] for d in dopts if d['sel']] if isinstance(dopts, list) else []
        check('HUMA 1315 highlighted as current pick', sel == ['HUMA 1315'], sel)
        js("document.querySelector('#sheetBox [data-dopt=\"2\"]').click()")
        time.sleep(0.6)
        tile2 = js("(()=>{const el=document.querySelector('.deg-tile[data-at=\"0:4\"]');"
                   "return el?{done:el.classList.contains('done'),"
                   "code:el.querySelector('.deg-code').textContent.trim(),"
                   "title:el.querySelector('.deg-title').textContent.trim()}:'missing'})()")
        check('tile now shows MUSI 1306', tile2.get('code', '').startswith('MUSI 1306'), tile2)
        check('tile now shows Music Appreciation',
              'Music Appreciation' in tile2.get('title', ''), tile2)
        nrec = js("Object.keys(HUB.store.state.degree.progress[%s].done)"
                  ".filter(k=>k==='s1-4'||k.indexOf('s1-4~~')===0).length" % json.dumps(SLUG))
        check('exactly ONE done record for the slot after swap', nrec == 1, nrec)
        earned_musi = js("document.querySelector('#hubDegRoot .deg-earned').textContent.trim()")
        check('earned unchanged after swap (no double count)',
              earned_musi == earned_huma, (earned_huma, earned_musi))

        # ---- 4. mark undone from detail sheet clears fully ----
        js("document.querySelector('.deg-tile[data-at=\"0:4\"] .deg-tile-main').click()")
        time.sleep(0.6)
        js("document.getElementById('degDetailToggle').click()")
        time.sleep(0.6)
        check('tile undone after Mark undone',
              not js("!!document.querySelector('.deg-tile[data-at=\"0:4\"].done')"))
        nrec2 = js("Object.keys(HUB.store.state.degree.progress[%s].done)"
                   ".filter(k=>k==='s1-4'||k.indexOf('s1-4~~')===0).length" % json.dumps(SLUG))
        check('no done records left for the slot', nrec2 == 0, nrec2)
        earned0 = js("document.querySelector('#hubDegRoot .deg-earned').textContent.trim()")
        check('earned back to 0', earned0 == '0 of 60 credits', earned0)

        # ---- 5. object-option plan still renders as before ----
        check('dallas transfer plan opens', fresh(OBJSLUG))
        js("document.querySelector('.deg-tile[data-at=\"2:5\"] .deg-tile-main').click()")
        time.sleep(0.6)
        orows = js("[...document.querySelectorAll('#sheetBox .deg-opt')].map(b=>({"
                   "c:b.querySelector('.c').textContent.trim(),"
                   "t:b.querySelector('.ti').textContent.trim()}))")
        check('object options render 3 rows', isinstance(orows, list) and len(orows) == 3, orows)
        ocodes = [r['c'] for r in orows] if isinstance(orows, list) else []
        check('object row codes intact',
              ocodes == ['ENGL 2321', 'ENGL 2326', 'ENGL 2331'], ocodes)
        check('object row keeps its title',
              isinstance(orows, list) and orows[0]['t'] == 'British Literature', orows)
        js("HUB.ui.closeSheet()")
        time.sleep(0.3)

        # ---- 6. zero console errors/warnings (whole session) ----
        errs = js("window.__degerr.splice(0)")
        check('zero console errors', isinstance(errs, list) and len(errs) == 0, errs)

        c.close()
    finally:
        try:
            proc.terminate()
        except Exception:
            pass

    print('\n==== qa_degreechoice: %d passed, %d failed ====' % (passed, failed))
    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
