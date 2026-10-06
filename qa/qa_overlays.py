#!/usr/bin/env python3
"""QA: full-screen overlays all have working close affordances (✕ / back / backdrop / Escape)."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9442
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
        '--user-data-dir=/tmp/hubqa-overlays', '--hide-scrollbars', '--allow-file-access-from-files',
        '--autoplay-policy=no-user-gesture-required', BASE],
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
            open(os.path.join(QA, name), 'wb').write(base64.b64decode(r['data']))
        def click_at(x, y):
            c.send('Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
            c.send('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
        def press_esc():
            c.send('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
            c.send('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
        def click_el(sel):
            v, _ = js("(()=>{const el=document.querySelector('"+sel+"'); if(!el) return 'missing'; const r=el.getBoundingClientRect(); return [r.left+r.width/2, r.top+r.height/2];})()")
            if not v or v == 'missing': return False
            click_at(v[0], v[1]); return True

        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(3); errs('load')
        js("try{var st=JSON.parse(localStorage.getItem('hub_v1')||'null'); if(st){st.profile=st.profile||{}; st.profile.name='QA'; localStorage.setItem('hub_v1',JSON.stringify(st));} var w=document.getElementById('wlcmHost'); if(w) w.hidden=true;}catch(e){}")
        time.sleep(1)

        chat_hidden = "document.getElementById('chatRoot').hidden===true"
        x_ok = """(()=>{const x=document.querySelector('#chatClose'); if(!x) return 'missing';
          const r=x.getBoundingClientRect(); return (r.width>=44&&r.height>=44)?'ok':'bad:'+r.width+'x'+r.height;})()"""

        # ---- 1. Chat list: ✕ present, visible, closes ----
        js("HUB.chat.openList()"); time.sleep(1.0)
        v, _ = js(x_ok); note(v == 'ok', 'chat list has visible 44px ✕', str(v))
        shot('ov-chat-list.png'); errs('chat-list-open')
        ok = click_el('#chatClose'); time.sleep(0.6)
        v, _ = js(chat_hidden); note(ok and v is True, 'chat list ✕ click closes overlay')

        # ---- 2. Chat list: backdrop tap closes ----
        js("HUB.chat.openList()"); time.sleep(0.8)
        click_at(250, 25)  # top strip is backdrop (panel is bottom-anchored, 92% height)
        time.sleep(0.6)
        v, _ = js(chat_hidden); note(v is True, 'chat list backdrop tap closes overlay'); errs('chat-backdrop')

        # ---- 3. Chat list: Escape closes ----
        js("HUB.chat.openList()"); time.sleep(0.8)
        press_esc(); time.sleep(0.6)
        v, _ = js(chat_hidden); note(v is True, 'chat list Escape closes overlay'); errs('chat-esc')

        # ---- 4. Chat thread: back returns to list; list ✕ exits fully ----
        tid, _ = js("(HUB.store.state.threads[0]||{}).id||null")
        if tid:
            js("HUB.chat.openThread("+json.dumps(tid)+")"); time.sleep(1.0)
            v, _ = js("!!document.getElementById('chBack')")
            note(v is True, 'thread has back control')
            shot('ov-chat-thread.png')
            ok = click_el('#chBack'); time.sleep(0.8)
            v, _ = js("!!document.getElementById('chatClose') && !document.getElementById('chBack') && "+chat_hidden.replace('===true','===false'))
            note(ok and v is True, 'thread back returns to chats list')
            # thread Escape -> back to list
            js("HUB.chat.openThread("+json.dumps(tid)+")"); time.sleep(0.8)
            press_esc(); time.sleep(0.8)
            v, _ = js("!!document.getElementById('chatClose') && !document.getElementById('chBack')")
            note(v is True, 'thread Escape returns to list')
            ok = click_el('#chatClose'); time.sleep(0.6)
            v, _ = js(chat_hidden); note(ok and v is True, 'thread path fully exits via list ✕')
            errs('chat-thread')
        else:
            note(False, 'thread tests skipped (no threads)')

        # ---- 5. Search ----
        js("HUB.search.open()"); time.sleep(0.8)
        v, _ = js("!!document.getElementById('hubSearchClose')")
        note(v is True, 'search has ✕')
        shot('ov-search.png')
        ok = click_el('#hubSearchClose'); time.sleep(0.6)
        v, _ = js("!document.getElementById('hubSearchRoot')")
        note(ok and v is True, 'search ✕ removes overlay node'); errs('search')

        # ---- 6. Notifications ----
        js("HUB.notifications.open()"); time.sleep(0.8)
        v, _ = js("!!document.getElementById('hubNotifClose')")
        note(v is True, 'notifications has ✕')
        shot('ov-notif.png')
        ok = click_el('#hubNotifClose'); time.sleep(0.6)
        v, _ = js("!document.getElementById('hubNotifRoot')")
        note(ok and v is True, 'notifications ✕ removes overlay node'); errs('notif')

        # ---- 7. Pulse ----
        js("HUB.pulse.open()"); time.sleep(0.8)
        v, _ = js("!!document.getElementById('hubPulseClose')")
        note(v is True, 'pulse has ✕')
        shot('ov-pulse.png')
        ok = click_el('#hubPulseClose'); time.sleep(0.6)
        v, _ = js("!document.getElementById('hubPulseRoot')")
        note(ok and v is True, 'pulse ✕ removes overlay node'); errs('pulse')

        # ---- 8. Story viewer ----
        sid, _ = js("((HUB.store.state.stories||[])[0]||{}).id||null")
        if sid:
            js("HUB.stories.openSingle(HUB.store.state.stories[0])"); time.sleep(1.0)
            v, _ = js("!!document.querySelector('.sview [data-v-close]')")
            note(v is True, 'story viewer has ✕')
            shot('ov-story.png')
            ok = click_el('.sview [data-v-close]'); time.sleep(0.6)
            v, _ = js("document.getElementById('storyViewer').hidden===true")
            note(ok and v is True, 'story viewer ✕ closes overlay (hidden)'); errs('story')
        else:
            note(False, 'story test skipped (no stories)')

        # ---- 9. Gym drawer ----
        js("HUB.gym.openSetup()"); time.sleep(1.0)
        v, _ = js("(()=>{const x=document.getElementById('gyX'); if(!x) return 'missing'; const r=x.getBoundingClientRect(); return (r.width>=44&&r.height>=44)?'ok':'bad:'+r.width;})()")
        note(v == 'ok', 'gym drawer has 44px ✕', str(v))
        shot('ov-gym.png')
        ok = click_el('#gyX'); time.sleep(0.8)
        v, _ = js("!document.getElementById('gyDrawer') && !document.getElementById('gyBd')")
        note(ok and v is True, 'gym drawer ✕ removes overlay nodes'); errs('gym')

        print('\n%d/%d checks passed, %d error groups' % (sum(1 for ok, _ in checks if ok), len(checks), len(errors)))
    finally:
        proc.terminate()
if __name__ == '__main__':
    main()
