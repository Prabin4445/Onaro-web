/* HUB auth: Firebase Authentication (Email/Password) + Onaro backend.
   - Signup/login go through the Firebase JS SDK (compat build, loaded in
     index.html). Firebase sends the verification email and the password-reset
     email — no SMTP/API keys on our side.
   - Email MUST be verified in Firebase before the backend allows login.
   - After Firebase auth, the ID token is POSTed to /v1/auth/firebase with the
     phone/country/name; the backend verifies the token and returns our own
     access_token + user. Phone is REQUIRED for new accounts (PraBin's rule).
   - Session: remember-me ON (default) persists in hub_v1; OFF keeps the
     session in sessionStorage only. Firebase persistence is aligned with the
     same choice (LOCAL vs SESSION). Logout signs out of Firebase too.
   - Face ID = WebAuthn platform authenticator, all honest: if the device or
     browser can't do it we say so (auth.faceIdNA) — never a fake prompt.
   - UI: full-page .authroot overlay (z-220) with a water-crystal aesthetic that
     continues the splash screen: dimmed splash art backdrop, rising sparkle
     motes, frosted crystal cards with gloss, volt accents. Every animation is
     transform/opacity-only (iOS-safe) and frozen under prefers-reduced-motion.
     iOS: margin-auto centering, never flex-center a fixed host.
     .authroot[hidden]{display:none} (hidden-vs-display lesson).
   - Escape: app.js's global handler defers while .authroot is visible; this
     module owns Escape (closes a topmost sheet first, else the overlay).
   - QA seams: HUB.auth._debug {reset,users,setCredApi,faceIdAvailable}. */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };
