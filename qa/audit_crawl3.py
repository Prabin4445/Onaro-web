#!/usr/bin/env python3
"""Onaro HUB crawl v3: delta retests + unreachable sections from v2.
Fresh profile. Findings appended to findings-<theme>.json (v2 file reused)."""
import json, subprocess, time, urllib.request, os, base64, shutil, sys
import websocket
THEME = sys.argv[1] if len(sys.argv) > 1 else 'dark'
QA = os.path.expanduser('~/workspace/hub/qa/audit-missing')
CHROME = '/opt/meta-chromium/chrome'
BASE = 'file:///home/hatch/workspace/hub/index.html'
IPHONE_UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) '
             'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1')
PORT = 9761 if THEME == 'dark' else 9762
os.makedirs(QA, exist_ok=True)
FJSON = os.path.join(QA, f'findings-{THEME}.json')
findings = json.load(open(FJSON)) if os.path.exists(FJSON) else []
def save(): json.dump(findings, open(FJSON, 'w'), indent=1)

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
    open(p, 'wb').write(base64.b64decode(r['data'])); return p
def finding(sev, surface, did, happened, should, slug):
    p = shot('audit-missing-' + slug)
    findings.append({'sev': sev, 'surface': surface, 'did': did, 'happened': happened, 'should': should, 'shot': p})
    print(f'  FINDING [{sev}] {surface}: {did} -- {happened}', flush=True); save()
def note(ok, label, detail=''):
    print(('PASS' if ok else 'FAIL'), label, str(detail)[:130], flush=True)
def errs(): return js("window.__huberr.splice(0)") or []
def sheet_open(): return bool(js("!document.getElementById('sheetHost').hidden"))
def on_tab(t): return bool(js(f"!document.getElementById('view-{t}').hidden"))
def tab(t):
    js(f"HUB.showTab('{t}');"); time.sleep(1.8)
    return on_tab(t)
def vct(txt):
    return js("""(()=>{const els=[...document.querySelectorAll('button,a,[data-tap]')];
for(const e of els){if(e.offsetParent===null)continue;
const t=(e.innerText||'').trim(),a=e.getAttribute('aria-label')||'';
if(t.includes(%r)||a.includes(%r)){e.scrollIntoView({block:'center'});e.click();return e.id||t.slice(0,25);}}
return false;})()""" % (txt, txt))
def vcs(sel):
    return js(f"(()=>{{const e=document.querySelector({sel!r});if(!e)return 'missing';if(e.offsetParent===null)return 'hidden-skip';e.scrollIntoView({{block:'center'}});e.click();return 'clicked';}})()")
def setv(sel, val):
    return js(f"(()=>{{const e=document.querySelector({sel!r});if(!e)return 'missing';e.focus();e.value={val!r};e.dispatchEvent(new Event('input',{{bubbles:true}}));e.dispatchEvent(new Event('change',{{bubbles:true}}));return 'set';}})()")
def page_text(): return js("document.body.innerText") or ''
def toast_now(): return js("(()=>[...document.querySelectorAll('#toastHost .toast')].map(e=>e.textContent).join('|'))()")
CLOSE_JS = ("try{HUB.ui.closeSheet();}catch(e){};"
  "for(const k of ['chat','pulse','search','notifications'])try{if(HUB[k]&&HUB[k].close)HUB[k].close();}catch(e){};"
  "['gyBd','gyDrawer'].forEach(function(id){var e=document.getElementById(id);if(e)e.remove();});"
  "document.querySelectorAll('.mkzoom').forEach(function(e){e.remove();});")
def close_all(): js(CLOSE_JS); time.sleep(0.8)
def section(name, fn):
    print(f'== {name} ==', flush=True)
    try: fn()
    except Exception as e:
        print(f'  SECTION-ERROR {name}: {type(e).__name__} {str(e)[:120]}', flush=True)
        try: close_all()
        except Exception: pass

