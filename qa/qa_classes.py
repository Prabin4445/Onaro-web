#!/usr/bin/env python3
"""QA: multi-class schedule card with live HH:MM:SS timers."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9446
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []
def note(ok, label, detail=''):
    checks.append(bool(ok)); print(('PASS' if ok else 'FAIL'), label, detail)
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
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=414,900',
        '--user-data-dir=/tmp/hubqc-prof', '--hide-scrollbars', '--allow-file-access-from-files', 'about:blank'],
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
        c.send('Page.addScriptToEvaluateOnNewDocument',
               {'source': "window.__loaderr=[];addEventListener('error',e=>__loaderr.push(e.message));"})
        c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        def js(expr):
            r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
            res = (r or {}).get('result', {}); return res.get('value')
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data']))
        note(not js("window.__loaderr.splice(0).length"), 'no load errors', '')
        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(6)
        # seed 3 classes across different days/times
        js("""var p=HUB.store.state.profile; p.name='QA'; p.campus='Test Campus'; HUB.store.save();
             HUB.store.state.classes=[]; HUB.store.state.classFires=[];
             var now=new Date();
             function hm(addMin){var d=new Date(now.getTime()+addMin*60000);return d.getHours()+':'+String(d.getMinutes()).padStart(2,'0');}
             var today=now.getDay(), tomorrow=(now.getDay()+1)%7, day2=(now.getDay()+2)%7;
             HUB.classes.addClass({subject:'Math 201',room:'118',days:[tomorrow],start:hm(90),end:'',sample:true});
             HUB.classes.addClass({subject:'Physics 101',room:'204',days:[today],start:hm(45),end:''});
             HUB.classes.addClass({subject:'Chemistry 110',room:'',days:[day2],start:'10:00',end:''});
             HUB.showTab('home');""")
        time.sleep(4)
        rows = js("document.querySelectorAll('#classCard .crow').length")
        note(rows == 3, 'all 3 classes shown as rows', 'rows='+str(rows))
        timers = js("[...document.querySelectorAll('#classCard .ctimer')].map(e=>e.textContent)")
        import re
        ok_fmt = timers and all(re.match(r'^\d{2,}:\d{2}:\d{2}$', x) for x in timers)
        note(ok_fmt, 'each row has HH:MM:SS timer', str(timers))
        badge = js("(()=>{const b=document.querySelector('#classCard .cupnext');return b?b.textContent:'NO BADGE'})()")
        note('Up next' in (badge or ''), 'first row tagged UP NEXT', badge)
        title = js("(()=>{const h=document.querySelector('#classCard h3');return h?h.textContent:'NO TITLE'})()")
        note('Your classes' in (title or ''), 'card titled Your classes', title)
        # live ticking: sample timer twice, 2.2s apart -> seconds decrease
        t1 = js("document.querySelector('#classCard .ctimer').textContent")
        time.sleep(2.2)
        t2 = js("document.querySelector('#classCard .ctimer').textContent")
        note(t1 != t2, 'timer ticks every second', t1+' -> '+t2)
        # fmtHMS unit checks
        note(js("HUB.classes.fmtHMS(3723000)") == '01:02:03', 'fmtHMS 1h2m3s', '')
        note(js("HUB.classes.fmtHMS(90000)") == '00:01:30', 'fmtHMS 90s', '')
        # sorted soonest-first
        order = js("HUB.classes.allUpcoming(Date.now()).map(u=>u.cls.subject).join(',')")
        note(order == 'Physics 101,Math 201,Chemistry 110', 'rows sorted soonest-first', order)
        # live-now row: add a class starting 1 min ago, ending later
        js("""var now2=new Date();
             function hm2(addMin){var d=new Date(now2.getTime()+addMin*60000);return d.getHours()+':'+String(d.getMinutes()).padStart(2,'0');}
             HUB.classes.addClass({subject:'Biology 105',room:'12',days:[now2.getDay()],start:hm2(-1),end:hm2(50)});
             HUB.views.home.render(document.getElementById('view-home'));""")
        time.sleep(2)
        live = js("(()=>{const e=document.querySelector('#classCard .clive');return e?e.textContent:'NO LIVE'})()")
        note('Live now' in live, 'in-session class shows Live now', live)
        rows2 = js("document.querySelectorAll('#classCard .crow').length")
        note(rows2 == 4, '4 rows incl. live class', 'rows='+str(rows2))
        shot('classes-card')
        js("document.body.classList.add('dark')"); time.sleep(1)
        shot('classes-card-dark')
        note(not js("window.__loaderr.splice(0).length"), 'no errors after all flows', '')
        print('RESULT:', 'ALL PASS' if all(checks) else 'FAILURES')
    finally:
        proc.terminate()
main()
