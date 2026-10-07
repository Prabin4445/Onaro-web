/* HUB app shell: tab router, onboarding, global wiring. */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };
HUB.views=HUB.views||{};

function applyTheme(){ document.body.classList.add('dark'); applyGenderTheme(false); }

/* Gender-driven UI theme (2026-09-29): female -> rose pink accent, everyone
   else -> the signature volt green. CSS vars do the heavy lifting (every tab
   follows); JS paints read the live tokens via HUB.theme so canvas/SVG
   accents match too. */
function themeAccent(){
  try{ var v=getComputedStyle(document.body).getPropertyValue('--volt').trim(); return v||'#C6F135'; }
  catch(e){ return '#C6F135'; }
}
function themeRGB(){
  try{ var v=getComputedStyle(document.body).getPropertyValue('--volt-rgb').trim(); return v||'198,241,53'; }
  catch(e){ return '198,241,53'; }
}
function themeRGBA(a){ return 'rgba('+themeRGB()+','+a+')'; }
function genderTheme(){ return (store.state.profile&&store.state.profile.gender)==='female' ? 'rose' : 'volt'; }
function applyGenderTheme(animate){
  var want=genderTheme()==='rose';
  var has=document.body.classList.contains('theme-rose');
  if(want===has){ document.body.classList.toggle('theme-rose',want); return; }
  if(!animate||(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches)){
    document.body.classList.toggle('theme-rose',want); return;
  }
  /* water-flow 3D transition: liquid accent blobs sweep while surfaces cross-fade */
  try{
    var ov=document.createElement('div');
    ov.className='themeflow'; ov.setAttribute('aria-hidden','true');
    ov.innerHTML='<div class="tf-stage"><div class="tf-blob b1"></div><div class="tf-blob b2"></div><div class="tf-blob b3"></div></div><div class="tf-sheen"></div>';
    document.body.appendChild(ov);
    document.body.classList.add('theming');
    requestAnimationFrame(function(){ ov.classList.add('on'); });
    setTimeout(function(){ document.body.classList.toggle('theme-rose',want); },140);
    setTimeout(function(){ ov.classList.remove('on'); },950);
    setTimeout(function(){ if(ov.parentNode) ov.parentNode.removeChild(ov); document.body.classList.remove('theming'); },1350);
  }catch(e){ document.body.classList.toggle('theme-rose',want); }
}
HUB.theme={accent:themeAccent,rgb:themeRGB,rgba:themeRGBA,current:genderTheme,
  apply:function(animate){ applyGenderTheme(animate!==false); }};