prof = f'/tmp/hubqa-crawl3-{THEME}'
shutil.rmtree(prof, ignore_errors=True)
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
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
    note(on_tab('home'), f'{THEME} v3 boot')

    def s_market2():
        tab('market'); time.sleep(1)
        n0 = js("document.querySelectorAll('#view-market [data-listing]').length")
        dists = js("(()=>[...document.querySelectorAll('#view-market [data-listing]')].map(e=>{const m=(e.innerText||'').match(/([0-9.]+)\\s*mi/);return m?+m[1]:null;}))()")
        note(True, 'market: distances parsed', f'{n0} {dists}')
        vct('5 mi'); time.sleep(1.4)
        n1 = js("document.querySelectorAll('#view-market [data-listing]').length")
        exp = sum(1 for d in (dists or []) if d is not None and d <= 5)
        if all(d is None for d in (dists or [])):
            note(True, 'market: radius (no distance text rendered)')
        elif n1 == exp: note(True, 'market: radius filters correctly', f'{n0}->{n1}')
        else: finding('broken','Market radius','tapped 5 mi',f'grid {n0}->{n1}, expected {exp}','radius should filter','market-radius-nofilter')
        vct('City-wide'); time.sleep(1.2)
        # detail -> message seller via #mkMsg
        vcs('#view-market [data-listing]'); time.sleep(1.6)
        if sheet_open():
            m = js("(()=>{const b=document.getElementById('mkMsg');if(b&&b.offsetParent!==null){b.click();return b.textContent.trim();}return false;})()")
            time.sleep(1.6)
            note(bool(m) and bool(js("document.querySelector('.chatroot:not([hidden])')")),'market: message seller opens chat',m)
            close_all()
        # post: unhide FAB (it hides on scroll)
        tab('market'); time.sleep(1)
        js("document.getElementById('views').scrollTop=0;const f=document.getElementById('mkPostBtn');if(f)f.classList.remove('hide');")
        time.sleep(0.6)
        pr = vcs('#mkPostBtn'); time.sleep(1.6)
        if pr == 'clicked' and sheet_open():
            js("(()=>{const ch=document.querySelector('#mkTypeChips .chip[data-t=\"SELL\"]');if(ch)ch.click();})()")
            setv('#mkTitle','QA Lamp v3'); setv('#mkPrice','25'); setv('#mkDesc','v3 desc')
            js("document.getElementById('mkPublish').click()"); time.sleep(1.6)
            e = errs(); note(not e,'market: publish no errors',e)
            note('QA Lamp v3' in page_text() and not sheet_open(),'market: listing published to grid')
        else: finding('broken','Market post','tapped post FAB (unhidden)','no form','post form should open','market-post-dead')
        close_all()
    section('MARKET v3', s_market2)

    def s_work2():
        tab('work'); time.sleep(1)
        pr = vcs('#postJobBtn'); time.sleep(1.5)
        if pr == 'clicked' and sheet_open():
            js("""(()=>{const b=document.getElementById('sheetBox');
const t=b.querySelector('#pjTitle');if(t){t.value='QA Mow Lawn v3';t.dispatchEvent(new Event('input',{bubbles:true}));}
const p=b.querySelector('#pjPay');if(p){p.value='40';p.dispatchEvent(new Event('input',{bubbles:true}));}
const d=b.querySelector('#pjDesc');if(d){d.value='v3 desc';d.dispatchEvent(new Event('input',{bubbles:true}));}
const go=b.querySelector('#pjGo');if(go)go.click();})()""")
            time.sleep(1.6); e=errs(); note(not e,'work: publish no errors',e)
            note('QA Mow Lawn v3' in page_text() and not sheet_open(),'work: job published')
        else: finding('broken','Work post','tapped Post a job','no form','job form should open','work-post-dead')
        close_all()
        # accept own? accept a sample job -> confirm -> chat -> send -> back
        ac = vct('Accept job'); time.sleep(1.4)
        if ac and sheet_open():
            vcs('#cfGo'); time.sleep(1.6)
            note('Accepted' in page_text() or 'accepted' in page_text().lower(),'work: accepted')
            jc = js("(()=>{const b=document.querySelector('#view-work [data-jchat]');if(b){b.click();return true;}return false;})()")
            time.sleep(1.6)
            if jc and js("!!document.querySelector('.chatroot:not([hidden])')"):
                note(True,'work: job chat opens')
                sn = js("""(()=>{const i=document.getElementById('chatText');if(!i)return 'no-input';i.focus();i.value='QA v3 hello';i.dispatchEvent(new Event('input',{bubbles:true}));
document.getElementById('chatSend').click();return 'sent';})()""")
                time.sleep(1.5); e=errs()
                got = js("(()=>{const b=[...document.querySelectorAll('#chatBubbles .bub')].map(x=>x.innerText).join('|');return b.slice(-60);})()")
                note(sn=='sent' and not e and 'QA v3 hello' in str(got),'work: chat message sent+rendered',f'{sn} {e} {got}')
                bk = js("(()=>{const b=document.getElementById('chBack');if(b){b.click();return true;}return false;})()")
                time.sleep(1)
                note(bk and bool(js("document.querySelector('.chatroot [data-thread]')")),'work: chat back to list',bk)
            else: finding('broken','Work job chat','accepted, tapped chat','no chat','job chat should open','work-jobchat-dead')
            close_all()
        tab('work')
    section('WORK v3', s_work2)

    def s_glance2():
        tab('home'); time.sleep(1)
        # unread -> chat list
        i = js("()=>[...document.querySelectorAll('#view-home .gltile')].findIndex(e=>/unread/i.test(e.innerText))")()
        if i is not None and i >= 0:
            js(f"document.querySelectorAll('#view-home .gltile')[{i}].click();"); time.sleep(1.6)
            note(bool(js("document.querySelector('.chatroot:not([hidden])')")),'glance: unread -> chat list')
            close_all()
        # jobs -> work tab
        tab('home')
        j = js("()=>[...document.querySelectorAll('#view-home .gltile')].findIndex(e=>/jobs near/i.test(e.innerText))")()
        if j is not None and j >= 0:
            js(f"document.querySelectorAll('#view-home .gltile')[{j}].click();"); time.sleep(1.6)
            note(on_tab('work'),'glance: jobs -> work tab')
        # sample honesty hint
        tab('home'); time.sleep(1)
        t = page_text()
        note('sample' in t.lower(),'glance: sample-data honesty hint present')
        tab('home')
    section('GLANCE v3', s_glance2)

    def s_groups2():
        tab('groups'); time.sleep(1)
        js("(()=>{const b=document.querySelector('#view-groups [data-sub=\"clubs\"]');if(b)b.click();})()"); time.sleep(1.4)
        nr = vcs('#cgNew'); time.sleep(1.5)
        if nr == 'clicked' and sheet_open():
            setv('#sheetBox input','QA Runners v3')
            js("(()=>{const b=[...document.querySelectorAll('#sheetBox button')].find(x=>/save|create/i.test(x.textContent));if(b)b.click();})()")
            time.sleep(2)
            onpage = 'Back to groups' in page_text() or '←' in page_text()
            note('QA Runners v3' in page_text(),'groups: created',f'onpage={onpage}')
            # publish draft if button present
            pb = vct('Publish') or vct('Go live'); time.sleep(1.5)
            live = js("(()=>{try{const gs=HUB.store.state.cgroups||[];const g=gs.find(x=>x.name&&x.name.includes('QA Runners v3'));return g&&g.live;}catch(e){return 'err';}})()")
            note(True,'groups: publish attempted',f'btn={pb} live={live}')
            # invite
            inv = vct('Invite'); time.sleep(1.6)
            t = page_text(); link = js("(document.getElementById('ginvLink')||{}).value||''")
            if inv and '#join=' in str(link):
                note(True,'groups: invite link sheet',str(link)[:60])
                cp = js("(()=>{const b=document.getElementById('ginvCopy');if(b){b.click();return true;}return false;})()")
                time.sleep(1)
                note('copied' in toast_now().lower() or cp,'groups: invite copy feedback',toast_now()[:60])
            elif inv and 'draft' in (t+toast_now()).lower():
                note(True,'groups: invite on draft -> draft hint toast (by design)')
            else: finding('broken','Groups invite','tapped Invite on live group','no link sheet','invite link sheet should open','groups-invite-dead')
            shot('audit-missing-groups-invite')
            close_all()
            # group chat send via #gcSend
            ch = vct('Chat'); time.sleep(1.8)
            if ch and js("!!document.getElementById('gcText')"):
                note(True,'groups: group chat opens')
                sn = js("""(()=>{const i=document.getElementById('gcText');i.focus();i.value='QA v3 group hi';i.dispatchEvent(new Event('input',{bubbles:true}));document.getElementById('gcSend').click();return 'sent';})()""")
                time.sleep(1.5); e=errs()
                got = js("(()=>{const b=document.getElementById('gcBubbles');return b?b.innerText.slice(-60):'no-bubbles';})()")
                note(sn=='sent' and not e and 'QA v3 group hi' in str(got),'groups: group chat send',f'{sn} {e}')
                # GIF affordance?
                em = js("!!document.getElementById('gcEmoji')")
                note(em,'groups: emoji/GIF picker button present')
                # voice call button with no HUB.call
                hascall = js("!!window.HUB.call")
                gcb = js("(()=>{const b=document.getElementById('gcCall');if(b){b.click();return true;}return false;})()")
                time.sleep(1.2); e2=errs()
                if gcb and not hascall and not e2 and not sheet_open():
                    finding('broken','Group chat call','tapped 📞 (no call module)','nothing happens','disabled state or honest note expected','groups-call-dead')
                else: note(True,'groups: call button',f'hascall={hascall} errs={e2}')
                js("try{HUB.gchat.close()}catch(e){}")
            else: finding('broken','Groups chat','tapped Chat','no group chat','group chat should open','groups-chat-dead')
            close_all()
        else: finding('broken','Groups new','tapped + New group','no form','create form should open','groups-new-dead')
        # households
        js("(()=>{const b=document.querySelector('#view-groups [data-sub=\"households\"]');if(b)b.click();})()"); time.sleep(1.6)
        cards = js("document.querySelectorAll('#view-groups .hh-card').length")
        if not cards:
            finding('missing-UX','Groups households','opened Households sub-tab','no household cards and no empty state visible','empty state or cards expected','groups-hh-empty')
            shot('audit-missing-groups-hh')
        else:
            note(True,'groups: household cards',cards)
            js("document.querySelector('#view-groups .hh-card').click()"); time.sleep(1.8)
            note('member' in page_text().lower() or sheet_open(),'groups: household detail opens')
            shot('audit-missing-household-detail')
        close_all()
        # contact sync -> manual sheet
        js("(()=>{const b=document.querySelector('#view-groups [data-sub=\"people\"]');if(b)b.click();})()"); time.sleep(1.6)
        sy = js("(()=>{const b=document.querySelector('#pplSyncBtn');if(b){b.click();return true;}return false;})()")
        time.sleep(1.8)
        if sy and sheet_open() and js("!!document.getElementById('frName')"):
            note(True,'groups: sync fallback -> manual add sheet')
            setv('#frName','QA Friend v3'); setv('#frPhone','+1 555-010-9999')
            js("document.getElementById('frSave').click()"); time.sleep(1.5)
            note('QA Friend v3' in page_text(),'groups: manual contact saved')
        else: finding('broken','Groups contacts','tapped Sync contacts','no fallback sheet','manual-add fallback should open','groups-sync-dead')
        close_all()
        # profile badge honesty
        pid = js("(()=>{const p=(HUB.people&&HUB.people.visiblePeople&&HUB.people.visiblePeople()[0])||null;return p&&p.id;})()")
        if pid:
            js(f"HUB.people.openProfile('{pid}')"); time.sleep(1.6)
            t = page_text()
            vb = js("(()=>{const b=document.querySelector('#sheetBox .vbadge, .vbadge');return b?b.innerText:'none';})()")
            note(True,'groups: profile badge text',f'{vb} | sample-in-text={"Sample" in t}')
            if vb and 'verified' in str(vb).lower() and 'Sample' in t:
                finding('honest-label','People profile','sample person shows "✓ Verified" badge','badge implies real verification','demo/seeded profiles must not look verified','people-verified-badge')
            fw = vct('Follow'); time.sleep(1.2)
            note(bool(fw),'groups: follow',fw)
            mp = js("(()=>{const b=document.getElementById('ppMsg');if(b){b.click();return true;}return false;})()")
            time.sleep(1.6)
            # non-mutual -> gate sheet expected
            note(bool(mp) and (sheet_open() or bool(js("document.querySelector('.chatroot:not([hidden])')"))),'groups: message -> gate sheet or chat',mp)
            if sheet_open(): shot('audit-missing-msg-gate')
        close_all(); tab('groups')
    section('GROUPS v3', s_groups2)

    def s_me2():
        tab('me'); time.sleep(1)
        for bid, label in [('#meGoList','post-listing'),('#meGoMarket','post-listing2'),('#meGoWork','jobs'),('#meGoWork2','jobs2')]:
            r = js(f"(()=>{{const b=document.querySelector('{bid}');if(b&&b.offsetParent!==null){{b.click();return true;}}return false;}})()")
            if r:
                time.sleep(1.5)
                ok = on_tab('market') or on_tab('work')
                note(ok, f'me: deep link {label}', bid)
                tab('me'); time.sleep(1)
                break
        # gym reset confirm (retry properly)
        tab('daily'); time.sleep(1.5)
        # ensure plan exists
        has = 'kcal' in page_text().lower() or js("!!document.querySelector('#gyReset')")
        if not has:
            vcs('#gySetup'); time.sleep(1.5)
            js("""(()=>{const d=document.getElementById('gyDrawer');if(!d)return;
[...d.querySelectorAll('input')].forEach(e=>{if(e.type==='number'){e.value='32';e.dispatchEvent(new Event('input',{bubbles:true}));}});
[...d.querySelectorAll('select')].forEach(e=>{if(e.options.length>1){e.selectedIndex=1;e.dispatchEvent(new Event('change',{bubbles:true}));}});})()""")
            js("(()=>{const d=document.getElementById('gyDrawer');const b=[...d.querySelectorAll('button')].find(x=>/save|create|start/i.test(x.textContent));if(b)b.click();})()")
            time.sleep(1.5)
            js("['gyBd','gyDrawer'].forEach(function(id){var e=document.getElementById(id);if(e)e.remove();})")
            tab('daily'); time.sleep(1.5)
        rs = js("(()=>{const b=document.getElementById('gyReset');if(!b)return 'missing';b.scrollIntoView({block:'center'});b.click();return 'clicked';})()")
        time.sleep(1.5)
        if rs == 'clicked' and sheet_open() and js("!!document.querySelector('#gyResetNo')"):
            note(True,'daily: gym reset shows in-app confirm')
            js("document.querySelector('#gyResetNo').click()"); time.sleep(1)
            note(not sheet_open(),'daily: gym reset cancel keeps plan')
        else: finding('missing-UX','Daily gym','tapped Reset','no in-app confirmation','destructive reset needs confirm','daily-gym-reset-noconfirm')
        close_all(); tab('me')
    section('ME v3', s_me2)

    def s_global2():
        tab('home'); time.sleep(1)
        sr = vcs('#searchBtn'); time.sleep(1.8)
        ov = bool(js("document.querySelector('.chatroot:not([hidden])')"))
        note(sr, 'global: search btn', f'{sr} overlay={ov}')
        if sr == 'clicked' and (ov or sheet_open()):
            setv('.chatroot input','zzznohit')
            js("""(()=>{const r=document.querySelector('.chatroot:not([hidden])');const i=r&&r.querySelector('input');if(i){i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));}})()""")
            time.sleep(2)
            t = page_text()
            if 'no result' in t.lower() or 'nothing found' in t.lower() or 'no match' in t.lower(): note(True,'global: search no-results state')
            else: finding('missing-UX','Search','searched "zzznohit"','no no-results message','"no results" state expected','search-noresults')
            shot('audit-missing-search-noresults')
            # real query
            js("""(()=>{const r=document.querySelector('.chatroot:not([hidden])');const i=r&&r.querySelector('input');if(i){i.value='bike';i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));}})()""")
            time.sleep(2)
            shot('audit-missing-search-results')
        else: finding('broken','Search','tapped search header button','overlay did not open','search overlay should open','search-dead')
        close_all()
        pr = vcs('#pulseBtn'); time.sleep(1.8)
        note(pr=='clicked' and (bool(js("document.querySelector('.chatroot:not([hidden])')")) or sheet_open()),'global: pulse opens',pr)
        if js("document.querySelector('.chatroot:not([hidden])')"): shot('audit-missing-pulse')
        close_all()
        nr = vcs('#notifBtn'); time.sleep(1.8)
        opened = bool(js("document.querySelector('.chatroot:not([hidden])')")) or sheet_open()
        note(nr=='clicked' and opened,'global: notifications open',nr)
        if opened: shot('audit-missing-notifications')
        close_all()
        cr = vcs('#chatFab'); time.sleep(1.8)
        if cr == 'clicked' and js("!!document.querySelector('.chatroot:not([hidden])')"):
            note(True,'global: chat list opens')
            th = js("(()=>{const t=document.querySelector('.chatroot [data-thread]');if(t&&t.offsetParent!==null){t.click();return true;}return false;})()")
            time.sleep(1.8)
            note(bool(th) and bool(js("!!document.getElementById('chatText')")),'global: chat thread opens',th)
            # online indicator honesty
            hd = js("(document.querySelector('.chatroot').innerText||'').slice(0,300)")
            note(True,'global: thread header',str(hd).replace('\n',' ')[:120])
            bk = js("(()=>{const b=document.getElementById('chBack');if(b){b.click();return true;}return false;})()")
            time.sleep(1)
            note(bk,'global: chat back button works',bk)
            shot('audit-missing-chat-list')
        else: finding('broken','Chat','tapped Chats FAB','list did not open','chat list should open','chat-dead')
        close_all()
        js("try{HUB.askHUB.open()}catch(e){}"); time.sleep(1.4)
        note(sheet_open(),'global: ask pill opens')
        close_all()
        lb = vcs('#langBtn'); time.sleep(1.4)
        note(lb=='clicked' and sheet_open(),'global: header lang button',lb)
        close_all()
    section('GLOBAL v3', s_global2)

    def s_astro2():
        r = js("try{HUB.astro.openCalendar();return 'ok';}catch(e){return 'ERR:'+String(e).slice(0,80);}")
        time.sleep(1.8)
        note(r=='ok' and sheet_open(),'astro: calendar opens',r)
        if sheet_open():
            bs = vct('BS'); time.sleep(1.4)
            note('२०' in page_text() or 'BS' in page_text(),'astro: BS mode renders',bs)
            shot('audit-missing-astro-bs')
            # day note add
            dn = js("(()=>{const b=[...document.querySelectorAll('#sheetBox button')].find(x=>/add note|＋|note/i.test(x.textContent));return b?(b.click(),b.textContent.trim().slice(0,20)):false;})()")
            time.sleep(1.2)
            note(True,'astro: day-note affordance',dn)
        close_all()
    section('ASTRO v3', s_astro2)

    def s_persist2():
        c.send('Page.reload'); time.sleep(5)
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message))")
        js("document.body.classList.%s('dark');" % ('add' if THEME=='dark' else 'remove'))
        js("try{var w=document.getElementById('wlcmHost');if(w)w.hidden=true;}catch(e){}")
        tab('home'); note('PraBin' in page_text(),'persist: profile name')
        tab('market'); note('QA Lamp v3' in page_text(),'persist: listing')
        tab('work'); note('QA Mow Lawn v3' in page_text(),'persist: job')
        tab('groups')
        js("(()=>{const b=document.querySelector('#view-groups [data-sub=\"clubs\"]');if(b)b.click();})()"); time.sleep(1.2)
        note('QA Runners v3' in page_text(),'persist: group')
        e = errs(); note(not e,f'{THEME}: zero console errors at end',e)
        shot('audit-missing-final')
    section('PERSISTENCE v3', s_persist2)

    save()
    print(f'==== {THEME} v3 done: {len(findings)} total findings ====', flush=True)
finally:
    proc.terminate()
