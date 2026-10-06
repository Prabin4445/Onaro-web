#!/usr/bin/env python3
"""Calculator QA round 10: 3D clay header chips + DEG overflow fix.

PraBin's iPhone: the Calculator card header row overflowed the card (DEG pill
cut off at the right edge). Fix: icon-only 38px clay chips (ADV, view toggle,
sound, settings) + a compact clay DEG/RAD pill; 3D clay PNG icons (calc-title,
calc-adv, calc-keypad, calc-snd-on, calc-snd-off, calc-set) replace the emoji.

Fresh profiles, 390x844 + 320px narrow, dark+light, zero console errors.
"""
import json, subprocess, time, urllib.request, os, base64, shutil

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9488
PROF = '/tmp/hubqa-calchead'
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []

def note(ok, label, detail=''):
    checks.append((ok, label)); print(('PASS' if ok else 'FAIL'), label, detail)

import websocket
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

HDR_JS = """(function(){
  const card=document.getElementById('calcRoot'), cr=card.getBoundingClientRect();
  const btns=['calcAdvBtn','calcViewBtn','calcSetBtn','calcModeBtn'];
  const out={card:{l:cr.left,r:cr.right},chips:{},vw:document.documentElement.clientWidth,
             docW:document.documentElement.scrollWidth};
  for(const id of btns){
    const el=document.getElementById(id); if(!el){out.chips[id]={missing:true};continue;}
    const r=el.getBoundingClientRect();
    out.chips[id]={l:Math.round(r.left),r:Math.round(r.right),
      inside: r.left>=cr.left-1 && r.right<=cr.right+1};
  }
  const top=document.querySelector('.calc-top');
  if(top){const tr=top.getBoundingClientRect(); out.top={l:Math.round(tr.left),r:Math.round(tr.right),
    inside: tr.left>=cr.left-1 && tr.right<=cr.right+1};}
  return out;
})()"""

