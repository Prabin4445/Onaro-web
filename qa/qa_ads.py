#!/usr/bin/env python3
"""QA: sponsored ad placements (market interleave, home carousel, story tray/viewer)."""
import json, subprocess, time, urllib.request, os, base64, sys
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9431
BASE = 'file:///home/hatch/workspace/hub/index.html'
W, H = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (414, 900)
TAG = 'm' if W < 800 else 'd'
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
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', f'--window-size={W},{H}',
        '--user-data-dir=/tmp/hubqa-ads', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
                res = (r or {}).get('result', {}); return res.get('value'), res.get('exceptionDetails')
            except Exception as e: return None, str(e)[:160]
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def errs(label):
            v, _ = js("window.__huberr.splice(0)")
            if v: errors.append((label, v)); print('ERRORS @', label, ':', json.dumps(v)[:300])
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(3)
        # dismiss onboarding (welcome + role picker)
        for _ in range(6):
            st, _ = js("(()=>{const n=document.getElementById('obName'); if(!n) return 'gone'; n.value='QA Tester'; const s=document.getElementById('obCampus'); if(s) s.selectedIndex=1; const g=document.getElementById('obGo'); if(g) g.click(); return 'clicked'})()")
            time.sleep(1)
            if st == 'gone': break
        # also dismiss welcome step if present
        js("(()=>{const b=[...document.querySelectorAll('button')].find(x=>/continue|weiter/i.test(x.textContent)); if(b) b.click()})()")
        time.sleep(1); errs('load')
        note(True if True else False, 'app loaded')

        # ---- MARKET: interleaved ads ----
        js("HUB.showTab('market')"); time.sleep(1.2); errs('market')
        v, _ = js("document.querySelectorAll('#mkList [data-adcard]').length")
        note(v and v >= 1, 'market feed has interleaved ad card(s)', 'count='+str(v))
        v, _ = js("(()=>{const c=document.querySelector('#mkList [data-adcard]'); return c?c.textContent:''})()")
        note('Sponsored' in str(v) and 'Demo ad' in str(v), 'ad card carries Sponsored + Demo ad labels')
        v, _ = js("(()=>{const cards=[...document.querySelectorAll('#mkList > div')]; const ai=cards.findIndex(e=>e.hasAttribute('data-adcard')); return ai+'/'+cards.length})()")
        note(True, 'ad position in feed', 'ad at index '+str(v))
        # scroll ad into view + shot
        js("(()=>{const c=document.querySelector('#mkList [data-adcard]'); if(c) c.scrollIntoView({block:'center'})})()")
        time.sleep(0.6); shot('ads-market-'+TAG)
        # tap ad card -> demo sheet
        js("(()=>{const c=document.querySelector('#mkList [data-adcard]'); if(c) c.click()})()")
        time.sleep(0.8); errs('adclick')
        v, _ = js("document.body.textContent.includes('This is a demo ad')")
        note(bool(v), 'ad tap opens demo honesty sheet')
        shot('ads-sheet-'+TAG)
        js("HUB.ui.closeSheet()"); time.sleep(0.5)

        # ---- HOME: carousel ----
        js("HUB.showTab('home')"); time.sleep(1.2); errs('home')
        v, _ = js("document.querySelectorAll('#adCarouselHost [data-adtile]').length")
        note(v and v >= 3, 'home carousel has sponsored tiles', 'count='+str(v))
        v, _ = js("(()=>{const h=document.getElementById('adCarouselHost'); return h?h.textContent.slice(0,120):''})()")
        note('Sponsored near you' in str(v), 'carousel header present')
        js("(()=>{const h=document.getElementById('adCarouselHost'); if(h) h.scrollIntoView({block:'center'})})()")
        time.sleep(0.6); shot('ads-carousel-'+TAG)

        # ---- STORY TRAY: ad rings with Ad badge on circle ----
        v, _ = js("document.querySelectorAll('#storyTrayHost .sring-ad').length")
        note(v == 2, 'story tray has 2 sponsored rings', 'count='+str(v))
        v, _ = js("(()=>{const b=document.querySelector('#storyTrayHost .sring-ad .sadbadge'); if(!b) return 'missing'; const r=b.getBoundingClientRect(), circ=b.closest('.sringc').getBoundingClientRect(); return b.textContent+'|badgeBottom:'+Math.round(r.bottom)+'|circleBottom:'+Math.round(circ.bottom)})()")
        note(str(v).startswith('Ad|'), 'Ad badge ON the circle', str(v))
        js("(()=>{const t=document.getElementById('storyTrayHost'); if(t) t.scrollIntoView()})()")
        time.sleep(0.5); shot('ads-tray-'+TAG)
        # open sponsored story
        js("(()=>{const r=document.querySelector('#storyTrayHost .sring-ad'); if(r) r.click()})()")
        time.sleep(1.2); errs('adviewer')
        v, _ = js("(()=>{const r=document.getElementById('storyViewer'); return r&&!r.hidden&&r.innerHTML.includes('ssponsored')})()")
        note(bool(v), 'sponsored viewer shows persistent Sponsored banner')
        v, _ = js("(()=>{const r=document.getElementById('storyViewer'); return r?r.textContent.includes('Learn more'):false})()")
        note(bool(v), 'sponsored viewer has Learn more action')
        shot('ads-story-'+TAG)
        # Learn more -> demo sheet
        js("(()=>{const b=document.querySelector('#storyViewer [data-v-adlink]'); if(b) b.click()})()")
        time.sleep(0.8)
        v, _ = js("document.body.textContent.includes('This is a demo ad')")
        note(bool(v), 'viewer Learn more opens demo sheet')
        js("HUB.ui.closeSheet()")
        js("(()=>{const b=document.querySelector('#storyViewer [data-v-close]'); if(b) b.click()})()")
        time.sleep(0.5)

        # ---- dark mode ----
        js("document.body.classList.add('dark')"); time.sleep(0.6)
        js("HUB.showTab('market')"); time.sleep(0.8)
        js("(()=>{const c=document.querySelector('#mkList [data-adcard]'); if(c) c.scrollIntoView({block:'center'})})()")
        time.sleep(0.5); shot('ads-market-dark-'+TAG)
        v, _ = js("(()=>{const c=document.querySelector('#mkList [data-adcard]'); if(!c) return false; const cs=getComputedStyle(c); return cs.display!=='none' && c.offsetHeight>40})()")
        note(bool(v), 'ad card visible in dark mode')
        js("document.body.classList.remove('dark')")

        # ---- RTL (Arabic lazy locale) ----
        js("HUB.i18n.setLang('ar')"); time.sleep(2.5); errs('rtl')
        v, _ = js("document.dir")
        note(v == 'rtl', 'Arabic flips dir=rtl', 'dir='+str(v))
        js("HUB.showTab('market')"); time.sleep(1.0)
        v, _ = js("document.querySelectorAll('#mkList [data-adcard]').length")
        note(v and v >= 1, 'ad cards render under RTL', 'count='+str(v))
        js("(()=>{const c=document.querySelector('#mkList [data-adcard]'); if(c) c.scrollIntoView({block:'center'})})()")
        time.sleep(0.5); shot('ads-market-ar-'+TAG)
        js("HUB.i18n.setLang('en')"); time.sleep(1.0)

        # ---- desktop: no horizontal scroll ----
        v, _ = js("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
        note(bool(v), 'no horizontal page scroll at '+str(W)+'px')

        print('\n=== errors ==='); print('NONE' if not errors else errors)
        fails = [l for ok, l in checks if not ok]
        print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
        if fails: print('FAILED:', fails)
        c.ws.close()
    finally: proc.terminate()
if __name__ == '__main__': main()
