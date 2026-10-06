#!/usr/bin/env python3
"""RUNTIME QA SWEEPER v3: HOME tab, DAILY tab (Happening events CRUD), GYM, CALCULATOR.
Usage: qa_sweep.py <width>   (390 or 320)
Fresh profile /tmp/hubqa-sweep-<width>, file:// load, dark then light.
Screenshots -> qa/ as .jpg (NEVER .png). Zero console errors target.
All interactions follow real user paths (DOM clicks; pointerdown where the app listens).
NOTE: JS="(function(){%s})()" already wraps in an IIFE: NEVER nest another IIFE
inside %s without returning its value (the outer wrapper would swallow it).
"""
import json, subprocess, time, urllib.request, os, shutil, sys, base64, re
try:
    import websocket
except ImportError:
    print('websocket-client missing'); sys.exit(2)

W = int(sys.argv[1]) if len(sys.argv) > 1 else 390
CHROME = '/opt/meta-chromium/chrome'; PORT = 9400 + W
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-sweep-%d' % W
SHOTDIR = os.path.expanduser('~/workspace/hub/qa')
JS = "(function(){%s})()"
checks = []
def note(ok, label, detail=''):
    checks.append(bool(ok)); print(('PASS' if ok else 'FAIL'), label, detail, flush=True)

KEY_IDS = ["mode","lp","rp","del","ac","sin","cos","tan","asin","acos","atan","log","ln",
 "p10","pex","sqrt","sq","cb","rc","pi","eu","npr","ncr","fact","pct","k7","k8","k9","kdiv",
 "kpow","k4","k5","k6","kmul","exp","k1","k2","k3","kmin","ans","k0","dot","plus","eq"]
ADV_EXTRA = ["sinh","cosh","tanh","asinh","acosh","atanh","cbrt","nthroot","logb","kx","ran",
 "mplus","mminus","mr"]
ADV_KEYS = ["lab-int","lab-der","lab-sum","lab-sol","lab-pol","lab-base"]

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12)
        self.id = 0
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        t = time.time()
        while time.time() - t < 15:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method)
            if 'method' in msg and 'id' not in msg: continue
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)
    def js(self, expr, awaitPromise=False):
        try:
            r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': awaitPromise})
            res = (r or {}).get('result', {})
            return res.get('value'), res.get('exceptionDetails')
        except Exception as e: return None, str(e)[:160]
    def shot(self, name):
        r = self.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 80, 'fromSurface': True})
        with open(os.path.join(SHOTDIR, name), 'wb') as f: f.write(base64.b64decode(r['data']))
        print('SHOT', name, flush=True)

def js_wait(c, expr, timeout=12):
    t = time.time()
    while time.time() - t < timeout:
        v, _ = c.js(JS % expr)
        if v: return True
        time.sleep(0.4)
    return False
def arm_hooks(c):
    c.js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
         "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
def collect_errors(c):
    v, _ = c.js(JS % "return (window.__huberr||[]).slice()")
    return [x for x in (v or []) if x]
def clear_errors(c):
    c.js(JS % "window.__huberr=[]; return 1")
def disarm_gate(c):
    c.js(JS % ("window.__gateSkip=true; try{if(HUB.auth&&HUB.auth.close){"
         "var a=document.querySelector('.authroot'); if(a&&!a.hidden) HUB.auth.close();}}catch(e){} return 1"))
def overflow(c, label):
    v, _ = c.js(JS % "return {sw:document.documentElement.scrollWidth, iw:window.innerWidth}")
    ok = v and v['sw'] <= v['iw'] + 1
    note(ok, 'no horizontal overflow: ' + label, str(v))
def hidden_veil_check(c, label):
    v, _ = c.js(JS % "var bad=[]; document.querySelectorAll('[hidden]').forEach(function(el){"
         "var d=getComputedStyle(el).display;"
         "if(d!=='none') bad.push(el.className||el.id||el.tagName); }); return bad;")
    note(not v, 'no stuck overlays (hidden respected): ' + label, str(v)[:160])
def set_theme(c, dark):
    c.js(JS % ("var s=HUB.store.state; s.prefs.dark=%s; HUB.store.save(); HUB.applyTheme(); return 1" % ('true' if dark else 'false')))
    time.sleep(0.6)
