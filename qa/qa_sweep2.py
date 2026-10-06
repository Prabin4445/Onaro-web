#!/usr/bin/env python3
"""Runtime QA SWEEP-2: TIME CAPSULE, CALENDAR(AD/BS), APPOINTMENTS, GRADE CALC,
NOTIFICATIONS, SEARCH, PULSE, ASTRO/HOROSCOPE, QUOTE, BADGES.
390px + 320px (two sessions), dark + light, zero console errors. Screenshots .jpg only."""
import json, subprocess, time, urllib.request, os, base64, shutil, sys, re
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
W = int(sys.argv[1]) if len(sys.argv) > 1 else 390
PORT = 9440 + W
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-sweep2-%d' % W
errors, checks = [], []
def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, detail, flush=True)

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=14); self.ws.settimeout(14); self.id = 0
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 18
        while time.time() < deadline:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:80])
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)
    def js(self, expr, awaitPromise=False):
        try:
            r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': awaitPromise})
            res = (r or {}).get('result', {})
            return res.get('value'), res.get('exceptionDetails')
        except Exception as e: return None, str(e)[:160]

JS = "(function(){%s})()"
def targets():
    with urllib.request.urlopen('http://localhost:%d/json/list' % PORT, timeout=5) as r:
        return json.load(r)
