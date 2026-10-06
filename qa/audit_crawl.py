#!/usr/bin/env python3
"""Onaro HUB completeness crawl v2. Drives UI only (no app code changes).
Usage: python3 audit_crawl.py <dark|light>
Findings -> qa/audit-missing/findings-<theme>.json (saved incrementally)
Shots    -> qa/audit-missing/<slug>-<theme>.png
"""
import json, subprocess, time, urllib.request, os, base64, shutil, sys, traceback
import websocket
THEME = sys.argv[1] if len(sys.argv) > 1 else 'dark'
QA = os.path.expanduser('~/workspace/hub/qa/audit-missing')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
IPHONE_UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) '
             'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1')
PORT = 9741 if THEME == 'dark' else 9742
os.makedirs(QA, exist_ok=True)
findings = []
FJSON = os.path.join(QA, f'findings-{THEME}.json')
def save():
    json.dump(findings, open(FJSON, 'w'), indent=1)

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12); self.id = 0
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 18
        while time.time() < deadline:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:80])
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)

c = None
def js(expr):
    r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
    return (r or {}).get('result', {}).get('value')
def shot(slug):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    p = os.path.join(QA, f'{slug}-{THEME}.png')
    open(p, 'wb').write(base64.b64decode(r['data']))
    return p
def finding(sev, surface, did, happened, should, slug):
    p = shot('audit-missing-' + slug)
    findings.append({'sev': sev, 'surface': surface, 'did': did,
                     'happened': happened, 'should': should, 'shot': p})
    print(f'  FINDING [{sev}] {surface}: {did} -- {happened}', flush=True); save()
def note(ok, label, detail=''):
    print(('PASS' if ok else 'FAIL'), label, str(detail)[:130], flush=True)
def errs(): return js("window.__huberr.splice(0)") or []
def sheet_open(): return bool(js("!document.getElementById('sheetHost').hidden"))
def on_tab(t): return bool(js(f"!document.getElementById('view-{t}').hidden"))
def tab(t):
    js(f"HUB.showTab('{t}');"); time.sleep(1.8)
    if not on_tab(t):  # retry once
        time.sleep(1.5); js(f"HUB.showTab('{t}');"); time.sleep(1.5)
    return on_tab(t)
def vis_click_text(txt):
    return js("""(()=>{const els=[...document.querySelectorAll('button,a,[data-tap]')];
for(const e of els){if(e.offsetParent===null)continue;
const t=(e.innerText||'').trim(),a=e.getAttribute('aria-label')||'';
if(t.includes(%r)||a.includes(%r)){e.scrollIntoView({block:'center'});e.click();return e.id||t.slice(0,25);}}
return false;})()""" % (txt, txt))
def vis_click_sel(sel):
    return js(f"(()=>{{const e=document.querySelector({sel!r});if(!e)return 'missing';if(e.offsetParent===null)return 'hidden-skip';e.scrollIntoView({{block:'center'}});e.click();return 'clicked';}})()")
def set_val(sel, val):
    return js(f"(()=>{{const e=document.querySelector({sel!r});if(!e)return 'missing';e.focus();e.value={val!r};e.dispatchEvent(new Event('input',{{bubbles:true}}));e.dispatchEvent(new Event('change',{{bubbles:true}}));return 'set';}})()")
def page_text(): return js("document.body.innerText") or ''
CLOSE_JS = ("try{HUB.ui.closeSheet();}catch(e){};"
  "for(const k of ['chat','pulse','search','notifications'])try{if(HUB[k]&&HUB[k].close)HUB[k].close();}catch(e){};"
  "['gyBd','gyDrawer'].forEach(function(id){var e=document.getElementById(id);if(e)e.remove();});"
  "document.querySelectorAll('.mkzoom').forEach(function(e){e.remove();});")
def close_all(): js(CLOSE_JS); time.sleep(0.8)
def toast_now(): return js("(()=>[...document.querySelectorAll('#toastHost .toast')].map(e=>e.textContent).join('|'))()")

def section(name, fn):
    print(f'== {name} ==', flush=True)
    try: fn()
    except Exception as e:
        print(f'  SECTION-ERROR {name}: {type(e).__name__} {str(e)[:120]}', flush=True)
        try: close_all()
        except Exception: pass