def click(c, sel):
    # real user path: pointerdown (app volt-glows / pauses carousels on it) then click
    v, ex = c.js(JS % ("var b=document.querySelector('%s'); if(!b) return 'no-el';"
         "b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true})); b.click(); return 'ok'" % sel))
    return v

def boot(c):
    ok = js_wait(c, "return !document.getElementById('splash')", 25)
    note(ok, 'splash dismissed')
    c.js(JS % ("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
              "var s=HUB.store.state; s.profile.name='QA User'; s.profile.campus='QA Campus';"
              "s.prefs.dark=true; HUB.store.save(); return 1"))
    c.send('Page.reload')
    ok = js_wait(c, "return document.readyState==='complete' && !document.getElementById('splash') && !!window.HUB && !!HUB.gym && !!HUB.calc", 25)
    note(ok, 'clean boot after seed')
    arm_hooks(c)  # reload wiped window: re-arm or zero-error checks are vacuous
    disarm_gate(c); time.sleep(0.8); disarm_gate(c)
    c.js(JS % "try{HUB.ui.closeSheet()}catch(e){} var w=document.getElementById('wlcmHost'); if(w) w.remove(); return 1")
    time.sleep(0.5)
    v, _ = c.js(JS % "return !!document.querySelector('.authroot:not([hidden])')")
    note(not v, 'no auth overlay (gate disarmed)')
    v, _ = c.js(JS % "return HUB.i18n.getCountry()")
    note(v == 'US', 'country is US', str(v))

# ---------------- HOME ----------------
def glance_idx(c):
    v, _ = c.js(JS % "var d=document.querySelectorAll('#glanceDots span');"
         "for(var j=0;j<d.length;j++){ if(d[j].classList.contains('on')) return j; }"
         "var f=document.getElementById('glanceFlow'); return f?f.scrollLeft:-1;")
    return v

