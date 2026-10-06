#!/usr/bin/env python3
"""Quick unbuffered fit probe: Home tab @390 dark, offender scan."""
import json, subprocess, time, urllib.request, os, base64, shutil, sys
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9471
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

OFFENDER_JS = open(os.path.expanduser('~/workspace/hub/qa/offender_snippet.js')).read() if os.path.exists(os.path.expanduser('~/workspace/hub/qa/offender_snippet.js')) else None
if not OFFENDER_JS:
    OFFENDER_JS = """(()=>{
      window.scrollTo(0,0);
      const iw=window.innerWidth; const out=[];
      for(const el of document.querySelectorAll('body *')){
        const cs=getComputedStyle(el);
        if(cs.display==='none'||cs.visibility==='hidden') continue;
        const r=el.getBoundingClientRect();
        if(r.width===0&&r.height===0) continue;
        if(r.right<=iw+0.5&&r.left>=-0.5) continue;
        let p=el.parentElement,inScroller=false,fixed=false;
        while(p&&p!==document.body){
          const pc=getComputedStyle(p);
          if(pc.position==='fixed'){fixed=true;break;}
          if(pc.overflowX==='auto'||pc.overflowX==='scroll'){inScroller=true;break;}
          p=p.parentElement;
        }
        if(getComputedStyle(el).position==='fixed') fixed=true;
        const cls=(el.className&&el.className.baseVal!==undefined)?el.className.baseVal:String(el.className||'');
        out.push({tag:el.tagName,cls:String(cls).slice(0,50),id:el.id||'',
          l:Math.round(r.left),r:Math.round(r.right),fixed:fixed,inScroller:inScroller});
      }
      return {iw:iw,docSW:document.documentElement.scrollWidth,bodySW:document.body.scrollWidth,
        phoneSW:document.getElementById('app').scrollWidth, offenders:out.slice(0,30),n:out.length};
    })()"""

prof = '/tmp/hubqa-fitmini'
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
    c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
    time.sleep(5)
    c.js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
    c.js("document.body.classList.add('dark')")
    time.sleep(0.8)
    c.js("HUB.showTab('home');window.scrollTo(0,0)")
    time.sleep(2)
    m = c.js("({sw:document.documentElement.scrollWidth,iw:window.innerWidth,sx:window.scrollX})")
    print('MEASURE:', m, flush=True)
    det = c.js(OFFENDER_JS)
    print('DETAIL:', json.dumps(det), flush=True)
    # scroll the page down a bit and re-measure (sticky/fixed interplay)
    c.js("window.scrollTo(0,600)"); time.sleep(1)
    m2 = c.js("({sw:document.documentElement.scrollWidth,sx:window.scrollX})")
    print('MEASURE2:', m2, flush=True)
    # simulate what a swipe-chain does: try scrolling page horizontally
    c.js("window.scrollTo(100,600)"); time.sleep(0.5)
    m3 = c.js("({sx:window.scrollX})")
    print('SCROLLX-after-forced:', m3, flush=True)
finally:
    proc.terminate()
print('MINI DONE', flush=True)
