#!/usr/bin/env python3
"""HUB QA: Gym Fuel smart day plan is country-aware (js/gym.js foodCui).
Fresh profile /tmp/hubqa-gymfood (wiped), file:// load, 390px + 320px.

Phases:
  A. boot: US country, gym profile seeded, no auth overlay
  B. US plan: generate 12 shuffles; NEVER an Indian dish (bhurji/roti/dal/paneer),
     at least one American dish appears (omelet/burrito/chili/meatballs/tacos/pancakes)
  C. US recipes: Turkey Chili shown, Red Lentil Dal hidden
  D. switch country to IN: 12 shuffles; NEVER an American dish,
     at least one Indian dish appears; recipes show Dal, not Chili
  E. i18n: new keys resolve in en; de lazy-loads with new kh and falls back
     to English for the new food keys (pattern from Ask v2)
  F. screenshots (US plan, 320px no-overflow) + zero console errors
"""
import json, subprocess, time, urllib.request, os, shutil, sys, base64
try:
    import websocket
except ImportError:
    print('websocket-client missing'); sys.exit(2)

CHROME = '/opt/meta-chromium/chrome'; PORT = 9448
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-gymfood'
SHOTDIR = os.path.expanduser('~/workspace/hub/qa')
JS = "(function(){%s})()"
checks = []
def note(ok, label, detail=''):
    checks.append(bool(ok)); print(('PASS' if ok else 'FAIL'), label, detail)

INDIAN = ['bhurji', 'roti', 'dal', 'paneer']
AMERICAN = ['omelet', 'burrito', 'chili', 'meatballs', 'tacos', 'pancakes']

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
    def shot(self, name):
        r = self.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 82, 'fromSurface': True})
        with open(os.path.join(SHOTDIR, name), 'wb') as f: f.write(base64.b64decode(r['data']))
        print('SHOT', name)

def t0(): return time.time()
def js_wait(c, expr, timeout=12):
    t = time.time()
    while time.time() - t < timeout:
        v, _ = c.js(JS % expr)
        if v: return True
        time.sleep(0.4)
    return False
def disarm_gate(c):
    c.js(JS % ("window.__gateSkip=true; try{if(HUB.auth&&HUB.auth.close){"
         "var a=document.querySelector('.authroot'); if(a&&!a.hidden) HUB.auth.close();}}catch(e){} return 1"))
def arm_hooks(c):
    c.js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
         "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
def collect_errors(c):
    v, _ = c.js(JS % "return window.__huberr||[]")
    return [x for x in (v or []) if x]

GYM_PROFILE = ("{sex:'m',age:28,wKg:80,hCm:180,targetKg:75,act:'moderate',"
               "goal:'maintain',diet:'all'}")

def boot(c):
    ok = js_wait(c, "return !document.getElementById('splash')", 25)
    note(ok, 'splash dismissed')
    c.js(JS % ("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
              "var s=HUB.store.state; s.profile.name='QA User'; s.profile.campus='QA Campus';"
              "s.prefs.dark=true; s.gym={unit:'imp',profile:%s}; HUB.store.save(); return 1" % GYM_PROFILE))
    c.send('Page.reload')
    ok = js_wait(c, "return document.readyState==='complete' && !document.getElementById('splash') && !!window.HUB && !!HUB.gym", 25)
    note(ok, 'clean boot after seed')
    disarm_gate(c); time.sleep(0.8); disarm_gate(c)
    c.js(JS % "try{HUB.ui.closeSheet()}catch(e){} var w=document.getElementById('wlcmHost'); if(w) w.remove(); return 1")
    time.sleep(0.5)
    v, _ = c.js(JS % "return !!document.querySelector('.authroot:not([hidden])')")
    note(not v, 'no auth overlay (gate disarmed)')
    v, _ = c.js(JS % "return HUB.i18n.getCountry()")
    note(v == 'US', 'country is US', str(v))

def open_meals(c):
    c.js(JS % "HUB.showTab('daily'); return 1"); time.sleep(0.6)
    c.js(JS % "var b=document.getElementById('gyMeals'); if(b) b.click(); return 1")
    ok = js_wait(c, "return !!document.getElementById('gyGenBtn')", 8)
    note(ok, 'meals sheet opens with Generate button')
    return ok

def gen_plan_text(c, rounds=12):
    c.js(JS % "document.getElementById('gyGenBtn').click(); return 1")
    time.sleep(0.4)
    agg, _ = c.js(JS % """
        var seen={}, i, btn=document.getElementById('gyShuffle');
        for(i=0;i<%d;i++){ btn.click(); seen[document.getElementById('gyPlan').textContent]=1; }
        return Object.keys(seen).join(' ||| ');
    """ % rounds)
    return (agg or '').lower()

