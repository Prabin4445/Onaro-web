#!/usr/bin/env python3
"""QA: rich Add Professor + reviewer points (25/10) + SPECIALIST at 1000.
Covers: form fields, blank-name rejection, profanity moderation, duplicate
prevention (exact / honorific / directory), no double points on re-render,
detail rendering, anonymous reviews, persistence, legacy migration,
SPECIALIST unlock, es/ne/hi/de keys. 320+390px, dark+light, zero console errors."""
import json, subprocess, time, urllib.request, shutil, os, base64
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
QA = os.path.dirname(os.path.abspath(__file__))
checks, errors = [], []

def note(ok, label, detail=''):
    checks.append((bool(ok), label))
    print(('PASS ' if ok else 'FAIL ') + label, detail if not ok else '')

class CDP:
    def __init__(self, wsurl):
        import websocket
        self.ws = websocket.create_connection(wsurl, timeout=15); self.ws.settimeout(15); self.iid = 0
    def send(self, method, params=None):
        self.iid += 1
        self.ws.send(json.dumps({'id': self.iid, 'method': method, 'params': params or {}}))
        dl = time.time() + 20
        while time.time() < dl:
            m = json.loads(self.ws.recv())
            if m.get('id') == self.iid: return m.get('result')
        raise TimeoutError(method)

def targets(port):
    return json.load(urllib.request.urlopen(f'http://localhost:{port}/json/list', timeout=10))

def j(c, expr, awaitPromise=False):
    # CDP Runtime.evaluate: bare `return` at top level is a SyntaxError.
    # Always wrap in an IIFE (AGENTS.md lesson).
    expr = "(function(){" + expr + "})()"
    try:
        r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': awaitPromise})
        if r and 'exceptionDetails' in r:
            ed = r['exceptionDetails']
            return 'THREW:' + str(ed.get('exception', {}).get('description', ed.get('text', '')))[:160]
        return (r or {}).get('result', {}).get('value')
    except Exception as e:
        return 'JSERR:' + str(e)[:120]

