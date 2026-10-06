#!/usr/bin/env python3
"""QA: block user + group blocked-member note (2026-09-30).
DM: block from thread options -> composer locked, send paths guarded,
    incoming dropped, thread list shows Blocked tag, persists across reload,
    unblock restores composer.
Groups: member sees "blocked user in group" note with stay/leave;
    Yes stays (dismissed), No leaves; requester gets join? Yes/No sheet.
Zero console errors."""
import subprocess, time, json, os, sys, base64
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa import CDP, CHROME, QA
import websocket  # noqa: F401

PORT = 9450
BASE = 'file:///home/hatch/workspace/hub/index.html'
fails = []

def check(n, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + n + ((" | " + str(extra)) if extra else ""))
    if not ok:
        fails.append(n)

def j(c, expr, await_=False):
    e = expr.strip()
    if e.startswith('return '):
        e = e[7:].rstrip()
        if e.endswith(';'):
            e = e[:-1]
    depth, instr, q, top_semi = 0, False, '', False
    for ch in e:
        if instr:
            if ch == q:
                instr = False
        elif ch in '"\'`':
            instr, q = True, ch
        elif ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        elif ch == ';' and depth == 0:
            top_semi = True
            break
    if not top_semi:
        e = 'return (' + e + ');'
    e = '(function(){ ' + e + ' })()'
    r = c.send('Runtime.evaluate', {'expression': e, 'awaitPromise': await_, 'returnByValue': True}, wait=True)
    return ((r or {}).get('result', {}) or {}).get('value')

ERR_SRC = ("window.__huberr=[];"
           "addEventListener('error',e=>__huberr.push('ERR:'+e.message));"
           "addEventListener('unhandledrejection',e=>__huberr.push('REJ:'+((e.reason&&e.reason.message)||e.reason)));")

def boot(c):
    for _ in range(60):
        if j(c, "return !!(window.HUB&&HUB.store&&HUB.store.state&&HUB.chat&&HUB.i18n&&HUB.views&&HUB.views.groups);") is True:
            break
        time.sleep(0.5)
    for _ in range(40):
        if j(c, "return !document.getElementById('splash');") is True:
            break
        time.sleep(0.5)
    j(c, """var p=HUB.store.state.profile; p.name='QA Block'; p.campus='The University of Texas at Dallas';
      p.verified=true; HUB.store.save(); try{HUB.auth.close()}catch(e){} return 1;""")
    time.sleep(0.8)

prof = '/tmp/hubqa-block'
subprocess.run(['rm', '-rf', prof])
proc = subprocess.Popen([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=%d' % PORT, '--allow-file-access-from-files', '--remote-allow-origins=*',
    '--user-data-dir=' + prof, '--hide-scrollbars', '--window-size=390,844', 'about:blank'])
time.sleep(2.5)
tgt = None
for _ in range(30):
    try:
        tgts = json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT, timeout=5).read())
        tgt = [t for t in tgts if t.get('type') == 'page'][0]
        break
    except Exception:
        time.sleep(0.4)