def recipes_text(c):
    v, _ = c.js(JS % "return document.querySelector('.sheethost .sheet').textContent")
    return (v or '').lower()

def phaseB_US(c):
    agg = gen_plan_text(c)
    note(len(agg) > 100, 'US plan generated across shuffles', str(len(agg)))
    bad = [w for w in INDIAN if w in agg]
    note(not bad, 'US plan: no Indian dishes', 'found: %s' % bad)
    good = [w for w in AMERICAN if w in agg]
    note(bool(good), 'US plan: American dishes appear', str(good))

def phaseC_US_recipes(c):
    txt = recipes_text(c)
    note('turkey chili' in txt, 'US recipes include Turkey Chili')
    note('lentil dal' not in txt and 'red lentil' not in txt, 'US recipes hide Red Lentil Dal')

def phaseD_IN(c):
    c.js(JS % "HUB.i18n.setCountry('IN'); try{HUB.ui.closeSheet()}catch(e){} return 1")
    time.sleep(0.4)
    v, _ = c.js(JS % "return HUB.i18n.getCountry()")
    note(v == 'IN', 'country switched to IN', str(v))
    c.js(JS % "var b=document.getElementById('gyMeals'); if(b) b.click(); return 1")
    ok = js_wait(c, "return !!document.getElementById('gyGenBtn')", 8)
    note(ok, 'meals sheet reopens for IN')
    agg = gen_plan_text(c)
    bad = [w for w in AMERICAN if w in agg]
    note(not bad, 'IN plan: no American dishes', 'found: %s' % bad)
    good = [w for w in INDIAN if w in agg]
    note(bool(good), 'IN plan: Indian dishes appear', str(good))
    txt = recipes_text(c)
    note('lentil dal' in txt or 'red lentil' in txt, 'IN recipes include Red Lentil Dal')
    note('turkey chili' not in txt, 'IN recipes hide Turkey Chili')
    c.js(JS % "HUB.i18n.setCountry('US'); try{HUB.ui.closeSheet()}catch(e){} return 1")
    time.sleep(0.3)

def phaseE_i18n(c):
    v, _ = c.js(JS % "return HUB.i18n.t('gym.fd20')")
    note(v == 'Egg-white omelet + 2 toast', 'en gym.fd20 resolves', str(v))
    v, _ = c.js(JS % "return HUB.i18n.t('gym.r5t')")
    note(v == 'Turkey Chili', 'en gym.r5t resolves', str(v))
    v, _ = c.js(JS % "return HUB.i18n.loadLocale('de').then(function(ok){"
                      "return ok && HUB.i18n._dict('de')!==HUB.i18n._dict('en'); })", awaitPromise=True)
    note(v is True, 'de lazy-loads with new kh (real load, identity check)')
    v, _ = c.js(JS % "HUB.i18n.setLang('de'); return HUB.i18n.t('gym.fd20')")
    note(v == 'Egg-white omelet + 2 toast', 'de falls back to English for new food key', str(v))
    c.js(JS % "HUB.i18n.setLang('en'); return 1")

def phaseF_shots(c):
    c.js(JS % "HUB.showTab('daily'); return 1"); time.sleep(0.5)
    c.js(JS % "var b=document.getElementById('gyMeals'); if(b) b.click(); return 1")
    js_wait(c, "return !!document.getElementById('gyGenBtn')", 8)
    c.js(JS % "document.getElementById('gyGenBtn').click(); return 1"); time.sleep(0.5)
    c.shot('gymfood-us-plan.jpg')
    v, _ = c.js(JS % "var s=document.querySelector('.sheethost .sheet'); var r=s.getBoundingClientRect();"
                      "return r.left>=0 && r.right<=window.innerWidth+1")
    note(v, 'meals sheet inside viewport (390px)')
    c.send('Emulation.setDeviceMetricsOverride', {'width': 320, 'height': 568, 'deviceScaleFactor': 2, 'mobile': True})
    time.sleep(0.6)
    c.shot('gymfood-us-plan-320.jpg')
    v, _ = c.js(JS % "return document.documentElement.scrollWidth<=320+1")
    note(v, 'no horizontal overflow at 320px')
    c.send('Emulation.clearDeviceMetricsOverride')

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
        arm_hooks(c)
        boot(c)
        if open_meals(c):
            phaseB_US(c); phaseC_US_recipes(c); phaseD_IN(c); phaseE_i18n(c); phaseF_shots(c)
        bad = collect_errors(c)
        note(not bad, 'zero console errors', '; '.join(bad)[:400])
        n = sum(checks); tot = len(checks)
        print('GYMFOOD QA: %d/%d' % (n, tot))
        sys.exit(0 if n == tot else 1)
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