const esc=function(s){ return String(s==null?'':s).replace(/[&<>"']/g,function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); };

/* ================= Firebase ================= */
var FIREBASE_CONFIG={
  apiKey:"AIzaSyDuRo2TpayHkrj1pxkh4d3dSL1XQYbgeec",
  authDomain:"onaro-ab57a.firebaseapp.com",
  projectId:"onaro-ab57a",
  storageBucket:"onaro-ab57a.firebasestorage.app",
  messagingSenderId:"944953080289",
  appId:"1:944953080289:web:97ad5ecd23bbb1cd41baa0"
};
var fbAuth=null, fbInitErr=null;
function firebaseReady(){
  if(fbAuth) return Promise.resolve(fbAuth);
  if(fbInitErr) return Promise.reject(fbInitErr);
  return new Promise(function(res,rej){
    try{
      if(!(window.firebase&&firebase.auth)){ throw new Error('firebase-sdk-missing'); }
      if(!firebase.apps.length) firebase.initializeApp(FIREBASE_CONFIG);
      fbAuth=firebase.auth();
      res(fbAuth);
    }catch(e){ fbInitErr=e; rej(e); }
  });
}
/* Map Firebase error codes to our honest inline messages. */
function firebaseErrMsg(e){
  var code=(e&&e.code)||'';
  if(e&&e.message==='firebase-sdk-missing') return t('auth.errNeedOnline');
  if(code==='auth/user-not-found') return t('auth.errUnknown');
  if(code==='auth/wrong-password') return t('auth.errWrongPw');
  if(code==='auth/invalid-email') return t('auth.errBadEmail');
  if(code==='auth/email-already-in-use') return t('auth.errDupEmail');
  if(code==='auth/weak-password') return t('auth.errPwShort');
  if(code==='auth/network-request-failed') return t('auth.errNeedOnline');
  if(code==='auth/too-many-requests') return t('auth.errLoginFailed');
  if(code==='auth/invalid-credential') return t('auth.errLoginFailed');
  return (e&&e.message)||t('auth.errLoginFailed');
}
var EMAIL_RE=/^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/* ================= state ================= */
function ag(){
  var st=HUB.store.state;
  if(!st.auth||typeof st.auth!=='object') st.auth={session:null,users:[]};
  if(!Array.isArray(st.auth.users)) st.auth.users=[];
  return st.auth;
}
var currentUid=null;
var faceIdProbe=null, faceIdOK=false, faceIdRepainted=false, credApiFake=null;
var TMP_KEY='hub_auth_tmp';

/* ================= phone country codes (public dial data) ================= */
var DIAL={NP:'977',IN:'91',US:'1',ES:'34',GB:'44',CA:'1',AU:'61',DE:'49',FR:'33',IT:'39',PT:'351',NL:'31',BE:'32',CH:'41',AT:'43',SE:'46',NO:'47',DK:'45',FI:'358',IE:'353',JP:'81',KR:'82',CN:'86',SG:'65',MY:'60',TH:'66',ID:'62',PH:'63',VN:'84',BD:'880',PK:'92',LK:'94',BT:'975',MM:'95',AE:'971',SA:'966',QA:'974',KW:'965',OM:'968',BH:'973',MX:'52',BR:'55',AR:'54',CO:'57',CL:'56',PE:'51',NG:'234',ZA:'27',KE:'254',EG:'20',NZ:'64',TR:'90',RU:'7',UA:'380',PL:'48'};
function defaultIso(){ var g=''; try{ g=HUB.i18n.getCountry()||HUB.i18n.guessCountry(); }catch(e){} return DIAL[g]?g:'US'; }
function ccOptions(selIso){
  var lang='en'; try{ lang=HUB.i18n.getLang(); }catch(e){}
  /* compact flag + dial code (WhatsApp-style): full names live in the dropdown;
     keeps the select narrow so a long country name can never truncate mid-word */
  return HUB.i18n.COUNTRIES.filter(function(c){ return !!DIAL[c.c]; }).map(function(c){
    return '<option value="'+c.c+'"'+(c.c===selIso?' selected':'')+'>'+c.f+' +'+DIAL[c.c]+'</option>';
  }).join('');
}
function toE164(iso,num){
  var digits=String(num||'').replace(/\D/g,'');
  return {e164:'+'+DIAL[iso]+digits, digits:digits};
}

/* ================= users & session (local session layer) ================= */
function userById(id){ var u=ag().users; for(var i=0;i<u.length;i++) if(u[i].id===id) return u[i]; return null; }
function currentUser(){ return currentUid?userById(currentUid):null; }
function syncProfile(u){
  try{
    var p=HUB.store.state.profile;
    if(p){ if(u.name) p.name=u.name; if(u.campus) p.campus=u.campus; }
    HUB.store.save();
  }catch(e){}
}
function repaintMe(){
  try{ var el=document.getElementById('view-me'); if(el&&HUB.views&&HUB.views.me) HUB.views.me.render(el); }catch(e){}
  try{ var lb=document.getElementById('logoutBtn'); if(lb) lb.hidden=!currentUser(); }catch(e){}
}
function clearSession(){
  var a=ag(); a.session=null; currentUid=null;
  try{ HUB.store.save(); }catch(e){}
  try{ sessionStorage.removeItem(TMP_KEY); }catch(e){}
}
function signIn(u,remember){
  var a=ag(); currentUid=u.id;
  /* Ensure the user exists in the users array for userById/currentUser. */
  var found=false;
  for(var i=0;i<a.users.length;i++){ if(a.users[i].id===u.id){ a.users[i]=u; found=true; break; } }
  if(!found) a.users.push(u);
  var sess={uid:u.id,at:Date.now(),remember:!!remember};
  if(remember){ a.session=sess; try{ sessionStorage.removeItem(TMP_KEY); }catch(e){} }
  else{ a.session=null; try{ sessionStorage.setItem(TMP_KEY,JSON.stringify(sess)); }catch(e){} }
  try{ HUB.store.save(); }catch(e){}
  syncProfile(u);
  repaintMe();
  /* Pull the account's degree progress from the backend so the tracked plan
     and completed courses follow the user across devices/logins. Silent and
     best-effort: local data is never wiped by this. */
  try{ if(window.HUB&&HUB.degree&&HUB.degree.pullFromCloud) HUB.degree.pullFromCloud(); }catch(e){}
}
function doSignOut(){ clearSession(); repaintMe(); try{ if(fbAuth) fbAuth.signOut(); }catch(e){} openLogin(); }
/* signOut plays the logout cinematic first; the real sign-out runs when it
   finishes (HUB.logout calls back into _doSignOut). No toast — the cinematic
   is the confirmation, and a toast would land behind the login overlay. */
function signOut(){
  if(HUB.logout&&HUB.logout.play){ HUB.logout.play(); return; }
  doSignOut();
}
function restore(){
  ag();
  var sess=ag().session||null;
  if(!sess){ try{ var raw=sessionStorage.getItem(TMP_KEY); if(raw) sess=JSON.parse(raw); }catch(e){ sess=null; } }
  if(sess&&sess.uid&&userById(sess.uid)){ currentUid=sess.uid; }
  else if(sess){ clearSession(); }
  repaintMe(); /* syncs the appbar logout button for remembered sessions */
  /* warm the Face ID probe so the ME card / login button can render it */
  faceIdAvailable().then(function(ok){ if(ok&&!faceIdRepainted){ faceIdRepainted=true; repaintMe(); } }).catch(function(){});
}

/* ================= Face ID (WebAuthn, honest) ================= */
function credApi(){ return credApiFake||((typeof navigator!=='undefined'&&navigator.credentials)||null); }
function randBytes(n){
  var b=new Uint8Array(n), i;
  try{ (window.crypto||{}).getRandomValues(b); }
  catch(e){ for(i=0;i<n;i++) b[i]=Math.floor(Math.random()*256); }
  return b.buffer;
}
function b64enc(buf){
  var bytes=new Uint8Array(buf), s='', i;
  for(i=0;i<bytes.length;i++) s+=String.fromCharCode(bytes[i]);
  return btoa(s).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}
function b64dec(s){
  s=String(s).replace(/-/g,'+').replace(/_/g,'/');
  while(s.length%4) s+='=';
  var b=atob(s), u=new Uint8Array(b.length), i;
  for(i=0;i<b.length;i++) u[i]=b.charCodeAt(i);
  return u.buffer;
}
function faceIdAvailable(){
  if(!faceIdProbe){
    faceIdProbe=Promise.resolve().then(function(){
      try{
        /* QA seam: an injected fake may expose its own availability check */
        if(credApiFake&&typeof credApiFake.isUserVerifyingPlatformAuthenticatorAvailable==='function'){
          return credApiFake.isUserVerifyingPlatformAuthenticatorAvailable().then(function(v){ faceIdOK=!!v; return faceIdOK; });
        }
        if(typeof window==='undefined'||!window.PublicKeyCredential) return false;
        return window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable().then(function(v){ faceIdOK=!!v; return faceIdOK; });
      }catch(e){ faceIdOK=false; return false; }
    }).catch(function(){ faceIdOK=false; return false; });
  }
  return faceIdProbe;
}
function faceCredUser(){ var a=ag(); return a.faceIdUid?userById(a.faceIdUid):null; }
function hasStoredFaceCred(){ var u=faceCredUser(); return !!(u&&u.faceId&&u.faceId.credId); }
function enrollFaceId(u){
  var api=credApi();
  if(!u||!api||typeof api.create!=='function'){ ui.toast(t('auth.faceIdNA')); return Promise.resolve(false); }
  var uname=u.email||u.phoneE164||u.id;
  return Promise.resolve().then(function(){
    return api.create({publicKey:{
      challenge:randBytes(32),
      rp:{name:'Onaro'},
      user:{id:randBytes(16),name:uname,displayName:u.name||uname},
      pubKeyCredParams:[{type:'public-key',alg:-7},{type:'public-key',alg:-257}],
      authenticatorSelection:{authenticatorAttachment:'platform',userVerification:'required',residentKey:'preferred'},
      timeout:60000
    }});
  }).then(function(cred){
    if(!cred||!cred.rawId) throw new Error('no-credential');
    u.faceId={credId:b64enc(cred.rawId)};
    ag().faceIdUid=u.id;
    try{ HUB.store.save(); }catch(e){}
    ui.toast(t('auth.faceIdDone'));
    repaintMe();
    return true;
  }).catch(function(){ ui.toast(t('auth.faceIdNA')); return false; });
}
function loginWithFaceId(){
  var u=faceCredUser();
  var api=credApi();
  if(!u||!u.faceId||!u.faceId.credId||!api||typeof api.get!=='function'){ ui.toast(t('auth.faceIdNA')); return; }
  Promise.resolve().then(function(){
    return api.get({publicKey:{
      challenge:randBytes(32),
      allowCredentials:[{id:b64dec(u.faceId.credId),type:'public-key'}],
      userVerification:'required',
      timeout:60000
    }});
  }).then(function(assertion){
    if(!assertion) throw new Error('no-assertion');
    signIn(u,true);
    successClose();
    ui.toast(t('auth.signedInAs',{name:u.name}));
  }).catch(function(){ ui.toast(t('auth.faceIdNA')); });
}

/* ================= overlay shell ================= */
var rootEl=null, pageEl=null, curView=null, curStep=0, backDir=false;
function ensureRoot(){
  if(rootEl) return;
  rootEl=document.createElement('div');
  rootEl.className='authroot'; rootEl.id='authRoot'; rootEl.hidden=true;
  rootEl.innerHTML='<div class="auth-bg" aria-hidden="true"></div><canvas class="auth-planet" id="authPlanet" aria-hidden="true"></canvas><div class="auth-scrim" aria-hidden="true"></div>'
    +'<div class="auth-motes" aria-hidden="true">'+motesHTML()+'</div>'
    +'<div class="authpage" id="authPage" role="dialog" aria-modal="true"></div>';
  document.body.appendChild(rootEl);
  pageEl=rootEl.querySelector('#authPage');
}
function motesHTML(){
  /* deterministic sparkles rising like the splash beam motes — transform-only */
  var h='', i;
  var xs=[8,22,35,47,58,70,82,92], ds=[6.2,8.1,7.3,9.4,6.8,8.8,7.7,9.9],
      dls=[0,1.4,2.8,.7,2.1,3.5,1.1,2.5], sz=[5,7,4,6,8,5,7,4], sx=[-14,10,-8,16,-12,8,-16,12];
  for(i=0;i<8;i++) h+='<i style="left:'+xs[i]+'%;width:'+sz[i]+'px;height:'+sz[i]+'px;--d:'+ds[i]+'s;--dl:'+dls[i]+'s;--sx:'+sx[i]+'px"></i>';
  return h;
}
function open(view,step){
  ensureRoot();
  /* a celebration timer from a previous success must never hide a fresh view */
  if(celebrateTimer){ clearTimeout(celebrateTimer); celebrateTimer=null; }
  curView=view; curStep=step||0; backDir=false;
  document.body.classList.add('auth-open');
  rootEl.hidden=false;
  rootEl.classList.remove('auth-leaving');
  render();
  try{ if(HUB.authplanet) HUB.authplanet.start(); }catch(e){}
  try{ var f=pageEl.querySelector('input:not([type=hidden])')||pageEl.querySelector('select'); if(f) f.focus({preventScroll:true}); }catch(e){}
}
function openLogin(){ open('login',0); }
function openSignup(){ suReset(); open('signup',1); }
/* Front door: after the splash (and any onboarding sheet) is gone, if nobody
   is signed in, open the login screen automatically so the auth experience is
   actually seen. Returns true when the gate opened the door. */
function gate(){
  if(curView) return true; /* already showing a view — gate satisfied */
  /* open as the splash BEGINS fading (not after removal): the splash lifts
     straight into the login, so the Home tab never flashes through. */
  var sp=document.getElementById('splash');
  if(sp&&!sp.classList.contains('splash-out')) return false;
  var sh=document.getElementById('sheetHost');
  if(sh&&!sh.hidden) return false; /* onboarding still up — wait */
  if(currentUser()) return false;
  openLogin(); return true;
}
function close(){
  if(rootEl) rootEl.hidden=true;
  document.body.classList.remove('auth-open');
  try{ if(HUB.authplanet) HUB.authplanet.stop(); }catch(e){}
  curView=null;
}
/* Escape: this listener registered at parse time, before app.js's global
   handler (DOMContentLoaded), so it runs first. Topmost layer wins: a sheet
   above the auth overlay (campus picker) closes first, else the overlay.
   stopImmediatePropagation keeps the global handler from double-closing. */
document.addEventListener('keydown',function(e){
  if(e.key!=='Escape') return;
  var r=document.getElementById('authRoot');
  if(!r||r.hidden) return;
  var sh=document.getElementById('sheetHost');
  if(sh&&!sh.hidden){ try{ ui.closeSheet(); }catch(err){} e.stopImmediatePropagation(); return; }
  e.stopImmediatePropagation();
  close();
});

/* ================= render dispatch ================= */
function render(){
  if(!pageEl) return;
  var html='';
  if(curView==='login') html=loginHTML();
  else if(curView==='signup') html=(curStep===1?su1HTML():su3HTML());
  else if(curView==='enroll') html=enrollHTML();
  pageEl.innerHTML='<div class="auth-step'+(backDir?' back':'')+'">'+html+'</div>';
  playEnter();
  if(curView==='login') wireLogin();
  else if(curView==='signup'){ if(curStep===1) wireSu1(); else wireSu3(); }
  else if(curView==='enroll') wireEnroll();
}
function goStep(n,back){ curStep=n; backDir=!!back; render(); }
/* Entrance choreography trigger: drop .auth-enter, assign 70ms stagger
   offsets (--st) in DOM order (brand, title, fields, CTA), then re-add the
   class after paint via double-rAF so every render replays the 3D card rise
   + staggered entrances. */
function playEnter(){
  if(!pageEl) return;
  pageEl.classList.remove('auth-enter');
  try{
    var ts=pageEl.querySelectorAll('.auth-brand,.auth-card .auth-title,.auth-card .field,.auth-card .auth-cta');
    for(var i=0;i<ts.length;i++) ts[i].style.setProperty('--st',(i*70)+'ms');
  }catch(e){}
  requestAnimationFrame(function(){
    requestAnimationFrame(function(){ if(pageEl) pageEl.classList.add('auth-enter'); });
  });
}
/* Success beat: card pop + volt flash, then the overlay fades out.
   Total added delay ~360ms — under the 450ms budget from the lingering-dialog
   fix (d63220e). Reduced motion skips the beat and dismisses immediately. */
var celebrateTimer=null;
function successClose(){
  var reduced=false;
  try{ reduced=!!(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches); }catch(e){}
  if(reduced){ close(); return; }
  try{
    var card=pageEl?pageEl.querySelector('.auth-card'):null;
    if(card) card.classList.add('auth-success');
    if(rootEl) rootEl.classList.add('auth-leaving');
  }catch(e){}
  if(celebrateTimer) clearTimeout(celebrateTimer);
  celebrateTimer=setTimeout(function(){ celebrateTimer=null; close(); },360);
}
function errShow(id,msg){
  var p=document.getElementById(id);
  if(!p) return;
  p.textContent=msg; p.hidden=false;
  p.classList.remove('auth-err-pop'); void p.offsetWidth; p.classList.add('auth-err-pop');
}
function brandHTML(){
  var mark='';
  try{ mark=(HUB.icons&&HUB.icons.logoMark)?HUB.icons.logoMark('H'):''; }catch(e){}
  return '<div class="auth-brand"><span class="auth-mark"><span class="auth-markclip">'+mark+'</span></span><span><span class="auth-brandname">Onaro</span>'
    +'<span class="auth-brandsub">'+esc(t('app.brandSub'))+'</span></span></div>';
}
function stepDots(n,total){
  total=total||3;
  var h='<div class="auth-dots" aria-hidden="true">';
  for(var i=1;i<=total;i++) h+='<i class="'+(i===n?'on':(i<n?'done':''))+'"></i>';
  return h+'</div>';
}

/* ================= LOGIN (Firebase email/password) ================= */
function loginHTML(){
  return brandHTML()
  +'<div class="card auth-card"><div class="auth-gloss" aria-hidden="true"></div>'
  +'<h1 class="auth-title">'+esc(t('auth.loginTitle'))+'</h1>'
  +'<p class="auth-sub">'+esc(t('auth.realNote'))+'</p>'
  +'<div class="field"><label for="aId">'+esc(t('auth.emailLabel'))+'</label>'
  +'<input class="input" id="aId" type="email" autocomplete="username" placeholder="'+esc(t('auth.emailPh'))+'"></div>'
  +'<div class="field"><label for="aPw">'+esc(t('auth.pwLabel'))+'</label>'
  +'<div class="auth-pwrow"><input class="input" id="aPw" type="password" autocomplete="current-password" placeholder="'+esc(t('auth.pwPh'))+'">'
  +'<button type="button" class="btn btn-line btn-sm auth-showpw" id="aShowPw">'+esc(t('auth.showPw'))+'</button></div></div>'
  +'<p class="auth-err" id="aErr" role="alert" hidden></p>'
  +'<div class="auth-remrow"><div class="toggle on" id="aRemember" role="switch" aria-checked="true" tabindex="0" aria-label="'+esc(t('auth.remember'))+'"></div>'
  +'<div><div class="auth-rt">'+esc(t('auth.remember'))+'</div><div class="auth-rsub">'+esc(t('auth.rememberSub'))+'</div></div></div>'
  +'<button class="btn btn-primary btn-block auth-cta" id="aLogin">'+esc(t('auth.loginBtn'))+'</button>'
  +'<div id="aFaceWrap" hidden><button class="btn btn-line btn-block auth-face" id="aFace">🪪 '+esc(t('auth.faceIdBtn'))+'</button></div>'
 +'<p class="auth-note" id="aFaceNote" hidden></p>'
  +'<div class="auth-links"><button class="linklike" id="aForgot">'+esc(t('auth.forgotPw'))+'</button></div>'
  +'<p class="auth-switch"><button class="linklike" id="aToSignup">'+esc(t('auth.toSignup'))+'</button></p>'
  +'</div>';
}
/* Complete a Firebase-authenticated session: exchange the ID token with the
   backend, build the local profile. The auth overlay is closed by the caller
   BEFORE this runs (dismiss-first) — this function never gates UI on network. */
function finishFirebaseLogin(fbUser, remember, extra){
  return fbUser.getIdToken().then(function(idToken){
    return HUB.api.authFirebase(idToken,
      (extra&&extra.phone)||'', (extra&&extra.country)||'',
      (extra&&extra.name)||fbUser.displayName||'');
  }).then(function(j){
    var u={
      id:j.user.id,
      name:j.user.display_name||j.user.name||(extra&&extra.name)||fbUser.displayName||'',
      email:j.user.email||fbUser.email||'',
      phoneE164:j.user.phone_e164||'',
      backendId:j.user.id,
      faceId:null,
      createdAt:Date.now()
    };
    signIn(u,remember);
    ui.toast(t('auth.signedInAs',{name:u.name||u.email}));
  });
}
function wireLogin(){
  var idEl=document.getElementById('aId'), pwEl=document.getElementById('aPw');
  var showBtn=document.getElementById('aShowPw');
  showBtn.onclick=function(){
    var show=pwEl.type==='password';
    pwEl.type=show?'text':'password';
    showBtn.textContent=t(show?'auth.hidePw':'auth.showPw');
    pwEl.focus();
  };
  var rem=document.getElementById('aRemember');
  var flip=function(){
    var on=!rem.classList.contains('on');
    rem.classList.toggle('on',on); rem.setAttribute('aria-checked',String(on));
  };
  rem.onclick=flip;
  rem.onkeydown=function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); flip(); } };
  var busy=false;
  var doLogin=function(){
    if(busy) return;
    var email=idEl.value.trim(), pw=pwEl.value;
    if(!EMAIL_RE.test(email)){ errShow('aErr',t('auth.errBadEmail')); return; }
    if(!pw){ errShow('aErr',t('auth.errNoPw')); return; }
    if(!(window.HUB&&HUB.api&&HUB.api.on())){ errShow('aErr',t('auth.errNeedOnline')); return; }
    busy=true;
    var btn=document.getElementById('aLogin');
    var remember=rem.classList.contains('on');
    btn.classList.add('is-busy'); btn.setAttribute('aria-disabled','true');
    btn.innerHTML='<span class="auth-spin" aria-hidden="true"></span>';
    var done=function(ok){
      busy=false;
      if(!ok&&btn){ btn.classList.remove('is-busy'); btn.removeAttribute('aria-disabled'); btn.textContent=t('auth.loginBtn'); }
    };
    firebaseReady().then(function(fa){
      return fa.setPersistence(remember?firebase.auth.Auth.Persistence.LOCAL:firebase.auth.Auth.Persistence.SESSION)
        .then(function(){ return fa.signInWithEmailAndPassword(email,pw); });
    }).then(function(cred){
      var user=cred.user;
      /* Force fresh token to bypass cached emailVerified state. */
      return user.getIdToken(true).then(function(){ return user.reload(); }).then(function(){ return user; });
    }).then(function(user){
      if(!user.emailVerified){
        /* Firebase account exists but email not verified yet — send them to
           the check-email screen (same as post-signup). */
        done(true);
        suReset();
        su.isSignup=false;
        su.firebaseUser=user;
        su.email=user.email||email;
        curView='signup'; goStep(3,false);
        return;
      }
      /* Dismiss-first: Firebase auth succeeded — play the quick success beat
         (pop + volt flash, ~360ms, under the 450ms budget), then close so the
         user sees Home; the backend handshake runs in the background. */
      successClose();
      done(true);
      finishFirebaseLogin(user, remember).catch(function(e){
        try{ ui.toast(t('auth.errBackend')||'Sign-in sync failed — please retry.'); }catch(e2){}
      });
      return;
    }).catch(function(e){
      done(false);
      errShow('aErr', firebaseErrMsg(e));
    });
  };
  document.getElementById('aLogin').onclick=doLogin;
  pwEl.onkeydown=function(e){ if(e.key==='Enter'){ e.preventDefault(); doLogin(); } };
  idEl.onkeydown=function(e){ if(e.key==='Enter'){ e.preventDefault(); doLogin(); } };
  /* Face ID surface: button when a stored credential exists on a capable
     device, otherwise an honest note when the device can't do it. */
  faceIdAvailable().then(function(ok){
    if(curView!=='login') return;
    var fw=document.getElementById('aFaceWrap'), fn=document.getElementById('aFaceNote');
    if(ok&&hasStoredFaceCred()){ if(fw) fw.hidden=false; }
    else if(!ok&&fn){ fn.textContent='🪪 '+t('auth.faceIdNA'); fn.hidden=false; }
  }).catch(function(){});
  document.getElementById('aFace').onclick=function(){ loginWithFaceId(); };
  /* Forgot password: real Firebase reset email. */
  document.getElementById('aForgot').onclick=function(){
    var email=idEl.value.trim();
    if(!EMAIL_RE.test(email)){ errShow('aErr',t('auth.errBadEmail')); return; }
    if(!(window.HUB&&HUB.api&&HUB.api.on())){ errShow('aErr',t('auth.errNeedOnline')); return; }
    firebaseReady().then(function(fa){ return fa.sendPasswordResetEmail(email); })
      .then(function(){ ui.toast(t('auth.resetSent')); })
      .catch(function(e){ errShow('aErr', firebaseErrMsg(e)); });
  };
  document.getElementById('aToSignup').onclick=function(){ suReset(); curView='signup'; goStep(1,false); };
}

