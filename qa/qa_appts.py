#!/usr/bin/env python3
"""QA: shifts mode + appointments card with countdowns + reminders."""
import json, subprocess, time, urllib.request, os, base64, re
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9448
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
        '--user-data-dir=/tmp/hubqa-prof', '--hide-scrollbars', '--allow-file-access-from-files', 'about:blank'],
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
        # --- community member: shifts mode ---
        js("""var p=HUB.store.state.profile; p.name='QA'; p.campus='Downtown'; p.audience='community';
              HUB.store.save(); HUB.store.state.classes=[]; HUB.store.state.appointments=[]; HUB.store.state.apptFires=[];
              var now=new Date(); function hm(a){var d=new Date(now.getTime()+a*60000);return d.getHours()+':'+String(d.getMinutes()).padStart(2,'0');}
              HUB.classes.addClass({subject:'Warehouse shift',room:'Main site',days:[(now.getDay()+1)%7],start:hm(600),end:''});
              HUB.showTab('home');""")
        time.sleep(3)
        title = js("(()=>{const h=document.querySelector('#classCard h3');return h?h.textContent:''})()")
        note('Your shifts' in title, 'community member sees "Your shifts"', title)
        note(js("HUB.classes.isShiftMode()")==True, 'isShiftMode true for community', '')
        # shift manage sheet labels
        js("HUB.classes.manageSheet()"); time.sleep(1)
        sheet = js("document.getElementById('sheetBox').textContent")
        note('Work shifts' in sheet and 'Shift name' in sheet, 'shift form labels', '')
        js("HUB.ui.closeSheet()")
        # --- student regression ---
        js("HUB.store.state.profile.audience='student'; HUB.store.save(); HUB.views.home.render(document.getElementById('view-home'));")
        time.sleep(2)
        title2 = js("(()=>{const h=document.querySelector('#classCard h3');return h?h.textContent:''})()")
        note('Your classes' in title2, 'student still sees "Your classes"', title2)
        js("HUB.store.state.profile.audience='community'; HUB.store.save(); HUB.views.home.render(document.getElementById('view-home'));")
        time.sleep(2)
        # --- appointments ---
        js("""var n2=new Date();
             function isoAdd(min){var d=new Date(n2.getTime()+min*60000);return [d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'), d.getHours()+':'+String(d.getMinutes()).padStart(2,'0')];}
             var a=isoAdd(90); HUB.appts.addAppt({title:'Doctor visit',date:a[0],time:a[1],remind:true});
             var b=isoAdd(3*24*60); HUB.appts.addAppt({title:'Car service',date:b[0],time:b[1],remind:true});
             HUB.views.home.render(document.getElementById('view-home'));""")
        time.sleep(2)
        rows = js("document.querySelectorAll('#apptCard .crow').length")
        note(rows == 2, '2 appointment rows on Home board', 'rows='+str(rows))
        atitle = js("(()=>{const h=document.querySelector('#apptCard h3');return h?h.textContent:''})()")
        note('Appointments' in atitle, 'card titled Appointments', atitle)
        timers = js("[...document.querySelectorAll('#apptCard .ctimer')].map(e=>e.textContent)")
        note(any(re.match(r'^\d{2,}:\d{2}:\d{2}$', x) for x in timers), 'near appointment has HH:MM:SS', str(timers))
        note(any('in 3 days' in x for x in timers), 'far appointment shows "in 3 days"', str(timers))
        t1 = js("[...document.querySelectorAll('#apptCard .ctimer')][0].textContent")
        time.sleep(2.2)
        t2 = js("[...document.querySelectorAll('#apptCard .ctimer')][0].textContent")
        note(t1 != t2, 'appointment timer ticks', t1+' -> '+t2)
        # edit
        aid = js("HUB.appts.list()[0].id")
        js("HUB.appts.formSheet('"+aid+"')"); time.sleep(1)
        ed = js("(()=>{const h=document.querySelector('#sheetBox h2');return h?h.textContent:''})()")
        note('Edit appointment' in ed, 'edit sheet opens', ed)
        js("""var b=document.getElementById('sheetBox'); b.querySelector('#apTitle').value='Dentist visit';
              b.querySelector('#apSave').click();""")
        time.sleep(1.5)
        note(js("HUB.appts.list().find(x=>x.id==='"+aid+"').title") == 'Dentist visit', 'edit saves', '')
        # delete
        js("HUB.appts.removeAppt(HUB.appts.list().find(x=>x.title==='Car service').id); HUB.views.home.render(document.getElementById('view-home'));")
        time.sleep(1.5)
        note(js("document.querySelectorAll('#apptCard .crow').length") == 1, 'delete removes row', '')
        # reminder fires -> notification center
        js("""var n3=new Date(); var d=new Date(n3.getTime()+30*60000);
              var dt=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
              var tm=d.getHours()+':'+String(d.getMinutes()).padStart(2,'0');
              HUB.appts.addAppt({title:'Oil change',date:dt,time:tm,remind:true});
              HUB.appts.checkReminders(Date.now());""")
        time.sleep(1)
        note(js("HUB.appts.dueEntries().length") >= 1, 'reminder fired into entries', '')
        notif = js("(()=>{try{return JSON.stringify(HUB.notifications.buildList().filter(n=>n.nid.indexOf('appt-')===0).map(n=>n.title))}catch(e){return 'ERR:'+e.message}})()")
        note('Oil change' in (notif or ''), 'reminder in notification center', (notif or '')[:80])
        shot('appts-card')
        js("document.body.classList.add('dark')"); time.sleep(1)
        shot('appts-card-dark')
        note(not js("window.__loaderr.splice(0).length"), 'no errors after all flows', '')
        print('RESULT:', 'ALL PASS' if all(checks) else 'FAILURES')
    finally:
        proc.terminate()
main()