def run_case(width, height, theme, port):
    tag = f'{width}x{height}-{theme}'
    prof = f'/tmp/hubqa-profpts-{width}-{theme}'
    shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof, exist_ok=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={port}', '--remote-allow-origins=*', f'--window-size={width},{height}',
        f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                ts = targets(port)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable')
        # true narrow viewport: headless floors --window-size at 500px, so
        # emulate the device metrics instead (real 390/320 CSS px)
        c.send('Emulation.setDeviceMetricsOverride',
               {'width': width, 'height': height, 'deviceScaleFactor': 2, 'mobile': True})
        time.sleep(0.5)
        note(j(c, "return window.innerWidth;") == width, f'true {width}px viewport [{tag}]')
        j(c, "window.__huberr=[];addEventListener('error',function(e){__huberr.push('ERR:'+e.message)});"
             "addEventListener('unhandledrejection',function(e){__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason))})")
        for _ in range(60):
            if j(c, "return !!(window.HUB&&HUB.store&&HUB.store.state&&HUB.professors&&HUB.badges&&HUB.i18n&&HUB.ui);") is True: break
            time.sleep(0.5)
        j(c, "localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
             "HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') + ";HUB.store.save();HUB.applyTheme();")
        j(c, """var p=HUB.store.state.profile; p.name='QA Pts'; p.campus='The University of Texas at Dallas';
          p.verified=true; HUB.store.save(); window.__gateSkip=true;
          try{HUB.auth.close()}catch(e){} var w=document.getElementById('wlcmHost'); if(w) w.remove();
          return 1;""")
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data']))

        # ---- wait for the cinematic splash to leave the DOM (its decorative
        #      elements transiently widen document.scrollWidth; not app UI) ----
        for _ in range(20):
            if j(c, "return !document.getElementById('splash');") is True: break
            time.sleep(0.5)

        # ---- banner at 0 ----
        j(c, "HUB.professors.open(null); return 1;"); time.sleep(1.5)
        note(j(c, "return !!document.getElementById('profPts');") is True, f'points banner visible [{tag}]')
        note(j(c, "return (document.getElementById('profPts').textContent||'').indexOf('0')>=0;") is True,
             f'banner starts at 0 pts [{tag}]')
        note(j(c, "return document.documentElement.scrollWidth<="+str(width)+";") is True, f'list no h-overflow [{tag}]')

        # ---- add form fields + visual ----
        j(c, "document.getElementById('profAdd').click(); return 1;"); time.sleep(0.9)
        for fid, lbl in [('apName', 'name'), ('apTitle', 'title'), ('apDept', 'dept'), ('apCourses', 'courses')]:
            note(j(c, "return !!document.getElementById('" + fid + "');") is True, f'add form has {lbl} field [{tag}]')
        note(j(c, "return document.documentElement.scrollWidth<="+str(width)+";") is True, f'add form no h-overflow [{tag}]')
        shot(f'profpts-addform-{width}-{theme}')

        # ---- blank required name: rejected, nothing saved, no points ----
        j(c, "document.getElementById('apName').value='';document.getElementById('apGo').click(); return 1;")
        time.sleep(0.5)
        note(j(c, "return (HUB.store.state.prof.custom||[]).length===0;") is True, f'blank name saves nothing [{tag}]')
        note(j(c, "return HUB.badges.myPoints()===0;") is True, f'blank name earns no points [{tag}]')
        note(j(c, "return !!document.getElementById('apGo');") is True, f'sheet stays open on blank name [{tag}]')

        # ---- profanity blocked + strike ----
        j(c, """document.getElementById('apName').value='shithead';
          document.getElementById('apTitle').value='Dr';
          document.getElementById('apDept').value='Math';
          document.getElementById('apGo').click(); return 1;""")
        time.sleep(0.6)
        note(j(c, "return (HUB.store.state.prof.custom||[]).length===0;") is True, f'abusive add blocked [{tag}]')
        note(j(c, "return (HUB.store.state.prof.mod.strikes||0)===1;") is True, f'blocked add earns a strike [{tag}]')
        note(j(c, "return HUB.badges.myPoints()===0;") is True, f'abusive add earns no points [{tag}]')

        # ---- directory duplicate blocked (real faculty name, no points, no strike) ----
        dname = j(c, """return (function(){var all=HUB.professors._all('The University of Texas at Dallas');
          var d=all.filter(function(p){return p.dir;}); return d.length?d[0].name:null;})();""")
        note(isinstance(dname, str) and len(dname) > 2, f'directory has faculty names [{tag}]', str(dname)[:40])
        if isinstance(dname, str) and dname:
            j(c, "document.getElementById('apName').value=" + json.dumps(dname) +
                 ";document.getElementById('apGo').click(); return 1;")
            time.sleep(0.5)
            note(j(c, "return (HUB.store.state.prof.custom||[]).length===0;") is True,
                 f'directory duplicate not saved [{tag}]')
            note(j(c, "return HUB.badges.myPoints()===0;") is True, f'directory duplicate earns no points [{tag}]')
            note(j(c, "return (HUB.store.state.prof.mod.strikes||0)===1;") is True,
                 f'duplicate is not a strike (honest mistake) [{tag}]')
            note(j(c, "return (document.getElementById('toastHost')||{textContent:''}).textContent.indexOf(" +
                 "HUB.i18n.t('prof.dupProf').slice(0,12))>=0;") is True, f'duplicate shows already-listed hint [{tag}]')

        # ---- clean add with full details: +25 ----
        j(c, """document.getElementById('apName').value='Ada Lovelace';
          document.getElementById('apTitle').value='Professor';
          document.getElementById('apDept').value='Computer Science';
          document.getElementById('apCourses').value='CS 1337, CS 4349';
          document.getElementById('apGo').click(); return 1;""")
        time.sleep(1.0)
        note(j(c, """var cs=HUB.store.state.prof.custom;
          return cs.length===1&&cs[0].name==='Ada Lovelace'&&cs[0].title==='Professor'
          &&cs[0].dept==='Computer Science'
          &&JSON.stringify(cs[0].courses)==='["CS 1337","CS 4349"]'
          &&cs[0].campus==='The University of Texas at Dallas';""") is True,
             f'added professor stores all details [{tag}]')
        note(j(c, "return HUB.badges.myPoints()===25;") is True, f'adding professor awards +25 pts [{tag}]')

        # ---- exact-name duplicate blocked ----
        j(c, "HUB.professors.open(null); return 1;"); time.sleep(0.8)
        j(c, "document.getElementById('profAdd').click(); return 1;"); time.sleep(0.7)
        j(c, "document.getElementById('apName').value='ada lovelace';document.getElementById('apGo').click(); return 1;")
        time.sleep(0.5)
        note(j(c, "return HUB.store.state.prof.custom.length===1;") is True, f'exact duplicate not saved [{tag}]')
        note(j(c, "return HUB.badges.myPoints()===25;") is True, f'exact duplicate earns no points [{tag}]')
        # ---- honorific-variant duplicate blocked ("Dr. Ada Lovelace") ----
        j(c, "document.getElementById('apName').value='Dr. Ada Lovelace';document.getElementById('apGo').click(); return 1;")
        time.sleep(0.5)
        note(j(c, "return HUB.store.state.prof.custom.length===1;") is True, f'honorific duplicate not saved [{tag}]')
        note(j(c, "return HUB.badges.myPoints()===25;") is True, f'honorific duplicate earns no points [{tag}]')
        j(c, "try{HUB.ui.closeSheet()}catch(e){} return 1;"); time.sleep(0.5)

        # ---- re-render / reopen awards nothing extra ----
        j(c, "HUB.professors.open(null); return 1;"); time.sleep(0.8)
        j(c, "HUB.professors.open(HUB.store.state.prof.custom[0].id); return 1;"); time.sleep(0.8)
        j(c, "HUB.professors.open(null); return 1;"); time.sleep(0.8)
        note(j(c, "return HUB.badges.myPoints()===25;") is True, f're-render/reopen adds no points [{tag}]')

        # ---- detail shows everything + student-added tag ----
        j(c, "HUB.professors.open(HUB.store.state.prof.custom[0].id); return 1;"); time.sleep(0.8)
        note(j(c, """var h=document.getElementById('profBody').innerHTML;
          return h.indexOf('Ada Lovelace')>=0&&h.indexOf('Professor')>=0
          &&h.indexOf('Computer Science')>=0&&h.indexOf('CS 1337')>=0&&h.indexOf('CS 4349')>=0;""") is True,
             f'detail shows name/title/dept/courses [{tag}]')
        note(j(c, "return document.getElementById('profBody').innerHTML.indexOf(HUB.i18n.t('prof.customTag'))>=0;") is True,
             f'detail shows student-added tag [{tag}]')
        shot(f'profpts-detail-{width}-{theme}')

        # ---- back to list: banner at 25 ----
        j(c, "document.getElementById('profBack').click(); return 1;"); time.sleep(0.8)
        note(j(c, "return (document.getElementById('profPts').textContent||'').indexOf('25')>=0;") is True,
             f'banner updates to 25 pts [{tag}]')

        # ---- rate the new professor: +10, anonymous ----
        j(c, "HUB.professors.open(HUB.store.state.prof.custom[0].id); return 1;"); time.sleep(0.8)
        j(c, "document.getElementById('profRate').click(); return 1;"); time.sleep(0.8)
        note(j(c, "return document.body.innerHTML.indexOf(HUB.i18n.t('prof.anonNote'))>=0;") is True,
             f'rate sheet shows anonymity disclaimer [{tag}]')
        j(c, """document.querySelectorAll('#rateStars [data-star]')[4].click();
          document.querySelector('#rateDiff [data-diff="5"]').click();
          document.querySelector('#rateAgain [data-ag="1"]').click();
          document.getElementById('rateCourse').value='CS 1337';
          document.getElementById('rateComment').value='Brilliant lecturer, tough but fair.';
          document.getElementById('rateGo').click(); return 1;""")
        time.sleep(1.0)
        note(j(c, "return HUB.badges.myPoints()===35;") is True, f'review awards +10 pts (25+10=35) [{tag}]')
        note(j(c, """var cs=HUB.store.state.prof.custom;
          var rs=HUB.store.state.prof.reviews[cs[0].id]||[];
          return rs.length===1&&rs[0].q===5&&!('author' in rs[0]);""") is True,
             f'review stored with no author name [{tag}]')
        note(j(c, "return document.getElementById('profBody').innerHTML.indexOf(HUB.i18n.t('prof.anon'))>=0;") is True,
             f'review renders as Anonymous [{tag}]')

        # ---- persistence across reload (re-arm the error siphon: reload wipes window) ----
        j(c, "location.reload(); return 1;"); time.sleep(4.0)
        for _ in range(60):
            if j(c, "return !!(window.HUB&&HUB.store&&HUB.store.state&&HUB.badges);") is True: break
            time.sleep(0.5)
        j(c, "window.__huberr=[];addEventListener('error',function(e){__huberr.push('ERR:'+e.message)});"
             "addEventListener('unhandledrejection',function(e){__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason))}); return 1;")
        note(j(c, "return HUB.badges.myPoints()===35;") is True, f'points survive reload [{tag}]')

        # ---- legacy migration ----
        j(c, """var p=HUB.store.state.profile; delete p.reviewPts;
          p.aid='mig-aid';
          HUB.store.state.prof.reviews={'mig':[{id:'r1',ts:1,q:5,authorId:'mig-aid'},{id:'r2',ts:2,q:4,authorId:'mig-aid'},{id:'r3',ts:3,q:5,authorId:'mig-aid'}]};
          HUB.store.save(); return HUB.badges.myPoints();""")
        v = j(c, "return HUB.badges.myPoints();")
        note(v == 30, f'3 legacy reviews seed 30 pts [{tag}]', 'got ' + str(v))

        # ---- SPECIALIST at 1000 ----
        j(c, "HUB.badges._debug.setPoints(1000); return 1;"); time.sleep(0.5)
        note(j(c, "return HUB.badges.isSpecialist()===true;") is True, f'SPECIALIST unlocks at 1000 pts [{tag}]')
        j(c, "HUB.professors.open(null); return 1;"); time.sleep(1.0)
        note(j(c, "return (document.getElementById('profPts').textContent||'').indexOf(HUB.i18n.t('prof.specEarned'))>=0;") is True,
             f'banner shows SPECIALIST earned [{tag}]')

        # ---- i18n keys ----
        for code in ['es', 'ne', 'hi']:
            ok = j(c, "return (function(){var d=HUB.i18n._dict('" + code + "');"
                       "return ['prof.fTitle','prof.fCourses','prof.myPoints','prof.ptsToSpec','prof.specEarned','prof.curseWarnAdd','prof.customTag','prof.dupProf','bdg.tipAddProf']"
                       ".every(function(k){return !!d[k];});})();")
            note(ok is True, f'{code} has new prof/points keys [{tag}]')
        try:
            r = c.send('Runtime.evaluate', {'expression': "(async function(){ await HUB.i18n.loadLocale('de');"
                         "var d=HUB.i18n._dict('de');"
                         "return d!==HUB.i18n._dict('en')&&['prof.fTitle','prof.myPoints','prof.dupProf','bdg.tipAddProf']"
                         ".every(function(k){return !!d[k];}); })()",
                         'returnByValue': True, 'awaitPromise': True})
            v = 'THREW' if (r and 'exceptionDetails' in r) else (r or {}).get('result', {}).get('value')
        except Exception: v = 'JSERR'
        note(v is True, f'de lazy locale loads with new keys [{tag}]')

        errs = j(c, "return window.__huberr.splice(0);")
        note(not errs, f'zero console errors [{tag}]', json.dumps(errs)[:300] if errs else '')
    finally:
        try: proc.terminate()
        except Exception: pass

def main():
    port = 9471
    for w, h in [(390, 844), (320, 568)]:
        for th in ['dark', 'light']:
            run_case(w, h, th, port); port += 1
    bad = [l for ok, l in checks if not ok]
    print('\n%d/%d checks passed' % (len(checks) - len(bad), len(checks)))
    if bad: print('FAILED:', bad)

if __name__ == '__main__':
    main()