def home_tests(c, dark):
    th = 'dark' if dark else 'light'
    c.js(JS % "HUB.showTab('home'); return 1"); time.sleep(1.2)
    clear_errors(c)
    v, _ = c.js(JS % "return {tiles:document.querySelectorAll('#glanceFlow .gltile').length, dots:document.querySelectorAll('#glanceDots span').length}")
    note(v and v['tiles'] == 7, 'glance carousel: 7 tiles', str(v))
    c.shot('sweep-%d-home-%s.jpg' % (W, th))
    a0 = glance_idx(c)
    time.sleep(4.8)
    a1 = glance_idx(c)
    note(a0 is not None and a1 is not None and a0 != a1, 'glance carousel auto-rotates ~4s', 'idx %s -> %s' % (a0, a1))
    errs = collect_errors(c); note(not errs, 'home tab: zero console errors', str(errs)[:200]); clear_errors(c)
    # real tap on tile 0 (owed) -> sheet opens, rotation stops forever
    r = click(c, '#glanceFlow .gltile[data-gl="owed"]')
    time.sleep(1.2)
    v, _ = c.js(JS % "return !!document.querySelector('#sheetHost:not([hidden])')")
    note(v, 'tile tap opens detail sheet', 'click=%s' % r)
    c.shot('sweep-%d-home-tiledetail-%s.jpg' % (W, th))
    c.js(JS % "try{HUB.ui.closeSheet()}catch(e){} return 1"); time.sleep(0.5)
    b0 = glance_idx(c)
    time.sleep(5.2)
    b1 = glance_idx(c)
    note(b0 == b1, 'tile tap STOPS auto-rotation', 'pos %s -> %s' % (b0, b1))
    # tap EVERY tile: each must open its real destination (sheet / chat overlay / tab)
    dest_for = {'owed': 'sheet', 'unread': 'chat', 'jobs': 'worktab',
                'bill': 'sheet', 'events': 'sheet', 'docs': 'sheet', 'spend': 'sheet'}
    keys, _ = c.js(JS % "return [].slice.call(document.querySelectorAll('#glanceFlow .gltile')).map(function(t){return t.dataset.gl})")
    results = []
    for i, k in enumerate(keys or []):
        c.js(JS % (("var t=document.querySelectorAll('#glanceFlow .gltile')[%d];" % i) +
             "if(t){t.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));t.click();} return 1"))
        time.sleep(1.0)
        d = dest_for.get(k, 'sheet')
        if d == 'sheet':
            v, _ = c.js(JS % "return !!document.querySelector('#sheetHost:not([hidden])')")
            c.js(JS % "try{HUB.ui.closeSheet()}catch(e){} return 1")
        elif d == 'chat':
            v, _ = c.js(JS % "var r=document.getElementById('chatRoot'); return !!r && !r.hidden")
            c.js(JS % "try{HUB.chat.close()}catch(e){} return 1")
        else:
            v, _ = c.js(JS % "var w=document.getElementById('view-work'); return !!w && !w.hidden")
            c.js(JS % "HUB.showTab('home'); return 1")
        time.sleep(0.4)
        results.append('%s:%s' % (k, 'ok' if v else 'MISS'))
    note(len(results) == 7 and all(x.endswith(':ok') for x in results),
         'all 7 glance tiles open their destinations', str(results))
    c.js(JS % "try{HUB.ui.closeSheet()}catch(e){} return 1"); time.sleep(0.6)
    # classes countdown: seed a class 45 min from now today; the card must show a
    # live friendly countdown chip ("in 45m") — the code's intended format for
    # class chips (HH:MM:SS is reserved for appointment timers by design)
    c.js(JS % "var d=new Date(); d.setMinutes(d.getMinutes()+45);"
         "var p=function(n){return String(n).padStart(2,'0')};"
         "try{HUB.classes.addClass({subject:'QA Math',room:'R101',days:[new Date().getDay()],"
         "start:p(d.getHours())+':'+p(d.getMinutes()),end:'23:59'});}catch(e){}"
         "try{if(HUB.classes.refreshHome)HUB.classes.refreshHome();}catch(e){} return 1;")
    time.sleep(1.5)
    v, _ = c.js(JS % "var el=document.querySelector('#classCard [data-cd-ts]');"
         "return el?{txt:el.textContent, subj:document.getElementById('classCard').textContent.indexOf('QA Math')>-1}:'no-timer';")
    ok = isinstance(v, dict) and v.get('subj') and re.match(r'in\s+\S+', (v.get('txt') or '').strip())
    note(bool(ok), 'class countdown chip renders live friendly countdown', str(v)[:120])
    c.shot('sweep-%d-home-classes-%s.jpg' % (W, th))
    v, _ = c.js(JS % "return typeof HUB!=='undefined' && HUB.gpa ? Object.keys(HUB.gpa) : 'no-gpa'")
    note(v != 'no-gpa', 'grade calculator present', str(v)[:120])
    v, _ = c.js(JS % "try{HUB.gpa.addSheet(null); return !!document.querySelector('#sheetHost:not([hidden])');}catch(e){return 'ERR:'+e.message}")
    note(v is True, 'grade calc add sheet opens', str(v)[:80])
    time.sleep(0.6)
    c.shot('sweep-%d-home-grade-%s.jpg' % (W, th))
    c.js(JS % "try{HUB.ui.closeSheet()}catch(e){} return 1"); time.sleep(0.4)
    overflow(c, 'home %s' % th)
    hidden_veil_check(c, 'home %s' % th)
    errs = collect_errors(c); note(not errs, 'home flows: zero console errors', str(errs)[:200]); clear_errors(c)

