#!/usr/bin/env python3
"""QA: contextual subject + appointment clay icons on Home board."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9451
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
        '--user-data-dir=/tmp/hubqa-prof2', '--hide-scrollbars', '--allow-file-access-from-files', 'about:blank'],
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
        # seed classes with varied subjects + appointments with varied titles
        js("""var now=new Date();
        function hm(a){var d=new Date(now.getTime()+a*60000);return d.getHours()+':'+String(d.getMinutes()).padStart(2,'0');}
        HUB.store.state.profile.audience='student';
        HUB.store.state.classes=[];
        var subs=['Mathematics','Biology 101','Chemistry Lab','Physics II','Computer Science','English Literature','World History','Spanish','Music Theory','General Science','Art Class','Robotics Club'];
        subs.forEach(function(s,i){HUB.classes.addClass({subject:s,room:'R'+(101+i),days:[(now.getDay()+1)%7],start:hm(60*(i+1)),end:''});});
        HUB.store.state.appointments=[];HUB.store.state.apptFires=[];
        function isoAdd(min){var d=new Date(now.getTime()+min*60000);return [d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'), d.getHours()+':'+String(d.getMinutes()).padStart(2,'0')];}
        var ts=[['Doctor visit',120],['Dentist appointment',180],['Car service',240],['Birthday party',300],['Lunch with mom',360],['Gym session',420],['Pick up package',480]];
        ts.forEach(function(t){var d=isoAdd(t[1]);HUB.appts.addAppt({title:t[0],date:d[0],time:d[1],remind:true});});
        HUB.views.home.render(document.getElementById('view-home'));""")
        time.sleep(3)
        rows = js("(()=>{return Array.from(document.querySelectorAll('#classCard .crow .csubj')).map(e=>{var i=e.querySelector('[data-icon]');return e.textContent.trim().slice(0,24)+'|'+(i?i.getAttribute('data-icon'):'NONE')})})()")
        exp = {'Mathematics':'subj-math','Biology 101':'subj-bio','Chemistry Lab':'subj-chem','Physics II':'subj-physics',
               'Computer Science':'subj-computer','English Literature':'subj-english','World History':'subj-history',
               'Spanish':'subj-language','Music Theory':'subj-music','General Science':'subj-science',
               'Art Class':'ev-art','Robotics Club':'ev-study'}
        ok_all = True
        for r in rows:
            name, icon = r.split('|')
            want = exp.get(name)
            if want != icon:
                print('  ROW MISMATCH:', repr(name), 'got', icon, 'want', want); ok_all = False
        note(ok_all and len(rows) >= 12, 'class rows show matching subject icons', 'rows=%d' % len(rows))
        arows = js("(()=>{return Array.from(document.querySelectorAll('#apptCard .crow .csubj')).map(e=>{var i=e.querySelector('[data-icon],.appt-fb');var n=i?(i.getAttribute('data-icon')||'appt-fb'):null;return e.textContent.trim().slice(0,24)+'|'+(n||'NONE')})})()")
        aexp = {'Doctor visit':'appt-medical','Dentist appointment':'appt-dental','Car service':'appt-car',
                'Birthday party':'ev-party','Lunch with mom':'ev-food','Gym session':'ev-sports','Pick up package':'appt-fb'}
        ok_a = True
        for r in arows:
            name, icon = r.split('|')
            want = aexp.get(name)
            if want != icon:
                print('  APPT MISMATCH:', repr(name), 'got', icon, 'want', want); ok_a = False
        note(ok_a and len(arows) == 7, 'appointment rows show matching icons', 'rows=%d' % len(arows))
        # no broken images (onerror fallback would replace img with .ico-fb span)
        broken = js("document.querySelectorAll('.subj-ico .ico-fb, .appt-ico .ico-fb').length")
        note(broken == 0, 'no broken subject/appt icon images', 'broken=%s' % broken)
        note(not js("window.__loaderr.splice(0).length"), 'no console errors after render', '')
        shot('subj-appt-icons')
        print('CHECKS:', sum(checks), '/', len(checks))
    finally:
        proc.terminate()
main()
