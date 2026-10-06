#!/usr/bin/env python3
"""HUB QA: professor rating anonymity + auto-moderation + US-default country
+ missing-professor note (PraBin 2026-09-23).

Covers: anonymous author label (never the user's name, not even stored),
rate-sheet disclaimer + clean-rule note, missing-professor note + empty-state
add flow, profanity block (plain, leet, dotted) with strike warnings,
3rd strike -> 1-month ban gate, ban expiry reset, es/ne/hi key presence,
lazy-locale kh validity via real loadLocale, guessCountry()==US default +
currencySymbol $, zero console errors. Fresh profile every run.
"""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9439
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-profmod'
errors, checks = [], []
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

JS = "(function(){%s})()"
def j(c, expr, awaitPromise=False):
    v, x = c.js(JS % expr, awaitPromise)
    if x: print('JS-EXC:', str(x)[:200])
    return v

def main():
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=390,844',
        f'--user-data-dir={PROF}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                ts = targets()
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        hook_err(c); time.sleep(2.5)
        # seed: verified student on a seeded campus; disarm the auth gate poller
        j(c, """localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));
          const p=HUB.store.state.profile; p.name='QA Mod'; p.campus='The University of Texas at Dallas';
          p.verified=true; HUB.store.save(); window.__gateSkip=true;
          try{HUB.auth.close()}catch(e){} const w=document.getElementById('wlcmHost'); if(w) w.remove();
          return 'seeded'""")
        time.sleep(7)  # splash out (~6.2s)
        j(c, "try{HUB.auth.close()}catch(e){} return 1")
        drain_err(c, 'load')
        note(j(c, "return !document.getElementById('wlcmHost')"), 'welcome overlay gone')

        # ---- 1. US default country ----
        note(j(c, "return HUB.i18n.guessCountry()==='US'"), 'guessCountry defaults to US')
        note(j(c, "return (HUB.i18n.getCountry()||HUB.i18n.guessCountry())==='US'"), 'effective country is US fresh')
        note(j(c, "return HUB.i18n.currencySymbol()==='$'"), 'currency defaults to $')
        # explicit user choice still wins
        j(c, "HUB.i18n.setCountry('NP'); return 1")
        note(j(c, "return HUB.i18n.getCountry()==='NP'"), 'explicit country choice wins over default')
        j(c, "HUB.i18n.setCountry('US'); return 1")

        # ---- 2. professors list: missing-professor note ----
        j(c, "HUB.professors.open(null); return 1"); time.sleep(1)
        note(j(c, "return document.querySelector('#hubProfRoot .hint')&&document.querySelector('#hubProfRoot').textContent.indexOf('Add professor to create them')>=0"),
             'missing-professor note on list')
        # empty state via gibberish search
        j(c, """const q=document.getElementById('profQ'); q.value='zzzqqqnonexistent';
          q.dispatchEvent(new Event('input',{bubbles:true})); return 1""")
        time.sleep(0.6)
        note(j(c, "return !!document.getElementById('profAddEmpty')"), 'empty state has Add button')
        note(j(c, "return document.getElementById('profList').textContent.indexOf('Add professor to create them')>=0"),
             'empty state shows missing-professor note')
        j(c, "document.getElementById('profAddEmpty').click(); return 1"); time.sleep(0.6)
        note(j(c, "return !!document.getElementById('apName')"), 'Add-professor sheet opens from empty state')
        j(c, """document.getElementById('apName').value='QA Testprofessor';
          document.getElementById('apDept').value='Testing'; document.getElementById('apGo').click(); return 1""")
        time.sleep(0.8)
        note(j(c, "return document.getElementById('profBody').textContent.indexOf('QA Testprofessor')>=0"),
             'created professor opens detail')
        shot(c, 'profmod-addsheet')
        drain_err(c, 'add-professor')

        # ---- 3. rate sheet: disclaimer + clean rule ----
        pid = j(c, "return HUB.professors._all('The University of Texas at Dallas')[0].id")
        note(bool(pid), 'seed professor found', str(pid)[:40])
        j(c, "HUB.professors.open(%s); return 1" % json.dumps(pid)); time.sleep(0.8)
        j(c, "document.getElementById('profRate').click(); return 1"); time.sleep(0.6)
        sheet_txt = j(c, "return document.getElementById('sheetHost').textContent") or ''
        note('never shown on ratings or comments' in sheet_txt, 'anonymity disclaimer in rate sheet')
        note('scanned automatically' in sheet_txt, 'clean-rule note in rate sheet')
        shot(c, 'profmod-ratesheet')

        def submit_rating(comment):
            j(c, "document.getElementById('toastHost').innerHTML=''; return 1")
            j(c, """const st=document.querySelector('#rateStars [data-star="5"]'); if(st) st.click();
              document.getElementById('rateComment').value=%s;
              document.getElementById('rateGo').click(); return 1""" % json.dumps(comment))
            time.sleep(0.7)
            return (j(c, "return document.getElementById('toastHost').textContent") or '')

        def nreviews():
            return j(c, "return HUB.professors._reviews(%s).length" % json.dumps(pid))

        # ---- 4. clean rating posts anonymously ----
        n0 = nreviews()
        toast = submit_rating('Great teacher, very clear explanations.')
        note('Thanks for rating' in toast, 'clean rating accepted', toast[:60])
        note(nreviews() == n0 + 1, 'review count +1')
        foot = j(c, "return document.querySelector('.prof-rev-foot').textContent") or ''
        note('Anonymous' in foot and 'QA Mod' not in foot, 'review shows Anonymous, never the name', foot[:60])
        stored = j(c, "return HUB.professors._reviews(%s)[0].author" % json.dumps(pid))
        note(stored in (None, ''), 'author name never stored', repr(stored))
        drain_err(c, 'clean-rating')

        # ---- 5. profanity: blocked + strikes ----
        j(c, "HUB.professors.open(%s); return 1" % json.dumps(pid)); time.sleep(0.6)
        j(c, "document.getElementById('profRate').click(); return 1"); time.sleep(0.5)
        n1 = nreviews()
        toast = submit_rating('This professor is shit')
        note('Warning 1 of 3' in toast, 'profanity blocked with warning 1/3', toast[:80])
        note(nreviews() == n1, 'offending comment never posted')
        note(j(c, "return HUB.professors._state().mod.strikes===1"), 'strike 1 recorded')
        note(j(c, "return document.getElementById('rateComment').classList.contains('prof-curse-flag')"),
             'comment box flagged red, sheet stays open')
        shot(c, 'profmod-curseflag')
        # leet evasion
        toast = submit_rating('sh1t happens here')
        note('Warning 2 of 3' in toast and j(c, "return HUB.professors._state().mod.strikes===2"),
             'leet-speak evasion blocked, strike 2', toast[:60])
        # dotted evasion -> 3rd strike -> month ban
        toast = submit_rating('what the f.u.c.k is this')
        time.sleep(0.5)
        note(j(c, "return HUB.professors._state().mod.strikes===3"), 'strike 3 recorded')
        ban = j(c, "return HUB.professors._state().mod.bannedUntil||0")
        note(ban and (ban - j(c, "return Date.now()")) > 29*24*3600*1000, 'banned ~30 days out')
        h2 = j(c, "return document.getElementById('sheetHost').textContent") or ''
        note('Account flagged' in h2 and "can't rate or comment until" in h2, 'banned gate shown with date')
        shot(c, 'profmod-banned')
        drain_err(c, 'profanity')

        # ---- 6. banned: rate entry blocked ----
        j(c, "HUB.professors.open(%s); return 1" % json.dumps(pid)); time.sleep(0.6)
        j(c, "document.getElementById('profRate').click(); return 1"); time.sleep(0.5)
        note(j(c, "return document.getElementById('sheetHost').textContent.indexOf('Account flagged')>=0"),
             'banned user gets flag gate, not rate sheet')

        # ---- 7. ban expiry resets ----
        j(c, "HUB.store.state.prof.mod.bannedUntil=Date.now()-1000; HUB.store.save(); return 1")
        j(c, "HUB.ui.closeSheet(); HUB.professors.open(%s); return 1" % json.dumps(pid)); time.sleep(0.6)
        j(c, "document.getElementById('profRate').click(); return 1"); time.sleep(0.5)
        note(j(c, "return !!document.getElementById('rateStars')"), 'rate sheet opens after ban served')
        note(j(c, "return HUB.professors._state().mod.strikes===0"), 'strikes reset after ban served')
        drain_err(c, 'ban-expiry')

        # ---- 8. i18n keys: bundled + lazy kh ----
        for code, frag in (('es', 'Aviso'), ('ne', 'चेतावनी'), ('hi', 'चेतावनी')):
            note(j(c, "return (HUB.i18n._dict(%s)['prof.curseWarn']||'').indexOf(%s)>=0" % (json.dumps(code), json.dumps(frag))),
                 f'{code} has real translation')
        note(j(c, "return HUB.i18n._dict('de')['prof.anon']==='Anonymous'"), 'lazy locales carry English fallback')
        ok = j(c, "return HUB.i18n.loadLocale('fr')", awaitPromise=True)
        note(ok is True, 'loadLocale(fr) passes real kh check')
        note(j(c, "return HUB.i18n._dict('fr')!==HUB.i18n._dict('en')"), 'fr really loaded (identity)')
        drain_err(c, 'i18n')

        # light-mode shot of the rate sheet w/ disclaimer
        j(c, "document.body.classList.remove('dark'); return 1"); time.sleep(0.5)
        shot(c, 'profmod-ratesheet-light')

        print('\n==== console errors:', 'NONE' if not errors else json.dumps(errors)[:600])
        fails = [l for ok, l in checks if not ok]
        print(f'==== {len(checks)-len(fails)}/{len(checks)} checks passed')
        if fails: print('FAILED:', fails)
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