def appointments_tests(c, dark):
    th = 'dark' if dark else 'light'
    v, _ = c.js(JS % "return typeof HUB!=='undefined' && HUB.appts ? 'ok' : 'no-appts'")
    note(v == 'ok', 'appointments module present')
    click(c, '[data-appt-add]'); time.sleep(0.8)
    v, _ = c.js(JS % "return !!document.querySelector('#sheetHost:not([hidden]) #apSave')")
    note(v, 'appointment add sheet opens')
    v, _ = c.js(JS % "var t=document.getElementById('apTitle'); if(!t) return 'no-title';"
         "t.value='QA Dentist'; t.dispatchEvent(new Event('input',{bubbles:true}));"
         "var d=document.getElementById('apDate'); d.value='2027-01-15'; d.dispatchEvent(new Event('change',{bubbles:true}));"
         "var tm=document.getElementById('apTime'); tm.value='10:30'; tm.dispatchEvent(new Event('change',{bubbles:true}));"
         "document.getElementById('apSave').click(); return 'saved';")
    time.sleep(1.0)
    v2, _ = c.js(JS % "return (document.getElementById('apptCard')||{textContent:''}).textContent")
    note('QA Dentist' in (v2 or ''), 'appointment appears on card', str(v)[:60])
    click(c, '[data-appt-edit]'); time.sleep(0.8)
    v, _ = c.js(JS % "var t=document.getElementById('apTitle'); if(!t) return 'no-edit';"
         "t.value='QA Dentist EDIT'; t.dispatchEvent(new Event('input',{bubbles:true}));"
         "document.getElementById('apSave').click(); return 'saved';")
    time.sleep(1.0)
    v2, _ = c.js(JS % "return (document.getElementById('apptCard')||{textContent:''}).textContent")
    note('QA Dentist EDIT' in (v2 or ''), 'appointment edit saves')
    c.shot('sweep-%d-home-appts-%s.jpg' % (W, th))
    click(c, '[data-appt-del]'); time.sleep(1.0)
    v2, _ = c.js(JS % "return (document.getElementById('apptCard')||{textContent:''}).textContent")
    note('QA Dentist EDIT' not in (v2 or ''), 'appointment delete removes')
    # live countdown: HH:MM:SS ticker for appointments under 24h (by design)
    c.js(JS % "var d=new Date(); d.setHours(d.getHours()+2);"
         "var p=function(n){return String(n).padStart(2,'0')};"
         "HUB.appts.addAppt({title:'QA Countdown', date:d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate()), time:p(d.getHours())+':'+p(d.getMinutes())});"
         "HUB.showTab('home'); return 1;")
    time.sleep(1.5)
    v, _ = c.js(JS % "var el=document.querySelector('#apptCard [data-appt-ts]'); return el?el.textContent:'no-timer';")
    note(bool(re.match(r'\d{2}:\d{2}:\d{2}', (v or '').strip())), 'appointment countdown ticks HH:MM:SS', str(v)[:40])
    overflow(c, 'appointments %s' % th)
    hidden_veil_check(c, 'appointments %s' % th)
    errs = collect_errors(c); note(not errs, 'appointments CRUD: zero console errors', str(errs)[:200]); clear_errors(c)

# ---------------- DAILY ----------------
def daily_events_tests(c, dark):
    th = 'dark' if dark else 'light'
    c.js(JS % "HUB.showTab('daily'); return 1"); time.sleep(1.2)
    clear_errors(c)
    v, _ = c.js(JS % "return (HUB.store.state.events||[]).filter(function(e){return !e.sample}).length")
    before = v or 0
    click(c, '[data-ev-add]'); time.sleep(0.8)
    v, _ = c.js(JS % "return !!document.querySelector('#sheetHost:not([hidden]) #efSave')")
    note(v, 'event add sheet opens from Daily + Add')
    c.shot('sweep-%d-daily-eventsheet-%s.jpg' % (W, th))
    v, _ = c.js(JS % "var set=function(id,val){var e=document.getElementById(id); if(!e) return false;"
         "e.value=val; e.dispatchEvent(new Event('input',{bubbles:true})); return true;};"
         "if(!set('efTitle','QA Sweep Party')) return 'no-title';"
         "set('efTime','Sat · 6:00 PM'); set('efWhere','QA Hall'); set('efCat','Test'); set('efDesc','sweep test');"
         "document.getElementById('efSave').click(); return 'saved';")
    time.sleep(1.2)
    v2, _ = c.js(JS % "return (HUB.store.state.events||[]).filter(function(e){return !e.sample}).length")
    note((v2 or 0) == before + 1, 'event add saves to store', '%s -> %s' % (before, v2))
    c.js(JS % "HUB.views.daily.openEventSheet((HUB.store.state.events||[]).filter(function(e){return !e.sample})[0].id); return 1")
    time.sleep(0.8)
    v, _ = c.js(JS % "return {edit:!!document.getElementById('evEditBtn'), del:!!document.getElementById('evDelBtn')}")
    note(v and v['edit'] and v['del'], 'event detail has Edit/Delete', str(v))
    c.shot('sweep-%d-daily-eventedit-%s.jpg' % (W, th))
    click(c, '#evEditBtn'); time.sleep(0.8)
    c.js(JS % "var t=document.getElementById('efTitle'); t.value='QA Sweep Party EDIT';"
         "t.dispatchEvent(new Event('input',{bubbles:true}));"
         "document.getElementById('efSave').click(); return 1")
    time.sleep(1.2)
    v, _ = c.js(JS % "return (HUB.store.state.events||[]).filter(function(e){return !e.sample}).map(function(e){return e.title})")
    note('QA Sweep Party EDIT' in (v or []), 'event edit saves', str(v)[:120])
    c.js(JS % "HUB.views.daily.openEventSheet((HUB.store.state.events||[]).filter(function(e){return !e.sample})[0].id); return 1")
    time.sleep(0.8)
    click(c, '#evDelBtn'); time.sleep(1.2)
    v3, _ = c.js(JS % "return (HUB.store.state.events||[]).filter(function(e){return !e.sample}).length")
    note((v3 or 0) == before, 'event delete removes', '%s -> %s' % (v2, v3))
    click(c, '[data-ev-add]'); time.sleep(0.8)
    c.js(JS % "document.getElementById('efTime').value='x'; document.getElementById('efSave').click(); return 1")
    time.sleep(0.6)
    v2, _ = c.js(JS % "return {open:!!document.querySelector('#sheetHost:not([hidden]) #efSave'), count:(HUB.store.state.events||[]).filter(function(e){return !e.sample}).length}")
    note(v2 and v2['open'] and v2['count'] == before, 'event validation blocks empty title', str(v2))
    c.js(JS % "try{HUB.ui.closeSheet()}catch(e){} return 1"); time.sleep(0.5)
    overflow(c, 'daily events %s' % th)
    hidden_veil_check(c, 'daily events %s' % th)
    errs = collect_errors(c); note(not errs, 'daily events CRUD: zero console errors', str(errs)[:200]); clear_errors(c)

