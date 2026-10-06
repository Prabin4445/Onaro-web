#!/usr/bin/env python3
"""HUB QA full: auth (js/auth.js) — functional + visual + i18n + reduced-motion.
Fresh profile /tmp/hubqa-authfull (wiped first), file:// load, 390px, dark+light.

Phases:
  A. signup validation (bad email/phone, short pw, mismatch, no campus, dup email/phone)
  B. full signup: step2 verify-method, step3 wrong-code rejected, resend, correct code
     -> account created + signed in, hub_v1 session (remember default ON)
  C. login: email + phone variants, wrong pw, unknown account, smart-identifier detection;
     wake-up glow moment; remember-ON survives Page.reload
  D. remember-OFF: no hub_v1 session, sessionStorage tmp only, same-tab reload keeps
     session, logout clears both
  E. Face ID: headless no-fake -> unavailable (button hidden + honest note);
     fake available -> enroll stores cred -> login via Face ID; fake rejects -> honest error
  F. i18n: real German via setLang('de') (dict identity, rendered copy, kh check)
  G. reduced-motion: animations frozen under emulation
  H. screenshots of every step, dark + light @390px, for designer review
  I. zero console errors (CDP siphon + window.__huberr)
"""
import json, subprocess, time, urllib.request, os, shutil, sys, base64
try:
    import websocket
except ImportError:
    print('websocket-client missing'); sys.exit(2)

CHROME = '/opt/meta-chromium/chrome'; PORT = 9445
BASE = 'file:///home/hatch/workspace/hub/index.html'
PROF = '/tmp/hubqa-authfull'
SHOTDIR = os.path.expanduser('~/workspace/hub/qa')
JS = "(function(){%s})()"
checks = []
def note(ok, label, detail=''):
    checks.append(bool(ok)); print(('PASS' if ok else 'FAIL'), label, detail)

FAKE_OK = ("{isUserVerifyingPlatformAuthenticatorAvailable:function(){return Promise.resolve(true)},"
           "create:function(){return Promise.resolve({rawId:new Uint8Array([1,2,3,4]).buffer})},"
           "get:function(){return Promise.resolve({})}}")
FAKE_REJECT = ("{isUserVerifyingPlatformAuthenticatorAvailable:function(){return Promise.resolve(true)},"
               "create:function(){return Promise.reject(new Error('x'))},"
               "get:function(){return Promise.reject(new Error('x'))}}")

class CDP:
    def __init__(self, wsurl):
        self.ws = websocket.create_connection(wsurl, timeout=12); self.ws.settimeout(12)
        self.id = 0; self.events = []
    def send(self, method, params=None):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params or {}}))
        deadline = time.time() + 15
        while time.time() - t0() < 15:
            try: msg = json.loads(self.ws.recv())
            except Exception as e: raise TimeoutError(method + ': ' + str(e)[:80])
            if 'method' in msg and 'id' not in msg:
                self.events.append(msg); continue
            if msg.get('id') == self.id: return msg.get('result')
        raise TimeoutError(method)
    def js(self, expr, awaitPromise=False):
        try:
            r = self.send('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': awaitPromise})
            res = (r or {}).get('result', {})
            return res.get('value'), res.get('exceptionDetails')
        except Exception as e: return None, str(e)[:160]
    def shot(self, name):
        r = self.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 82, 'fromSurface': True})
        with open(os.path.join(SHOTDIR, name), 'wb') as f: f.write(base64.b64decode(r['data']))
        print('SHOT', name)

def t0(): return time.time()

def js_wait(c, expr, timeout=12):
    t = time.time()
    while time.time() - t < timeout:
        v, _ = c.js(JS % expr)
        if v: return True
        time.sleep(0.4)
    return False

def setval(c, sel, val):
    c.js(JS % ("var el=document.querySelector(%s); el.value=%s;"
               "el.dispatchEvent(new Event('input',{bubbles:true}));"
               "el.dispatchEvent(new Event('change',{bubbles:true})); return 1"
               % (json.dumps(sel), json.dumps(val))))

