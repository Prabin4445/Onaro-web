#!/usr/bin/env python3
"""Social layer QA: follow graph, mutual-only messaging gate, chat attachments
(photos/files/links), AES-GCM device encryption at rest, Nepali, dark mode,
zero console errors."""
import json, subprocess, time, urllib.request, os, base64

QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'
PORT = 9471
BASE = 'file:///home/hatch/workspace/hub/index.html'
checks = []

def note(ok, label, detail=''):
    checks.append((ok, label)); print(('PASS' if ok else 'FAIL'), label, detail)

import websocket
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
    # test files for attachments
    png_b64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
    open('/tmp/qa-photo.png','wb').write(base64.b64decode(png_b64))
    open('/tmp/qa-note.txt','w').write('hello attachment file')
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=414,900',
        '--user-data-dir=/tmp/hubqa-social-prof', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable'); c.send('DOM.enable')
        def js(expr):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
                res = (r or {}).get('result', {}); return res.get('value')
            except Exception as e: return 'JSERR:' + str(e)[:120]
        def jsa(expr):
            try:
                r = c.send('Runtime.evaluate', {'expression': expr, 'awaitPromise': True, 'returnByValue': True})
                res = (r or {}).get('result', {})
                if res.get('subtype') == 'error': return 'JSERR:' + str(res.get('description'))[:120]
                return res.get('value')
            except Exception as e: return 'JSERR:' + str(e)[:120]
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def click(sel):
            js("(()=>{const el=document.querySelector('"+sel+"'); if(el){el.scrollIntoView({block:'center'}); return true} return false})()")
            time.sleep(0.3); js("document.querySelector('"+sel+"').click()"); time.sleep(1.0)
        def type_in(sel, text):
            js("(()=>{const el=document.querySelector('"+sel+"'); if(!el) return 'noel'; el.focus(); el.value=''; return 'ok'})()")
            for ch in text:
                js("document.querySelector('"+sel+"').value+= "+json.dumps(ch))
                js("document.querySelector('"+sel+"').dispatchEvent(new Event('input',{bubbles:true}))")
                time.sleep(0.03)
            time.sleep(0.8)
        def set_files(sel, path):
            doc = c.send('DOM.getDocument', {'depth': 0})['root']['nodeId']
            q = c.send('DOM.querySelector', {'nodeId': doc, 'selector': sel})
            nid = q.get('nodeId')
            if not nid: return False
            c.send('DOM.setFileInputFiles', {'nodeId': nid, 'files': [path]})
            return True

        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(7)
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        js("var p=HUB.store.state.profile; p.name='PraBin'; p.campus='Riverside State'; p.audience='student'; HUB.store.save(); try{HUB.ui.closeSheet();}catch(e){} HUB.showTab('home');")
        time.sleep(2)

        # 1. crypto available + roundtrip
        avail = jsa("HUB.crypto.available()")
        note(avail is True, 'crypto available on file://', str(avail))
        rt = jsa("(async()=>{const e=await HUB.crypto.encryptText('roundtrip-abc'); const d=await HUB.crypto.decryptText(e); return d==='roundtrip-abc' && !!e.iv && !!e.ct})()")
        note(rt is True, 'AES-GCM encrypt/decrypt roundtrip', str(rt))

        # 2. people surface
        js("HUB.showTab('groups'); HUB.views.groups.setSub('people')"); time.sleep(1.5)
        has_search = js("!!document.querySelector('#pplSearch')")
        note(has_search, 'people search box present', '')
        n_cards = js("document.querySelectorAll('#pplList [data-act=\"view\"]').length")
        note(n_cards >= 4, 'people cards listed', str(n_cards))
        has_fol = js("!!document.querySelector('#pplList [data-act=\"fol\"]')")
        note(has_fol, 'follow buttons on cards', '')

        # 3. name search filters
        type_in('#pplSearch', 'maya')
        n_maya = js("document.querySelectorAll('#pplList [data-act=\"view\"]').length")
        names = js("[...document.querySelectorAll('#pplList .ppl-card h3')].map(e=>e.textContent).join('|')")
        note(n_maya == 1 and 'Maya' in names, 'search filters to Maya Chen', names)
        shot('social-people')

        # 4. follow Maya (seeded follower -> mutual)
        click('#pplList [data-act="fol"]')
        following = js("HUB.store.state.following.length")
        mutual = js("(()=>{const p=HUB.store.state.people.find(x=>x.name==='Maya Chen'); return HUB.people.isMutual(p.id)})()")
        note(following == 1 and mutual is True, 'follow -> mutual with seeded follower', f'following={following} mutual={mutual}')
        btn_txt = js("document.querySelector('#pplList [data-act=\"fol\"]').textContent")
        note('Following' in btn_txt, 'button flips to Following', btn_txt.strip())

        # 5. gate: Jordan is NOT a follower -> gate sheet
        type_in('#pplSearch', 'jordan')
        click('#pplList [data-act="msg"]')
        gate = js("document.body.textContent.includes('Messaging is mutual-only')")
        note(gate, 'non-mutual message shows gate sheet', '')
        shot('social-gate')
        click('#gateFol')  # follow from gate
        waiting = js("document.body.textContent.includes('follow you back')")
        note(waiting, 'gate shows waiting-for-follow-back state', '')
        js("HUB.ui.closeSheet()"); time.sleep(0.8)

        # 6. mutual message opens thread (Maya)
        type_in('#pplSearch', 'maya')
        click('#pplList [data-act="msg"]')
        thread_open = js("!document.getElementById('chatRoot').hidden && document.getElementById('chatPanel').textContent.includes('Maya Chen')")
        note(thread_open, 'mutual message opens chat thread', '')

        # 7. encrypted text message
        type_in('#chatText', 'secret-qa-msg-xyz')
        click('#chatSend'); time.sleep(1.5)
        bubble = js("document.getElementById('chatBubbles').textContent")
        note('secret-qa-msg-xyz' in bubble, 'sent message renders decrypted', '')
        stored = js("(()=>{const th=HUB.store.state.threads.find(t=>t.title==='Maya Chen'); const m=th.messages[th.messages.length-1]; return {enc:!!(m.enc&&m.enc.iv&&m.enc.ct), plain:('text' in m)&&m.text==='secret-qa-msg-xyz'}})()")
        note(stored.get('enc') and not stored.get('plain'), 'message stored as ciphertext only', str(stored))
        ls = js("localStorage.getItem('hub_v1').includes('secret-qa-msg-xyz')")
        note(ls is False, 'no plaintext in localStorage', '')
        lock = js("document.getElementById('chatLock').textContent")
        note('Encrypted on this device' in lock, 'lock label in thread', lock.strip())

        # 8. linkify
        type_in('#chatText', 'see https://example.com ok')
        click('#chatSend'); time.sleep(1.5)
        link = js("(()=>{const a=[...document.querySelectorAll('#chatBubbles a.cblink')].find(x=>x.href.includes('example.com')); return a?a.target+'|'+a.rel:''})()")
        note(link == '_blank|noopener', 'links become safe anchors', link)

        # 9. photo attachment
        okf = set_files('#chPhotoIn', '/tmp/qa-photo.png'); time.sleep(2.5)
        img_b = js("!!document.querySelector('#chatBubbles .cbimg')")
        note(okf and img_b, 'photo attachment renders in bubble', '')
        img_enc = js("(()=>{const th=HUB.store.state.threads.find(t=>t.title==='Maya Chen'); const m=th.messages[th.messages.length-1]; return m.kind==='image' && !!(m.enc&&m.enc.ct)})()")
        note(img_enc is True, 'photo payload stored encrypted', '')
        shot('social-chat')

        # 10. file attachment
        okf2 = set_files('#chFileIn', '/tmp/qa-note.txt'); time.sleep(2.5)
        file_b = js("(()=>{const b=[...document.querySelectorAll('#chatBubbles .cbfile')].find(x=>x.textContent.includes('qa-note.txt')); return !!b})()")
        note(okf2 and file_b, 'file attachment renders with name', '')

        # 11. daily tasks/notes encrypted
        js("HUB.chat.close(); HUB.showTab('daily')"); time.sleep(2.5)
        type_in('#dyTaskIn', 'secret-task-xyz'); click('#dyTaskAdd'); time.sleep(1.5)
        task_txt = js("document.getElementById('dyTasks').textContent")
        note('secret-task-xyz' in task_txt, 'task renders decrypted', '')
        task_enc = js("(()=>{const x=HUB.store.state.tasks.find(t=>HUB.crypto.peek(t)==='secret-task-xyz'||t.text==='secret-task-xyz'); return x?{enc:!!(x.enc&&x.enc.ct),plain:x.text==='secret-task-xyz'}:null})()")
        note(task_enc and task_enc.get('enc') and not task_enc.get('plain'), 'task stored encrypted', str(task_enc))
        type_in('#dyNoteIn', 'secret-note-xyz'); click('#dyNoteAdd'); time.sleep(1.5)
        ls2 = js("localStorage.getItem('hub_v1').includes('secret-note-xyz')||localStorage.getItem('hub_v1').includes('secret-task-xyz')")
        note(ls2 is False, 'task/note plaintext absent from localStorage', '')
        dlock = js("document.getElementById('view-daily').textContent.includes('Encrypted on this device')")
        note(dlock, 'lock note on daily cards', '')

        # 12. unfollow -> gate returns
        js("HUB.showTab('groups'); HUB.views.groups.setSub('people')"); time.sleep(1.5)
        type_in('#pplSearch', 'maya')
        click('#pplList [data-act="fol"]')  # unfollow
        still = js("HUB.store.state.following.length")
        click('#pplList [data-act="msg"]')
        gate2 = js("document.body.textContent.includes('Messaging is mutual-only')")
        note(still == 1 and gate2, 'unfollow re-locks messaging (Jordan follow remains)', f'following={still}')
        js("HUB.ui.closeSheet()")

        # 13. Nepali
        pre_errs = js("window.__huberr.length")
        js("localStorage.setItem('orbit_i18n',JSON.stringify({lang:'ne',country:'NP'}))")
        c.send('Page.navigate', {'url': BASE}); time.sleep(7)
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        js("HUB.showTab('groups'); HUB.views.groups.setSub('people')"); time.sleep(1.5)
        ne_txt = js("document.getElementById('view-groups').textContent")
        note('फलो गर्नुहोस्' in ne_txt, 'Nepali follow strings render', '')
        shot('social-ne')

        # 14. dark mode
        js("HUB.store.state.prefs.dark=true; HUB.store.save(); document.body.classList.add('dark'); HUB.showTab('groups'); HUB.views.groups.setSub('people')")
        time.sleep(1.5); shot('social-dark')
        dark_bg = js("getComputedStyle(document.body).backgroundColor")
        note(dark_bg == 'rgb(13, 16, 10)', 'dark bg token intact', dark_bg)

        # 15. console errors (pre-reload count + post-reload count)
        errs = js("window.__huberr.length")
        ed = js("window.__huberr.slice(0,3).join(' | ')")
        total_errs = (pre_errs if isinstance(pre_errs, int) else 999) + (errs if isinstance(errs, int) else 999)
        note(total_errs == 0, 'zero console errors', f'pre={pre_errs} post={ed}')

        passed = sum(1 for ok, _ in checks if ok)
        print(f'\n==== {passed}/{len(checks)} passed ====')
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