def run(theme, w, h):
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', f'--window-size={w},{h}',
        f'--user-data-dir={PROF}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        c.send('Emulation.setDeviceMetricsOverride', {'width': w, 'height': h, 'deviceScaleFactor': 2, 'mobile': True})
        def js(expr):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
                if r and 'exceptionDetails' in r:
                    ed = r['exceptionDetails']
                    return 'THREW:' + str(ed.get('exception', {}).get('description', ed.get('text', '')))[:160]
                res = (r or {}).get('result', {}); return res.get('value')
            except Exception as e: return 'JSERR:' + str(e)[:120]
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'zero console errors @ {label} [{theme} {w}px]', json.dumps(v)[:200] if v else '')

        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
           "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        js("var p=HUB.store.state.profile; p.name='PraBin'; p.campus='Downtown'; p.audience='community';"
           "HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') + ";"
           "HUB.store.save(); HUB.applyTheme(); try{HUB.ui.closeSheet();}catch(e){} HUB.showTab('daily');")
        time.sleep(2)
        errs('load')

        # scroll the calc card into view so rects are real
        js("document.getElementById('calcRoot').scrollIntoView({block:'start'})"); time.sleep(0.6)

        hdr = js(HDR_JS)
        tag = f'{theme} {w}px'
        note(hdr['docW'] <= hdr['vw'], f'no page horizontal overflow [{tag}]',
             f"docW={hdr['docW']} vw={hdr['vw']}")
        note(hdr.get('top', {}).get('inside'), f'header row inside card [{tag}]', json.dumps(hdr.get('top')))
        allin = all(v.get('inside') for v in hdr['chips'].values() if not v.get('missing'))
        note(allin, f'all 4 header chips inside card [{tag}]',
             json.dumps({k: [v['l'], v['r']] for k, v in hdr['chips'].items()}))

        # 3D clay icons present, loaded, no emoji fallback
        for bid, iname in [('calcAdvBtn', 'calc-adv'), ('calcViewBtn', 'chart-emoji'),
                           ('calcSetBtn', 'calc-set')]:
            if iname == 'chart-emoji':
                note(js("document.querySelector('#calcViewBtn .calc-emoji')!==null"),
                     f'view btn shows chart glyph (policy-blocked clay graph fallback) [{tag}]')
            else:
                src = js(f"(function(){{const i=document.querySelector('#{bid} img');"
                          f"return i?i.currentSrc+'|'+(i.complete&&i.naturalWidth>0):'noimg';}})()")
                note(isinstance(src, str) and iname in src and src.lower().endswith('|true'),
                     f'{iname} clay icon loaded [{tag}]', str(src)[:90])
        note(js("document.querySelector('.calc-tico img')!==null"),
             f'title clay calculator icon present [{tag}]')
        note(js("document.querySelectorAll('#calcRoot .ico-fb').length") == 0,
             f'no icon emoji-fallback spans (all PNGs loaded) [{tag}]')

        # ADV toggle still works: bank flips on/off
        before = js("HUB.calc._adv.advBank()")
        js("document.getElementById('calcAdvBtn').click()"); time.sleep(0.5)
        after = js("HUB.calc._adv.advBank()")
        note(before != after, f'ADV toggles bank [{tag}]', f'{before}->{after}')
        note(js("document.getElementById('calcAdvBtn').classList.contains('on')") == after,
             f'ADV clay chip .on state tracks bank [{tag}]')
        js("document.getElementById('calcAdvBtn').click()"); time.sleep(0.5)

        # view toggle: keypad -> graph -> keypad, icon swaps each way
        js("document.getElementById('calcViewBtn').click()"); time.sleep(1)
        note(js("!document.getElementById('calcGraph').hidden"), f'graph view opens [{tag}]')
        gsrc = js("(function(){const i=document.querySelector('#calcViewBtn img');"
                  "return i?i.currentSrc:'noimg';})()")
        note(isinstance(gsrc, str) and 'calc-keypad' in gsrc, f'view btn shows clay keypad in graph mode [{tag}]')
        hdr2 = js(HDR_JS)
        note(all(v.get('inside') for v in hdr2['chips'].values() if not v.get('missing')),
             f'chips still inside card in graph mode [{tag}]')
        js("document.getElementById('calcViewBtn').click()"); time.sleep(1)
        note(js("document.getElementById('calcGraph').hidden"), f'back to keypad mode [{tag}]')

        # sound toggle REMOVED 2026-09-29 on PraBin's order (only ringtone +
        # notification sounds remain): the chip must be gone from the header
        note(js("document.getElementById('calcSndBtn')===null"),
             f'sound chip removed from header [{tag}]')
        note(js("typeof HUB.calc._sndStats==='undefined'"),
             f'calc sound API removed [{tag}]')

        # settings opens the setup sheet
        js("document.getElementById('calcSetBtn').click()"); time.sleep(0.8)
        note(js("document.querySelector('.sheet:not([hidden])')!==null||document.querySelector('.sheethost:not([hidden])')!==null"),
             f'settings opens a sheet [{tag}]')
        js("try{HUB.ui.closeSheet();}catch(e){}"); time.sleep(0.5)

        # DEG/RAD toggle: label flips, pill stays inside the card
        lbl0 = js("document.getElementById('calcModeBtn').textContent.trim()")
        js("document.getElementById('calcModeBtn').click()"); time.sleep(0.5)
        lbl1 = js("document.getElementById('calcModeBtn').textContent.trim()")
        note(lbl0 != lbl1 and lbl1 in ('DEG', 'RAD'), f'DEG/RAD label toggles [{tag}]', f'{lbl0}->{lbl1}')
        hdr3 = js(HDR_JS)
        note(hdr3['chips']['calcModeBtn'].get('inside'), f'DEG/RAD pill inside card after toggle [{tag}]',
             json.dumps(hdr3['chips']['calcModeBtn']))
        errs('flow')
        shot(f'calchead-{theme}-{w}')
    finally:
        proc.terminate()

for th in ['dark', 'light']:
    run(th, 390, 844)
run('dark', 320, 568)
run('light', 320, 568)

ok = sum(1 for o, _ in checks if o); tot = len(checks)
print(f'\n==== {ok}/{tot} checks passed ====')
fails = [l for o, l in checks if not o]
if fails:
    print('FAILURES:'); [print(' -', l) for l in fails]
    raise SystemExit(1)
