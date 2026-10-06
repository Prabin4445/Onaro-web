#!/usr/bin/env python3
"""Professors overlay iOS-offset fix QA (2026-09-23).

PraBin's iPhone: the full-page Professors overlay was shifted LEFT (~20-40px):
header title clipped at left edge, avatars touching the left edge, "Top rated"
pill clipped, dark gap on the right. Root cause: .chatroot is a fixed flex host
using justify-content:center — iOS Safari mis-centers the flex item (same bug
family as the .sheethost sheet shift). Fix: .profroot marker class on the root,
host becomes display:block, panel absolutely bottom-docked with left:50% +
translateX(-50%) and sheetUpC entrance (translateX(-50%) in every keyframe).

Asserts at 390x844 and 320x568, dark+light, en + real German (setLang):
- root carries profroot; panel left >= -1 and right <= innerWidth (no left
  clip, no right gap)
- header title, first avatar, first sort chip all fully inside (rect.left >= 8)
- no sampled element overflows right edge; documentElement.scrollWidth <= vw
- panel is full-page (top==0, height==viewport)
- zero console errors; screenshots at both widths
"""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9497
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

SEED_JS = """(function(){
HUB.store.state.profile.name='Prabin';
HUB.store.state.profile.campus='Dallas College';
HUB.store.state.profile.verified=true;
HUB.store.save();
if(HUB.professors&&HUB.professors._reset) HUB.professors._reset();
return true;})()"""

GEO_JS = """(function(){
const r=document.querySelector('.profroot .chatpanel').getBoundingClientRect();
const vw=window.innerWidth;
function rect(sel){const e=document.querySelector(sel);if(!e)return null;const b=e.getBoundingClientRect();return [Math.round(b.left),Math.round(b.right),Math.round(b.top),Math.round(b.bottom)];}
const els={};
['.prof-topbar-t','.prof-ava','.prof-tools .chip','.prof-hero','.prof-swrap .input','#profAdd','.prof-card .grow b'].forEach(s=>{els[s]=rect(s);});
let maxRight=0;
document.querySelectorAll('.profroot .chatpanel *').forEach(e=>{try{const b=e.getBoundingClientRect();if(b.width>0&&b.right>maxRight)maxRight=b.right;}catch(_){}});
return {panel:[Math.round(r.left),Math.round(r.right),Math.round(r.top),Math.round(r.bottom)],vw:vw,
  els:els,maxRight:Math.round(maxRight),
  docSW:document.documentElement.scrollWidth,
  rootCls:(document.getElementById('hubProfRoot')||{className:''}).className};
})()"""

