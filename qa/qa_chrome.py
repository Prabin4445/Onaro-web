#!/usr/bin/env python3
"""QA: line-icon chrome + dead-X fixes."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA=os.path.expanduser('~/workspace/hub/qa'); PORT=9458
checks=[]
def note(ok,label,detail=''):
    checks.append(bool(ok)); print(('PASS' if ok else 'FAIL'),label,detail)
proc=subprocess.Popen(['/opt/meta-chromium/chrome','--headless=new','--no-sandbox','--disable-gpu',
 f'--remote-debugging-port={PORT}','--remote-allow-origins=*','--window-size=414,900',
 '--user-data-dir=/tmp/hubqm-prof','--hide-scrollbars','--allow-file-access-from-files','about:blank'],
 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    for _ in range(30):
        time.sleep(1)
        try:
            with urllib.request.urlopen(f'http://localhost:{PORT}/json/list',timeout=3) as r: ts=json.load(r)
            tgt=next(t for t in ts if t['type']=='page' and 'devtools' not in t['url']); break
        except Exception: continue
    ws=websocket.create_connection(tgt['webSocketDebuggerUrl'],timeout=12); ws.settimeout(12)
    def send(m_id,method,params): ws.send(json.dumps({'id':m_id,'method':method,'params':params}))
    def js(e):
        send(1,'Runtime.evaluate',{'expression':e,'returnByValue':True})
        dl=time.time()+20
        while time.time()<dl:
            m=json.loads(ws.recv())
            if m.get('id')==1: return (m.get('result') or {}).get('result',{}).get('value')
        raise TimeoutError()
    def shot(name,clip=None):
        send(2,'Page.captureScreenshot',{'format':'png','clip':clip} if clip else {'format':'png'})
        dl=time.time()+15
        while time.time()<dl:
            m=json.loads(ws.recv())
            if m.get('id')==2:
                open(os.path.join(QA,name+'.png'),'wb').write(base64.b64decode(m['result']['data'])); return
    def click(sel):
        js("(()=>{const el=document.querySelector('"+sel+"'); if(el){el.scrollIntoView({block:'center'}); return true} return false})()")
        time.sleep(0.4); js("document.querySelector('"+sel+"').click()"); time.sleep(1.2)
    send(90,'Page.navigate',{'url':'file:///home/hatch/workspace/hub/index.html'}); time.sleep(6)
    js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
    send(89,'Page.navigate',{'url':'file:///home/hatch/workspace/hub/index.html'}); time.sleep(8)
    note(not js("window.__err||0"), 'boot ok','')
    js("""var p=HUB.store.state.profile; p.name='PraBin'; p.campus='Downtown'; p.audience='community'; HUB.store.save();
          try{HUB.ui.closeSheet();}catch(e){}
          var ap=document.getElementById('askPill'); if(ap) ap.style.display='none';
          HUB.showTab('home');""")
    time.sleep(3)
    # --- tab icons are SVG line icons ---
    n_svg = js("document.querySelectorAll('#tabbar .tab-ico svg.lnico').length")
    n_img = js("document.querySelectorAll('#tabbar .tab-ico img').length")
    note(n_svg==6 and n_img==0, '6 tab icons are SVG line icons', f'svg={n_svg} img={n_img}')
    hdr_svg = js("['searchBtn','pulseBtn','notifBtn','chatFab'].filter(id=>document.querySelector('#'+id+' svg.lnico')).length")
    note(hdr_svg==4, '4 header icons are SVG', str(hdr_svg))
    note(js("!!document.querySelector('#askPillIco svg.lnico')"), 'ask pill icon is SVG','')
    # --- tab switching still works ---
    click('#tabbar [data-tab="market"]')
    note(js("document.querySelector('#tabbar [data-tab=\"market\"]').classList.contains('active')"), 'market tab activates','')
    click('#tabbar [data-tab="home"]')
    note(js("document.querySelector('#tabbar [data-tab=\"home\"]').classList.contains('active')"), 'home tab reactivates','')
    # --- dead X fixes ---
    js("HUB.appts.formSheet(null)"); time.sleep(1)
    note(js("!document.getElementById('sheetHost').hidden"), 'appointment sheet opened','')
    click("#sheetBox [data-close]")
    note(js("document.getElementById('sheetHost').hidden"), 'appointment sheet X closes','')
    js("HUB.astro.openSheet()"); time.sleep(1)
    click("#sheetBox [data-close]")
    note(js("document.getElementById('sheetHost').hidden"), 'horoscope sheet X closes','')
    js("HUB.astro.openCalendar()"); time.sleep(1)
    click("#sheetBox [data-close]")
    note(js("document.getElementById('sheetHost').hidden"), 'calendar sheet X closes','')
    # --- screenshots: tab bar ---
    js("document.getElementById('tabbar').scrollIntoView({block:'end'})"); time.sleep(0.8)
    shot('chrome-tabs', {'x':0,'y':640,'width':414,'height':260,'scale':1})
    js("document.body.classList.add('dark')"); time.sleep(1)
    shot('chrome-tabs-dark', {'x':0,'y':640,'width':414,'height':260,'scale':1})
    errs = js("(()=>{const e=[];return e.length})()")
    print('RESULT:', 'ALL PASS' if all(checks) else 'FAILURES')
finally:
    proc.terminate()
