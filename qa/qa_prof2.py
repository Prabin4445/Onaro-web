#!/usr/bin/env python3
"""Professors Fix 1+2 QA (2026-09-23): no self-voting + same-name disambiguation.

Per case (fresh profile, zero console errors via window.__huberr siphon):
- Fix 1: own comment -> heart/thumb render disabled (is-own + aria-disabled),
  tap does nothing to counts but shows the prof.voteSelf toast; other users'
  comments still votable (like -> undo -> switch sides); _vote() guard false.
- Fix 2: two "Michael Shepard"s (seed English + custom Mathematics) -> search
  shows both rows with distinct dept + college labels; detail headers show
  dept + campus chips; add-professor sheet shows the campus.
- en + de (real setLang + _dict identity), dark + light, 390 + 320px,
  no horizontal overflow, no banned purple in new markup.
"""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9493
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []

def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, detail)

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

SEED_JS = """(function(){
HUB.store.state.profile.name='QATester';
HUB.store.state.profile.campus='Dallas College';
HUB.store.state.profile.verified=true;
HUB.store.state.prof={reviews:{},votes:{},custom:[]};
HUB.store.save();
HUB.professors._reset();
var all=HUB.professors._all('Dallas College').filter(function(p){return p.name==='Michael Shepard';});
var pid=all[0].id;
/* custom same-name professor, different department */
HUB.store.state.prof.custom.unshift({id:'c-qa-dup',name:'Michael Shepard',dept:'Mathematics',title:'',campus:'Dallas College',ts:Date.now()});
HUB.store.save();
/* own review (authorId auto = profile.aid) + another user's review */
HUB.professors._add(pid,{q:5,d:2,again:1,course:'ENG 1301',comment:'QA own comment here',author:'QATester'});
HUB.professors._add(pid,{q:3,d:4,again:0,course:'ENG 1302',comment:'QA other comment here',author:'SomeoneElse',authorId:'other-device-aid'});
return pid;})()"""

