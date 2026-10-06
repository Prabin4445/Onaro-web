#!/usr/bin/env python3
"""QA: Group invite links — share sheet, copy, deep-link boot (known + unknown id),
draft guardrail, member visibility, lazy locales. Zero console errors."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9449
BASE = 'file:///home/hatch/workspace/hub/index.html'
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

def boot_js(c):
    # reinstall error trap + seed profile/welcome-skip; returns when HUB ready
    c.send('Runtime.evaluate', {'expression':
        "window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
        "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))"})
    time.sleep(4)
    c.send('Runtime.evaluate', {'expression':
        "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
        "HUB.store.state.profile.name='QA';HUB.store.state.profile.campus='Riverside State';"
        "HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}"})
    time.sleep(1)

def run(theme, full):
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-ginv-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        c.send('Runtime.enable'); c.send('Page.enable')
        def js(expr):
            r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
            return (r or {}).get('result', {}).get('value')
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name), 'wb').write(base64.b64decode(r['data']))
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'{theme}: {label} zero errors', json.dumps(v)[:200] if v else '')
        def nav(url):
            # hash-only change is a same-document navigation (no reload, no boot):
            # set the hash explicitly, then force a full reload so boot runs.
            if '#' in url:
                frag = url.split('#', 1)[1]
                js('location.hash=' + json.dumps('#' + frag))
                c.send('Page.reload')
            else:
                c.send('Page.navigate', {'url': url})
            boot_js(c)

        nav(BASE)  # plain boot (no hash): no invite UI should auto-open
        errs('boot')
        v = js("document.getElementById('sheetHost').hidden && !document.getElementById('cgInviteBtn')")
        note(v, f'{theme}: no invite UI on plain boot', str(v))
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()});")

        # --- invite button on admin's live group ---
        gid = js("HUB.store.state.cgroups.find(g=>g.name==='Weekend Hikers').id")
        js(f"HUB.cgroups.openClub('{gid}')"); time.sleep(1.0)
        v = js("!!document.getElementById('cgInviteBtn')")
        note(v, f'{theme}: invite button on admin group page', str(v))

        # --- share sheet: link field ---
        js("document.getElementById('cgInviteBtn').click()"); time.sleep(0.8)
        v = js("(()=>{const i=document.getElementById('ginvLink'); return i?i.value:'missing';})()")
        ok = isinstance(v, str) and '#join=' + gid in v and 'name=Weekend%20Hikers' in v
        note(ok, f'{theme}: sheet shows invite link with id+name', str(v)[-80:])
        shot(f'ginv-sheet-{theme}.png')
        # native share absent in headless -> button hidden, no throw
        v = js("!document.getElementById('ginvShare')")
        note(v, f'{theme}: native-share button hidden when unsupported', str(v))
        # copy -> toast confirmation
        js("document.getElementById('ginvCopy').click()"); time.sleep(0.8)
        v = js("document.getElementById('toastHost').textContent")
        note('Link copied' in str(v), f'{theme}: copy shows confirmation toast', str(v)[:60])
        errs('share sheet')
        js("try{HUB.ui.closeSheet()}catch(e){}")

        # --- member (non-admin) also sees invite button ---
        js(f"(()=>{{const g=HUB.store.state.cgroups.find(x=>x.name==='PUBG Squad'); if(!g.members.includes('QA')) g.members.push('QA'); HUB.store.save(); HUB.cgroups.openClub(g.id);}})()")
        time.sleep(1.0)
        v = js("!!document.getElementById('cgInviteBtn')")
        note(v, f'{theme}: member sees invite button', str(v))

        if not full:
            shot(f'ginv-member-{theme}.png')
            return

        # --- draft group: hint instead of link ---
        # setSub('clubs') resets any open detail view (openClub=null) -> discovery list
        js("HUB.views.groups.setSub('clubs')"); time.sleep(1.0)
        js("document.getElementById('cgNew').click()"); time.sleep(0.8)
        js("document.getElementById('cgName').value='Invite Draft Test';")
        js("document.getElementById('cgSave').click()"); time.sleep(1.0)
        v = js("!!document.getElementById('cgInviteBtn')")
        note(v, f'{theme}: draft group shows invite button (admin)', str(v))
        js("document.getElementById('cgInviteBtn').click()"); time.sleep(0.8)
        v = js("document.getElementById('toastHost').textContent")
        note('live first' in str(v), f'{theme}: draft tap shows make-live hint', str(v)[-80:])
        errs('draft guardrail')

        # --- deep link, known id, non-member group -> page + emphasized CTA ---
        pgid = js("HUB.store.state.cgroups.find(g=>g.name==='Math Study Group').id")
        nav(BASE + '#join=' + pgid + '&name=Math%20Study%20Group')
        errs('deep-link boot (known id)')
        v = js("(()=>{const h=document.querySelector('#view-groups .greet'); return h?h.textContent:'nohead';})()")
        note('Math Study Group' in str(v), f'{theme}: deep link opens the group page', str(v)[:40])
        v = js("(()=>{const b=document.getElementById('cgReq'); return b?(b.classList.contains('pulse-hi')?'emphasized':'noemph'):'nobtn';})()")
        note(v == 'emphasized', f'{theme}: join CTA emphasized for non-member', str(v))
        v = js("location.hash")
        note(v in ('', '#'), f'{theme}: hash cleared after handling', repr(v))
        shot(f'ginv-deeplink-{theme}.png')

        # --- deep link, unknown id -> honest landing, no faked membership ---
        nav(BASE + '#join=nosuch123&name=Far%20Away%20Group')
        errs('deep-link boot (unknown id)')
        v = js("document.getElementById('sheetHost').hidden===false && document.getElementById('sheetHost').textContent")
        txt = str(v)
        ok = ("invited" in txt.lower()) and ('Far Away Group' in txt) and ('backend' in txt.lower())
        note(ok, f'{theme}: honest invite landing for unknown group', txt[:90])
        shot(f'ginv-landing-{theme}.png')
        js("document.getElementById('ginvBrowse').click()"); time.sleep(1.0)
        v = js("!document.getElementById('view-groups').hidden")
        note(v, f'{theme}: landing browse button opens groups tab', str(v))

        # --- lazy locale validates new kh ---
        v = js("HUB.i18n.loadLocale('fr').then(ok=>'loaded:'+ok+'|has:'+!!HUB.i18n._dict('fr')['ginv.invite'])")
        note(v == 'loaded:true|has:true', f'{theme}: lazy fr locale validates new kh', str(v))
        errs('final')
    finally:
        proc.terminate()

run('dark', full=True)
run('light', full=False)
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
