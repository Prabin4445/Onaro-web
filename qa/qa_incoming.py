#!/usr/bin/env python3
"""HUB QA: full-screen incoming-call UI + Web Push groundwork.
Covers: incoming screen renders (caller/avatar/group/controls) dark+light,
selected ringtone starts, Answer stops + accept once, Decline stops + reject
once, Escape declines, 45s-timeout path (forced via _missedNow) records a
missed call in Notification Center, preview button from empty call, no
overflow, zero uncaught errors, push honest-degrades without worker/VAPID,
manifest link present, lazy de locale carries the new keys with fresh kh.
Fresh profile, 390x844."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9437
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-inc'
errors, checks = [], []
def note(ok, label, detail=''):
    checks.append((ok, label)); print(('PASS' if ok else 'FAIL'), label, detail)

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12); self.id = 0
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 15
        while time.time() < deadline:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:80])
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)
    def js(self, expr, awaitPromise=False):
        try:
            r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': awaitPromise})
            res = (r or {}).get('result', {})
            return res.get('value'), res.get('exceptionDetails')
        except Exception as e: return None, str(e)[:160]

def targets():
    with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=5) as r:
        return json.load(r)
def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
def hook_err(c):
    c.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
def drain_err(c, label):
    v, _ = c.js("window.__huberr.splice(0)")
    if v: errors.append((label, v)); print('ERRORS @', label, ':', json.dumps(v)[:400])
def wait_js(c, expr, timeout=15):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v, _ = c.js(expr)
        if v: return v
        time.sleep(0.5)
    return None
def seed(c, name):
    c.js("(()=>{const p=HUB.store.state.profile; p.name=%s; p.campus='QA Campus'; HUB.store.save(); HUB.ui.closeSheet(); const w=document.getElementById('wlcmHost'); if(w) w.remove(); return 'seeded'})()" % json.dumps(name))
    c.js("(()=>{const s=HUB.store.state; s.cgroups=s.cgroups||[]; if(!s.cgroups.find(g=>g.id==='qa-inc-g')) s.cgroups.push({id:'qa-inc-g',name:'QA Call Group',emoji:'📞',mine:true,live:true,members:[],chat:[]}); HUB.store.save(); return 'ok'})()")
def set_theme(c, dark):
    c.js("(()=>{HUB.store.state.prefs.dark=%s; HUB.store.save(); HUB.applyTheme(); return 't'})()" % ('true' if dark else 'false'))
    time.sleep(0.8)
def no_overflow(c):
    v, _ = c.js("document.documentElement.scrollWidth<=window.innerWidth")
    return bool(v)
SHOW = "HUB.incoming.show({name:'Maya Shrestha',kind:'voice',groupName:'Family Group',demo:true,accept:function(){window.__acc=(window.__acc||0)+1},reject:function(){window.__rej=(window.__rej||0)+1}})"
VIS = "!document.getElementById('incallRoot').hidden"

def flow(c, theme):
    set_theme(c, theme == 'dark')
    seed(c, 'Prabin QA')
    # --- show incoming ---
    v, _ = c.js("(()=>{%s; return %s})()" % (SHOW, VIS))
    note(bool(v), f'{theme}: incoming screen visible')
    v, _ = c.js("document.getElementById('incName').textContent")
    note(v == 'Maya Shrestha', f'{theme}: caller name', repr(v))
    v, _ = c.js("document.getElementById('incSub').textContent")
    note(v == 'Family Group', f'{theme}: group name', repr(v))
    v, _ = c.js("document.getElementById('incTag').hidden===false")
    note(bool(v), f'{theme}: demo tag visible')
    v, _ = c.js("document.getElementById('incAnswer')&&document.getElementById('incDecline')?true:false")
    note(bool(v), f'{theme}: Answer + Decline controls present')
    time.sleep(1.2)
    v, _ = c.js("HUB.sound.isRinging()")
    note(bool(v), f'{theme}: ringtone playing')
    note(no_overflow(c), f'{theme}: no horizontal overflow')
    shot(c, f'incoming-{theme}')
    # --- Answer: accept once, ringtone stops, screen hides ---
    c.js("window.__acc=0;window.__rej=0;document.getElementById('incAnswer').click()")
    time.sleep(0.6)
    v, _ = c.js("window.__acc")
    note(v == 1, f'{theme}: answer ran accept exactly once', repr(v))
    v, _ = c.js("HUB.sound.isRinging()")
    note(not v, f'{theme}: ringtone stopped after answer')
    v, _ = c.js("document.getElementById('incallRoot').hidden")
    note(bool(v), f'{theme}: screen hidden after answer')
    # --- Decline: reject once ---
    c.js("(()=>{%s})()" % SHOW)
    time.sleep(0.5)
    c.js("window.__acc=0;window.__rej=0;document.getElementById('incDecline').click()")
    time.sleep(0.6)
    v, _ = c.js("window.__rej")
    note(v == 1, f'{theme}: decline ran reject exactly once', repr(v))
    v, _ = c.js("HUB.sound.isRinging()")
    note(not v, f'{theme}: ringtone stopped after decline')
    # --- Escape declines ---
    c.js("(()=>{window.__rej=0;%s})()" % SHOW)
    time.sleep(0.5)
    c.send('Input.dispatchKeyEvent', {'type': 'rawKeyDown', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
    time.sleep(0.6)
    v, _ = c.js("window.__rej")
    note(v == 1, f'{theme}: Escape declined the call', repr(v))
    drain_err(c, f'{theme} incoming flow')

def main():
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--disable-dev-shm-usage', f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        f'--user-data-dir={PROF}', '--allow-file-access-from-files', '--hide-scrollbars',
        '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
        '--autoplay-policy=no-user-gesture-required',
        '--no-first-run', '--no-default-browser-check', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(1)
        try:
            targets(); break
        except Exception:
            pass
    else:
        proc.terminate(); raise SystemExit('chrome did not come up')
    try:
        t = [x for x in targets() if x['type'] == 'page'][0]
        c = CDP(t['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable')
        c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        c.send('Page.navigate', {'url': BASE})
        wait_js(c, "window.HUB&&HUB.incoming&&HUB.incoming.show?true:false", 25)
        hook_err(c)
        # module present
        v, _ = c.js("!!(HUB.incoming&&HUB.push&&HUB.push.setOn)")
        note(bool(v), 'HUB.incoming + HUB.push present')
        v, _ = c.js("!!document.querySelector('link[rel=manifest]')")
        note(bool(v), 'manifest link present')
        flow(c, 'dark')
        flow(c, 'light')
        # --- missed call path (forced timeout) -> Notification Center ---
        set_theme(c, True); seed(c, 'Prabin QA')
        c.js("(()=>{HUB.store.state.missedCalls=[];HUB.store.save();%s;HUB.incoming._missedNow();})()" % SHOW)
        time.sleep(1.0)
        v, _ = c.js("HUB.store.state.missedCalls.length")
        note(v == 1, 'missed call recorded in store', repr(v))
        v, _ = c.js("HUB.store.state.missedCalls[0]&&HUB.store.state.missedCalls[0].name")
        note(v == 'Maya Shrestha', 'missed call has caller name', repr(v))
        v, _ = c.js("document.querySelectorAll('.toasthost .toast').length>0||document.querySelectorAll('#toastHost .toast').length>0")
        note(bool(v), 'missed-call toast shown')
        c.js("HUB.notifications.open()")
        time.sleep(0.8)
        v, _ = c.js("document.getElementById('hubNotifRows').textContent")
        note(v and 'Maya Shrestha' in v, 'missed call in Notification Center', (v or '')[:120])
        shot(c, 'incoming-missed-center')
        c.js("HUB.notifications.close&&HUB.notifications.close()")
        # --- empty-call preview button -> incoming screen ---
        c.js("HUB.call.start('qa-inc-g')")
        time.sleep(1.5)
        v, _ = c.js("(()=>{const b=[...document.querySelectorAll('.callroot button')].find(x=>x.textContent&&x.textContent.indexOf('incoming call')>-1); if(!b) return 'BTN-MISSING'; b.click(); return 'clicked'})()")
        note(v == 'clicked', 'empty-call preview button clicked', repr(v))
        time.sleep(0.8)
        v, _ = c.js("document.getElementById('incName').textContent+'|'+(!document.getElementById('incallRoot').hidden)")
        note(v and v.startswith('Demo caller|true'), 'preview opens demo incoming screen', repr(v))
        note(no_overflow(c), 'no overflow on preview screen')
        shot(c, 'incoming-preview')
        c.js("document.getElementById('incDecline').click();HUB.call&&HUB.call.leave()")
        time.sleep(0.8)
        # --- push honest degradation ---
        v, _ = c.js("HUB.push._debug()")
        note(isinstance(v, dict) and v.get('supported') and not v.get('on'), 'push debug: supported, off', repr(v))
        note(isinstance(v, dict) and not v.get('vapidSet'), 'push debug: VAPID placeholder unset', repr(v))
        note(isinstance(v, dict) and not v.get('worker'), 'push debug: no worker deployed', repr(v))
        v, _ = c.js("HUB.push.setOn(true)", awaitPromise=True)
        note(isinstance(v, dict) and not v.get('ok') and v.get('reason') == 'noVapid',
             'push setOn(true) degrades honestly (noVapid)', repr(v))
        v, _ = c.js("HUB.store.state.prefs.pushOn===false")
        note(bool(v), 'push pref stays OFF after failed subscribe')
        # --- de lazy locale with fresh hash ---
        v, _ = c.js("HUB.i18n.loadLocale('de')", awaitPromise=True)
        v, _ = c.js("HUB.i18n._dict('de')!==HUB.i18n._dict('en')&&HUB.i18n._dict('de')['inc.answer']")
        note(v == 'Annehmen', 'de locale carries inc.answer (real load)', repr(v))
        # --- i18n hash consistency (filesystem, real data; en is bundled in js/i18n.js) ---
        import glob as _g
        files = sorted(_g.glob(os.path.expanduser('~/workspace/hub/data/locales/*.json')))
        ref = json.load(open(files[0])); rks = set(ref['values'].keys())
        khok = len(files) == 24
        for fp in files:
            d = json.load(open(fp))
            if d.get('kh') != 'msvnpp' or set(d['values'].keys()) != rks or len(rks) != 1627:
                khok = False; print('KH MISMATCH:', fp)
        note(khok, 'all 24 lazy locales: 1627 identical keys, kh=msvnpp')
        v, _ = c.js("Object.keys(HUB.i18n._dict('en')).length")
        note(v == 1627, 'bundled English dict has 1627 keys', repr(v))
        drain_err(c, 'tail')
    finally:
        proc.terminate()
    print('\n==== %d/%d passed ====' % (sum(1 for ok, _ in checks if ok), len(checks)))
    if errors: print('JS ERRORS:', errors)
    bad = [l for ok, l in checks if not ok]
    if bad: print('FAILED:', bad); raise SystemExit(1)

if __name__ == '__main__':
    main()
