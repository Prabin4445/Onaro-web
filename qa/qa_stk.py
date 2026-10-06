#!/usr/bin/env python3
"""HUB QA: sticker/GIF/emoji picker (track: original art pack + picker UI).
Fresh profile per theme. file:// load, 390x844, dark + light."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9431
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

def run(theme):
    port = 9431 if theme == 'dark' else 9432
    prof = f'/tmp/hubqa-stk-{theme}'
    shutil.rmtree(prof, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={port}', '--remote-allow-origins=*', '--window-size=390,844',
        f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{port}/json/list', timeout=3) as r:
                    ts = json.load(r)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        def js(expr):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
                res = (r or {}).get('result', {}); return res.get('value'), res.get('exceptionDetails')
            except Exception as e: return None, str(e)[:160]
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def errs(label):
            v, _ = js("window.__huberr.splice(0)")
            note(not v, f'{theme}: {label} zero errors', json.dumps(v)[:200] if v else '')
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(3)
        js("try{HUB.store.state.profile.name='QA';HUB.store.state.profile.campus='QA Campus';HUB.store.save();"
           "var w=document.getElementById('wlcmHost');if(w)w.hidden=true;HUB.ui.closeSheet();}catch(e){}")
        time.sleep(1); errs('load')
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()});"); time.sleep(0.5)

        # --- group chat: open picker via the composer emoji button ---
        js("(()=>{const g=HUB.store.state.cgroups.find(x=>x.name==='Weekend Hikers');HUB.gchat.open(g.id);})()")
        time.sleep(1.0); errs('group-open')
        note(js("!!document.getElementById('gcEmoji')")[0], f'{theme}: group composer has emoji button')
        js("document.getElementById('gcEmoji').click()"); time.sleep(0.8); errs('picker-open')
        note(js("!!document.querySelector('#sheetBox .stktabs')")[0], f'{theme}: picker sheet with 3 tabs opens')
        note(js("document.querySelectorAll('#sheetBox .stktab').length")[0] == 3, f'{theme}: exactly 3 tabs')
        tabs = js("Array.from(document.querySelectorAll('#sheetBox .stktab')).map(b=>b.textContent.trim()).join('|')")[0]
        note(tabs == 'Emoji|GIFs|Stickers', f'{theme}: tab labels', tabs)
        n_stk = js("document.querySelectorAll('#sheetBox .stkgrid .artcell').length")[0]
        note(n_stk == 24, f'{theme}: stickers tab shows 24 art cells', str(n_stk))
        # all sticker images actually loaded (scroll grid first: cells are loading=lazy)
        js("(()=>{const g=document.querySelector('#sheetBox .stkgrid');if(g)g.scrollTop=g.scrollHeight;return 1})()"); time.sleep(1.2)
        loaded = js("(()=>{const ims=[...document.querySelectorAll('#sheetBox .stkgrid img')];return ims.filter(i=>i.naturalWidth>0).length+'/'+ims.length})()")[0]
        note(loaded == '24/24', f'{theme}: all 24 sticker images decode', loaded)
        shot(f'stk-picker-{theme}')
        # send a sticker (first cell)
        before = js("HUB.store.state.cgroups.find(x=>x.name==='Weekend Hikers').chat.length")[0]
        js("document.querySelector('#sheetBox .stkgrid .artcell').click()"); time.sleep(1.0); errs('sticker-send')
        after = js("HUB.store.state.cgroups.find(x=>x.name==='Weekend Hikers').chat.length")[0]
        lastk = js("(()=>{const ch=HUB.store.state.cgroups.find(x=>x.name==='Weekend Hikers').chat;return ch[ch.length-1].kind})()")[0]
        note(after == before + 1 and lastk == 'sticker', f'{theme}: sticker message sent (kind=sticker)', f'{before}->{after} {lastk}')
        note(js("!!document.querySelector('#gcBubbles img.stkimg')")[0], f'{theme}: sticker renders inline in group thread')
        shot(f'stk-sticker-sent-{theme}')
        # recents row populated
        js("document.getElementById('gcEmoji').click()"); time.sleep(0.8)
        nrec = js("document.querySelectorAll('#sheetBox .stkrec img').length")[0]
        if not (nrec and nrec >= 1):
            print('   DIAG recents state:', js("JSON.stringify(HUB.store.state.stickerRecents)")[0])
            print('   DIAG recWrap len:', js("document.getElementById('stkRecWrap').innerHTML.length")[0])
            print('   DIAG sheet open:', js("!document.getElementById('sheetHost').hidden")[0])
            print('   DIAG stkTab:', js("document.querySelector('#sheetBox .stktab.on').textContent")[0])
        note(nrec and nrec >= 1, f'{theme}: recents row populated after send', str(nrec))
        # search filters
        js("(()=>{const s=document.getElementById('stkSearch');s.value='rocket';s.dispatchEvent(new Event('input',{bubbles:true}));})()"); time.sleep(0.6)
        nq = js("document.querySelectorAll('#sheetBox .stkgrid .artcell, #sheetBox #stkGridWrap .artcell').length")[0]
        note(nq == 1, f'{theme}: search "rocket" filters to 1 sticker', str(nq))
        js("(()=>{const s=document.getElementById('stkSearch');s.value='';s.dispatchEvent(new Event('input',{bubbles:true}));})()"); time.sleep(0.6)
        # GIFs tab: 12 gifs + 5 memes merged
        js("document.querySelector('#sheetBox [data-stktab=\"gifs\"]').click()"); time.sleep(0.6)
        ng = js("document.querySelectorAll('#sheetBox .artgrid .artcell').length")[0]
        note(ng == 17, f'{theme}: GIFs tab shows 12 gifs + 5 memes', str(ng))
        note(js("(()=>[...document.querySelectorAll('#sheetBox .artgrid .artcell img')].some(i=>i.src.includes('gif-clap.png')))()")[0],
             f'{theme}: new gif-clap.png present in GIFs tab')
        # Emoji tab: insert emoji into composer
        js("document.querySelector('#sheetBox [data-stktab=\"emoji\"]').click()"); time.sleep(0.6)
        nem = js("document.querySelectorAll('#sheetBox .stkcell.emj').length")[0]
        note(nem >= 40, f'{theme}: emoji tab shows unicode set', str(nem))
        js("document.querySelector('#sheetBox .stkcell.emj').click()"); time.sleep(0.5)
        note(js("document.getElementById('gcText').value.length>0")[0], f'{theme}: emoji tap inserts into group composer')
        shopen, sherr = js("!document.getElementById('sheetHost').hidden"), None
        if not shopen:
            print('   DIAG sheet closed after emoji; errors:', js("JSON.stringify(window.__huberr.splice(0))")[0])
        note(shopen, f'{theme}: sheet stays open after emoji tap')
        js("HUB.ui.closeSheet()"); time.sleep(0.5)
        # Escape closes picker (group-owned layering)
        js("document.getElementById('gcEmoji').click()"); time.sleep(0.6)
        js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))"); time.sleep(0.5)
        note(js("document.getElementById('sheetHost').hidden")[0], f'{theme}: Escape closes picker sheet')
        errs('group-flow')
        js("HUB.gchat.close()"); time.sleep(0.5)

        # --- 1:1 chat ---
        tid = js("HUB.store.state.threads[0].id")[0]
        js(f"HUB.chat.openThread({json.dumps(tid)})"); time.sleep(1.0); errs('11-open')
        note(js("!!document.getElementById('chEmoji')")[0], f'{theme}: 1:1 composer has emoji button')
        js("document.getElementById('chEmoji').click()"); time.sleep(0.8)
        note(js("!!document.querySelector('#sheetBox .stktabs')")[0], f'{theme}: picker opens from 1:1 chat')
        js("document.querySelector('#sheetBox [data-stktab=\"stickers\"]').click()"); time.sleep(0.5)
        js("document.querySelector('#sheetBox .stkgrid .artcell').click()"); time.sleep(1.5); errs('11-send')
        note(js("!!document.querySelector('#chatBubbles img.stkimg')")[0], f'{theme}: sticker renders in 1:1 thread')
        pv = js("(()=>{const th=HUB.store.state.threads.find(t=>t.id===HUB.store.state.threads[0].id);return th.messages[th.messages.length-1].kind})()")[0]
        note(pv == 'sticker', f'{theme}: 1:1 sticker msg kind persisted', pv)
        # tap-to-zoom viewer
        js("document.querySelector('#chatBubbles img.stkimg').click()"); time.sleep(0.8)
        note(js("!document.getElementById('sheetHost').hidden && !!document.querySelector('#sheetBox img')")[0],
             f'{theme}: tap sticker opens fullscreen viewer')
        js("HUB.ui.closeSheet()"); time.sleep(0.4)
        shot(f'stk-11-{theme}')
        errs('11-flow')
        ok = sum(1 for o, _ in checks[-60:] if o)
    finally:
        proc.terminate()
    return checks

run('dark'); run('light')
p = sum(1 for o, _ in checks if o); f = sum(1 for o, _ in checks if not o)
print(f'\n=== stk QA: {p} pass, {f} fail ===')
if errors: print(errors)
