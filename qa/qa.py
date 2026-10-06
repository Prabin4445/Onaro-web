#!/usr/bin/env python3
"""HUB headless-Chromium QA: console errors + screenshots per tab and key flows."""
import json, subprocess, time, urllib.request, os, sys
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
os.makedirs(QA, exist_ok=True)
CHROME = '/opt/meta-chromium/chrome'
PORT = 9326
BASE = 'file:///home/hatch/workspace/hub/index.html'

errors, logs = [], []

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl)
        self.id = 0
    def send(self, method, params=None, wait=True):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        if not wait: return None
        self.ws.settimeout(None)  # blocking recv; CDP always answers
        try:
            deadline = time.time() + 25
            while time.time() < deadline:
                msg = json.loads(self.ws.recv())
                if msg.get('id') == self.id:
                    return msg.get('result')
            raise TimeoutError(method)
        finally:
            pass

def new_target():
    with urllib.request.urlopen(f'http://localhost:{PORT}/json/list') as r:
        for t in json.load(r):
            if t['type'] == 'page' and 'devtools' not in t['url']:
                return t
    raise RuntimeError('no page target')

def port_open():
    import socket
    s = socket.socket(); s.settimeout(1)
    try: s.connect(('localhost', PORT)); return True
    except OSError: return False

def main():
    global proc
    if port_open():
        proc = None  # reuse already-running chrome
    else:
        proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
            f'--remote-debugging-port={PORT}', '--window-size=414,900',
            '--user-data-dir=/tmp/hubqa-prof', '--hide-scrollbars', BASE])
        time.sleep(2.5)
    tgt = new_target()
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')

    def js(expr, await_=False):
        r = c.send('Runtime.evaluate', {'expression': expr, 'awaitPromise': await_, 'returnByValue': True}, wait=True)
        res = (r or {}).get('result', {})
        return res.get('value'), res.get('exceptionDetails')

    def shot(name):
        r = c.send('Page.captureScreenshot', {'format': 'png'})
        data = r['data']
        import base64
        p = os.path.join(QA, name + '.png')
        open(p, 'wb').write(base64.b64decode(data))
        print('shot:', p)

    def console_errors():
        v, _ = js("(()=>{const e=[];window.__huberr=window.__huberr||[];return window.__huberr.length})()")
        return v

    # install error hooks ASAP
    js("window.__huberr=[];window.addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
       "window.addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+(e.reason&&e.reason.message||e.reason)));"
       "document.title")

    time.sleep(3)  # let onboarding finish
    # dismiss onboarding (fresh profile) so tabs are visible; verify it took
    for _ in range(3):
        st, _ = js("(()=>{const n=document.getElementById('obName'); if(!n) return 'gone'; n.value='QA Tester'; const c=document.getElementById('obCampus'); c.selectedIndex=1; document.getElementById('obGo').click(); return 'clicked'})()")
        time.sleep(1.0)
        if st == 'gone': break
    time.sleep(1.0)
    e0, _ = js("window.__huberr.slice()")
    if e0: errors.append(('load', e0))

    def tab(name, snap):
        v, ex = js(f"HUB.showTab('{name}')")
        if ex: errors.append((name, str(ex)[:200]))
        time.sleep(1.2)
        errs, _ = js("window.__huberr.splice(0)")
        if errs: errors.append((name, errs))
        shot(snap)

    # 1. all six tabs
    for t in ['home', 'discover', 'market', 'work', 'groups', 'me']:
        tab(t, f'tab-{t}')

    # 2. overlays
    for label, expr, snap in [
        ('search', 'HUB.search.open()', 'flow-search'),
        ('notifications', 'HUB.notifications.open()', 'flow-notifications'),
        ('pulse', 'HUB.pulse.open()', 'flow-pulse'),
        ('create', 'HUB.create.open()', 'flow-create'),
    ]:
        js(expr); time.sleep(1.0)
        errs, _ = js("window.__huberr.splice(0)")
        if errs: errors.append((label, errs))
        shot(snap)
        v, ex = js("(()=>{try{document.querySelectorAll('.chatroot:not(#chatRoot)').forEach(x=>x.remove());HUB.ui.closeSheet();if(HUB.chat)HUB.chat.close();return 'ok'}catch(e){return 'ERR:'+e.message}})()")
        if v != 'ok': errors.append((label + '-cleanup', v))
        time.sleep(0.5)

    # 3. market post sheet + detail sheet + report
    js("HUB.showTab('market')"); time.sleep(1.0)
    js("document.getElementById('mkPostBtn').click()"); time.sleep(0.8)
    shot('flow-market-post'); js("HUB.ui.closeSheet()")
    js("document.querySelector('#view-market .card.tight, #view-market .item') && document.querySelector('#view-market [data-mk-detail]')")
    # open first listing detail via its card click
    v, _ = js("(()=>{const el=document.querySelector('#view-market .lcard, #view-market [data-listing]'); if(el){el.click();return true;} return false})()")
    time.sleep(0.8)
    shot('flow-market-detail')
    v, _ = js("(()=>{const b=document.getElementById('mkReport'); if(b){b.click();return true;} return false})()")
    time.sleep(0.8)
    shot('flow-report')
    js("HUB.ui.closeSheet()")

    # 4. chat
    js("HUB.chat.openList()"); time.sleep(1.0)
    shot('flow-chat'); js("HUB.chat.close()")

    # 5. dark mode on ME
    js("HUB.showTab('me')"); time.sleep(1.0)
    js("document.getElementById('darkToggle').click()"); time.sleep(1.0)
    shot('tab-me-dark')
    js("document.getElementById('darkToggle').click()"); time.sleep(0.5)

    # 6. trust moderation queue
    js("HUB.trust.moderationQueue()"); time.sleep(0.8)
    shot('flow-modqueue'); js("HUB.ui.closeSheet()")

    # 7. discover map (Leaflet) — wait for tiles
    js("HUB.showTab('discover')"); time.sleep(4)
    shot('flow-discover-map')
    errs, _ = js("window.__huberr.splice(0)")
    if errs: errors.append(('final', errs))

    print('\n=== console/page errors ===')
    if not errors: print('NONE')
    for k, e in errors: print(k, ':', e)
    c.ws.close()

if __name__ == '__main__':
    main()
