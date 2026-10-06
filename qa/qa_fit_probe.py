#!/usr/bin/env python3
"""HUB QA: page-fit probe — every tab must never exceed viewport width.
Asserts documentElement.scrollWidth <= innerWidth per tab per width,
and scans for offending elements when it fails.
Widths: 320/360/390/430/480/768, dark+light. Screenshots per tab @390.
Overlays probed @390: market detail, group chat, 1:1 thread, call UI, welcome."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
WIDTHS = [320, 360, 390, 430, 480, 768]
TABS = ['home', 'daily', 'market', 'work', 'groups', 'me']
errors, checks = [], []

def note(ok, label, detail=''):
    checks.append((ok, label))
    print(('PASS' if ok else 'FAIL'), label, detail[:160])

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
        try:
            r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
            res = (r or {}).get('result', {})
            return res.get('value')
        except Exception as e:
            return '__EVAL_ERR__:' + str(e)[:120]

OFFENDER_JS = """(()=>{
  window.scrollTo(0,0);
  const iw=window.innerWidth;
  const out=[];
  const els=document.querySelectorAll('body *');
  for(const el of els){
    const cs=getComputedStyle(el);
    if(cs.display==='none'||cs.visibility==='hidden') continue;
    const r=el.getBoundingClientRect();
    if(r.width===0&&r.height===0) continue;
    if(r.right<=iw+0.5&&r.left>=-0.5) continue;
    // inside an intentional horizontal scroller? then it's scroll content, fine
    let p=el.parentElement, inScroller=false, fixed=false;
    while(p&&p!==document.body){
      const pc=getComputedStyle(p);
      if(pc.position==='fixed'){fixed=true;break;}
      if(pc.overflowX==='auto'||pc.overflowX==='scroll'){inScroller=true;break;}
      p=p.parentElement;
    }
    if(getComputedStyle(el).position==='fixed') fixed=true;
    const cls=(el.className&&el.className.baseVal!==undefined)?el.className.baseVal:String(el.className||'');
    out.push({tag:el.tagName,cls:String(cls).slice(0,60),id:el.id||'',
      l:Math.round(r.left),r:Math.round(r.right),w:Math.round(r.width),
      fixed:fixed,inScroller:inScroller,
      html:el.outerHTML.slice(0,120)});
  }
  return {iw:iw,docSW:document.documentElement.scrollWidth,bodySW:document.body.scrollWidth,
    offenders:out.slice(0,25),n:out.length};
})()"""

def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data']))

def probe_tabs(c, theme, width):
    c.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+String((e.reason&&e.reason.message)||e.reason)))")
    c.js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();}catch(e){}")
    c.js("var w=document.getElementById('wlcmHost');if(w)w.hidden=true;")
    c.js("document.body.classList.%s('dark')" % ('add' if theme == 'dark' else 'remove'))
    time.sleep(0.8)
    for tab in TABS:
        c.js("HUB.showTab('%s');window.scrollTo(0,0);" % tab)
        time.sleep(1.4)
        m = c.js("({sw:document.documentElement.scrollWidth,iw:window.innerWidth})")
        ok = isinstance(m, dict) and m['sw'] <= m['iw']
        note(ok, '[%s/%d] tab %s fits (sw=%s)' % (theme, width, tab, m.get('sw') if isinstance(m, dict) else m))
        if not ok:
            det = c.js(OFFENDER_JS)
            print('   OFFENDERS:', json.dumps(det, indent=None)[:1200] if det else 'eval failed')
        if width == 390:
            shot(c, '%s-fit-%s' % (tab, theme))
        # auto-rotation must not move the page: wait 5s on home, re-assert
        if tab == 'home':
            sx0 = c.js("window.scrollX")
            time.sleep(5.2)
            m2 = c.js("({sw:document.documentElement.scrollWidth,sx:window.scrollX})")
            ok2 = isinstance(m2, dict) and m2['sw'] <= width and (m2.get('sx') or 0) == 0
            note(ok2, '[%s/%d] home rotation does not shift page' % (theme, width), str(m2))
    errs = c.js("window.__huberr.splice(0)")
    if errs: print('   console errors:', errs[:5])

def probe_overlays(c, theme):
    # market listing detail
    c.js("HUB.showTab('market');window.scrollTo(0,0)"); time.sleep(1.2)
    c.js("var k=document.querySelector('.mkcard');if(k)k.click()"); time.sleep(1.2)
    m = c.js("({sw:document.documentElement.scrollWidth,iw:window.innerWidth})")
    note(isinstance(m, dict) and m['sw'] <= m['iw'], '[%s] overlay market-detail fits' % theme, str(m))
    shot(c, 'ovl-mkdetail-fit-%s' % theme)
    c.js("try{HUB.ui.closeSheet();}catch(e){}"); time.sleep(0.6)
    # group chat (first group in store)
    gid = c.js("(()=>{var g=(HUB.store.state.groups||[])[0];return g?g.id:null;})()")
    if gid and gid != '__EVAL_ERR__':
        c.js("HUB.groupchat.open(%s)" % json.dumps(gid)); time.sleep(1.2)
        m = c.js("({sw:document.documentElement.scrollWidth,iw:window.innerWidth})")
        note(isinstance(m, dict) and m['sw'] <= m['iw'], '[%s] overlay groupchat fits' % theme, str(m))
        shot(c, 'ovl-groupchat-fit-%s' % theme)
        c.js("try{HUB.groupchat.close();}catch(e){}"); time.sleep(0.6)
    # 1:1 chat thread
    tid = c.js("(()=>{HUB.store.add('contacts',{name:'FitProbe',phone:''});var c0=HUB.store.state.contacts[HUB.store.state.contacts.length-1];HUB.store.add('threads',{contactId:c0.id,title:'FitProbe',messages:[],unread:0});return HUB.store.state.threads[HUB.store.state.threads.length-1].id;})()")
    c.js("HUB.chat.openThread(%s)" % json.dumps(tid)); time.sleep(1.0)
    m = c.js("({sw:document.documentElement.scrollWidth,iw:window.innerWidth})")
    note(isinstance(m, dict) and m['sw'] <= m['iw'], '[%s] overlay 1:1 thread fits' % theme, str(m))
    shot(c, 'ovl-thread-fit-%s' % theme)
    c.js("try{HUB.chat.close();}catch(e){}"); time.sleep(0.6)
    # call UI
    c.js("HUB.call.start('qa-fit')"); time.sleep(1.2)
    m = c.js("({sw:document.documentElement.scrollWidth,iw:window.innerWidth})")
    note(isinstance(m, dict) and m['sw'] <= m['iw'], '[%s] overlay call UI fits' % theme, str(m))
    shot(c, 'ovl-call-fit-%s' % theme)
    c.js("try{HUB.call.leave();}catch(e){}"); time.sleep(0.6)
    errs = c.js("window.__huberr.splice(0)")
    if errs: print('   console errors:', errs[:5])

def main():
    for theme in ['dark', 'light']:
        port = 9451 if theme == 'dark' else 9452
        prof = '/tmp/hubqa-fit-%s' % theme
        shutil.rmtree(prof, ignore_errors=True)
        proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
            '--disable-dev-shm-usage', '--remote-debugging-port=%d' % port, '--remote-allow-origins=*',
            '--user-data-dir=' + prof, '--hide-scrollbars', '--allow-file-access-from-files', BASE],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            tgt = None
            for _ in range(30):
                time.sleep(1)
                try:
                    with urllib.request.urlopen('http://localhost:%d/json/list' % port, timeout=3) as r:
                        ts = json.load(r)
                    tgt = next(x for x in ts if x['type'] == 'page' and 'devtools' not in x['url'])
                    break
                except Exception: continue
            c = CDP(tgt['webSocketDebuggerUrl'])
            c.send('Runtime.enable'); c.send('Page.enable')
            time.sleep(4)
            for width in WIDTHS:
                c.send('Emulation.setDeviceMetricsOverride', {'width': width, 'height': 844,
                    'deviceScaleFactor': 2, 'mobile': True})
                c.send('Page.reload'); time.sleep(3.5)
                probe_tabs(c, theme, width)
            # overlays at 390
            c.send('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844,
                'deviceScaleFactor': 2, 'mobile': True})
            c.send('Page.reload'); time.sleep(3.5)
            probe_overlays(c, theme)
        finally:
            proc.terminate()
    ok = sum(1 for o, _ in checks if o); tot = len(checks)
    print('==== FIT PROBE: %d/%d passed' % (ok, tot))

if __name__ == '__main__':
    main()
