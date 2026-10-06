#!/usr/bin/env python3
"""QA: chat read receipts — sent/delivered/seen ticks (1:1 + job threads),
'Seen by N' in group chat. Both themes, zero console errors."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9471
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

def run(theme):
    shutil.rmtree(f'/tmp/hubqa-ticks-{theme}', ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-ticks-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as r:
                    ts = json.load(r)
                tgt = next(x for x in ts if x['type'] == 'page' and 'devtools' not in x['url']); break
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
        def wait_js(expr, timeout=8):
            for _ in range(int(timeout * 2)):
                if js(expr): return True
                time.sleep(0.5)
            return False
        def as_user(name):
            js(f"HUB.store.state.profile.name={json.dumps(name)};HUB.store.save();")
            time.sleep(0.5)
        def send11(text):
            js(f"(()=>{{var i=document.getElementById('chatText');i.value={json.dumps(text)};document.getElementById('chatSend').click();}})()")
        def sendgc(text):
            js(f"(()=>{{var i=document.getElementById('gcText');i.value={json.dumps(text)};document.getElementById('gcSend').click();}})()")

        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(4)
        errs('boot')
        js("try{HUB.store.state.profile.name='Alex';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()});")
        time.sleep(1.0)

        # ---- 1:1 thread: sent -> delivered -> seen ----
        tid = js("(()=>{HUB.store.add('contacts',{name:'Maya',phone:''});var c=HUB.store.state.contacts[0];"
                 "HUB.store.add('threads',{contactId:c.id,title:'Maya',messages:[],unread:0});"
                 "return HUB.store.state.threads[0].id;})()")
        note(bool(tid), f'{theme}: 1:1 thread created', str(tid)[:10])
        js(f"HUB.chat.openThread({json.dumps(tid)})")
        note(wait_js("!document.getElementById('chatRoot').hidden"), f'{theme}: thread opens')
        note(bool(js("!!(function(){var x=HUB.store.find('threads'," + json.dumps(tid) + ");return x&&x.seenBy&&x.seenBy.Alex;})()")),
             f'{theme}: opening records my seenBy')
        send11('Hey Maya, QA tick test')
        note(wait_js("!!document.querySelector('#chatBubbles .bubble.out .tk-sent')"),
             f'{theme}: sent state shows single check')
        time.sleep(1.6)
        note(bool(js("!!document.querySelector('#chatBubbles .bubble.out .tk-del')"))
             and not js("!!document.querySelector('#chatBubbles .bubble.out .tk-seen')")
             and not js("!!document.querySelector('#chatBubbles .bubble.out .tk-sent')"),
             f'{theme}: delivered state shows gray double check')
        # Maya opens on her identity -> Alex's message becomes seen
        js("HUB.chat.close()"); time.sleep(0.4)
        as_user('Maya')
        js(f"HUB.chat.openThread({json.dumps(tid)})"); time.sleep(0.8)
        note(bool(js("!!(function(){var x=HUB.store.find('threads'," + json.dumps(tid) + ");return x&&x.seenBy&&x.seenBy.Maya;})()")),
             f'{theme}: Maya opening records her seenBy')
        js("HUB.chat.close()"); time.sleep(0.4)
        as_user('Alex')
        js(f"HUB.chat.openThread({json.dumps(tid)})")
        note(wait_js("!!document.querySelector('#chatBubbles .bubble.out .tk-seen')"),
             f'{theme}: seen state shows volt double check')
        shot(f'chat-ticks-{theme}.png')
        js("HUB.chat.close()"); time.sleep(0.4)
        errs('1:1 ticks')

        # ---- job thread: sys seed has no ticks, own msg ticks work ----
        js("HUB.store.add('threads',{id:'job:qa1',title:'\U0001f4bc QA job · Maya',"
           "messages:[{from:'sys',text:'seed line',at:Date.now(),kind:'text'}],unread:0})")
        as_user('Alex')
        js("HUB.chat.openThread('job:qa1')")
        note(wait_js("!!document.querySelector('#chatBubbles .csys')"), f'{theme}: job sys seed line renders')
        note(not js("!!document.querySelector('#chatBubbles .csys .tk')"),
             f'{theme}: job sys seed line is tick-free')
        send11('On my way')
        note(wait_js("!!document.querySelector('#chatBubbles .bubble.out .tk-del')"),
             f'{theme}: job thread message reaches delivered')
        js("HUB.chat.close()"); time.sleep(0.4)
        as_user('Maya'); js("HUB.chat.openThread('job:qa1')"); time.sleep(0.8)
        js("HUB.chat.close()"); time.sleep(0.4)
        as_user('Alex'); js("HUB.chat.openThread('job:qa1')")
        note(wait_js("!!document.querySelector('#chatBubbles .bubble.out .tk-seen')"),
             f'{theme}: job thread message seen after Maya opens')
        js("HUB.chat.close()"); time.sleep(0.4)
        errs('job thread ticks')

        # ---- group chat: 'Seen by N' under latest own message ----
        js("(()=>{HUB.store.state.cgroups=HUB.store.state.cgroups||[];"
           "HUB.store.state.cgroups.unshift({id:'g-qa1',name:'QA Runners',emoji:'\U0001f3c3',mine:true,"
           "members:['Maya'],live:true,chat:[],sample:false,createdAt:Date.now()});HUB.store.save();})()")
        as_user('Alex')
        js("HUB.gchat.open('g-qa1')"); time.sleep(0.8)
        sendgc('Morning run at 6?')
        note(wait_js("!!document.querySelector('#gcBubbles .bubble.out')"),
             f'{theme}: group message sends')
        time.sleep(0.6)
        note(not js("!!document.querySelector('#gcBubbles .seennote')"),
             f'{theme}: no Seen-by note before anyone else opens')
        js("HUB.gchat.close()"); time.sleep(0.4)
        as_user('Maya'); js("HUB.gchat.open('g-qa1')"); time.sleep(0.8)
        js("HUB.gchat.close()"); time.sleep(0.4)
        as_user('Alex'); js("HUB.gchat.open('g-qa1')")
        note(wait_js("(()=>{var e=document.querySelector('#gcBubbles .seennote');return e&&e.textContent.indexOf('Seen by 1')!==-1;})()"),
             f'{theme}: group shows "Seen by 1" under latest own message',
             str(js("document.querySelector('#gcBubbles .seennote')?document.querySelector('#gcBubbles .seennote').textContent:''")))
        shot(f'chat-group-seen-{theme}.png')
        # second own message, not yet seen by Maya: note hides (only latest own msg can carry it)
        sendgc('Bring water')
        note(wait_js("!!document.querySelectorAll('#gcBubbles .bubble.out')[1]"), f'{theme}: second group message sends')
        time.sleep(0.6)
        note(js("document.querySelectorAll('#gcBubbles .seennote').length") == 0,
             f'{theme}: no Seen-by note while latest own message is unseen')
        # Maya opens again -> exactly one note, on the latest own message
        js("HUB.gchat.close()"); time.sleep(0.4)
        as_user('Maya'); js("HUB.gchat.open('g-qa1')"); time.sleep(0.8)
        js("HUB.gchat.close()"); time.sleep(0.4)
        as_user('Alex'); js("HUB.gchat.open('g-qa1')")
        note(wait_js("document.querySelectorAll('#gcBubbles .seennote').length===1"),
             f'{theme}: exactly one Seen-by note after Maya re-opens')
        last_txt = js("(()=>{var es=document.querySelectorAll('#gcBubbles .seennote');return es.length?es[es.length-1].textContent:'';})()")
        note('Seen by 1' in str(last_txt), f'{theme}: note sits on latest own message', str(last_txt))
        js("HUB.gchat.close()"); time.sleep(0.4)
        errs('group seen')

        errs('final')
    finally:
        proc.terminate()

run('dark')
run('light')
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
