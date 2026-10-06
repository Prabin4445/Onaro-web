#!/usr/bin/env python3
"""HUB QA: People glass-sheet upgrades — no miles, Follow, group Request-to-join.
Fresh profile, 390x844 (true device metrics), dark+light. Covers:
- zero mile text anywhere on the row or in the sheet (.hp-mi gone, no "N mi")
- 9 demo groups seeded as real sample cgroups (sample:true, mine+live)
- Follow toggles Follow->Following->Follow, count +1, persists across reload
- Request to join uses the real groups path: g.requests -> Notifications row ->
  group page pending -> approve -> member; sheet shows "You're a member"
- lazy de locale really loads under the new kh (identity check)
- zero console errors.
State flows: dark does the destructive flow; light re-verifies visuals + carried state."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9462
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-hppl2'
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
def set_theme(c, dark):
    c.js("(()=>{HUB.store.state.prefs.dark=%s; HUB.store.save(); HUB.applyTheme(); return 't'})()" % ('true' if dark else 'false'))
    time.sleep(0.8)
def open_first_sheet(c):
    c.js("document.querySelector('#homePplSec [data-hp]:not([data-hp=\"hp-self\"])').click()")
    time.sleep(0.9)
    return c.js("!document.getElementById('hpGlass').hidden")[0]
def no_miles(c):
    return c.js("(()=>{const a=document.querySelectorAll('.hp-mi').length;"
        "const t=(document.getElementById('homePplSec')?document.getElementById('homePplSec').textContent:'')"
        "+(document.getElementById('hpGlassCard')?document.getElementById('hpGlassCard').textContent:'');"
        "return {badges:a, mileText:/\\b\\d+(\\.\\d+)?\\s?mi\\b/i.test(t)}})()")[0]

def main():
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--disable-dev-shm-usage', f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        f'--user-data-dir={PROF}', '--allow-file-access-from-files', '--hide-scrollbars',
        '--no-first-run', '--no-default-browser-check', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(1)
        try: targets(); break
        except Exception: pass
    else:
        proc.terminate(); raise SystemExit('chrome did not come up')
    try:
        t = [x for x in targets() if x['type'] == 'page'][0]
        c = CDP(t['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable')
        c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        c.send('Page.navigate', {'url': BASE}); time.sleep(3.5)
        hook_err(c)
        c.js("(()=>{const p=HUB.store.state.profile; p.name='PraBin Test'; p.campus='Riverside State';"
            "HUB.store.save(); const w=document.getElementById('wlcmHost'); if(w) w.remove();"
            "HUB.showTab('home'); return 1})()")
        time.sleep(1.5)

        # ---- demo groups seeded as real sample cgroups ----
        gg, _ = c.js("(()=>{const gs=(HUB.store.state.cgroups||[]).filter(g=>g&&g.hpGroup);"
            "return {n:gs.length, allSample:gs.every(g=>g.sample===true), allLive:gs.every(g=>g.live===true),"
            " allMine:gs.every(g=>g.mine===true)}})()")
        note(bool(gg and gg['n'] == 9 and gg['allSample'] and gg['allLive'] and gg['allMine']),
             '9 demo groups seeded as real sample cgroups (sample+mine+live)', str(gg))
        gf, _ = c.js("(()=>{const p=HUB.people.hpList()[0]; const g=HUB.people.hpGroupFor(p);"
            "return g?{name:g.name, members:g.members.length}:null})()")
        note(bool(gf and gf['name'] and gf['members'] >= 2), 'hpGroupFor resolves group for a public person', str(gf))

        wait_js(c, "!!document.getElementById('homePplSec')")
        tmiss, _ = c.js("HUB.i18n.t('hp.mi')==='hp.mi' && HUB.i18n.t('hp.away')==='hp.away'")
        note(bool(tmiss), 'hp.mi/hp.away keys fully removed from bundle (fallback to key)')

        # ================= DARK: full destructive flow =================
        set_theme(c, True)
        c.js("HUB.showTab('home')"); time.sleep(1.2)
        nm = no_miles(c)
        note(bool(nm and nm['badges'] == 0 and not nm['mileText']), '[dark] no miles: row + sheet', str(nm))
        heads, _ = c.js("document.querySelectorAll('#homePplSec [data-hp]').length")
        note(heads == 9, '[dark] exactly 9 public heads (3 private hidden)', 'heads=%s' % heads)

        note(bool(open_first_sheet(c)), '[dark] tap head -> glass sheet opens')
        sh, _ = c.js("(()=>{const d=document.getElementById('hpGlassCard');"
            "const fb=document.getElementById('hpFolBtn'); const rq=document.getElementById('hpReqJoin');"
            "return {folks:d.querySelector('.hpglass-folks').textContent,"
            " folBtn:fb?fb.textContent.trim():null, groups:!!(d.textContent.indexOf(\"Priya's Study Circle\")>=0),"
            " reqBtn:rq?rq.textContent.trim():null, members:(d.textContent.match(/(\\d+) members/)||[])[1]}})()")
        note(bool(sh and '214 followers' in sh['folks'] and sh['folBtn'] == '+ Follow'),
             '[dark] followers 214 + Follow button', str(sh))
        note(bool(sh and sh['groups'] and sh['reqBtn'] and 'Request to join' in sh['reqBtn'] and sh['members'] == '4'),
             '[dark] Groups section: created group, 4 members, Request-to-join', str(sh))

        # follow toggle ON
        c.js("document.getElementById('hpFolBtn').click()"); time.sleep(0.7)
        f1, _ = c.js("(()=>{const d=document.getElementById('hpGlassCard');"
            "return {btn:document.getElementById('hpFolBtn').textContent.trim(),"
            " folks:d.querySelector('.hpglass-folks').textContent, inStore:HUB.store.state.following.length}})()")
        note(bool(f1 and f1['btn'] == '✓ Following' and '215 followers' in f1['folks'] and f1['inStore'] == 1),
             '[dark] Follow -> Following, 214->215, in store', str(f1))
        shot(c, 'people-sheet-follow-dark'); drain_err(c, 'follow-dark')

        # request to join -> real groups path
        c.js("document.getElementById('hpReqJoin').click()"); time.sleep(0.7)
        r1, _ = c.js("(()=>{const p=HUB.people.hpList()[0]; const g=HUB.people.hpGroupFor(p);"
            "const d=document.getElementById('hpGlassCard');"
            "return {reqs:(g.requests||[]).map(r=>r.name),"
            " pendingBtn:[...d.querySelectorAll('button[disabled]')].some(b=>b.textContent.indexOf('Request sent')>=0),"
            " joinGone:!document.getElementById('hpReqJoin'),"
            " toast:document.getElementById('toastHost').textContent}})()")
        note(bool(r1 and 'PraBin Test' in r1['reqs'] and r1['pendingBtn'] and r1['joinGone']),
             '[dark] Request to join -> real g.requests + "Request sent" state', str({k: r1[k] for k in ('reqs','pendingBtn','joinGone')}))
        note(bool(r1 and 'Request sent' in r1['toast']), '[dark] request toast shown', str((r1 or {}).get('toast'))[:80])
        drain_err(c, 'request-dark')

        # notification -> group page -> approve
        c.js("HUB.people.closeGlass(); HUB.notifications.open()"); time.sleep(1.0)
        nrow, _ = c.js("(()=>{const items=[...document.querySelectorAll('#hubNotifRows .item')];"
            "const hit=items.find(el=>el.textContent.indexOf('wants to join')>=0);"
            "return hit?{nid:hit.dataset.nid, ok:hit.textContent.indexOf(\"Priya's Study Circle\")>=0}:null})()")
        note(bool(nrow and nrow['ok']), '[dark] join request appears in Notifications', str(nrow))
        if nrow:
            c.js("(()=>{const items=[...document.querySelectorAll('#hubNotifRows .item')];"
                 "const hit=items.find(el=>el.textContent.indexOf('wants to join')>=0); if(hit) hit.click()})()")
            time.sleep(1.2)
            gp, _ = c.js("(()=>{const el=document.getElementById('view-groups');"
                "return el?el.textContent.indexOf(\"Priya's Study Circle\")>=0:false})()")
            note(bool(gp), '[dark] tapping notification opens the group page')
            c.js("document.querySelector('#view-groups [data-appr]').click()"); time.sleep(0.9)
            mem2, _ = c.js("(()=>{const p=HUB.people.hpList()[0]; const g=HUB.people.hpGroupFor(p);"
                "return {members:g.members, reqs:(g.requests||[]).length}})()")
            note(bool(mem2 and 'PraBin Test' in mem2['members'] and mem2['reqs'] == 0),
                 '[dark] approve -> member added, request cleared', str(mem2))
        drain_err(c, 'notif-dark')

        # ================= LIGHT: visuals + carried state =================
        set_theme(c, False)
        c.js("HUB.showTab('home')"); time.sleep(1.2)
        nm2 = no_miles(c)
        note(bool(nm2 and nm2['badges'] == 0 and not nm2['mileText']), '[light] no miles: row + sheet', str(nm2))
        note(bool(open_first_sheet(c)), '[light] tap head -> glass sheet opens')
        sh2, _ = c.js("(()=>{const d=document.getElementById('hpGlassCard');"
            "return {folks:d.querySelector('.hpglass-folks').textContent,"
            " folBtn:document.getElementById('hpFolBtn').textContent.trim(),"
            " member:d.textContent.indexOf(\"You're a member\")>=0,"
            " groups:d.textContent.indexOf(\"Priya's Study Circle\")>=0}})()")
        note(bool(sh2 and '215 followers' in sh2['folks'] and sh2['folBtn'] == '✓ Following' and sh2['member'] and sh2['groups']),
             '[light] sheet: Following/215 + already-a-member + group, no miles', str(sh2))
        contained, _ = c.js("(()=>{const d=document.getElementById('hpGlass'); const r=d.getBoundingClientRect();"
            "return r.left>=0&&r.right<=window.innerWidth+1})()")
        note(bool(contained), '[light] glass overlay contained in viewport')
        note(bool(c.js("document.documentElement.scrollWidth<=window.innerWidth+1")[0]), '[light] no horizontal page overflow')
        shot(c, 'people-sheet-member-light'); drain_err(c, 'light')

        # ================= reload: follow persists, then unfollow =================
        c.send('Page.navigate', {'url': BASE}); time.sleep(3.5)
        hook_err(c)
        c.js("(()=>{const w=document.getElementById('wlcmHost'); if(w) w.remove(); HUB.showTab('home'); return 1})()")
        time.sleep(1.5)
        open_first_sheet(c)
        pf, _ = c.js("(()=>{const d=document.getElementById('hpGlassCard');"
            "return {btn:document.getElementById('hpFolBtn').textContent.trim(),"
            " folks:d.querySelector('.hpglass-folks').textContent}})()")
        note(bool(pf and pf['btn'] == '✓ Following' and '215 followers' in pf['folks']),
             'follow persists across reload (Following, 215 followers)', str(pf))
        c.js("document.getElementById('hpFolBtn').click()"); time.sleep(0.7)
        pf2, _ = c.js("(()=>{const d=document.getElementById('hpGlassCard');"
            "return {btn:document.getElementById('hpFolBtn').textContent.trim(),"
            " folks:d.querySelector('.hpglass-folks').textContent, inStore:HUB.store.state.following.length}})()")
        note(bool(pf2 and pf2['btn'] == '+ Follow' and '214 followers' in pf2['folks'] and pf2['inStore'] == 0),
             'unfollow toggles back (Follow, 214 followers, store cleared)', str(pf2))
        c.js("document.getElementById('hpGlassX').click()"); time.sleep(0.4)
        drain_err(c, 'reload')

        # ================= lazy de locale under the NEW kh =================
        lv, _ = c.js("HUB.i18n.loadLocale('de').then(ok=>({ok:ok,ident:HUB.i18n._dict('de')!==HUB.i18n._dict('en'),"
            "join:HUB.i18n._dict('de')['hp.joinGroup'],fol:HUB.i18n._dict('de')['hp.followers'],"
            "grp:HUB.i18n._dict('de')['hp.groups'],miles:('hp.mi' in HUB.i18n._dict('de'))}))", awaitPromise=True)
        note(bool(lv and lv.get('ok') and lv.get('ident')), 'lazy de loads under new kh (identity, not fallback)', str(lv)[:200])
        note(bool(lv and lv.get('join') == 'Beitritt anfragen' and '{n}' in str(lv.get('fol'))
             and lv.get('grp') == 'Gruppen' and lv.get('miles') is False),
             'de translations present (join/followers/groups), mile keys gone', str({k: lv.get(k) for k in ('join','fol','grp','miles')}))
        drain_err(c, 'locale')

        print('\n==== %d/%d checks passed, %d error groups ====' % (sum(1 for ok, _ in checks if ok), len(checks), len(errors)))
        for ok, label in checks:
            if not ok: print('FAILED:', label)
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
