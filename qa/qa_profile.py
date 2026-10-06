#!/usr/bin/env python3
"""QA: profile editing (photo/name/bio/school/skills) + verified badge design."""
import json, subprocess, time, urllib.request, os, base64, sys
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9437
BASE = 'file:///home/hatch/workspace/hub/index.html'
W, H = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (414, 900)
TAG = 'm' if W < 800 else 'd'
PHOTO = os.path.expanduser('~/workspace/hub/icons/ask-hub.png')
errors, checks = [], []
def note(ok, label, detail=''):
    checks.append((bool(ok), label)); print(('PASS' if ok else 'FAIL'), label, detail)
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
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', f'--window-size={W},{H}',
        '--user-data-dir=/tmp/hubqa-profile', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
                res = (r or {}).get('result', {}); return res.get('value'), res.get('exceptionDetails')
            except Exception as e: return None, str(e)[:160]
        def shot(name):
            r = c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
        def errs(label):
            v, _ = js("window.__huberr.splice(0)")
            if v: errors.append((label, v)); print('ERRORS @', label, ':', json.dumps(v)[:300])
        js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
        time.sleep(3)
        # dismiss onboarding (welcome + role picker)
        for _ in range(6):
            st, _ = js("(()=>{const n=document.getElementById('obName'); if(!n) return 'gone'; n.value='QA Tester'; const s=document.getElementById('obCampus'); if(s) s.selectedIndex=1; const g=document.getElementById('obGo'); if(g) g.click(); return 'clicked'})()")
            time.sleep(1)
            if st == 'gone': break
        js("(()=>{const b=[...document.querySelectorAll('button')].find(x=>/continue|weiter/i.test(x.textContent)); if(b) b.click()})()")
        time.sleep(1); errs('load')

        # ---- ME hero: Edit button present ----
        js("HUB.showTab('me')"); time.sleep(1.2); errs('me')
        v, _ = js("!!document.getElementById('meEditBtn')")
        note(v, 'Edit button on ME hero')
        shot('profile-hero')

        # ---- open edit sheet ----
        js("document.getElementById('meEditBtn').click()"); time.sleep(0.8); errs('edit-open')
        v, _ = js("!!document.getElementById('peditName')&&!!document.getElementById('peditFile')&&!!document.getElementById('peditCampus')&&!!document.getElementById('peditSave')")
        note(v, 'edit sheet has name/photo/school/skills/save')
        v, _ = js("document.body.textContent.includes('this browser only')||document.getElementById('sheetHost').textContent.includes('browser')")
        note(v, 'browser-only honesty note in edit sheet')
        shot('profile-edit')

        # ---- fill fields + upload photo ----
        js("document.getElementById('peditName').value='QA Tester';document.getElementById('peditBio').value='Loves testing things';document.getElementById('peditSkills').value='tutoring, moving help, tutoring'")
        doc = c.send('DOM.getDocument', {'depth': 0})['root']['nodeId']
        q = c.send('DOM.querySelector', {'nodeId': doc, 'selector': '#peditFile'})
        c.send('DOM.setFileInputFiles', {'nodeId': q['nodeId'], 'files': [PHOTO]})
        js("document.getElementById('peditFile').dispatchEvent(new Event('change',{bubbles:true}))")
        time.sleep(1.5); errs('photo-pick')
        v, _ = js("!!document.querySelector('#peditPrev img.avimg')")
        note(v, 'photo preview shows in edit sheet')
        js("document.getElementById('peditSave').click()"); time.sleep(1.0); errs('save')
        v, _ = js("String(HUB.store.state.profile.photo||'').startsWith('data:image/jpeg')")
        note(v, 'photo saved as downscaled dataURL')
        v, _ = js("document.querySelector('#view-me .me-avatar img.avimg')!==null")
        note(v, 'hero avatar shows uploaded photo')
        v, _ = js("HUB.store.state.profile.bio==='Loves testing things'")
        note(v, 'bio saved')
        v, _ = js("JSON.stringify(HUB.store.state.profile.skills)")
        note(v == '["tutoring","moving help"]', 'skills saved deduped', str(v))
        v, _ = js("document.getElementById('view-me').textContent.includes('Loves testing things')")
        note(v, 'bio renders on hero')
        shot('profile-photo')

        # ---- persistence across reload ----
        v, _ = js("(()=>{try{return JSON.parse(localStorage.getItem('hub_v1')).profile.photo||''}catch(e){return ''}})().slice(0,15)")
        note(str(v).startswith('data:image'), 'photo persisted in localStorage')
        c.send('Page.reload'); time.sleep(4); errs('reload')
        v, _ = js("document.querySelector('#view-me .me-avatar img.avimg, .me-avatar img.avimg')!==null || String(HUB.store.state.profile.photo||'').startsWith('data:image')")
        note(v, 'photo survives reload')
        js("HUB.showTab('me')"); time.sleep(1.0)

        # ---- school change via world directory ----
        js("document.getElementById('meEditBtn').click()"); time.sleep(0.8)
        js("document.getElementById('peditCampus').click()"); time.sleep(2.5); errs('picker')
        v, _ = js("!!document.getElementById('intlSearch')")
        note(v, 'institution picker opens from edit sheet')
        js("(()=>{const i=document.getElementById('intlSearch'); i.value='Harvard'; i.dispatchEvent(new Event('input',{bubbles:true}))})()")
        time.sleep(2.0)
        v, _ = js("document.getElementById('intlResults').textContent")
        found = 'Harvard' in str(v)
        note(found, 'world directory search finds Harvard', str(v)[:80])
        if found:
            js("document.querySelector('#intlResults .intl-pick').click()"); time.sleep(0.8)
            v, _ = js("document.getElementById('peditCampus').textContent")
            note('Harvard' in str(v), 'picked school shows on edit sheet', str(v)[:60])
            js("document.getElementById('peditSave').click()"); time.sleep(1.0); errs('school-save')
            v, _ = js("HUB.store.state.profile.campus")
            note('Harvard' in str(v), 'profile.campus updated', str(v))
            v, _ = js("document.querySelector('#view-me .me-campus').textContent")
            note('Harvard' in str(v), 'hero shows new school', str(v)[:60])
        else:
            js("HUB.ui.closeSheet()"); time.sleep(0.5)
        shot('profile-school')

        # ---- verified badge: temp flip, screenshot, flip back ----
        js("HUB.store.state.profile.verified=true;HUB.store.save();HUB.showTab('me')"); time.sleep(1.0); errs('vflip')
        v, _ = js("(()=>{const b=document.querySelector('#view-me .vbadge'); if(!b) return 'none'; const tick=getComputedStyle(b.querySelector('.vbadge-tick')).backgroundColor; const cap=b.querySelector('.vbadge-cap').textContent; return tick+'|'+cap})()")
        note(str(v).startswith('rgb(37, 99, 235)|Verified'), 'hero verified badge: blue tick + "Verified" caption', str(v))
        shot('profile-verified')
        v, _ = js("!!document.querySelector('#view-me .badge.b-unverified')")
        note(not v, 'no unverified pill when verified')
        js("HUB.store.state.profile.verified=false;HUB.store.save();HUB.showTab('me')"); time.sleep(0.8)
        v, _ = js("!!document.querySelector('#view-me .badge.b-unverified')")
        note(v, 'unverified pill restored after flip-back')

        # seeds live at Riverside State: set campus there to see Maya/Alex cards+stories
        js("HUB.store.state.profile.campus='Riverside State';HUB.store.save()"); time.sleep(0.5)
        v, _ = js("HUB.people.visiblePeople().map(p=>p.name).join(',')")
        note('Maya Chen' in str(v), 'people surface follows new school', str(v)[:80])

        # ---- people card verified badge (Maya Chen is verified in seeds) ----
        js("HUB.showTab('groups')"); time.sleep(1.0)
        js("document.querySelector('[data-sub=\"people\"]').click()"); time.sleep(1.2); errs('people')
        v, _ = js("(()=>{const cards=[...document.querySelectorAll('.ppl-card')]; const maya=cards.find(c=>c.textContent.includes('Maya Chen')); return maya&&maya.querySelector('.vbadge')?maya.querySelector('.vbadge-cap').textContent:'none'})()")
        note(str(v) == 'Verified', 'people card shows stacked verified badge', str(v))
        shot('profile-people')

        # ---- chat header verified badge (temp flip on contact) ----
        js("(()=>{const th=HUB.store.state.threads.find(t=>t.title==='Alex Rivera'); if(th) HUB.chat.openThread(th.id)})()")
        time.sleep(1.0); errs('chat')
        v, _ = js("(()=>{const b=document.querySelector('.chathead .vbadge'); return b?b.querySelector('.vbadge-cap').textContent:'none'})()")
        note(str(v) == 'Verified', 'chat header shows verified badge', str(v))
        shot('profile-chat')
        js("HUB.chat.close()"); time.sleep(0.5)

        # ---- story tray tick + viewer badge ----
        js("HUB.showTab('home')"); time.sleep(1.2)
        v, _ = js("document.querySelectorAll('.sringc .svtick').length")
        note(v and v >= 1, 'verified tick on story rings', 'count='+str(v))
        v, _ = js("(()=>{const gs=HUB.stories.groups(); const gi=gs.findIndex(g=>g.author==='Maya Chen'); if(gi<0) return -1; HUB.stories.openViewer(gi,0); return gi})()")
        time.sleep(1.0); errs('story')
        v2, _ = js("(()=>{const b=document.querySelector('.sname .vbadge'); return b?b.querySelector('.vbadge-cap').textContent:'none'})()")
        note(str(v) != '-1' and str(v2) == 'Verified', 'story viewer header shows verified badge', str(v2))
        shot('profile-story')
        js("HUB.stories.closeViewer()"); time.sleep(0.5)

        # ---- dark mode ----
        js("HUB.store.state.prefs.dark=true;HUB.store.save();HUB.applyTheme();HUB.showTab('me')"); time.sleep(1.0); errs('dark')
        v, _ = js("getComputedStyle(document.body).backgroundColor")
        note('13, 16, 10' in str(v), 'dark mode bg', str(v))
        js("document.getElementById('meEditBtn').click()"); time.sleep(0.8)
        shot('profile-dark')
        js("HUB.ui.closeSheet()")
        js("HUB.store.state.prefs.dark=false;HUB.store.save();HUB.applyTheme()"); time.sleep(0.8)

        # ---- RTL spot check ----
        js("HUB.i18n.setLang('ar')"); time.sleep(2.5); errs('rtl')
        v, _ = js("document.dir")
        note(v == 'rtl', 'Arabic flips dir=rtl', 'dir='+str(v))
        js("HUB.showTab('me')"); time.sleep(1.0)
        v, _ = js("!!document.getElementById('meEditBtn')")
        note(v, 'edit button renders under RTL')
        shot('profile-ar')
        js("HUB.i18n.setLang('en')"); time.sleep(1.5)

        # ---- no horizontal scroll ----
        v, _ = js("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
        note(bool(v), 'no horizontal page scroll')

        print('\n=== errors ==='); print('NONE' if not errors else errors)
        fails = [l for ok, l in checks if not ok]
        print(f'\n{len(checks)-len(fails)}/{len(checks)} passed')
        if fails: print('FAILED:', fails)
        c.ws.close()
    finally: proc.terminate()
if __name__ == '__main__': main()