/* ================= SIGNUP (Firebase) =================
   Step 1: details form (name, email, phone, password, campus).
   Step 2 (curStep 3, keeps the old numbering): "check your email" screen —
   Firebase sends the verification link; "I've verified" reloads the user,
   checks emailVerified, then exchanges the ID token with the backend. */
var su=null;
function suReset(){ su={name:'',email:'',cc:defaultIso(),num:'',pw:'',pw2:'',campusRec:null,phoneE164:'',firebaseUser:null,isSignup:true}; }
function stashSu1(){
  var g=function(id){ var el=document.getElementById(id); return el?el.value:''; };
  su.name=g('suName'); su.email=g('suEmail'); su.cc=g('suCC')||su.cc; su.num=g('suNum'); su.pw=g('suPw'); su.pw2=g('suPw2');
}
function pwScore(pw){
  var classes=0;
  if(/[a-z]/.test(pw)) classes++;
  if(/[A-Z]/.test(pw)) classes++;
  if(/[0-9]/.test(pw)) classes++;
  if(/[^a-zA-Z0-9]/.test(pw)) classes++;
  if(pw.length>=12&&classes>=3) return 2;
  if(pw.length>=8&&classes>=2) return 1;
  return 0;
}
function pwHintHTML(){
  var s=pwScore(su.pw||'');
  var cls=s===2?'strong':(s===1?'ok':'weak');
  var key=s===2?'auth.pwStrong':(s===1?'auth.pwOk':'auth.pwWeak');
  return '<p class="auth-hint '+cls+'" id="suPwHint">'+esc(t(key))+' · '+esc(t('auth.pwHint'))+'</p>';
}
function su1HTML(){
  return brandHTML()
  +'<div class="card auth-card with-back"><div class="auth-gloss" aria-hidden="true"></div>'
  +'<button class="auth-back" id="suBack1" aria-label="'+esc(t('auth.back'))+'">‹</button>'
  +'<p class="auth-steps">'+esc(t('auth.stepOf2',{a:1}))+'</p>'+stepDots(1,2)
  +'<h1 class="auth-title">'+esc(t('auth.signupTitle'))+'</h1>'
  +'<p class="auth-sub">'+esc(t('auth.realNote'))+'</p>'
  +'<div class="field"><label for="suName">'+esc(t('auth.nameLabel'))+'</label>'
  +'<input class="input" id="suName" autocomplete="name" placeholder="'+esc(t('auth.namePh'))+'" value="'+esc(su.name)+'"></div>'
  +'<div class="field"><label for="suEmail">'+esc(t('auth.emailLabel'))+'</label>'
  +'<input class="input" id="suEmail" type="email" autocomplete="email" placeholder="'+esc(t('auth.emailPh'))+'" value="'+esc(su.email)+'"></div>'
  +'<div class="field"><label>'+esc(t('auth.phoneLabel'))+'</label><div class="auth-phonerow">'
  +'<select class="input auth-cc" id="suCC" aria-label="'+esc(t('auth.ccLabel'))+'">'+ccOptions(su.cc)+'</select>'
  +'<input class="input" id="suNum" inputmode="tel" autocomplete="tel" placeholder="'+esc(t('auth.phonePh'))+'" value="'+esc(su.num)+'"></div></div>'
  +'<div class="field"><label for="suPw">'+esc(t('auth.pwLabel'))+'</label>'
  +'<input class="input" id="suPw" type="password" autocomplete="new-password" placeholder="'+esc(t('auth.pwPh'))+'" value="'+esc(su.pw)+'">'
  +pwHintHTML()+'</div>'
  +'<div class="field"><label for="suPw2">'+esc(t('auth.pwConfirm'))+'</label>'
  +'<input class="input" id="suPw2" type="password" autocomplete="new-password" value="'+esc(su.pw2)+'"></div>'
  +'<div class="field"><label>'+esc(t('auth.campusLabel'))+'</label>'
  +'<button type="button" class="input auth-campusbtn" id="suCampus"><span id="suCampusLabel">'+(su.campusRec?esc(su.campusRec.name):esc(t('auth.chooseCampus')))+'</span><span aria-hidden="true">›</span></button></div>'
  +'<p class="auth-err" id="suErr1" role="alert" hidden></p>'
  +'<button class="btn btn-primary btn-block auth-cta" id="suNext1">'+esc(t('auth.signupBtn'))+'</button>'
  +'<p class="auth-switch"><button class="linklike" id="suToLogin">'+esc(t('auth.toLogin'))+'</button></p>'
  +'</div>';
}
function wireSu1(){
  var bind=function(id,fn){ var el=document.getElementById(id); if(el) el.oninput=function(){ stashSu1(); if(fn) fn(); }; };
  bind('suName'); bind('suEmail'); bind('suNum'); bind('suPw2');
  var pwEl=document.getElementById('suPw');
  if(pwEl) pwEl.oninput=function(){
    stashSu1();
    var h=document.getElementById('suPwHint');
    if(h){ var tmp=document.createElement('div'); tmp.innerHTML=pwHintHTML(); h.replaceWith(tmp.firstChild); }
  };
  var ccEl=document.getElementById('suCC');
  if(ccEl) ccEl.onchange=function(){ stashSu1(); };
  document.getElementById('suCampus').onclick=function(){
    stashSu1();
    ui.openInstitutionPicker({mode:'student',onPick:function(rec){ su.campusRec=rec; goStep(1,false); }});
  };
  document.getElementById('suBack1').onclick=function(){ curView='login'; goStep(0,true); };
  document.getElementById('suToLogin').onclick=function(){ curView='login'; goStep(0,true); };
  document.getElementById('suNext1').onclick=function(){
    stashSu1();
    su.name=su.name.trim(); su.email=su.email.trim();
    if(!su.name){ errShow('suErr1',t('auth.errName')); return; }
    if(!EMAIL_RE.test(su.email)){ errShow('suErr1',t('auth.errBadEmail')); return; }
    var ph=toE164(su.cc,su.num);
    if(ph.digits.length<7||ph.digits.length>15){ errShow('suErr1',t('auth.errBadPhone')); return; }
    if(su.pw.length<8){ errShow('suErr1',t('auth.errPwShort')); return; }
    if(su.pw!==su.pw2){ errShow('suErr1',t('auth.errPwMismatch')); return; }
    if(!su.campusRec){ errShow('suErr1',t('auth.errNoCampus')); return; }
    su.phoneE164=ph.e164;
    /* Firebase signup: create the account, send the verification email,
       then show the "check your email" screen. */
    if(!(window.HUB&&HUB.api&&HUB.api.on())){
      errShow('suErr1', t('auth.errNeedOnline'));
      return;
    }
    var btn=document.getElementById('suNext1');
    if(btn) btn.disabled=true;
    firebaseReady().then(function(fa){
      return fa.createUserWithEmailAndPassword(su.email, su.pw);
    }).then(function(cred){
      var user=cred.user;
      su.firebaseUser=user; su.isSignup=true;
      var upd=(su.name&&user.updateProfile)
        ? user.updateProfile({displayName:su.name}).catch(function(){})
        : Promise.resolve();
      return upd.then(function(){ return user; });
    }).then(function(user){
      return user.sendEmailVerification().then(function(){ return user; });
    }).then(function(){
      su.pw=''; su.pw2='';
      if(btn) btn.disabled=false;
      goStep(3,false);
    }).catch(function(e){
      if(btn) btn.disabled=false;
      errShow('suErr1', firebaseErrMsg(e));
    });
  };
}
function maskEmail(em){
  var parts=String(em||'').split('@');
  if(parts.length<2) return em;
  var l=parts[0];
  return (l.charAt(0)||'')+'•••@'+parts[1];
}
/* ---- step 2: "check your email" (Firebase sends the verification link) ---- */
function su3HTML(){
  var em=maskEmail(su.email||'');
  return brandHTML()
  +'<div class="card auth-card with-back"><div class="auth-gloss" aria-hidden="true"></div>'
  +'<button class="auth-back" id="suBack3" aria-label="'+esc(t('auth.back'))+'">‹</button>'
  +'<p class="auth-steps">'+esc(t('auth.stepOf2',{a:2}))+'</p>'+stepDots(2,2)
  +'<div class="auth-mail3d" aria-hidden="true">'
  +'<div class="mail3d-env"><div class="mail3d-flap"></div><div class="mail3d-body"></div>'
  +'<div class="mail3d-spark s1"></div><div class="mail3d-spark s2"></div><div class="mail3d-spark s3"></div></div>'
  +'</div>'
  +'<h1 class="auth-title">'+esc(t('auth.checkEmailTitle'))+'</h1>'
  +'<p class="auth-sub">'+esc(t('auth.checkEmailNote',{email:em}))+'</p>'
  +'<div id="suPhoneWrap" hidden><div class="field"><label>'+esc(t('auth.phoneLabel'))+'</label><div class="auth-phonerow">'
  +'<select class="input auth-cc" id="suCC2" aria-label="'+esc(t('auth.ccLabel'))+'">'+ccOptions(su.cc)+'</select>'
  +'<input class="input" id="suNum2" inputmode="tel" autocomplete="tel" placeholder="'+esc(t('auth.phonePh'))+'"></div></div></div>'
  +'<p class="auth-err" id="suErr3" role="alert" hidden></p>'
  +'<button class="btn btn-primary btn-block auth-cta" id="suVerified">'+esc(t('auth.iveVerified'))+'</button>'
  +'<div class="auth-links"><button class="linklike" id="suResendEmail">'+esc(t('auth.resendEmail'))+'</button></div>'
  +'</div>';
}
function wireSu3(){
  document.getElementById('suBack3').onclick=function(){ goStep(1,true); };
  /* Resend the Firebase verification email. */
  document.getElementById('suResendEmail').onclick=function(){
    var u=su.firebaseUser;
    if(!u){ errShow('suErr3',t('auth.errLoginFailed')); return; }
    u.sendEmailVerification()
      .then(function(){ ui.toast(t('auth.emailResent')); })
      .catch(function(e){ errShow('suErr3', firebaseErrMsg(e)); });
  };
  /* "I've verified": reload the Firebase user, require emailVerified, then
     exchange the ID token with the backend. If the backend needs a phone
     (login-then-verify path where we have none), reveal the phone row. */
  document.getElementById('suVerified').onclick=function(){
    var u=su.firebaseUser;
    if(!u){ errShow('suErr3',t('auth.errLoginFailed')); return; }
    var btn=document.getElementById('suVerified');
    btn.disabled=true;
    /* Force a fresh ID token first — this bypasses Firebase's cached user
       state and ensures emailVerified reflects the server truth. */
    u.getIdToken(true).then(function(){
      return u.reload();
    }).then(function(){
      if(!u.emailVerified){
        btn.disabled=false;
        errShow('suErr3',t('auth.errNotVerified'));
        return null;
      }
      var phone=su.phoneE164||'', cc=su.cc||defaultIso();
      var pw=document.getElementById('suPhoneWrap');
      if(!phone&&pw&&!pw.hidden){
        var ccEl=document.getElementById('suCC2'), numEl=document.getElementById('suNum2');
        var ph=toE164(ccEl?ccEl.value:cc,(numEl&&numEl.value)||'');
        if(ph.digits.length<7||ph.digits.length>15){
          btn.disabled=false;
          errShow('suErr3',t('auth.errBadPhone'));
          return null;
        }
        phone=ph.e164; cc=ccEl.value; su.phoneE164=phone; su.cc=cc;
      }
      return u.getIdToken().then(function(idToken){
        return HUB.api.authFirebase(idToken, phone, cc, su.name||'');
      });
    }).then(function(j){
      if(!j) return;
      btn.disabled=false;
      completeBackendSignup(j.user);
    }).catch(function(e){
      btn.disabled=false;
      var msg=(e&&e.message)||'';
      if(msg.indexOf('phone required')>=0){
        var pw2=document.getElementById('suPhoneWrap');
        if(pw2) pw2.hidden=false;
        errShow('suErr3',t('auth.phoneNeededSub'));
        return;
      }
      errShow('suErr3', msg||t('auth.errLoginFailed'));
    });
  };
}
function completeBackendSignup(backendUser){
  /* Firebase verification complete + backend token stored by authFirebase.
     Create the local profile from backend user data. Signup path gets the
     welcome + Face ID enroll moment; login-then-verify path just signs in. */
  var u={
    id:backendUser.id||backendUser.user_id,
    name:backendUser.display_name||su.name,
    email:backendUser.email||su.email,
    phoneE164:backendUser.phone_e164||su.phoneE164,
    cc:su.cc,
    campus:su.campusRec?su.campusRec.name:'',
    backendId:backendUser.id||backendUser.user_id,
    faceId:null,
    createdAt:Date.now()
  };
  var wasSignup=!!su.isSignup;
  su.firebaseUser=null; su.pw=''; su.pw2='';
  signIn(u,true);
  if(wasSignup){
    /* New signup: clear profile name/campus so onboarding triggers,
       then run the welcome (language) + onboarding flow like a fresh install. */
    try{
      var p=HUB.store.state.profile;
      if(p){ p.name=''; p.campus=''; }
      HUB.store.save();
    }catch(e){}
    successClose();
    ui.toast(t('auth.welcomeNew',{name:u.name}));
    if(HUB.i18n&&HUB.i18n.ensureWelcome){
      HUB.i18n.ensureWelcome(function(){
        if(HUB.ensureOnboarded) HUB.ensureOnboarded();
      });
    }else if(HUB.ensureOnboarded){
      HUB.ensureOnboarded();
    }
  }else{
    ui.toast(t('auth.signedInAs',{name:u.name||u.email}));
    successClose();
  }
}

