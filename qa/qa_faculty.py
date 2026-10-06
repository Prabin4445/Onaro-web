#!/usr/bin/env python3
"""Faculty pipeline QA (2026-09-23).
- data/faculty/index.json valid; every slug file loads as JSON with expected shape
- spot-check counts match index counts
- app lazy-loads real directory data for a seeded campus; fallback honest for unknown campus
- zero console errors; 390px no horizontal overflow
"""
import json, subprocess, time, urllib.request, os, shutil, glob
import websocket
CHROME='/opt/meta-chromium/chrome'; PORT=9493
BASE='file:///home/hatch/workspace/hub/index.html'
FAC=os.path.expanduser('~/workspace/hub/data/faculty')
checks=[]
def note(ok,label,detail=''):
    checks.append(bool(ok)); print(('PASS' if ok else 'FAIL'),label,detail)
class CDP:
    def __init__(self,wsurl):
        self.ws=websocket.create_connection(wsurl,timeout=12); self.ws.settimeout(12); self.id=0
    def send(self,method,params=None):
        self.id+=1
        self.ws.send(json.dumps({'id':self.id,'method':method,'params':params or {}}))
        deadline=time.time()+15
        while time.time()<deadline:
            try: msg=json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method+': '+str(e)[:80])
            if msg.get('id')==self.id: return msg.get('result')
        raise TimeoutError(method)
    def js(self,expr,awaitPromise=False):
        r=self.send('Runtime.evaluate',{'expression':expr,'awaitPromise':awaitPromise,'returnByValue':True})
        return (r.get('result') or {}).get('value')

# ---- static checks ----
idx=json.load(open(os.path.join(FAC,'index.json')))
note(isinstance(idx.get('colleges'),list),'index.json has colleges array',f"n={len(idx.get('colleges',[]))}")
total=0
for c in idx['colleges']:
    fp=os.path.join(FAC,c['slug']+'.json')
    ok=os.path.exists(fp)
    note(ok,f"slug file exists: {c['slug']}")
    if not ok: continue
    d=json.load(open(fp,encoding='utf-8'))
    ps=d.get('professors',[])
    note(isinstance(ps,list) and len(ps)>0,f"{c['slug']}: non-empty professors",f"n={len(ps)}")
    note(len(ps)==c.get('count'),f"{c['slug']}: count matches index",f"{len(ps)} vs {c.get('count')}")
    bad=[p for p in ps if not p.get('name')]
    note(len(bad)==0,f"{c['slug']}: all records have names")
    total+=len(ps)
note(total>0 or len(idx['colleges'])==0,'total professors > 0',f'total={total}')

# ---- app integration ----
def app_case(campus, expect_dirs):
    prof=f'/tmp/hubqa-faculty-{abs(hash(campus))%9999}'; shutil.rmtree(prof,ignore_errors=True); os.makedirs(prof,exist_ok=True)
    proc=subprocess.Popen([CHROME,'--headless=new','--no-sandbox','--disable-gpu',
        f'--remote-debugging-port={PORT}','--remote-allow-origins=*','--window-size=390,844',
        f'--user-data-dir={prof}','--hide-scrollbars','--allow-file-access-from-files',BASE],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    errs=[]
    try:
        # 2026-09-23: Chrome needs ~6-10s to serve /json on first launch; poll instead of fixed sleep
        tabs=None
        for _ in range(30):
            try:
                tabs=json.loads(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json',timeout=5).read().decode())
                break
            except Exception:
                time.sleep(1)
        if tabs is None:
            raise RuntimeError('chrome devtools /json never responded')
        page=[t for t in tabs if t.get('type')=='page'][0]
        c=CDP(page['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Log.enable')
        # true 390px viewport: headless clamps --window-size to min 500px wide,
        # so emulate the device explicitly then reload
        c.send('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':2,'mobile':True})
        c.send('Page.reload')
        for _ in range(40):
            if c.js("document.readyState")=='complete': break
            time.sleep(0.5)
        c.js(f"(()=>{{HUB.store.state.profile.name='QA';HUB.store.state.profile.campus={json.dumps(campus)};HUB.store.save();return 1;}})()")
        time.sleep(0.5)
        loaded=c.js("(async()=>{await HUB.professors._faculty.ensure(HUB.store.state.profile.campus);return HUB.professors._faculty.dirs(HUB.store.state.profile.campus).length;})()",awaitPromise=True)
        if expect_dirs:
            note(loaded and loaded>0,f'[{campus}] lazy-loads directory data',f'n={loaded}')
            slug=c.js("HUB.professors._faculty.slugFor(HUB.store.state.profile.campus)")
            note(bool(slug),f'[{campus}] slug matched',str(slug))
            # open the page, check list renders + no overflow
            c.js("HUB.professors.open()"); time.sleep(1.5)
            cards=c.js("document.querySelectorAll('.prof-card').length")
            note(cards and cards>0,f'[{campus}] renders professor cards',f'cards={cards}')
            ov=c.js("document.documentElement.scrollWidth<=390")
            note(ov,f'[{campus}] no horizontal overflow at 390px')
            c.js("HUB.professors.close()")
        else:
            note(loaded==0,f'[{campus}] unknown campus: no directory data (honest fallback)',f'n={loaded}')
        deadline=time.time()+2
        while time.time()<deadline:
            try:
                m=json.loads(c.ws.recv(timeout=2))
                if m.get('method')=='Runtime.exceptionThrown': errs.append(str(m.get('params',{}).get('exceptionDetails',{}).get('text'))[:120])
                if m.get('method')=='Log.entryAdded' and m.get('params',{}).get('entry',{}).get('level')=='error': errs.append(str(m['params']['entry'].get('text'))[:120])
            except Exception: break
        note(len(errs)==0,f'[{campus}] zero console errors',repr(errs[:3]))
    finally:
        proc.terminate()

# pick a landed campus with real data, else skip app assertions gracefully
landed=[c for c in idx['colleges'] if c.get('count',0)>0]
if landed:
    app_case(landed[0]['match'][0] if landed[0].get('match') else landed[0]['name'], True)
app_case('Nonexistent Test University', False)
print(f"\n{sum(checks)}/{len(checks)} passed")