function showTab(name){
  /* chatroot overlays (search/pulse/notifications/chat) and bottom sheets are
     mutually exclusive with tabs — a tab switch always clears them so an
     overlay can never cover the newly shown tab. */
  try{ ui.closeSheet(); }catch(e){}
  ['search','pulse','notifications'].forEach(k=>{ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
  try{ if(HUB.chat&&HUB.chat.close) HUB.chat.close(); }catch(e){}
  document.querySelectorAll('#tabbar .tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));
  document.querySelectorAll('.view').forEach(v=>{ v.hidden = v.dataset.view!==name; });
  const el=document.getElementById('view-'+name);
  const view=HUB.views[name];
  if(view&&view.render){ try{ view.render(el); }catch(e){ console.error('render',name,e); el.innerHTML='<div class="empty"><div class="big">😕</div><p>'+t('app.renderError')+'</p></div>'; } }
  const vs=document.getElementById('views'); if(vs) vs.scrollTop=0;
  refreshDots();
}
HUB.showTab=showTab;

/* Launch splash: fade out after boot + first tab render. Minimum 5.0s show so
   the volt loading bar completes its fill; the inline backstop in index.html is
   the hard ~6.0s cap if boot JS ever fails. */
function hideSplash(){
  try{
    var sh=document.getElementById('splash');
    if(!sh||sh.getAttribute('data-gone'))return;
    sh.setAttribute('data-gone','1');
    var waitMs=Math.max(0,5000-(Date.now()-(window.__splashT0||Date.now())));
    setTimeout(function(){
      sh.classList.add('splash-out');
      /* auth front door: if armed (signed-out, no onboarding sheet), open the
         login NOW as the splash begins fading — the splash lifts into the
         login and the Home tab never flashes through. */
      try{ if(window.__gateArmed&&HUB.auth&&HUB.auth.gate) HUB.auth.gate(); }catch(e){}
      setTimeout(function(){ if(sh.parentNode)sh.parentNode.removeChild(sh); window.__splashGone=Date.now(); },650);
    },waitMs);
  }catch(e){}
}
HUB.splashDone=hideSplash;
HUB.paintChrome=paintChrome;
/* Global offline guard: returns true if offline (and shows toast).
   Use at the start of any internet-required action:
   if(HUB.offline.check()) return; */
HUB.offline={
  is:function(){ try{ return typeof navigator!=='undefined'&&navigator.onLine===false; }catch(e){ return false; } },
  check:function(){
    if(this.is()){
      try{
        var msg='📡 ';
        try{ msg+=HUB.i18n.t('common.offline'); }catch(e){ msg+='You are offline — check your connection.'; }
        if(HUB.ui&&HUB.ui.toast) HUB.ui.toast(msg); else alert(msg);
      }catch(e){}
      return true;
    }
    return false;
  }
};

function refreshDots(){
  if(HUB.chat) HUB.chat.refreshDot();
  const nd=document.getElementById('notifDot');
  if(nd&&HUB.notifications){ try{ nd.hidden = !(HUB.notifications.unreadCount()>0); }catch(e){} }
}
HUB.refreshDots=refreshDots;

/* ---------- 2026 chrome: 3D clay tab icons + line-icon headers ---------- */
function paintChrome(){
  if(!HUB.icons) return;
  document.querySelectorAll('#tabbar .tab').forEach(b=>{
    let n=b.dataset.icon, s=b.querySelector('.tab-ico');
    /* gender-aware ME icon: female->girl, other->rainbow, na->ninja, male/unset->boy */
    if(b.dataset.tab==='me'&&HUB.me&&HUB.me.tabIconName) n=HUB.me.tabIconName();
    if(n&&s) s.innerHTML=HUB.icons.icon(n);   /* clay PNGs — PraBin's signature look */
  });
  const hdr={searchBtn:'ic-search',askBtn:'ic-pulse',notifBtn:'ic-bell'};
  Object.keys(hdr).forEach(id=>{
    const b=document.getElementById(id); if(!b) return;
    const dot=b.querySelector('.dot'); // preserved for refreshDots()
    b.innerHTML=HUB.icons.icon(hdr[id])+(dot?dot.outerHTML:'');
  });
  /* profile button: gender-aware ME clay icon, same as the ME tab */
  const pb=document.getElementById('profileBtn');
  if(pb){ let n='nav-me'; try{ if(HUB.me&&HUB.me.tabIconName) n=HUB.me.tabIconName(); }catch(e){} pb.innerHTML=HUB.icons.icon(n); }
  const pi=document.getElementById('askPillIco');
  if(pi) pi.innerHTML=HUB.icons.icon('ask-hub');
}

const ASK_CHIPS=['ask.chip.help','ask.chip.bill','ask.chip.desk','ask.chip.jobs'];

/* Ask Onaro bottom sheet — reuses the ai domain (HUB.ai.answer / bindGotos).
   Quiet global entry: a pill above the tab bar, never a new page. */
function openAskSheet(prefill){
  ui.openSheet(
    '<div class="askhead">'+HUB.icons.icon('ask-hub')+'<h2>'+t('ask.title')+'</h2><span class="badge b-BUY">'+t('honesty.demoAssistant')+'</span></div>'+
    '<p class="sub" style="margin:6px 0 4px">'+t('ask.sub')+'</p>'+
    '<div class="chips askchips">'+ASK_CHIPS.map(c=>'<button class="chip askchip" data-q="'+ui.esc(t(c))+'">'+ui.esc(t(c))+'</button>').join('')+'</div>'+
    '<div class="askbox"><input class="input" id="askSheetInput" placeholder="'+t('ask.ph')+'" value="'+ui.esc(prefill||'')+'"><button class="btn btn-dark btn-sm" id="askSheetSend">'+t('ask.send')+'</button></div>'+
    '<div id="askSheetResults"></div>'
  );
  const input=document.getElementById('askSheetInput'), results=document.getElementById('askSheetResults');
  const askAbout=(q)=>{
    const card=document.createElement('div');
    card.className='card tight'; card.style.marginTop='12px';
    card.innerHTML='<div class="sub" style="margin-bottom:8px">'+t('ask.youAsked')+' <b>'+ui.esc(q)+'</b></div>'+HUB.ai.answer(q);
    HUB.ai.bindGotos(card);
    if(HUB.ai.bindWalk) HUB.ai.bindWalk(card, askAbout);
    results.prepend(card);
    const sc=card.closest('.sheet'); if(sc) sc.scrollTop=0;
  };
  const run=()=>{
    const q=input.value.trim();
    if(!q){ ui.toast(t('ask.typeFirst')); return; }
    askAbout(q);
    input.value='';
  };
  document.getElementById('askSheetSend').onclick=run;
  input.addEventListener('keydown',e=>{ if(e.key==='Enter') run(); });
  document.querySelectorAll('.askchip').forEach(c=>{
    c.onclick=()=>{ input.value=c.dataset.q; input.focus(); };
  });
  if(prefill) input.focus();
}
HUB.askHUB={open:openAskSheet};

function mountAskPill(){
  const pill=document.getElementById('askPill'); if(!pill) return;
  try{ if(sessionStorage.getItem('hub_askpill_off')) return; }catch(e){}
  pill.hidden=false;
  document.getElementById('askPillMain').onclick=()=>openAskSheet('');
  document.getElementById('askPillX').onclick=()=>{
    try{ sessionStorage.setItem('hub_askpill_off','1'); }catch(e){}
    pill.hidden=true;
  };
  /* get out of the way while reading: hide on scroll-down, return on scroll-up/idle.
     The page scrolls on window/body (.views grows with content), so watch both. */
  const views=document.querySelector('.views');
  let lastY=0, idleT=null;
  const curY=function(){ return Math.max(window.scrollY||0, views?views.scrollTop:0); };
  const onScroll=function(){
    const y=curY();
    if(y>lastY+6) pill.classList.add('hide');
    else if(y<lastY-4) pill.classList.remove('hide');
    lastY=y;
    clearTimeout(idleT);
    idleT=setTimeout(()=>pill.classList.remove('hide'),1400);
  };
  if(views) views.addEventListener('scroll',onScroll,{passive:true});
  window.addEventListener('scroll',onScroll,{passive:true});
}

/* ---------- first-run onboarding (Workstream C: Campus → Communities) ----------
   One question — "Are you a student or a community member?" — then a
   community picker. Students pick a campus; everyone else picks a
   neighborhood / apartment complex / city area / workplace community.
   If a choice already exists from a prior run, never force re-onboarding
   (ME keeps a "change community" picker). Local-only, demo-labeled. */
function ensureOnboarded(){
  const p=store.state.profile;
  if(p.name&&p.campus) return;
  let audience=''; // 'student' | 'community'
  let picked=null; // institution picker result {name,lat,lng,iso,sample}
  let typedName=p.name||'';
  let typedGender=p.gender||''; /* survives stepPick re-renders (institution picker) */
  function genderSegHTML(cur){
    const opts=[['male','me.gender.male'],['female','me.gender.female'],['other','me.gender.other'],['na','me.gender.na']];
    return opts.map(o=>'<button type="button" data-g="'+o[0]+'" class="'+(cur===o[0]?'on':'')+'">'+t(o[1])+'</button>').join('');
  }
  function bindGenderSeg(rootId){
    const root=document.getElementById(rootId); if(!root) return;
    root.querySelectorAll('button').forEach(b=>{ b.onclick=()=>{ typedGender=b.dataset.g;
      root.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b)); }; });
  }
  function stepRole(){
    ui.openSheet(
      '<h2>'+t('ob.title')+'</h2><p class="sub" style="margin-bottom:6px">'+t('ob.sub')+'</p>'+
      '<p style="font-weight:800;font-size:16px;margin:14px 0 4px">'+t('ob.roleQ')+'</p>'+
      '<div class="ob-roles">'+
        '<button class="ob-role" id="obStudent"><span class="ob-emoji">🎓</span><span class="ob-t">'+t('ob.student')+'</span><span class="ob-d">'+t('ob.studentD')+'</span></button>'+
        '<button class="ob-role" id="obCommunity"><span class="ob-emoji">🏘️</span><span class="ob-t">'+t('ob.member')+'</span><span class="ob-d">'+t('ob.memberD')+'</span></button>'+
      '</div>'+
      '<p class="hint" style="text-align:center">'+t('ob.demoNote')+'</p>'
    );
    document.getElementById('obStudent').onclick=()=>{audience='student';stepPick();};
    document.getElementById('obCommunity').onclick=()=>{audience='community';stepPick();};
  }
  function stepPick(){
    const isStudent=audience==='student';
    ui.openSheet(
      '<button class="ob-back" id="obBack">'+t('ob.back')+'</button>'+
      '<h2>'+t(isStudent?'ob.pickCampus':'ob.pickCommunity')+'</h2>'+
      '<p class="sub" style="margin-bottom:14px">'+t('ob.pickSub')+'</p>'+
      '<div class="field"><label>'+t('ob.nameLabel')+'</label><input class="input" id="obName" placeholder="'+t('ob.namePh')+'" value="'+ui.esc(typedName)+'"></div>'+
      '<div class="field"><label>'+t('pedit.gender')+'</label><div class="seg" id="obGender" role="radiogroup">'+genderSegHTML(typedGender)+'</div></div>'+
      '<div class="field"><label>'+t(isStudent?'ob.campusLabel':'ob.communityLabel')+'</label>'+
      '<button class="input intl-pickbtn" id="obPickBtn" type="button"><span id="obPickLabel">'+ui.esc(picked?picked.name:t('ob.choose'))+'</span>'+(picked&&picked.sample?ui.sampleBadge(true):'')+'<span aria-hidden="true">›</span></button>'+
      '<p class="hint">'+t('intl.bundledDir')+' · '+t('honesty.sampleCommunities')+'</p></div>'+
      '<button class="btn btn-primary btn-block" id="obGo">'+t('ob.getStarted')+'</button>'
    );
    document.getElementById('obBack').onclick=stepRole;
    document.getElementById('obName').oninput=e=>{ typedName=e.target.value; };
    bindGenderSeg('obGender');
    document.getElementById('obPickBtn').onclick=()=>{
      typedName=document.getElementById('obName').value;
      ui.openInstitutionPicker({mode:audience,onPick:rec=>{ picked=rec; stepPick(); }});
    };
    document.getElementById('obGo').onclick=()=>{
      const name=document.getElementById('obName').value.trim();
      if(!name){ui.toast(t('ob.needName'));return;}
      if(!picked){ui.toast(t(isStudent?'ob.needCampus':'ob.needCommunity'));return;}
      p.name=name;p.campus=picked.name;p.audience=audience;p.campusSample=!!picked.sample;p.campusKind=picked.kind||'';
      if(typedGender) p.gender=typedGender; /* drives the ME tab icon */
      if(!picked.sample&&picked.lat!=null&&picked.lng!=null&&isFinite(picked.lat)&&isFinite(picked.lng)){
        p.campusCoords=[picked.lat,picked.lng];p.campusIso=picked.iso||'';p.campusCity=picked.city||'';
      }else{ delete p.campusCoords; delete p.campusIso; delete p.campusCity; }
      store.save();
      ui.closeSheet();showTab('home');paintChrome();
      /* onboarding done — the auth front door takes it from here */
      try{ if(HUB.auth&&HUB.auth.gate) HUB.auth.gate(); }catch(e){}
      ui.toast(t('ob.welcomeToast',{name:name}));
    };
  }
  stepRole();
}

document.addEventListener('DOMContentLoaded',()=>{
  /* Connectivity monitor: toast when going offline/online */
  try{
    window.addEventListener('offline',function(){
      if(HUB.ui&&HUB.ui.toast) HUB.ui.toast('📡 '+HUB.i18n.t('common.offline'));
    });
    window.addEventListener('online',function(){
      if(HUB.ui&&HUB.ui.toast) HUB.ui.toast('✅ '+HUB.i18n.t('common.online'));
    });
  }catch(e){}
  /* Self-healing: any synchronous init fault shows the branded recovery
     screen instead of a blank page (see js/safeboot.js). */
  try{
  applyTheme();
  /* Planet wordmark: the planet is the O in "Onaro". */
  try{ var bm=document.getElementById('brandMark'); if(bm&&HUB.icons&&HUB.icons.logoMark) bm.innerHTML=HUB.icons.logoMark('H'); }catch(e){}
  /* Splash tagline follows the active locale (falls back to the English
     hardcoded in index.html until i18n is ready). */
  try{ var stag=document.getElementById('splashTag'); if(stag) stag.textContent=t('app.brandSub'); }catch(e){}
  /* Freeze the logo riders for reduced-motion users (SMIL ignores CSS). */
  try{ if(HUB.icons&&HUB.icons.freezeLogos) HUB.icons.freezeLogos(); }catch(e){}
  paintChrome();
  HUB.i18n.applyStatic();
  HUB.i18n.mountChrome();
  mountAskPill();
  /* Prime the selected ringtone at boot: preloads + decodes the audio now so
     an incoming call's first play() starts from cache instead of paying a
     network fetch on its critical path (was ~10s late on iOS). */
  try{ if(HUB.sound&&HUB.sound.primeRingtone) HUB.sound.primeRingtone(); }catch(e){}
  /* Profile badges: start the 60-second qualifying-login tracker at boot. */
  try{ if(HUB.badges&&HUB.badges.start) HUB.badges.start(); }catch(e){}
  /* Auth: restore the persisted session (hub_v1) or the tab-scoped one (sessionStorage). */
  try{ if(HUB.auth&&HUB.auth.restore) HUB.auth.restore(); }catch(e){}
  const tabbar=document.getElementById('tabbar');
  if(tabbar) tabbar.addEventListener('click',e=>{
    const b=e.target.closest('.tab'); if(b) showTab(b.dataset.tab);
  });
  const searchBtn=document.getElementById('searchBtn'); if(searchBtn) searchBtn.onclick=()=>{ if(HUB.search) HUB.search.open(); };
  const askBtn=document.getElementById('askBtn'); if(askBtn) askBtn.onclick=()=>{ if(HUB.askHUB) HUB.askHUB.open(''); };
  const profileBtn=document.getElementById('profileBtn'); if(profileBtn) profileBtn.onclick=()=>HUB.showTab('me');
  const notifBtn=document.getElementById('notifBtn'); if(notifBtn) notifBtn.onclick=()=>{ if(HUB.notifications){ HUB.notifications.open(); setTimeout(refreshDots,600); } };
  document.addEventListener('keydown',e=>{ if(e.key==='Escape'){ if(document.querySelector('.mkzoom')) return; /* lightbox handles its own dismissal */ if(document.querySelector('.callroot:not([hidden])')) return; /* call UI owns Escape while visible */ if(document.querySelector('.incallroot:not([hidden])')) return; /* incoming-call screen owns Escape while visible */ if(document.querySelector('.hpglass:not([hidden])')) return; /* people glass sheet owns Escape while visible */ if(document.querySelector('.authroot:not([hidden])')) return; /* auth overlay owns Escape while visible */ const sh=document.getElementById('sheetHost'); const sheetWasOpen=!!(sh&&!sh.hidden); ui.closeSheet(); /* a sheet above chat closes alone on the first Escape (same layering as group chat); only dismiss chat when no sheet consumed the keypress */ if(!sheetWasOpen&&HUB.chat) HUB.chat.close(); } });
  /* Global sheet close: every [data-close] ✕ button (appointments, horoscope,
     calendar day-notes…) closes the current sheet. One handler, no dead Xs. */
  document.addEventListener('click',e=>{
    if(e.target.closest('[data-close]')){ try{ ui.closeSheet(); }catch(err){} }
  });
  /* Workstream G: warm a lazy-stored language from cache/network before the
     first render so repeat visits apply it instantly (no English flash). */
  }catch(__initErr){ try{ if(HUB.safe) HUB.safe.showRecovery('init fault'); }catch(e){} return; }
  HUB.i18n.bootLocale(function(){
    HUB.i18n.ensureWelcome(function(){ ensureOnboarded(); showTab('home'); hideSplash();
      try{ if(HUB.safe) HUB.safe.booted(); }catch(e){} /* boot watchdog: all clear */
      /* Arm the auth front door: signed-out + no onboarding sheet showing ->
         the login opens the moment the splash begins fading (see hideSplash).
         The poller below stays as a backstop (e.g. onboarding completed later). */
      try{
        var sh0=document.getElementById('sheetHost');
        window.__gateArmed=!!(HUB.auth&&!HUB.auth.currentUser()&&!(sh0&&!sh0.hidden));
      }catch(e){ window.__gateArmed=false; }
      /* Auth front door backstop: once the splash is gone (and any onboarding
         sheet), signed-out visitors land on the login screen. gate() returns
         false while the splash/sheet is still up or a session exists. */
      var gateTries=0;
      (function waitGate(){
        var opened=false;
        try{ if(HUB.auth&&HUB.auth.gate) opened=HUB.auth.gate(); }catch(e){}
        if(!opened&&++gateTries<120) setTimeout(waitGate,250);
      })();
      /* group invite deep link (#join=<id>): open the group or show the
         honest invite landing. Runs after boot so tabs/sheets are ready. */
      try{ if(HUB.cgroups&&HUB.cgroups.handleJoinHash) HUB.cgroups.handleJoinHash(); }catch(e){}
    });
  });
});
HUB.applyTheme=applyTheme;
HUB.ensureOnboarded=ensureOnboarded;
})();
