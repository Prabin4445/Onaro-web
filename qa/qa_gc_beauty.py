#!/usr/bin/env python3
"""QA: group chat beautification — bubbles, dividers, reply, reactions,
typing, member grid, system msgs, ticks regression. Both themes, zero errors."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9477
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

def seed_group_js():
    return """(()=>{HUB.store.state.cgroups=HUB.store.state.cgroups||[];
var y=new Date(); y.setDate(y.getDate()-1); y.setHours(12,0,0,0);
var now=Date.now();
HUB.store.state.cgroups.unshift({id:'g-qabeauty',name:'QA Runners',emoji:'\U0001F3C3',mine:true,
members:['Maya','Liam','Sofia'],online:['Maya','Liam'],live:true,sample:false,createdAt:now,
chat:[
 {id:'m1',from:'Maya',at:y.getTime(),kind:'text',text:'Hey team! Ready for tomorrow?'},
 {id:'m2',from:'Liam',at:y.getTime()+6e4,kind:'text',text:'Morning! \\U0001f3c3'},
 {id:'m3',from:'me',at:now-3.6e6,kind:'text',text:'Morning run at 6, riverside loop',status:'delivered'},
 {id:'m4',from:'Sofia',at:now-1.8e6,kind:'text',text:'Bringing water for everyone'}
]});
HUB.store.save();return 'seeded';})()"""

def run(theme):
    prof = f'/tmp/hubqa-gc-{theme}'
    shutil.rmtree(prof, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=390,844',
        f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
            open(os.path.join(QA, name), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'{theme}: {label} zero errors', json.dumps(v)[:200] if v else '')
        def wait_js(expr, timeout=8):
            for _ in range(int(timeout * 2)):
                if js(expr): return True
                time.sleep(0.5)
            return False
        def as_user(name):
            js(f"HUB.store.state.profile.name={json.dumps(name)};HUB.store.save()")
            time.sleep(0.5)

        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(4); errs('boot')
        js("try{var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()});HUB.store.state.profile.name='Alex';HUB.store.save();")
        time.sleep(1.0)

        # API surface
        note(bool(js("!!(HUB.groupchat&&HUB.groupchat.openStickerPicker&&HUB.groupchat.simulateTyping&&HUB.groupchat.onTyping&&HUB.groupchat.systemMsg&&HUB.groupchat.setReply&&HUB.groupchat.toggleReact&&HUB.groupchat.openMembers)")),
             f'{theme}: HUB.groupchat hooks exposed')
        note(bool(js("!!(HUB.gchat&&HUB.gchat.open&&HUB.gchat.close)")), f'{theme}: HUB.gchat legacy API intact')

        js(seed_group_js()); time.sleep(0.4)
        js("HUB.gchat.open('g-qabeauty')")
        note(wait_js("!document.getElementById('chatRoot').hidden"), f'{theme}: group chat opens')
        note(bool(js("document.getElementById('chatPanel').classList.contains('gc-panel')")),
             f'{theme}: .gc-panel class on panel')

        # header: avatar stack, name, member count, tappable
        note(bool(js("!!document.getElementById('gcHeadInfo')")), f'{theme}: rich header present')
        note(js("document.querySelectorAll('#gcHeadInfo .gc-stack .gc-ava').length") >= 4,
             f'{theme}: avatar stack renders', str(js("document.querySelectorAll('#gcHeadInfo .gc-stack .gc-ava').length")))
        note(bool(js("!!document.querySelector('#gcHeadInfo .gc-pres')")), f'{theme}: presence dot in stack')
        hdr = js("document.getElementById('gcHeadInfo').textContent") or ''
        note('QA Runners' in hdr and '4' in hdr, f'{theme}: header name + member count', hdr.replace('\n',' ')[:60])

        # date dividers
        divs = js("Array.from(document.querySelectorAll('#gcBubbles .gc-daydiv span')).map(e=>e.textContent)")
        note(isinstance(divs, list) and len(divs) >= 2, f'{theme}: date dividers (>=2)', str(divs))
        note(divs and any('oday' in str(x) for x in divs) and any('esterday' in str(x) for x in divs),
             f'{theme}: Today + Yesterday dividers', str(divs))

        # sender chips + avatars on incoming
        note(bool(js("!!document.querySelector('#gcBubbles .gc-chip')")), f'{theme}: sender name chips')
        note(js("document.querySelectorAll('#gcBubbles .gc-ava').length") >= 2, f'{theme}: member avatars in thread')
        note(bool(js("!!document.querySelector('#gcBubbles .gc-msg .gc-pres')")), f'{theme}: online dot on avatar')

        # send text
        js("(()=>{var i=document.getElementById('gcText');i.value='See you at 6!';document.getElementById('gcSend').click();})()")
        note(wait_js("Array.from(document.querySelectorAll('#gcBubbles .bubble.out')).some(b=>b.textContent.indexOf('See you at 6!')!==-1)"),
             f'{theme}: send text works')
        shot(f'gc-beauty-{theme}.png')

        # ---- reply flow: contextmenu on Sofia's bubble -> Reply ----
        js("""(()=>{var m=document.querySelector('#gcBubbles .gc-msg[data-mid=\"m4\"]');
m.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true}));})()""")
        note(wait_js("!!document.getElementById('gcActReply')"), f'{theme}: long-press/right-click opens actions')
        shot(f'gc-actions-{theme}.png')
        js("document.getElementById('gcActReply').click()")
        note(wait_js("!document.getElementById('gcReplyBar').hidden"), f'{theme}: reply bar appears above composer')
        bar = js("document.getElementById('gcReplyBar').textContent") or ''
        note('Sofia' in bar, f'{theme}: reply bar names quoted sender', bar.replace('\n',' ')[:70])
        js("(()=>{var i=document.getElementById('gcText');i.value='Thanks Sofia!';document.getElementById('gcSend').click();})()")
        note(wait_js("!!document.querySelector('#gcBubbles .gc-quote')"), f'{theme}: sent message carries quote block')
        q = js("document.querySelector('#gcBubbles .gc-quote').textContent") or ''
        note('Sofia' in q and 'water' in q, f'{theme}: quote shows sender + preview', q.replace('\n',' ')[:70])
        shot(f'gc-reply-{theme}.png')

        # ---- reactions: react button -> emoji -> chip -> toggle ----
        js("""(()=>{var b=document.querySelector('#gcBubbles .gc-msg[data-mid=\"m1\"] .gc-reactbtn');b.click();})()""")
        note(wait_js("!!document.querySelector('#sheetBox [data-emo]')"), f'{theme}: react button opens emoji row')
        js("document.querySelector('#sheetBox [data-emo]').click()")
        note(wait_js("!!document.querySelector('#gcBubbles .gc-msg[data-mid=\"m1\"] .gc-react')"),
             f'{theme}: reaction chip renders under bubble')
        n1 = js("document.querySelector('#gcBubbles .gc-msg[data-mid=\"m1\"] .gc-react .n').textContent")
        note(n1 == '1', f'{theme}: reaction count 1', str(n1))
        # another member's reaction via demo API, then toggle mine off
        js("HUB.groupchat.addReactAs(HUB.gchat.findGroup('g-qabeauty'),'m1','❤️','Maya')")
        note(wait_js("document.querySelector('#gcBubbles .gc-msg[data-mid=\"m1\"] .gc-react .n').textContent==='2'"),
             f'{theme}: grouped reaction count 2 (me + Maya)')
        js("document.querySelector('#gcBubbles .gc-msg[data-mid=\"m1\"] .gc-react').click()")
        note(wait_js("document.querySelector('#gcBubbles .gc-msg[data-mid=\"m1\"] .gc-react .n').textContent==='1'"),
             f'{theme}: tapping reaction toggles mine off (back to 1)')
        errs('reactions')

        # ---- typing indicator ----
        js("HUB.groupchat.simulateTyping('Maya',5000)")
        note(wait_js("!!document.getElementById('gcTyping')"), f'{theme}: typing indicator shows')
        tw = js("document.getElementById('gcTyping').textContent") or ''
        note('Maya' in tw and 'typing' in tw, f'{theme}: typing names the member', tw.replace('\n',' ')[:60])
        shot(f'gc-typing-{theme}.png')
        time.sleep(5.6)
        note(not js("!!document.getElementById('gcTyping')"), f'{theme}: typing indicator auto-clears')

        # ---- member grid ----
        js("document.getElementById('gcHeadInfo').click()")
        note(wait_js("!!document.querySelector('#sheetBox .gc-mgrid')"), f'{theme}: member grid sheet opens')
        mems = js("Array.from(document.querySelectorAll('#sheetBox .gc-mem .gc-mname')).map(e=>e.textContent)")
        note(isinstance(mems, list) and len(mems) == 4, f'{theme}: 4 members in grid', str(mems))
        note(bool(js("!!document.querySelector('#sheetBox .gc-role.admin')")), f'{theme}: admin role badge')
        note(bool(js("!!document.querySelector('#sheetBox .gc-mgrid .gc-pres')")), f'{theme}: online dots in grid')
        shot(f'gc-members-{theme}.png')
        # Escape closes the sheet first, NOT the chat (layering)
        c.send('Input.dispatchKeyEvent', {'type': 'keyDown', 'windowsVirtualKeyCode': 27, 'key': 'Escape'})
        time.sleep(0.6)
        note(bool(js("document.getElementById('sheetHost').hidden")) and not js("document.getElementById('chatRoot').hidden"),
             f'{theme}: Escape closes sheet, chat stays open')
        # Escape again closes the chat
        c.send('Input.dispatchKeyEvent', {'type': 'keyDown', 'windowsVirtualKeyCode': 27, 'key': 'Escape'})
        note(wait_js("document.getElementById('chatRoot').hidden"), f'{theme}: second Escape closes chat')
        errs('members+escape')

        # ---- join system message ----
        js("HUB.gchat.open('g-qabeauty')"); time.sleep(0.8)
        js("HUB.groupchat.systemMsg('g-qabeauty','gc.joined',{name:'Ravi'})")
        note(wait_js("!!document.querySelector('#gcBubbles .gc-sys')"), f'{theme}: join system pill renders')
        sy = js("document.querySelector('#gcBubbles .gc-sys').textContent") or ''
        note('Ravi' in sy and 'joined' in sy, f'{theme}: system pill text', sy[:60])

        # ---- ticks regression: Seen by N ----
        js("HUB.gchat.close()"); time.sleep(0.4)
        as_user('Maya'); js("HUB.gchat.open('g-qabeauty')"); time.sleep(0.8)
        js("HUB.gchat.close()"); time.sleep(0.4)
        as_user('Alex'); js("HUB.gchat.open('g-qabeauty')")
        note(wait_js("(()=>{var e=document.querySelector('#gcBubbles .seennote');return e&&e.textContent.indexOf('Seen by 1')!==-1;})()"),
             f'{theme}: Seen by 1 still works')
        # 1:1 thread sanity: no gc polish leaks, ticks intact
        tid = js("(()=>{HUB.store.add('contacts',{name:'Maya',phone:''});var c0=HUB.store.state.contacts[0];"
                 "HUB.store.add('threads',{contactId:c0.id,title:'Maya',messages:[],unread:0});"
                 "return HUB.store.state.threads[0].id;})()")
        js(f"HUB.chat.openThread({json.dumps(tid)})"); time.sleep(0.6)
        note(not js("document.getElementById('chatPanel').classList.contains('gc-panel')"),
             f'{theme}: 1:1 thread has no gc-panel class')
        js(f"(()=>{{var i=document.getElementById('chatText');i.value='Hey Maya';document.getElementById('chatSend').click();}})()")
        note(wait_js("!!document.querySelector('#chatBubbles .bubble.out .tk-sent')"),
             f'{theme}: 1:1 send shows sent tick')
        time.sleep(1.6)
        note(bool(js("!!document.querySelector('#chatBubbles .bubble.out .tk-del')")),
             f'{theme}: 1:1 reaches delivered tick')
        js("HUB.chat.close()"); time.sleep(0.4)
        errs('ticks+11')
        errs('final')
    finally:
        proc.terminate()

run('dark')
run('light')
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