def clear_toasts(c):
    c.js(JS % "var h=document.getElementById('toastHost'); if(h) h.innerHTML=''; return 1")

def last_toast(c):
    v, _ = c.js(JS % "var h=document.getElementById('toastHost'); var ts=h?h.querySelectorAll('.toast'):[];"
                      "return ts.length?ts[ts.length-1].textContent:''")
    return v or ''

def su_err(c, eid='suErr1'):
    v, _ = c.js(JS % "var e=document.getElementById(%s); return e?{vis:!e.hidden,txt:e.textContent}:null" % json.dumps(eid))
    return v

def pick_campus(c, name='QA University', city='Austin'):
    """Drive the real campus picker manual-add path; returns True when label shows."""
    c.js(JS % "document.getElementById('suCampus').click(); return 1")
    if not js_wait(c, "return !!document.getElementById('intlAddManual')", 10): return False
    c.js(JS % "document.getElementById('intlAddManual').click(); return 1"); time.sleep(0.4)
    setval(c, '#intlCustomName', name); setval(c, '#intlCustomCity', city)
    c.js(JS % "document.getElementById('intlCustomAdd').click(); return 1")
    return js_wait(c, "return (document.getElementById('suCampusLabel')||{}).textContent===%s" % json.dumps(name), 8)

def fill_su1(c, name, email, num, pw, pw2=None, campus=True):
    setval(c, '#suName', name); setval(c, '#suEmail', email); setval(c, '#suNum', num)
    setval(c, '#suPw', pw); setval(c, '#suPw2', pw if pw2 is None else pw2)
    if campus:
        if not pick_campus(c): return False
    c.js(JS % "document.getElementById('suNext1').click(); return 1")
    return js_wait(c, "return !!document.getElementById('suSend')", 8)

def enter_code(c, code):
    for i, ch in enumerate(code):
        setval(c, "#suCodes .auth-code:nth-child(%d)" % (i + 1), ch)

def boot(c):
    ok = js_wait(c, "return !document.getElementById('splash')", 25)
    note(ok, 'splash dismissed')
    c.js(JS % "localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));"
              "var s=HUB.store.state; s.profile.name='QA User'; s.profile.campus='QA Campus';"
              "s.prefs.dark=true; HUB.store.save(); return 1")
    c.send('Page.reload')
    arm_hooks(c)
    ok = js_wait(c, "return document.readyState==='complete' && !document.getElementById('splash') && !!window.HUB && !!HUB.auth", 25)
    note(ok, 'clean boot after seed')
    c.js(JS % "try{HUB.ui.closeSheet()}catch(e){} var w=document.getElementById('wlcmHost'); if(w) w.remove(); return 1")
    time.sleep(0.6)

def phaseA(c):
    print('--- A: signup validation ---')
    cases = [
        ('empty name',      dict(name='', email='a@b.com', num='5551234567', pw='Sup3r$ecretPass!'), 'name'),
        ('bad email',       dict(name='QA', email='not-an-email', num='5551234567', pw='Sup3r$ecretPass!'), 'email'),
        ('bad phone',       dict(name='QA', email='a@b.com', num='123', pw='Sup3r$ecretPass!'), 'phone'),
        ('short pw',        dict(name='QA', email='a@b.com', num='5551234567', pw='short'), '8 characters'),
        ('pw mismatch',     dict(name='QA', email='a@b.com', num='5551234567', pw='Sup3r$ecretPass!', pw2='Different1!'), 'match'),
        ('no campus',       dict(name='QA', email='a@b.com', num='5551234567', pw='Sup3r$ecretPass!'), 'campus'),
    ]
    for label, f, needle in cases:
        c.js(JS % "HUB.auth.close(); HUB.auth.openSignup(); return 1"); time.sleep(0.3)
        clear_toasts(c)
        setval(c, '#suName', f['name']); setval(c, '#suEmail', f['email']); setval(c, '#suNum', f['num'])
        setval(c, '#suPw', f['pw']); setval(c, '#suPw2', f.get('pw2', f['pw']))
        if label != 'no campus':
            pass  # no campus picked on purpose for that case
        c.js(JS % "document.getElementById('suNext1').click(); return 1"); time.sleep(0.4)
        e = su_err(c)
        ok = e and e['vis'] and needle in e['txt'].lower()
        note(ok, 'signup validation: ' + label, json.dumps(e)[:90])
        t = last_toast(c)
        note(needle in t.lower(), 'signup toast: ' + label, t[:60])
    c.js(JS % "HUB.auth.close(); return 1")
    # visual: step 1 dark
    c.js(JS % "HUB.auth.openSignup(); return 1"); time.sleep(0.9)
    c.shot('shot-auth-su1-dark.jpg'); c.js(JS % "HUB.auth.close(); return 1")

