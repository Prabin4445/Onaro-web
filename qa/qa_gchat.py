#!/usr/bin/env python3
"""QA: Group chat — boot clean, thread, composer (text/photo/file/link/GIF/meme),
seed content, member gating, notifications, dismissal, lazy locales."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9448
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

PHOTO_JS = """(async()=>{
  const cv=document.createElement('canvas'); cv.width=16; cv.height=16;
  const x=cv.getContext('2d'); x.fillStyle='#C6F135'; x.fillRect(0,0,16,16);
  const blob=await new Promise(r=>cv.toBlob(r,'image/png'));
  const f=new File([blob],'qa-photo.png',{type:'image/png'});
  const inp=document.getElementById('gcPhotoIn');
  const dt=new DataTransfer(); dt.items.add(f); inp.files=dt.files;
  inp.dispatchEvent(new Event('change',{bubbles:true}));
  return 'dispatched';
})()"""
FILE_JS = """(()=>{
  const f=new File(['hello group chat'],'notes.txt',{type:'text/plain'});
  const inp=document.getElementById('gcFileIn');
  const dt=new DataTransfer(); dt.items.add(f); inp.files=dt.files;
  inp.dispatchEvent(new Event('change',{bubbles:true}));
  return 'dispatched';
})()"""

def run(theme):
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-gchat-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(4)
        errs('boot')
        js("try{HUB.store.state.profile.name='QA'; HUB.store.save(); var w=document.getElementById('wlcmHost'); if(w) w.hidden=true;}catch(e){}")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()});")
        time.sleep(0.5)

        note(js("!!(HUB.gchat&&HUB.gchat.open)"), f'{theme}: HUB.gchat module present')

        # seed chats: Math (text+text+image+meme), PUBG (text+text+gif)
        v = js("(()=>{const g=HUB.store.state.cgroups.find(x=>x.name==='Math Study Group');return g?g.chat.map(m=>m.kind).join(','):'nogroup';})()")
        note(v == 'text,text,image,meme', f'{theme}: math seed chat (text/picture/meme)', str(v))
        v = js("(()=>{const g=HUB.store.state.cgroups.find(x=>x.name==='PUBG Squad');return g?g.chat.map(m=>m.kind).join(','):'nogroup';})()")
        note(v == 'text,text,gif', f'{theme}: pubg seed chat (text/gif)', str(v))
        v = js("(()=>{const g=HUB.store.state.cgroups.find(x=>x.name==='PUBG Squad');const m=g.chat.find(x=>x.kind==='text'&&x.text.includes('http'));return m?m.text:'nolink';})()")
        note('https://' in str(v), f'{theme}: seed link message present', str(v)[:40])

        # inject an incoming message to the member group -> notification row
        js("""(()=>{const g=HUB.store.state.cgroups.find(x=>x.name==='Weekend Hikers');
          g.chat.push({id:'qa-in1',from:'Riley Patel',at:Date.now(),kind:'text',text:'Trail at 8?',sample:true});
          HUB.store.save();})()""")
        v = js("(()=>{const n=HUB.notifications; return n.unreadCount();})()")
        note(isinstance(v, (int, float)) and v >= 1, f'{theme}: notification indicator bumps', f'unread={v}')
        js("HUB.notifications.open()"); time.sleep(0.8)
        v = js("!!document.querySelector('[data-nid^=\"cgchat-\"]')")
        note(v, f'{theme}: group-chat notification row renders', str(v))
        shot(f'gchat-notif-{theme}.png')
        js("document.querySelector('[data-nid^=\"cgchat-\"]').click()"); time.sleep(1.0)
        v = js("(()=>{const r=document.getElementById('chatRoot');return !r.hidden && (document.getElementById('gcBubbles')||{}).textContent.includes('Trail at 8?');})()")
        note(v, f'{theme}: tapping notification opens the group chat', str(v))
        errs('notif -> chat')
        shot(f'gchat-thread-{theme}.png')

        # send text
        js("document.getElementById('gcText').value='Hello hikers!';document.getElementById('gcSend').click()")
        time.sleep(0.8)
        v = js("document.getElementById('gcBubbles').textContent.includes('Hello hikers!')")
        note(v, f'{theme}: send text', str(v))
        # send link
        js("document.getElementById('gcText').value='map https://example.com/trail';document.getElementById('gcSend').click()")
        time.sleep(0.8)
        v = js("(()=>{const a=document.querySelector('#gcBubbles a.cblink');return a?a.href:'noanchor';})()")
        note(str(v).startswith('https://example.com'), f'{theme}: link auto-detect renders anchor', str(v)[:50])
        # photo
        js(PHOTO_JS); time.sleep(1.8)
        v = js("(()=>{const i=document.querySelector('#gcBubbles img.gcimg');return i?i.src.slice(0,22):'noimg';})()")
        note(str(v).startswith('data:image/jpeg'), f'{theme}: photo attaches (downscaled JPEG)', str(v)[:30])
        # file
        js(FILE_JS); time.sleep(1.2)
        v = js("(()=>{const b=document.querySelector('#gcBubbles .cbfile');return b?b.textContent:'nofile';})()")
        note('notes.txt' in str(v), f'{theme}: file chip with name', str(v)[:40])
        v = js("(()=>{const a=document.querySelector('#gcBubbles a[download]');return a?a.getAttribute('download'):'nodl';})()")
        note(v == 'notes.txt', f'{theme}: file download link', str(v))
        errs('composer sends')
        # GIF picker
        js("document.getElementById('gcGif').click()"); time.sleep(0.8)
        v = js("document.querySelectorAll('#sheetBox .artcell').length")
        note(v == 5, f'{theme}: GIF sheet grids 5 originals', f'found={v}')
        shot(f'gchat-picker-{theme}.png')
        js("document.querySelector('#sheetBox .artcell').click()"); time.sleep(0.8)
        v = js("(()=>{const b=[...document.querySelectorAll('#gcBubbles .gcbadge')].map(x=>x.textContent);return b.join(',');})()")
        note('GIF' in str(v), f'{theme}: GIF sends as image message', str(v))
        # meme picker
        js("document.getElementById('gcMeme').click()"); time.sleep(0.8)
        v = js("document.querySelectorAll('#sheetBox .artcell').length")
        note(v == 5, f'{theme}: meme sheet grids 5 originals', f'found={v}')
        js("document.querySelector('#sheetBox .artcell').click()"); time.sleep(0.8)
        v = js("(()=>{const b=[...document.querySelectorAll('#gcBubbles .gcbadge')].map(x=>x.textContent);return b.join(',');})()")
        note('MEME' in str(v), f'{theme}: meme sends as image message', str(v))
        errs('art pickers')
        # tap image -> full view sheet
        js("document.querySelector('#gcBubbles img.gcimg').click()"); time.sleep(0.8)
        v = js("(()=>{const s=document.getElementById('sheetHost');return !s.hidden && !!document.querySelector('#sheetBox img');})()")
        note(v, f'{theme}: tap image opens full view', str(v))
        js("HUB.ui.closeSheet()"); time.sleep(0.4)
        # dismissal: X, backdrop, Escape
        js("document.getElementById('gcClose').click()"); time.sleep(0.5)
        v = js("document.getElementById('chatRoot').hidden")
        note(v is True, f'{theme}: X closes chat', str(v))
        js("(()=>{const g=HUB.store.state.cgroups.find(x=>x.name==='Weekend Hikers');HUB.gchat.open(g.id);})()"); time.sleep(0.8)
        js("document.getElementById('chatRoot').click()"); time.sleep(0.5)
        v = js("document.getElementById('chatRoot').hidden")
        note(v is True, f'{theme}: backdrop tap closes chat', str(v))
        js("(()=>{const g=HUB.store.state.cgroups.find(x=>x.name==='Weekend Hikers');HUB.gchat.open(g.id);})()"); time.sleep(0.8)
        js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))"); time.sleep(0.5)
        v = js("document.getElementById('chatRoot').hidden")
        note(v is True, f'{theme}: Escape closes chat', str(v))
        errs('dismissal')
        # group page entry: member sees chat button
        js("(()=>{const g=HUB.store.state.cgroups.find(x=>x.name==='Weekend Hikers');HUB.cgroups.openClub(g.id);})()"); time.sleep(1.0)
        v = js("(()=>{const b=document.getElementById('cgChatBtn');return b?b.textContent:'nobtn';})()")
        note('Group chat' in str(v), f'{theme}: member group page has chat button', str(v)[:30])
        shot(f'gchat-grouppage-{theme}.png')
        js("document.getElementById('cgChatBtn').click()"); time.sleep(0.8)
        v = js("!document.getElementById('chatRoot').hidden")
        note(v is True, f'{theme}: chat button opens thread', str(v))
        js("HUB.gchat.close()")
        # non-member: no chat button, join UI instead
        js("(()=>{const g=HUB.store.state.cgroups.find(x=>x.name==='PUBG Squad');HUB.cgroups.openClub(g.id);})()"); time.sleep(1.0)
        v = js("!document.getElementById('cgChatBtn') && !!document.getElementById('cgReq')")
        note(v is True, f'{theme}: non-member sees join request, no chat', str(v))
        errs('entry gating')
        # lazy locale validates new kh (no silent fallback)
        v = js("HUB.i18n.loadLocale('de').then(ok=>'loaded:'+ok+'|has:'+!!HUB.i18n._dict('de')['gc.openChat'])")
        note(v == 'loaded:true|has:true', f'{theme}: lazy de locale validates kh', str(v))
        v = js("HUB.i18n.t('gc.openChat')")
        note(v == 'Group chat', f'{theme}: gc key falls back to English (not raw key)', str(v))
        js("HUB.i18n.setLang('en')")
        errs('final')
    finally:
        proc.terminate()

run('dark')
run('light')
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