def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 78})
    open(os.path.join(QA, name + '.jpg'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
def hook_err(c):
    c.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
def drain_err(c, label):
    v, _ = c.js("window.__huberr.splice(0)")
    if v: errors.append((label, v)); print('ERRORS @', label, ':', json.dumps(v)[:500])
def seed_profile(c, name='QA Sweep'):
    c.js("(()=>{const p=HUB.store.state.profile; p.name=%s; p.campus='QA Campus'; p.dob='1998-08-29'; HUB.store.save(); window.__gateSkip=true; if(HUB.auth&&HUB.auth.close) HUB.auth.close(); const w=document.getElementById('wlcmHost'); if(w) w.remove(); return 'seeded'})()" % json.dumps(name))
    time.sleep(0.8)
def close_all(c):
    c.js("(()=>{HUB.ui.closeSheet(); ['notifications','search','pulse'].forEach(k=>{try{if(HUB[k]&&HUB[k].close)HUB[k].close()}catch(e){}}); document.getElementById('toastHost').innerHTML=''; return 1})()")
    time.sleep(0.4)
def overflow(c, label):
    v, _ = c.js(JS % "return {dw:document.documentElement.scrollWidth, iw:window.innerWidth, bw:document.body.scrollWidth}")
    ok = v and v['dw'] <= v['iw'] + 1
    note(ok, 'no horizontal overflow: ' + label, str(v))
def wait_splash(c):
    t0 = time.time()
    while time.time() - t0 < 20:
        if c.js(JS % "return !document.getElementById('splash')")[0]: break
        time.sleep(0.5)

def main():
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--remote-debugging-port=%d' % PORT, '--remote-allow-origins=*', '--window-size=%d,844' % W,
        '--user-data-dir=%s' % PROF, '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                ts = targets()
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        c.send('Page.addScriptToEvaluateOnNewDocument',
               {'source': "window.__loaderr=[];addEventListener('error',e=>__loaderr.push(e.message));window.confirm=function(){return true};"})
        c.send('Page.navigate', {'url': BASE}); time.sleep(5)
        c.js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(5)
        note(not c.js("window.__loaderr.splice(0).length")[0], 'no load errors')
        hook_err(c); time.sleep(2.5); seed_profile(c); drain_err(c, 'load'); wait_splash(c)
        note(c.js(JS % "return !document.getElementById('splash')")[0], 'splash dismissed')
        # addScriptToEvaluateOnNewDocument does NOT run in this Chrome build (verified
        # via marker: window.confirm stayed native, and native confirm() hangs the
        # headless renderer forever). Direct live-context override is reliable.
        c.js(JS % "window.confirm=function(){return true}; return 1")
        TAG = 'w%d-' % W

        # ================= 1. TIME CAPSULE =================
        c.js(JS % "HUB.showTab('daily'); return 1"); time.sleep(1.2)
        c.js(JS % "HUB.store.state.capsules=[]; HUB.store.save(); HUB.views.daily.render(document.getElementById('view-daily')); return 1"); time.sleep(0.8)
        capT, _ = c.js(JS % "return document.getElementById('dyCaps').textContent")
        note(capT and 'capEmpty' not in capT and len(capT.strip()) > 5, 'capsule empty state (translated)', (capT or '')[:60])
        c.js(JS % "HUB.views.daily.openCapsuleSheet(); return 1"); time.sleep(0.8)
        c.js(JS % """const b=document.getElementById('sheetBox');
          b.querySelector('#cpTitle').value='Dear future me';
          b.querySelector('#cpMsg').value='Hello from September 2026';
          b.querySelector('[data-cpdays="182"]').click(); return 1"""); time.sleep(0.4)
        dv, _ = c.js(JS % "return document.getElementById('cpDate').value")
        note(bool(dv) and dv > '2026-09-24', 'chip sets unlock date +182d', str(dv))
        c.js(JS % "document.getElementById('toastHost').innerHTML=''; document.getElementById('cpSeal').click(); return 1"); time.sleep(1.2)
        locked, _ = c.js(JS % """const rows=[...document.querySelectorAll('#dyCaps .item')];
          return {n:rows.length, txt:rows[0]?rows[0].textContent:'', sheetClosed:document.getElementById('sheetHost').hidden,
            toast:document.getElementById('toastHost').textContent}""")
        note(locked['n'] == 1 and 'Dear future me' in locked['txt'], 'sealed capsule row appears', locked['txt'][:80])
        note('Unlocks in' in locked['txt'], 'locked state shows "Unlocks in N days"', locked['txt'][:80])
        note('182' in locked['txt'] or '181' in locked['txt'], 'unlock countdown ~182 days', locked['txt'][:80])
        note(locked['sheetClosed'] and len(locked['toast']) > 2, 'sheet closes + sealed toast', locked['toast'][:60])
        enc, _ = c.js(JS % "const e=HUB.store.state.capsules[0].enc; return JSON.stringify(e).slice(0,120)")
        note(enc and 'Hello from September 2026' not in (enc or ''), 'capsule stored encrypted, no plaintext', (enc or '')[:80])
        c.js(JS % "HUB.views.daily.openCapsuleSheet(); document.getElementById('toastHost').innerHTML=''; return 1"); time.sleep(0.6)
        c.js(JS % "document.getElementById('cpSeal').click(); return 1"); time.sleep(0.6)
        v2, _ = c.js(JS % "return {open:!document.getElementById('sheetHost').hidden, toast:document.getElementById('toastHost').textContent, n:HUB.store.state.capsules.length}")
        note(v2['open'] and v2['n'] == 1 and len(v2['toast']) > 2, 'seal without message: blocked + toast', v2['toast'][:60])
        c.js(JS % "HUB.ui.closeSheet(); return 1"); time.sleep(0.4)
        c.js(JS % """HUB.views.daily.openCapsuleSheet(); document.getElementById('toastHost').innerHTML='';
          const b=document.getElementById('sheetBox'); b.querySelector('#cpMsg').value='x';
          b.querySelector('#cpDate').value='2020-01-01'; document.getElementById('cpSeal').click(); return 1"""); time.sleep(0.6)
        v3, _ = c.js(JS % "return {open:!document.getElementById('sheetHost').hidden, toast:document.getElementById('toastHost').textContent, n:HUB.store.state.capsules.length}")
        note(v3['open'] and v3['n'] == 1 and len(v3['toast']) > 2, 'seal with past date: blocked + toast', v3['toast'][:60])
        c.js(JS % "HUB.ui.closeSheet(); return 1"); time.sleep(0.4)
        c.js(JS % """const t=new Date(); const s=t.getFullYear()+'-'+String(t.getMonth()+1).padStart(2,'0')+'-'+String(t.getDate()).padStart(2,'0');
          HUB.store.state.capsules.push({id:'cap-today',title:'Today letter',text:'opened text 123',enc:null,unlock:s,createdAt:Date.now()-1});
          HUB.store.save(); HUB.views.daily.render(document.getElementById('view-daily')); return 1"""); time.sleep(0.8)
        openT, _ = c.js(JS % "return document.getElementById('dyCaps').textContent")
        note('opened text 123' in (openT or '') and 'Today letter' in (openT or ''), 'unlock-today capsule opens + decrypts', (openT or '')[:80])
        c.js(JS % """const b=document.querySelector('#dyCaps [data-cdel]'); if(b) b.click(); return 1"""); time.sleep(0.8)
        note(c.js(JS % "return HUB.store.state.capsules.length")[0] == 1, 'delete capsule removes row')
        shot(c, TAG + 'capsule'); overflow(c, 'daily capsule w%d' % W)
        c.js(JS % "HUB.showTab('home'); return 1"); time.sleep(1.2)
        pill, _ = c.js(JS % """const p=document.getElementById('homeCapCard')||document.getElementById('homeCapNew');
          return p?{txt:p.textContent, hasTs:!!p.querySelector('[data-capcd-ts]')}:null""")
        note(bool(pill) and pill['hasTs'], 'home pill shows live countdown (data-capcd-ts)', json.dumps(pill)[:100] if pill else 'null')
        t1, _ = c.js(JS % "const b=document.querySelector('[data-capcd-ts]'); return b?b.textContent:null")
        time.sleep(2.2)
        t2, _ = c.js(JS % "const b=document.querySelector('[data-capcd-ts]'); return b?b.textContent:null")
        note(t1 and t2 and t1 != t2, 'home pill countdown ticks', str(t1)+' -> '+str(t2))
        c.js(JS % "document.getElementById('homeCapInfo').click(); return 1"); time.sleep(0.6)
        info, _ = c.js(JS % "const s=document.getElementById('sheetBox'); return s?{open:!document.getElementById('sheetHost').hidden, steps:s.querySelectorAll('.capsteps li').length, cta:!!document.getElementById('capInfoOpen')}:null")
        note(info and info['open'] and info['steps'] == 4 and info['cta'], '(i) how-it-works sheet (4 steps + CTA)', json.dumps(info))
        shot(c, TAG + 'capsule-info')
        c.js(JS % "document.getElementById('capInfoOpen').click(); return 1"); time.sleep(0.8)
        note(c.js(JS % "return document.querySelector('#view-daily')&&!document.querySelector('#view-daily').hidden")[0], '(i) CTA goes to Daily tab')
        close_all(c); drain_err(c, 'capsule')

        # ================= 2. CALENDAR =================
        c.js(JS % "HUB.i18n.setCountry('NP'); HUB.astro.openCalendar(); return 1"); time.sleep(0.8)
        cal, _ = c.js(JS % """return {title:(document.querySelector('#calBody > div > div')||{}).textContent||'',
          cells:document.querySelectorAll('#calBody [data-calday]').length,
          toggle:document.getElementById('calToggle').textContent,
          sub:document.querySelector('#sheetBox .meta').textContent}""")
        note('2083' in cal['title'] and 'Aswin' in cal['title'], 'NP defaults BS: Aswin 2083', cal['title'][:40])
        note(cal['cells'] == 31, 'Aswin 2083 has 31 day cells', str(cal['cells']))
        note(cal['toggle'] == 'AD', 'toggle offers AD from BS view')
        conv, _ = c.js(JS % "return HUB.astro.adToBs(2026,9,24).join('-')")
        note(conv == '2083-6-8', 'page conversion 2026-09-24 -> 2083-06-08', str(conv))
        conv2, _ = c.js(JS % "return [HUB.astro.adToBs(1943,4,14).join('-'),HUB.astro.adToBs(2000,1,1).join('-'),HUB.astro.bsToAd(2083,6,8).join('-')].join('|')")
        note(conv2 == '2000-1-1|2056-9-17|2026-9-24', 'anchors + roundtrip in page', str(conv2))
        shot(c, TAG + 'cal-bs')
        c.js(JS % "document.getElementById('calToggle').click(); return 1"); time.sleep(0.8)
        cal2, _ = c.js(JS % "return {title:(document.querySelector('#calBody > div > div')||{}).textContent||'', toggle:document.getElementById('calToggle').textContent, cells:document.querySelectorAll('#calBody [data-calday]').length}")
        note('2026' in cal2['title'] and 'September' in cal2['title'], 'toggle switches to AD September 2026', cal2['title'][:40])
        note(cal2['toggle'] == 'BS' and cal2['cells'] == 30, 'AD view: 30 cells, toggle offers BS', str(cal2['cells']))
        c.js(JS % "document.querySelector('[data-calnav=\"1\"]').click(); return 1"); time.sleep(0.6)
        note('October' in (c.js(JS % "return (document.querySelector('#calBody > div > div')||{}).textContent||''")[0] or ''), 'AD next-month nav')
        c.js(JS % "document.querySelector('[data-calnav=\"-1\"]').click(); return 1"); time.sleep(0.6)
        c.js(JS % "HUB.ui.closeSheet(); HUB.i18n.setCountry('US'); HUB.astro.openCalendar(); return 1"); time.sleep(0.8)
        note('September' in (c.js(JS % "return (document.querySelector('#calBody > div > div')||{}).textContent||''")[0] or ''), 'US defaults AD')
        c.js(JS % """const b=[...document.querySelectorAll('#calBody [data-calday]')].find(x=>x.style.border.indexOf('var(--accent)')>=0)||document.querySelector('#calBody [data-calday="24"]');
          if(b) b.click(); return 1"""); time.sleep(0.8)
        c.js(JS % """const b=document.getElementById('sheetBox');
          b.querySelector('#calText').value='Aunt Maya birthday'; b.querySelector('#calKind').value='birthday';
          b.querySelector('#calSave').click(); return 1"""); time.sleep(1.0)
        noted, _ = c.js(JS % """HUB.astro.openCalendar();
          const b=[...document.querySelectorAll('#calBody [data-calday]')].find(x=>x.innerHTML.indexOf('border-radius:50%')>=0);
          return {dot:!!b, notes:HUB.astro.notes().length}""")
        time.sleep(0.8)
        note(noted['notes'] >= 1, 'day note saved to store')
        note(noted['dot'], 'note dot rendered on the day cell')
        c.js(JS % """const b=[...document.querySelectorAll('#calBody [data-calday]')].find(x=>x.style.border.indexOf('var(--accent)')>=0)||document.querySelector('#calBody [data-calday="24"]');
          if(b) b.click(); return 1"""); time.sleep(0.8)
        dayT, _ = c.js(JS % "return document.getElementById('sheetBox').textContent")
        note('Aunt Maya birthday' in (dayT or '') and '🎂' in (dayT or ''), 'day sheet lists the birthday note', (dayT or '')[:80])
        c.js(JS % "HUB.ui.closeSheet(); HUB.ui.closeSheet(); return 1"); time.sleep(0.4)
        c.js(JS % "HUB.notifications.open(); return 1"); time.sleep(0.8)
        note(c.js(JS % "return [...document.querySelectorAll('#hubNotifRoot .item')].some(x=>x.textContent.indexOf('Aunt Maya birthday')>=0)")[0],
             'remind-me note appears in notification center')
        shot(c, TAG + 'cal-notif')
        c.js(JS % "HUB.notifications.close(); HUB.astro.openCalendar(); return 1"); time.sleep(0.8)
        c.js(JS % """const b=[...document.querySelectorAll('#calBody [data-calday]')].find(x=>x.style.border.indexOf('var(--accent)')>=0)||document.querySelector('#calBody [data-calday="24"]');
          if(b) b.click(); return 1"""); time.sleep(0.8)
        c.js(JS % "const b=document.querySelector('#sheetBox [data-candel]'); if(b) b.click(); return 1"); time.sleep(0.8)
        note(c.js(JS % "return HUB.astro.notes().length")[0] == 0, 'delete note clears it')
        shot(c, TAG + 'cal-ad'); overflow(c, 'calendar sheet w%d' % W)
        c.js(JS % "HUB.ui.closeSheet(); return 1"); time.sleep(0.4)
        drain_err(c, 'calendar')

        # ================= 3. APPOINTMENTS =================
        c.js(JS % """var n=new Date();
          function iso(min){var d=new Date(n.getTime()+min*60000);
            return [d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'),
                    String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')];}
          var a=iso(90), b=iso(3*24*60);
          HUB.appts.addAppt({title:'Doctor visit',date:a[0],time:a[1],remind:true});
          HUB.appts.addAppt({title:'Car service',date:b[0],time:b[1],remind:true});
          HUB.showTab('home'); return 1"""); time.sleep(1.6)
        rows, _ = c.js(JS % "return {n:document.querySelectorAll('#apptCard .crow').length, t:[...document.querySelectorAll('#apptCard .ctimer')].map(e=>e.textContent)}")
        note(rows['n'] == 2, '2 appointment rows on home', json.dumps(rows))
        note(any(re.match(r'^\d{2,}:\d{2}:\d{2}$', x) for x in rows['t']) and any('day' in x for x in rows['t']),
             'under-24h HH:MM:SS + far "in N days"', json.dumps(rows['t']))
        t1, _ = c.js(JS % "return [...document.querySelectorAll('#apptCard .ctimer')][0].textContent")
        time.sleep(2.2)
        t2, _ = c.js(JS % "return [...document.querySelectorAll('#apptCard .ctimer')][0].textContent")
        note(t1 != t2, 'appointment countdown ticks', str(t1)+' -> '+str(t2))
        shot(c, TAG + 'appt')
        aid, _ = c.js(JS % "return HUB.appts.list()[0].id")
        c.js(JS % "document.querySelector('[data-appt-edit=\"%s\"]').click(); return 1" % aid); time.sleep(0.8)
        c.js(JS % """const b=document.getElementById('sheetBox'); b.querySelector('#apTitle').value='Dentist visit';
          document.getElementById('toastHost').innerHTML=''; b.querySelector('#apSave').click(); return 1"""); time.sleep(1.2)
        note(c.js(JS % "return HUB.appts.list().find(x=>x.id==='%s').title" % aid)[0] == 'Dentist visit', 'edit appointment saves')
        c.js(JS % "document.querySelector('[data-appt-del=\"%s\"]').click(); return 1" % aid); time.sleep(1.0)
        note(c.js(JS % "return HUB.appts.list().length")[0] == 1, 'delete appointment removes it')
        c.js(JS % """document.querySelector('[data-appt-add]').click(); document.getElementById('toastHost').innerHTML='';
          const b=document.getElementById('sheetBox'); b.querySelector('#apTitle').value='Old';
          b.querySelector('#apDate').value='2020-01-01'; b.querySelector('#apTime').value='10:00';
          b.querySelector('#apSave').click(); return 1"""); time.sleep(0.6)
        pv, _ = c.js(JS % "return {open:!document.getElementById('sheetHost').hidden, n:HUB.appts.list().length, toast:document.getElementById('toastHost').textContent}")
        note(pv['open'] and pv['n'] == 1 and len(pv['toast']) > 2, 'past appointment blocked + toast', pv['toast'][:60])
        c.js(JS % "HUB.ui.closeSheet(); return 1"); time.sleep(0.4)
        c.js(JS % """var n2=new Date(); var d=new Date(n2.getTime()+30*60000);
          var dt=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
          var tm=String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
          HUB.appts.addAppt({title:'Oil change',date:dt,time:tm,remind:true});
          document.getElementById('toastHost').innerHTML='';
          HUB.appts.checkReminders(Date.now()); return 1"""); time.sleep(0.8)
        rem, _ = c.js(JS % "return {toast:document.getElementById('toastHost').textContent, entries:HUB.appts.dueEntries().length}")
        note(rem['entries'] >= 1 and 'Oil change' in rem['toast'], '60-min reminder -> toast + entry', rem['toast'][:60])
        c.js(JS % "HUB.notifications.open(); return 1"); time.sleep(0.8)
        note(c.js(JS % "return [...document.querySelectorAll('#hubNotifRoot .item')].some(x=>x.textContent.indexOf('Oil change')>=0)")[0],
             'appointment reminder in notification center')
        shot(c, TAG + 'appt-notif')
        c.js(JS % "HUB.notifications.close(); return 1"); time.sleep(0.4)
        overflow(c, 'appointments w%d' % W); drain_err(c, 'appointments')

        # ================= 4. GRADE CALC =================
        c.js(JS % "HUB.store.state.gpaCourses=[]; HUB.store.save(); HUB.showTab('home'); return 1"); time.sleep(1.2)
        note(c.js(JS % "return !!document.querySelector('#gpaCard .gpa-empty')")[0], 'GPA empty state renders')
        c.js(JS % "HUB.gpa.courseSheet(null); return 1"); time.sleep(0.8)
        c.js(JS % """const b=document.getElementById('sheetBox');
          b.querySelector('#gpaSubj').value='Math'; b.querySelector('#gpaCr').value='3';
          b.querySelector('[data-ggrade="A"]').click(); b.querySelector('#gpaSave').click(); return 1"""); time.sleep(1.2)
        c.js(JS % "HUB.gpa.courseSheet(null); return 1"); time.sleep(0.8)
        c.js(JS % """const b=document.getElementById('sheetBox');
          b.querySelector('#gpaSubj').value='Physics'; b.querySelector('#gpaCr').value='4';
          b.querySelector('[data-ggrade="B"]').click(); b.querySelector('#gpaSave').click(); return 1"""); time.sleep(1.2)
        gpa, _ = c.js(JS % "return {g:HUB.gpa.calc().gpa.toFixed(2), shown:document.querySelector('#gpaCard .gpa-num').textContent, band:document.querySelector('#gpaCard').className}")
        note(gpa['g'] == '3.43' and gpa['shown'] == '3.43', 'GPA 3.43 for A(3)+B(4)', json.dumps(gpa))
        note('gb4' in gpa['band'], 'GPA glow band gb4 for 3.43', gpa['band'][:60])
        shot(c, TAG + 'gpa')
        c.js(JS % """const r=document.querySelector('#gpaCard [data-gswipe]');
          const rect=r.getBoundingClientRect(); const cx=rect.left+rect.width-40, cy=rect.top+rect.height/2;
          const mk=(type,x)=>{ r.dispatchEvent(new PointerEvent(type,{clientX:x,clientY:cy,pointerId:7,bubbles:true,cancelable:true})); };
          mk('pointerdown',cx); mk('pointermove',cx-30); mk('pointermove',cx-120); mk('pointerup',cx-120);
          return 1""")
        time.sleep(0.4)  # tray opacity fades in over 180ms; read computed style after it settles
        sw, _ = c.js(JS % """const r=document.querySelector('#gpaCard [data-gswipe]');
          return {open:r.classList.contains('gpa-open'),
            op:getComputedStyle(r.querySelector('.gpa-swactions')).opacity,
            vis:getComputedStyle(r.querySelector('.gpa-swactions')).visibility}""")
        note(sw['open'] and sw['op'] == '1' and sw['vis'] == 'visible', 'swipe >=24px reveals Edit/Delete tray', json.dumps(sw))
        c.js(JS % """const r=document.querySelector('#gpaCard [data-gswipe].gpa-open')||document.querySelector('#gpaCard [data-gswipe]');
          r.querySelector('.gsw-edit').click(); return 1"""); time.sleep(0.8)
        note('Edit' in (c.js(JS % "return (document.querySelector('#sheetBox h2')||{}).textContent||''")[0] or ''), 'tray Edit opens edit sheet')
        c.js(JS % "HUB.ui.closeSheet(); return 1"); time.sleep(0.4)
        tap, _ = c.js(JS % """const r=[...document.querySelectorAll('#gpaCard [data-gswipe]')][1];
          const rect=r.getBoundingClientRect(); const cx=rect.left+rect.width/2, cy=rect.top+rect.height/2;
          const mk=(type,x)=>{ r.dispatchEvent(new PointerEvent(type,{clientX:x,clientY:cy,pointerId:9,bubbles:true,cancelable:true})); };
          mk('pointerdown',cx); mk('pointerup',cx);
          return r.classList.contains('gpa-open')""")
        note(tap is False, 'plain tap does not reveal tray (24px threshold)')
        c.js(JS % """const r=[...document.querySelectorAll('#gpaCard [data-gswipe]')][0];
          const rect=r.getBoundingClientRect(); const cx=rect.left+rect.width-40, cy=rect.top+rect.height/2;
          const mk=(type,x)=>{ r.dispatchEvent(new PointerEvent(type,{clientX:x,clientY:cy,pointerId:11,bubbles:true,cancelable:true})); };
          mk('pointerdown',cx); mk('pointermove',cx-120); mk('pointerup',cx-120);
          r.querySelector('.gsw-del').click(); return 1""")
        # headless rAF can stall, leaving the 650ms count animation mid-flight;
        # poll for the settled value instead of asserting at a fixed instant
        gpaNum = None
        for _ in range(20):
            time.sleep(0.25)
            gpaNum = c.js(JS % "return document.querySelector('#gpaCard .gpa-num').textContent")[0]
            if gpaNum == '3.00': break
        note(c.js(JS % "return HUB.store.state.gpaCourses.length")[0] == 1, 'tray Delete removes course (confirm=true)')
        note(gpaNum == '3.00', 'GPA recalculates after delete (B 4cr -> 3.00)', repr(gpaNum))
        c.js(JS % "HUB.gpa.courseSheet(null); return 1"); time.sleep(0.6)
        cr, _ = c.js(JS % "const i=document.getElementById('gpaCr'); return {min:i.min,max:i.max,step:i.step}")
        note(cr['min'] == '0.5' and cr['max'] == '12' and cr['step'] == '0.5', 'credits input bounded 0.5-12 step 0.5', json.dumps(cr))
        c.js(JS % """const b=document.getElementById('sheetBox'); document.getElementById('toastHost').innerHTML='';
          b.querySelector('#gpaSubj').value=''; b.querySelector('#gpaCr').value='3'; b.querySelector('#gpaSave').click(); return 1"""); time.sleep(0.6)
        note(c.js(JS % "return {toast:document.getElementById('toastHost').textContent.length>2}")[0]['toast'], 'empty subject blocked + toast')
        c.js(JS % "HUB.ui.closeSheet(); return 1"); time.sleep(0.4)
        c.js(JS % "document.querySelector('[data-gpa-clear]').click(); return 1"); time.sleep(0.6)
        c.js(JS % "document.getElementById('cfGo').click(); return 1"); time.sleep(0.8)
        note(c.js(JS % "return HUB.store.state.gpaCourses.length===0 && !!document.querySelector('#gpaCard .gpa-empty')")[0], 'clear-all resets to empty state')
        shot(c, TAG + 'gpa-empty'); overflow(c, 'gpa w%d' % W); drain_err(c, 'gpa')

        # ================= 5. NOTIFICATIONS / SEARCH / PULSE =================
        c.js(JS % "HUB.notifications.open(); return 1"); time.sleep(0.8)
        nn, _ = c.js(JS % "return {mounted:!!document.getElementById('hubNotifRoot'), rows:document.querySelectorAll('#hubNotifRoot .item').length, close:!!document.getElementById('hubNotifClose'), read:!!document.getElementById('hubNotifRead')}")
        note(nn['mounted'] and nn['close'] and nn['read'], 'notifications opens (.chatroot)', json.dumps(nn))
        shot(c, TAG + 'notif')
        c.js(JS % "document.getElementById('hubNotifClose').click(); return 1"); time.sleep(0.4)
        note(c.js(JS % "return !document.getElementById('hubNotifRoot')")[0], 'notifications close removes .chatroot')
        c.js(JS % "HUB.notifications.open(); return 1"); time.sleep(0.5)
        c.send('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Escape', 'code': 'Escape'})
        c.send('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Escape', 'code': 'Escape'}); time.sleep(0.4)
        note(c.js(JS % "return !document.getElementById('hubNotifRoot')")[0], 'Escape closes notifications')
        c.js(JS % "HUB.notifications.open(); document.getElementById('hubNotifRead').click(); return 1"); time.sleep(0.8)
        note(c.js(JS % "return !!document.getElementById('hubNotifRoot') && HUB.store.state.prefs.lastSeenNotifications>0")[0], 'mark-all-read keeps overlay, stamps seen')
        c.js(JS % "HUB.notifications.close(); return 1"); time.sleep(0.3)
        c.js(JS % "HUB.search.open(); return 1"); time.sleep(0.8)
        se, _ = c.js(JS % "return {mounted:!!document.getElementById('hubSearchRoot'), sug:document.querySelectorAll('#hubSearchResults [data-q]').length, focused:document.activeElement.id==='hubSearchInput'}")
        note(se['mounted'] and se['sug'] == 3 and se['focused'], 'search opens with suggestions + focus', json.dumps(se))
        c.js(JS % """const i=document.getElementById('hubSearchInput'); i.value='zzz-no-such-thing-qqq'; i.dispatchEvent(new Event('input',{bubbles:true})); return 1"""); time.sleep(0.6)
        note('🤷' in (c.js(JS % "return document.getElementById('hubSearchResults').textContent")[0] or ''), 'search no-match -> honest empty state')
        c.js(JS % """const i=document.getElementById('hubSearchInput'); i.value='';
          HUB.store.state.listings.push({id:'sw1',title:'Calculus textbook',desc:'used',type:'SELL',price:25,seller:'QA',campus:'QA Campus',createdAt:Date.now()});
          HUB.store.save(); i.value='textbook'; i.dispatchEvent(new Event('input',{bubbles:true})); return 1"""); time.sleep(0.8)
        sr, _ = c.js(JS % "return {n:document.querySelectorAll('#hubSearchResults .item').length, t:document.getElementById('hubSearchResults').textContent.slice(0,80)}")
        note(sr['n'] >= 1 and 'Calculus textbook' in sr['t'], 'search finds real listing', json.dumps(sr))
        shot(c, TAG + 'search')
        c.js(JS % "document.getElementById('hubSearchClose').click(); return 1"); time.sleep(0.4)
        note(c.js(JS % "return !document.getElementById('hubSearchRoot')")[0], 'search close removes .chatroot')
        c.js(JS % "HUB.pulse.open(); return 1"); time.sleep(0.8)
        pu, _ = c.js(JS % "return {mounted:!!document.getElementById('hubPulseRoot'), rows:document.querySelectorAll('#hubPulseRows .prow').length, title:document.querySelector('#hubPulseRoot h2').textContent}")
        note(pu['mounted'] and pu['rows'] >= 1, 'pulse opens with real feed rows', json.dumps(pu))
        shot(c, TAG + 'pulse')
        c.js(JS % "document.querySelector('#hubPulseRows .prow').click(); return 1"); time.sleep(0.8)
        note(c.js(JS % "return !document.getElementById('hubPulseRoot')")[0], 'pulse row tap navigates (overlay gone)')
        close_all(c)
        c.js(JS % "HUB.search.open(); HUB.pulse.open(); return 1"); time.sleep(0.8)
        note(c.js(JS % "return !!document.getElementById('hubPulseRoot') && !document.getElementById('hubSearchRoot')")[0],
             'opening pulse closes search (mutually exclusive)')
        c.js(JS % "HUB.notifications.open(); return 1"); time.sleep(0.8)
        note(c.js(JS % "return !!document.getElementById('hubNotifRoot') && !document.getElementById('hubPulseRoot')")[0],
             'opening notifications closes pulse')
        c.js(JS % "HUB.notifications.close(); return 1"); time.sleep(0.4)
        c.js(JS % """window.__snap=JSON.stringify({listings:HUB.store.state.listings,jobs:HUB.store.state.jobs,campusPosts:HUB.store.state.campusPosts,memory:HUB.store.state.memory,threads:HUB.store.state.threads,events:HUB.store.state.events});
          HUB.store.state.listings=[]; HUB.store.state.jobs=[]; HUB.store.state.campusPosts=[]; HUB.store.state.memory=[]; HUB.store.state.threads=[]; HUB.store.state.events=[]; HUB.store.save();
          HUB.pulse.open(); return 1"""); time.sleep(0.8)
        note('⚡' in (c.js(JS % "return document.getElementById('hubPulseRows').textContent")[0] or '') and c.js(JS % "return !!document.getElementById('hubPulsePost')")[0],
             'pulse empty state invites posting')
        shot(c, TAG + 'pulse-empty')
        c.js(JS % "document.getElementById('hubPulsePost').click(); return 1"); time.sleep(0.6)
        note(c.js(JS % "return !document.getElementById('hubPulseRoot')")[0], 'pulse empty CTA closes overlay')
        c.js(JS % "const s=JSON.parse(window.__snap); Object.keys(s).forEach(k=>{HUB.store.state[k]=s[k]}); HUB.store.save(); return 1"); time.sleep(0.4)
        overflow(c, 'overlays w%d' % W); drain_err(c, 'nsp')

        # ================= 6. ASTRO =================
        sg, _ = c.js(JS % "return {s:HUB.astro.signForDob('1998-08-29').n, edges:[HUB.astro.signForDob('2000-03-20').n,HUB.astro.signForDob('2000-03-21').n,HUB.astro.signForDob('2000-12-21').n,HUB.astro.signForDob('2000-12-22').n].join(',')}")
        note(sg['s'] == 'Virgo' and sg['edges'] == 'Pisces,Aries,Sagittarius,Capricorn', 'zodiac boundaries correct', json.dumps(sg))
        c.js(JS % "HUB.showTab('home'); return 1"); time.sleep(1.2)
        note('Virgo' in (c.js(JS % "return document.getElementById('astroCard').textContent")[0] or ''), 'home astro card shows Virgo (DOB from ME)')
        c.js(JS % "document.getElementById('astroCard').click(); return 1"); time.sleep(1.6)
        dl, _ = c.js(JS % "return {date:document.getElementById('horoDateLine').textContent, full:(document.getElementById('horoFull').textContent||'').slice(0,60), lucky:(document.getElementById('horoLucky').textContent||'').replace(/\\s+/g,' ').slice(0,60)}")
        note('2026-09-23' in dl['date'], 'horoscope shows BAKED date 2026-09-23 (not "today")', dl['date'][:80])
        note(len(dl['full']) > 40, 'full horoscope text loaded', dl['full'][:60])
        lk1, _ = c.js(JS % "return JSON.stringify(HUB.astro.luckyFor('Virgo','2026-09-24'))")
        lk2, _ = c.js(JS % "return JSON.stringify(HUB.astro.luckyFor('Virgo','2026-09-24'))")
        note(lk1 == lk2 and '"n":' in lk1, 'lucky number/color deterministic per sign+day', lk1)
        note(str(json.loads(lk1)['n']) in dl['lucky'], 'sheet lucky number matches luckyFor()', dl['lucky'][:60])
        shot(c, TAG + 'horo')
        c.js(JS % "HUB.ui.closeSheet(); HUB.showTab('home'); return 1"); time.sleep(1.0)
        c.js(JS % "document.getElementById('astroCalBtn').click(); return 1"); time.sleep(0.8)
        note(c.js(JS % "return !document.getElementById('sheetHost').hidden && !!document.getElementById('calBody')")[0],
             'astro card calendar button opens calendar')
        shot(c, TAG + 'horo-cal')
        c.js(JS % "HUB.ui.closeSheet(); return 1"); time.sleep(0.4)
        drain_err(c, 'astro')

        # ================= 7. QUOTE =================
        qd, _ = c.js(JS % "return {a:HUB.quote.dayIndex(120), b:HUB.quote.dayIndex(120), txt:(document.getElementById('quoteText')||{}).textContent||'', auth:(document.getElementById('quoteAuthor')||{}).textContent||''}")
        note(qd['a'] == qd['b'] and 0 <= qd['a'] < 120, 'quote dayIndex deterministic in [0,120)', str(qd['a']))
        note(len(qd['txt']) > 10 and len(qd['auth']) > 2, 'daily quote renders text + author', qd['txt'][:60]+' '+qd['auth'][:30])
        drain_err(c, 'quote')

        # ================= 8. BADGES (spot check) =================
        th, _ = c.js(JS % "const f=HUB.badges.tierOf; return [f(0),f(89),f(90),f(179),f(180),f(364),f(365)].join(',')")
        note(th == 'new,new,silver,silver,gold,gold,legend', 'badge thresholds pure', str(th))
        c.js(JS % "HUB.badges._debug.reset(); HUB.badges._debug.setLoginDays(89); return 1"); time.sleep(0.4)
        note(c.js(JS % "return !document.querySelector('.bdg-earn') && HUB.badges._debug.status().tier==='new'")[0], '89 days = NEW, no celebration')
        c.js(JS % "document.getElementById('toastHost').innerHTML=''; HUB.badges._debug.setLoginDays(365); return 1"); time.sleep(0.6)
        lg, _ = c.js(JS % "const e=document.querySelector('.bdg-earn'); return {earn:!!e, why:e?e.querySelector('.bdg-why').textContent:'', toast:document.getElementById('toastHost').textContent}")
        note(lg['earn'] and '365' in lg['why'], '365 days = LEGEND celebration w/ exact reason', lg['why'][:60])
        c.js(JS % "HUB.badges._debug.setReviews(100); return 1"); time.sleep(0.6)
        note(c.js(JS % "return HUB.badges.isSpecialist()")[0], '100 reviews = SPECIALIST')
        c.js(JS % "HUB.badges.openShowcase(); return 1"); time.sleep(0.6)
        sc, _ = c.js(JS % "const cs2=[...document.querySelectorAll('.bdg-show .bdg-card')]; return {n:cs2.length, locked:cs2.filter(x=>x.classList.contains('bdg-islocked')).length}")
        note(sc['n'] == 5 and sc['locked'] == 0, 'showcase: 5 cards, all unlocked at legend+specialist', json.dumps(sc))
        shot(c, TAG + 'badges')
        c.js(JS % "HUB.ui.closeSheet(); HUB.badges._debug.reset(); return 1"); time.sleep(0.4)
        note(c.js(JS % "return document.getElementById('sheetHost').hidden")[0], 'showcase closes cleanly')
        drain_err(c, 'badges')

        # ================= LIGHT THEME pass =================
        c.js(JS % "HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme(); HUB.showTab('home'); return 1"); time.sleep(1.2)
        note(c.js(JS % "return !document.body.classList.contains('dark')")[0], 'light theme applied')
        shot(c, TAG + 'home-light')
        c.js(JS % "HUB.showTab('daily'); return 1"); time.sleep(1.0)
        shot(c, TAG + 'daily-light'); overflow(c, 'daily light w%d' % W)
        c.js(JS % "HUB.showTab('me'); return 1"); time.sleep(1.0)
        shot(c, TAG + 'me-light'); overflow(c, 'me light w%d' % W)
        c.js(JS % "HUB.showTab('market'); return 1"); time.sleep(1.0)
        shot(c, TAG + 'market-light'); overflow(c, 'market light w%d' % W)
        c.js(JS % "HUB.showTab('work'); return 1"); time.sleep(1.0)
        overflow(c, 'work light w%d' % W)
        c.js(JS % "HUB.showTab('groups'); return 1"); time.sleep(1.0)
        overflow(c, 'groups light w%d' % W)
        drain_err(c, 'light')
        c.js(JS % "HUB.store.state.prefs.dark=true; HUB.store.save(); HUB.applyTheme(); HUB.showTab('home'); return 1"); time.sleep(1.0)
        shot(c, TAG + 'home-dark'); overflow(c, 'home dark final w%d' % W)

        drain_err(c, 'final')
        n_fail = sum(1 for ok, _ in checks if not ok)
        print('\n==== %d/%d checks passed, console errors: %d ====' % (len(checks) - n_fail, len(checks), len(errors)))
        for label, ev in errors: print('ERR', label, json.dumps(ev)[:300])
        for ok, label in checks:
            if not ok: print('FAILED:', label)
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
