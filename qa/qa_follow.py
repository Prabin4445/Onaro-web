#!/usr/bin/env python3
"""QA: follow -> notification -> profile overview -> connect/message flow."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9443
BASE = 'file:///home/hatch/workspace/hub/index.html'
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
def main():
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        '--user-data-dir=/tmp/hubqa-follow2', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as r:
                    ts = json.load(r)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        def js(expr):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
                res = (r or {}).get('result', {})
                return res.get('value'), None
            except Exception as e: return None, str(e)[:160]
        def errs(label):
            v, _ = js("window.__huberr.splice(0)")
            if v: errors.append((label, v)); print('ERRORS @', label, ':', json.dumps(v)[:400])
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data']))
            print('shot:', name)
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(3)
        errs('load')
        # fresh profile -> seed followers + followerEvents; complete onboarding so tabs render
        js("""try{
          localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));
          var st=JSON.parse(localStorage.getItem('hub_v1')||'null');
          if(st){st.profile=st.profile||{}; st.profile.name='QA'; st.profile.campus='Riverside State'; st.profile.audience='student';
            localStorage.setItem('hub_v1',JSON.stringify(st));}
        }catch(e){}""")
        time.sleep(1)
        js("location.reload()")
        time.sleep(4)
        errs('reload')

        # (a) follow state seeded: two sample followers + events
        v, _ = js("JSON.stringify({followers:(HUB.store.state.followers||[]).length, events:(HUB.store.state.followerEvents||[]).length})")
        d = json.loads(v or '{}')
        note(d.get('followers') == 2 and d.get('events') == 2, 'seed: 2 followers + 2 follow events', str(v))

        # (b) bell dot visible (unread follow notifications)
        v, _ = js("HUB.notifications.unreadCount()")
        note((v or 0) > 0, 'bell shows unread notifications', 'unreadCount=' + str(v))
        v, _ = js("var nd=document.getElementById('notifDot'); nd?String(nd.hidden):'no-dot-el'")
        note(v == 'false', 'bell dot visible on startup', 'notifDot.hidden=' + str(v))

        # open notifications, verify follow rows render
        js("HUB.notifications.open()")
        time.sleep(0.8)
        v, _ = js("[...document.querySelectorAll('#hubNotifRows .item')].map(el=>el.textContent).join(' || ').slice(0,1200)")
        note('Maya Chen' in str(v) and 'followed you' in str(v), 'follow notification rows render', str(v)[str(v).find('Maya'):str(v).find('Maya')+120])
        v, _ = js("(()=>{const h=[...document.querySelectorAll('#hubNotifRows h3')].map(e=>e.textContent).join('|'); return h})()")
        note('People' in str(v), 'People section in notifications', str(v)[:120])
        shot('follow-notifications')
        errs('notif-open')

        # (c) tap Maya Chen's row -> profile overview opens
        js("""(()=>{const rows=[...document.querySelectorAll('#hubNotifRows .item')];
          const row=rows.find(el=>el.textContent.indexOf('Maya Chen')>=0); if(row) row.click();})()""")
        time.sleep(0.8)
        v, _ = js("JSON.stringify({sheet:!!document.querySelector('.ppl-prof'), name:(document.querySelector('.ppl-prof .ppl-name')||{}).textContent||'', notifGone:!document.getElementById('hubNotifRoot')})")
        d = json.loads(v or '{}')
        note(d.get('sheet') and 'Maya Chen' in d.get('name',''), 'tap notification -> profile overview', str(v)[:140])
        note(d.get('notifGone'), 'notifications closed on deep-link', '')
        shot('follow-profile')
        errs('profile-open')

        # profile has working follow + message buttons
        v, _ = js("JSON.stringify({fol:!!document.getElementById('ppFol'), msg:!!document.getElementById('ppMsg')})")
        d = json.loads(v or '{}')
        note(d.get('fol') and d.get('msg'), 'profile has follow + message buttons', str(v))

        # (d) follow back (connect) -> mutual
        v, _ = js("document.getElementById('ppFol').click(); 'clicked'")
        time.sleep(0.6)
        v, _ = js("""(()=>{const p=HUB.store.state.people.find(x=>x.name==='Maya Chen');
          return JSON.stringify({following:HUB.people.isFollowing(p.id), mutual:HUB.people.isMutual(p.id)});})()""")
        d = json.loads(v or '{}')
        note(d.get('following') and d.get('mutual'), 'follow-back creates mutual connection', str(v))
        errs('follow-back')

        # reopen profile -> mutual badge visible
        js("(()=>{const p=HUB.store.state.people.find(x=>x.name==='Maya Chen'); HUB.people.openProfile(p.id);})()")
        time.sleep(0.6)
        v, _ = js("document.querySelector('.ppl-prof').textContent.indexOf('\U0001F91D')>=0")
        note(v is True, 'mutual 🤝 badge on profile', '')

        # (e) message -> chat thread opens directly (mutual, no gate)
        js("document.getElementById('ppMsg').click()")
        time.sleep(1.0)
        v, _ = js("JSON.stringify({chat:!document.getElementById('chatRoot').hidden, gate:!!document.querySelector('.sheethost')&&document.querySelector('.sheethost').textContent.indexOf('gateT')>=0||document.body.textContent.indexOf('mutual')>=0})")
        d = json.loads(v or '{}')
        v2, _ = js("(()=>{const r=document.getElementById('chatRoot'); return r&&!r.hidden?document.querySelector('#chatRoot h3').textContent:'HIDDEN'})()")
        note('Maya Chen' in str(v2), 'message opens chat thread with Maya', str(v2)[:60])
        shot('follow-thread')
        errs('thread-open')
        js("HUB.chat.close()")

        # gate path: Alex Rivera (not followed back) -> message shows honest gate
        js("(()=>{const p=HUB.store.state.people.find(x=>x.name==='Alex Rivera'); HUB.people.openProfile(p.id);})()")
        time.sleep(0.6)
        js("document.getElementById('ppMsg').click()")
        time.sleep(0.6)
        v, _ = js("(()=>{const sh=document.querySelector('.sheethost'); return sh?sh.textContent.slice(0,120):'NO-SHEET'})()")
        note('follow' in str(v).lower() or 'Follow' in str(v), 'non-mutual message shows follow gate', str(v)[:100])
        shot('follow-gate')
        errs('gate')

        print('\n==== checks:', sum(1 for ok, _ in checks if ok), '/', len(checks))
        for ok, label in checks:
            if not ok: print('FAILED:', label)
        if errors: print('JS ERRORS:', json.dumps(errors)[:600])
    finally:
        proc.terminate()
main()
