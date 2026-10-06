#!/usr/bin/env python3
"""QA: Marketplace real-commerce redesign (2026-09-22 plan section 9).
Fresh profile per theme; ZERO uncaught console errors; 390x844 dark+light.
Covers: grid (square media, price-first, 2-line title, area·distance meta,
neutral badges, counts chips, demo banner, circular FAB), filters/search/
radius, float-overlap at top/bottom scroll, detail (carousel+counter, price/
title/specs/seller/similar/sticky CTA), lightbox (pinch/Escape), post flow
+ validation, no horizontal overflow, lazy-locale kh."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9471
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors, checks = [], []  # noqa: F841
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

def run(theme):
    shutil.rmtree(f'/tmp/hubqa-mkred-{theme}', ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=390,844',
        f'--user-data-dir=/tmp/hubqa-mkred-{theme}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        # True 390x844 mobile emulation (this Chrome build ignores --window-size)
        c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
        def js(expr):
            # Single evaluation only: NEVER retry. An expression that returns
            # undefined (e.g. el.click()) would otherwise be re-executed,
            # double-firing side effects like publish.
            r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
            return (r or {}).get('result', {}).get('value')
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name), 'wb').write(base64.b64decode(r['data']))
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'{theme}: {label} zero errors', json.dumps(v)[:200] if v else '')
        def nox(label):
            sw = js("document.documentElement.scrollWidth"); iw = js("innerWidth")
            note(sw <= iw + 1, f'{theme}: {label} no horizontal overflow', f'scrollWidth={sw} innerWidth={iw}')

        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(4)
        errs('boot')
        js(f"try{{HUB.store.state.profile.name='QA';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}}catch(e){{}}")
        js(f"document.body.classList.toggle('dark', {str(theme=='dark').lower()}); HUB.showTab('market');")
        time.sleep(1.5)
        errs('market render')

        # ---- grid: real-commerce card grammar ----
        n = js("document.querySelectorAll('#mkList .mktile').length")
        note(n == 6, f'{theme}: 6 seed tiles rendered', f'found={n}')
        v = js("getComputedStyle(document.querySelector('.mktile-media')).aspectRatio")
        note(v == '1 / 1', f'{theme}: tile media is square (1/1)', str(v))
        v = js("Array.from(document.querySelectorAll('#mkList .mktile .mkbadge')).map(b=>b.textContent)")
        note(isinstance(v, list) and len(v) == 6 and 'Sell' in v and 'Borrow' in v,
             f'{theme}: neutral badges use i18n labels', str(v))
        v = js("document.querySelectorAll('#mkList .mktile .badge.b-SELL, #mkList .mktile .badge.b-BUY, #mkList .mktile .badge.b-SWAP, #mkList .mktile .badge.b-BORROW, #mkList .mktile .badge.b-FREE').length")
        note(v == 0, f'{theme}: zero pastel b-TYPE badges in market', f'found={v}')
        # NOTE: all 6 seeds have photos; placeholder glyph is checked after
        # publishing the photo-less QA listing (see post flow below).
        v = js("getComputedStyle(document.querySelector('.mktile-body h3')).webkitLineClamp")
        note(v == '2', f'{theme}: title is 2-line clamp', str(v))
        v = js("Array.from(document.querySelectorAll('#mkList .mktile .meta')).every(m=>m.textContent.split('·').length===2)")
        note(v, f'{theme}: meta is single area·distance line', '')
        v = js("document.querySelector('.mktile-media .mkbadge-volt') ? document.querySelector('.mktile-media .mkbadge-volt').textContent : 'none'")
        note(v == 'Sell', f'{theme}: SELL badge gets volt variant', str(v))
        v = js("!!document.querySelector('.mkdemonote') && document.querySelector('.mkdemonote').textContent")
        note('Sample listings' in str(v), f'{theme}: honest demo banner above grid', str(v)[:50])
        # chips: text-only + counts, active volt
        v = js("document.querySelector('#view-market .chips').textContent.replace(/\\s+/g,' ')")
        note('All 6' in str(v) and 'Sell 2' in str(v) and 'Free 2' in str(v),
             f'{theme}: chips text-only with counts', str(v)[:80])
        v = js("document.querySelectorAll('#view-market .chips svg').length")
        note(v == 0, f'{theme}: no clay icons in filter chips', f'found={v}')
        v = js("getComputedStyle(document.querySelector('#view-market .chip.on')).backgroundColor")
        note(v == 'rgb(198, 241, 53)', f'{theme}: active chip is volt fill', str(v))
        # FAB: circular, no inline pill override
        v = js("(()=>{const b=document.getElementById('mkPostBtn');const cs=getComputedStyle(b);return [b.getAttribute('style'),b.textContent.trim(),b.offsetWidth,b.offsetHeight,cs.position,cs.bottom];})()")
        note(v[0] is None and v[1] == '+' and v[2] == 56 and v[3] == 56 and v[4] == 'fixed' and v[5] == '152px',
             f'{theme}: + Post is a restrained circular FAB (no pill override)', str(v))
        v = js("getComputedStyle(document.getElementById('view-market')).paddingBottom")
        note(str(v).startswith('210px'), f'{theme}: view has 210px bottom clearance', str(v))
        nox('market grid')
        shot(f'market-new-grid-{theme}.png')

        # ---- filters / search / radius ----
        js("Array.from(document.querySelectorAll('#view-market .chip')).find(p=>p.dataset.f==='SELL').click()")
        time.sleep(1.0)
        v = js("document.querySelectorAll('#mkList .mktile').length")
        note(v == 2, f'{theme}: SELL chip narrows to 2', f'found={v}')
        js("Array.from(document.querySelectorAll('#view-market .chip')).find(p=>p.dataset.f==='ALL').click()")
        time.sleep(1.0)
        js("(()=>{const s=document.getElementById('mkSearch'); s.value='bike'; s.dispatchEvent(new Event('input',{bubbles:true}));})()")
        time.sleep(1.2)
        v = js("document.querySelectorAll('#mkList .mktile').length")
        note(v == 1, f'{theme}: search narrows to 1 tile', f'found={v}')
        js("(()=>{const s=document.getElementById('mkSearch'); s.value=''; s.dispatchEvent(new Event('input',{bubbles:true}));})()")
        time.sleep(1.0)
        js("document.querySelector('#mkRadius button[data-r=\"1\"]').click()")
        time.sleep(1.0)
        v = js("[document.querySelectorAll('#mkList .mktile').length, document.getElementById('mkScopePill').textContent]")
        note(v[0] < 6 and v[1] == 'Within 1 mi · sorted by distance', f'{theme}: radius 1mi narrows + scope pill text', str(v))
        js("document.querySelector('#mkRadius button[data-r=\"20\"]').click()")
        time.sleep(1.0)
        errs('filters/search/radius')

        # ---- float overlap at top / bottom scroll ----
        js("window.scrollTo(0,0)"); time.sleep(0.6)
        v = js("(()=>{const f=document.getElementById('mkPostBtn').getBoundingClientRect(),t0=document.querySelector('#mkList .mktile').getBoundingClientRect();return f.top>t0.bottom;})()")
        note(v, f'{theme}: top scroll — FAB clears first row', str(v))
        js("window.scrollTo(0,document.body.scrollHeight)"); time.sleep(0.8)
        shot(f'market-new-grid-bottom-{theme}.png')
        v = js("(()=>{const f=document.getElementById('mkPostBtn').getBoundingClientRect(),a=document.getElementById('askPill').getBoundingClientRect(),ts=Array.from(document.querySelectorAll('#mkList .mktile'));const last=ts[ts.length-1].getBoundingClientRect();return [f.top>last.bottom, a.top>last.bottom, f.left>a.right||f.right<a.left];})()")
        note(v[0] and v[1], f'{theme}: bottom scroll — last row clears FAB + Ask pill', str(v))
        note(v[2], f'{theme}: FAB and Ask pill do not collide (<=360px safe)', str(v))
        js("window.scrollTo(0,document.body.scrollHeight/2)"); time.sleep(0.5)
        shot(f'market-new-grid-mid-{theme}.png')

        # ---- detail sheet (open the 2-photo bike listing specifically) ----
        js("window.scrollTo(0,0)"); time.sleep(0.4)
        js("(()=>{const l=HUB.store.state.listings.find(x=>x.title.includes('bike'));document.querySelector('#mkList [data-listing=\"'+l.id+'\"]').click();})()")
        time.sleep(1.2)
        v = js("document.getElementById('sheetHost').hidden===false")
        note(v, f'{theme}: detail sheet opens', str(v))
        v = js("[getComputedStyle(document.querySelector('.mkd-price')).fontSize, getComputedStyle(document.querySelector('.mkd-title')).fontSize]")
        note(v[0] == '22px' and v[1] == '17px', f'{theme}: price 22px + title 17px hierarchy', str(v))
        v = js("Array.from(document.querySelectorAll('.mkspecs .mkspec .k')).map(e=>e.textContent)")
        note('Condition' not in v and 'Distance' in v and len(v) == 3, f'{theme}: specs grid (category/posted/distance, no condition on seeds)', str(v))
        v = js("document.querySelector('.mkseller').textContent.replace(/\\s+/g,' ')")
        note('listings' in str(v), f'{theme}: seller card shows real listing count', str(v)[:60])
        v = js("getComputedStyle(document.querySelector('.mkcta')).position")
        note(v == 'sticky', f'{theme}: sticky CTA bar present', str(v))
        v = js("document.querySelector('.mkcta .btn').textContent")
        note(v == 'Message seller', f'{theme}: sticky CTA is Message seller', str(v))
        v = js("document.querySelector('.mksim') ? document.querySelectorAll('.mksim .mksim-card').length : -1")
        note(v >= 1, f'{theme}: "You may also like" row', f'cards={v}')
        v = js("document.querySelector('.mksim') ? document.querySelector('.mksim').previousElementSibling.textContent : ''")
        note('You may also like' in str(v), f'{theme}: similar heading copy', str(v)[:40])
        v = js("[document.getElementById('mkPhotoCount').textContent, getComputedStyle(document.querySelector('.mkphoto-media')).height]")
        note(v[0] == '1 / 2' and v[1] == '260px', f'{theme}: photo counter badge + 260px media', str(v))
        v = js("document.querySelectorAll('#mkPhotoFlow .gmem').length")
        note(v == 0, f'{theme}: photo zoom emoji purged', f'found={v}')
        nox('detail sheet')
        shot(f'market-new-detail-{theme}.png')

        # ---- carousel swipe updates counter ----
        js("(()=>{const f=document.getElementById('mkPhotoFlow'); f.scrollLeft=f.scrollWidth;})()")
        time.sleep(0.8)
        v = js("document.getElementById('mkPhotoCount').textContent")
        note(v == '2 / 2', f'{theme}: swipe updates counter to 2/2', str(v))

        # ---- lightbox: open, pinch, Escape ----
        js("(()=>{const cd=document.querySelector('#mkPhotoFlow .gcard');const r=cd.getBoundingClientRect();const x=r.left+r.width/2,y=r.top+r.height/2;cd.dispatchEvent(new PointerEvent('pointerdown',{pointerId:7,clientX:x,clientY:y,bubbles:true}));cd.dispatchEvent(new MouseEvent('click',{clientX:x,clientY:y,bubbles:true}));})()")
        time.sleep(0.8)
        v = js("!!document.querySelector('.mkzoom')")
        note(v, f'{theme}: tap opens lightbox', str(v))
        shot(f'market-new-lightbox-{theme}.png')
        v = js(PINCH)
        note('scale(' in str(v) and 'scale(1)' not in str(v), f'{theme}: pinch zooms', str(v)[:40])
        c.send('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
        time.sleep(0.5)
        v = js("!document.querySelector('.mkzoom')")
        note(v, f'{theme}: Escape dismisses lightbox', str(v))
        errs('detail/lightbox')

        # ---- post flow ----
        js("HUB.showTab('market')"); time.sleep(1.0)
        js("document.getElementById('mkPostBtn').click()"); time.sleep(1.0)
        v = js("document.getElementById('sheetHost').hidden===false && !!document.getElementById('mkPhotoInput')")
        note(v, f'{theme}: + Post opens composer', str(v))
        v = js("document.querySelectorAll('#mkTypeChips svg').length")
        note(v == 0, f'{theme}: post type chips text-only', f'found={v}')
        v = js("document.querySelector('label[for=\"mkPhotoInput\"]').textContent")
        note(v == 'Add photos', f'{theme}: de-emojied add-photos label', str(v))
        js("document.getElementById('mkPublish').click()"); time.sleep(0.4)
        v = js("document.querySelector('#toastHost .toast') ? document.querySelector('#toastHost .toast').textContent : ''")
        note('Please add a title' in str(v), f'{theme}: publish validation toast', str(v)[:40])
        js("document.querySelector('#toastHost').innerHTML=''")
        js("(()=>{document.getElementById('mkTitle').value='QA Redesign Chair';document.querySelector('#mkTypeChips .chip').click();})()")
        time.sleep(0.3)
        js("document.getElementById('mkPublish').click()"); time.sleep(1.2)
        v = js("[document.querySelectorAll('#mkList .mktile').length, document.querySelector('#toastHost .toast') ? document.querySelector('#toastHost .toast').textContent : '']")
        note(v[0] == 7 and 'Listing posted' in str(v[1]) and '🎉' not in str(v[1]),
             f'{theme}: publish adds listing + de-emojied toast', str(v))
        v = js("(()=>{const t0=document.querySelector('#mkList .mktile');const b=t0.querySelector('.mkbadge');return b?b.textContent+'|'+b.className:'none';})()")
        note(str(v).startswith('Sell|') and 'mkbadge-volt' in str(v), f'{theme}: newest tile has volt SELL badge', str(v))
        v = js("(()=>{const t0=document.querySelector('#mkList .mktile');return t0.querySelector('.mktile-ico svg')?'svg':'missing';})()")
        note(v == 'svg', f'{theme}: photo-less tile uses neutral glyph (no clay icon)', str(v))
        shot(f'market-new-post-{theme}.png')
        errs('post flow')

        # ---- lazy locale kh: new keys load under 'de' (read individually; the
        # dict is async-loaded, so allow it to settle) ----
        js("HUB.i18n.setLang('de')"); time.sleep(3.0)
        v = [js("HUB.i18n._dict('de')['market.demoNote']"),
             js("HUB.i18n._dict('de')['market.d.similar']"),
             js("HUB.i18n._dict('de')['market.d.listings']"),
             js("HUB.i18n._dict('de')['market.postShort']")]
        note(isinstance(v, list) and v[0] == 'Sample listings — post yours to start selling' and v[1] == 'You may also like' and v[2] == '{n} listings' and v[3] == '+',
             f'{theme}: lazy de locale loads new keys (kh 60v565 ok)', str(v))
        js("HUB.i18n.setLang('en')"); time.sleep(1.5)
        errs('locale switch')
        errs('final')
    finally:
        proc.terminate()

run('dark')
run('light')
fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
print('FAILURES:', fails if fails else 'none')