def phaseB(c):
    print('--- B: full signup ---')
    c.js(JS % "HUB.auth.openSignup(); return 1"); time.sleep(0.4)
    ok = fill_su1(c, 'Dup Tester', 'dup@example.com', '5551112222', 'Sup3r$ecretPass!')
    note(ok, 'signup step1 -> step2 (real campus picker)')
    time.sleep(0.9); c.shot('shot-auth-su2-dark.jpg')
    c.js(JS % "document.getElementById('suSend').click(); return 1")
    ok = js_wait(c, "return !!document.querySelector('#suCodes .auth-code')", 8)
    note(ok, 'verify-method -> code step')
    v, _ = c.js(JS % "return (HUB.auth._debug.lastCode()||{}).code")
    note(v and len(v) == 6 and v.isdigit(), 'demo code issued (6 digits)', repr(v))
    time.sleep(0.9); c.shot('shot-auth-su3-dark.jpg')
    # wrong code rejected
    clear_toasts(c); enter_code(c, '000000'); time.sleep(0.6)
    e = su_err(c, 'suErr3')
    note(e and e['vis'] and 'code' in e['txt'].lower(), 'wrong code rejected', json.dumps(e)[:80])
    # resend issues a fresh code
    old = v
    c.js(JS % "document.getElementById('suResend').click(); return 1"); time.sleep(0.5)
    v, _ = c.js(JS % "return (HUB.auth._debug.lastCode()||{}).code")
    note(v and v != old, 'resend issues new code', repr(v))
    # correct code -> account created + signed in (no Face ID fake: overlay closes)
    enter_code(c, v)
    ok = js_wait(c, "return !!HUB.auth.currentUser()", 8)
    note(ok, 'correct code -> signed in')
    time.sleep(0.6)
    u, _ = c.js(JS % "var u=HUB.auth.currentUser()||{}; return {name:u.name,email:u.email,phone:u.phoneE164}")
    note(u and u['name'] == 'Dup Tester' and u['email'] == 'dup@example.com', 'account created', json.dumps(u)[:80])
    s, _ = c.js(JS % "var st=JSON.parse(localStorage.getItem('hub_v1')||'{}'); return (st.auth||{}).session||null")
    note(s and s['uid'] and s['remember'] is True, 'hub_v1 session persisted (remember default ON)', json.dumps(s)[:80] if s else '')
    n, _ = c.js(JS % "return HUB.auth._debug.users().length")
    note(n == 1, 'one user in store', repr(n))
    # ME card signed-in
    c.js(JS % "HUB.showTab('me'); return 1"); time.sleep(1.0)
    v, _ = c.js(JS % "return {name:(document.querySelector('.auth-acct-name')||{}).textContent,"
                      " logout:!!document.getElementById('acLogout')}")
    note(v and v['name'] == 'Dup Tester' and v['logout'], 'ME card signed-in (name + logout)', json.dumps(v))
    c.js(JS % "var el=document.querySelector('.auth-acct'); if(el) el.scrollIntoView({block:'center'}); return 1")
    time.sleep(0.7)
    c.shot('shot-auth-me-in-dark.jpg')
    # duplicates rejected
    c.js(JS % "HUB.auth.logout(); return 1"); time.sleep(0.4)
    c.js(JS % "HUB.auth.openSignup(); return 1"); time.sleep(0.3)
    setval(c, '#suName', 'Dup Two'); setval(c, '#suEmail', 'dup@example.com')
    setval(c, '#suNum', '5559998888'); setval(c, '#suPw', 'Sup3r$ecretPass!'); setval(c, '#suPw2', 'Sup3r$ecretPass!')
    pick_campus(c)
    c.js(JS % "document.getElementById('suNext1').click(); return 1"); time.sleep(0.4)
    e = su_err(c)
    note(e and e['vis'] and 'email' in e['txt'].lower(), 'duplicate email rejected', (e or {}).get('txt','')[:60])
    setval(c, '#suEmail', 'dup2@example.com'); setval(c, '#suNum', '5551112222')
    c.js(JS % "document.getElementById('suNext1').click(); return 1"); time.sleep(0.4)
    e = su_err(c)
    note(e and e['vis'] and 'phone' in e['txt'].lower() or 'number' in (e or {}).get('txt','').lower(),
         'duplicate phone rejected', (e or {}).get('txt','')[:60])
    c.js(JS % "HUB.auth.close(); return 1")

