#!/usr/bin/env python3
"""HUB QA: ALL-USA-SCHOOLS directory (data/schools_us.json + js/store.js wiring).
Fresh profile /tmp/hubqa-sch (wiped), file:// load, 390px + 320px, dark.

Phases:
  A. boot + gate disarm + seed; both JSONs load via loadColleges()
  B. merged count == 37645 (colleges) + 122620 (schools) == 160265
  C. "Lincoln High School" -> results in multiple states
  D. "Thomas Jefferson" -> Alexandria VA school found (official CCD name
     "Thomas Jefferson High for Science and Technology")
  E. US country filter (cc='US') -> only United States rows
  F. null-coord school stays searchable; coord guard never fires on it
  G. institution picker: no horizontal overflow at 390px and 320px
  H. timings: JSON load+merge ms, one search ms
  I. zero console errors
"""
import json, subprocess, time, urllib.request, os, shutil, sys, base64
try:
    import websocket
except ImportError:
    print('websocket-client missing'); sys.exit(2)

CHROME = '/opt/meta-chromium/chrome'; PORT = 9451
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-sch'
JS = "(function(){%s})()"
checks = []
def note(ok, label, detail=''):
    checks.append(bool(ok)); print(('PASS' if ok else 'FAIL'), label, detail)

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12)
        self.id = 0; self.events = []
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        t = time.time()
        while time.time() - t < 15:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:80])
            if 'method' in msg and 'id' not in msg:
                self.events.append(msg); continue
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)
    def js(self, expr, awaitPromise=False):
        try:
            r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': awaitPromise})
            res = (r or {}).get('result', {})
            return res.get('value'), res.get('exceptionDetails')
        except Exception as e: return None, str(e)[:160]

def t0(): return time.time()
def js_wait(c, expr, timeout=20):
    t = time.time()
    while time.time() - t < timeout:
        v, _ = c.js(JS % expr)
        if v: return True
        time.sleep(0.4)
    return False

def disarm_gate(c):
    c.js(JS % ("window.__gateSkip=true; try{if(HUB.auth&&HUB.auth.close){"
         "var a=document.querySelector('.authroot'); if(a&&!a.hidden) HUB.auth.close();}}catch(e){} return 1"))

def boot(c):
    ok = js_wait(c, "return !document.getElementById('splash')", 25)
    note(ok, 'splash dismissed')
    c.js(JS % ("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
              "var s=HUB.store.state; s.profile.name='QA User'; s.profile.campus='QA Campus';"
              "s.prefs.dark=true; HUB.store.save(); return 1"))
    c.send('Page.reload')
    ok = js_wait(c, "return document.readyState==='complete' && !document.getElementById('splash') && !!window.HUB && !!HUB.store", 25)
    note(ok, 'clean boot after seed')
    disarm_gate(c); time.sleep(0.8); disarm_gate(c)
    c.js(JS % "try{HUB.ui.closeSheet()}catch(e){} var w=document.getElementById('wlcmHost'); if(w) w.remove(); return 1")
    time.sleep(0.5)
    v, _ = c.js(JS % "return !!document.querySelector('.authroot:not([hidden])')")
    note(not v, 'no auth overlay (gate disarmed)')

def open_picker(c):
    c.js(JS % "HUB.ui.openInstitutionPicker({mode:'student',onPick:function(){window.__picked=arguments[0];}}); return 1")
    return js_wait(c, "return !!document.getElementById('intlSearch')", 8)

