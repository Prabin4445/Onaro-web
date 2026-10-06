#!/usr/bin/env python3
"""QA: Marketplace photo upgrade — 4-photo upload w/ downscale, grid tiles,
detail water-flow photo carousel, pinch-zoom lightbox. i18n lazy-locale kh check."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9461
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

MAKE_FILES = """(async()=>{
  const files=[];
  for(let k=0;k<5;k++){
    const c=document.createElement('canvas'); c.width=2000; c.height=1500;
    const g=c.getContext('2d'); g.fillStyle=['#e33','#3e6','#36e','#ee3','#e3e'][k];
    g.fillRect(0,0,2000,1500); g.fillStyle='#fff'; g.font='120px sans-serif';
    g.fillText('QA-PHOTO-'+(k+1),300,750);
    const blob=await new Promise(r=>c.toBlob(r,'image/png'));
    files.push(new File([blob],'qa'+k+'.png',{type:'image/png'}));
  }
  const dt=new DataTransfer(); files.forEach(f=>dt.items.add(f));
  const inp=document.getElementById('mkPhotoInput'); inp.files=dt.files;
  inp.dispatchEvent(new Event('change',{bubbles:true}));
  return files.length;
})()"""

PINCH = """(()=>{
  const img=document.querySelector('.mkzoom-stage img'); if(!img) return 'no-img';
  const r=img.getBoundingClientRect(), cx=r.left+r.width/2, cy=r.top+r.height/2;
  img.dispatchEvent(new PointerEvent('pointerdown',{pointerId:1,clientX:cx-40,clientY:cy,bubbles:true}));
  img.dispatchEvent(new PointerEvent('pointerdown',{pointerId:2,clientX:cx+40,clientY:cy,bubbles:true}));
  img.dispatchEvent(new PointerEvent('pointermove',{pointerId:1,clientX:cx-90,clientY:cy,bubbles:true}));
  img.dispatchEvent(new PointerEvent('pointermove',{pointerId:2,clientX:cx+90,clientY:cy,bubbles:true}));
  img.dispatchEvent(new PointerEvent('pointerup',{pointerId:1,clientX:cx-90,clientY:cy,bubbles:true}));
  img.dispatchEvent(new PointerEvent('pointerup',{pointerId:2,clientX:cx+90,clientY:cy,bubbles:true}));
  return img.style.transform;
})()"""

def run(theme, full):
    shutil.rmtree(f'/tmp/hubqa-mkphoto-{theme}', ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        f'--user-data-dir=/tmp/hubqa-mkphoto-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        v = js("document.body.classList.contains('dark')")
        note(v, f'{theme}: fresh install boots dark by default', str(v))
        js("try{HUB.store.state.profile.name='QA';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        time.sleep(0.5)

        # lazy locale kh check: new keys must load under 'de' (proves kh matches)
        js("HUB.i18n.setLang('de')"); time.sleep(2.5)
        v = js("HUB.i18n._dict('de')['market.p.photosCount']")
        note(v == '{n} of 4', f'{theme}: lazy de locale loads new keys (kh ok)', str(v))
        js("HUB.i18n.setLang('en')"); time.sleep(1.5)
        errs('locale switch')

        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.showTab('market');")
        time.sleep(1.5)
        errs('market render')

        v = js("!!document.querySelector('#mkList.mkgrid')")
        note(v, f'{theme}: #mkList is a 2-col grid', str(v))
        n = js("document.querySelectorAll('#mkList .mktile').length")
        note(n == 6, f'{theme}: 6 seed tiles rendered', f'found={n}')
        v = js("document.querySelector('#mkList .mktile img') ? document.querySelector('#mkList .mktile img').src : 'none'")
        note('market/photos/' in str(v), f'{theme}: tile shows bundled seed photo', str(v)[:60])
        v = js("document.querySelector('#mkList').textContent")
        txt = str(v)
        note('$15' in txt and 'Desk lamp' in txt and 'SELL' in txt, f'{theme}: tile has price+title+type badge', txt[:70])
        shot(f'market-grid-{theme}.png')

        # filters
        js("Array.from(document.querySelectorAll('#view-market .chip')).find(p=>p.dataset.f==='SELL').click()")
        time.sleep(1.0)
        v = js("Array.from(document.querySelectorAll('#mkList .mktile .badge.b-SELL, #mkList .mktile .badge.b-BUY, #mkList .mktile .badge.b-SWAP, #mkList .mktile .badge.b-BORROW, #mkList .mktile .badge.b-FREE')).map(b=>b.textContent)")
        note(isinstance(v, list) and len(v) > 0 and all(x == 'SELL' for x in v), f'{theme}: SELL filter narrows tiles', str(v))
        js("Array.from(document.querySelectorAll('#view-market .chip')).find(p=>p.dataset.f==='ALL').click()")
        time.sleep(1.0)
        v = js("document.querySelectorAll('#mkList .mktile').length")
        note(v == 6, f'{theme}: All filter restores 6 tiles', f'found={v}')

        # search
        js("(()=>{const s=document.getElementById('mkSearch'); s.value='bike'; s.dispatchEvent(new Event('input',{bubbles:true}));})()")
        time.sleep(1.2)
        v = js("document.querySelectorAll('#mkList .mktile').length")
        note(v == 1, f'{theme}: search narrows to 1 tile', f'found={v}')
        js("(()=>{const s=document.getElementById('mkSearch'); s.value=''; s.dispatchEvent(new Event('input',{bubbles:true}));})()")
        time.sleep(1.0)

        if not full:
            errs('final'); return

        # ---- post flow: 5 files -> max-4 rejection, downscale, counter ----
        js("document.getElementById('mkPostBtn').click()"); time.sleep(1.0)
        v = js("document.getElementById('sheetHost').hidden===false && !!document.getElementById('mkPhotoInput')")
        note(v, f'{theme}: + Post opens composer with photo input', str(v))
        v = js(MAKE_FILES)
        note(v == 5, f'{theme}: 5 test photos fed to picker', str(v))
        time.sleep(1.0)  # toast fires immediately; downscale needs longer
        v = js("document.querySelector('#toastHost .toast') ? document.querySelector('#toastHost .toast').textContent : ''")
        note('Only 4 photos' in str(v), f'{theme}: honest max-4 error shown', str(v)[:60])
        time.sleep(2.5)  # FileReader + canvas downscale
        v = js("document.querySelectorAll('#mkPhotoPrev .ph-thumb').length")
        note(v == 4, f'{theme}: 5th photo rejected, 4 thumbs kept', f'found={v}')
        v = js("document.getElementById('mkPhotoPrev').textContent")
        note('4 of 4' in str(v), f'{theme}: counter shows "4 of 4"', str(v)[-20:])
        v = js("(()=>{const im=document.querySelector('#mkPhotoPrev .ph-thumb img'); return im.naturalWidth+'x'+im.naturalHeight+'|'+im.src.slice(0,22);})()")
        note(str(v).startswith('1000x750|data:image/jpeg'), f'{theme}: 2000px photo downscaled to ~1000px JPEG', str(v)[:40])
        js("document.querySelector('#mkPhotoPrev .ph-x').click()"); time.sleep(0.5)
        v = js("document.getElementById('mkPhotoPrev').textContent")
        note('3 of 4' in str(v) and js("document.querySelectorAll('#mkPhotoPrev .ph-thumb').length") == 3,
             f'{theme}: remove button drops to "3 of 4"', str(v)[-20:])
        shot(f'market-post-{theme}.png')

        # publish with 3 photos (type chip tap is required by the form)
        js("document.querySelector('#mkTypeChips .chip').click()")
        js("(()=>{document.getElementById('mkTitle').value='QA Test Chair';document.getElementById('mkDesc').value='QA listing with photos';document.getElementById('mkPhone').value='555-0000';})()")
        time.sleep(0.3)
        js("document.getElementById('mkPublish').click()"); time.sleep(1.2)
        errs('publish')
        v = js("document.querySelectorAll('#mkList .mktile').length")
        note(v == 7, f'{theme}: new listing appears in grid', f'found={v}')
        v = js("document.querySelector('#mkList .mktile img').src.slice(0,22)")
        note(str(v) == 'data:image/jpeg;base64', f'{theme}: newest tile shows uploaded photo', str(v))

        # ---- detail: water-flow carousel ----
        js("document.querySelector('#mkList .mktile').click()"); time.sleep(1.2)
        v = js("document.querySelectorAll('#mkPhotoFlow .gcard').length")
        note(v == 3, f'{theme}: detail carousel has all 3 photos', f'found={v}')
        v = js("document.querySelector('#mkPhotoFlow .gcard .gcard-meta').textContent")
        note('1 / 3' in str(v), f'{theme}: photo counter "1 / 3"', str(v))
        v = js("document.querySelector('#mkPhotoFlow .gcard').style.transform")
        note('rotateY' in str(v), f'{theme}: cover-flow tilt on photo cards', str(v)[:50])
        shot(f'market-detail-{theme}.png')

        # ---- lightbox: open, pinch zoom, dismiss ----
        js("(()=>{const cd=document.querySelector('#mkPhotoFlow .gcard');const r=cd.getBoundingClientRect();const x=r.left+r.width/2,y=r.top+r.height/2;cd.dispatchEvent(new PointerEvent('pointerdown',{pointerId:7,clientX:x,clientY:y,bubbles:true}));cd.dispatchEvent(new MouseEvent('click',{clientX:x,clientY:y,bubbles:true}));})()")
        time.sleep(0.8)
        v = js("!!document.querySelector('.mkzoom') && getComputedStyle(document.querySelector('.mkzoom')).display!=='none'")
        note(v, f'{theme}: tap opens fullscreen lightbox', str(v))
        shot(f'market-lightbox-{theme}.png')
        v = js(PINCH)
        note('scale(' in str(v) and 'scale(1)' not in str(v), f'{theme}: synthetic pinch zooms image', str(v)[:50])
        js("document.querySelector('.mkzoom-stage').dispatchEvent(new WheelEvent('wheel',{deltaY:-100,bubbles:true,cancelable:true}))")
        time.sleep(0.3)
        v = js("document.querySelector('.mkzoom-stage img').style.transform")
        note('scale(' in str(v), f'{theme}: wheel zoom works (desktop)', str(v)[:50])
        c.send('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
        time.sleep(0.5)
        v = js("!document.querySelector('.mkzoom')")
        note(v, f'{theme}: Escape dismisses lightbox', str(v))
        errs('lightbox')

        # comment flow still works
        js("(()=>{document.getElementById('mkCommentInput').value='QA comment here';document.getElementById('mkCommentSend').click();})()")
        time.sleep(1.0)
        v = js("document.getElementById('mkComments').textContent")
        note('QA comment here' in str(v), f'{theme}: comment posts in detail', str(v)[:60])

        # delete own listing (two-tap confirm)
        js("(()=>{document.getElementById('mkDelete').click();document.getElementById('mkDelete').click();})()")
        time.sleep(1.0)
        v = js("document.getElementById('sheetHost').hidden===true && document.querySelectorAll('#mkList .mktile').length")
        note(v == 6, f'{theme}: delete removes own listing, grid back to 6', f'found={v}')
        errs('final')
    finally:
        proc.terminate()

run('dark', full=True)
run('light', full=False)
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