def run_case(width, height, theme, lang):
    prof = f'/tmp/hubqa-prof2-{width}-{theme}-{lang}'
    shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof, exist_ok=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        f'--window-size={width},{height}',
        f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tag = f'{width}x{height}-{theme}-{lang}'
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as rr:
                    ts = json.load(rr)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        c.send('Emulation.setDeviceMetricsOverride', {'width': width, 'height': height,
               'deviceScaleFactor': 2, 'mobile': True})
        def js(expr):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
                if r and 'exceptionDetails' in r:
                    ed = r['exceptionDetails']
                    return 'THREW:' + str(ed.get('exception', {}).get('description', ed.get('text', '')))[:160]
                return (r or {}).get('result', {}).get('value')
            except Exception as e: return 'JSERR:' + str(e)[:120]
        def arm_errs():
            js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
               "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'zero console errors @ {label} [{tag}]', json.dumps(v)[:200] if v else '')

        js(f"localStorage.setItem('orbit_i18n',JSON.stringify({{lang:'{lang}',country:'US'}}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        arm_errs()
        js("HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') + ";HUB.store.save();HUB.applyTheme();")
        if lang == 'de':
            js("HUB.i18n.setLang('de')"); time.sleep(1.5)
            note(js("HUB.i18n._dict('de')!==HUB.i18n._dict('en')") is True, f'de locale really loaded [{tag}]')
        pid = js(SEED_JS); time.sleep(0.5)
        note(isinstance(pid, str) and pid, f'seed ok [{tag}]', repr(pid)[:40])

        js("HUB.professors.open()"); time.sleep(1.5)

        # ---------- Fix 2: same-name disambiguation in search ----------
        js("(function(){var q=document.getElementById('profQ');q.value='shepard';"
           "q.dispatchEvent(new Event('input',{bubbles:true}));return 1;})()")
        time.sleep(0.8)
        rows = js("[...document.querySelectorAll('.prof-card')].map(b=>b.textContent)")
        note(isinstance(rows, list) and len(rows) >= 2, f'two Shepards in search [{tag}]', f'n={len(rows) if isinstance(rows,list) else rows}')
        if isinstance(rows, list) and len(rows) >= 2:
            txt = ' || '.join(rows)
            note('English' in txt and 'Mathematics' in txt, f'distinct dept labels [{tag}]')
            note(all('Dallas College' in r for r in rows), f'college on every row [{tag}]')
        note(js("document.documentElement.scrollWidth") <= width, f'list no h-overflow [{tag}]')
        shot(f'prof2-list-{width}-{theme}-{lang}')

        # ---------- Fix 2: detail chips ----------
        js(f"document.querySelector('[data-pid=\"{pid}\"]').click()"); time.sleep(1.2)
        chips = js("(document.querySelector('.prof-idchips')||{textContent:''}).textContent")
        note('English' in str(chips) and 'Dallas College' in str(chips), f'detail chips dept+campus [{tag}]', repr(chips)[:80])
        note(js("document.documentElement.scrollWidth") <= width, f'detail no h-overflow [{tag}]')

        # ---------- Fix 1: own comment cannot be voted ----------
        own_btns = js("(function(){var r=[...document.querySelectorAll('.prof-rev')].find(x=>x.textContent.includes('QA own comment here'));"
                      "if(!r)return 'norev';"
                      "var h=r.querySelector('[data-vote=\"1\"]'),d=r.querySelector('[data-vote=\"-1\"]');"
                      "return {hOwn:h.classList.contains('is-own'),hDis:h.getAttribute('aria-disabled'),"
                      "dOwn:d.classList.contains('is-own'),dDis:d.getAttribute('aria-disabled')};})()")
        note(isinstance(own_btns, dict) and own_btns.get('hOwn') and own_btns.get('dOwn'),
             f'own vote buttons disabled-state [{tag}]', repr(own_btns)[:120])
        note(isinstance(own_btns, dict) and own_btns.get('hDis') == 'true',
             f'own buttons aria-disabled [{tag}]')
        js("document.getElementById('toastHost').innerHTML=''")
        before = js("(function(){var r=[...document.querySelectorAll('.prof-rev')].find(x=>x.textContent.includes('QA own comment here'));"
                    "return r.querySelector('[data-vote=\"1\"] b').textContent;})()")
        js("(function(){var r=[...document.querySelectorAll('.prof-rev')].find(x=>x.textContent.includes('QA own comment here'));"
           "r.querySelector('[data-vote=\"1\"]').click();return 1;})()")
        time.sleep(0.6)
        after = js("(function(){var r=[...document.querySelectorAll('.prof-rev')].find(x=>x.textContent.includes('QA own comment here'));"
                   "return r.querySelector('[data-vote=\"1\"] b').textContent;})()")
        note(before == after == '0', f'own like tap changes nothing [{tag}]', f'{before}->{after}')
        toast_txt = js("document.getElementById('toastHost').textContent")
        expect = js("HUB.i18n.t('prof.voteSelf')")
        note(bool(toast_txt) and toast_txt == expect, f'voteSelf toast shown [{tag}]', repr(toast_txt)[:60])
        shot(f'prof2-own-{width}-{theme}-{lang}')

        # _vote() belt-and-braces guard
        guard = js("(function(){var r=[...document.querySelectorAll('.prof-rev')].find(x=>x.textContent.includes('QA own comment here'));"
                   "return HUB.professors._vote(r.dataset.rev,1);})()")
        note(guard is False, f'_vote guard returns false [{tag}]')

        # ---------- other users' comments still votable: like -> undo -> switch ----------
        other = js("(function(){var r=[...document.querySelectorAll('.prof-rev')].find(x=>x.textContent.includes('QA other comment here'));"
                   "if(!r)return 'norev';"
                   "var h=r.querySelector('[data-vote=\"1\"]'),d=r.querySelector('[data-vote=\"-1\"]');"
                   "return {ownCls:h.classList.contains('is-own')};})()")
        note(isinstance(other, dict) and not other.get('ownCls'), f'other comment votable [{tag}]')
        def cnt(side):
            return js("(function(){var r=[...document.querySelectorAll('.prof-rev')].find(x=>x.textContent.includes('QA other comment here'));"
                      "return r.querySelector('[data-vote=\"" + side + "\"] b').textContent;})()")
        def clk(side):
            return js("(function(){var r=[...document.querySelectorAll('.prof-rev')].find(x=>x.textContent.includes('QA other comment here'));"
                      "r.querySelector('[data-vote=\"" + side + "\"]').click();return 1;})()")
        clk("1"); time.sleep(0.4)
        note(cnt("1") == '1', f'like increments [{tag}]')
        clk("1"); time.sleep(0.4)
        note(cnt("1") == '0', f'like tap-again undoes [{tag}]')
        clk("-1"); time.sleep(0.4)
        note(cnt("-1") == '1' and cnt("1") == '0', f'switch sides [{tag}]')

        # add-professor sheet shows campus
        js("HUB.professors.close()"); time.sleep(0.5)
        js("HUB.professors.open()"); time.sleep(1.0)
        js("document.getElementById('profAdd').click()"); time.sleep(0.8)
        note('Dallas College' in str(js("document.getElementById('sheetHost').textContent")),
             f'add sheet shows campus [{tag}]')
        js("HUB.ui.closeSheet()")

        # banned purple in new markup
        note(js("""(function(){var bad=['#7C3AED','#8B5CF6','#A855F7'];var html=document.body.innerHTML.toUpperCase();
return !bad.some(h=>html.includes(h));})()""") is True, f'no banned purple [{tag}]')

        errs('prof2')
        js("HUB.professors.close()")
    finally:
        proc.terminate(); time.sleep(1)

for (w, h, th, lang) in [(390, 844, 'dark', 'en'), (390, 844, 'light', 'en'),
                         (320, 568, 'dark', 'en'), (320, 568, 'light', 'de')]:
    run_case(w, h, th, lang)

ok = sum(1 for c in checks if c[0]); print(f'\n{ok}/{len(checks)} passed')
