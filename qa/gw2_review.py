#!/usr/bin/env python3
"""GW2 visual review harness: renders all 19 exercises at top/bottom/mid of the
rep using the HUB.gymworkAnim._pose QA hook, screenshots to qa/gw2-<id>-<pos>.png.
Dark mode, 390px wide. Also thumbnails, alt-variant check, light mode, reduced motion."""
import json, subprocess, time, urllib.request, os, base64, socket, sys
import websocket

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
import random
PORT = 9600 + random.randint(0, 300)
PROFILE = '/tmp/hubqa-gw2-%d-%d' % (os.getpid(), int(time.time()))
os.makedirs(QA, exist_ok=True)

def port_open():
    s = socket.socket(); s.settimeout(1)
    try: s.connect(('localhost', PORT)); return True
    except OSError: return False

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl); self.id = 0
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 30
        while time.time() < deadline:
            msg = json.loads(self.ws.recv())
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)

BASE = 'file:///home/hatch/workspace/hub/index.html'

def launch(reduced=False):
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
        '--allow-file-access-from-files', f'--user-data-dir={PROFILE}',
        '--hide-scrollbars', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tgt = None
    for _ in range(60):
        try:
            with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=2) as r:
                for t in json.load(r):
                    if t['type'] == 'page' and 'devtools' not in t['url']: tgt = t
            if tgt: break
        except Exception:
            time.sleep(0.5)
    if not tgt: raise RuntimeError('no page target')
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Runtime.enable'); c.send('Page.enable')
    return proc, c

def js(c, expr, await_=False):
    r = c.send('Runtime.evaluate', {'expression': '(function(){' + expr + '})()',
        'awaitPromise': await_, 'returnByValue': True})
    res = (r or {}).get('result', {})
    return res.get('value'), res.get('exceptionDetails')

def shot_el(c, path, scale=1):
    rect, _ = js(c, "return document.getElementById('gwa').getBoundingClientRect().toJSON()")
    r = c.send('Page.captureScreenshot', {'format': 'png',
        'clip': {'x': rect['x'], 'y': rect['top'], 'width': rect['width'], 'height': rect['height'], 'scale': 1}})
    open(path, 'wb').write(base64.b64decode(r['data']))
    return path

HARNESS = """
window.__GWA_QA=true;
try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))}catch(e){}
"""

def boot(c, dark=True, reduced=False):
    c.send('Page.addScriptToEvaluateOnNewDocument', {'source': HARNESS})
    if reduced:
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
    c.send('Page.navigate', {'url': BASE})
    for _ in range(40):
        v, _ = js(c, "return !!(window.HUB&&HUB.gymworkAnim&&HUB.gymworkAnim._pose)")
        if v: break
        time.sleep(0.5)
    assert v, 'no _pose hook'
    js(c, "window.__huberr=[];window.addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
          "window.addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+(e.reason&&e.reason.message||e.reason)));return 1")
    js(c, "window.__gateSkip=true;try{HUB.auth.close()}catch(e){};"
          "var sp=document.getElementById('splash');if(sp)sp.remove();"
          "var w=document.getElementById('wlcmHost');if(w)w.remove();return 1")
    js(c, "document.body.className=%s;document.body.innerHTML='<div id=\"gwa\" style=\"width:390px\"></div>';return 1" % ('"dark"' if dark else "''"))
    time.sleep(1.0)  # let the app's async theme pass settle so bg is consistent
    js(c, """window.gwaShow=function(id,pos,frac){var host=document.getElementById('gwa');
HUB.gymworkAnim.destroy(host);HUB.gymworkAnim.render(host,id,{mode:'full'});
var st=host._gwa,tm=st.def.tempo||{ecc:2,pauseB:.5,conc:1.5,pauseT:.5};
var T=tm.ecc+tm.pauseB+tm.conc+tm.pauseT,f;
if(frac!==undefined)f=frac;
else if(pos==='top')f=0;
else if(pos==='bottom')f=(tm.ecc+tm.pauseB/2)/T;
else f=(tm.ecc+tm.pauseB+tm.conc/2)/T;
HUB.gymworkAnim._pose(host,f);return {id:id,pos:pos,frac:f,T:T,view:st.view,eq:st.def.equipment,anim:st.animate};};
window.gwaThumb=function(id){var host=document.getElementById('gwa');
HUB.gymworkAnim.destroy(host);HUB.gymworkAnim.render(host,id,{mode:'thumb'});return 1;};return 1""")
    v, _ = js(c, "return HUB.gymworkAnim.EXERCISES")
    return v

def main():
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    only = sys.argv[2] if len(sys.argv) > 2 else None
    if which == 'reduced':
        # launch with emulated reduced motion BEFORE load
        proc, c = launch()
        try:
            boot(c, reduced=True)
            v, _ = js(c, "return gwaShow('deadlift','mid')")
            print('reduced show:', v)
            v2, _ = js(c, "return {anim:document.getElementById('gwa')._gwa.animate,"
                          "running:document.getElementById('gwa')._gwa.running}")
            print('reduced anim state:', v2)
            p = shot_el(c, os.path.join(QA, 'gw2-reduced-deadlift.png'))
            print('shot', p)
        finally:
            proc.terminate()
        return
    proc, c = launch()
    fails = []
    try:
        ids = boot(c)
        print('EXERCISES:', ids)
        if which in ('all', 'frames'):
            ids2 = [i for i in ids if (not only or i == only)]
            for i, id_ in enumerate(ids2):
                for pos in ('top', 'bottom', 'mid'):
                    v, ex = js(c, "return gwaShow(%s,%s)" % (json.dumps(id_), json.dumps(pos)))
                    if ex: fails.append((id_, pos, 'JSERR')); print('JSERR', id_, pos, ex); continue
                    p = shot_el(c, os.path.join(QA, 'gw2-%s-%s.png' % (id_, pos)))
                    print('shot', p, v)
            # walking-lunge alt variant (second loop, mid-ecc)
            v, _ = js(c, "return gwaShow('walking-lunge','mid',1.5625)")
            p = shot_el(c, os.path.join(QA, 'gw2-walking-lunge-alt.png'))
            print('shot', p, v)
        if which in ('all', 'thumbs'):
            for id_ in ids:
                js(c, "gwaThumb(%s)" % json.dumps(id_))
                p = shot_el(c, os.path.join(QA, 'gw2-thumb-%s.png' % id_))
                print('thumb', p)
        if which in ('all', 'light'):
            js(c, "document.body.className='';return 1")
            for id_ in ('deadlift', 'face-pull', 'walking-lunge'):
                v, _ = js(c, "return gwaShow(%s,'mid')" % json.dumps(id_))
                p = shot_el(c, os.path.join(QA, 'gw2-light-%s.png' % id_))
                print('light', p, v)
        if which in ('all', 'errors'):
            err, _ = js(c, "return (window.__huberr||[]).slice(0,12)")
            print('ERRORS:', err)
        print('FAILS:', fails)
    finally:
        proc.terminate()

main()
