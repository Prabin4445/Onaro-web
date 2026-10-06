#!/usr/bin/env python3
"""Professors feature QA (2026-09-23, PraBin's full brief + entry-card design upgrade).

Asserts at 390x844 and 320x568, dark+light, fresh profiles, zero console errors:
- Home entry card: blackboard SVG scene (5 animated chalk stars), punchy hook
  copy (prof.entryHook/Sub), placement directly below classes card + above GPA
  card, no new tab-bar icon (tab bar still 5 tabs)
- Full-page overlay open/close (tap, X, Escape); panel height == viewport
- Search by name / partial / course; visible clear button clears + restores
- Campus scoping (Dallas College vs SMU seeds)
- Honest empty states (no ratings / no results)
- Unverified rating gate: verify-only sheet; CTA routes to ME verification
- Verified rating+comment submission; stats + courses update
- Like (3D glowing heart SVG) / dislike (red thumbs-down SVG): increment,
  undo on re-tap, switch sides; no emoji thumbs in buttons
- Comment up/down floaters: smooth scroll both directions
- German locale: real load (identity check), hook + overlay copy in German
- No horizontal overflow anywhere; banned-purple sweep on entry card
"""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9491
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
HUB.store.state.profile.name='Prabin';
HUB.store.state.profile.campus='Dallas College';
HUB.store.state.profile.verified=false;
HUB.store.save();
if(HUB.professors&&HUB.professors._reset) HUB.professors._reset();
return true;})()"""

def run_case(width, height, theme):
    prof = f'/tmp/hubqa-prof-{width}-{theme}'
    shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof, exist_ok=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        f'--window-size={width},{height}',
        f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tag = f'{width}x{height}-{theme}'
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
        def js_wait_ready(timeout=20):
            dl = time.time() + timeout
            while time.time() < dl:
                try:
                    r = c.send('Runtime.evaluate', {'expression': 'document.readyState', 'returnByValue': True})
                    if (r or {}).get('result', {}).get('value') == 'complete': return True
                except Exception: pass
                time.sleep(0.5)
            return False
        def arm_errs():
            js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
               "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'zero console errors @ {label} [{tag}]', json.dumps(v)[:200] if v else '')

        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        arm_errs()
        js("HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') + ";HUB.store.save();HUB.applyTheme();")
        js(SEED_JS); time.sleep(0.5)
        # Disarm the auth gate: with no session the boot poller pops the login
        # (z-220) over the app; synthetic clicks would then open the professors
        # overlay (z-60) UNDERNEATH it and Escape would correctly close the
        # topmost layer (login) — a state no real user can reach. (2026-09-29)
        js("window.__gateSkip=true;try{HUB.auth.close()}catch(e){}"
           "var w=document.getElementById('wlcmHost');if(w)w.remove();"); time.sleep(0.5)

        # ---------- A. home entry card ----------
        js("HUB.showTab('home')"); time.sleep(1.5)
        note(js("!!document.getElementById('homeProfEntry')") is True, f'entry card on home [{tag}]')
        note(js("(function(){const e=document.getElementById('homeProfEntry');"
               "return e&&e.querySelector('.prof-entry-hook').textContent.trim();})()")
             == 'Rate the ones who graded you.', f'hook copy punchy [{tag}]')
        note(js("(function(){const e=document.getElementById('homeProfEntry');"
               "return e&&e.querySelector('.prof-entry-s').textContent.trim();})()")
             == 'Find your professor, drop an honest rating, and save a freshman.', f'hook sub copy [{tag}]')
        note(js("(function(){const e=document.getElementById('homeProfEntry');"
               "return e&&e.querySelector('.prof-entry-eyebrow').textContent.trim();})()")
             == 'Professors', f'eyebrow label [{tag}]')
        note(js("!!document.querySelector('#homeProfEntry .prof-bb-svg')") is True,
             f'blackboard SVG on card [{tag}]')
        note(js("(function(){const s=document.querySelectorAll('#homeProfEntry .prof-star-draw');"
               "if(s.length!==5)return 'n='+s.length;"
               "const a=getComputedStyle(s[0]).animationName;return a;})()") == 'profChalk',
             f'5 chalk stars animated [{tag}]')
        note(js("(function(){const t=document.querySelector('#homeProfEntry .prof-teacher');"
               "return t&&getComputedStyle(t).animationName;})()") == 'profBob',
             f'teacher figure animated [{tag}]')
        # placement: classes card -> entry -> GPA card (document order)
        note(js("(function(){const a=document.getElementById('classCard'),"
               "b=document.getElementById('homeProfEntry'),d=document.getElementById('gpaCard');"
               "if(!a||!b||!d)return 'missing';"
               "return (a.compareDocumentPosition(b)&4)&& (b.compareDocumentPosition(d)&4);})()") == 4,
             f'placement classes>entry>gpa [{tag}]')
        # tab bar: professors adds NO icon (bar keeps its pre-existing 6 tabs)
        note(js("document.querySelectorAll('#tabbar .tab').length") == 6, f'no new tab icon (still 6) [{tag}]')
        note(js("document.documentElement.scrollWidth") <= width, f'home no h-overflow [{tag}]')
        note(js("""(function(){const bad=['#7C3AED','#8B5CF6','#A855F7'];
const html=document.getElementById('homeProfEntry').innerHTML.toUpperCase();
return !bad.some(h=>html.includes(h));})()""") is True, f'no banned purple on entry [{tag}]')
        js("document.getElementById('homeProfEntry').scrollIntoView({block:'center'})"); time.sleep(0.6)
        shot(f'prof-entry-{width}-{theme}')

        # ---------- B. open/close full page ----------
        js("document.getElementById('homeProfEntry').click()"); time.sleep(1.0)
        note(js("!!document.getElementById('hubProfRoot')") is True, f'overlay opens on tap [{tag}]')
        note(js("(function(){const p=document.querySelector('.prof-panel');if(!p)return -1;"
               "return Math.round(p.getBoundingClientRect().height);})()") >= height - 2,
             f'full-page height [{tag}]')
        shot(f'prof-list-{width}-{theme}')
        js("document.getElementById('profClose').click()"); time.sleep(0.6)
        note(js("!document.getElementById('hubProfRoot')") is True, f'X closes overlay [{tag}]')
        js("document.getElementById('homeProfEntry').click()"); time.sleep(1.0)
        js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))"); time.sleep(0.6)
        note(js("!document.getElementById('hubProfRoot')") is True, f'Escape closes overlay [{tag}]')

        # ---------- C. list / search ----------
        js("document.getElementById('homeProfEntry').click()"); time.sleep(1.0)
        note(js("document.querySelectorAll('.prof-card').length") >= 6, f'Dallas College profs listed [{tag}]')  # pipeline may add real directory data
        got = js("(function(){const n=document.querySelector('#profBody .prof-norate');"
                "return n&&n.textContent.trim();})()")
        note(got == 'No ratings yet — be the first.',
             f'honest no-ratings state [{tag}]', repr(got))
        js("(function(){const q=document.getElementById('profQ');q.value='shepard';"
           "q.dispatchEvent(new Event('input',{bubbles:true}));})()"); time.sleep(0.5)
        note(js("document.querySelectorAll('.prof-card').length") >= 1, f'search name finds Shepard [{tag}]')
        note(js("!document.getElementById('profClear').hidden") is True, f'clear button visible [{tag}]')
        js("(function(){const q=document.getElementById('profQ');q.value='she';"
           "q.dispatchEvent(new Event('input',{bubbles:true}));})()"); time.sleep(0.5)
        note(js("document.querySelectorAll('.prof-card').length") >= 1, f'partial search [{tag}]')
        js("document.getElementById('profClear').click()"); time.sleep(0.5)
        note(js("document.getElementById('profQ').value") == '', f'clear empties query [{tag}]')
        note(js("document.querySelectorAll('.prof-card').length") >= 6, f'clear restores list [{tag}]')
        js("(function(){const q=document.getElementById('profQ');q.value='zzz-nope';"
           "q.dispatchEvent(new Event('input',{bubbles:true}));})()"); time.sleep(0.5)
        got = js("(function(){const e=document.querySelector('#profList .empty p');"
                "return e&&e.textContent;})()")
        note(got == 'No matches for "zzz-nope".',
             f'honest no-results state [{tag}]', repr(got))
        js("document.getElementById('profClear').click()"); time.sleep(0.4)

        # ---------- D. campus scoping ----------
        js("HUB.store.state.profile.campus='Southern Methodist University';HUB.store.save();"
           "HUB.professors.close();HUB.professors.open(null);"); time.sleep(1.0)
        note(js("(function(){const t=document.getElementById('profBody').textContent;"
               "return t.indexOf('Trey Bowles')>=0 && t.indexOf('Michael Shepard')<0;})()") is True,
             f'SMU seed scoped, no DC profs [{tag}]')
        js("HUB.store.state.profile.campus='Dallas College';HUB.store.save();"
           "HUB.professors.close();HUB.professors._reset();")

        # ---------- E. unverified gate ----------
        js("HUB.professors.open('p-dc-shepard')"); time.sleep(1.0)
        note(js("!!document.getElementById('profRate')") is True, f'detail opens [{tag}]')
        js("document.getElementById('profRate').click()"); time.sleep(0.8)
        note(js("(function(){const s=document.getElementById('sheetBox');"
               "return s&&s.textContent.indexOf('Verified students only')>=0;})()") is True,
             f'unverified sees verify-only gate [{tag}]')
        note(js("!!document.getElementById('profVerifyGo')") is True, f'verify CTA present [{tag}]')
        shot(f'prof-gate-{width}-{theme}')
        js("document.getElementById('profVerifyGo').click()"); time.sleep(1.4)
        note(js("!document.getElementById('hubProfRoot')") is True, f'gate CTA leaves professors [{tag}]')
        note(js("!document.getElementById('view-me').hidden") is True, f'lands on ME tab [{tag}]')
        note(js("!document.getElementById('sheetHost').hidden") is True, f'verify sheet opens [{tag}]')
        js("HUB.ui.closeSheet()"); time.sleep(0.4)

        # ---------- F. verified rating ----------
        js("HUB.store.state.profile.verified=true;HUB.store.save();HUB.professors.open('p-dc-shepard');")
        time.sleep(1.0)
        js("document.getElementById('profRate').click()"); time.sleep(0.8)
        note(js("!!document.getElementById('rateGo')") is True, f'verified gets rate sheet [{tag}]')
        js("document.querySelectorAll('#rateStars [data-star]')[3].click()"); time.sleep(0.2)
        js("document.querySelector('#rateDiff [data-diff=\"2\"]').click()"); time.sleep(0.1)
        js("document.querySelector('#rateAgain [data-ag=\"1\"]').click()"); time.sleep(0.1)
        js("document.getElementById('rateCourse').value='ENGL 1301';"
           "document.getElementById('rateComment').value='Explains clearly and grades fairly.';")
        js("document.getElementById('rateGo').click()"); time.sleep(1.0)
        note(js("(function(){const t=document.getElementById('profBody').textContent;"
               "return t.indexOf('Explains clearly and grades fairly.')>=0;})()") is True,
             f'comment submitted [{tag}]')
        note(js("(function(){const b=document.querySelector('.prof-bignum');"
               "return b&&b.textContent.trim();})()") == '4.0', f'stats avg 4.0 [{tag}]')
        note(js("(function(){const t=document.getElementById('profBody').textContent;"
               "return t.indexOf('ENGL 1301')>=0;})()") is True, f'course chip from review [{tag}]')
        # search by course now finds him
        js("HUB.professors.open(null)"); time.sleep(1.0)
        js("(function(){const q=document.getElementById('profQ');q.value='engl 1301';"
           "q.dispatchEvent(new Event('input',{bubbles:true}));})()"); time.sleep(0.5)
        note(js("(function(){return document.getElementById('profBody').textContent.indexOf('Michael Shepard')>=0;})()") is True,
             f'search by course [{tag}]')
        js("HUB.professors.open('p-dc-shepard')"); time.sleep(1.0)
        shot(f'prof-detail-{width}-{theme}')

        # ---------- G. like / dislike (on ANOTHER student's comment) ----------
        # the section-F review belongs to the seeded profile, so self-voting is
        # now disabled on it; inject a classmate's review and vote on THAT one.
        js("HUB.professors._add('p-dc-shepard',{q:4,d:3,again:1,course:'ENGL 1301',"
           "comment:'QA votable comment by classmate.',author:'Classmate',authorId:'qa-classmate-aid'});")
        js("HUB.professors.open('p-dc-shepard')")  # _add does not repaint; re-render the detail
        time.sleep(1.2)
        rid = js("HUB.professors._reviews('p-dc-shepard')[0].id")
        note(isinstance(rid, str) and len(rid) > 0, f'review id readable [{tag}]')
        # own (section-F) review is now vote-disabled
        note(js("(function(){const r=[...document.querySelectorAll('.prof-rev')].find(x=>x.textContent.indexOf('Explains clearly')>=0);"
               "const b=r&&r.querySelector('[data-vote=\"1\"]');"
               "return !!(b&&b.classList.contains('is-own')&&b.getAttribute('aria-disabled')==='true');})()") is True,
             f'own review vote-disabled [{tag}]')
        note(js("!!document.querySelector('.prof-vote[data-vote=\"1\"] .prof-heart')") is True,
             f'heart SVG present [{tag}]')
        note(js("!!document.querySelector('.prof-vote[data-vote=\"-1\"] .prof-thumb')") is True,
             f'thumbs-down SVG present [{tag}]')
        note(js("(function(){const b=document.querySelector('.prof-vote[data-vote=\"1\"]');"
               "return b.textContent.indexOf('👍')<0;})()") is True, f'no emoji thumbs [{tag}]')
        js(f"document.querySelector('.prof-vote[data-rid=\"{rid}\"][data-vote=\"1\"]').click()"); time.sleep(0.4)
        note(js(f"(function(){{const b=document.querySelector('.prof-vote[data-rid=\"{rid}\"][data-vote=\"1\"]');"
               "return b.classList.contains('on')&&b.querySelector('b').textContent==='1';})()") is True,
             f'like increments [{tag}]')
        note(js("(function(){const cs=getComputedStyle(document.querySelector('.prof-vote.on .prof-heart'));"
               "return cs.filter.indexOf('drop-shadow')>=0;})()") is True, f'heart glows [{tag}]')
        js(f"document.querySelector('.prof-vote[data-rid=\"{rid}\"][data-vote=\"1\"]').click()"); time.sleep(0.4)
        note(js(f"(function(){{const b=document.querySelector('.prof-vote[data-rid=\"{rid}\"][data-vote=\"1\"]');"
               "return !b.classList.contains('on')&&b.querySelector('b').textContent==='0';})()") is True,
             f'like undo on re-tap [{tag}]')
        js(f"document.querySelector('.prof-vote[data-rid=\"{rid}\"][data-vote=\"-1\"]').click()"); time.sleep(0.4)
        note(js(f"(function(){{const b=document.querySelector('.prof-vote[data-rid=\"{rid}\"][data-vote=\"-1\"]');"
               "return b.classList.contains('on')&&b.querySelector('b').textContent==='1';})()") is True,
             f'dislike increments [{tag}]')
        js(f"document.querySelector('.prof-vote[data-rid=\"{rid}\"][data-vote=\"1\"]').click()"); time.sleep(0.4)
        got = js(f"(function(){{const l=document.querySelector('.prof-vote[data-rid=\"{rid}\"][data-vote=\"1\"] b').textContent;"
               f"const d=document.querySelector('.prof-vote[data-rid=\"{rid}\"][data-vote=\"-1\"] b').textContent;"
               "return l+'/'+d;})()")
        note(got == '1/0', f'switch sides adjusts [{tag}]', repr(got))

        # ---------- H. comment scroll controls ----------
        js("(function(){for(let i=0;i<8;i++)HUB.professors._add('p-dc-shepard',"
           "{q:5-(i%2),d:3,again:1,course:'ENGL 1301',comment:'Seeded comment number '+i+' for scroll testing.',author:'Prabin'});"
           "HUB.professors.open('p-dc-shepard');return true;})()"); time.sleep(1.2)
        note(js("!!document.getElementById('profGoDown')") is True, f'down floater present [{tag}]')
        note(js("document.getElementById('profGoUp').hidden") is True, f'up hidden at top [{tag}]')
        s0 = js("document.getElementById('profBody').scrollTop")
        js("document.getElementById('profGoDown').click()"); time.sleep(1.2)
        s1 = js("document.getElementById('profBody').scrollTop")
        note(isinstance(s1, (int, float)) and s1 > (s0 or 0), f'down scrolls smoothly [{tag}]', f'{s0}->{s1}')
        note(js("!document.getElementById('profGoUp').hidden") is True, f'up appears after scroll [{tag}]')
        js("document.getElementById('profGoUp').click()"); time.sleep(1.2)
        s2 = js("document.getElementById('profBody').scrollTop")
        note(isinstance(s2, (int, float)) and s2 < s1, f'up scrolls back [{tag}]', f'{s1}->{s2}')
        note(js("document.documentElement.scrollWidth") <= width, f'overlay no h-overflow [{tag}]')

        # ---------- I. German (real language switch) ----------
        js("HUB.i18n.setLang('de')"); time.sleep(1.5)
        note(js("HUB.i18n.getLang()") == 'de', f'de active [{tag}]')
        note(js("HUB.i18n._dict('de')!==HUB.i18n._dict('en')") is True, f'de genuinely loaded [{tag}]')
        js("HUB.professors.close();HUB.showTab('home')"); time.sleep(1.2)
        note(js("(function(){const e=document.getElementById('homeProfEntry');"
               "return e&&e.querySelector('.prof-entry-hook').textContent.trim();})()")
             == 'Bewerte die, die dich benotet haben.', f'de hook copy [{tag}]')
        js("document.getElementById('homeProfEntry').click()"); time.sleep(1.0)
        note(js("(function(){return document.querySelector('.prof-topbar-t').textContent.trim();})()")
             == 'Professoren', f'de overlay title [{tag}]')
        note(js("document.documentElement.scrollWidth") <= width, f'de no h-overflow [{tag}]')
        errs('final')
    finally:
        proc.terminate()

for w, h in [(390, 844), (320, 568)]:
    for th in ['dark', 'light']:
        run_case(w, h, th)

n_fail = sum(1 for ok, _ in checks if not ok)
print(f'{len(checks)-n_fail}/{len(checks)} passed')
raise SystemExit(1 if n_fail else 0)