c = CDP(tgt['webSocketDebuggerUrl'])
c.send('Runtime.enable')
c.send('Page.enable')
c.send('Emulation.setDeviceMetricsOverride',
       {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
c.send('Page.addScriptToEvaluateOnNewDocument', {'source':
    "try{localStorage.setItem('orbit_i18n',JSON.stringify({lang:'en',country:'US'}));}catch(e){}" + ERR_SRC})
c.send('Page.navigate', {'url': BASE})
boot(c)

def shot(tag):
    r = c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(QA, 'block-%s.png' % tag), 'wb').write(base64.b64decode(r['data']))

def errs0(tag):
    e = j(c, "return window.__huberr.slice(0,8);")
    check(tag + ' zero console errors', not e, e)

# ---- seed contacts, threads, groups ----
j(c, """HUB.store.state.contacts=[
    {id:'c-rita',name:'Rita Blocked',phone:'+15550001111'},
    {id:'c-maya',name:'Maya Friend',phone:'+15550002222'}];
  HUB.store.state.threads=[
    {id:'t-rita',contactId:'c-rita',title:'Rita Blocked',messages:[{from:'me',at:Date.now(),kind:'text',text:'hey',status:'delivered'}],unread:0},
    {id:'t-maya',contactId:'c-maya',title:'Maya Friend',messages:[],unread:0}];
  HUB.store.state.cgroups=[
    {id:'g-hike',name:'Hike Club',mine:true,live:true,members:['QA Block','Rita Blocked'],requests:[]},
    {id:'g-camp',name:'Camp Club',mine:true,live:true,members:['QA Block','Rita Blocked'],requests:[]},
    {id:'g-trail',name:'Trail Club',mine:false,live:true,members:['QA Block','Rita Blocked'],requests:[]},
    {id:'g-river',name:'River Club',mine:false,live:true,members:['Rita Blocked','Sam Other'],requests:[]}];
  HUB.store.save(); return 1;""")

# ================= DM block =================
j(c, "HUB.chat.openThread('t-rita'); return 1;")
time.sleep(0.6)
check('DM composer present before block', j(c, "return !!document.getElementById('chatSend');") is True)
j(c, "document.getElementById('chMore').click(); return 1;")
time.sleep(0.5)
check('thread sheet shows Block user', j(c, "return !!document.getElementById('blkThread');") is True)
j(c, "document.getElementById('blkThread').click(); return 1;")
time.sleep(0.8)
st = j(c, """return {blocked:HUB.store.state.blocked,
  send:!!document.getElementById('chatSend'),
  unblock:!!document.getElementById('chUnblock'),
  toast:document.getElementById('toastHost').textContent};""")
check('block persisted in store', st['blocked'] == ['id:c-rita'], st['blocked'])
check('composer send gone after block', st['send'] is False, st)
check('unblock button shown after block', st['unblock'] is True, st)
check('blocked toast shown', 'blocked' in st['toast'].lower(), st['toast'][:60])
shot('dm-blocked')

# thread list shows Blocked tag
j(c, "HUB.chat.openList(); return 1;")
time.sleep(0.6)
check('thread list shows Blocked tag', j(c,
    "return Array.from(document.querySelectorAll('#chatRoot .item h3')).some(h=>/Rita Blocked/.test(h.textContent)&&/Blocked/.test(h.textContent));") is True)

# incoming message from blocked contact is dropped
n0 = j(c, "return HUB.store.state.threads.find(t=>t.id==='t-rita').messages.length;")
j(c, "HUB.chat.pushMessage(HUB.store.state.threads.find(t=>t.id==='t-rita'),{from:'Rita Blocked',at:Date.now(),kind:'text',text:'hi there'}); return 1;")
time.sleep(0.4)
n1 = j(c, "return HUB.store.state.threads.find(t=>t.id==='t-rita').messages.length;")
check('incoming from blocked contact dropped', n0 == n1, (n0, n1))

# unblock from the notice restores composer
j(c, "HUB.chat.openThread('t-rita'); return 1;")
time.sleep(0.6)
j(c, "document.getElementById('chUnblock').click(); return 1;")
time.sleep(0.8)
st = j(c, "return {send:!!document.getElementById('chatSend'), blocked:HUB.store.state.blocked};")
check('unblock restores composer', st['send'] is True and st['blocked'] == [], st)

# persistence across reload
j(c, "HUB.block.blockContact(HUB.store.state.contacts[0]); return 1;")
time.sleep(0.4)
c.send('Page.navigate', {'url': BASE})
boot(c)
check('block survives reload', j(c,
    "return HUB.block.isBlockedContact(HUB.store.state.contacts.find(c=>c.id==='c-rita'));") is True)
j(c, "HUB.chat.openThread('t-rita'); return 1;")
time.sleep(0.6)
check('composer still locked after reload', j(c,
    "return !!document.getElementById('chUnblock') && !document.getElementById('chatSend');") is True)
errs0('dm')

# ================= group member note =================
def open_group(gid):
    j(c, "HUB.showTab('groups'); return 1;")
    time.sleep(1.2)
    ok = j(c, "var el=document.querySelector('[data-club=\"%s\"]'); if(el){el.click();return true;} return false;" % gid)
    time.sleep(1.0)
    return ok

check('open Hike Club detail', open_group('g-hike') is True)
nt = j(c, """return {yes:!!document.getElementById('cgStayYes'),
  no:!!document.getElementById('cgStayNo'),
  txt:document.body.textContent};""")
check('blocked note shown to member', nt['yes'] is True and nt['no'] is True and 'Rita Blocked' in nt['txt'], nt['txt'][:80])
shot('group-note')

# No -> leave group
j(c, "document.getElementById('cgStayNo').click(); return 1;")
time.sleep(1.0)
st = j(c, """return {member:(HUB.store.state.cgroups.find(g=>g.id==='g-hike').members||[]),
  backToList:!document.getElementById('cgBack')};""")
check('No leaves the group', 'QA Block' not in st['member'] and st['backToList'] is True, st)

# Yes -> stay, note dismissed
check('open Camp Club detail', open_group('g-camp') is True)
check('note shown on Camp Club', j(c, "return !!document.getElementById('cgStayYes');") is True)
j(c, "document.getElementById('cgStayYes').click(); return 1;")
time.sleep(1.0)
st = j(c, """return {note:!!document.getElementById('cgStayYes'),
  member:(HUB.store.state.cgroups.find(g=>g.id==='g-camp').members||[])};""")
check('Yes stays + note dismissed', st['note'] is False and 'QA Block' in st['member'], st)
# standalone Leave button renders for non-owned groups the user is a member of
check('open Trail Club detail', open_group('g-trail') is True)
check('Leave group button exists for member', j(c, "return !!document.getElementById('cgLeave');") is True)
j(c, "document.getElementById('cgLeave').click(); return 1;")
time.sleep(1.0)
check('Leave button leaves the group', j(c,
    "return (HUB.store.state.cgroups.find(g=>g.id==='g-trail').members||[]);") == ['Rita Blocked'])
errs0('group-member')

# ================= requester join warning =================
check('open River Club detail', open_group('g-river') is True)
check('request button shown (nonmember)', j(c, "return !!document.getElementById('cgReq');") is True)
j(c, "document.getElementById('cgReq').click(); return 1;")
time.sleep(0.8)
w = j(c, """return {yes:!!document.getElementById('cgJoinYes'),
  no:!!document.getElementById('cgJoinNo'),
  txt:(document.querySelector('.sheethost')||{textContent:''}).textContent};""")
check('join warning names blocked user', w['yes'] is True and w['no'] is True and 'Rita Blocked' in w['txt'], w['txt'][:90])
shot('group-joinwarn')
j(c, "document.getElementById('cgJoinNo').click(); return 1;")
time.sleep(0.6)
check('No cancels: no request sent', j(c,
    "return (HUB.store.state.cgroups.find(g=>g.id==='g-river').requests||[]).length;") == 0)
j(c, "document.getElementById('cgReq').click(); return 1;")
time.sleep(0.8)
j(c, "document.getElementById('cgJoinYes').click(); return 1;")
time.sleep(0.8)
check('Yes continues: request sent', j(c,
    "return (HUB.store.state.cgroups.find(g=>g.id==='g-river').requests||[]).length;") == 1)
errs0('group-join')

print('fails=%d' % len(fails))
proc.terminate()
proc.wait()
sys.exit(1 if fails else 0)