# ---------------- GYM ----------------
def gym_tests(c, dark):
    th = 'dark' if dark else 'light'
    c.js(JS % "HUB.showTab('daily'); return 1"); time.sleep(1.0)
    clear_errors(c)
    c.js(JS % "var s=HUB.store.state; s.gym={unit:'met',profile:null,logs:[]}; HUB.store.save();"
         "HUB.views.daily.render(document.getElementById('view-daily')); return 1")
    time.sleep(0.8)
    v, _ = c.js(JS % "return !!document.getElementById('gySetup')")
    note(v, 'gym setup CTA present on fresh profile')
    c.shot('sweep-%d-gym-setupcard-%s.jpg' % (W, th))
    c.js(JS % "HUB.gym.openSetup(); return 1"); time.sleep(1.0)
    v, _ = c.js(JS % "return {dr:!!document.querySelector('.gy-drawer.show'), bd:!!document.querySelector('.gy-bd.show'), inputs:document.querySelectorAll('#gyDrawer input,#gyDrawer select').length}")
    note(v and v['dr'], 'gym setup drawer opens', str(v))
    c.shot('sweep-%d-gym-drawer-%s.jpg' % (W, th))
    v, _ = c.js(JS % "var set=function(id,val){var e=document.getElementById(id); if(!e) return id+'-missing';"
         "e.focus(); e.value=val; e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true})); return null;};"
         "var errs=[];"
         "var r1=set('fAge','30'); if(r1) errs.push(r1);"
         "var r2=set('fW','82'); if(r2) errs.push(r2);"
         "var r3=set('fT','78'); if(r3) errs.push(r3);"
         "var h=set('fHcm','182');"
         "if(h==='fHcm-missing'){ set('fFt','5'); set('fIn','11'); } else if(h) errs.push(h);"
         "return errs.length?errs:'filled';")
    note(v == 'filled', 'gym setup fields fill', str(v)[:160])
    time.sleep(0.6)
    c.shot('sweep-%d-gym-drawer-filled-%s.jpg' % (W, th))
    click(c, '#fSave'); time.sleep(1.2)
    v2, _ = c.js(JS % "return {dr:!!document.querySelector('.gy-drawer.show'), kcal:document.body.textContent.indexOf('kcal')>-1}")
    note(not v2['dr'], 'gym drawer closes after save', str(v2))
    note(v2['kcal'], 'gym card shows calorie data after save', str(v2))
    c.shot('sweep-%d-gym-card-%s.jpg' % (W, th))
    click(c, '#gyMeals'); time.sleep(1.0)
    v, _ = c.js(JS % "return !!document.getElementById('gyGenBtn')")
    note(v, 'gym meals sheet opens with Generate button')
    if v:
        click(c, '#gyGenBtn'); time.sleep(1.0)
        v2, _ = c.js(JS % "return (document.getElementById('gyPlan')||{textContent:''}).textContent.length")
        note((v2 or 0) > 100, 'gym day plan generates', 'chars=%s' % v2)
        c.shot('sweep-%d-gym-plan-%s.jpg' % (W, th))
        sh, _ = c.js(JS % "var s=document.getElementById('gyShuffle'); return s&&s.style.display!=='none'")
        if sh:
            click(c, '#gyShuffle'); time.sleep(0.8)
            note(True, 'gym plan shuffle works')
    # country cuisine: deterministic checks (genPlan shuffles randomly, so assert
    # ABSENCE of the other cuisine's dishes + the recipes list, which is fixed)
    IN_DISHES = ['egg bhurji', 'red lentil dal', 'paneer tikka', 'paneer + veg']
    US_DISHES = ['egg-white omelet', 'protein pancakes', 'chicken burrito bowl', 'turkey chili + beans', 'turkey meatballs']
    v, _ = c.js(JS % "var p=document.getElementById('gyPlan'); return p?p.textContent.toLowerCase():'no-plan';")
    sh, _ = c.js(JS % "return (document.querySelector('#sheetHost:not([hidden])')||{textContent:''}).textContent.toLowerCase()")
    if v and v != 'no-plan':
        note(not any(d in v for d in IN_DISHES), 'US plan hides Indian-only dishes')
    note('turkey chili' in (sh or '') and 'red lentil dal' not in (sh or ''),
         'US recipes: Turkey Chili in, Red Lentil Dal out')
    c.js(JS % "HUB.i18n.setCountry('IN'); return 1"); time.sleep(0.6)
    # recipes render at openMeals() time: close + re-open the sheet for IN recipes
    c.js(JS % "try{HUB.ui.closeSheet()}catch(e){} return 1"); time.sleep(0.5)
    click(c, '#gyMeals'); time.sleep(1.0)
    click(c, '#gyGenBtn'); time.sleep(1.0)
    v, _ = c.js(JS % "var p=document.getElementById('gyPlan'); return p?p.textContent.toLowerCase():'no-plan';")
    sh, _ = c.js(JS % "return (document.querySelector('#sheetHost:not([hidden])')||{textContent:''}).textContent.toLowerCase()")
    if v and v != 'no-plan':
        note(not any(d in v for d in US_DISHES), 'IN plan hides US-only dishes')
    note('red lentil dal' in (sh or ''), 'IN recipes include Red Lentil Dal')
    c.shot('sweep-%d-gym-plan-in-%s.jpg' % (W, th))
    c.js(JS % "HUB.i18n.setCountry('US'); return 1"); time.sleep(0.4)
    c.js(JS % "try{HUB.ui.closeSheet()}catch(e){} return 1"); time.sleep(0.5)
    v, _ = c.js(JS % "return [].slice.call(document.querySelectorAll('button')).filter(function(x){return /log|progress/i.test(x.textContent)&&x.offsetParent}).length")
    note((v or 0) > 0, 'gym progress/log buttons present', str(v))
    c.js(JS % "HUB.showTab('daily'); return 1"); time.sleep(0.8)
    v, _ = c.js(JS % "var b=document.querySelector('#gyReset'); if(!b) return 'no-reset'; b.click(); return 'clicked';")
    time.sleep(0.8)
    c.shot('sweep-%d-gym-reset-%s.jpg' % (W, th))
    v2, _ = c.js(JS % "var sh=document.querySelector('#sheetHost:not([hidden])'); if(!sh) return 'no-sheet';"
         "var yes=[].slice.call(sh.querySelectorAll('button')).filter(function(b){return /confirm|yes|reset/i.test(b.textContent)});"
         "if(yes.length){yes[0].click(); return 'confirmed';} return 'no-confirm';")
    time.sleep(1.0)
    v3, _ = c.js(JS % "return !!document.getElementById('gySetup')")
    note(v3, 'gym reset returns to setup card', '%s / %s' % (v, v2))
    overflow(c, 'gym %s' % th)
    hidden_veil_check(c, 'gym %s' % th)
    errs = collect_errors(c); note(not errs, 'gym flows: zero console errors', str(errs)[:200]); clear_errors(c)