def run_case(width, height, theme, lang):
    prof = f'/tmp/hubqa-profoff-{width}-{theme}-{lang}'
    shutil.rmtree(prof, ignore_errors=True); os.makedirs(prof, exist_ok=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        f'--window-size={width},{height}',
        f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tag = f'{width}x{height}-{theme}-{lang}'
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as rr:
                    ts = json.load(rr)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        c.send('Emulation.setDeviceMetricsOverride', {'width': width, 'height': height,
               'deviceScaleFactor': 2, 'mobile': True})
        def js(expr):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
                if r and 'exceptionDetails' in r:
                    ed = r['exceptionDetails']
                    return 'THREW:' + str(ed.get('exception', {}).get('description', ed.get('text', '')))[:160]
                return (r or {}).get('result', {}).get('value')
            except Exception as e: return 'JSERR:' + str(e)[:120]
        def js_wait_ready(timeout=20):
            dl = time.time() + timeout
            while time.time() < dl:
                try:
                    r = c.send('Runtime.evaluate', {'expression': 'document.readyState', 'returnByValue': True})
                    if (r or {}).get('result', {}).get('value') == 'complete': return True
                except Exception: pass
                time.sleep(0.5)
            return False
        def arm_errs():
            js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
               "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def errs(label):
            v = js("window.__huberr.splice(0)")
            note(not v, f'zero console errors @ {label} [{tag}]', json.dumps(v)[:200] if v else '')

        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        arm_errs()
        js("HUB.store.state.prefs.dark=" + ('true' if theme == 'dark' else 'false') + ";HUB.store.save();HUB.applyTheme();")
        js(SEED_JS); time.sleep(0.5)
        if lang == 'de':
            # setLang fires the locale fetch; poll until the dict actually swaps
            # (one-shot identity right after await is racy — fetch may lag)
            okde = False
            for _ in range(16):
                if js("HUB.i18n._dict('de')!==HUB.i18n._dict('en')") is True:
                    okde = True; break
                js("HUB.i18n.setLang('de')"); time.sleep(0.5)
            note(okde, f'real German locale loaded (identity) [{tag}]')

        # open the full-page overlay
        js("HUB.showTab('home')"); time.sleep(1.0)
        js("HUB.professors.open(null)"); time.sleep(1.2)
        note(js("!!document.getElementById('hubProfRoot')") is True, f'overlay opens [{tag}]')

        g = js(GEO_JS)
        note(isinstance(g, dict) and 'profroot' in (g.get('rootCls') or ''), f'root carries profroot class [{tag}]',
             repr(g.get('rootCls')) if isinstance(g, dict) else repr(g))
        if isinstance(g, dict):
            vw = g['vw']
            pl, pr, pt, pb = g['panel']
            note(pl >= -1, f'panel not clipped left (left={pl}) [{tag}]')
            note(pr <= vw + 1, f'panel no right gap (right={pr} vw={vw}) [{tag}]')
            note(pt <= 1 and pb >= height - 2, f'panel full-page height [{tag}]',
                 f'top={pt} bottom={pb} h={height}')
            if lang == 'de':
                det = js("(function(){const e=document.querySelector('.prof-topbar-t');return e&&e.textContent.trim();})()")
                note(det == 'Professoren', f'German overlay copy rendered [{tag}]', repr(det))
            e = g['els']
            t = e.get('.prof-topbar-t')
            note(t and t[0] >= 8, f'header title fully inside (left={t[0] if t else "?"}) [{tag}]')
            a = e.get('.prof-ava')
            note(a and a[0] >= 8, f'first avatar fully inside (left={a[0] if a else "?"}) [{tag}]')
            ch = e.get('.prof-tools .chip')
            note(ch and ch[0] >= 8, f'first sort chip fully inside (left={ch[0] if ch else "?"}) [{tag}]')
            note(g['maxRight'] <= vw + 1, f'nothing overflows right edge (maxRight={g["maxRight"]} vw={vw}) [{tag}]')
            note(g['docSW'] <= vw, f'documentElement.scrollWidth <= viewport [{tag}]', f'sw={g["docSW"]}')
            # panel symmetric inside viewport: left margin ~= right margin
            note(abs(pl - (vw - pr)) <= 4, f'panel horizontally centered (l={pl} r-gap={vw-pr}) [{tag}]')
        else:
            note(False, f'geometry probe returned [{tag}]', repr(g)[:120])

        shot(f'profoff-{width}-{theme}-{lang}')
        errs(f'overlay-{tag}')

        # detail page uses the same root/mount — spot-check it too
        js("(function(){const c0=document.querySelector('.prof-card');if(c0)c0.click();})()"); time.sleep(1.2)
        g2 = js(GEO_JS)
        if isinstance(g2, dict):
            pl2, pr2 = g2['panel'][0], g2['panel'][1]
            note(pl2 >= -1 and pr2 <= g2['vw'] + 1, f'detail page pinned (l={pl2} r={pr2} vw={g2["vw"]}) [{tag}]')
            note(g2['docSW'] <= g2['vw'], f'detail no h-overflow [{tag}]')
        else:
            note(False, f'detail geometry probe [{tag}]', repr(g2)[:120])
        errs(f'detail-{tag}')

        js("HUB.professors.close()"); time.sleep(0.4)
        note(js("!document.getElementById('hubProfRoot')") is True, f'close removes overlay [{tag}]')
    finally:
        proc.terminate()

for w, h in [(390, 844), (320, 568)]:
    for theme in ['dark', 'light']:
        for lang in ['en', 'de']:
            run_case(w, h, theme, lang)

fails = [l for ok, l in checks if not ok]
print(f'\n{len(checks)-len(fails)}/{len(checks)} checks passed')
if fails: print('FAILURES:'); [print(' -', l) for l in fails]
raise SystemExit(1 if fails else 0)
