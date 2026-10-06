#!/usr/bin/env python3
"""Orbit i18n QA: welcome, pickers, 4-language tab matrix, dark mode, overlays, console-error sweep."""
import json, subprocess, time, urllib.request, os, base64
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9481
BASE = 'file:///home/hatch/workspace/hub/index.html'
errors, checks = [], []
def note(ok, label, detail=''):
    checks.append((ok, label)); print(('PASS' if ok else 'FAIL'), label, detail)
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
    subprocess.Popen(['rm','-rf','/tmp/hubi18n-prof'])
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=414,900',
        '--user-data-dir=/tmp/hubi18n-prof', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        def js(expr):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': False})
                res = (r or {}).get('result', {})
                if res.get('subtype') == 'error' or 'exceptionDetails' in (r or {}):
                    return None, 'EXC'
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
        time.sleep(3); errs('load')

        # 1. welcome visible on clean profile
        v, _ = js("(()=>{const h=document.getElementById('wlcmHost');return h&&!h.hidden})()")
        note(bool(v), 'welcome shown on clean profile')
        v, _ = js("document.getElementById('wlcmBody').textContent.includes('Welcome to Orbit')")
        note(bool(v), 'welcome title in English default')
        shot('i18n-01-welcome')

        # 2. pick Nepali on welcome -> welcome re-renders in Nepali instantly
        js("(()=>{const b=document.querySelector('[data-wlang=\"ne\"]');if(b)b.click()})()")
        time.sleep(0.8); errs('welcome-ne')
        v, _ = js("document.getElementById('wlcmBody').textContent.includes('Orbit मा स्वागत छ')")
        note(bool(v), 'welcome re-renders in Nepali')
        shot('i18n-02-welcome-ne')

        # 3. country search + select Nepal
        js("(()=>{const q=document.getElementById('wlcmQ');q.value='nepal';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
        time.sleep(0.8)
        v, _ = js("(()=>{const rows=[...document.querySelectorAll('.wlcm-crow')].map(r=>r.textContent);return rows.join('|')})()")
        note('नेपाल' in str(v), 'country search finds Nepal (localized)', str(v)[:60])
        js("(()=>{const r=[...document.querySelectorAll('.wlcm-crow')].find(r=>/नेपाल/.test(r.textContent));if(r)r.click()})()")
        time.sleep(0.6)
        v, _ = js("(()=>{const r=document.querySelector('.wlcm-crow.on');return r&&r.textContent})()")
        note('नेपाल' in str(v), 'Nepal selected', str(v)[:30])
        shot('i18n-03-welcome-country')

        # 4. continue -> onboarding -> complete
        js("document.getElementById('wlcmGo').click()")
        time.sleep(1.2); errs('welcome-continue')
        v, _ = js("localStorage.getItem('orbit_i18n')")
        note('"ne"' in str(v) and '"NP"' in str(v), 'persisted {lang:ne, country:NP}', str(v))
        # onboarding role step
        v, _ = js("document.body.textContent.includes('विद्यार्थी')")
        note(bool(v), 'onboarding in Nepali after welcome')
        js("(()=>{const b=[...document.querySelectorAll('button')].find(b=>/विद्यार्थी/.test(b.textContent));if(b)b.click()})()")
        time.sleep(0.8)
        js("(()=>{const n=document.getElementById('obName');if(n)n.value='QA Tester';const s=document.getElementById('obCampus');if(s)s.selectedIndex=1;const g=document.getElementById('obGo');if(g)g.click()})()")
        time.sleep(1.5); errs('onboarding-done')
        v, _ = js("(()=>{const t=document.querySelector('#tabbar .tab.active');return t&&t.dataset.tab})()")
        note(v == 'home', 'landed on home tab', str(v))
        shot('i18n-04-home-ne')

        # 5. returning user: reload skips welcome
        c.send('Page.reload'); time.sleep(3.5); errs('reload')
        v, _ = js("(()=>{const h=document.getElementById('wlcmHost');return !h||h.hidden})()")
        note(bool(v), 'welcome skipped for returning user')

        # 6. language x tab matrix
        LANG_ASSERT={'es':'INICIO','ne':'होम','hi':'होम','en':'HOME'}
        for lang in ['es','hi','en','ne']:
            js(f"HUB.i18n.setLang('{lang}')"); time.sleep(1.0); errs('setLang-'+lang)
            v, _ = js("document.documentElement.lang")
            note(v == lang, f'html lang={lang}')
            v, _ = js("document.getElementById('tabbar').textContent")
            note(LANG_ASSERT[lang] in str(v), f'nav label in {lang}', str(v)[:40])
            for tab in ['home','discover','market','work','groups','me']:
                js(f"HUB.showTab('{tab}')"); time.sleep(0.9)
                errs(f'{lang}/{tab}')
                shot(f'i18n-tab-{tab}-{lang}')
        # people segment (inside groups) in Nepali
        js("HUB.i18n.setLang('ne');HUB.showTab('groups')"); time.sleep(1.0)
        js("(()=>{const s=document.querySelector('[data-seg=\"people\"]');if(s)s.click()})()")
        time.sleep(1.2); errs('people-ne')
        shot('i18n-tab-people-ne')

        # 7. globe button -> language picker, instant switch without reload
        js("HUB.i18n.setLang('en');HUB.showTab('home')"); time.sleep(0.9)
        js("window.__rmark=12345;document.getElementById('langBtn').click()")
        time.sleep(0.9); errs('langpicker-open')
        v, _ = js("document.getElementById('sheetBox').textContent.includes('Español')")
        note(bool(v), 'language picker lists Español')
        shot('i18n-05-langpicker')
        js("(()=>{const b=[...document.querySelectorAll('#sheetBox button')].find(b=>/Español/.test(b.textContent));if(b)b.click()})()")
        time.sleep(1.2); errs('langpicker-es')
        v, _ = js("window.__rmark===12345&&document.documentElement.lang==='es'")
        note(bool(v), 'instant re-render, no reload (marker intact)')
        v, _ = js("document.getElementById('tabbar').textContent.includes('INICIO')")
        note(bool(v), 'home tab now Spanish')

        # 8. country editing from ME/settings
        js("HUB.showTab('me')"); time.sleep(1.0)
        js("(()=>{const b=document.getElementById('meCountryBtn');if(b)b.click()})()")
        time.sleep(0.9); errs('countrypicker-open')
        v, _ = js("document.getElementById('sheetBox').textContent.length>50")
        note(bool(v), 'country picker opened from settings')
        shot('i18n-06-countrypicker')
        js("(()=>{const q=document.querySelector('#sheetBox input');if(q){q.value='japan';q.dispatchEvent(new Event('input',{bubbles:true}))}})()")
        time.sleep(0.8)
        js("(()=>{const r=[...document.querySelectorAll('#sheetBox .wlcm-crow, #sheetBox button')].find(b=>/Japón|日本/.test(b.textContent));if(r)r.click()})()")
        time.sleep(0.8); errs('country-pick')
        v, _ = js("JSON.parse(localStorage.getItem('orbit_i18n')).country")
        note(v == 'JP', 'country changed to JP', str(v))
        cleanup()

        # 9. dark mode spot check (Nepali home)
        js("HUB.i18n.setLang('ne');HUB.store.state.prefs.dark=true;HUB.store.save();HUB.applyTheme();HUB.showTab('home')")
        time.sleep(1.0); errs('dark')
        v, _ = js("getComputedStyle(document.body).backgroundColor")
        note('13, 16, 10' in str(v), 'dark bg is brand #0D100A', str(v))
        shot('i18n-07-dark-ne')
        js("HUB.store.state.prefs.dark=false;HUB.store.save();HUB.applyTheme()")

        # 10. all nine create actions in Spanish (no dead ends, no errors)
        js("HUB.i18n.setLang('es');HUB.create.open()"); time.sleep(0.8)
        v, _ = js("document.querySelectorAll('#sheetBox .caction').length")
        note(v == 9, 'nine create actions listed', str(v))
        shot('i18n-08-create-es')
        for i in range(9):
            js("HUB.create.open()"); time.sleep(0.5)
            js(f"(()=>{{const b=document.querySelectorAll('#sheetBox .caction')[{i}];if(b)b.click()}})()")
            time.sleep(1.4); errs(f'create-action-{i}')
            cleanup(); time.sleep(0.3)

        # 11. notifications / pulse / search overlays in Hindi
        js("HUB.i18n.setLang('hi')"); time.sleep(0.8)
        js("HUB.notifications.open()"); time.sleep(1.0); errs('notif-hi')
        v, _ = js("document.body.textContent.includes('सूचनाएँ')")
        note(bool(v), 'notifications title in Hindi')
        shot('i18n-09-notif-hi')
        cleanup()
        js("HUB.pulse.open()"); time.sleep(1.0); errs('pulse-hi')
        shot('i18n-10-pulse-hi')
        cleanup()
        js("HUB.search.open()"); time.sleep(0.8)
        js("(()=>{const i=document.querySelector('.chatroot input');if(i){i.value='काम';i.dispatchEvent(new Event('input',{bubbles:true}))}})()")
        time.sleep(1.0); errs('search-hi')
        shot('i18n-11-search-hi')
        cleanup()

        # 12. chat thread + scam banner in Hindi
        js("HUB.chat.openWith({name:'Maya Chen',phone:'+1 555-902-1173'})"); time.sleep(0.8)
        js("(()=>{document.querySelectorAll('#sheetBox input[type=checkbox]').forEach(b=>b.checked=true);const btn=[...document.querySelectorAll('#sheetBox button')].find(b=>/समझ|Got it|Entendido/.test(b.textContent));if(btn)btn.click()})()")
        time.sleep(1.2); errs('chat-hi-checklist')
        js("(()=>{const t=HUB.store.state.threads.find(t=>t.title==='Maya Chen');t.messages.push({from:'them',text:'wire money first, gift cards ok',at:Date.now()});HUB.store.save();HUB.chat.openThread(t.id)})()")
        time.sleep(1.2); errs('chat-hi-scam')
        v, _ = js("document.getElementById('chatPanel').textContent.includes('डेमो सुरक्षा संकेत')")
        note(bool(v), 'scam banner in Hindi')
        shot('i18n-12-chat-hi')
        cleanup()

        # 13. honesty labels in each language (sample/demo/computed)
        for lang, word in [('es','Muestra'),('ne','नमूना'),('hi','नमूना')]:
            js(f"HUB.i18n.setLang('{lang}');HUB.showTab('me')"); time.sleep(0.9)
            v, _ = js(f"document.getElementById('view-me').textContent.includes('{word}')")
            note(bool(v), f'honesty label "{word}" in {lang}')
        errs('final')
        print('\n=== console errors ==='); print('NONE' if not errors else json.dumps(errors)[:2000])
        fails = [l for ok, l in checks if not ok]
        print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
        if fails: print('FAILED:', fails)
        c.ws.close()
    finally: proc.terminate()
if __name__ == '__main__': main()
