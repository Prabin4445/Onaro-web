#!/usr/bin/env python3
"""HUB QA: PraBin's premium 3D profile badge system (post-rewrite).
Covers: tier thresholds (89/90, 179/180, 364/365), 60s foreground rule,
same-date no-double-count, next-day recount, unlock celebration with exact
reason + next-badge guidance, toast, notification-center entry (tap opens
showcase), ME name-adjacent placement, inline SVG rendering, shine keyframes,
showcase float/glow, reduced-motion freeze, locked-dimmed, SPECIALIST 99/100,
friends' profiles, glass profile card (badge next to the name, tap opens a
read-only showcase, SPECIALIST stacking, demo derivation), no purple, de (identity-asserted, German copy) + en,
dark + light, 390px, zero console errors. Fresh profile every run."""
import json, subprocess, time, urllib.request, os, base64, shutil
import websocket
QA = os.path.expanduser('~/workspace/hub/qa')
CHROME = '/opt/meta-chromium/chrome'; PORT = 9433
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-badges'
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
    def js(self, expr, awaitPromise=False):
        try:
            r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': awaitPromise})
            res = (r or {}).get('result', {})
            return res.get('value'), res.get('exceptionDetails')
        except Exception as e: return None, str(e)[:160]

def targets():
    with urllib.request.urlopen(f'http://localhost:{PORT}/json/list', timeout=5) as r:
        return json.load(r)
def shot(c, name):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, name + '.png'), 'wb').write(base64.b64decode(r['data'])); print('shot:', name)
def hook_err(c):
    c.js("window.__huberr=[];addEventListener('error',e=>__huberr.push('ERR:'+e.message));addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")
def drain_err(c, label):
    v, _ = c.js("window.__huberr.splice(0)")
    if v: errors.append((label, v)); print('ERRORS @', label, ':', json.dumps(v)[:400])
def seed_profile(c, name):
    c.js("(()=>{const p=HUB.store.state.profile; p.name=%s; p.campus='QA Campus'; HUB.store.save(); HUB.ui.closeSheet(); const w=document.getElementById('wlcmHost'); if(w) w.remove(); return 'seeded'})()" % json.dumps(name))
    time.sleep(0.8)
def close_all(c):
    c.js("(()=>{HUB.ui.closeSheet(); if(HUB.notifications&&HUB.notifications.close) HUB.notifications.close(); return 1})()"); time.sleep(0.4)

JS = "(function(){%s})()"
def st(c): return c.js(JS % "return HUB.badges._debug.status()")[0]
def cs(c, sel, prop):
    v, _ = c.js(JS % "const e=document.querySelector(%s); return e?getComputedStyle(e).getPropertyValue(%s):null" % (json.dumps(sel), json.dumps(prop)))
    return (v or '').strip()