def phaseC(c):
    print('--- C: login variants + wake moment + remember-ON reload ---')
    # email variant
    clear_toasts(c)
    c.js(JS % "HUB.auth.openLogin(); return 1"); time.sleep(0.9)
    c.shot('shot-auth-login-dark.jpg')
    setval(c, '#aId', 'dup@example.com'); setval(c, '#aPw', 'Sup3r$ecretPass!')
    c.js(JS % "document.getElementById('aLogin').click(); return 1")
    time.sleep(0.85)
    w, _ = c.js(JS % "return !!document.querySelector('.auth-wake')")
    note(w, 'wake-up glow fires mid-login')
    c.shot('shot-auth-wake.jpg')
    ok = js_wait(c, "return document.getElementById('authRoot').hidden && !!(HUB.auth.currentUser()||{}).name", 8)
    note(ok, 'login via email -> signed in, overlay closed')
    # remember-ON survives reload
    c.send('Page.reload')
    arm_hooks(c)
    ok = js_wait(c, "return document.readyState==='complete' && !document.getElementById('splash') && (HUB.auth.currentUser()||{}).name==='Dup Tester'", 25)
    note(ok, 'remember-ON persists across reload')
    # wrong password
    c.js(JS % "HUB.auth.logout(); HUB.auth.openLogin(); return 1"); time.sleep(0.4)
    clear_toasts(c)
    setval(c, '#aId', 'dup@example.com'); setval(c, '#aPw', 'WrongPass1!')
    c.js(JS % "document.getElementById('aLogin').click(); return 1"); time.sleep(0.4)
    v, _ = c.js(JS % "var e=document.getElementById('aErr'); return e?{vis:!e.hidden,txt:e.textContent}:null")
    note(v and v['vis'] and 'password' in v['txt'].lower(), 'wrong password -> auth.errWrongPw', (v or {}).get('txt','')[:50])
    # unknown account (email + phone)
    setval(c, '#aId', 'nobody@example.com'); setval(c, '#aPw', 'Whatever1!')
    c.js(JS % "document.getElementById('aLogin').click(); return 1"); time.sleep(0.4)
    v, _ = c.js(JS % "var e=document.getElementById('aErr'); return e?e.textContent:''")
    note('No account' in (v or ''), 'unknown email -> auth.errUnknown', (v or '')[:50])
    setval(c, '#aId', '9998887777'); setval(c, '#aPw', 'Whatever1!')
    c.js(JS % "document.getElementById('aLogin').click(); return 1"); time.sleep(0.4)
    v, _ = c.js(JS % "var e=document.getElementById('aErr'); return e?e.textContent:''")
    note('No account' in (v or ''), 'unknown phone -> auth.errUnknown', (v or '')[:50])
    # smart identifier: malformed email (has @, no domain) -> email error path
    setval(c, '#aId', 'a@b'); c.js(JS % "document.getElementById('aLogin').click(); return 1"); time.sleep(0.4)
    v, _ = c.js(JS % "var e=document.getElementById('aErr'); return e?e.textContent:''")
    note('email' in (v or '').lower(), 'smart identifier: bad email format detected', (v or '')[:50])
    # phone variant login
    setval(c, '#aId', '5551112222'); setval(c, '#aPw', 'Sup3r$ecretPass!')
    c.js(JS % "document.getElementById('aLogin').click(); return 1")
    ok = js_wait(c, "return document.getElementById('authRoot').hidden && (HUB.auth.currentUser()||{}).name==='Dup Tester'", 8)
    note(ok, 'login via phone -> signed in')

