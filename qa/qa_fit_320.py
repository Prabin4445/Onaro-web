#!/usr/bin/env python3
"""Focused 320px probe: offender dump + long-string stress test."""
import json, subprocess, time, urllib.request, os, shutil
import websocket
CHROME = '/opt/meta-chromium/chrome'; PORT = 9475
BASE = 'file:///home/hatch/workspace/hub/index.html'

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
    def js(self, expr):
        r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
        return (r or {}).get('result', {}).get('value')

OFF = """(()=>{
  window.scrollTo(0,0);
  const iw=window.innerWidth; const out=[];
  for(const el of document.querySelectorAll('body *')){
    const cs=getComputedStyle(el);
    if(cs.display==='none'||cs.visibility==='hidden') continue;
    const r=el.getBoundingClientRect();
    if(r.width<2||r.height<2) continue;
    if(r.right<=iw+0.5&&r.left>=-0.5) continue;
    let p=el.parentElement,inScroller=false,fixed=false;
    while(p&&p!==document.body){
      const pc=getComputedStyle(p);
      if(pc.position==='fixed'){fixed=true;break;}
      if(pc.overflowX==='auto'||pc.overflowX==='scroll'){inScroller=true;break;}
      p=p.parentElement;
    }
    if(getComputedStyle(el).position==='fixed') fixed=true;
    if(inScroller) continue;
    const cls=String(el.className&&el.className.baseVal!==undefined?el.className.baseVal:(el.className||'')).slice(0,50);
    out.push({tag:el.tagName,cls:cls,id:el.id||'',l:Math.round(r.left),r:Math.round(r.right),
      fixed:fixed,txt:(el.textContent||'').trim().slice(0,40)});
  }
  return {iw:iw,docSW:document.documentElement.scrollWidth,viewsSW:document.querySelector('.views').scrollWidth,
    offenders:out.slice(0,20),n:out.length};
})()"""

prof = '/tmp/hubqa-fit320'
shutil.rmtree(prof, ignore_errors=True)
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    '--disable-dev-shm-usage', '--remote-debugging-port=%d' % PORT, '--remote-allow-origins=*',
    '--user-data-dir=' + prof, '--hide-scrollbars', '--allow-file-access-from-files', BASE],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    tgt = None
    for _ in range(30):
        time.sleep(1)
        try:
            with urllib.request.urlopen('http://localhost:%d/json/list' % PORT, timeout=3) as r:
                ts = json.load(r)
            tgt = next(x for x in ts if x['type'] == 'page' and 'devtools' not in x['url'])
            break
        except Exception: continue
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable'); c.send('Page.enable')
    c.send('Emulation.setDeviceMetricsOverride', {'width': 320, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    time.sleep(5)
    c.js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
    c.js("document.body.classList.add('dark')")
    time.sleep(0.8)
    for tab in ['home', 'daily', 'market', 'work', 'groups', 'me']:
        c.js("HUB.showTab('%s');window.scrollTo(0,0)" % tab)
        time.sleep(1.2)
        det = c.js(OFF)
        flag = 'OK ' if det['docSW'] <= det['iw'] else 'OVER'
        print('%s [%s] iw=%s docSW=%s viewsSW=%s offenders=%d' % (flag, tab, det['iw'], det['docSW'], det['viewsSW'], det['n']), flush=True)
        for o in det['offenders'][:8]:
            print('    %s.%s#%s l=%s r=%s fixed=%s txt=%s' % (o['tag'], o['cls'], o['id'], o['l'], o['r'], o['fixed'], o['txt'][:30]), flush=True)
    # stress: long unbroken strings in user data (bill name, event title, chat msg)
    c.js("HUB.store.add('bills',{item:'Supercalifragilisticexpialidocious-Electricity-Bill-December',amount:70,paidBy:'PraBin',at:Date.now()});")
    c.js("HUB.showTab('home');window.scrollTo(0,0)")
    time.sleep(1.0)
    det = c.js(OFF)
    print('%s [home+longstring] iw=%s docSW=%s offenders=%d' % ('OK ' if det['docSW'] <= det['iw'] else 'OVER', det['iw'], det['docSW'], det['n']), flush=True)
    for o in det['offenders'][:8]:
        print('    %s.%s#%s l=%s r=%s txt=%s' % (o['tag'], o['cls'], o['id'], o['l'], o['r'], o['txt'][:30]), flush=True)
finally:
    proc.terminate()
print('FOCUSED DONE', flush=True)
