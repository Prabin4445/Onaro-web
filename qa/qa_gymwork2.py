#!/usr/bin/env python3
"""Gymwork expansion QA: sections (warmup/abs/pilates/zumba), level switching,
teaching cards, video routing for all 99 exercises, standalone completion,
320/390px dark+light, zero console errors."""
import json, subprocess, time, urllib.request, os, base64, socket, random
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9500 + random.randint(0, 400)
PROFILE = '/tmp/hubqa-gw2-%d-%d' % (os.getpid(), int(time.time()))
os.makedirs(QA, exist_ok=True)

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
    if not tgt: raise RuntimeError('no page target')
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable'); c.send('Page.enable')
    fails = []
    def js(expr, await_=False):
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
        v, _ = js("return (window.__huberr||[]).slice(0,10)")
        return v or []

    js("window.__huberr=[];window.addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
       "window.addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+(e.reason&&e.reason.message||e.reason)));return 1")
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source':
        "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))}catch(e){}"})
    c.send('Page.reload')
    for _ in range(40):
        v, _ = js("return !!(window.HUB&&HUB.store&&HUB.gymwork&&HUB.gymworkData&&HUB.gymworkAnim)")
        if v: break
        time.sleep(0.5)
    check('boot', bool(v))
    js("window.__gateSkip=true;try{HUB.auth.close()}catch(e){};"
       "var w=document.getElementById('wlcmHost');if(w)w.remove();"
       "var sp=document.getElementById('splash');if(sp)sp.remove();return 1")
    set_viewport(390, 844)

    # ---- data integrity ----
    v, _ = js("return {n:HUB.gymworkData.EXERCISES.length,"
              "warmup:HUB.gymworkData.sectionExercises('warmup').length,"
              "abs:HUB.gymworkData.sectionExercises('abs').length,"
              "pilates:HUB.gymworkData.sectionExercises('pilates').length,"
              "zumba:HUB.gymworkData.sectionExercises('zumba').length,"
              "cooldown:HUB.gymworkData.sectionExercises('cooldown').length,"
              "anim:HUB.gymworkAnim.EXERCISES.length}")
    check('data: 99 exercises, sections 10/14/12/10/8, anim list 99',
          v == {'n':99,'warmup':10,'abs':14,'pilates':12,'zumba':10,'cooldown':8,'anim':99}, str(v))
    v, _ = js("return (function(){var a=HUB.gymworkData.EXERCISES.map(function(e){return e.id;}).sort();"
              "var b=HUB.gymworkAnim.EXERCISES.slice().sort();"
              "return a.length===b.length&&a.every(function(x,i){return x===b[i];});})()")
    check('anim ID list matches data IDs exactly', bool(v))
    v, _ = js("return HUB.gymworkData.EXERCISES.every(function(e){"
              "return e.teach&&e.teach.setup&&e.teach.steps.length===4&&e.teach.breathing&&"
              "e.teach.mistakes.length===3&&e.cues.length===3;})")
    check('every exercise has full teaching (setup/4 steps/breathing/3 mistakes/3 cues)', bool(v))

    # ---- video + poster files exist for all 99 ----
    v, _ = js("return Promise.all(HUB.gymworkAnim.EXERCISES.map(function(id){"
              "return fetch('videos/gym/'+id+'.mp4',{method:'HEAD'}).then(function(r){return r.ok?id:null;})"
              ".catch(function(){return null;});})).then(function(a){return a.filter(Boolean);})", await_=True)
    check('all 99 mp4 files load', isinstance(v, list) and len(v) == 99,
          'loaded=%d' % (len(v) if isinstance(v, list) else -1))
    v, _ = js("return Promise.all(HUB.gymworkAnim.EXERCISES.map(function(id){"
              "return fetch('videos/gym/'+id+'-poster.jpg',{method:'HEAD'}).then(function(r){return r.ok?id:null;})"
              ".catch(function(){return null;});})).then(function(a){return a.filter(Boolean);})", await_=True)
    check('all 99 poster files load', isinstance(v, list) and len(v) == 99,
          'loaded=%d' % (len(v) if isinstance(v, list) else -1))

    # ---- level programs genuinely differ ----
    v, _ = js("return (function(){var d=HUB.gymworkData;"
              "function sig(lv){return ['push','pull','legs'].map(function(g){"
              "return d.exercisesFor(g,lv).map(function(e){return e.id;}).join(',');}).join('|');}"
              "return {b:sig('beginner'),i:sig('intermediate'),a:sig('advanced')};})()")
    check('level programs differ', v and v['b'] != v['i'] and v['i'] != v['a'] and v['b'] != v['a'],
          str({k: len(x) for k, x in (v or {}).items()}))

    # ---- UI: plan home, sections, levels ----
    js("HUB.gymwork._debug.reset();HUB.gymwork._debug.seedPlan();HUB.gymwork.openPlan();return 1")
    time.sleep(0.8)
    v, _ = js("return document.querySelectorAll('.gw-secrow [data-gwsec]').length")
    check('6 section chips', v == 6, str(v))
    v, _ = js("return document.querySelectorAll('.gw-lvlrow [data-gwlvl]').length")
    check('3 level buttons', v == 3, str(v))
    for sid, n in [('warmup',10),('abs',14),('pilates',12),('zumba',10),('cooldown',8)]:
        js("document.querySelector('[data-gwsec=\"%s\"]').click();return 1" % sid); time.sleep(0.6)
        v, _ = js("return document.querySelectorAll('#gwov-section .gw-exrow').length")
        check('section %s lists %d exercises' % (sid, n), v == n, str(v))
        no_overflow('section-' + sid)
    shot('gw2-section-zumba')
    js("document.querySelector('[data-gwsec=\"plan\"]').click();return 1"); time.sleep(0.6)

    # ---- standalone section completion (warmup, 10 exercises) ----
    js("document.querySelector('[data-gwsec=\"warmup\"]').click();return 1"); time.sleep(0.5)
    v, _ = js("return (function(){var rows=document.querySelectorAll('#gwov-section .gw-exrow');"
              "var out=[];rows.forEach(function(r,i){out.push(r.getAttribute('data-ex')||i);});return out;})()")
    print('warmup rows:', v)
    # ---- complete all 10 via UI: open each, mark done through player complete buttons
    js("window.__gwSecDone=function(){return new Promise(function(res){var n=0;"
       "var iv=setInterval(function(){n++;"
       "function click(id){var b=document.getElementById(id);if(b){b.click();return true;}return false;}"
       "var sh=document.getElementById('sheetHost');"
       "if(sh&&!sh.hidden&&document.getElementById('gwSecFinish')){clearInterval(iv);res('secDone');return;}"
       "if(n>900){clearInterval(iv);res('timeout');return;}"
       "if(click('gwPComplete'))return;if(click('gwPSkip'))return;if(click('gwPDone'))return;if(click('gwPStart'))return;"
       "var row=document.querySelector('#gwov-section .gw-exrow:not(.gw-done)');if(row){row.click();return;}"
       "},200);});};return 1")
    v, _ = js("return window.__gwSecDone()", await_=True)
    check('standalone warmup completes -> celebration', v == 'secDone', str(v))
    shot('gw2-sec-celebration')
    js("document.getElementById('gwSecFinish').click();return 1"); time.sleep(0.8)
    v, _ = js("return !!document.getElementById('gwov-plan')")
    check('section finish returns to plan home', bool(v))

    # ---- level switching preserves logs ----
    js("HUB.gymwork._debug.seedPlan();HUB.gymwork.openPlan();HUB.gymwork.openDay('push');return 1")
    time.sleep(0.6)
    v, _ = js("return (function(){var rows=document.querySelectorAll('#gwov-day .gw-exrow');"
              "return rows.length?rows[0].getAttribute('data-ex'):null;})()")
    first_beg = v
    # mark first exercise done via debug markDone path through player
    js("var b=document.querySelector('#gwov-day .gw-exrow');if(b)b.click();return 1"); time.sleep(0.7)
    v, _ = js("return {setup:!!document.querySelector('#gwov-player .gw-teach'),"
              "video:!!document.querySelector('#gwov-player video'),"
              "src:(document.querySelector('#gwov-player video')||{}).currentSrc||''}")
    check('player: teaching card + video', v['setup'] and v['video'] and 'videos/gym/' in v['src'], str(v))
    shot('gw2-player-teach'); no_overflow('player')
    # drive the player state machine (start->set->rest->idle...) until one exercise is logged done
    js("window.__gwOneDone=function(){return new Promise(function(res){var n=0;"
       "var iv=setInterval(function(){n++;"
       "function click(id){var b=document.getElementById(id);if(b){b.click();return true;}return false;}"
       "var st=HUB.gymwork._debug.state(), lg=(st&&st.log)||{}, done=0;"
       "Object.keys(lg).forEach(function(d){Object.keys(lg[d]).forEach(function(e){if(lg[d][e].done)done++;});});"
       "if(done>0){clearInterval(iv);res(done);return;}"
       "if(n>200){clearInterval(iv);res(-done);return;}"
       "if(click('gwPStart'))return;if(click('gwPDone'))return;"
       "if(click('gwPSkip'))return;if(click('gwPComplete'))return;"
       "},250);});};return 1")
    v, _ = js("return window.__gwOneDone()", await_=True)
    print('exercises done in player:', v)
    v, _ = js("return HUB.gymwork._debug.state().log")
    n_done_b = sum(1 for d in (v or {}).values() for e in d.values() if e.get('done'))
    # switch to intermediate via UI
    js("HUB.gymwork.openPlan();return 1"); time.sleep(0.5)
    js("document.querySelector('[data-gwlvl=\"intermediate\"]').click();return 1"); time.sleep(0.8)
    v, _ = js("return {lvl:HUB.gymwork._debug.state().level,"
              "first:(function(){HUB.gymwork.openDay('push');"
              "var r=document.querySelector('#gwov-day .gw-exrow');"
              "return r?r.getAttribute('data-ex'):null;})()}")
    check('level switched to intermediate', v['lvl'] == 'intermediate', str(v))
    v2, _ = js("return HUB.gymwork._debug.state().log")
    n_done_i = sum(1 for d in (v2 or {}).values() for e in d.values() if e.get('done'))
    check('logs preserved across level switch', n_done_i == n_done_b and n_done_b >= 1,
          'before=%d after=%d' % (n_done_b, n_done_i))
    # switch back
    js("HUB.gymwork.openPlan();return 1"); time.sleep(0.5)
    js("document.querySelector('[data-gwlvl=\"beginner\"]').click();return 1"); time.sleep(0.8)
    v, _ = js("return HUB.gymwork._debug.state().level")
    check('level switched back to beginner', v == 'beginner', str(v))

    # ---- player video routing spot check: 8 players incl. new sections + new exercises ----
    for exid in ['hammer-curl', 'warmup-jumping-jacks', 'abs-plank', 'pilates-hundred', 'zumba-salsa-basic', 'deadlift',
                 'db-floor-press', 'cobra-stretch']:
        js("HUB.gymwork._debug.seedPlan();HUB.gymwork.openPlayer('%s');return 1" % exid)
        time.sleep(0.6)
        v, _ = js("return (document.querySelector('#gwov-player video')||{}).currentSrc||''")
        ok = ('videos/gym/%s.mp4' % exid) in v
        check('player routes video ' + exid, ok, v[-40:])
        err1 = errors()
        if err1:
            check('no errors after ' + exid, False, str(err1)); fails.append('err-' + exid)
    js("HUB.gymwork.openPlan();return 1"); time.sleep(0.5)

    # ---- light mode + 320px ----
    js("document.body.classList.remove('dark');return 1"); time.sleep(0.4)
    js("document.querySelector('[data-gwsec=\"abs\"]').click();return 1"); time.sleep(0.6)
    shot('gw2-abs-light'); no_overflow('abs-light')
    js("document.body.classList.add('dark');return 1"); time.sleep(0.3)
    set_viewport(320, 700)
    js("HUB.gymwork.openPlan();return 1"); time.sleep(0.6)
    shot('gw2-plan-320'); no_overflow('plan-320')
    js("document.querySelector('[data-gwsec=\"pilates\"]').click();return 1"); time.sleep(0.6)
    shot('gw2-pilates-320'); no_overflow('pilates-320')

    err = errors()
    check('zero console errors', len(err) == 0, str(err))
    print('\nRESULT:', 'ALL PASS' if not fails else 'FAILURES: %s' % fails)
    proc.terminate()

main()
