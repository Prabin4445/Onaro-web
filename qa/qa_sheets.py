#!/usr/bin/env python3
"""QA: universal sheet ✕, add-auto-close, done-closes — across representative sheets."""
import json, subprocess, time, urllib.request, os
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9441
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
def main():
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=500,900',
        '--user-data-dir=/tmp/hubqa-sheets', '--hide-scrollbars', '--allow-file-access-from-files',
        '--autoplay-policy=no-user-gesture-required', BASE],
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
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
                res = (r or {}).get('result', {})
                return res.get('value'), None
            except Exception as e: return None, str(e)[:160]
        def errs(label):
            v, _ = js("window.__huberr.splice(0)")
            if v: errors.append((label, v)); print('ERRORS @', label, ':', json.dumps(v)[:400])
        def shot(name):
            c.send('Page.captureScreenshot', {'format': 'png'})
            # captureScreenshot returns via result.data
            return None
        def shot2(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            import base64
            open(os.path.join(QA, name), 'wb').write(base64.b64decode(r['data']))
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(3); errs('load')
        js("try{var st=JSON.parse(localStorage.getItem('hub_v1')||'null'); if(st){st.profile=st.profile||{}; st.profile.name='QA'; localStorage.setItem('hub_v1',JSON.stringify(st));} var w=document.getElementById('wlcmHost'); if(w) w.hidden=true;}catch(e){}")
        time.sleep(1)

        sheet_open = "document.getElementById('sheetHost').hidden===false"
        x_visible = """(()=>{const x=document.querySelector('#sheetBox .sheetx'); if(!x) return 'missing';
          const r=x.getBoundingClientRect(); return (r.width>=44&&r.height>=44&&r.top>=0&&r.left>=0&&r.right<=innerWidth+1)?'ok':'badrect:'+JSON.stringify(r);})()"""

        # ---- 1. Class schedule sheet (PraBin's reported bug) ----
        v, e = js("HUB.classes.manageSheet(); 'ok'")
        time.sleep(0.9)
        note(v == 'ok', 'class sheet opens')
        v, _ = js(x_visible); note(v == 'ok', 'class sheet has visible 44px ✕', str(v))
        shot2('sheet-class.png'); errs('class-open')
        # click the ✕
        v, _ = js("document.querySelector('#sheetBox .sheetx').click(); 'clicked'")
        time.sleep(0.6)
        v, _ = js("document.getElementById('sheetHost').hidden")
        note(v is True, '✕ closes class sheet')
        # reopen, add a class -> sheet must auto-close
        js("HUB.classes.manageSheet()")
        time.sleep(0.4)
        js("""(()=>{const b=document.getElementById('sheetBox');
          b.querySelector('#clsSubject').value='QA Biology';
          b.querySelector('.daypick[data-day=\"1\"]').click();
          b.querySelector('.daypick[data-day=\"3\"]').click();})()""")
        time.sleep(0.3)
        v, _ = js("document.getElementById('clsAdd').click(); 'added'")
        time.sleep(0.8)
        v, _ = js("document.getElementById('sheetHost').hidden")
        note(v is True, 'adding class auto-closes sheet')
        v, _ = js("HUB.classes.list().some(c=>c.subject==='QA Biology')")
        note(v is True, 'class persisted')
        errs('class-add')

        # ---- 2. Generic openSheet gets ✕; ✕ click + backdrop click close ----
        js("HUB.ui.openSheet('<h2>Probe</h2><p>probe body</p>')")
        time.sleep(0.9)
        v, _ = js(x_visible); note(v == 'ok', 'generic sheet has ✕', str(v))
        shot2('sheet-generic.png')
        js("document.querySelector('#sheetBox .sheetx').click()"); time.sleep(0.5)
        v, _ = js("document.getElementById('sheetHost').hidden")
        note(v is True, '✕ closes generic sheet')
        js("HUB.ui.openSheet('<h2>Probe2</h2><p>x</p>')"); time.sleep(0.3)
        v, _ = js("document.getElementById('sheetHost').dispatchEvent(new MouseEvent('click',{bubbles:true})); document.getElementById('sheetHost').hidden")
        note(v is True, 'backdrop tap still closes')
        errs('generic')

        # ---- 3. Story composer: own ✕, no duplicate universal ✕ ----
        js("HUB.stories.createSheet()"); time.sleep(0.5)
        v, _ = js("document.querySelectorAll('#sheetBox .sheetx').length")
        note(v == 0, 'composer skips duplicate ✕ (has own stc-x)', 'count='+str(v))
        v, _ = js("!!document.getElementById('sCancel')")
        note(v is True, 'composer own ✕ present')
        shot2('sheet-composer.png')
        js("document.getElementById('sCancel').click()"); time.sleep(0.5)
        v, _ = js("document.getElementById('sheetHost').hidden")
        note(v is True, 'composer ✕ closes')
        errs('composer')

        # ---- 4. Sheet with its own data-close: no duplicate ----
        js("HUB.ui.openSheet('<h2>T</h2><button data-close>✕</button>')"); time.sleep(0.3)
        v, _ = js("document.querySelectorAll('#sheetBox .sheetx').length")
        note(v == 0, 'data-close sheet skips duplicate ✕', 'count='+str(v))
        js("HUB.ui.closeSheet()"); errs('dataclose')

        # ---- 5. Market post sheet: ✕ present, publish auto-closes ----
        js("HUB.showTab('market')"); time.sleep(1.2)
        v, _ = js("(()=>{const b=document.getElementById('mkPostBtn'); if(!b) return 'nobtn'; b.click(); return 'ok'})()")
        note(v == 'ok', 'market post sheet opens', str(v))
        time.sleep(0.9)
        v, _ = js(x_visible); note(v == 'ok', 'market sheet has ✕', str(v))
        shot2('sheet-market.png')
        js("""(()=>{const b=document.getElementById('sheetBox');
          b.querySelector('#mkTitle').value='QA Chair';
          b.querySelector('#mkTypeChips .chip[data-t=\"SELL\"]').click();})()""")
        time.sleep(0.3)
        js("document.getElementById('mkPublish').click()"); time.sleep(0.8)
        v, _ = js("document.getElementById('sheetHost').hidden")
        note(v is True, 'publishing listing auto-closes sheet')
        errs('market')

        # ---- 6. Create > event sheet: ✕ + save closes ----
        js("HUB.create.open()"); time.sleep(0.5)
        v, _ = js(x_visible); note(v == 'ok', 'create menu sheet has ✕', str(v))
        js("document.querySelector('.caction[data-a=\"3\"]').click()"); time.sleep(0.9)
        v, _ = js(x_visible); note(v == 'ok', 'event sheet has ✕', str(v))
        shot2('sheet-event.png')
        js("""(()=>{document.getElementById('evTitle').value='QA Party';document.getElementById('evTime').value='Friday 8pm';})()""")
        js("document.getElementById('evSave').click()"); time.sleep(0.8)
        v, _ = js("document.getElementById('sheetHost').hidden")
        note(v is True, 'saving event auto-closes sheet')
        errs('create-event')

        # ---- 7. Work job sheet ----
        js("HUB.showTab('work')"); time.sleep(1.2)
        js("document.getElementById('postJobBtn').click()"); time.sleep(0.5)
        v, _ = js(x_visible); note(v == 'ok', 'work job sheet has ✕', str(v))
        js("HUB.ui.closeSheet()"); errs('work')

        print('\n%d/%d checks passed' % (sum(1 for ok, _ in checks if ok), len(checks)))
        print('console-error groups:', len(errors))
    finally:
        proc.terminate()
main()