def main():
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        f'--remote-debugging-port={PORT}', '--remote-allow-origins=*', '--window-size=390,844',
        f'--user-data-dir={PROF}', '--hide-scrollbars', '--allow-file-access-from-files', BASE],
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
        hook_err(c); time.sleep(2.5); seed_profile(c, 'QA Ari'); drain_err(c, 'load')
        # splash exits ~6.2s after boot; wait for its removal so screenshots show the app
        t0 = time.time()
        while time.time() - t0 < 20:
            if c.js(JS % "return !document.getElementById('splash')")[0]: break
            time.sleep(0.5)
        note(c.js(JS % "return !document.getElementById('splash')")[0], 'splash dismissed before checks')

        # 1. module + non-user-visible debug hook
        note(c.js(JS % "return !!(window.HUB&&HUB.badges&&HUB.badges._debug)")[0], 'HUB.badges + _debug hook present')
        note(c.js(JS % "return document.body.innerText.indexOf('_debug')<0")[0], 'debug hook not user-visible')

        # 2. tier thresholds (pure)
        th, _ = c.js(JS % "const f=HUB.badges.tierOf; return [f(0),f(89),f(90),f(179),f(180),f(364),f(365),f(500)].join(',')")
        note(th == 'new,new,silver,silver,gold,gold,legend,legend', 'tier thresholds 89/90,179/180,364/365', str(th))

        # 3. 60s rule: one tick does not award; forced 60s awards exactly once
        c.js(JS % "HUB.badges._debug.reset(); return 1"); time.sleep(0.3)
        s0 = st(c)
        c.js(JS % "HUB.badges._tick(); return 1")
        s1 = st(c)
        note(s0['loginDays'] == 0 and s1['loginDays'] == 0, 'single 1s tick does not award a login day', json.dumps(s1))
        today, _ = c.js(JS % "return new Date().toISOString().slice(0,10)")
        s2, _ = c.js(JS % "return HUB.badges._debug.simulateMinute()")
        note(s2['loginDays'] == 1 and s2['lastLoginDay'] == today, 'forced 60s foreground awards one login day', json.dumps(s2))

        # 4. same-date no double count; next calendar day counts again
        s3, _ = c.js(JS % "return HUB.badges._debug.simulateMinute()")
        note(s3['loginDays'] == 1, 'same-date second session does not double-count', json.dumps(s3))
        s4, _ = c.js(JS % "HUB.badges._debug.setLastDay('2000-01-01'); return HUB.badges._debug.simulateMinute()")
        note(s4['loginDays'] == 2, 'next calendar day counts again', json.dumps(s4))

        # 5. 89 = NEW, no celebration
        c.js(JS % "HUB.badges._debug.reset(); HUB.badges._debug.setLoginDays(89); return 1"); time.sleep(0.4)
        note(c.js(JS % "return !document.querySelector('.bdg-earn')")[0] and st(c)['tier'] == 'new',
             '89 logins = NEW, no celebration')

        # 6. 90 -> SILVER celebration: exact reason, next guidance, toast (same-tick read)
        r, _ = c.js(JS % """HUB.badges._debug.setLoginDays(90);
          const e=document.querySelector('.bdg-earn');
          return {earn:!!e,
            h1:e?e.querySelector('h1').textContent:'',
            why:e?e.querySelector('.bdg-why').textContent:'',
            need:e?e.querySelector('.bdg-nextneed').textContent:'',
            tip:e?e.querySelector('.bdg-nexttip').textContent:'',
            hero:e?e.querySelector('.bdg-earnart svg').viewBox.baseVal.width:0,
            heroW:e?getComputedStyle(e.querySelector('.bdg-earnart .bdg')).width:'',
            oth:e?e.querySelectorAll('.bdg-oth').length:0,
            othEarn:e?e.querySelectorAll('.bdg-oth-earned').length:0,
            toast:document.getElementById('toastHost').textContent};""")
        note(r['earn'] and 'Badge unlocked!' in r['h1'], '90 -> SILVER earn celebration sheet', r['h1'][:60])
        note(r['why'] == 'You completed 90 active logins.', 'exact earn reason (tier)', r['why'])
        note('90 more daily logins to GOLD' in r['need'], 'accurate next-tier remaining', r['need'])
        note(len(r['tip']) > 20, 'concrete tip present', r['tip'][:60])
        note(r['hero'] == 120 and r['heroW'] == '120px', 'large hero badge = inline SVG 120px', str(r['heroW']))
        note(r['oth'] == 4 and r['othEarn'] == 1, 'other-badges strip: 4 shown, 1 already earned', '%d/%d' % (r['oth'], r['othEarn']))
        note('Badge unlocked!' in r['toast'] and 'SILVER' in r['toast'], 'unlock toast appears', r['toast'][:80])
        shot(c, 'badge-earn-silver')

        # 7. notification center entry -> tap opens showcase
        c.js(JS % "HUB.notifications.open(); return 1"); time.sleep(0.6)
        ni, _ = c.js(JS % """const it=document.querySelector('.item[data-nid="bdg-silver"]');
          const spans=it?it.querySelectorAll('h3 span'):[];
          return it?{t:spans.length?spans[spans.length-1].textContent:'', s:it.querySelector('.meta').textContent,
            unread:!!it.querySelector('.unread'), sys:!!document.querySelector('#hubNotifRows h3')}:null""")
        note(bool(ni) and ni['t'] == 'Badge unlocked!', 'badge unlock in notification center', json.dumps(ni)[:160])
        note(bool(ni) and 'SILVER' in ni['s'] and 'You completed 90 active logins.' in ni['s'],
             'notification carries exact reason', (ni['s'] if ni else '')[:120])
        note(bool(ni) and ni['unread'], 'badge notification is unread')
        shot(c, 'badge-notif-center')
        c.js(JS % "document.querySelector('.item[data-nid=\"bdg-silver\"]').click(); return 1"); time.sleep(0.6)
        note(c.js(JS % "return !!document.querySelector('.bdg-show') && !document.getElementById('hubNotifRoot')")[0],
             'tapping badge notification opens the showcase')
        shot(c, 'badge-showcase-dark')
        close_all(c)

        # 8. no celebration replay without a tier change
        c.js(JS % "HUB.badges._debug.setLoginDays(95); return 1"); time.sleep(0.4)
        note(c.js(JS % "return !document.querySelector('.bdg-earn')")[0], 'no celebration replay without a tier change')

        # 9. SPECIALIST: 99 no-op, 100 celebration with exact reason
        c.js(JS % "HUB.badges._debug.setReviews(99); return 1"); time.sleep(0.4)
        note(c.js(JS % "return !HUB.badges.isSpecialist() && !document.querySelector('.bdg-earn')")[0],
             '99 reviews: not SPECIALIST, no celebration')
        r2, _ = c.js(JS % """HUB.badges._debug.setReviews(100);
          const e=document.querySelector('.bdg-earn');
          return {earn:!!e, txt:e?e.textContent:'', toast:document.getElementById('toastHost').textContent};""")
        note(bool(r2['earn']) and 'SPECIALIST' in r2['txt'], '100 reviews -> SPECIALIST celebration')
        why, _ = c.js(JS % "return HUB.i18n.t('bdg.whySpec')")
        note(bool(why) and why in r2['txt'], 'exact earn reason (specialist)', (why or '')[:60])
        note('SPECIALIST' in r2['toast'], 'specialist unlock toast appears')
        note('85 more daily logins to GOLD' in r2['txt'], 'next-tier remaining accurate at 95 logins')
        note('more professor reviews to SPECIALIST' not in r2['txt'], 'no specialist next-row once earned')
        bf, _ = c.js(JS % "return (HUB.store.state.profile.badgeFeed||[]).map(u=>u.id).join(',')")
        note(bf == 'silver,specialist', 'honest unlock log (badgeFeed)', str(bf))
        shot(c, 'badge-earn-specialist')

        # 10. reduced-motion freezes decorative motion (earn sheet still open)
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
        time.sleep(0.4)
        note(cs(c, '.bdg-shineg', 'animation-name') == 'none', 'reduced-motion: shine sweep frozen')
        note(cs(c, '.bdg-earnburst', 'animation-name') == 'none', 'reduced-motion: celebration burst frozen')
        note(cs(c, '.bdg-earncard', 'animation-name') == 'none', 'reduced-motion: earn card pop frozen')
        note(cs(c, '.bdg-earnart .bdg', 'animation-name') == 'none', 'reduced-motion: hero pulse frozen')
        c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'no-preference'}]})
        time.sleep(0.3)
        close_all(c)

        # 11. ME: badge sits right next to the profile name
        c.js(JS % "HUB.showTab('me'); return 1"); time.sleep(0.8)
        me, _ = c.js(JS % """const row=document.querySelector('.me-namerow');
          const b=document.getElementById('meBadges');
          return row?{inRow:row.contains(b),
            nameNext:!!(row.querySelector('.me-name')&&b),
            order:[...row.children].map(x=>x.className||x.id).join('>'),
            txt:b?b.textContent.trim():'', ic:b?b.querySelectorAll('.me-badges-ic').length:0,
            w:b?getComputedStyle(b.querySelector('.bdg svg')).width:''}:null""")
        note(bool(me) and me['inRow'] and me['nameNext'], 'badge right next to profile name (.me-namerow)', json.dumps(me)[:140] if me else 'null')
        note(bool(me) and 'SILVER' in me['txt'] and me['ic'] == 2, 'ME header: SILVER + SPECIALIST side by side', (me['txt'] if me else '')[:60])
        note(me and me['w'] == '30px', 'inline SVG badge renders at 30px (no fallback)', str(me['w']) if me else 'null')
        shot(c, 'badge-me-header')

        # 12. showcase: 5 cards, locks, progress, float, glow, dimmed, no purple
        c.js(JS % "document.getElementById('meBadges').click(); return 1"); time.sleep(0.6)
        sc, _ = c.js(JS % """const g=document.querySelector('.bdg-grid'); if(!g) return null;
          const cards=[...g.querySelectorAll('.bdg-card')].map(x=>({n:x.querySelector('.bdg-name').textContent,
            locked:x.classList.contains('bdg-islocked'),
            prog:(x.querySelector('.bdg-prog')||{textContent:''}).textContent.trim()}));
          return {count:cards.length, cards:cards, title:document.querySelector('.bdg-show h2').textContent,
            float:getComputedStyle(document.querySelector('.bdg-card:not(.bdg-islocked) .bdg-art .bdg')).animationName,
            floatLocked:getComputedStyle(document.querySelector('.bdg-card.bdg-islocked .bdg-art .bdg')).animationName,
            shine:getComputedStyle(document.querySelector('.bdg-card .bdg-shineg')).animationName,
            glow:getComputedStyle(document.querySelector('.bdg-card .bdg-t-silver svg')).filter,
            dim:getComputedStyle(document.querySelector('.bdg-card.bdg-islocked .bdg-art .bdg')).filter,
            svgOk:[...document.querySelectorAll('.bdg-card .bdg svg')].every(s=>s.viewBox.baseVal.width===120),
            noPurple:['#7c3aed','#8b5cf6','#a855f7','purple'].every(x=>[...document.querySelectorAll('.bdg-card .bdg svg')].map(s=>s.outerHTML).join('').toLowerCase().indexOf(x)<0)}""")
        note(sc and sc['count'] == 5 and sc['title'] == 'Profile badges', 'showcase: 5 cards, correct title')
        lk = [x['n'] for x in sc['cards'] if x['locked']] if sc else []
        note(set(lk) == {'GOLD', 'LEGEND'}, 'gold+legend locked, others unlocked', json.dumps(lk))
        note('95/180' in sc['cards'][1]['prog'] and 'GOLD' in sc['cards'][1]['prog'], 'showcase progress 95/180 to GOLD', sc['cards'][1]['prog'][:60])
        note('SPECIALIST' in sc['cards'][4]['prog'] or '100' in sc['cards'][4]['prog'], 'specialist card shows earned state', sc['cards'][4]['prog'][:60])
        note(sc['float'] == 'bdgfloat', 'showcase float animation runs on unlocked badges', str(sc['float']))
        note(sc['floatLocked'] in ('none', ''), 'locked badges stay static', str(sc['floatLocked']))
        note(sc['shine'] == 'bdgshine', 'shine sweep keyframes run', str(sc['shine']))
        note('drop-shadow' in sc['glow'], 'tier glow on badge art', sc['glow'][:60])
        note('grayscale' in sc['dim'], 'locked badges dimmed', sc['dim'][:60])
        note(sc['svgOk'], 'all badge art is inline SVG (viewBox 120)')
        note(sc['noPurple'], 'no purple anywhere in badge art')
        shot(c, 'badge-showcase-dark2')
        close_all(c)

        # 13. keyframes exist in shipped CSS
        cssv, _ = c.js("fetch('styles.css').then(r=>r.text())", awaitPromise=True)
        for kf in ['bdgshine', 'bdgfloat', 'bdgearnpulse', 'bdgburst', 'bdgpop']:
            note(bool(cssv) and ('@keyframes ' + kf) in cssv, 'CSS keyframes: ' + kf)

        # 14. German: genuinely loaded (identity), then really switched via setLang
        v, _ = c.js("HUB.i18n.loadLocale('de').then(()=>HUB.i18n._dict('de')!==HUB.i18n._dict('en'))", awaitPromise=True)
        note(v is True, 'de locale genuinely loaded (identity, not fallback)')
        c.js(JS % "HUB.i18n.setLang('de'); return 1")
        de_ready = False
        for _ in range(20):
            time.sleep(0.5)
            if c.js(JS % "return HUB.i18n.t('bdg.title')")[0] == 'Profil-Badges':
                de_ready = True; break
        note(de_ready, 'setLang(de) applied (t() serves German)')
        c.js(JS % "HUB.badges._debug.reset(); HUB.badges._debug.setLoginDays(89); HUB.badges._debug.setLoginDays(90); return 1")
        time.sleep(0.5)
        de, _ = c.js(JS % """const e=document.querySelector('.bdg-earn');
          return e?{h1:e.querySelector('h1').textContent, why:e.querySelector('.bdg-why').textContent,
            toast:document.getElementById('toastHost').textContent}:null""")
        note(bool(de) and de['h1'].startswith('Badge freigeschaltet!'), 'German earn title', (de['h1'] if de else '')[:40])
        note(bool(de) and de['why'] == 'Du hast 90 aktive Logins geschafft.', 'German earn reason', (de['why'] if de else ''))
        note(bool(de) and 'Badge freigeschaltet!' in de['toast'], 'German unlock toast')
        c.js(JS % "HUB.notifications.open(); return 1"); time.sleep(0.6)
        den, _ = c.js(JS % """const it=document.querySelector('.item[data-nid="bdg-silver"]');
          const spans=it?it.querySelectorAll('h3 span'):[];
          return spans.length?spans[spans.length-1].textContent:null""")
        note(den == 'Badge freigeschaltet!', 'German notification-center entry', str(den))
        shot(c, 'badge-notif-de')
        close_all(c)
        c.js(JS % "HUB.badges.openShowcase(); return 1"); time.sleep(0.5)
        note(c.js(JS % "return document.querySelector('.bdg-show h2').textContent")[0] == 'Profil-Badges',
             'showcase title in German', c.js(JS % "return document.querySelector('.bdg-show h2').textContent")[0])
        shot(c, 'badge-showcase-de')
        close_all(c)
        c.js(JS % "HUB.i18n.setLang('en'); return 1"); time.sleep(0.5)

        # 15. light theme
        c.js(JS % "HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme(); HUB.badges.openShowcase(); return 1"); time.sleep(0.6)
        note(c.js(JS % "return !document.body.classList.contains('dark')")[0], 'light theme applied')
        shot(c, 'badge-showcase-light')
        close_all(c)
        c.js(JS % "HUB.store.state.prefs.dark=true; HUB.store.save(); HUB.applyTheme(); return 1"); time.sleep(0.4)

        # 16. friends' profiles
        fr, _ = c.js(JS % """const ps=HUB.store.state.people;
          const j=ps.find(p=>p.name==='Jordan Lee'), o=ps.find(p=>p.name==='Omar Haddad');
          return j&&o?{jid:j.id,oid:o.id, jl:j.loginDays, jr:j.profReviews, ol:o.loginDays, orr:o.profReviews}:null""")
        note(bool(fr), 'seed friends present', json.dumps(fr)[:120] if fr else 'null')
        if fr:
            c.js(JS % "HUB.people.openProfile(%s); return 1" % json.dumps(fr['jid'])); time.sleep(0.7)
            jb, _ = c.js(JS % "const r=document.querySelector('.ppl-badgerow'); return r?{n:r.querySelectorAll('.bdg').length,t:r.textContent,w:getComputedStyle(r.querySelector('.bdg svg')).width}:null")
            note(jb and jb['n'] == 2, 'Jordan Lee (400/150): LEGEND + SPECIALIST', json.dumps(jb)[:100] if jb else 'null')
            note(jb and jb['w'] == '26px', 'friend badge inline SVG renders at 26px', str(jb['w']) if jb else 'null')
            shot(c, 'badge-friend-legend')
            c.js(JS % "HUB.ui.closeSheet(); HUB.people.openProfile(%s); return 1" % json.dumps(fr['oid'])); time.sleep(0.7)
            ob, _ = c.js(JS % "const r=document.querySelector('.ppl-badgerow'); return r?r.querySelectorAll('.bdg').length:null")
            note(ob == 1, 'Omar Haddad (10/0): single NEW badge', str(ob))
            close_all(c)

        # 17. glass profile card (PraBin's screenshot): badge next to the person's
        # name, tap opens their read-only showcase
        pg, _ = c.js(JS % """const p=HUB.store.state.people.find(x=>x.name==='Priya Nair');
          return p?{id:p.id}:null""")
        note(bool(pg), 'demo person Priya Nair present', json.dumps(pg) if pg else 'null')
        if pg:
            c.js(JS % "HUB.people.openGlass(%s); return 1" % json.dumps(pg['id'])); time.sleep(0.7)
            gb, _ = c.js(JS % """const row=document.querySelector('.hpglass-namerow');
              const b=row?row.querySelector('.hp-badges'):null;
              const r=b?b.getBoundingClientRect():null;
              const exp=HUB.badges.personTier(HUB.store.find('people',%s));
              const ic=b?b.querySelector('.bdg'):null;
              return row?{inRow:!!b, tag:b?b.tagName:'', vis:r&&r.width>0&&r.height>0,
                tierOk:ic&&ic.className.indexOf('bdg-t-'+exp)>=0, tier:exp,
                w:ic?getComputedStyle(ic.querySelector('svg')).width:''}:null""" % json.dumps(pg['id']))
            note(gb and gb['inRow'] and gb['tag'] == 'BUTTON', 'badge button right next to name on glass card', json.dumps(gb)[:160] if gb else 'null')
            note(gb and gb['vis'] and gb['tierOk'], 'badge visible, tier matches personTier()', (json.dumps(gb)[:140] if gb else 'null'))
            note(gb and gb['w'] == '26px', 'glass badge inline SVG renders at 26px', str(gb['w']) if gb else 'null')
            shot(c, 'badge-glass-card')
            c.js(JS % "document.querySelector('#hpGlassCard .hp-badges').click(); return 1"); time.sleep(0.6)
            ps, _ = c.js(JS % """const s=document.querySelector('.bdg-show');
              if(!s) return null;
              const cards=[...s.querySelectorAll('.bdg-card')].map(x=>({n:x.querySelector('.bdg-name').textContent, locked:x.classList.contains('bdg-islocked')}));
              return {h2:s.querySelector('h2').textContent, count:cards.length, cards:cards,
                noNext:!s.querySelector('.bdg-next'), noEarn:!document.querySelector('.bdg-earn'),
                demoNote:s.textContent.indexOf('Demo profile')>=0}""")
            note(ps and ps['h2'] == 'Priya Nair' and ps['count'] == 5, 'tap opens read-only showcase for the person', json.dumps(ps)[:160] if ps else 'null')
            note(ps and ps['noNext'] and ps['noEarn'], 'person showcase: no next-tips, no earn sheet')
            note(ps and ps['demoNote'], 'person showcase carries the demo-data note')
            shot(c, 'badge-person-showcase')
            c.js(JS % "HUB.ui.closeSheet(); HUB.people.closeGlass(); return 1"); time.sleep(0.5)
            c.js(JS % """const p=HUB.store.state.people.find(x=>x.name==='Priya Nair');
              p.profReviews=150; HUB.store.save(); HUB.people.openGlass(p.id); return 1"""); time.sleep(0.7)
            sp, _ = c.js(JS % """const b=document.querySelector('#hpGlassCard .hp-badges');
              const exp=HUB.badges.personTier(HUB.store.state.people.find(x=>x.name==='Priya Nair'));
              return b?{n:b.querySelectorAll('.bdg').length, spec:!!b.querySelector('.bdg-t-specialist'),
                tier:!!b.querySelector('.bdg-t-'+exp)}:null""")
            note(sp and sp['n'] == 2 and sp['spec'] and sp['tier'], 'SPECIALIST stacks beside tier on glass card', json.dumps(sp) if sp else 'null')
            shot(c, 'badge-glass-specialist')
            c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
            time.sleep(0.4)
            note(cs(c, '#hpGlassCard .hp-badges .bdg-shineg', 'animation-name') == 'none', 'reduced-motion: glass badge shine frozen')
            c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'no-preference'}]})
            time.sleep(0.3)
            c.js(JS % "HUB.people.closeGlass(); return 1"); time.sleep(0.4)
            c.js(JS % "HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme(); HUB.people.openGlass(%s); return 1" % json.dumps(pg['id'])); time.sleep(0.7)
            note(c.js(JS % "return !document.body.classList.contains('dark') && !!document.querySelector('#hpGlassCard .hp-badges')")[0],
                 'glass badge renders in light theme')
            shot(c, 'badge-glass-light')
            c.js(JS % "HUB.people.closeGlass(); HUB.store.state.prefs.dark=true; HUB.store.save(); HUB.applyTheme(); return 1"); time.sleep(0.4)

        # 18. badge tap closes the profile card FIRST, then opens the person's
        # badge collection (PraBin: no stacked layers). Priya Nair stands in
        # for Grace Liu (same glass + sheet paths).
        pg2, _ = c.js(JS % """const p=HUB.store.state.people.find(x=>x.name==='Priya Nair');
          return p?{id:p.id}:null""")
        note(bool(pg2), 'demo person Priya Nair present for close-first test', json.dumps(pg2) if pg2 else 'null')
        if pg2:
            c.js(JS % "HUB.people.openGlass(%s); return 1" % json.dumps(pg2['id'])); time.sleep(0.7)
            c.js(JS % "document.querySelector('#hpGlassCard .hp-badges').click(); return 1"); time.sleep(0.8)
            cf, _ = c.js(JS % """return {glassHidden:document.getElementById('hpGlass').hidden,
              sheetOpen:!document.getElementById('sheetHost').hidden,
              cards:document.querySelectorAll('.bdg-show .bdg-card').length,
              h2:(document.querySelector('.bdg-show h2')||{}).textContent||''}""")
            note(cf and cf['glassHidden'] and cf['sheetOpen'] and cf['cards'] == 5 and cf['h2'] == 'Priya Nair',
                 'glass card: badge tap closes card, opens her 5-badge showcase', json.dumps(cf)[:160] if cf else 'null')
            shot(c, 'badge-closefirst-glass')
            c.js(JS % "(()=>{const x=document.querySelector('#sheetHost .sheetx'); if(x) x.click(); return 1})()"); time.sleep(0.6)
            cx, _ = c.js(JS % """return {sheetHidden:document.getElementById('sheetHost').hidden,
              glassHidden:document.getElementById('hpGlass').hidden}""")
            note(cx and cx['sheetHidden'] and cx['glassHidden'],
                 'showcase close returns cleanly to tab (no half-closed card)', json.dumps(cx) if cx else 'null')
            c.js(JS % "HUB.people.openProfile(%s); return 1" % json.dumps(pg2['id'])); time.sleep(0.7)
            c.js(JS % "document.querySelector('.ppl-badgerow .hp-badges').click(); return 1"); time.sleep(0.8)
            cs2, _ = c.js(JS % """return {sheetOpen:!document.getElementById('sheetHost').hidden,
              isShow:!document.querySelector('#sheetHost .ppl-prof'),
              cards:document.querySelectorAll('.bdg-show .bdg-card').length,
              h2:(document.querySelector('.bdg-show h2')||{}).textContent||''}""")
            note(cs2 and cs2['sheetOpen'] and cs2['isShow'] and cs2['cards'] == 5 and cs2['h2'] == 'Priya Nair',
                 'sheet profile: badge tap closes card, opens her 5-badge showcase', json.dumps(cs2)[:160] if cs2 else 'null')
            shot(c, 'badge-closefirst-sheet')
            c.js(JS % "(()=>{const x=document.querySelector('#sheetHost .sheetx'); if(x) x.click(); return 1})()"); time.sleep(0.6)
            cx2, _ = c.js(JS % "return document.getElementById('sheetHost').hidden")
            note(cx2, 'sheet showcase close returns clean tab state', str(cx2))
            close_all(c)

        drain_err(c, 'final')
        n_fail = sum(1 for ok, _ in checks if not ok)
        print('\n==== %d/%d checks passed, console errors: %d ====' % (len(checks) - n_fail, len(checks), len(errors)))
        for label, ev in errors: print('ERR', label, json.dumps(ev)[:200])
        for ok, label in checks:
            if not ok: print('FAILED:', label)
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