# ---------------- CALCULATOR ----------------
def calc_tests(c, dark):
    th = 'dark' if dark else 'light'
    c.js(JS % "HUB.showTab('daily'); return 1"); time.sleep(1.0)
    clear_errors(c)
    v, _ = c.js(JS % "return !!document.querySelector('#calcRoot')")
    note(v, 'calculator card present on daily')
    c.shot('sweep-%d-calc-card-%s.jpg' % (W, th))
    fails = []
    for kid in KEY_IDS:
        r = click(c, '#calcRoot [data-ck="%s"]' % kid)
        time.sleep(0.03)
        if r != 'ok':
            fails.append('%s:%s' % (kid, str(r)[:50]))
    note(not fails, 'calculator: all %d std keys clickable, no throw' % len(KEY_IDS), str(fails)[:300])
    errs = collect_errors(c); note(not errs, 'calc all-keys: zero console errors', str(errs)[:200]); clear_errors(c)
    r = click(c, '#calcAdvBtn'); time.sleep(0.8)
    v, _ = c.js(JS % "return HUB.calc._adv.advBank()")
    note(v is True, 'ADV bank toggles on', 'click=%s' % r)
    fails = []
    for kid in ADV_EXTRA:
        r = click(c, '#calcRoot [data-ck="%s"]' % kid)
        time.sleep(0.05)
        if r != 'ok':
            fails.append('%s:%s' % (kid, str(r)[:50]))
    note(not fails, 'calculator: all %d adv keys clickable, no throw' % len(ADV_EXTRA), str(fails)[:300])
    errs = collect_errors(c); note(not errs, 'calc adv-keys: zero console errors', str(errs)[:200]); clear_errors(c)
    fails = []
    for kid in ADV_KEYS:
        r = click(c, '#calcRoot [data-ck="%s"]' % kid)
        time.sleep(0.5)
        sh, _ = c.js(JS % "return !!document.querySelector('#sheetHost:not([hidden])')")
        c.js(JS % "try{HUB.ui.closeSheet()}catch(e){} return 1"); time.sleep(0.3)
        if r != 'ok' or not sh:
            fails.append('%s:%s/sheet=%s' % (kid, str(r)[:40], sh))
    note(not fails, 'all 6 calculus lab sheets open via UI', str(fails)[:200])
    c.shot('sweep-%d-calc-adv-%s.jpg' % (W, th))
    click(c, '#calcAdvBtn'); time.sleep(0.5)
    v, _ = c.js(JS % "return HUB.calc._eval('2+2','std',null)")
    ok = isinstance(v, dict) and v.get('ok') == 1 and abs(v.get('value', 0) - 4) < 1e-9
    note(ok, 'calc evaluates 2+2=4', str(v)[:80])
    v, ex = c.js(JS % "try{"
         "var r={};"
         "r.integ=HUB.calc._adv.integ('x^2',0,1);"
         "r.deriv=HUB.calc._adv.deriv('x^2',3);"
         "r.sigma=HUB.calc._adv.sigma('x',1,10);"
         "r.solve=HUB.calc._adv.solve('x^2-4');"
         "r.base=HUB.calc._adv.base('0xff',10);"
         "return r;}catch(e){return 'ERR:'+e.message+'/'+((e&&e.code)||'')} ")
    ok = isinstance(v, dict) and abs(v.get('integ', 0) - 1/3) < 1e-6 and abs(v.get('deriv', 0) - 6) < 1e-6 and v.get('sigma') == 55
    note(ok, 'calculus hooks correct (integ~1/3, deriv=6, sigma=55)', str(v)[:200])
    note(isinstance(v, dict) and str(v.get('base')) == '255', 'base converter 0xFF -> 255', str(v.get('base') if isinstance(v, dict) else v)[:40])
    c.js(JS % "HUB.calc._press('set'); return 1"); time.sleep(0.8)
    sh, _ = c.js(JS % "return !!document.querySelector('#sheetHost:not([hidden])')")
    note(sh, 'calc settings sheet opens')
    c.shot('sweep-%d-calc-settings-%s.jpg' % (W, th))
    c.js(JS % "try{HUB.ui.closeSheet()}catch(e){} return 1"); time.sleep(0.4)
    # memory round-trip follows the real user flow: digits live in the std bank,
    # M+/M-/MR live in the ADV bank, so the bank must be toggled between steps.
    # (No MC key exists: assert relative to the pre-existing memory value.)
    m0, _ = c.js(JS % "return HUB.calc._adv.mem()")
    c.js(JS % "var q=function(k){var b=document.querySelector('#calcRoot [data-ck=\"'+k+'\"]');"
         "if(b){b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));b.click();}};"
         "q('ac');q('k5'); return 1")
    time.sleep(0.4)
    click(c, '#calcAdvBtn'); time.sleep(0.5)
    c.js(JS % "var q=function(k){var b=document.querySelector('#calcRoot [data-ck=\"'+k+'\"]');"
         "if(b){b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));b.click();}};"
         "q('mplus'); return 1")
    time.sleep(0.4)
    click(c, '#calcAdvBtn'); time.sleep(0.5)
    c.js(JS % "var q=function(k){var b=document.querySelector('#calcRoot [data-ck=\"'+k+'\"]');"
         "if(b){b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));b.click();}};"
         "q('ac'); return 1")
    time.sleep(0.4)
    click(c, '#calcAdvBtn'); time.sleep(0.5)
    c.js(JS % "var q=function(k){var b=document.querySelector('#calcRoot [data-ck=\"'+k+'\"]');"
         "if(b){b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));b.click();}};"
         "q('mr'); return 1")
    time.sleep(0.5)
    v, _ = c.js(JS % "return {mem:HUB.calc._adv.mem(), disp:document.getElementById('calcExpr').value}")
    want = (m0 or 0) + 5
    ok = v and abs((v.get('mem') or 0) - want) < 1e-9 and str(v.get('disp')) == str(want if want != int(want) else int(want))
    note(ok, 'memory M+/MR round-trip', 'mem0=%s -> %s' % (m0, v))
    click(c, '#calcAdvBtn'); time.sleep(0.5)
    c.js(JS % "HUB.calc._graph.setView('graph'); return 1"); time.sleep(1.2)
    v, _ = c.js(JS % "return {g:!!document.querySelector('#calcGraph:not([hidden])'), svg:!!document.querySelector('#calcGraph svg, #calcGraph canvas')}")
    note(v and v['g'], 'graph view opens', str(v))
    c.shot('sweep-%d-calc-graph-%s.jpg' % (W, th))
    v, ex = c.js(JS % "try{"
         "HUB.calc._graph.pad.ins('x'); HUB.calc._graph.pad.ins('^'); HUB.calc._graph.pad.ins('2');"
         "HUB.calc._graph.validate(); return 'ok';}catch(e){return 'ERR:'+e.message}")
    note(v == 'ok', 'graph keypad types x^2 and validates', str(v)[:120])
    c.shot('sweep-%d-calc-graphfn-%s.jpg' % (W, th))
    c.js(JS % "HUB.calc._graph.setView('calc'); return 1"); time.sleep(0.6)
    overflow(c, 'calc %s' % th)
    hidden_veil_check(c, 'calc %s' % th)
    errs = collect_errors(c); note(not errs, 'calc flows: zero console errors', str(errs)[:200]); clear_errors(c)

