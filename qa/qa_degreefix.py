#!/usr/bin/env python3
"""QA: degree-plan occurrence-identity + semester-label fixes (js/degree.js).

Bug 1: semesters without `n` rendered every header as "Summer NaN".
Bug 2: placeholder slot_ids ("s?-N") reused across courses meant checking one
       tile checked every other tile sharing the id, and earned credits were
       inflated by counting each duplicate.

2026-10-01 pipeline renumber: build.py now normalizes every semester to a
numeric n, so runtime slot_ids are sK-N (unique per plan). Legacy user done
maps keyed by the old "s?-N" ids are ORPHAN keys; the app's migrateDoneOcc
rescues them by code/title/choice_note match, never deleting user data.

Seeds a LEGACY done map (bare "s?-N" orphan keys, no `at` field) on the Adams
State BA Elementary Education plan, opens it, and asserts:
  1. headers are Fall 2026 / Spring 2027 / ... / Spring 2030, no "NaN"
  2. orphan migration re-attaches each legacy record to exactly ONE occurrence
     (MATH 104 -> s1-4 by code, FYS 101 -> s1-0 by code,
      HIST 202 -> s1-2 via the slot's choice_note "recommends HIST 202")
  3. earned credits count each completion once (no duplicate inflation)
  4. toggling a tile affects only that tile (on and off)
  5. completing a choice slot records the pick on that tile only
  6. collapsing one semester does not collapse others
  7. zero console errors/warnings

Headless Chromium via file:/// (repo AGENTS.md pattern). stdlib only.
"""
import json, subprocess, time, urllib.request, os, sys, shutil, socket
import hashlib, base64, struct
from urllib.parse import urlparse

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
SLUG = 'adams-state-university-ba-elementary-education'
PORT = 9511
PROFILE = '/tmp/hubqa-degfix'

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
        while time.time() < deadline:
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

