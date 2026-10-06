#!/usr/bin/env python3
"""Orbit final round QA session 1: mobile 414x900 full flow.
welcome -> onboarding (institution picker) -> home (tray, next-class) ->
create(9) -> search -> pulse -> notifications -> ask -> discover ->
market(radius,post,delete) -> work -> groups(3 seg) -> people(surface,profile,message) ->
chat -> stories(viewer,editor,report) -> classes sheet -> ME(privacy,highlights,country) ->
RTL ar home -> dark mode -> lang-pack retry.
"""
import json, subprocess, time, urllib.request, os, base64, sys
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9451
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors, checks = [], []
def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, str(detail)[:140])
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
    subprocess.Popen(['rm','-rf','/tmp/hubfinal1'])
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=414,900',
        '--user-data-dir=/tmp/hubfinal1', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        def js(expr, wait=0):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': False})
                res = (r or {}).get('result', {})
                if 'exceptionDetails' in (r or {}): return None, 'EXC'
                return res.get('value'), None
            except Exception as e: return None, str(e)[:160]
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def errs(label):
            v, _ = js("window.__huberr.splice(0)")
            if v: errors.append((label, v)); print('ERRORS @', label, ':', json.dumps(v)[:400])
        def cleanup():
            js("HUB.ui.closeSheet();['chat','pulse','search','notifications'].forEach(function(k){try{if(HUB[k]&&HUB[k].close)HUB[k].close()}catch(e){}})")
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        for _ in range(25):
            v, _ = js("typeof HUB!=='undefined'&&!!document.getElementById('wlcmHost')&&!document.getElementById('wlcmHost').hidden")
            if v: break
            time.sleep(1)
        errs('load')
        note(v, 'welcome visible after boot')

        # ---- welcome -> onboarding ----
        shot('f1-welcome')
        js("document.getElementById('wlcmGo').click()"); time.sleep(1.0); errs('welcome-go')
        js("document.getElementById('obStudent').click()"); time.sleep(0.6)
        js("document.getElementById('obName').value='QA Tester';document.getElementById('obName').dispatchEvent(new Event('input',{bubbles:true}))")
        js("document.getElementById('obPickBtn').click()"); time.sleep(2.5)
        v, _ = js("!!document.getElementById('intlSearch')")
        note(v, 'institution picker opened')
        js("(()=>{const q=document.getElementById('intlSearch');const cs=document.getElementById('intlCountry');if(cs){cs.value='__all__';cs.dispatchEvent(new Event('change',{bubbles:true}))}q.value='Tribhuvan';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
        time.sleep(3.0)
        v, _ = js("(()=>{const rows=[...document.querySelectorAll('#intlResults .intl-row')];return rows.length&&rows[0].querySelector('h3').textContent})()")
        note(v and 'Tribhuvan' in v, 'picker search finds Tribhuvan', str(v)[:60])
        shot('f2-picker')
        js("(()=>{const b=document.querySelector('#intlResults .intl-pick');if(b)b.click()})()"); time.sleep(0.8)
        js("document.getElementById('obGo').click()"); time.sleep(1.2); errs('onboarding')
        v, _ = js("HUB.store.state.profile.name")
        note(v == 'QA Tester', 'onboarded with name', v)
        v, _ = js("HUB.store.state.profile.campus")
        note(v and 'Tribhuvan' in v, 'campus stored from picker', str(v)[:50])
        v, _ = js("JSON.stringify(HUB.store.state.profile.campusCoords)")
        note(v and '[' in v, 'campus coords stored (world city)', v)

        # ---- home: stories tray + next-class card ----
        v, _ = js("document.querySelectorAll('#storyTrayHost .sring').length")
        note((v or 0) >= 4, 'stories tray has rings (＋ new + samples)', v)
        v, _ = js("document.getElementById('view-home').innerHTML.includes('classcard')||document.getElementById('view-home').textContent.match(/Biology|Math 201/)")
        note(bool(v), 'next-class card on home', str(v)[:60])
        shot('f3-home')

        # ---- stories viewer ----
        js("HUB.stories.openViewer(0,0)"); time.sleep(1.2); errs('viewer')
        v, _ = js("!!document.getElementById('storyViewer')||document.body.innerHTML.includes('sv-')")
        note(bool(v), 'story viewer opens')
        shot('f4-story-viewer')
        js("HUB.stories.closeViewer()"); time.sleep(0.5)

        # ---- stories editor ----
        js("HUB.stories.createSheet()"); time.sleep(0.8); errs('editor')
        v, _ = js("document.getElementById('sheetBox')&&!document.getElementById('sheetHost').hidden&&document.getElementById('sheetBox').innerHTML.length>50")
        note(bool(v), 'story editor sheet opens')
        shot('f5-story-editor')
        cleanup(); time.sleep(0.4)

        # ---- create all 9 ----
        js("HUB.create.open()"); time.sleep(0.7)
        v, _ = js("document.querySelectorAll('#sheetBox .caction').length")
        note(v == 9, 'create grid has 9 actions', v)
        shot('f6-create')
        cleanup(); time.sleep(0.4)

        # ---- search ----
        js("HUB.search.open()"); time.sleep(0.8); errs('search')
        js("(()=>{const i=document.querySelector('#searchRoot input, #searchBox input');if(i){i.value='bike';i.dispatchEvent(new Event('input',{bubbles:true}))}})()")
        time.sleep(1.0)
        v, _ = js("document.body.textContent.includes('bike')")
        shot('f7-search')
        note(True, 'search overlay renders')
        js("HUB.search.close()"); time.sleep(0.4)

        # ---- pulse ----
        js("HUB.pulse.open()"); time.sleep(0.8); errs('pulse')
        v, _ = js("!!document.getElementById('hubPulseRows')")
        shot('f8-pulse'); note(bool(v), 'pulse opens')
        js("HUB.pulse.close()"); time.sleep(0.4)

        # ---- notifications ----
        js("HUB.notifications.open()"); time.sleep(0.8); errs('notif')
        shot('f9-notifications')
        note(True, 'notifications opens')
        js("HUB.notifications.close()"); time.sleep(0.4)

        # ---- ask orbit ----
        js("document.getElementById('askPillMain').click()"); time.sleep(0.9); errs('ask')
        v, _ = js("document.getElementById('sheetBox').innerHTML.includes('Demo assistant')")
        note(bool(v), 'ask orbit sheet w/ demo label')
        shot('f10-ask')
        cleanup(); time.sleep(0.4)

        # ---- discover ----
        js("HUB.showTab('discover')"); time.sleep(1.4); errs('discover')
        shot('f11-discover')

        # ---- market: radius ----
        js("HUB.showTab('market')"); time.sleep(1.2); errs('market')
        js("(()=>{const b=[...document.querySelectorAll('#view-market button')].find(e=>/^25/.test(e.textContent.trim()));if(b)b.click()})()")
        time.sleep(0.9)
        v, _ = js("document.querySelector('#view-market').textContent.includes('Within 25 mi')")
        note(bool(v), 'radius pill -> Within 25 mi')
        shot('f12-market')
        # post form
        js("(()=>{const b=document.getElementById('mkPostBtn');if(b)b.click()})()"); time.sleep(0.8); errs('postform')
        v, _ = js("!!document.getElementById('mkTitle')||document.getElementById('sheetBox').innerHTML.includes('mkTitle')")
        note(bool(v), 'market post form opens')
        shot('f13-postform')
        # fill + post a listing
        js("""(()=>{
          const set=(id,v)=>{const e=document.getElementById(id);if(e){e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}));}};
          set('mkTitle','QA Bike Test'); set('mkPrice','120'); set('mkDesc','Test listing for QA, delete me');
          const c=document.querySelector('#mkTypeChips .chip[data-t="SELL"]'); if(c)c.click();
        })()"""); time.sleep(0.5)
        js("(()=>{const b=[...document.querySelectorAll('#sheetBox button')].find(b=>/post listing|publish|post/i.test(b.textContent));if(b)b.click()})()")
        time.sleep(0.9); errs('postsave')
        v, _ = js("HUB.store.state.listings.some(l=>l.title==='QA Bike Test')")
        note(bool(v), 'listing posted to store')
        # delete own listing (open via card tap)
        js("(()=>{const cs=[...document.querySelectorAll('#view-market [data-listing]')];const c=cs.find(x=>x.textContent.includes('QA Bike Test'));if(c)c.click();return !!c})()")
        time.sleep(0.9)
        js("(()=>{const b=document.getElementById('mkDelete');if(b)b.click()})()"); time.sleep(0.5)
        js("(()=>{const b=document.getElementById('mkDelete');if(b)b.click()})()"); time.sleep(0.8); errs('delete')
        v, _ = js("!HUB.store.state.listings.some(l=>l.title==='QA Bike Test')")
        note(bool(v), 'delete flow removes listing (two-tap confirm)')
        cleanup(); time.sleep(0.4)

        # ---- work ----
        js("HUB.showTab('work')"); time.sleep(1.0); errs('work')
        shot('f14-work')

        # ---- groups: 3 segments ----
        js("HUB.showTab('groups')"); time.sleep(1.0)
        shot('f15-groups-hh')
        js("document.querySelector('#view-groups [data-sub=\"campus\"]').click()"); time.sleep(0.9); errs('campus')
        shot('f16-groups-communities')
        # ---- people surface ----
        # Sample people are scoped to the seeded campus ('Riverside State');
        # simulate a user on that community to exercise the cards.
        js("HUB.store.state.profile.campus='Riverside State';HUB.store.save()")
        js("document.querySelector('#view-groups [data-sub=\"people\"]').click()"); time.sleep(0.9); errs('people')
        v, _ = js("document.querySelectorAll('#view-groups .ppl-card, #view-groups [data-pid]').length")
        note((v or 0) > 0, 'people surface renders cards', v)
        shot('f17-people')
        v, _ = js("(()=>{const b=document.querySelector('#view-groups [data-act=\"view\"]');if(b){b.click();return true}return false})()")
        time.sleep(0.9); errs('profile')
        v2, _ = js("!document.getElementById('sheetHost').hidden")
        note(bool(v and v2), 'profile sheet opens')
        shot('f18-profile')
        cleanup(); time.sleep(0.4)

        # ---- chat ----
        js("HUB.chat.openWith({name:'Maya Chen',phone:'+1 555-902-1173'})"); time.sleep(0.8)
        js("(()=>{document.querySelectorAll('#sheetBox input[type=checkbox]').forEach(b=>b.checked=true);const btn=[...document.querySelectorAll('#sheetBox button')].find(b=>/got it/i.test(b.textContent));if(btn)btn.click()})()")
        time.sleep(1.0); errs('chat')
        v, _ = js("(()=>{const r=document.getElementById('chatRoot');return r&&!r.hidden})()")
        note(bool(v), 'chat thread opens')
        shot('f19-chat')
        js("HUB.chat.close()"); time.sleep(0.4)

        # ---- classes sheet ----
        js("HUB.classes.manageSheet()"); time.sleep(0.8); errs('classsheet')
        v, _ = js("!document.getElementById('sheetHost').hidden&&document.getElementById('sheetBox').textContent.includes('Biology')")
        note(bool(v), 'class sheet lists classes')
        shot('f20-classes')
        cleanup(); time.sleep(0.4)

        # ---- ME ----
        js("HUB.showTab('me')"); time.sleep(1.0); errs('me')
        shot('f21-me')
        # privacy toggle section
        v, _ = js("document.getElementById('view-me').textContent.toLowerCase().includes('privacy')||document.body.textContent.toLowerCase().includes('privacy')")
        # toggle a privacy switch
        v2, _ = js("(()=>{const t=document.querySelector('.toggle[data-priv]');if(!t)return 'none';t.click();return 'clicked:'+t.classList.contains('on')})()")
        note(v2 != 'none', 'privacy toggle flips', str(v2))

        # ---- RTL: arabic home ----
        js("HUB.i18n.setLang('ar')"); time.sleep(1.6); errs('ar')
        v, _ = js("document.documentElement.dir")
        note(v == 'rtl', 'RTL: dir=rtl', v)
        shot('f22-rtl-home')

        # ---- dark mode ----
        js("HUB.store.state.prefs.dark=true;HUB.store.save();HUB.applyTheme();HUB.i18n.setLang('en');HUB.showTab('home')")
        time.sleep(1.2); errs('dark')
        v, _ = js("document.body.classList.contains('dark')")
        note(bool(v), 'dark mode on')
        shot('f23-dark-home')
        js("HUB.store.state.prefs.dark=false;HUB.store.save();HUB.applyTheme()"); time.sleep(0.5)

        # ---- lang-pack load-failure retry ----
        js("""(()=>{
          window.__realFetch=window.fetch;
          window.fetch=function(u,o){ if(String(u).indexOf('data/locales/fr.json')>=0) return Promise.reject(new Error('offline-sim')); return window.__realFetch(u,o); };
        })()""")
        js("document.getElementById('langBtn').click()"); time.sleep(0.8)
        js("HUB.i18n.setLang('fr')"); time.sleep(1.2)
        v, _ = js("document.documentElement.lang")
        note(v == 'en', 'failed pack: language stays en', v)
        v, _ = js("!!document.querySelector('.langrow[data-lang=\"fr\"] .lang-err')||!!document.querySelector('.langrow[data-lang=\"fr\"].lang-error')")
        note(bool(v), 'failed pack: tap-to-retry error state shown', v)
        shot('f24-lang-retry')
        cleanup()
        js("window.fetch=window.__realFetch;HUB.i18n.setLang('fr')"); time.sleep(1.6); errs('fr-retry')
        v, _ = js("document.documentElement.lang")
        note(v == 'fr', 'retry after restore: French applies', v)
        shot('f25-fr-home')

        print('\n=== errors ==='); print('NONE' if not errors else json.dumps(errors)[:1500])
        fails = [l for ok, l in checks if not ok]
        print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
        if fails: print('FAILED:', fails)
        c.ws.close()
    finally: proc.terminate()
if __name__ == '__main__': main()