/* ================= enroll / welcome moment ================= */
function enrollHTML(){
  var u=currentUser();
  var nm=u?u.name:'';
  return brandHTML()
  +'<div class="card auth-card auth-welcome"><div class="auth-gloss" aria-hidden="true"></div>'
  +'<div class="auth-check" aria-hidden="true"><span class="auth-checkring"></span><span class="auth-checkmark">✓</span></div>'
  +'<h1 class="auth-title">'+esc(t('auth.welcomeNew',{name:nm}))+'</h1>'
  +'<p class="auth-sub">'+esc(t('auth.signedInAs',{name:nm}))+'</p>'
  +'<button class="btn btn-primary btn-block auth-cta" id="enRoll">🪪 '+esc(t('auth.enableFaceId'))+'</button>'
  +'<div class="auth-links"><button class="linklike" id="enSkip">'+esc(t('common.close'))+'</button></div>'
  +'</div>';
}
function wireEnroll(){
  var u=currentUser();
  document.getElementById('enRoll').onclick=function(){
    if(!u){ close(); return; }
    enrollFaceId(u).then(function(ok){ if(ok) successClose(); });
  };
  document.getElementById('enSkip').onclick=function(){ close(); };
  /* the magical moment: a burst of sparkles rises off the checkmark */
  successBurst();
}
/* verification-success sparkle burst: 14 motes rise from the welcome check,
   transform/opacity-only, removed after the animation (frozen under
   prefers-reduced-motion by the global auth rule) */
