#!/usr/bin/env python3
"""Interactive probe: verify suspicious findings one by one. Prints precise DOM behavior."""
import json, subprocess, time, urllib.request, os, base64, shutil, sys
import websocket
QA = os.path.expanduser('~/workspace/hub/qa/audit-missing')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
PORT = 9751
class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12); self.id = 0
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 18
        while time.time() < deadline:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:80])
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)
prof = '/tmp/hubqa-probe'
shutil.rmtree(prof, ignore_errors=True)
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
    f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def js(expr):
    r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
    return (r or {}).get('result', {}).get('value')
def shot(name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, name + '-probe.png'), 'wb').write(base64.b64decode(r['data']))
def st():
    return {'sheet': js("!document.getElementById('sheetHost').hidden"),
            'chatroot': js("!!document.querySelector('.chatroot:not([hidden])')"),
            'mkzoom': js("!!document.querySelector('.mkzoom:not([hidden])')"),
            'gydrawer': js("!!document.getElementById('gyDrawer')"),
            'tab': js("document.querySelector('#tabbar .tab.active').dataset.tab")}
try:
    for _ in range(30):
        time.sleep(1)
        try:
            with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as r: ts = json.load(r)
            tgt = next(x for x in ts if x['type'] == 'page' and 'devtools' not in x['url']); break
        except Exception: continue
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Emulation.setDeviceMetricsOverride', {'width':390,'height':844,'deviceScaleFactor':2,'mobile':True})
    c.send('Runtime.enable'); c.send('Page.enable')
    js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message))")
    time.sleep(5)
    js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
    js("document.body.classList.add('dark')"); time.sleep(1)

    def tab(t): js(f"HUB.showTab('{t}')"); time.sleep(1.5)
    def close_all():
        js("try{HUB.ui.closeSheet();}catch(e){};for(const k of ['chat','pulse','search','notifications'])try{if(HUB[k]&&HUB[k].close)HUB[k].close();}catch(e){};['gyBd','gyDrawer'].forEach(function(id){var e=document.getElementById(id);if(e)e.remove();});document.querySelectorAll('.mkzoom').forEach(function(e){e.remove();});")
        time.sleep(0.7)

    # A. glance tiles
    tab('home')
    print('A gltile count:', js("document.querySelectorAll('.gltile').length"))
    print('  home inner has glance:', 'glance' in (js("document.getElementById('view-home').innerHTML") or '').lower())
    # B. gym setup
    tab('daily'); time.sleep(1)
    print('B gySetup exists:', js("!!document.querySelector('#gySetup')"))
    js("document.querySelector('#gySetup').click()"); time.sleep(1.5)
    print('  after click:', st())
    print('  sheet text head:', (js("document.getElementById('sheetBox').innerText") or '')[:200].replace('\n',' | '))
    print('  gym state:', js("JSON.stringify(HUB.store.state.gym||null).slice(0,120)"))
    close_all()
    # C. GPA add
    tab('home')
    print('C addCourse btn:', js("(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent.includes('Add course'));return b?b.id+'|'+b.className:'none';})()"))
    js("(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent.includes('Add course'));if(b)b.click();})()"); time.sleep(1.5)
    print('  after click:', st())
    close_all()
    # D. appt add
    print('D appt btn:', js("(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent.includes('Add appointment'));return b?(b.id+'|'+b.className+'|'+(b.dataset?'d:'+JSON.stringify(b.dataset):'')):'none';})()"))
    js("(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent.includes('Add appointment'));if(b)b.click();})()"); time.sleep(1.5)
    print('  after click:', st())
    close_all()
    # E. create FAB
    print('E createFab exists:', js("!!document.querySelector('#createFab')"))
    js("document.querySelector('#createFab').click()"); time.sleep(1.5)
    print('  after click:', st())
    print('  caction count:', js("document.querySelectorAll('.caction').length"))
    print('  sheet head:', (js("document.getElementById('sheetBox').innerText") or '')[:150].replace('\n',' | '))
    close_all()
    # F. market radius
    tab('market'); time.sleep(1)
    print('F listings:', js("document.querySelectorAll('[data-listing]').length"))
    print('  distances:', js("()=>[...document.querySelectorAll('[data-listing]')].map(e=>(e.innerText.match(/[0-9.]+\\s?mi/)||['?'])[0]).join(',')"))
    print('  radius chips:', js("()=>[...document.querySelectorAll('.rchip,.chip')].slice(0,8).map(e=>e.textContent.trim().slice(0,12)).join('|')"))
    close_all()
    # G. listing persistence probe: add via API then reload
    n0 = js("HUB.store.state.market.length")
    js("HUB.store.state.market.unshift({id:'qa-persist-1',title:'QA Persist Lamp',price:25,type:'SELL',desc:'d',seller:'PraBin',dist:1,imgs:[],createdAt:Date.now()});HUB.store.save();")
    time.sleep(0.5)
    c.send('Page.reload'); time.sleep(5)
    js("document.body.classList.add('dark')")
    print('G after reload market len:', js("HUB.store.state.market.length"), 'was', n0)
    print('  QA lamp present:', js("HUB.store.state.market.some(m=>m.id==='qa-persist-1')"))
    print('  errors:', js("window.__huberr.splice(0)"))
    # H. language
    print('H setLang es:', js("try{HUB.i18n.setLang('es');'ok'}catch(e){String(e)}"))
    time.sleep(2)
    tab('home'); time.sleep(1)
    t = js("document.body.innerText.slice(0,400)") or ''
    print('  home head es:', t.replace('\n',' | ')[:300])
    js("try{HUB.i18n.setLang('en');'ok'}catch(e){}")
    time.sleep(1.5)
    print('done')
finally:
    proc.terminate()