def phaseD(c):
    print('--- D: remember-OFF ---')
    c.js(JS % "HUB.auth.logout(); HUB.auth.openLogin(); return 1"); time.sleep(0.4)
    c.js(JS % "document.getElementById('aRemember').click(); return 1"); time.sleep(0.3)
    v, _ = c.js(JS % "return document.getElementById('aRemember').classList.contains('on')")
    note(v is False, 'remember toggle switches OFF')
    setval(c, '#aId', '5551112222'); setval(c, '#aPw', 'Sup3r$ecretPass!')
    c.js(JS % "document.getElementById('aLogin').click(); return 1")
    ok = js_wait(c, "return document.getElementById('authRoot').hidden && !!(HUB.auth.currentUser()||{}).name", 8)
    note(ok, 'login with remember OFF -> signed in')
    v, _ = c.js(JS % "var st=JSON.parse(localStorage.getItem('hub_v1')||'{}');"
                      "var tmp=null; try{tmp=sessionStorage.getItem('hub_auth_tmp')}catch(e){};"
                      "return {hub:!!((st.auth||{}).session), tmp:!!tmp, tmpUid:tmp?JSON.parse(tmp).uid:null}")
    note(v and not v['hub'] and v['tmp'], 'hub_v1 has NO session; sessionStorage tmp only', json.dumps(v)[:80])
    uid = v['tmpUid'] if v else None
    c.send('Page.reload')
    arm_hooks(c)
    ok = js_wait(c, "return document.readyState==='complete' && !document.getElementById('splash') && !!(HUB.auth.currentUser()||{}).name", 25)
    v2, _ = c.js(JS % "return (HUB.auth.currentUser()||{}).id")
    note(ok and v2 == uid, 'same-tab reload keeps tab session (sessionStorage restore)')
    # logout clears both
    c.js(JS % "HUB.auth.logout(); return 1"); time.sleep(0.5)
    v, _ = c.js(JS % "var st=JSON.parse(localStorage.getItem('hub_v1')||'{}');"
                      "var tmp='x'; try{tmp=sessionStorage.getItem('hub_auth_tmp')}catch(e){tmp='x'};"
                      "return {hub:!!((st.auth||{}).session), tmp:tmp, user:!!HUB.auth.currentUser()}")
    note(v and not v['hub'] and v['tmp'] is None and not v['user'], 'logout clears hub_v1 + sessionStorage', json.dumps(v))
    c.js(JS % "HUB.showTab('me'); return 1"); time.sleep(1.0)
    v, _ = c.js(JS % "return {login:!!document.getElementById('acLogin'), signup:!!document.getElementById('acSignup')}")
    note(v and v['login'] and v['signup'], 'ME card back to signed-out')
    c.js(JS % "var el=document.querySelector('.auth-acct'); if(el) el.scrollIntoView({block:'center'}); return 1")
    time.sleep(0.7)
    c.shot('shot-auth-me-out-dark.jpg')
    # signed-out Sign up button opens the overlay
    c.js(JS % "document.getElementById('acSignup').click(); return 1"); time.sleep(0.4)
    v, _ = c.js(JS % "return !document.getElementById('authRoot').hidden && !!document.getElementById('suName')")
    note(v, 'ME card Sign up opens signup overlay')
    c.js(JS % "HUB.auth.close(); return 1")