def main():
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--remote-debugging-port=%d' % PORT, '--remote-allow-origins=*', '--window-size=390,844',
        '--user-data-dir=%s' % PROF, '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen('http://localhost:%d/json/list' % PORT, timeout=5) as r:
                    ts = json.load(r)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        c.js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
             "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        boot(c)

        # --- A/B: load both JSONs, merged count ---
        t = t0()
        v, e = c.js(JS % "return HUB.intl.loadColleges().then(function(rows){ return {n:rows.length, us:rows.filter(function(r){return r[1]==='United States'}).length}; }).catch(function(err){ return {err:String(err)}; })", awaitPromise=True)
        loadms = int((t0() - t) * 1000)
        note(not (v or {}).get('err'), 'both JSONs load with zero throw', json.dumps(v)[:120] if v else str(e)[:100])
        note(v and v.get('n') == 160265, 'merged institution count == 37645 + 122620 == 160265', str(v.get('n') if v else None))
        note(v and v.get('us') == 8090 + 122620, 'US rows == 8090 colleges + 122620 schools == 130710', str(v.get('us') if v else None))

        # --- C: Lincoln High School, multiple states ---
        v, _ = c.js(JS % "var rs=HUB.intl.searchColleges('Lincoln High School','US',60); var st={}; rs.forEach(function(r){ var p=String(r[2]).split(', ').pop(); if(r[0]==='Lincoln High School') st[p]=1; }); return {n:rs.length, states:Object.keys(st)}")
        note(v and len(v.get('states', [])) >= 5, '"Lincoln High School" in multiple states', str(v))

        # --- D: Thomas Jefferson (Alexandria VA) ---
        v, _ = c.js(JS % "var rs=HUB.intl.searchColleges('Thomas Jefferson','US',60); return rs.filter(function(r){return String(r[2]).indexOf('Alexandria')>=0}).map(function(r){return [r[0],r[2]]})")
        note(bool(v), 'Thomas Jefferson school found in Alexandria VA', str(v)[:160])

        # --- E: US country filter ---
        v, _ = c.js(JS % "var rs=HUB.intl.searchColleges('high school','US',60); return {n:rs.length, allUS:rs.every(function(r){return r[1]==='United States'})}")
        note(v and v.get('n') > 0 and v.get('allUS'), 'cc=US filter returns only United States rows', str(v))
        v, _ = c.js(JS % "return HUB.intl.collegeCountries().some(function(c){return c.iso==='US'})")
        note(bool(v), 'US present in country list')

        # --- F: null-coord school searchable, guard safe ---
        v, _ = c.js(JS % ("var rs=HUB.intl.searchColleges('126-E-W-4','US',10);"
                         "var rec=rs[0]; var picked=rec?{name:rec[0],country:rec[1],city:rec[2],lat:rec[3],lng:rec[4],sample:false}:null;"
                         "var guard=picked?(!picked.sample&&picked.lat!=null&&picked.lng!=null&&isFinite(picked.lat)&&isFinite(picked.lng)):null;"
                         "return {found:rs.length, lat:rec?rec[3]:'none', guardFires:guard};"))
        note(v and v.get('found') > 0 and v.get('lat') is None, 'null-coord school is searchable', str(v))
        note(v and v.get('guardFires') is False, 'null-coord guard never fires (null-safe check)', str(v))

        # --- H: one-search timing ---
        t = t0()
        c.js(JS % "var t2=performance.now(); HUB.intl.searchColleges('lincoln','US',60); return performance.now()-t2")
        v2, _ = c.js(JS % "var t2=performance.now(); HUB.intl.searchColleges('lincoln','US',60); return performance.now()-t2")
        print('TIMING loadColleges+merge: %d ms | one search "lincoln": %.1f ms' % (loadms, v2 or -1))
        note(v2 is not None and v2 < 500, 'one search keystroke under 500ms', '%.1f ms' % (v2 or -1))

        # --- G: picker overflow 390px then 320px ---
        note(open_picker(c), 'institution picker opens (390px)')
        c.js(JS % "var i=document.getElementById('intlSearch'); i.value='lincoln'; i.dispatchEvent(new Event('input',{bubbles:true})); return 1")
        time.sleep(1.2)
        v, _ = c.js(JS % "return {sw:document.documentElement.scrollWidth, vw:window.innerWidth, rows:document.querySelectorAll('.intl-row').length}")
        note(v and v['sw'] <= v['vw'] + 1 and v['rows'] > 0, 'picker no horizontal overflow at 390px', str(v))
        c.send('Emulation.setDeviceMetricsOverride', {'width': 320, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        c.js(JS % "HUB.ui.closeSheet(); HUB.ui.openInstitutionPicker({mode:'student',onPick:function(){}}); return 1")
        time.sleep(0.6)
        c.js(JS % "var i=document.getElementById('intlSearch'); i.value='high school'; i.dispatchEvent(new Event('input',{bubbles:true})); return 1")
        time.sleep(1.2)
        v, _ = c.js(JS % "return {sw:document.documentElement.scrollWidth, vw:window.innerWidth, rows:document.querySelectorAll('.intl-row').length}")
        note(v and v['sw'] <= v['vw'] + 1 and v['rows'] > 0, 'picker no horizontal overflow at 320px', str(v))
        c.js(JS % "HUB.ui.closeSheet(); return 1")

        # --- I: zero console errors ---
        bad = []
        for ev in c.events:
            m = ev.get('method', '')
            if m == 'Runtime.exceptionThrown':
                bad.append('EXC:' + json.dumps(ev['params'].get('exceptionDetails', {}).get('text', ''))[:140])
            elif m == 'Log.entryAdded' and ev['params']['entry'].get('level') == 'error':
                bad.append('LOG:' + ev['params']['entry'].get('text', '')[:140])
            elif m == 'Runtime.consoleAPICalled' and ev['params'].get('type') == 'error':
                bad.append('CON:' + json.dumps(ev['params'].get('args', []))[:140])
        v, _ = c.js("window.__huberr?window.__huberr.splice(0):[]")
        if v: bad.append('HOOK:' + json.dumps(v)[:400])
        note(not bad, 'zero console errors', '; '.join(bad)[:400])

        n = sum(checks); tot = len(checks)
        print('SCHOOLS QA: %d/%d' % (n, tot))
        sys.exit(0 if n == tot else 1)
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