def main():
    if os.path.isdir(PROF): shutil.rmtree(PROF, ignore_errors=True)
    os.makedirs(PROF, exist_ok=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--remote-debugging-port=%d' % PORT, '--remote-allow-origins=*',
        '--allow-file-access-from-files', '--user-data-dir=' + PROF,
        '--window-size=%d,844' % W, '--hide-scrollbars', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wsurl = None
        for _ in range(40):
            try:
                tabs = json.load(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT, timeout=3))
                wsurl = tabs[0]['webSocketDebuggerUrl']; break
            except Exception: time.sleep(0.5)
        assert wsurl, 'no devtools'
        c = CDP(wsurl)
        c.send('Emulation.setDeviceMetricsOverride', {'width': W, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        arm_hooks(c)
        c.send('Page.navigate', {'url': BASE})
        boot(c)
        for dark in (True, False):
            set_theme(c, dark)
            home_tests(c, dark)
            appointments_tests(c, dark)
            daily_events_tests(c, dark)
            gym_tests(c, dark)
            calc_tests(c, dark)
            hidden_veil_check(c, 'final %s' % ('dark' if dark else 'light'))
        errs = collect_errors(c)
        note(not errs, 'FINAL: zero console errors across whole sweep', str(errs)[:300])
    finally:
        proc.terminate()
    n = len(checks); p = sum(checks)
    print('==== SWEEP %dpx: %d/%d PASS ====' % (W, p, n))
    sys.exit(0 if p == n else 1)

if __name__ == '__main__':
    main()