def phaseE(c):
    print('--- E: Face ID ---')
    c.js(JS % "HUB.auth._debug.reset(); HUB.auth._debug.setCredApi(null); return 1")
    v, _ = c.js(JS % "return HUB.auth.faceIdAvailable()", awaitPromise=True)
    note(v is False, 'headless: faceIdAvailable() false without real authenticator', repr(v))
    c.js(JS % "HUB.auth.openLogin(); return 1")
    ok = js_wait(c, "return !document.getElementById('aFaceNote').hidden && "
                    "document.getElementById('aFaceWrap').hidden", 10)
    v, _ = c.js(JS % "return document.getElementById('aFaceNote').textContent")
    note(ok and "isn't available" in (v or ''), 'unavailable: button hidden + honest note shown', (v or '')[:60])
    clear_toasts(c); time.sleep(0.6); c.shot('shot-auth-faceid-na-dark.jpg')
    c.js(JS % "HUB.auth.close(); return 1")
    # inject the fake -> enroll a user with Face ID
    c.js(JS % "HUB.auth._debug.setCredApi(%s); return 1" % FAKE_OK)
    v, _ = c.js(JS % "return HUB.auth.faceIdAvailable()", awaitPromise=True)
    note(v is True, 'fake: faceIdAvailable() true via real path')
    c.js(JS % "HUB.auth.openSignup(); return 1"); time.sleep(0.4)
    ok = fill_su1(c, 'Face Tester', 'face@example.com', '5552223333', 'Sup3r$ecretPass!')
    note(ok, 'signup step1 -> step2 (face user)')
    c.js(JS % "document.getElementById('suSend').click(); return 1")
    js_wait(c, "return !!document.querySelector('#suCodes .auth-code')", 8)
    v, _ = c.js(JS % "return (HUB.auth._debug.lastCode()||{}).code")
    enter_code(c, v)
    ok = js_wait(c, "return !!document.getElementById('enRoll')", 10)
    note(ok, 'post-verify: Face ID enroll/welcome screen appears')
    time.sleep(0.45)
    n, _ = c.js(JS % "return document.querySelectorAll('.auth-bmote').length")
    note(n and n > 8, 'sparkle burst motes mid-flight', repr(n))
    c.shot('shot-auth-burst.jpg')
    time.sleep(0.9); c.shot('shot-auth-enroll-dark.jpg')
    clear_toasts(c)
    c.js(JS % "document.getElementById('enRoll').click(); return 1")
    ok = js_wait(c, "return document.getElementById('authRoot').hidden", 8)
    u, _ = c.js(JS % "return HUB.auth._debug.users()")
    note(ok and u and u[0].get('faceId') is True, 'enroll stores credential, overlay closes', json.dumps(u)[:120])
    note("Face ID" in last_toast(c) or "face" in last_toast(c).lower(), 'enroll success toast', last_toast(c)[:60])
    # logout -> login screen offers Face ID
    c.js(JS % "HUB.auth.logout(); HUB.auth.openLogin(); return 1")
    ok = js_wait(c, "return !document.getElementById('aFaceWrap').hidden", 10)
    note(ok, '"Use Face ID" button appears on login')
    clear_toasts(c); time.sleep(0.6); c.shot('shot-auth-face-dark.jpg')
    clear_toasts(c)
    c.js(JS % "document.getElementById('aFace').click(); return 1")
    ok = js_wait(c, "return document.getElementById('authRoot').hidden && (HUB.auth.currentUser()||{}).name==='Face Tester'", 8)
    note(ok, 'Face ID login signs in as the enrolled user')
    # fake rejects -> honest error, stays signed out
    c.js(JS % "HUB.auth._debug.setCredApi(%s); HUB.auth.logout(); HUB.auth.openLogin(); return 1" % FAKE_REJECT)
    js_wait(c, "return !document.getElementById('aFaceWrap').hidden", 10)
    clear_toasts(c)
    c.js(JS % "document.getElementById('aFace').click(); return 1"); time.sleep(0.6)
    v, _ = c.js(JS % "return {toast:(document.getElementById('toastHost')||{}).textContent||'', user:!!HUB.auth.currentUser()}")
    note(v and "isn't available" in v['toast'] and not v['user'], 'fake rejects -> honest error, no sign-in', (v or {}).get('toast','')[:60])
    c.js(JS % "HUB.auth.close(); HUB.auth._debug.setCredApi(null); return 1")

