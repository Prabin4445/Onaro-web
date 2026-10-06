#!/usr/bin/env python3
"""HUB QA: group-chat mega-upgrade INTEGRATION (beauty + stickers + calls + i18n).
Verifies the three tracks coexist: no boot errors, picker/reply/react/typing/
members/call UI all work in one session, lazy locale kh accepted, no overflow.
Dark + light, 390x844 mobile emulation, fresh profiles."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9432
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
    def js(self, expr, await_promise=False):
        try:
            r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': await_promise})
            res = (r or {}).get('result', {})
            return res.get('value'), res.get('exceptionDetails')
        except Exception as e: return None, str(e)[:160]

def targets():
    with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=5) as r:
        return json.load(r)
def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
def hook_err(c):
    c.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
def drain_err(c, label):
    v, _ = c.js("window.__huberr.splice(0)")
    if v: errors.append((label, v)); print('ERRORS @', label, ':', json.dumps(v)[:500])
def wait_js(c, expr, timeout=12):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v, _ = c.js(expr)
        if v: return v
        time.sleep(0.4)
    return None
def esc_key(c):
    c.send('Input.dispatchKeyEvent', {'type': 'rawKeyDown', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
    time.sleep(0.3)
    c.send('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
    time.sleep(0.5)

SEED = """(()=>{const p=HUB.store.state.profile; p.name='QA Int'; p.campus='QA Campus'; HUB.store.save();
const w=document.getElementById('wlcmHost'); if(w) w.remove();
HUB.store.state.cgroups=HUB.store.state.cgroups||[];
var y=new Date(); y.setDate(y.getDate()-1); y.setHours(12,0,0,0); var now=Date.now();
HUB.store.state.cgroups.unshift({id:'g-qa',name:'QA Crew',emoji:'\\U0001FA90',mine:true,
members:['Maya','Liam','Sofia'],online:['Maya'],live:true,sample:false,createdAt:now,
chat:[{id:'m1',from:'Maya',at:y.getTime(),kind:'text',text:'Yesterday thread'},
{id:'m2',from:'me',at:now-3.6e6,kind:'text',text:'Today thread',status:'delivered'},
{id:'m3',from:'Sofia',at:now-1.8e6,kind:'text',text:'Hey all'}]});
HUB.store.save(); return 'seeded';})()"""

def run(theme):
    dark = theme == 'dark'
    prof = f'/tmp/hubqa-gcint-{theme}'
    shutil.rmtree(prof, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=390,844',
        f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                ts = targets()
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable')
        c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True, 'hasTouch': True})
        hook_err(c)
        time.sleep(2.5)
        drain_err(c, 'boot')
        if dark: c.js("document.body.classList.add('dark')")
        else: c.js("document.body.classList.remove('dark')")
        note(bool(c.js("!!(window.HUB&&HUB.store)")[0]), f'{theme}: boot, HUB.store alive')
        note(bool(c.js("!!(HUB.gchat&&HUB.call&&HUB.groupchat&&HUB.groupchat.openStickerPicker&&HUB.groupchat.simulateTyping)")[0]),
             f'{theme}: all three track APIs present')
        c.js(SEED); time.sleep(0.6)
        # --- group chat beauty ---
        c.js("HUB.gchat.open('g-qa')"); time.sleep(1.0)
        note(bool(c.js("!!document.querySelector('#chatPanel.gc-panel')")[0]), f'{theme}: gc-panel beauty class')
        note((c.js("document.querySelectorAll('#gcBubbles .gc-daydiv span').length")[0] or 0) >= 2, f'{theme}: date dividers (>=2)')
        note(bool(c.js("!!document.querySelector('.gc-stack')")[0]), f'{theme}: header avatar stack')
        shot(c, f'gc-int-{theme}')
        drain_err(c, 'chat-open')
        # --- sticker picker ---
        c.js("HUB.groupchat.openStickerPicker()"); time.sleep(0.8)
        note(bool(c.js("!!document.querySelector('#sheetBox [data-stktab]')")[0]), f'{theme}: picker sheet + tabs')
        note((c.js("document.querySelectorAll('#sheetBox [data-stktab]').length")[0] or 0) == 3, f'{theme}: 3 tabs')
        c.js("document.querySelector('#sheetBox [data-stktab=\"stickers\"]').click()"); time.sleep(0.6)
        nstk = c.js("document.querySelectorAll('#stkGridWrap .artcell').length")[0] or 0
        note(nstk >= 20, f'{theme}: stickers tab cells', str(nstk))
        c.js("document.querySelector('#stkGridWrap .artcell').click()"); time.sleep(0.8)
        note(bool(c.js("!!document.querySelector('.bubble img.stkimg')")[0]), f'{theme}: sticker sent + rendered')
        shot(c, f'gc-int-picker-{theme}')
        esc_key(c)
        note(bool(c.js("!!document.querySelector('#chatPanel:not([hidden])')")[0]), f'{theme}: picker Escape -> chat intact')
        drain_err(c, 'picker')
        # --- reply ---
        c.js("""(()=>{const b=document.querySelector('#gcBubbles .gc-msg[data-mid] .bubble'); if(b){b.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true}))} return !!b})()""")
        time.sleep(0.8)
        note(bool(c.js("!!document.getElementById('gcActReply')")[0]), f'{theme}: msg actions sheet')
        c.js("document.getElementById('gcActReply').click()"); time.sleep(0.6)
        note(bool(c.js("!document.getElementById('gcReplyBar').hidden")[0]), f'{theme}: reply bar shown')
        c.js("""(()=>{const ta=document.querySelector('#chatPanel textarea, #chatPanel input[type=text]'); const btn=document.querySelector('#chatPanel [data-send], #chatPanel .sendbtn, #chatPanel button.send'); return 'n/a'})()""")
        # send via composer: set input value + click send
        c.js("""(()=>{const inp=document.getElementById('gcText'); if(inp){inp.value='replying!'; inp.dispatchEvent(new Event('input',{bubbles:true}))}
const s=document.getElementById('gcSend'); if(s) s.click(); return !!s})()""")
        time.sleep(0.8)
        note(bool(c.js("!!document.querySelector('.gc-quote')")[0]), f'{theme}: quote block rendered')
        shot(c, f'gc-int-reply-{theme}')
        drain_err(c, 'reply')
        # --- reactions ---
        c.js("""(()=>{const b=document.querySelector('#gcBubbles .gc-msg[data-mid] .bubble'); if(b){b.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true}))} return !!b})()""")
        time.sleep(0.8)
        c.js("(()=>{const e=document.querySelector('#sheetBox [data-emo]'); if(e) e.click(); return !!e})()")
        time.sleep(0.8)
        note(bool(c.js("!!document.querySelector('.gc-reacts')")[0]), f'{theme}: reaction chip rendered')
        drain_err(c, 'react')
        # --- typing ---
        c.js("HUB.groupchat.simulateTyping('Maya',3000)"); time.sleep(0.8)
        note(bool(c.js("!!document.querySelector('.gc-typing')")[0]), f'{theme}: typing indicator')
        shot(c, f'gc-int-typing-{theme}')
        # --- members ---
        c.js("document.getElementById('gcHeadInfo').click()"); time.sleep(0.8)
        nmem = c.js("document.querySelectorAll('#sheetBox .gc-mem').length")[0] or 0
        note(nmem >= 4, f'{theme}: member grid', str(nmem))
        note(bool(c.js("!![...document.querySelectorAll('#sheetBox .gc-mem')].find(e=>/admin/i.test(e.textContent))")[0]), f'{theme}: admin badge')
        esc_key(c)
        note(bool(c.js("!!document.querySelector('#chatPanel:not([hidden])')")[0]), f'{theme}: member Escape -> chat intact')
        drain_err(c, 'members')
        # --- call ---
        c.js("document.getElementById('gcCall').click()"); time.sleep(1.5)
        note(bool(c.js("!document.getElementById('callRoot').hidden")[0]), f'{theme}: call UI opened')
        note(bool(c.js("/deploy the free signaling worker/i.test(document.getElementById('callRoot').textContent)")[0]), f'{theme}: honest demo label')
        note(bool(c.js("!!document.querySelector('.calltile')")[0]), f'{theme}: self tile')
        c.js("HUB.call._debugTone(true)"); time.sleep(1.2)
        spk = c.js("document.querySelector('.calltile.speaking')!==null")[0]
        note(bool(spk), f'{theme}: 3D speaking glow ON')
        shot(c, f'gc-int-call-{theme}')
        c.js("HUB.call._debugTone(false); HUB.call._debugMicTap(false)"); time.sleep(1.8)
        note(c.js("document.querySelector('.calltile.speaking')===null")[0], f'{theme}: speaking glow OFF when silent')
        note(bool(c.js("!![...document.querySelectorAll('#callRoot button')].find(b=>/mute/i.test(b.textContent+b.getAttribute('aria-label')||''))")[0]), f'{theme}: mute control present')
        esc_key(c); time.sleep(0.8)
        note(bool(c.js("document.getElementById('callRoot').hidden")[0]), f'{theme}: Escape leaves call')
        drain_err(c, 'call')
        # --- overflow ---
        c.js("HUB.gchat.open('g-qa')"); time.sleep(0.8)
        sw = c.js("Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)")[0] or 0
        note(sw <= 390, f'{theme}: no horizontal overflow', str(sw))
        # --- lazy locale kh ---
        lv, _ = c.js("HUB.i18n.loadLocale('de')", await_promise=True)
        note(lv is True, f'{theme}: de lazy locale loadLocale resolved')
        is_de = c.js("HUB.i18n._dict('de')!==HUB.i18n._dict('en') && !!HUB.i18n._dict('de')['call.demoNote']")[0]
        note(bool(is_de), f'{theme}: de lazy locale really loaded (not en fallback)')
        khc = c.js("JSON.parse(localStorage.getItem('orbit_i18n_dict_de')||'{}').kh")[0]
        note(khc == 'iaznu6', f'{theme}: cached de kh matches', str(khc))
        tval = c.js("HUB.i18n.t('call.demoNote')")[0]
        note(isinstance(tval, str) and 'signaling worker' in tval, f'{theme}: t() fallback for new key')
        drain_err(c, 'i18n')
        drain_err(c, 'final')
    finally:
        try: proc.terminate()
        except Exception: pass

for th in ['dark', 'light']:
    run(th)

print('\n==== %d/%d integration checks passed ====' % (sum(1 for ok, _ in checks if ok), len(checks)))
for ok, label in checks:
    if not ok: print('FAILED:', label)
print('console error batches:', len(errors))