function successBurst(){
  try{
    if(!pageEl) return;
    var host=pageEl.querySelector('.auth-check');
    if(!host) return;
    var r=host.getBoundingClientRect(), pr=pageEl.getBoundingClientRect();
    var cx=r.left-pr.left+r.width/2+pageEl.scrollLeft, cy=r.top-pr.top+r.height/2+pageEl.scrollTop;
    var colors=['#FFFFFF','#C6F135','#FFE58A'], i, s;
    for(i=0;i<14;i++){
      s=document.createElement('i');
      var sz=(5+Math.random()*7).toFixed(0);
      s.className='auth-bmote';
      s.setAttribute('aria-hidden','true');
      s.style.left=cx+'px'; s.style.top=cy+'px';
      s.style.width=sz+'px'; s.style.height=sz+'px';
      s.style.background=colors[i%3];
      s.style.setProperty('--bx',(Math.random()*170-85).toFixed(0)+'px');
      s.style.setProperty('--bd',(Math.random()*0.18).toFixed(2)+'s');
      pageEl.appendChild(s);
      (function(el){ setTimeout(function(){ if(el.parentNode) el.parentNode.removeChild(el); },1700); })(s);
    }
  }catch(e){}
}

/* ================= ME tab account card ================= */
function accountCardHTML(){
  var u=currentUser();
  var inner='';
  if(!u){
    inner='<div class="auth-acct-row"><div><h2>'+esc(t('auth.accountTitle'))+'</h2>'
      +'<p class="hint">'+esc(t('auth.realNote'))+'</p></div></div>'
      +'<div class="auth-acct-btns"><button class="btn btn-primary" id="acLogin">'+esc(t('auth.loginBtn'))+'</button>'
      +' <button class="btn btn-line" id="acSignup">'+esc(t('auth.signupBtn'))+'</button></div>';
  }else{
    var av='';
    try{ av=esc(ui.initials(u.name||'?')); }catch(e){ av=esc(String(u.name||'?').charAt(0)); }
    inner='<div class="auth-acct-row"><div class="auth-acct-av">'+av+'</div>'
      +'<div class="auth-acct-id"><div class="auth-acct-name">'+esc(u.name)+'</div>'
      +'<div class="auth-acct-sub">'+esc(u.email||u.phoneE164||'')+'</div></div></div>'
      +((faceIdOK&&!u.faceId)?'<button class="btn btn-line btn-block" id="acFace">🪪 '+esc(t('auth.enableFaceId'))+'</button>':'')
      +'<button class="btn btn-line btn-block" id="acLogout" style="margin-top:8px">'+esc(t('auth.logout'))+'</button>';
  }
  return '<div class="card auth-acct">'+inner+'</div>';
}
function wireAccountCard(){
  var l=document.getElementById('acLogin'); if(l) l.onclick=function(){ openLogin(); };
  var s=document.getElementById('acSignup'); if(s) s.onclick=function(){ openSignup(); };
  var o=document.getElementById('acLogout'); if(o) o.onclick=function(){ signOut(); };
  var f=document.getElementById('acFace');
  if(f) f.onclick=function(){ var u=currentUser(); if(u) enrollFaceId(u); };
  faceIdAvailable().then(function(ok){ if(ok&&!faceIdRepainted){ faceIdRepainted=true; repaintMe(); } }).catch(function(){});
}