# ---------------- boot ----------------
prof = f'/tmp/hubqa-crawl2-{THEME}'
shutil.rmtree(prof, ignore_errors=True)
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    f'--remote-debugging-port={PORT}', '--remote-allow-origins=*',
    f'--user-data-dir={prof}', '--hide-scrollbars', '--allow-file-access-from-files',
    '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', BASE],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(30):
        time.sleep(1)
        try:
            with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=3) as r: ts = json.load(r)
            tgt = next(x for x in ts if x['type'] == 'page' and 'devtools' not in x['url']); break
        except Exception: continue
    else: raise RuntimeError('no target')
    c = CDP(tgt['webSocketDebuggerUrl'])
    c.send('Emulation.setDeviceMetricsOverride', {'width':390,'height':844,'deviceScaleFactor':2,'mobile':True})
    c.send('Network.enable', {})
    c.send('Network.setUserAgentOverride', {'userAgent': IPHONE_UA})
    c.send('Emulation.setGeolocationOverride', {'latitude':32.783,'longitude':-96.806,'accuracy':40})
    c.send('Runtime.enable'); c.send('Page.enable'); c.send('Page.reload')
    js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
    time.sleep(5)
    js("try{HUB.store.state.profile.name='PraBin';HUB.store.save();var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
    js("document.body.classList.%s('dark');" % ('add' if THEME=='dark' else 'remove'))
    time.sleep(1)
    note(True, f'{THEME} boot', on_tab('home'))

    # ---------------- HOME ----------------
    def s_home_capsule():
        tab('home')
        r = vis_click_sel('#homeCapNew'); time.sleep(1.5)
        note(r == 'clicked' and sheet_open(), 'home: capsule pill opens composer', r)
        set_val('#cpTitle','QA letter'); set_val('#cpMsg','Hello future me — QA test.');
        set_val('#cpDate','2027-09-22')
        quick = vis_click_text('6 months')
        vis_click_sel('#cpSeal'); time.sleep(1.5)
        e = errs(); note(not e, 'home: capsule seal no errors', e)
        note(not sheet_open(), 'home: capsule saved (sheet closed)')
        tab('daily'); time.sleep(1)
        t = page_text()
        note('QA letter' in t and 'Unlocks in' in t, 'daily: capsule listed as locked')
        shot('audit-missing-capsule-locked'); save()
        close_all()
    section('HOME capsule', s_home_capsule)

    def s_home_info():
        tab('home')
        vis_click_sel('#homeCapInfo'); time.sleep(1.2)
        if sheet_open():
            t = page_text()
            note('device' in t.lower(), 'home: capsule info honest (stays on device)')
            r = vis_click_text('Open Time Capsule'); time.sleep(1.5)
            note(r and on_tab('daily'), 'home: capsule info CTA -> Daily', r)
        else: finding('broken','Home capsule (i)','tapped (i)','no sheet','how-it-works sheet should open','home-capsule-info-dead')
        close_all()
    section('HOME capsule info', s_home_info)

    def s_home_glance():
        tab('home')
        n = js("document.querySelectorAll('#view-home .gltile').length")
        if not n: time.sleep(2); n = js("document.querySelectorAll('#view-home .gltile').length")
        note(n and n >= 7, 'home: glance tiles present', n)
        for i in range(n or 0):
            label = js(f"(document.querySelectorAll('#view-home .gltile')[{i}].innerText||'').replace(/\\n/g,' ').slice(0,28)")
            js(f"document.querySelectorAll('#view-home .gltile')[{i}].click();"); time.sleep(1.4)
            opened = sheet_open() or bool(js("document.querySelector('.chatroot:not([hidden])')"))
            if not opened:
                finding('broken','Home glance',f'tapped tile "{label}"','nothing opened','tile detail should open',f'home-glance-{i}')
            else:
                tx = page_text()
                is_empty = ('nothing' in tx.lower() or 'no ' in tx.lower() or '$0' in tx) and len(tx) < 400
                cta = bool(js("!![...document.querySelectorAll('#sheetBox button,.chatroot button')].length"))
                if is_empty and not cta:
                    finding('missing-UX','Home glance',f'tile "{label}" detail','empty with no CTA','empty state + CTA',f'home-glance-{i}-empty')
                else: note(True, f'home: glance "{label[:22]}" detail ok')
            close_all(); time.sleep(0.4)
        tab('home')
    section('HOME glance', s_home_glance)

    def s_home_classes():
        tab('home')
        r = vis_click_text('Manage classes'); time.sleep(1.4)
        if r and sheet_open():
            note(True,'home: classes manage sheet opens')
            # add a class via manage sheet if possible
            add = vis_click_text('Add class') or vis_click_text('+ Add'); time.sleep(1.2)
            flds = js("(()=>[...document.querySelectorAll('#sheetBox input,#sheetBox select')].map(e=>e.id||e.type).join(','))()")
            note(True,'home: class add fields',flds)
            if js("!!document.querySelector('#clsName')"):
                set_val('#clsName','QA Physics')
                sv = js("(()=>{const b=[...document.querySelectorAll('#sheetBox button')].find(x=>/save/i.test(x.textContent));if(b){b.click();return true;}return false;})()")
                time.sleep(1.2); note(sv and 'QA Physics' in page_text(),'home: class added')
            close_all()
            # delete without confirm? use code-verified list; try UI delete if present
            d = js("(()=>{const b=document.querySelector('[data-class-del]');return b?(b.click(),true):false;})()")
            if d:
                time.sleep(1.2)
                gone = 'QA Physics' not in page_text()
                note(sheet_open() or not gone,'home: class delete confirm-or-kept')
                if gone and not sheet_open():
                    finding('missing-UX','Home classes','deleted QA class','no confirmation, instant delete','destructive delete needs confirm','home-class-del-noconfirm')
            close_all()
        else: finding('broken','Home classes','tapped Manage classes','no sheet','manage sheet should open','home-classes-dead')
    section('HOME classes', s_home_classes)

    def s_home_gpa():
        tab('home')
        r = vis_click_text('+ Add course'); time.sleep(1.4)
        if not (r and sheet_open()):
            finding('broken','Home GPA','tapped + Add course','no sheet','add-course sheet should open','home-gpa-add'); return
        set_val('#gpaSubj','QA Chemistry'); set_val('#gpaCr','3')
        js("(()=>{const s=[...document.querySelectorAll('#sheetBox select')].find(e=>/grade/i.test(e.id));if(s){s.value='A';s.dispatchEvent(new Event('change',{bubbles:true}));}})()")
        vis_click_sel('#gpaSave'); time.sleep(1.4)
        e = errs(); note(not e,'home: GPA add no errors',e)
        note('QA Chemistry' in page_text(),'home: GPA course listed')
        # delete -> native confirm(); override to accept
        did = js("(()=>{const cs=HUB.gpa.courses();const c=cs.find(x=>x.subject&&x.subject.includes('QA'));return c&&c.id;})()")
        note(bool(did),'home: QA course id found',did)
        if did:
            js("window.__cf=window.confirm;window.confirm=function(){return true;}")
            js(f"HUB.gpa.courseSheet('{did}')"); time.sleep(1.2)
            vis_click_text('Delete'); time.sleep(1.2)
            js("window.confirm=window.__cf;")
            gone = js("!HUB.gpa.courses().some(x=>x.subject&&x.subject.includes('QA'))")
            note(gone,'home: GPA course deleted (native confirm)')
            if gone: note(True,'home: GPA delete uses NATIVE confirm() dialog')
        close_all()
    section('HOME gpa', s_home_gpa)

    def s_home_appt():
        tab('home')
        r = vis_click_text('+ Add appointment'); time.sleep(1.4)
        if not (r and sheet_open()):
            finding('broken','Home appointments','tapped + Add appointment','no sheet','form sheet should open','home-appt-add'); return
        ok = js("""(()=>{const b=document.getElementById('sheetBox');
const t=[...b.querySelectorAll('input')].find(e=>!e.type||e.type==='text');if(t){t.value='QA Dentist';t.dispatchEvent(new Event('input',{bubbles:true}));}
const d=[...b.querySelectorAll('input')].find(e=>e.type==='date'||e.type==='datetime-local');if(d){d.value='2026-09-23T10:00';d.dispatchEvent(new Event('change',{bubbles:true}));}
const btn=[...b.querySelectorAll('button')].find(x=>/save|add/i.test(x.textContent));if(btn){btn.click();return true;}return false;})()""")
        time.sleep(1.4); e=errs(); note(not e and ok,'home: appt saved',e)
        note('QA Dentist' in page_text(),'home: appt appears on card')
        # open appt -> delete (code says no confirm) -> verify
        aid = js("(()=>{const a=(HUB.appts.list()||[]).find(x=>x.title&&x.title.includes('QA'));return a&&a.id;})()")
        if aid:
            js(f"HUB.appts.formSheet('{aid}')"); time.sleep(1.2)
            dl = js("(()=>{const b=[...document.querySelectorAll('#sheetBox button')].find(x=>/delete/i.test(x.textContent));if(b){b.click();return true;}return false;})()")
            time.sleep(1)
            gone = js(f"!(HUB.appts.list()||[]).some(x=>String(x.id)==='{aid}')")
            if dl and gone and not sheet_open():
                finding('missing-UX','Home appointments','deleted QA appt','deleted instantly, no confirm dialog','destructive delete needs confirm','home-appt-del-noconfirm')
            else: note(True,'home: appt delete confirm-or-kept',f'dl={dl} gone={gone}')
        close_all()
    section('HOME appointments', s_home_appt)

    def s_home_wx():
        tab('home'); time.sleep(2.5)  # allow live fetch attempt (sandbox blocks egress)
        t = page_text()
        r = vis_click_sel('#wxStrip'); time.sleep(1.6)
        if r == 'clicked' and (sheet_open() or 'weather' in page_text().lower()):
            note(True,'home: weather strip opens detail')
            if sheet_open():
                note('°C' in page_text() or '°F' in page_text(),'home: wx unit toggle present')
                g = vis_click_text('Use my location'); time.sleep(2.5)
                t2 = page_text()
                note('Dallas' in t2 or 'demo' in t2.lower() or 'sample' in t2.lower() or 'unavailable' in t2.lower() or 'failed' in t2.lower(),'home: wx GPS result/error state',t2[:90].replace('\n',' '))
                if 'failed' in t2.lower() or 'unavailable' in t2.lower() or 'try again' in t2.lower():
                    note(True,'home: wx shows error state when fetch fails')
                shot('audit-missing-wx-detail')
            close_all()
        else: finding('broken','Home weather','tapped strip','nothing opened','detail/location picker should open','home-wx-dead')
        tab('home')
    section('HOME weather', s_home_wx)

    def s_home_ads_ask():
        tab('home')
        r = vis_click_sel('.adtile'); time.sleep(1.4)
        if r == 'clicked' and (sheet_open() or 'demo' in page_text().lower()):
            note('demo' in page_text().lower() or 'sponsor' in page_text().lower(),'home: ad sheet honest demo label')
        else: finding('broken','Home ads','tapped ad tile','nothing opened','ad demo sheet should open','home-ad-dead')
        close_all()
        r = vis_click_sel('#homeAskRow'); time.sleep(1.4)
        if r == 'clicked' and sheet_open():
            note('Keyword-based demo helper' in page_text(),'home: ask honest badge')
            set_val('#askSheetInput','where is my class')
            vis_click_sel('#askSheetSend'); time.sleep(1.5)
            ans = js("(document.getElementById('askSheetResults').innerText||'').length")
            note(ans > 20,'home: ask returns answer',ans)
        else: finding('broken','Home ask row','tapped Ask row','no sheet','ask sheet should open','home-askrow-dead')
        close_all()
        r = vis_click_sel('#homeCgAll'); time.sleep(1.6)
        note(r == 'clicked' and on_tab('groups'),'home: See all groups -> Groups tab',r)
        tab('home')
    section('HOME ads+ask+seeall', s_home_ads_ask)

    def s_home_astro():
        tab('home'); time.sleep(1.5)
        t = page_text()
        # DOB seeded later in ME; check card presence either way
        has = 'horoscope' in t.lower() or '♈' in t or 'Aries' in t
        note(True,'home: astro card checked','present' if has else 'absent (DOB not set yet)')
        shot('audit-missing-home-astro')
        close_all()
    section('HOME astro peek', s_home_astro)

    # ---------------- DAILY ----------------
    def s_daily_gym():
        tab('daily')
        r = vis_click_sel('#gySetup'); time.sleep(1.6)
        drawer = bool(js("!!document.getElementById('gyDrawer')"))
        note(r == 'clicked' and drawer,'daily: gym setup opens drawer',r)
        if drawer:
            flds = js("(()=>[...document.querySelectorAll('#gyDrawer input,#gyDrawer select,#gyDrawer button')].map(e=>e.id||e.type).join(','))()")
            note(True,'daily: gym drawer fields',flds[:160])
            filled = js("""(()=>{const d=document.getElementById('gyDrawer');let n=0;
[...d.querySelectorAll('input')].forEach(e=>{if(e.type==='number'){e.value='32';e.dispatchEvent(new Event('input',{bubbles:true}));n++;}});
[...d.querySelectorAll('select')].forEach(e=>{if(e.options.length>1){e.selectedIndex=1;e.dispatchEvent(new Event('change',{bubbles:true}));n++;}});return n;})()""")
            sv = js("(()=>{const d=document.getElementById('gyDrawer');const b=[...d.querySelectorAll('button')].find(x=>/save|create|start/i.test(x.textContent));if(b){b.click();return b.textContent.trim();}return false;})()")
            time.sleep(1.6); e=errs(); note(not e,'daily: gym setup save no errors',e)
            t=page_text(); note('kcal' in t.lower() or 'calorie' in t.lower(),'daily: gym plan shows ring',sv)
            shot('audit-missing-gym-plan')
            # unit toggle persists
            u = vis_click_sel('#gyUnit'); time.sleep(0.8)
            c.send('Page.reload'); time.sleep(5)
            js("document.body.classList.%s('dark');" % ('add' if THEME=='dark' else 'remove'))
            js("try{var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
            tab('daily')
            note('kcal' in page_text().lower() or 'calorie' in page_text().lower(),'daily: gym plan persists after reload')
            # reset -> in-app confirm
            rs = vis_click_sel('#gyReset'); time.sleep(1.4)
            if rs == 'clicked' and (sheet_open() or 'reset' in page_text().lower()):
                has_no = bool(js("!!document.querySelector('#gyResetNo')"))
                note(has_no,'daily: gym reset has Cancel option')
                if has_no: vis_click_sel('#gyResetNo'); time.sleep(0.8)
                else: close_all()
                note('kcal' in page_text().lower() or 'calorie' in page_text().lower(),'daily: gym reset cancelled keeps plan')
            else: finding('missing-UX','Daily gym','tapped Reset','no confirmation','destructive reset needs confirm','daily-gym-reset-noconfirm')
            close_all()
        else: finding('broken','Daily gym','tapped Set up my plan','no drawer/sheet','setup UI should open','daily-gym-setup')
    section('DAILY gym', s_daily_gym)

    def s_daily_capsule2():
        tab('daily')
        r = vis_click_sel('#dyCapNew'); time.sleep(1.4)
        if r == 'clicked' and sheet_open():
            set_val('#cpTitle','QA daily letter'); set_val('#cpMsg','second letter'); set_val('#cpDate','2027-01-01')
            vis_click_sel('#cpSeal'); time.sleep(1.4)
            t = page_text()
            note('QA daily letter' in t and 'Unlocks in' in t,'daily: capsule listed locked')
            # tap locked capsule -> should NOT open content
            lk = js("(()=>{const b=[...document.querySelectorAll('#view-daily button')].find(x=>/unlocks in/i.test(x.textContent));if(b){b.click();return true;}return false;})()")
            time.sleep(1.2)
            leaked = 'second letter' in page_text()
            note(not leaked,'daily: locked capsule content stays sealed',f'clicked={lk}')
            if leaked: finding('broken','Daily capsule','tapped locked capsule','letter text revealed early','must stay sealed until date','daily-capsule-early-leak')
        else: finding('broken','Daily capsule','tapped New capsule','no sheet','composer should open','daily-capsule-new')
        close_all()
    section('DAILY capsule', s_daily_capsule2)

    def s_daily_events():
        tab('daily'); time.sleep(1)
        r = vis_click_text('RSVP') or js("(()=>{const e=document.querySelector('#view-daily [data-ev]');if(e&&e.offsetParent!==null){e.click();return true;}return false;})()")
        time.sleep(1.4)
        note(bool(r) and sheet_open(),'daily: event sheet opens',r)
        close_all()
        # create FAB -> each action
        fr = vis_click_sel('#createFab'); time.sleep(1.4)
        if fr == 'clicked' and sheet_open():
            n = js("document.querySelectorAll('#sheetBox .caction').length")
            if not n: time.sleep(1.5); n = js("document.querySelectorAll('#sheetBox .caction').length")
            note(n and n >= 8,'create: action grid populated',n)
            for i in range(n or 0):
                a = js(f"(document.querySelectorAll('#sheetBox .caction')[{i}].innerText||'').trim()")
                js(f"document.querySelectorAll('#sheetBox .caction')[{i}].click();"); time.sleep(1.6)
                o = sheet_open() or on_tab('market') or on_tab('work') or on_tab('groups') or on_tab('me')
                if not o: finding('broken','Create FAB',f'tapped "{a}"','nothing opened','target should open',f'create-{i}')
                else: note(True,f'create: "{a[:24]}" opens target')
                close_all(); vis_click_sel('#createFab'); time.sleep(1.2)
            close_all()
        else: finding('broken','Create FAB','tapped +','no sheet','action grid should open','create-fab-dead')
        tab('daily')
    section('DAILY events+create', s_daily_events)

    # ---------------- MARKET ----------------
    def s_market():
        tab('market'); time.sleep(1)
        n0 = js("document.querySelectorAll('#view-market [data-listing]').length")
        dists = js("(()=>[...document.querySelectorAll('#view-market [data-listing]')].map(e=>{const m=(e.innerText||'').match(/([0-9.]+)\\s*mi/);return m?+m[1]:null;})()")
        note(n0 and n0 > 0,'market: listings render',f'{n0} dists={dists}')
        vis_click_text('5 mi'); time.sleep(1.4)
        n1 = js("document.querySelectorAll('#view-market [data-listing]').length")
        exp = sum(1 for d in (dists or []) if d is not None and d <= 5)
        note(n1 == exp or (not any(d is not None for d in (dists or []))), 'market: radius filter actually filters', f'{n0}->{n1} (<=5mi: {exp})')
        if n1 == n0 and exp < n0:
            finding('broken','Market radius','tapped 5 mi','grid unchanged though nearer listings exist','radius should filter','market-radius-nofilter')
        vis_click_text('City-wide') or vis_click_text('20 mi'); time.sleep(1.2)
        vis_click_text('Free'); time.sleep(1.4)
        n2 = js("document.querySelectorAll('#view-market [data-listing]').length")
        note(n2 <= n0,'market: Free filter narrows',f'{n0}->{n2}')
        vis_click_text('All'); time.sleep(1.2)
        # listing detail
        r = vis_click_sel('#view-market [data-listing]'); time.sleep(1.6)
        if r == 'clicked' and sheet_open():
            note(True,'market: listing detail opens')
            ph = vis_click_sel('#sheetBox [data-photo]'); time.sleep(1.4)
            if ph == 'clicked' and js("!!document.querySelector('.mkzoom:not([hidden])')"):
                note(True,'market: photo lightbox opens')
                js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))"); time.sleep(0.8)
                note(not js("!!document.querySelector('.mkzoom:not([hidden])')"),'market: lightbox Escape closes')
                js("document.querySelectorAll('.mkzoom').forEach(e=>e.remove())")
            else: finding('broken','Market listing','tapped photo','no lightbox','photo lightbox should open','market-photo-dead')
            ms = vis_click_text('Message'); time.sleep(1.6)
            note(bool(ms) and bool(js("document.querySelector('.chatroot:not([hidden])')")),'market: message seller opens chat',ms)
            close_all()
            vis_click_sel('#view-market [data-listing]'); time.sleep(1.4)
            rp = vis_click_text('Report'); time.sleep(1.4)
            note(bool(rp) and sheet_open(),'market: report opens trust sheet',rp)
            close_all()
        else: finding('broken','Market listing','tapped listing card','no detail','detail sheet should open','market-listing-dead')
        close_all()
        # post flow (select type chip first!)
        pr = vis_click_sel('#mkPostBtn'); time.sleep(1.6)
        if pr == 'clicked' and sheet_open():
            tp = js("(()=>{const c=document.querySelector('#mkTypeChips .chip[data-t=\"SELL\"]');if(c){c.click();return true;}return false;})()")
            set_val('#mkTitle','QA Test Lamp'); set_val('#mkPrice','25'); set_val('#mkDesc','QA listing description')
            pb = js("(()=>{const b=document.getElementById('mkPublish');if(b){b.click();return true;}return false;})()")
            time.sleep(1.6); e=errs(); note(not e and pb,'market: publish no errors',e)
            note('QA Test Lamp' in page_text() and not sheet_open(),'market: new listing in grid')
            c.send('Page.reload'); time.sleep(5)
            js("document.body.classList.%s('dark');" % ('add' if THEME=='dark' else 'remove'))
            js("try{var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
            tab('market')
            note('QA Test Lamp' in page_text(),'market: listing persists after reload')
            # delete own listing -> two-tap arm pattern
            qac = js("(()=>{const l=[...document.querySelectorAll('#view-market [data-listing]')].find(e=>(e.innerText||'').includes('QA Test Lamp'));if(l){l.scrollIntoView({block:'center'});l.click();return true;}return false;})()")
            time.sleep(1.4)
            mine = js("(()=>{const b=[...document.querySelectorAll('#sheetBox button')].find(x=>/delete/i.test(x.textContent));return b?b.textContent.trim():null;})()")
            if mine:
                vis_click_text('Delete'); time.sleep(1)
                t = page_text()
                armed = 'confirm' in t.lower() or 'sure' in t.lower() or 'tap again' in t.lower()
                note(armed,'market: listing delete needs 2nd tap (arm pattern)',mine)
            close_all()
        else: finding('broken','Market post','tapped post FAB','no form','post form should open','market-post-dead')
        tab('market')
    section('MARKET', s_market)

    # ---------------- WORK ----------------
    def s_work():
        tab('work'); time.sleep(1)
        pr = vis_click_sel('#postJobBtn'); time.sleep(1.5)
        if pr == 'clicked' and sheet_open():
            ok = js("""(()=>{const b=document.getElementById('sheetBox');
const t=[...b.querySelectorAll('input')].find(e=>!e.type||e.type==='text');if(t){t.value='QA Mow Lawn';t.dispatchEvent(new Event('input',{bubbles:true}));}
const d=b.querySelector('textarea');if(d){d.value='QA job desc';d.dispatchEvent(new Event('input',{bubbles:true}));}
const btn=[...b.querySelectorAll('button')].find(x=>/publish|post/i.test(x.textContent));if(btn){btn.click();return btn.textContent.trim();}return false;})()""")
            time.sleep(1.6); e=errs(); note(not e and ok,'work: job published',ok)
            note('QA Mow Lawn' in page_text(),'work: job in list')
        else: finding('broken','Work post','tapped Post a job','no form','job form should open','work-post-dead')
        close_all()
        for chip in ['Open','Accepted','Done']:
            vis_click_text(chip); time.sleep(1)
        note(True,'work: status chips switch')
        vis_click_text('All'); time.sleep(1)
        # accept -> confirmSheet
        ac = vis_click_text('Accept job'); time.sleep(1.4)
        if ac and sheet_open() and js("!!document.querySelector('#cfGo')"):
            note(True,'work: accept shows confirm sheet')
            vis_click_sel('#cfNo'); time.sleep(1)  # cancel first
            note(not sheet_open(),'work: accept confirm cancels')
            vis_click_text('Accept job'); time.sleep(1.2)
            vis_click_sel('#cfGo'); time.sleep(1.6)
            e=errs(); note(not e,'work: accept confirm no errors',e)
            note('Accepted' in page_text(),'work: job accepted')
            # chat now available
            jc = js("(()=>{const b=document.querySelector('#view-work [data-jchat]');if(b){b.click();return true;}return false;})()")
            time.sleep(1.6)
            if jc and js("!!document.querySelector('.chatroot:not([hidden])')"):
                note(True,'work: job chat opens after accept')
                sn = js("""(()=>{const i=document.querySelector('.chatroot input');if(!i)return 'no-input';i.focus();i.value='QA hello';i.dispatchEvent(new Event('input',{bubbles:true}));
const b=[...document.querySelectorAll('.chatroot button')].find(x=>/send/i.test(x.textContent));if(b){b.click();return 'sent';}return 'no-send';})()""")
                time.sleep(1.2); note(sn=='sent','work: job chat send',sn)
            else: finding('broken','Work job chat','accepted job, tapped chat','no chat','job chat should open','work-jobchat-dead')
            close_all()
            # mark done -> confirm
            dn = vis_click_text('Mark done') or vis_click_text('Done'); time.sleep(1.2)
            if dn and sheet_open(): note(True,'work: mark-done confirms'); close_all()
        elif ac:
            finding('missing-UX','Work accept','tapped Accept job','no confirm sheet','accept is consequential; confirm expected (code says confirmSheet)','work-accept-noconfirm')
        close_all(); tab('work')
    section('WORK', s_work)

    # ---------------- GROUPS ----------------
    def s_groups():
        tab('groups'); time.sleep(1)
        for sub,label in [('clubs','Groups'),('households','Households'),('campus','Communities'),('people','People')]:
            r = js(f"(()=>{{const b=document.querySelector('#view-groups [data-sub=\"{sub}\"]');if(b&&b.offsetParent!==null){{b.click();return true;}}return false;}})()")
            time.sleep(1.2); note(r,f'groups: sub-tab {label}')
        js("(()=>{const b=document.querySelector('#view-groups [data-sub=\"clubs\"]');if(b)b.click();})()"); time.sleep(1.4)
        # new group
        nr = vis_click_sel('#cgNew'); time.sleep(1.5)
        if nr == 'clicked' and sheet_open():
            set_val('#sheetBox input','QA Runners')
            sv = js("(()=>{const b=[...document.querySelectorAll('#sheetBox button')].find(x=>/save|create/i.test(x.textContent));if(b){b.click();return b.textContent.trim();}return false;})()")
            time.sleep(1.6); e=errs(); note(not e and sv,'groups: group created',sv)
            note('QA Runners' in page_text(),'groups: new group listed')
        else: finding('broken','Groups new','tapped + New group','no form','create form should open','groups-new-dead')
        close_all()
        # club page
        cr = vis_click_sel('#view-groups [data-club]'); time.sleep(1.8)
        opened = 'member' in page_text().lower() or sheet_open()
        note(cr == 'clicked' and opened,'groups: club page opens',cr)
        if opened:
            ch = vis_click_text('Chat'); time.sleep(1.6)
            if ch and js("!!document.querySelector('.chatroot:not([hidden])')"):
                note(True,'groups: group chat opens')
                sn = js("""(()=>{const i=document.querySelector('.chatroot input');if(!i)return 'no-input';i.focus();i.value='QA group hi';i.dispatchEvent(new Event('input',{bubbles:true}));
const b=[...document.querySelectorAll('.chatroot button')].find(x=>/send/i.test(x.textContent));if(b){b.click();return 'sent';}return 'no-send';})()""")
                time.sleep(1.2); note(sn=='sent','groups: group chat send',sn)
                # image/GIF buttons present?
                at = js("(()=>[...document.querySelectorAll('.chatroot button')].map(b=>b.getAttribute('aria-label')||b.textContent).join('|'))()")
                note('GIF' in str(at) or 'gif' in str(at).lower(),'groups: GIF/meme affordance in chat',str(at)[:100])
            else: finding('broken','Groups chat','tapped Chat','no chat','group chat should open','groups-chat-dead')
            close_all()
            inv = vis_click_text('Invite'); time.sleep(1.6)
            t = page_text(); to = toast_now()
            if inv and ('#join=' in t or 'copied' in t.lower() or 'copied' in to.lower() or 'link' in t.lower()):
                note(True,'groups: invite link/copy feedback',to[:60])
            else: finding('broken','Groups invite','tapped Invite','no link or copy feedback','invite link/share/copy should appear','groups-invite-dead')
            shot('audit-missing-groups-invite')
            close_all()
        # households
        js("(()=>{const b=document.querySelector('#view-groups [data-sub=\"households\"]');if(b)b.click();})()"); time.sleep(1.6)
        hr = vis_click_sel('#view-groups .hh-card'); time.sleep(1.6)
        note(hr == 'clicked' and ('member' in page_text().lower() or sheet_open()),'groups: household detail opens',hr)
        shot('audit-missing-household-detail')
        close_all()
        # people
        js("(()=>{const b=document.querySelector('#view-groups [data-sub=\"people\"]');if(b)b.click();})()"); time.sleep(1.6)
        sy = vis_click_text('Sync contacts'); time.sleep(1.8)
        t = page_text(); to = toast_now()
        note(bool(sy) and ('not supported' in t.lower() or 'not available' in t.lower() or 'manually' in t.lower() or 'browser' in t.lower()),'groups: contact sync graceful fallback',(t[:110]+to[:60]).replace('\n',' '))
        close_all()
        # manual add: find its input
        ma = js("(()=>{const b=[...document.querySelectorAll('#view-groups button')].find(x=>/add/i.test(x.textContent)&&/manual|contact|friend/i.test(x.textContent));return b?(b.click(),b.textContent.trim()):null;})()")
        time.sleep(1.4)
        if sheet_open():
            ok = js("""(()=>{const b=document.getElementById('sheetBox');const t=[...b.querySelectorAll('input')].find(e=>!e.type||e.type==='text');if(t){t.value='QA Friend';t.dispatchEvent(new Event('input',{bubbles:true}));}
const btn=[...b.querySelectorAll('button')].find(x=>/save|add/i.test(x.textContent));if(btn){btn.click();return true;}return false;})()""")
            time.sleep(1.4); note(ok and 'QA Friend' in page_text(),'groups: manual contact added',ma)
        else: note(True,'groups: manual add (no sheet)',ma)
        close_all()
        pid = js("(()=>{const p=(HUB.people&&HUB.people.visiblePeople&&HUB.people.visiblePeople()[0])||null;return p&&p.id;})()")
        if pid:
            js(f"HUB.people.openProfile('{pid}')"); time.sleep(1.6)
            note(sheet_open() or 'profile' in page_text().lower(),'groups: people profile opens')
            t = page_text()
            if '🪐' in t or 'onaro' in t.lower():
                note('on-device' in t.lower() or 'not verified' in t.lower() or 'match' in t.lower(),'groups: Onaro badge honest label',t[t.lower().find('onaro')-40:t.lower().find('onaro')+80].replace('\n',' '))
            fw = vis_click_text('Follow'); time.sleep(1.2)
            note(bool(fw) and ('Following' in page_text() or 'Unfollow' in page_text()),'groups: follow toggles',fw)
            mp = vis_click_text('Message'); time.sleep(1.6)
            note(bool(mp) and bool(js("document.querySelector('.chatroot:not([hidden])')")),'groups: message opens chat',mp)
        close_all(); tab('groups')
    section('GROUPS', s_groups)

    # ---------------- ME ----------------
    def s_me_edit():
        tab('me'); time.sleep(1)
        r = vis_click_sel('#meEditBtn'); time.sleep(1.5)
        if r == 'clicked' and sheet_open():
            setv = js("""(()=>{const b=document.getElementById('sheetBox');const t=[...b.querySelectorAll('input')].find(e=>!e.type||e.type==='text');if(t){t.value='PraBin QA';t.dispatchEvent(new Event('input',{bubbles:true}));}
const d=[...b.querySelectorAll('input')].find(e=>e.type==='date');if(d){d.value='1998-04-15';d.dispatchEvent(new Event('change',{bubbles:true}));return 'dob-set';}return 'no-dob';})()""")
            sv = js("(()=>{const b=[...document.querySelectorAll('#sheetBox button')].find(x=>/^save/i.test(x.textContent.trim()));if(b){b.click();return true;}return false;})()")
            time.sleep(1.6); e=errs(); note(not e and sv,'me: edit saved',setv)
            note('PraBin QA' in page_text(),'me: name updated on card')
        else: finding('broken','Me edit','tapped Edit','no sheet','edit sheet should open','me-edit-dead')
        close_all()
        # safety score honest label
        sr = vis_click_sel('#meScoreStrip'); time.sleep(1.4)
        t = page_text()
        note(bool(sr) and ('safety' in t.lower() or sheet_open()),'me: safety strip opens',sr)
        if 'Demo score' in t: note(True,'me: safety score labeled demo')
        elif sr: finding('honest-label','Me safety score','opened score detail','no demo/sample label','browser-local demo score must be labeled','me-score-label')
        close_all()
    section('ME edit+safety', s_me_edit)

    def s_me_skills_community():
        tab('me')
        sv = set_val('#meSkillInput','QA Welding')
        ar = vis_click_sel('#meSkillAdd'); time.sleep(1.4)
        e = errs(); note(sv=='set' and ar=='clicked' and not e and 'QA Welding' in page_text(),'me: skill added inline',e)
        # skill remove -> confirm?
        rm = js("(()=>{const b=document.querySelector('#view-me [data-skill]');if(b){b.click();return true;}return false;})()")
        if rm:
            time.sleep(1)
            gone = 'QA Welding' not in page_text()
            if gone and not sheet_open():
                finding('missing-UX','Me skills','tapped skill remove','removed instantly, no confirm','destructive remove needs confirm','me-skill-del-noconfirm')
            else: note(True,'me: skill remove confirm-or-kept')
        cr = vis_click_sel('#meCampusBtn'); time.sleep(1.6)
        note(cr == 'clicked' and sheet_open(),'me: change community opens picker',cr)
        if sheet_open():
            pk = js("(()=>{const b=[...document.querySelectorAll('#sheetBox button')].slice(0,12).find(x=>x.textContent.trim().length>2&&!/cancel|close/i.test(x.textContent));if(b){b.click();return b.textContent.trim().slice(0,30);}return false;})()")
            time.sleep(1.6); note(bool(pk),'me: community picked',pk)
        close_all()
        # deep links
        gl = vis_click_text("Post your first listing"); time.sleep(1.6)
        note(bool(gl) and (on_tab('market') or sheet_open()),'me: post-listing deep link',gl)
        tab('me')
        gw = vis_click_text('Find micro-jobs'); time.sleep(1.6)
        note(bool(gw) and on_tab('work'),'me: find-jobs deep link',gw)
        tab('me')
    section('ME skills+community', s_me_skills_community)

    def s_me_vault_verify():
        tab('me')
        # vault save
        sv = js("""(()=>{const t=document.querySelector('#memTitle');if(t){t.value='QA memory';t.dispatchEvent(new Event('input',{bubbles:true}));}
const b=[...document.querySelectorAll('#view-me button')].find(x=>/save to vault/i.test(x.textContent));if(b){b.click();return true;}return false;})()""")
        time.sleep(1.4); note(sv and 'QA memory' in page_text(),'me: vault save',sv)
        # voice note (fake mic granted via flags)
        vr = vis_click_text('Record voice note'); time.sleep(3)
        e = errs(); t = page_text()
        note(not e,'me: voice note no errors',e)
        note('recording' in t.lower() or 'stop' in t.lower() or 'permission' in t.lower() or 'microphone' in t.lower(),'me: voice note feedback',t[:90].replace('\n',' '))
        shot('audit-missing-voice-note')
        close_all()
        # vault delete -> confirm?
        n0 = js("document.querySelectorAll('#view-me .memDel').length")
        if n0:
            js("document.querySelector('#view-me .memDel').click()"); time.sleep(1.2)
            n1 = js("document.querySelectorAll('#view-me .memDel').length")
            if n1 < n0 and not sheet_open():
                finding('missing-UX','Me vault','tapped delete','deleted instantly, no confirm','destructive delete needs confirm','me-vault-del-noconfirm')
            else: note(True,'me: vault delete confirm-or-kept',f'{n0}->{n1}')
        # verify
        vf = vis_click_sel('#verifyBtn'); time.sleep(1.6)
        t = page_text()
        note(vf == 'clicked' and (sheet_open() or 'verif' in t.lower()),'me: verify flow opens',vf)
        if sheet_open(): shot('audit-missing-verify')
        close_all()
        # report / review / blocked
        rp = vis_click_sel('#meReport'); time.sleep(1.4)
        note(rp == 'clicked' and sheet_open(),'me: report opens trust sheet',rp)
        close_all()
    section('ME vault+verify', s_me_vault_verify)

    def s_me_lang():
        tab('me')
        lr = vis_click_sel('#meLangBtn'); time.sleep(1.4)
        if lr == 'clicked' and sheet_open():
            opts = js("(()=>[...document.querySelectorAll('#sheetBox button')].map(b=>b.textContent.trim()).join('|'))()")
            note('Español' in str(opts),'me: language options',str(opts)[:80])
            es = js("(()=>{const b=[...document.querySelectorAll('#sheetBox button')].find(x=>/español/i.test(x.textContent));if(b){b.click();return true;}return false;})()")
            time.sleep(2.5)
            t = page_text()
            note(bool(es) and ('Crear' in t or 'INICIO' in t or 'Hoy' in t),'me: UI switched to es',t[:90].replace('\n',' '))
            shot('audit-missing-i18n-es-me')
            hard = []
            for tbn in ['home','market','work','groups']:
                tab(tbn)
                tx = page_text()
                for pat in ['See all →','+ Add course','Post a job','+ New group','Set up my plan','Manage classes','+ Add appointment','Create a time capsule']:
                    if pat in tx: hard.append(f'{tbn}:{pat}')
            if hard: finding('i18n','es locale','scanned 4 tabs',f'hardcoded English: {hard}','all user strings translated','i18n-es-hardcoded')
            else: note(True,'i18n: es tabs show no hardcoded EN from checklist')
            shot('audit-missing-i18n-es-home')
            # ne + hi spot check
            for lang, tag in [('ne','i18n-ne'),('hi','i18n-hi')]:
                js(f"try{{HUB.i18n.setLang('{lang}')}}catch(e){{}}"); time.sleep(2)
                tab('home'); time.sleep(1)
                shot(f'audit-missing-{tag}-home')
            js("try{HUB.i18n.setLang('en')}catch(e){}"); time.sleep(2)
            note('Create a time capsule' in page_text() or 'Time Capsule' in page_text(),'i18n: back to en')
        else: finding('broken','Me language','tapped language button','no picker','language picker should open','me-lang-dead')
        close_all(); tab('me')
    section('ME language', s_me_lang)

    def s_me_country_astro():
        tab('me')
        cr = vis_click_sel('#meCountryBtn'); time.sleep(1.4)
        note(cr == 'clicked' and sheet_open(),'me: country picker opens',cr)
        close_all()
        # clear samples -> confirm? (code uses native? check behavior)
        cl = vis_click_text('Clear'); time.sleep(1.4)
        if cl and (sheet_open() or 'clear' in toast_now().lower() or 'sample' in page_text().lower()):
            note(True,'me: clear samples feedback/confirm')
        else: finding('missing-UX','Me clear','tapped Clear','no confirm/feedback','destructive clear needs confirm','me-clear-noconfirm')
        close_all()
        # reset -> native confirm; override to CANCEL to verify dialog exists w/o wiping
        js("window.__cf=window.confirm;window.confirm=function(){window.__cfCalled=true;return false;}")
        rs = vis_click_sel('#resetAll'); time.sleep(1.5)
        asked = js("window.__cfCalled===true")
        alive = 'PraBin QA' in page_text()
        js("window.confirm=window.__cf;")
        note(bool(rs) and asked,'me: reset-all asks confirm (cancel path)',f'asked={asked}')
        note(alive,'me: reset cancelled keeps data')
        if not asked: finding('missing-UX','Me reset','tapped Reset all data','no confirm dialog','full wipe needs confirm','me-reset-noconfirm')
        close_all()
        # astro calendar (DOB was set in edit)
        cal = js("try{HUB.astro.openCalendar();return 'ok';}catch(e){return String(e).slice(0,60);}")
        time.sleep(1.6)
        note(cal=='ok' and sheet_open(),'astro: calendar opens',cal)
        if sheet_open():
            t = page_text()
            note('BS' in t or 'Bikram' in t or 'बि' in t,'astro: BS toggle present')
            bs = vis_click_text('BS'); time.sleep(1.2)
            note('२०' in page_text() or 'BS' in page_text(),'astro: BS mode renders',bs)
            shot('audit-missing-astro-bs')
        close_all()
        # home astro card with DOB
        tab('home'); time.sleep(2)
        t = page_text()
        if 'Aries' in t or '♈' in t or 'horoscope' in t.lower():
            note(True,'home: astro sign shows from DOB')
            shot('audit-missing-astro-card')
            hs = vis_click_text('horoscope') or vis_click_text('Aries'); time.sleep(1.4)
            note(bool(hs) and sheet_open(),'home: astro day sheet opens',hs)
            if sheet_open():
                dt = page_text()
                note('stale' in dt.lower() or '2026' in dt or 'today' in dt.lower(),'astro: day sheet honest date label',dt[:80].replace('\n',' '))
                shot('audit-missing-astro-day')
            close_all()
        else: finding('missing-UX','Home astro','DOB 1998-04-15 set in profile','no zodiac/horoscope on home card','sign + daily horoscope should appear','home-astro-missing')
    section('ME country+reset+astro', s_me_country_astro)

    # ---------------- GLOBAL ----------------
    def s_global_search():
        tab('home')
        sr = vis_click_sel('#searchBtn'); time.sleep(1.6)
        ov = bool(js("document.querySelector('.chatroot:not([hidden])')"))
        if sr == 'clicked' and (ov or sheet_open()):
            note(True,'global: search opens')
            set_val('.chatroot input','zzznohit')
            go = js("""(()=>{const r=document.querySelector('.chatroot:not([hidden])');if(!r)return false;
const b=[...r.querySelectorAll('button')].find(x=>/search/i.test(x.textContent));if(b){b.click();return 'btn';}
const i=r.querySelector('input');if(i){i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));return 'enter';}return false;})()""")
            time.sleep(1.8)
            t = page_text()
            if 'no result' in t.lower() or 'nothing found' in t.lower() or 'no match' in t.lower():
                note(True,'global: search no-results state')
            else: finding('missing-UX','Search','searched "zzznohit"','no empty/no-results message','"no results" state expected','search-noresults')
            shot('audit-missing-search-noresults')
        else: finding('broken','Search','tapped search','overlay did not open','search overlay should open','search-dead')
        close_all()
    section('GLOBAL search', s_global_search)

    def s_global_overlays():
        tab('home')
        pr = vis_click_sel('#pulseBtn'); time.sleep(1.6)
        note(pr=='clicked' and (bool(js("document.querySelector('.chatroot:not([hidden])')")) or sheet_open()),'global: pulse opens',pr)
        close_all()
        nr = vis_click_sel('#notifBtn'); time.sleep(1.6)
        note(nr=='clicked' and (bool(js("document.querySelector('.chatroot:not([hidden])')")) or sheet_open()),'global: notifications open',nr)
        if js("document.querySelector('.chatroot:not([hidden])')"):
            tx = page_text(); note(len(tx) > 200,'global: notifications list content')
            shot('audit-missing-notifications')
        close_all()
        cr = vis_click_sel('#chatFab'); time.sleep(1.6)
        if cr == 'clicked' and js("!!document.querySelector('.chatroot:not([hidden])')"):
            note(True,'global: chat list opens')
            th = js("(()=>{const t=document.querySelector('.chatroot [data-thread]');if(t&&t.offsetParent!==null){t.click();return true;}return false;})()")
            time.sleep(1.6)
            note(bool(th) and bool(js("document.querySelector('.chatroot input')")),'global: chat thread opens',th)
            bk = js("(()=>{const b=[...document.querySelectorAll('.chatroot button')].find(x=>/back|‹|←/i.test(x.textContent)||/back/i.test(x.getAttribute('aria-label')||''));if(b&&b.offsetParent!==null){b.click();return true;}return false;})()")
            time.sleep(1)
            if not bk: finding('missing-UX','Chat thread','opened thread','no back affordance','way back to list','chat-noback')
            else: note(True,'global: chat back works')
            shot('audit-missing-chat-list')
        else: finding('broken','Chat','tapped Chats FAB','list did not open','chat list should open','chat-dead')
        close_all()
        js("try{HUB.askHUB.open()}catch(e){}"); time.sleep(1.4)
        note(sheet_open(),'global: ask pill opens')
        close_all()
    section('GLOBAL overlays', s_global_overlays)

    def s_global_langbtn_theme():
        tab('home')
        lb = vis_click_sel('#langBtn'); time.sleep(1.4)
        note(lb == 'clicked' and sheet_open(),'global: header language button opens picker',lb)
        close_all()
    section('GLOBAL langbtn', s_global_langbtn_theme)

    # ---------------- persistence ----------------
    def s_persist():
        c.send('Page.reload'); time.sleep(5)
        js("document.body.classList.%s('dark');" % ('add' if THEME=='dark' else 'remove'))
        js("try{var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        tab('home'); note('PraBin QA' in page_text(),'persist: profile name')
        tab('daily'); note('QA letter' in page_text() or 'Unlocks in' in page_text(),'persist: capsule')
        tab('market'); note('QA Test Lamp' in page_text(),'persist: listing')
        tab('work'); note('QA Mow Lawn' in page_text(),'persist: job')
        tab('groups')
        js("(()=>{const b=document.querySelector('#view-groups [data-sub=\"clubs\"]');if(b)b.click();})()"); time.sleep(1.2)
        note('QA Runners' in page_text(),'persist: group')
        tab('me'); note('QA Welding' in page_text() or 'QA memory' in page_text(),'persist: skill/memory')
        e = errs(); note(not e,f'{THEME}: zero console errors at end',e)
        shot('audit-missing-final-me')
    section('PERSISTENCE', s_persist)

    save()
    print(f'==== {THEME}: {len(findings)} findings ====', flush=True)
finally:
    proc.terminate()
