#!/usr/bin/env python3
"""Gymwork UI QA: wizard -> plan home -> day view -> player full flow ->
celebration -> badge -> buddies -> ME badge -> light mode -> 320px -> reload."""
import json, subprocess, time, urllib.request, os, base64, socket, shutil
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
import random
PORT = 9400 + random.randint(0, 400)
PROFILE = '/tmp/hubqa-gw-%d-%d' % (os.getpid(), int(time.time()))
os.makedirs(QA, exist_ok=True)

def port_open():
    s = socket.socket(); s.settimeout(1)
    try: s.connect(('localhost', PORT)); return True
    except OSError: return False

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl); self.id = 0
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 30
        while time.time() < deadline:
            msg = json.loads(self.ws.recv())
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)

BASE = 'file:///home/hatch/workspace/hub/index.html'

def main():
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        '--allow-file-access-from-files', f'--user-data-dir={PROFILE}',
        '--hide-scrollbars', '--autoplay-policy=no-user-gesture-required', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tgt = None
    for _ in range(60):
        try:
            with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=2) as r:
                for t in json.load(r):
                    if t['type'] == 'page' and 'devtools' not in t['url']: tgt = t
            if tgt: break
        except Exception:
            time.sleep(0.5)
    if not tgt: raise RuntimeError('no page target after 30s')
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable'); c.send('Page.enable')
    fails = []
    def js(expr, await_=False):
        # IIFE-wrap: bare `return` is a SyntaxError in Runtime.evaluate
        r = c.send('Runtime.evaluate', {'expression': '(function(){' + expr + '})()',
            'awaitPromise': await_, 'returnByValue': True})
        res = (r or {}).get('result', {})
        return res.get('value'), res.get('exceptionDetails')
    def check(name, cond, extra=''):
        print(('PASS' if cond else 'FAIL'), name, extra)
        if not cond: fails.append(name)
    def shot(name):
        js("var w=document.getElementById('wlcmHost');if(w)w.remove();return 1")
        r = c.send('Page.captureScreenshot', {'format': 'png'})
        p = os.path.join(QA, name + '.png')
        open(p, 'wb').write(base64.b64decode(r['data']))
        print('shot:', p)
    def set_viewport(w, h):
        c.send('Emulation.setDeviceMetricsOverride',
            {'width': w, 'height': h, 'deviceScaleFactor': 2, 'mobile': True})
        time.sleep(0.4)
    def no_overflow(name):
        v, _ = js("return {sw:document.documentElement.scrollWidth, iw:window.innerWidth}")
        check(name + ' no-h-overflow', v['sw'] <= v['iw'], str(v))
    def errors():
        v, _ = js("return (window.__huberr||[]).slice(0,8)")
        return v or []

    js("window.__huberr=[];window.addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
       "window.addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+(e.reason&&e.reason.message||e.reason)));return 1")
    # Seed onboarding-complete BEFORE page scripts run, so the welcome overlay never builds.
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source':
        "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))}catch(e){}"})
    c.send('Page.reload')
    # wait for boot
    for _ in range(40):
        v, _ = js("return !!(window.HUB&&HUB.store&&HUB.gymwork&&HUB.gymworkData&&HUB.gymworkAnim)")
        if v: break
        time.sleep(0.5)
    check('boot HUB.gymwork', bool(v))
    # disarm auth gate + splash
    js("window.__gateSkip=true;try{HUB.auth.close()}catch(e){};"
       "var w=document.getElementById('wlcmHost');if(w)w.remove();"
       "var sp=document.getElementById('splash');if(sp)sp.remove();return 1")
    set_viewport(390, 844)
    js("HUB.showTab('daily');return 1")
    time.sleep(1.2)
    v, _ = js("return !!document.getElementById('gwOpen')")
    check('entry card present (wrap of gym.cardHTML)', bool(v))
    shot('gw-entry-dark'); no_overflow('entry')

    # ---- wizard ----
    js("document.getElementById('gwOpen').click();return 1"); time.sleep(0.6)
    shot('gw-wiz-level')
    js("document.querySelector('[data-wlvl=intermediate]').click();return 1"); time.sleep(0.3)
    js("document.getElementById('gwWizNext').click();return 1"); time.sleep(0.6)
    shot('gw-wiz-split')
    js("document.querySelector('[data-wsplit=lpp]').click();return 1"); time.sleep(0.3)
    js("document.getElementById('gwWizNext').click();return 1"); time.sleep(0.6)
    shot('gw-wiz-days')
    js("document.querySelector('[data-wday=tue]').click();return 1"); time.sleep(0.3)  # cycle tue
    js("document.getElementById('gwWizNext').click();return 1"); time.sleep(0.8)  # Done -> plan home
    v, _ = js("return HUB.gymwork._debug.state()")
    check('wizard saved plan', v and v['level'] == 'intermediate' and v['order'][0] == 'legs', str(v.get('order')) if v else '')
    v2, _ = js("return document.querySelector('.gw-panel')?'open':'closed'")
    check('plan home overlay open after wizard', v2 == 'open')
    shot('gw-plan-dark'); no_overflow('plan-home')

    # ---- deterministic full-flow run ----
    js("HUB.gymwork._debug.reset();HUB.gymwork._debug.seedPlan();return 1")
    js("HUB.gymwork.openPlan();return 1"); time.sleep(0.6)
    v, _ = js("return HUB.gymwork._debug.state().days")
    print('seeded days:', v)
    js("HUB.gymwork.startWorkout();return 1"); time.sleep(0.8)  # first tap -> earn sheet
    v, _ = js("return {badge:!!HUB.store.state.gym.workoutBadge, sheet:!!document.querySelector('.gw-cele')}")
    check('BEAST badge awarded on first Start', v['badge'] and v['sheet'], str(v))
    shot('gw-earn')
    js("var b=document.querySelector('.gw-cele [data-close]');if(b)b.click();return 1"); time.sleep(0.5)
    v, _ = js("return document.getElementById('sheetHost').hidden")
    check('earn sheet closed via data-close', bool(v))
    js("HUB.gymwork.startWorkout();return 1"); time.sleep(0.8)  # second tap -> straight to day
    v, _ = js("return {day:!!document.getElementById('gwov-day'),"
               "cele:!!document.querySelector('#sheetBox .gw-cele')&&!document.getElementById('sheetHost').hidden}")
    check('second Start skips earn sheet', v['day'] and not v['cele'], str(v))
    shot('gw-day'); no_overflow('day-view')
    v, _ = js("return document.querySelectorAll('#gwov-day .gw-thumb img').length")
    check('day rows have anim thumbs', v and v >= 3, str(v))  # beginner pull day = 3 exercises

    # ---- player ----
    js("document.querySelector('#gwov-day .gw-exrow:not(.gw-done)').click();return 1"); time.sleep(0.8)
    shot('gw-player'); no_overflow('player')
    v, _ = js("return {vid:!!document.querySelector('#gwov-player .gw-stage video'),"
               "chips:document.querySelectorAll('#gwov-player .gw-mchip').length,"
               "t1:(function(){var vd=document.querySelector('#gwov-player .gw-stage video');"
               "return vd?vd.currentTime:null;})()}")
    time.sleep(0.7)
    t2, _ = js("return (function(){var vd=document.querySelector('#gwov-player .gw-stage video');"
               "return vd?{ct:vd.currentTime,paused:vd.paused,rs:vd.readyState}:null;})()")
    check('player renders anim + muscle chips',
          v['vid'] and t2 and t2['ct'] is not None and (t2['ct'] > (v['t1'] or 0) or not t2['paused']) and v['chips'] > 0,
          str({'vid':v['vid'],'t1':v['t1'],'t2':t2,'chips':v['chips']}))
    # drive the whole day through the real UI (celebration = VISIBLE sheet with #gwFinish;
    # the hidden earn sheet also uses .gw-cele, so require visibility + the finish button)
    js("window.__gwDriver=function(){return new Promise(function(res){var n=0;"
       "var iv=setInterval(function(){n++;"
       "function click(id){var b=document.getElementById(id);if(b){b.click();return true;}return false;}"
       "var sh=document.getElementById('sheetHost');"
       "if(sh&&!sh.hidden&&document.getElementById('gwFinish')){clearInterval(iv);res('celebration');return;}"
       "if(n>900){clearInterval(iv);res('timeout');return;}"
       "if(click('gwPComplete'))return;if(click('gwPSkip'))return;if(click('gwPDone'))return;if(click('gwPStart'))return;"
       "var row=document.querySelector('#gwov-day .gw-exrow:not(.gw-done)');if(row){row.click();return;}"
       "},200);});};return 1")
    v, _ = js("return window.__gwDriver()", await_=True)
    check('full day flow completes', v == 'celebration', str(v))
    time.sleep(0.6); shot('gw-celebration')
    v, _ = js("return HUB.gymwork._debug.state().log")
    n_done = sum(1 for d in (v or {}).values() for e in d.values() if e.get('done'))
    check('log has done exercises', n_done >= 3, 'done=%d' % n_done)  # beginner pull day = 3
    js("document.getElementById('gwFinish').click();return 1"); time.sleep(0.8)
    v, _ = js("return document.querySelector('#gwov-plan .gw-prog')?document.querySelector('#gwov-plan .gw-prog').textContent:''")
    print('today progress:', v)
    shot('gw-plan-done')

    # ---- ME profile badge ----
    js("HUB.showTab('me');return 1"); time.sleep(1.0)
    v, _ = js("return {badge:document.querySelectorAll('#view-me .gw-beastbadge').length,"
               "gwOpen:document.querySelectorAll('.gw-root').length,"
               "wrapped:!!HUB._gwShowTab}")
    check('ME profile shows beast badge (headerHTML wrap)', v['badge'] and v['badge'] > 0, str(v))
    check('tab switch closes gymwork overlays', v['wrapped'] and v['gwOpen'] == 0, str(v))
    shot('gw-me-dark')
    js("document.querySelector('#view-me .gw-beastbadge').click();return 1"); time.sleep(0.6)
    shot('gw-badge-info')
    v, _ = js("return !!document.querySelector('#sheetBox .gw-cele')")
    check('badge tap opens info sheet', bool(v))
    js("HUB.ui.closeSheet();return 1"); time.sleep(0.4)

    # ---- buddies chat wiring: seed one MUTUAL follow + one one-way follow ----
    js("var ps=HUB.store.state.people.filter(function(x){return x&&x.sample;});"
       "var p=ps[0],q=ps[1];"
       "HUB.store.state.following=[p.id,q.id];HUB.store.state.followers=[p.id];"  # q follows nobody back
       "HUB.store.save();window.__gwP=p;window.__gwQ=q;return 1")
    js("HUB.gymwork.openPlan();return 1"); time.sleep(0.6)
    v, _ = js("return {n:document.querySelectorAll('#gwov-plan .gw-buddy').length,"
               "names:(function(){var a=[];document.querySelectorAll('#gwov-plan .gw-buddyname').forEach(function(e){a.push(e.textContent);});return a;})(),"
               "chat:document.querySelectorAll('#gwov-plan [data-gwchat]').length,"
               "qname:window.__gwQ.name}")
    print('buddies:', v)
    check('mutual buddy shown, one-way follow hidden',
          v['n'] == 1 and v['qname'] not in v['names'], str(v))
    js("window.__gwChatArgs=null;var _ow=HUB.chat.openWith;"
       "HUB.chat.openWith=function(a,b,c){window.__gwChatArgs=[a,b,c];return _ow(a,b,c);};return 1")
    js("document.querySelector('#gwov-plan [data-gwchat]').click();return 1"); time.sleep(0.8)
    v, _ = js("return {args:window.__gwChatArgs,pname:window.__gwP.name}")
    a = (v['args'] or [None, None, None])
    check('buddy Chat calls HUB.chat.openWith with buddy name + skipSafety',
          a[0] and a[0].get('name') == v['pname'] and isinstance(a[0].get('phone'), str)
          and a[2] and a[2].get('skipSafety') is True,
          str({'name': a[0].get('name') if a[0] else None, 'skipSafety': (a[2] or {}).get('skipSafety')}))
    js("HUB.chat.close();HUB.gymwork.openPlan();return 1"); time.sleep(0.6)

    # ---- light mode ----
    js("document.body.classList.remove('dark');return 1"); time.sleep(0.4)
    shot('gw-plan-light'); no_overflow('plan-light')
    js("HUB.gymwork.openDay('push');return 1"); time.sleep(0.6)
    shot('gw-day-light'); no_overflow('day-light')
    js("document.body.classList.add('dark');HUB.gymwork.openPlan();return 1"); time.sleep(0.5)

    # ---- 320px ----
    set_viewport(320, 700)
    shot('gw-plan-320'); no_overflow('plan-320')
    js("HUB.gymwork.openDay('push');return 1"); time.sleep(0.6)
    shot('gw-day-320'); no_overflow('day-320')

    # ---- reload persistence ----
    v, _ = js("return {badge:!!HUB.store.state.gym.workoutBadge,"
               "logKeys:Object.keys((HUB.gymwork._debug.state()||{log:{}}).log||{}).length}")
    print('pre-reload:', v)
    c.send('Page.reload'); time.sleep(3)
    for _ in range(40):
        vv, _ = js("return !!(window.HUB&&HUB.gymwork)")
        if vv: break
        time.sleep(0.5)
    v, _ = js("return {badge:!!(HUB.store.state.gym&&HUB.store.state.gym.workoutBadge),"
               "plan:!!(HUB.gymwork._debug.state()),"
               "logKeys:Object.keys((HUB.gymwork._debug.state()||{log:{}}).log||{}).length}")
    check('state persists across reload', v['badge'] and v['plan'] and v['logKeys'] > 0, str(v))

    err = errors()
    check('zero console errors', len(err) == 0, str(err))
    print('\nRESULT:', 'ALL PASS' if not fails else 'FAILURES: %s' % fails)
    proc.terminate()

main()