/* ================= public API ================= */
HUB.auth={
  openLogin:openLogin, openSignup:openSignup, close:close, gate:gate,
  logout:signOut, restore:restore, currentUser:currentUser,
  accountCardHTML:accountCardHTML, wireAccountCard:wireAccountCard,
  faceIdAvailable:faceIdAvailable, enrollFaceId:enrollFaceId,
  _doSignOut:doSignOut,
  _debug:{
    reset:function(){
      var a=ag(); a.users=[]; a.session=null; delete a.faceIdUid;
      currentUid=null; faceIdOK=false; faceIdProbe=null; faceIdRepainted=false;
      try{ HUB.store.save(); }catch(e){}
      try{ sessionStorage.removeItem(TMP_KEY); }catch(e){}
      try{ if(fbAuth) fbAuth.signOut(); }catch(e){}
      repaintMe(); return true;
    },
    users:function(){
      return ag().users.map(function(u){
        return {id:u.id,name:u.name,email:u.email,phoneE164:u.phoneE164,faceId:!!(u.faceId&&u.faceId.credId)};
      });
    },
    lastCode:function(){ return null; }, /* retired with the 6-digit demo codes */
    setCredApi:function(fake){ credApiFake=fake||null; faceIdProbe=null; faceIdOK=false; faceIdRepainted=false; },
    faceIdAvailable:faceIdAvailable
  }
};

/* appbar logout button (static HTML): wire once, set initial visibility.
   repaintMe() keeps it in sync on every auth change. */
try{
  var loBtn=document.getElementById('logoutBtn');
  if(loBtn){
    loBtn.addEventListener('click',function(){ signOut(); });
    loBtn.hidden=!currentUser();
  }
}catch(e){}
})();
