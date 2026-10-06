#!/usr/bin/env python3
"""HUB QA: Home "People in {campus}" head row + clear-glass 3D profile sheet.
Fresh profile, 390x844, dark+light. Covers: placement (below capsule pill,
above glance), campus title, public-only filtering (private absent), row
scroll w/o page overflow, glass sheet open (name/major/year/college/
distance/bio/interests) + close via X/scrim/Escape, privacy toggle default
OFF -> ON (own head first with "You", persists across reload), lazy de
locale with new kh, zero console errors."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9461
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-hppl'
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
def seed(c, name, campus):
    c.js("(()=>{const p=HUB.store.state.profile; p.name=%s; p.campus=%s; HUB.store.save(); const w=document.getElementById('wlcmHost'); if(w) w.remove(); return 'seeded'})()" % (json.dumps(name), json.dumps(campus)))
def set_theme(c, dark):
    c.js("(()=>{HUB.store.state.prefs.dark=%s; HUB.store.save(); HUB.applyTheme(); return 't'})()" % ('true' if dark else 'false'))
    time.sleep(0.8)
def no_overflow(c):
    v, _ = c.js("document.documentElement.scrollWidth<=window.innerWidth")
    return bool(v)

def main():
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--disable-dev-shm-usage', f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        f'--user-data-dir={PROF}', '--allow-file-access-from-files', '--hide-scrollbars',
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
        c.send('Page.navigate', {'url': BASE}); time.sleep(3.5)
        hook_err(c); seed(c, 'Prabin QA', 'Riverside State')
        c.js("HUB.showTab('home')"); time.sleep(1.5)

        # lazy de locale: real load (object identity) + new key + kh guard
        lv, _ = c.js("HUB.i18n.loadLocale('de').then(ok=>({ok:ok,ident:HUB.i18n._dict('de')!==HUB.i18n._dict('en'),pub:HUB.i18n._dict('de')['pedit.pubProf'],kh:document.querySelector('html').lang}))", awaitPromise=True)
        note(bool(lv and lv.get('ok') and lv.get('ident')), 'lazy de locale really loads (identity)', str(lv)[:140])
        note(bool(lv and 'ffentlich' in str(lv.get('pub') or '')), 'de pedit.pubProf translated', str((lv or {}).get('pub')))
        c.js("HUB.i18n.setLang('en')"); time.sleep(0.8)
        c.js("HUB.showTab('home')"); time.sleep(1.0)

        for theme, dark in [('dark', True), ('light', False)]:
            set_theme(c, dark)
            c.js("HUB.showTab('home')"); time.sleep(1.2)

            sec = wait_js(c, "!!document.getElementById('homePplSec')")
            note(bool(sec), f'[{theme}] people section renders on Home')
            # placement: below capsule pill/manifest, above glance carousel
            pos, _ = c.js("(()=>{const s=document.getElementById('homePplSec'); if(!s) return null;"
                "const r=s.getBoundingClientRect(); const cap=document.querySelector('.capmanifest');"
                "const gl=document.getElementById('glanceSec')||document.querySelector('.glance');"
                "return {top:r.top, capB:cap?cap.getBoundingClientRect().bottom:-1,"
                " glT:gl?gl.getBoundingClientRect().top:1e9}})()")
            note(bool(pos and pos['top'] >= pos['capB']), f'[{theme}] section is BELOW the Time Capsule manifest line', str(pos))
            note(bool(pos and pos['top'] < pos['glT']), f'[{theme}] section is ABOVE "Today at a glance"', str(pos))
            ttl, _ = c.js("document.querySelector('#homePplSec h2').textContent")
            note('Riverside State' in str(ttl), f'[{theme}] title carries the campus name', str(ttl))
            cnt, _ = c.js("document.querySelectorAll('#homePplSec [data-hp]').length")
            note(cnt == 9, f'[{theme}] exactly 9 public heads (3 private hidden)', 'heads=%s' % cnt)
            priv, _ = c.js("['Lena Fischer','Kenji Tanaka','Chris Novak'].some(n=>document.getElementById('homePplSec').textContent.indexOf(n)>=0)")
            note(not priv, f'[{theme}] private profiles absent from the row')
            row, _ = c.js("(()=>{const r=document.querySelector('.hp-row'); const rr=r.getBoundingClientRect();"
                "return {scrolls:r.scrollWidth>r.clientWidth+4, inView:rr.left>=0&&rr.right<=window.innerWidth+1}})()")
            note(bool(row and row['inView']), f'[{theme}] row contained, no page overflow', str(row))
            note(no_overflow(c), f'[{theme}] no horizontal page overflow')
            shot(c, f'people-row-{theme}'); drain_err(c, f'row-{theme}')

            # glass sheet: open via first head
            c.js("document.querySelector('#homePplSec [data-hp]').click()"); time.sleep(0.9)
            gopen, _ = c.js("!document.getElementById('hpGlass').hidden")
            note(bool(gopen), f'[{theme}] tap head -> glass sheet opens')
            g, _ = c.js("(()=>{const d=document.getElementById('hpGlassCard');"
                "return {name:d.querySelector('.hpglass-name').textContent,"
                " major:d.querySelector('.hpglass-major').textContent,"
                " meta:d.querySelector('.hpglass-meta').textContent,"
                " bio:!!d.querySelector('.hpglass-bio'), chips:d.querySelectorAll('.hpglass-chips .ppl-skill').length,"
                " demo:d.textContent.indexOf('Demo profile')>=0}})()")
            note(bool(g and g['name'] and '🎓' in g['major']), f'[{theme}] sheet: name + major prominent', str(g)[:160])
            note(bool(g and 'Riverside State' in g['meta'] and 'mi away' in g['meta']), f'[{theme}] sheet: year/college/distance', str((g or {}).get('meta')))
            note(bool(g and g['bio'] and g['chips'] >= 2 and g['demo']), f'[{theme}] sheet: bio + interests + demo note', str(g)[:160])
            contained, _ = c.js("(()=>{const d=document.querySelector('.hpglass-card'); const r=d.getBoundingClientRect();"
                "return r.left>=0&&r.right<=window.innerWidth+1&&r.width<=410})()")
            note(bool(contained), f'[{theme}] glass card contained in phone column')
            shot(c, f'people-sheet-{theme}')
            # close via X
            c.js("document.getElementById('hpGlassX').click()"); time.sleep(0.5)
            xclosed, _ = c.js("document.getElementById('hpGlass').hidden")
            note(bool(xclosed), f'[{theme}] close via X button')
            # close via scrim
            c.js("document.querySelector('#homePplSec [data-hp]').click()"); time.sleep(0.7)
            c.js("(()=>{const g=document.getElementById('hpGlass'); const r=g.getBoundingClientRect();"
                "const e=new MouseEvent('click',{bubbles:true,clientX:r.left+8,clientY:r.top+8}); g.dispatchEvent(e); return 1})()")
            time.sleep(0.5)
            sclosed, _ = c.js("document.getElementById('hpGlass').hidden")
            note(bool(sclosed), f'[{theme}] close via scrim tap')
            # close via Escape
            c.js("document.querySelector('#homePplSec [data-hp]').click()"); time.sleep(0.7)
            c.send('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
            c.send('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
            time.sleep(0.5)
            eclosed, _ = c.js("document.getElementById('hpGlass').hidden")
            note(bool(eclosed), f'[{theme}] close via Escape')
            drain_err(c, f'sheet-{theme}')

            # privacy: default OFF -> own head absent
            own0, _ = c.js("!!document.querySelector('#homePplSec [data-hp=\"hp-self\"]')")
            note(not own0, f'[{theme}] own head absent by default (toggle OFF)')

        # flip the toggle ON via Edit profile, add major/year
        c.js("HUB.showTab('me')"); time.sleep(1.2)
        c.js("document.getElementById('meEditBtn').click()"); time.sleep(0.8)
        tog, _ = c.js("(()=>{const el=document.getElementById('peditPub'); return el?el.getAttribute('aria-checked'):null})()")
        note(tog == 'false', 'privacy toggle defaults OFF in Edit profile', 'aria-checked=%s' % tog)
        c.js("(()=>{document.getElementById('peditMajor').value='Computer Science';"
            "document.getElementById('peditYear').value='Senior';"
            "document.getElementById('peditPub').click(); return 1})()")
        time.sleep(0.4)
        tog2, _ = c.js("document.getElementById('peditPub').getAttribute('aria-checked')")
        note(tog2 == 'true', 'toggle flips ON')
        c.js("document.getElementById('peditSave').click()"); time.sleep(1.0)
        c.js("HUB.showTab('home')"); time.sleep(1.2)
        first, _ = c.js("(()=>{const h=document.querySelectorAll('#homePplSec [data-hp]');"
            "return h.length?{first:h[0].dataset.hp, you:!!h[0].querySelector('.hp-you'), n:h.length}:null})()")
        note(bool(first and first['first'] == 'hp-self' and first['you']), 'own head appears FIRST with "You" badge', str(first))
        # own sheet shows major/year
        c.js("document.querySelector('#homePplSec [data-hp=\"hp-self\"]').click()"); time.sleep(0.8)
        sm, _ = c.js("(()=>{const d=document.getElementById('hpGlassCard');"
            "return {major:d.querySelector('.hpglass-major').textContent, meta:d.querySelector('.hpglass-meta').textContent}})()")
        note(bool(sm and 'Computer Science' in sm['major'] and 'Senior' in sm['meta']), 'own sheet shows major + year', str(sm))
        c.js("document.getElementById('hpGlassX').click()"); time.sleep(0.4)
        drain_err(c, 'toggle-on')

        # persistence across reload
        c.send('Page.navigate', {'url': BASE}); time.sleep(3.5)
        hook_err(c)
        c.js("(()=>{const w=document.getElementById('wlcmHost'); if(w) w.remove(); HUB.showTab('home'); return 1})()")
        time.sleep(1.5)
        pers, _ = c.js("(()=>{const h=document.querySelectorAll('#homePplSec [data-hp]');"
            "return h.length&&h[0].dataset.hp==='hp-self'&&!!h[0].querySelector('.hp-you')})()")
        note(bool(pers), 'toggle ON + own head persist across reload')
        drain_err(c, 'reload')

        print('\n==== %d/%d checks passed, %d error groups ====' % (sum(1 for ok, _ in checks if ok), len(checks), len(errors)))
        for ok, label in checks:
            if not ok: print('FAILED:', label)
    finally:
        proc.terminate()

main()