def reg(c, js, wait_js):
    """Regression on plans that were already correct (unique slot_ids or not):
    labels, toggle, detail sheet, tabs, choice completion, prereq warnings."""
    def fresh(slug):
        js("(()=>{delete HUB.degree._state().progress[%s];HUB.store.save();"
           "HUB.degree.open(%s);return 'fresh'})()" % (json.dumps(slug), json.dumps(slug)))
        return wait_js("document.querySelectorAll('#hubDegRoot .deg-sem').length>0", 20)

    # R1. dallas-college-aa-business: proper s1-0 ids, n=1..4
    check('reg: dallas plan opens', fresh('dallas-college-aa-business'))
    dh = js("[...document.querySelectorAll('#hubDegRoot .deg-sem .t')].map(e=>e.textContent.trim())")
    check('reg: dallas headers Fall 2026..Spring 2028',
          dh == ['Fall 2026', 'Spring 2027', 'Fall 2027', 'Spring 2028'], dh)
    check('reg: dallas 20 tiles',
          js("document.querySelectorAll('#hubDegRoot .deg-tile').length") == 20)
    js("document.querySelector('.deg-tile[data-at=\"0:0\"] .deg-check').click()")
    import time as _t; _t.sleep(0.3)
    e1 = js("document.querySelector('#hubDegRoot .deg-earned').textContent.trim()")
    check('reg: dallas toggle on -> 3 of 60 credits', e1 == '3 of 60 credits', e1)
    check('reg: dallas tile 0:0 done',
          js("!!document.querySelector('.deg-tile[data-at=\"0:0\"].done')"))
    js("document.querySelector('.deg-tile[data-at=\"0:0\"] .deg-check').click()")
    _t.sleep(0.3)
    e0 = js("document.querySelector('#hubDegRoot .deg-earned').textContent.trim()")
    check('reg: dallas toggle off -> 0 of 60 credits', e0 == '0 of 60 credits', e0)
    # detail sheet opens and closes without toggling
    js("document.querySelector('.deg-tile[data-at=\"0:1\"] .deg-tile-main').click()")
    _t.sleep(0.5)
    check('reg: detail sheet opens',
          js("!document.getElementById('sheetHost').hidden"))
    js("HUB.ui.closeSheet()")
    _t.sleep(0.3)
    check('reg: detail sheet closes, tile still undone',
          not js("!!document.querySelector('.deg-tile[data-at=\"0:1\"].done')"))
    # tabs
    js("document.getElementById('degTabXfer').click()")
    _t.sleep(0.5)
    check('reg: transfer tab renders',
          js("!!document.querySelector('#hubDegRoot .deg-xrow, #hubDegRoot .empty')"))
    js("document.getElementById('degTabPlan').click()")
    _t.sleep(0.5)
    check('reg: back to plan tab',
          js("document.querySelectorAll('#hubDegRoot .deg-tile').length") == 20)

    # R2. uta-bba-management: 8 sems, 41 tiles, choice slots
    check('reg: uta plan opens', fresh('uta-bba-management'))
    uh = js("[...document.querySelectorAll('#hubDegRoot .deg-sem .t')].map(e=>e.textContent.trim())")
    check('reg: uta headers Fall 2026..Spring 2030',
          uh == ['Fall 2026', 'Spring 2027', 'Fall 2027', 'Spring 2028',
                 'Fall 2028', 'Spring 2029', 'Fall 2029', 'Spring 2030'], uh)
    check('reg: uta 41 tiles',
          js("document.querySelectorAll('#hubDegRoot .deg-tile').length") == 41)
    cat = js("(()=>{const t=[...document.querySelectorAll('#hubDegRoot .deg-tile')]"
             ".find(t=>t.querySelector('.deg-choice-chip')&&!t.classList.contains('done'));"
             "return t?t.dataset.at:'none'})()")
    check('reg: uta has an open choice tile', cat != 'none', cat)
    if cat != 'none':
        js("document.querySelector('.deg-tile[data-at=\"%s\"] .deg-tile-main').click()" % cat)
        _t.sleep(0.5)
        js(("(()=>{document.getElementById('degChoiceCode').value='MGMT 9999';"
            "document.getElementById('degChoiceSave').click();return 's'})()"))
        _t.sleep(0.5)
        check('reg: uta choice tile done with pick',
              js("(()=>{const el=document.querySelector('.deg-tile[data-at=\"%s\"]');"
                 "return el&&el.classList.contains('done')&&"
                 "el.querySelector('.deg-code').textContent.indexOf('MGMT 9999')===0})()" % cat))

    # R3. aaniiih plan: placeholder ids + real prereqs + no `n`
    check('reg: aaniiih plan opens', fresh('aaniiih-nakoda-college-aa-business'))
    ah = js("[...document.querySelectorAll('#hubDegRoot .deg-sem .t')].map(e=>e.textContent.trim())")
    check('reg: aaniiih headers Fall 2026..Spring 2028, no NaN',
          ah == ['Fall 2026', 'Spring 2027', 'Fall 2027', 'Spring 2028'], ah)
    check('reg: WRIT 201 shows prereq warn badge',
          js("!!document.querySelector('.deg-tile[data-at=\"1:4\"] [data-warn]')"))
    js("document.querySelector('.deg-tile[data-at=\"1:4\"] .deg-tile-main').click()")
    _t.sleep(0.5)
    check('reg: detail sheet lists pending prereq',
          js("[...document.querySelectorAll('#sheetBox .deg-req')].some("
             "e=>e.textContent.indexOf('WRIT 101')!==-1)"))
    js("HUB.ui.closeSheet()")
    _t.sleep(0.3)
    js("document.querySelector('.deg-tile[data-at=\"0:5\"] .deg-check').click()")
    _t.sleep(0.5)
    check('reg: completing WRIT 101 clears the warn badge',
          not js("!!document.querySelector('.deg-tile[data-at=\"1:4\"] [data-warn]')"))
    check('reg: WRIT 201 still not done',
          not js("!!document.querySelector('.deg-tile[data-at=\"1:4\"].done')"))

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
        # seed profile past onboarding + auth gate
        js(("(()=>{try{const p=HUB.store.state.profile;p.name='QA Tester';"
            "p.campus='QA Campus';HUB.store.save();}catch(e){return 'ERR:'+e.message}"
            "const w=document.getElementById('wlcmHost');if(w)w.remove();"
            "try{HUB.showTab('home');}catch(e){}return 'seeded'})()"))
        time.sleep(1.0)

        # ---- seed a LEGACY done map: bare "s?-N" ORPHAN keys (the pipeline
        # renumbered runtime ids to sK-N), NO `at` field ----
        seed = js("""(()=>{
          const st=HUB.store.state;
          st.degree={active:null,progress:{'%s':{
            done:{
              's?-4':{code:'MATH 104',title:'Finite Mathematics',credits:3,ts:1759291200000},
              's?-2':{code:'HIST 202',title:'US History II',credits:3,ts:1759291200000},
              's?-0':{code:'FYS 101',title:'First Year Seminar',credits:3,ts:1759291200000}
            },
            startYear:2026, intake:{term:'fall',year:2026}
          }}};
          HUB.store.save(); return 'seeded';
        })()""" % SLUG)
        check('legacy done map seeded', seed == 'seeded', seed)

        js("HUB.degree.open(%s)" % json.dumps(SLUG))
        ok = wait_js("document.querySelectorAll('#hubDegRoot .deg-sem').length===8", 20)
        check('plan renders 8 semesters', ok, ok)

        # 1. headers: Fall 2026 ... Spring 2030, no NaN
        headers = js("[...document.querySelectorAll('#hubDegRoot .deg-sem .t')].map(e=>e.textContent.trim())")
        expect = ['Fall 2026', 'Spring 2027', 'Fall 2027', 'Spring 2028',
                  'Fall 2028', 'Spring 2029', 'Fall 2029', 'Spring 2030']
        check('semester headers Fall 2026..Spring 2030', headers == expect, headers)
        body_txt = js("document.getElementById('hubDegRoot').textContent")
        check('no "NaN" anywhere in tracker', body_txt is not None and 'NaN' not in body_txt,
              (body_txt or '')[:120])

        # 2. orphan migration: each legacy record rescued to exactly ONE occurrence
        keys = js("Object.keys(HUB.store.state.degree.progress[%s].done).sort()" % json.dumps(SLUG))
        check('orphan keys rescued to s1-0/s1-2/s1-4', keys == ['s1-0', 's1-2', 's1-4'], keys)
        check('no s?- orphan keys remain',
              not js("Object.keys(HUB.store.state.degree.progress[%s].done).some(k=>k.indexOf('s?-')===0)" % json.dumps(SLUG)))
        n_s14 = js("document.querySelectorAll('.deg-tile[data-slot=\"s1-4\"].done').length")
        check('exactly one s1-4 tile done (MATH 104)', n_s14 == 1, n_s14)
        check('MATH 104 tile (0:4) is the done one',
              js("!!document.querySelector('.deg-tile[data-at=\"0:4\"].done')"))
        check('ED 347 tile (4:4) is NOT done',
              not js("!!document.querySelector('.deg-tile[data-at=\"4:4\"].done')"))
        check('HIST 202 rescued to choice slot (0:2)',
              js("!!document.querySelector('.deg-tile[data-at=\"0:2\"].done')"))
        n_s10 = js("document.querySelectorAll('.deg-tile[data-slot=\"s1-0\"].done').length")
        check('exactly one s1-0 tile done (FYS 101)', n_s10 == 1, n_s10)

        # 3. earned credits counted once per completion
        earned = js("document.querySelector('#hubDegRoot .deg-earned').textContent.trim()")
        check('earned shows honest 9 of 122 (not inflated 66)', earned == '9 of 122 credits', earned)

        # 4. toggle a tile -> only that tile flips
        js("document.querySelector('.deg-tile[data-at=\"4:4\"] .deg-check').click()")
        time.sleep(0.3)
        n_s54 = js("document.querySelectorAll('.deg-tile[data-slot=\"s5-4\"].done').length")
        check('toggling 4:4 on: ED 347 tile done', n_s54 == 1, n_s54)
        check('MATH 104 still done after 4:4 toggled on',
              js("!!document.querySelector('.deg-tile[data-at=\"0:4\"].done')"))
        earned2 = js("document.querySelector('#hubDegRoot .deg-earned').textContent.trim()")
        check('earned 12 after toggle on', earned2 == '12 of 122 credits', earned2)
        js("document.querySelector('.deg-tile[data-at=\"4:4\"] .deg-check').click()")
        time.sleep(0.3)
        n_s54b = js("document.querySelectorAll('.deg-tile[data-slot=\"s5-4\"].done').length")
        earned3 = js("document.querySelector('#hubDegRoot .deg-earned').textContent.trim()")
        check('toggling 4:4 off: ED 347 tile not done', n_s54b == 0, n_s54b)
        check('earned back to 9 after toggle off', earned3 == '9 of 122 credits', earned3)

        # 5. complete a choice slot (sem1 GENED-II-2) -> pick lands on that tile only
        js("document.querySelector('.deg-tile[data-at=\"1:2\"] .deg-tile-main').click()")
        time.sleep(0.5)
        sheet_open = js("!document.getElementById('sheetHost').hidden")
        check('choice sheet opens for 1:2', sheet_open)
        js(("(()=>{document.getElementById('degChoiceCode').value='ART 101';"
            "document.getElementById('degChoiceTitle').value='Art Appreciation';"
            "document.getElementById('degChoiceSave').click();return 'saved'})()"))
        time.sleep(0.5)
        tile12 = js("(()=>{const el=document.querySelector('.deg-tile[data-at=\"1:2\"]');"
                   "return el?(el.classList.contains('done')+'|'+el.querySelector('.deg-code').textContent.trim()):'missing'})()")
        check('choice tile 1:2 done showing pick ART 101', tile12 == 'true|ART 1013 cr', tile12)
        n_s22 = js("document.querySelectorAll('.deg-tile[data-slot=\"s2-2\"].done').length")
        check('s2-2 tile done (new pick)', n_s22 == 1, n_s22)
        n_s12 = js("document.querySelectorAll('.deg-tile[data-slot=\"s1-2\"].done').length")
        check('s1-2 tile still done (rescued HIST 202, unaffected)', n_s12 == 1, n_s12)
        earned4 = js("document.querySelector('#hubDegRoot .deg-earned').textContent.trim()")
        check('earned 12 after choice completion', earned4 == '12 of 122 credits', earned4)

        # 6. collapsing one semester does not collapse others
        js("document.querySelector('[data-semtgl=\"1\"]').click()")
        time.sleep(0.3)
        s1 = js("document.querySelector('[data-sem=\"1\"]').classList.contains('open')")
        s2 = js("document.querySelector('[data-sem=\"2\"]').classList.contains('open')")
        s8 = js("document.querySelector('[data-sem=\"8\"]').classList.contains('open')")
        check('semester 1 collapsed', s1 is False, s1)
        check('semester 2 still open', s2 is True, s2)
        check('semester 8 still open', s8 is True, s8)

        # ---- regression phase: well-formed plans must behave exactly as before ----
        reg(c, js, wait_js)

        # 7. zero console errors/warnings (whole session)
        errs = js("window.__degerr.splice(0)")
        check('zero console errors', isinstance(errs, list) and len(errs) == 0, errs)

        c.close()
    finally:
        try:
            proc.terminate()
        except Exception:
            pass

    print('\n==== qa_degreefix: %d passed, %d failed ====' % (passed, failed))
    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