def phaseG(c):
    print('--- G: reduced motion ---')
    c.js(JS % "HUB.auth.openLogin(); return 1"); time.sleep(0.4)
    c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
    time.sleep(0.4)
    v, _ = c.js(JS % "var m=document.querySelector('.auth-motes i');"
                      "var s=document.querySelector('.auth-step');"
                      "return {mote:getComputedStyle(m).animationName, step:getComputedStyle(s).animationName}")
    note(v and v['mote'] == 'none' and v['step'] == 'none', 'animations frozen under reduced-motion', json.dumps(v))
    c.send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'no-preference'}]})
    c.js(JS % "HUB.auth.close(); return 1")

def phaseH_light(c):
    print('--- H: light-mode pass (signup user C with Face ID fake -> enroll shot) ---')
    c.js(JS % "HUB.store.state.prefs.dark=false; HUB.store.save(); HUB.applyTheme(); return 1"); time.sleep(0.8)
    c.js(JS % "HUB.auth._debug.setCredApi(%s); HUB.auth.openLogin(); return 1" % FAKE_OK); time.sleep(0.9)
    c.shot('shot-auth-login-light.jpg')
    c.js(JS % "HUB.auth.openSignup(); return 1"); time.sleep(0.9)
    c.shot('shot-auth-su1-light.jpg')
    ok = fill_su1(c, 'Light Tester', 'light@example.com', '5553334444', 'Sup3r$ecretPass!')
    note(ok, 'light: signup step1 -> step2')
    time.sleep(0.9); c.shot('shot-auth-su2-light.jpg')
    c.js(JS % "document.getElementById('suSend').click(); return 1")
    js_wait(c, "return !!document.querySelector('#suCodes .auth-code')", 8)
    time.sleep(0.9); c.shot('shot-auth-su3-light.jpg')
    v, _ = c.js(JS % "return (HUB.auth._debug.lastCode()||{}).code")
    enter_code(c, v)
    ok = js_wait(c, "return !!document.getElementById('enRoll')", 10)
    note(ok, 'light: enroll screen appears')
    time.sleep(1.2); c.shot('shot-auth-enroll-light.jpg')
    c.js(JS % "document.getElementById('enSkip').click(); return 1"); time.sleep(0.5)
    c.js(JS % "HUB.auth.logout(); HUB.auth.openLogin(); return 1")
    ok = js_wait(c, "return !document.getElementById('aFaceWrap').hidden", 10)
    note(ok, 'light: Face ID button visible')
    clear_toasts(c); time.sleep(0.6); c.shot('shot-auth-face-light.jpg')
    c.js(JS % "HUB.auth.close(); HUB.auth._debug.setCredApi(null);"
              "HUB.store.state.prefs.dark=true; HUB.store.save(); HUB.applyTheme(); return 1")

def phaseF_i18n(c):
    print('--- F: i18n German ---')
    c.js(JS % "HUB.auth._debug.reset(); return 1")
    c.js(JS % "HUB.i18n.setLang('de'); return 1")
    ok = js_wait(c, "return HUB.i18n._dict('de')!==HUB.i18n._dict('en') && Object.keys(HUB.i18n._dict('de')).length>1500", 20)
    note(ok, "de dict really loaded (identity !== en)")
    c.js(JS % "HUB.auth.openLogin(); return 1")
    v, _ = c.js(JS % "return {btn:document.getElementById('aLogin').textContent,"
                      " want:HUB.i18n._dict('de')['auth.loginBtn'],"
                      " title:document.querySelector('.auth-title').textContent,"
                      " wantT:HUB.i18n._dict('de')['auth.loginTitle']}")
    note(v and v['btn'] == v['want'] and v['title'] == v['wantT'], 'rendered German copy (loginBtn + title)',
         json.dumps(v)[:120])
    time.sleep(0.8); c.shot('shot-auth-login-de.jpg')
    v, _ = c.js(JS % """return fetch('data/locales/de.json').then(function(r){return r.json()}).then(function(d){
        var keys=Object.keys(HUB.i18n._dict('en')).join('\\n'), h=5381, i;
        for(i=0;i<keys.length;i++) h=((h<<5)+h+keys.charCodeAt(i))>>>0;
        return {fileKh:d.kh, liveKh:h.toString(36)};
      }).catch(function(e){return {err:String(e)}})""", awaitPromise=True)
    note(v and not v.get('err') and v['fileKh'] == v['liveKh'], 'de.json kh === live keyhash', json.dumps(v)[:80])
    c.js(JS % "HUB.auth.close(); HUB.i18n.setLang('en'); return 1")

def collect_errors(c):
    bad = []
    for ev in c.events:
        m = ev.get('method', '')
        if m == 'Runtime.exceptionThrown':
            bad.append('EXC:' + json.dumps(ev['params'].get('exceptionDetails', {}).get('text', ''))[:140])
        elif m == 'Log.entryAdded' and ev['params']['entry'].get('level') == 'error':
            bad.append('LOG:' + ev['params']['entry'].get('text', '')[:140])
        elif m == 'Runtime.consoleAPICalled' and ev['params'].get('type') == 'error':
            bad.append('CON:' + json.dumps(ev['params'].get('args', []))[:140])
    v, _ = c.js("window.__huberr?window.__huberr.splice(0):[]")
    if v: bad.append('HOOK:' + json.dumps(v)[:400])
    return bad

def arm_hooks(c):
    c.js("window.__huberr=[];addEventListener('error',e=>window.__huberr.push('ERR:'+e.message));"
         "addEventListener('unhandledrejection',e=>window.__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)))")

def main():
    shutil.rmtree(PROF, ignore_errors=True)
    proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
        '--remote-debugging-port=%d' % PORT, '--remote-allow-origins=*', '--window-size=390,844',
        '--user-data-dir=%s' % PROF, '--hide-scrollbars', '--allow-file-access-from-files', BASE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(30):
            time.sleep(1)
            try:
                with urllib.request.urlopen('http://localhost:%d/json/list' % PORT, timeout=5) as r:
                    ts = json.load(r)
                tgt = next(t for t in ts if t['type'] == 'page' and 'devtools' not in t['url']); break
            except Exception: continue
        else: raise RuntimeError('no target')
        c = CDP(tgt['webSocketDebuggerUrl'])
        c.send('Runtime.enable'); c.send('Page.enable'); c.send('Log.enable')
        arm_hooks(c)
        boot(c)
        phaseA(c); phaseB(c); phaseC(c); phaseD(c); phaseE(c)
        phaseG(c); phaseH_light(c); phaseF_i18n(c)
        bad = collect_errors(c)
        note(not bad, 'zero console errors', '; '.join(bad)[:400])
        n = sum(checks); tot = len(checks)
        print('AUTH QA: %d/%d' % (n, tot))
        sys.exit(0 if n == tot else 1)
    finally:
        proc.terminate()

if __name__ == '__main__':
    main()
