/* HUB Period & Wellness — Daily tab feature (2026-09-30, wave 2).
   A private cycle & everyday wellness space: period tracking, symptoms, mood,
   hydration, daily trackers, private notes, cycle history, reminders, food &
   diet plans, and a wellness knowledge hub.
   INTEGRATION RULES (standing):
   - Gender gate uses ONLY HUB.store.state.profile.gender ('female'/'other'
     full access, 'male' restricted, missing -> complete-profile card). Never
     inferred, never displayed publicly, never leaves this module.
   - Wellness data lives in its OWN localStorage key (hub_wellness_v1), never
     mixed with public profile data. Nothing is logged, nothing is sent to
     analytics, nothing leaves the device except an explicit user Export.
   - Predictions are always labeled estimates; the medical disclaimer ships
     with the dashboard. No diagnoses, ever.
   - Pink/rose is an ACCENT only; the module reuses .card/.btn/.chip/.input,
     HUB.ui.openSheet/toast/esc and the .chatroot overlay pattern. */
(function(){
'use strict';
var t=function(k,v){ return HUB.i18n.t(k,v); };
function ui(){ return HUB.ui; }
function esc(s){ return ui().esc(s==null?'':String(s)); }
function st(){ return HUB.store.state; }

/* ================= storage: separate key, private ================= */
var KEY='hub_wellness_v1';
var W=null;
function blank(){ return {
  enabled:false, lastPeriodStart:'', lastPeriodEnd:'', cycleLength:28,
  periodHistory:[], entries:{}, notes:[],
  reminders:{period:true, checkin:true, hydration:true},
  lockBio:false, hideCard:false, credId:null,
  createdAt:Date.now(), updatedAt:Date.now()
};}
function load(){
  if(W) return W;
  try{
    var raw=localStorage.getItem(KEY);
    if(raw){ var o=JSON.parse(raw)||{}; W=Object.assign(blank(),o);
      W.reminders=Object.assign({period:true,checkin:true,hydration:true},o.reminders||{});
      return W; }
  }catch(e){}
  W=blank(); save(); return W;
}
function save(){ if(!W) return; W.updatedAt=Date.now();
  try{ localStorage.setItem(KEY,JSON.stringify(W)); }catch(e){} }
function wipe(){ try{ localStorage.removeItem(KEY); }catch(e){} W=blank(); save(); }

/* ================= dates ================= */
function pad(n){ return (n<10?'0':'')+n; }
function dstr(d){ return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate()); }
function todayS(){ return dstr(new Date()); }
function parseD(s){ var m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(String(s||''));
  if(!m) return null; var d=new Date(+m[1],+m[2]-1,+m[3]); return isNaN(d)?null:d; }
function addD(s,n){ var d=parseD(s); if(!d) return ''; d.setDate(d.getDate()+n); return dstr(d); }
function diffD(a,b){ var x=parseD(a), y=parseD(b); if(!x||!y) return null;
  return Math.round((y.getTime()-x.getTime())/86400000); }
function fmtD(s){ try{ return new Date(s+'T12:00:00').toLocaleDateString(undefined,{month:'short',day:'numeric'}); }catch(e){ return s; } }
function fmtDFull(s){ try{ return new Date(s+'T12:00:00').toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'}); }catch(e){ return s; } }
function clampNum(v,lo,hi,fb){ v=parseInt(v,10); if(!isFinite(v)) return fb; return Math.max(lo,Math.min(hi,v)); }

/* ================= gender gate: profile.gender ONLY ================= */
function gender(){ try{ var p=st().profile||{}; return p.gender||''; }catch(e){ return ''; } }
function access(){ var g=gender();
  if(g==='female'||g==='other') return 'full';
  if(g==='male') return 'restr'; return 'none'; }

/* ================= per-day entries ================= */
function entry(ds){ load();
  var e=W.entries[ds];
  if(!e){ e={symptoms:[],symOther:'',mood:'',moodNote:'',hyd:{n:0,goal:8},trackers:{}}; W.entries[ds]=e; }
  if(!e.hyd) e.hyd={n:0,goal:8};
  if(!e.trackers) e.trackers={};
  if(!e.symptoms) e.symptoms=[];
  return e; }

/* ================= cycle math (estimates, never certain) ================= */
function avgCycle(){ load();
  var starts=[];
  (W.periodHistory||[]).forEach(function(h){ if(h&&h.start) starts.push(h.start); });
  if(W.lastPeriodStart) starts.push(W.lastPeriodStart);
  starts.sort();
  var gaps=[];
  for(var i=1;i<starts.length;i++){ var g=diffD(starts[i-1],starts[i]); if(g>=15&&g<=45) gaps.push(g); }
  var r=gaps.slice(-6);
  if(r.length) return Math.round(r.reduce(function(a,b){ return a+b; },0)/r.length);
  return clampNum(W.cycleLength,21,35,28);
}
function estNext(){ load();
  if(!W.enabled||!W.lastPeriodStart) return null;
  var len=avgCycle(), next=addD(W.lastPeriodStart,len);
  return {next:next, left:diffD(todayS(),next), len:len};
}
function cycleDay(){ load();
  if(!W.lastPeriodStart) return null;
  var d=diffD(W.lastPeriodStart,todayS()); return d==null?null:d+1;
}
/* Logged period longer than 7 days -> soft educational nudge (informational only). */
function heavyEntry(){ load();
  var found=null;
  (W.periodHistory||[]).forEach(function(h){
    if(h&&h.start&&h.end){ var d=diffD(h.start,h.end); if(d!=null&&d+1>7) found=h; } });
  if(W.lastPeriodStart&&W.lastPeriodEnd){ var d2=diffD(W.lastPeriodStart,W.lastPeriodEnd);
    if(d2!=null&&d2+1>7) found={start:W.lastPeriodStart,end:W.lastPeriodEnd,current:true}; }
  return found;
}

/* ================= static lists ================= */
var SYMPTOMS=[['cramps','wel.sCramps'],['bloat','wel.sBloat'],['head','wel.sHead'],
  ['back','wel.sBack'],['acne','wel.sAcne'],['fatigue','wel.sFatigue'],
  ['nausea','wel.sNausea'],['breast','wel.sBreast'],['moodch','wel.sMoodCh'],
  ['crave','wel.sCrave'],['sleep','wel.sSleep'],['other','wel.sOther']];
var MOODS=[['great','wel.mGreat'],['good','wel.mGood'],['okay','wel.mOkay'],
  ['low','wel.mLow'],['hard','wel.mHard']];
var TRACKERS=[['water','wel.trWater','droplet'],['sleep','wel.trSleep','moon'],['move','wel.trMove','activity'],
  ['relax','wel.trRelax','leaf'],['meals','wel.trMeals','bowl'],['mood','wel.trMood','smile']];
function moodKey2i18n(k){ for(var i=0;i<MOODS.length;i++) if(MOODS[i][0]===k) return MOODS[i][1]; return ''; }
function symLabel(k){ for(var i=0;i<SYMPTOMS.length;i++) if(SYMPTOMS[i][0]===k) return t(SYMPTOMS[i][1]); return k; }

/* ================= original inline SVG icons (stroke-based, minimal) ================= */
var IC={
heart:'<path fill="currentColor" stroke="none" d="M12 20.6C6.9 16.6 3 13.3 3 9.4 3 6.5 5.2 4.6 7.7 4.6c1.7 0 3.3.9 4.3 2.4 1-1.5 2.6-2.4 4.3-2.4 2.5 0 4.7 1.9 4.7 4.8 0 3.9-3.9 7.2-9 11.2z"/>',
droplet:'<path d="M12 3.2c3.4 4.4 6.3 7.9 6.3 11.3a6.3 6.3 0 1 1-12.6 0C5.7 11.1 8.6 7.6 12 3.2z"/>',
calendar:'<rect x="3.5" y="5" width="17" height="15.5" rx="3"/><path d="M3.5 9.8h17M8 3v3.6M16 3v3.6"/>',
activity:'<path d="M3 12.5h3.6l2.4-6.2 3.8 11.4 2.4-5.2H21"/>',
smile:'<circle cx="12" cy="12" r="8.6"/><circle cx="9" cy="10" r=".6" fill="currentColor" stroke="none"/><circle cx="15" cy="10" r=".6" fill="currentColor" stroke="none"/><path d="M8.6 14.2c.9 1.1 2.1 1.7 3.4 1.7s2.5-.6 3.4-1.7"/>',
moon:'<path d="M20 14.6A8.2 8.2 0 1 1 9.4 4a6.6 6.6 0 0 0 10.6 10.6z"/>',
leaf:'<path d="M5 19.5C5 10 12.5 5 20 4.5 19 12.5 14.5 19.5 5 19.5z"/><path d="M5 19.5c2.8-4.8 6.4-8.4 10.8-10.6"/>',
sprout:'<path d="M12 20v-7"/><path d="M12 13C12 9.5 9 7 5.5 7c0 3.8 2.8 6 6.5 6z"/><path d="M12 11c0-3 2.6-5 6-5 0 3.2-2.4 5-6 5z"/>',
flower:'<circle cx="12" cy="7.2" r="2.4"/><circle cx="16.6" cy="10.4" r="2.4"/><circle cx="14.8" cy="15.6" r="2.4"/><circle cx="9.2" cy="15.6" r="2.4"/><circle cx="7.4" cy="10.4" r="2.4"/><circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none"/>',
bowl:'<path d="M4 12.5h16a8 8 0 0 1-16 0z"/><path d="M9.5 8.8c0-1.3 1-1.5 1-2.8M14.5 8.8c0-1.3 1-1.5 1-2.8"/>',
book:'<path d="M5 4.5h10.5A3.5 3.5 0 0 1 19 8v11.5H8.5A3.5 3.5 0 0 1 5 16z"/><path d="M5 16a3.5 3.5 0 0 1 3.5-3.5H19"/>',
clock:'<circle cx="12" cy="12" r="8.6"/><path d="M12 7.5V12l3 2"/>',
bell:'<path d="M6 10a6 6 0 1 1 12 0c0 4 1.5 5.5 1.5 5.5h-15S6 14 6 10z"/><path d="M10 19a2.2 2.2 0 0 0 4 0"/>',
shield:'<path d="M12 3.2l6.8 2.8v5.6c0 4.3-2.9 7.2-6.8 8.7-3.9-1.5-6.8-4.4-6.8-8.7V6z"/><path d="M9.2 11.8l2 2 3.6-3.8"/>',
lock:'<rect x="5.5" y="10.5" width="13" height="9.5" rx="2.5"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/>',
note:'<rect x="5.5" y="4" width="13" height="16.5" rx="2.5"/><path d="M9 9.5h6M9 13h6M9 16.5h3.5"/>',
sparkle:'<path d="M12 3.5l1.7 5 5 1.7-5 1.7-1.7 5-1.7-5-5-1.7 5-1.7z"/><path d="M18.5 15.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z"/>'
};
function icSvg(n,cls){ return '<svg class="wl-ic'+(cls?' '+cls:'')+'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+IC[n]+'</svg>'; }
/* clay icons first (registered in js/icons.js as wl-*); SVG stays as the
   fallback for any icon that wasn't generated. */
function ic(n,cls){
  try{ if(window.HUB&&HUB.icons&&HUB.icons.map&&HUB.icons.map['wl-'+n])
    return HUB.icons.icon('wl-'+n,'wl-ic'+(cls?' '+cls:'')); }catch(e){}
  return icSvg(n,cls);
}
/* mood faces: clay 3D faces first, original SVG faces as fallback */
function faceSvg(k){
  var mouth={'great':'M7.6 14.2c1.2 2.1 2.7 3 4.4 3s3.2-.9 4.4-3','good':'M8.6 14.4c.9 1.1 2.1 1.6 3.4 1.6s2.5-.5 3.4-1.6','okay':'M9 15h6','low':'M8.8 16.2c1-1.2 2.1-1.8 3.2-1.8s2.2.6 3.2 1.8','hard':'M8.6 16.6c1.1-1.6 2.2-2.4 3.4-2.4s2.3.8 3.4 2.4'}[k]||'M9 15h6';
  return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="8.6"/><circle cx="9.1" cy="10" r=".6" fill="currentColor" stroke="none"/><circle cx="14.9" cy="10" r=".6" fill="currentColor" stroke="none"/><path d="'+mouth+'"/></svg>';
}
function face(k){
  try{ if(window.HUB&&HUB.icons&&HUB.icons.map&&HUB.icons.map['wl-mood-'+k])
    return HUB.icons.icon('wl-mood-'+k,'wl-moodface'); }catch(e){}
  return faceSvg(k);
}
/* tap ripple for primary buttons (delegated once) */
var rippleBound=false;
function bindRipple(){
  if(rippleBound) return; rippleBound=true;
  document.addEventListener('pointerdown',function(e){
    var b=e.target&&e.target.closest?e.target.closest('#wlCard .wl-btn,#wlRoot .wl-btn,.sheet .wl-btn'):null;
    if(!b) return;
    try{
      var r=b.getBoundingClientRect(), s=document.createElement('span');
      s.className='wl-ink'; var d=Math.max(r.width,r.height)*2.2;
      s.style.width=s.style.height=d+'px';
      s.style.left=(e.clientX-r.left-d/2)+'px'; s.style.top=(e.clientY-r.top-d/2)+'px';
      b.appendChild(s); setTimeout(function(){ s.remove(); },620);
    }catch(err){}
  },{passive:true});
}

/* ================= Daily card ================= */
function daysTxt(left){
  if(left==null) return '–';
  if(left<=0) return t('wel.dueNow');
  if(left===1) return t('wel.day1');
  return t('wel.daysN',{n:left});
}
function cardHTML(){
  load();
  var a=access(), h='';
  h+='<div class="card wl-card" style="margin-bottom:14px" id="wlCard">';
  if(a==='none'){
    h+='<div class="wl-nogender"><div class="wl-setup-mark" aria-hidden="true">'+ic('heart')+'</div>'
      +'<h3>'+esc(t('wel.title'))+'</h3>'
      +'<p class="sub" style="margin:8px 0 12px"><b>'+esc(t('wel.noProfT'))+'</b><br>'+esc(t('wel.noProfD'))+'</p>'
      +'<button class="btn wl-btn btn-sm" id="wlUpdProf">'+esc(t('wel.updProf'))+'</button>'
      +'<div class="wl-lockline">'+ic('lock','wl-ic-xs')+' '+esc(t('wel.privDefault'))+'</div></div>';
  }else if(a==='restr'){
    /* Restricted: no cycle data of any kind — tasteful, no shaming. */
    h+='<div class="wl-restrict"><div class="wl-setup-mark" aria-hidden="true">'+ic('shield')+'</div>'
      +'<h3>'+esc(t('wel.restrT'))+'</h3>'
      +'<p class="sub" style="margin:8px 0 12px">'+esc(t('wel.restrD'))+'</p>'
      +'<button class="btn btn-ghost btn-sm" id="wlBackDaily">'+esc(t('wel.backDaily'))+'</button></div>';
  }else if(W.hideCard){
    h+='<button class="wl-hidden-row" id="wlOpenDash">'+ic('lock','wl-ic-xs')
      +'<span class="grow">'+esc(t('wel.hidden'))
      +'<span class="sub2" style="display:block;font-size:12px;color:var(--wl-secondary)">'+esc(t('wel.hiddenSub'))+'</span></span>'
      +'<span aria-hidden="true">›</span></button>';
  }else if(!W.enabled){
    h+='<div class="wl-card-head"><div class="wl-card-ico" aria-hidden="true">'+ic('heart')+'</div><div>'
      +'<h3>'+esc(t('wel.title'))+'</h3><div class="sub">'+esc(t('wel.sub'))+'</div></div></div>'
      +'<div style="text-align:center;padding:14px 6px 2px"><div class="wl-setup-mark" aria-hidden="true">'+ic('heart')+'</div>'
      +'<p style="font-weight:800;margin:8px 0 2px">'+esc(t('wel.setupT'))+'</p>'
      +'<p class="sub" style="margin:0 0 12px">'+esc(t('wel.setupD'))+'</p>'
      +'<button class="btn wl-btn wl-shimmer" id="wlStart">'+esc(t('wel.start'))+'</button>'
      +'<div class="wl-lockline">'+ic('lock','wl-ic-xs')+' '+esc(t('wel.privDefault'))+'</div></div>';
  }else{
    var e=estNext(), en=entry(todayS());
    var mk=moodKey2i18n(en.mood), moodName=mk?t(mk):'–';
    h+='<div class="wl-card-head"><div class="wl-card-ico" aria-hidden="true">'+ic('heart')+'</div><div class="grow">'
      +'<h3>'+esc(t('wel.title'))+'</h3><div class="sub">'+esc(t('wel.sub'))+'</div></div></div>';
    if(e){
      h+='<div class="wl-next"><div><div class="lbl">'+esc(t('wel.next'))+'</div>'
        +'<div class="n">'+esc(daysTxt(e.left))+'</div></div>'
        +'<div style="margin-left:auto;text-align:right"><div class="est">'+esc(t('wel.estOn',{date:fmtD(e.next)}))+'</div></div></div>';
    }
    h+='<div class="wl-stats">'
      +'<div class="wl-stat"><div class="v">'+ic('droplet','wl-ic-xs')+' '+en.hyd.n+'/'+en.hyd.goal+'</div><div class="k">'+esc(t('wel.hyd'))+'</div></div>'
      +'<div class="wl-stat"><div class="v">'+esc(moodName)+'</div><div class="k">'+esc(t('wel.moodL'))+'</div></div>'
      +'<div class="wl-stat"><div class="v">'+ic('heart','wl-ic-xs')+' '+en.symptoms.length+'</div><div class="k">'+esc(t('wel.symL'))+'</div></div>'
      +'</div>'
      +'<button class="btn wl-btn wl-shimmer btn-block" id="wlOpenDash">'+esc(t('wel.open'))+'</button>'
      +'<div class="wl-lockline">'+ic('lock','wl-ic-xs')+' '+esc(t('wel.privDefault'))+'</div>';
  }
  h+='</div>';
  return h;
}
function refreshCard(){
  var c=document.getElementById('wlCard'); if(!c) return;
  var tmp=document.createElement('div'); tmp.innerHTML=cardHTML();
  var nw=tmp.firstChild; c.replaceWith(nw); bindCard(nw);
}
function bindCard(card){
  if(!card||!card.querySelector) return;
  function on(id,fn){ var b=card.querySelector('#'+id); if(b) b.onclick=fn; }
  on('wlStart',function(){ load(); W.enabled=true; save(); refreshCard(); openDash(); });
  on('wlOpenDash',function(){ openDash(); });
  on('wlBackDaily',function(){ try{ HUB.showTab('daily'); }catch(e){} });
  on('wlUpdProf',function(){
    try{ HUB.showTab('me'); }catch(e){}
    setTimeout(function(){ var b=document.getElementById('meEditBtn'); if(b) b.click(); },400);
  });
}
function bind(host){ var c=(host&&host.querySelector)?host.querySelector('#wlCard'):document.getElementById('wlCard'); bindCard(c); bindRipple(); }

/* ================= dashboard overlay ================= */
var OVL='wlRoot', unlocked=false, calCur=null;
function closeDash(){ var o=document.getElementById(OVL); if(o) o.remove();
  document.removeEventListener('keydown',onKey,true); unlocked=false; }
function onKey(e){ if(e.key!=='Escape') return;
  var sh=document.getElementById('sheetHost');
  if(sh&&!sh.hidden){ e.stopImmediatePropagation(); ui().closeSheet(); return; }
  e.stopImmediatePropagation(); e.preventDefault(); closeDash(); }
function openDash(){
  load(); if(access()!=='full') return;
  closeDash(); ui().closeSheet();
  ['search','pulse','notifications'].forEach(function(k){ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
  try{ if(HUB.chat&&HUB.chat.close) HUB.chat.close(); }catch(e){}
  var host=document.getElementById('app')||document.body;
  var d=document.createElement('div'); d.className='chatroot wlroot'; d.id=OVL;
  d.innerHTML='<div class="wl-page" id="wlPage"></div>';
  host.appendChild(d);
  document.addEventListener('keydown',onKey,true);
  var now=new Date(); calCur={y:now.getFullYear(),m:now.getMonth()};
  paintDash(); bindRipple();
}
function page(){ return document.getElementById('wlPage'); }

var sectN=0, calDir=0;
function dly(){ sectN++; return Math.min(sectN*45,360); }
function sectOpen(h3){ return '<div class="wl-sect wl-in" style="animation-delay:'+dly()+'ms">'+(h3?'<h3>'+h3+'</h3>':''); }
function sectHead(x){ return sectOpen(x); }
function sectEnd(){ return '</div>'; }

function paintDash(flash){
  load(); var p=page(); if(!p) return;
  if(W.lockBio&&W.credId&&!unlocked){ paintLock(p); return; }
  sectN=0;
  var ds=todayS(), now=new Date();
  var dateLine=now.toLocaleDateString(undefined,{weekday:'long',month:'long',day:'numeric'});
  var h='<div class="wl-topbar"><button class="wl-back" id="wlBack" aria-label="'+esc(t('wel.backDaily'))+'">←</button>'
    +'<h2>'+esc(t('wel.dashT'))+'</h2></div>'
    +'<p class="wl-date">'+esc(t('wel.dashSub'))+' · '+esc(dateLine)+'</p>';
  h+=remindersHTML(ds);
  var hv=heavyEntry();
  if(hv) h+='<div class="wl-nudge wl-in" style="animation-delay:'+dly()+'ms" role="note">'+ic('heart')+'<span>'+esc(t('wel.nudgeHeavy'))+'</span></div>';
  h+=sectOpen()+cycleHeroHTML()+sectEnd();
  h+=sectHead(ic('droplet')+t('wel.logPeriod'))+'<div class="card tight" style="margin-bottom:16px"><button class="btn wl-btn wl-shimmer btn-sm" id="wlLogBtn">'+esc(t('wel.logPeriod'))+'</button></div>'+sectEnd();
  h+=sectHead(ic('calendar')+t('wel.cal'))+calHTML()+sectEnd();
  h+=sectHead(ic('activity')+t('wel.howFeel'))+symptomsHTML(ds)+sectEnd();
  h+=sectHead(ic('smile')+t('wel.todayMood'))+moodHTML(ds)+sectEnd();
  h+=sectHead(ic('droplet')+t('wel.hydT'))+hydHTML(ds)+sectEnd();
  h+=sectHead(ic('leaf')+t('wel.trackers'))+trackersHTML(ds)+sectEnd();
  h+=sectHead(ic('bowl')+t('wel.foodT'))+foodHTML()+sectEnd();
  h+=sectHead(ic('book')+t('wel.hubT'))+hubHTML()+sectEnd();
  h+=sectHead(ic('note')+t('wel.notes'))+notesHTML()+sectEnd();
  h+=sectHead(ic('clock')+t('wel.history'))+historyHTML()+sectEnd();
  h+=sectHead(ic('bell')+t('wel.remT'))+remSetHTML()+sectEnd();
  h+=sectHead(ic('shield')+t('wel.privT'))+privHTML()+sectEnd();
  /* keep the user's scroll position: repainting innerHTML resets it to the
     top, which feels like a page refresh on every tap. */
  var keepY=p.scrollTop||0;
  p.innerHTML=h;
  bindDash(p);
  if(p.scrollTop!==keepY){ try{ p.scrollTop=keepY; }catch(e){} }
  calDir=0;
  if(flash){ var el=p.querySelector(flash);
    if(el){ el.classList.add('wl-pop');
      el.addEventListener('animationend',function(){ el.classList.remove('wl-pop'); },{once:true}); } }
}

function remindersHTML(ds){
  load(); var out='', en=entry(ds), e=estNext();
  if(W.reminders.period&&e&&e.left!=null&&e.left>=0&&e.left<=3)
    out+='<div class="wl-remind" role="note">'+ic('flower')+'<span>'+esc(t('wel.remSoon'))+'</span></div>';
  if(W.reminders.checkin&&!en.mood&&!en.symptoms.length)
    out+='<div class="wl-remind" role="note">'+ic('heart')+'<span>'+esc(t('wel.remCheck'))+'</span></div>';
  if(W.reminders.hydration&&en.hyd.n<en.hyd.goal)
    out+='<div class="wl-remind" role="note">'+ic('droplet')+'<span>'+esc(t('wel.remWater'))+'</span></div>';
  return out;
}

function cycleHeroHTML(){
  load(); var e=estNext();
  var h='<div class="wl-hero">';
  if(e){
    /* animated cycle-progress ring around a floating heart mark */
    var pct=Math.min(Math.max((e.len-e.left)/e.len,0),1), C=188.5, off=(C*(1-pct)).toFixed(1);
    h+='<div class="wl-hero-ring" aria-hidden="true"><svg class="ring" viewBox="0 0 72 72"><circle class="bg" cx="36" cy="36" r="30"/><circle class="fg" cx="36" cy="36" r="30" stroke-dasharray="'+C+'" style="--rf:'+C+';--rt:'+off+'"/></svg><span class="wl-hero-mark">'+ic('heart')+'</span></div>'
      +'<div style="font-weight:800;font-size:15px">'+esc(t('wel.next'))+'</div>'
      +'<div class="n">'+esc(daysTxt(e.left))+'</div>'
      +'<div class="est">'+esc(t('wel.estOn',{date:fmtDFull(e.next)}))+' · '+esc(t('wel.avgCycle'))+': '+e.len+' '+esc(t('wel.daysU'))+'</div>';
  }else{
    h+='<div class="wl-hero-ring" aria-hidden="true"><svg class="ring" viewBox="0 0 72 72"><circle class="bg" cx="36" cy="36" r="30"/><circle class="fg" cx="36" cy="36" r="30" stroke-dasharray="188.5" style="--rf:188.5;--rt:188.5"/></svg><span class="wl-hero-mark">'+ic('heart')+'</span></div>'
      +'<div style="font-weight:800;font-size:15px">'+esc(t('wel.next'))+'</div>'
      +'<p class="sub" style="margin:8px 0 0">'+esc(t('wel.noData'))+'</p>';
  }
  h+='<p class="hint" style="margin:10px 0 0">'+esc(t('wel.basedOn'))+'</p></div>'
    +'<p class="hint" style="margin:8px 2px 0">'+ic('note','wl-ic-xs')+' '+esc(t('wel.disclaimer'))+' '+esc(t('wel.consider'))+'</p>';
  return h;
}

/* ---------- log period sheet ---------- */
function logSheet(){
  load();
  var avg=avgCycle();
  ui().openSheet(
    '<h2>'+ic('droplet')+' '+esc(t('wel.logPeriod'))+'</h2>'
    +'<p class="sub">'+esc(t('wel.qStart'))+'</p>'
    +'<div class="field"><label>'+esc(t('wel.startDate'))+'</label><input class="input" id="wlPStart" type="date" value="'+esc(W.lastPeriodStart||todayS())+'" max="'+todayS()+'"></div>'
    +'<div class="field"><label>'+esc(t('wel.endDateOpt'))+'</label><input class="input" id="wlPEnd" type="date" value="'+esc(W.lastPeriodEnd||'')+'" max="'+todayS()+'"></div>'
    +'<div class="field"><label>'+esc(t('wel.cycleLen'))+'</label><input class="input" id="wlPLen" type="number" min="21" max="35" value="'+avg+'" style="width:110px"></div>'
    +'<button class="btn wl-btn wl-shimmer btn-block" id="wlPSave">'+esc(t('wel.save'))+'</button>'
    +'<p class="hint" style="margin-top:8px">'+esc(t('wel.disclaimer'))+'</p>'
  );
  document.getElementById('wlPSave').onclick=function(){
    var s=document.getElementById('wlPStart').value, en2=document.getElementById('wlPEnd').value;
    var len=clampNum(document.getElementById('wlPLen').value,21,35,avg);
    if(!parseD(s)){ ui().toast(t('wel.needDate')); return; }
    if(en2&&diffD(s,en2)<0){ ui().toast(t('wel.endAfter')); return; }
    if(s!==W.lastPeriodStart&&W.lastPeriodStart){
      W.periodHistory.push({id:'p'+Date.now(),start:W.lastPeriodStart,end:W.lastPeriodEnd||''});
    }
    W.lastPeriodStart=s; W.lastPeriodEnd=en2||''; W.cycleLength=len;
    save(); ui().closeSheet(); ui().toast(t('wel.saved')); paintDash(); refreshCard();
  };
}

/* ---------- calendar ---------- */
function calHTML(){
  load();
  var y=calCur.y, m=calCur.m;
  var first=new Date(y,m,1), startDow=first.getDay();
  var dim=new Date(y,m+1,0).getDate();
  var monthName=first.toLocaleDateString(undefined,{month:'long',year:'numeric'});
  var e=estNext();
  var estDays={};
  if(e&&e.next){ for(var i=0;i<5;i++) estDays[addD(e.next,i)]=1; }
  var bleedDays={};
  function markBleed(s,en2){ if(!s) return; var n=en2&&diffD(s,en2)>=0?diffD(s,en2)+1:5;
    for(var i=0;i<Math.min(n,8);i++) bleedDays[addD(s,i)]=1; }
  markBleed(W.lastPeriodStart,W.lastPeriodEnd);
  (W.periodHistory||[]).forEach(function(h){ markBleed(h.start,h.end); });
  var loggedDays={};
  Object.keys(W.entries||{}).forEach(function(ds){
    var en3=W.entries[ds];
    if(en3&&(en3.mood||en3.symptoms.length||en3.moodNote||en3.hyd.n>0)) loggedDays[ds]=1;
  });
  var tds=todayS(), h='';
  h+='<div class="wl-cal'+(calDir<0?' wl-slide-l':calDir>0?' wl-slide-r':'')+'"><div class="wl-cal-head">'
    +'<button class="wl-cal-nav" id="wlCalPrev" aria-label="‹">‹</button><b>'+esc(monthName)+'</b>'
    +'<button class="wl-cal-nav" id="wlCalNext" aria-label="›">›</button></div>'
    +'<div class="wl-cal-grid">';
  var dows=[]; try{ for(var di=0;di<7;di++) dows.push(new Date(2026,5,di).toLocaleDateString(undefined,{weekday:'narrow'})); }
  catch(err){ dows=['S','M','T','W','T','F','S']; }
  dows.forEach(function(d){ h+='<div class="wl-cal-dow">'+esc(d)+'</div>'; });
  var prevDim=new Date(y,m,0).getDate();
  for(var i=startDow-1;i>=0;i--){ h+='<div class="wl-cal-day dim">'+(prevDim-i)+'</div>'; }
  for(var d2=1;d2<=dim;d2++){
    var ds2=y+'-'+pad(m+1)+'-'+pad(d2), cls='wl-cal-day', dot='';
    if(bleedDays[ds2]) cls+=' period';
    else if(estDays[ds2]) cls+=' est';
    if(ds2===tds) cls+=' today';
    if(loggedDays[ds2]&&!bleedDays[ds2]) dot='<span class="dot"></span>';
    h+='<div class="'+cls+'" data-ds="'+ds2+'">'+d2+dot+'</div>';
  }
  var tail=(7-(startDow+dim)%7)%7;
  for(var k2=1;k2<=tail;k2++){ h+='<div class="wl-cal-day dim">'+k2+'</div>'; }
  h+='</div><div class="wl-cal-legend">'
    +'<span><span class="wl-swatch" style="background:var(--wl-primary)"></span>'+esc(t('wel.lPeriod'))+'</span>'
    +'<span><span class="wl-swatch" style="background:var(--wl-soft);border:1px solid var(--wl-primary)"></span>'+esc(t('wel.lEst'))+'</span>'
    +'<span><span class="wl-swatch" style="background:var(--wl-primary-deep)"></span>'+esc(t('wel.lLogged'))+'</span>'
    +'</div></div>';
  return h;
}

/* ---------- symptoms ---------- */
function symptomsHTML(ds){
  load(); var en=entry(ds);
  var h='<div class="wl-chips" id="wlSymChips">';
  SYMPTOMS.forEach(function(s){
    var on=en.symptoms.indexOf(s[0])>=0;
    h+='<button class="wl-chip'+(on?' on':'')+'" data-sym="'+s[0]+'">'+esc(t(s[1]))+'</button>';
  });
  h+='</div>';
  var showOther=en.symptoms.indexOf('other')>=0;
  h+='<div class="field" id="wlSymOtherWrap" style="margin-top:8px;'+(showOther?'':'display:none')+'">'
    +'<input class="input" id="wlSymOther" maxlength="60" placeholder="'+esc(t('wel.sOtherPh'))+'" value="'+esc(en.symOther||'')+'"></div>';
  return h;
}
/* ---------- mood ---------- */
function moodHTML(ds){
  load(); var en=entry(ds);
  var h='<div class="wl-moods" id="wlMoods">';
  MOODS.forEach(function(m){
    h+='<button class="wl-mood'+(en.mood===m[0]?' on':'')+'" data-mood="'+m[0]+'"><span class="e">'+face(m[0])+'</span>'+esc(t(m[1]))+'</button>';
  });
  h+='</div><div class="field" style="margin-top:8px"><input class="input" id="wlMoodNote" maxlength="120" placeholder="'+esc(t('wel.notePh'))+'" value="'+esc(en.moodNote||'')+'"></div>';
  return h;
}
/* ---------- hydration ---------- */
function hydHTML(ds){
  load(); var en=entry(ds);
  var h='<div class="card tight"><div class="row between" style="margin-bottom:6px">'
    +'<b>'+ic('droplet','wl-ic-xs')+' '+esc(t('wel.hydT'))+'</b>'
    +'<span class="sub" id="wlHydCount"><b>'+en.hyd.n+' / '+en.hyd.goal+'</b> '+esc(t('wel.glasses'))+'</span></div>'
    +'<div class="wl-glasses" id="wlGlasses">';
  for(var i=0;i<en.hyd.goal;i++){
    h+='<button class="wl-glass'+(i<en.hyd.n?' full':'')+'" data-g="'+i+'" aria-label="'+(i+1)+'"><span class="wl-fill"></span><span class="wl-drop">'+ic('droplet')+'</span></button>';
  }
  h+='</div><div class="row" style="gap:8px;align-items:center">'
    +'<span class="sub">'+esc(t('wel.goal'))+':</span>'
    +'<button class="btn btn-ghost btn-sm" id="wlGoalDown" aria-label="−">−</button>'
    +'<b>'+en.hyd.goal+'</b>'
    +'<button class="btn btn-ghost btn-sm" id="wlGoalUp" aria-label="+">+</button></div>'
    +'</div><p class="hint" style="margin:6px 2px 0">'+esc(t('wel.noPressure'))+'</p>';
  return h;
}
/* ---------- daily trackers (all optional) ---------- */
function trackersHTML(ds){
  load(); var en=entry(ds);
  var h='<div class="wl-trackers" id="wlTrackers">';
  TRACKERS.forEach(function(tr){
    var on=!!en.trackers[tr[0]];
    h+='<button class="wl-tracker'+(on?' on':'')+'" data-tr="'+tr[0]+'"><span class="e">'+ic(tr[2])+'</span>'+esc(t(tr[1]))+'</button>';
  });
  h+='</div><p class="hint" style="margin:6px 2px 0">'+esc(t('wel.noPressure'))+'</p>';
  return h;
}
/* ---------- private notes ---------- */
function notesHTML(){
  load();
  var h='<div class="card tight"><div class="field" style="margin:0">'
    +'<textarea class="input" id="wlNoteTxt" rows="2" maxlength="280" placeholder="'+esc(t('wel.notePh2'))+'"></textarea></div>'
    +'<button class="btn wl-btn-ghost btn-sm" id="wlNoteAdd" style="margin-top:8px">＋ '+esc(t('wel.addNote'))+'</button>'
    +'<div id="wlNoteList" style="margin-top:10px">';
  var notes=(W.notes||[]).slice().sort(function(a,b){ return b.at-a.at; }).slice(0,30);
  if(!notes.length) h+='<p class="sub" style="margin:4px 0">'+esc(t('wel.noNotes'))+'</p>';
  notes.forEach(function(n){
    var d=''; try{ d=new Date(n.at).toLocaleDateString(undefined,{month:'short',day:'numeric'}); }catch(e){}
    h+='<div class="wl-note"><div class="row between"><span class="d">'+esc(d)+' '+ic('lock','wl-ic-xs')+'</span>'
      +'<button class="linklike" data-ndel="'+n.id+'" aria-label="'+esc(t('wel.delete'))+'">✕</button></div>'
      +'<p>'+esc(n.text)+'</p></div>';
  });
  h+='</div></div><p class="hint" style="margin:6px 2px 0">'+ic('lock','wl-ic-xs')+' '+esc(t('wel.notesPriv'))+'</p>';
  return h;
}
/* ---------- cycle history ---------- */
function historyHTML(){
  load();
  var h='<div id="wlHistList">';
  var hist=(W.periodHistory||[]).slice().sort(function(a,b){ return a.start<b.start?1:-1; });
  if(W.lastPeriodStart) hist.unshift({start:W.lastPeriodStart,end:W.lastPeriodEnd||'',current:true,id:'cur'});
  if(!hist.length) h+='<p class="sub">'+esc(t('wel.noHist'))+'</p>';
  hist.slice(0,12).forEach(function(c){
    var label=''; try{ label=new Date(c.start+'T12:00:00').toLocaleDateString(undefined,{month:'long'}); }catch(e){ label=c.start; }
    var len=''; if(c.end&&diffD(c.start,c.end)!=null) len=(diffD(c.start,c.end)+1)+' '+t('wel.daysU');
    h+='<button class="wl-hist" data-hid="'+c.id+'"><div class="row between"><span class="m">'+esc(label)+(c.current?' · <span style="color:var(--wl-primary-deep)">'+esc(t('wel.current'))+'</span>':'')+'</span><span>›</span></div>'
      +'<div class="l">'+esc(len||t('wel.inProgress'))+'</div></button>';
  });
  h+='</div>';
  return h;
}
function cycleDetailSheet(c){
  load();
  var nxt=null, all=[];
  (W.periodHistory||[]).forEach(function(h){ if(h.start) all.push(h.start); });
  if(W.lastPeriodStart) all.push(W.lastPeriodStart);
  all.sort();
  var i=all.indexOf(c.start);
  var endBound=(i>=0&&i<all.length-1)?addD(all[i+1],-1):todayS();
  var syms={}, moods=[], notes=[];
  Object.keys(W.entries||{}).forEach(function(ds){
    if(ds>=c.start&&ds<=endBound){ var en2=W.entries[ds];
      (en2.symptoms||[]).forEach(function(s){ syms[s]=1; });
      if(en2.mood) moods.push({d:ds,m:en2.mood});
      if(en2.moodNote) notes.push(en2.moodNote); }
  });
  (W.notes||[]).forEach(function(n){ try{ var ds3=dstr(new Date(n.at)); if(ds3>=c.start&&ds3<=endBound) notes.push(n.text); }catch(e){} });
  var len=c.end&&diffD(c.start,c.end)!=null?(diffD(c.start,c.end)+1)+' '+t('wel.daysU'):'–';
  ui().openSheet('<h2>'+ic('droplet')+' '+esc(fmtDFull(c.start))+'</h2><dl class="wl-detail">'
    +'<dt>'+esc(t('wel.cStart'))+'</dt><dd>'+esc(fmtDFull(c.start))+'</dd>'
    +'<dt>'+esc(t('wel.cEnd'))+'</dt><dd>'+esc(c.end?fmtDFull(c.end):t('wel.inProgress'))+'</dd>'
    +'<dt>'+esc(t('wel.cLen'))+'</dt><dd>'+esc(len)+'</dd>'
    +'<dt>'+esc(t('wel.cSym'))+'</dt><dd>'+esc(Object.keys(syms).map(symLabel).join(', ')||'–')+'</dd>'
    +'<dt>'+esc(t('wel.cMood'))+'</dt><dd>'+esc(moods.length?t(moodKey2i18n(moods[moods.length-1].m)):'–')+'</dd>'
    +'<dt>'+esc(t('wel.cNotes'))+'</dt><dd>'+esc(notes.slice(0,5).join(' · ')||'–')+'</dd>'
    +'</dl><p class="hint">'+esc(t('wel.basedOn'))+'</p>'
    +'<button class="btn btn-ghost btn-block" data-close>'+esc(t('wel.close'))+'</button>');
}
/* ---------- reminder settings ---------- */
function remSetHTML(){
  load();
  function row(k,label){ return '<div class="wl-setrow"><span class="grow">'+esc(label)+'</span>'
    +'<button class="wl-toggle'+(W.reminders[k]?' on':'')+'" data-rem="'+k+'" role="switch" aria-checked="'+(!!W.reminders[k])+'"></button></div>'; }
  return '<div class="card tight">'
    +row('period',t('wel.remPeriod'))+row('checkin',t('wel.remCheckin'))+row('hydration',t('wel.remHyd'))
    +'</div><p class="hint" style="margin:6px 2px 0">'+esc(t('wel.remNote'))+'</p>';
}

/* ================= food & diet plans (wave 2) ================= */
var PHASES=[
  {id:'men',icon:'droplet',tag:'wel.phMen',desc:'wel.phMenD',
   favor:['wel.fMen1','wel.fMen2','wel.fMen3','wel.fMen4','wel.fMen5'],
   limit:['wel.lMen1','wel.lMen2'],meals:['wel.mMen1','wel.mMen2','wel.mMen3']},
  {id:'fol',icon:'sprout',tag:'wel.phFol',desc:'wel.phFolD',
   favor:['wel.fFol1','wel.fFol2','wel.fFol3','wel.fFol4','wel.fFol5'],
   limit:['wel.lFol1','wel.lFol2'],meals:['wel.mFol1','wel.mFol2','wel.mFol3']},
  {id:'ovu',icon:'flower',tag:'wel.phOvu',desc:'wel.phOvuD',
   favor:['wel.fOvu1','wel.fOvu2','wel.fOvu3','wel.fOvu4','wel.fOvu5'],
   limit:['wel.lOvu1','wel.lOvu2'],meals:['wel.mOvu1','wel.mOvu2','wel.mOvu3']},
  {id:'lut',icon:'leaf',tag:'wel.phLut',desc:'wel.phLutD',
   favor:['wel.fLut1','wel.fLut2','wel.fLut3','wel.fLut4','wel.fLut5'],
   limit:['wel.lLut1','wel.lLut2'],meals:['wel.mLut1','wel.mLut2','wel.mLut3']}
];
function currentPhase(){
  var cd=cycleDay(); if(cd==null) return null;
  if(cd<=5) return 'men';
  if(cd<14) return 'fol';
  if(cd<=16) return 'ovu';
  return 'lut';
}
function foodHTML(){
  load();
  var cur=currentPhase();
  var h='<p class="sub" style="margin:0 0 10px">'+esc(t('wel.foodSub'))+'</p>';
  PHASES.forEach(function(ph){
    h+='<div class="wl-phase"><h4>'+ic(ph.icon)+' '+esc(t(ph.tag))
      +(cur===ph.id?' <span class="tag">'+esc(t('wel.now'))+'</span>':'')
      +'</h4><div class="sub" style="font-size:12.5px;margin-bottom:6px">'+esc(t(ph.desc))+'</div>'
      +'<div class="wl-kicker" style="margin:8px 0 4px">✓ '+esc(t('wel.eatMore'))+'</div><ul>'
      +ph.favor.map(function(k){ return '<li>'+esc(t(k))+'</li>'; }).join('')+'</ul>'
      +'<div class="wl-kicker" style="margin:8px 0 4px">– '+esc(t('wel.limit'))+'</div><ul>'
      +ph.limit.map(function(k){ return '<li>'+esc(t(k))+'</li>'; }).join('')+'</ul>'
      +'<div class="wl-kicker" style="margin:8px 0 4px">'+ic('bowl','wl-ic-xs')+' '+esc(t('wel.mealIdeas'))+'</div><ul>'
      +ph.meals.map(function(k){ return '<li>'+esc(t(k))+'</li>'; }).join('')+'</ul></div>';
  });
  h+='<div class="wl-phase"><h4>'+ic('bowl')+' '+esc(t('wel.dietT'))+'</h4><ul>'
    +['wel.d1','wel.d2','wel.d3','wel.d4','wel.d5','wel.d6'].map(function(k){ return '<li>'+esc(t(k))+'</li>'; }).join('')
    +'</ul></div>'
    +'<p class="hint" style="margin:6px 2px 0">'+ic('note','wl-ic-xs')+' '+esc(t('wel.foodNote'))+'</p>';
  return h;
}
/* ================= wellness knowledge hub (wave 2) ================= */
var ARTICLES=[
  {icon:'flower',title:'wel.a1T',body:['wel.a11','wel.a12','wel.a13','wel.a14','wel.a15']},
  {icon:'sparkle',title:'wel.a2T',body:['wel.a21','wel.a22','wel.a23','wel.a24','wel.a25','wel.a26']},
  {icon:'moon',title:'wel.a3T',body:['wel.a31','wel.a32','wel.a33','wel.a34','wel.a35']},
  {icon:'droplet',title:'wel.a4T',body:['wel.a41','wel.a42','wel.a43','wel.a44','wel.a45','wel.a46','wel.a47']}
];
function hubHTML(){
  var h='<p class="sub" style="margin:0 0 10px">'+esc(t('wel.hubSub'))+'</p>';
  ARTICLES.forEach(function(a,i){
    h+='<button class="wl-article" data-art="'+i+'"><h4>'+ic(a.icon)+' '
      +esc(t(a.title))+' <span style="margin-left:auto;color:var(--faint)">›</span></h4>'
      +'<div class="body"><ul>'+a.body.map(function(k){ return '<li>'+esc(t(k))+'</li>'; }).join('')
      +'</ul></div></button>';
  });
  h+='<p class="hint" style="margin:6px 2px 0">'+ic('note','wl-ic-xs')+' '+esc(t('wel.foodNote'))+' '+esc(t('wel.consider'))+'</p>';
  return h;
}
/* ================= privacy ================= */
function privHTML(){
  load();
  var h='<p class="sub" style="margin:0 0 10px">'+ic('lock','wl-ic-xs')+' '+esc(t('wel.privD'))+'</p><div class="card tight">';
  h+='<div class="wl-setrow"><span class="grow">'+esc(t('wel.lockBio'))
    +'<span class="sub2">'+(W.lockBio?esc(t('wel.on')):esc(t('wel.off')))+'</span></span>'
    +'<button class="btn btn-ghost btn-sm" id="wlBioBtn">'+esc(W.lockBio?t('wel.turnOff'):t('wel.turnOn'))+'</button></div>';
  h+='<div class="wl-setrow"><span class="grow">'+esc(W.hideCard?t('wel.showCard'):t('wel.hideCard'))+'</span>'
    +'<button class="wl-toggle'+(W.hideCard?' on':'')+'" id="wlHideTgl" role="switch" aria-checked="'+(!!W.hideCard)+'"></button></div>';
  h+='<div class="wl-setrow"><span class="grow">'+esc(t('wel.export'))+'</span>'
    +'<button class="btn btn-ghost btn-sm" id="wlExport">'+esc(t('wel.export'))+'</button></div>';
  h+='<div class="wl-setrow"><span class="grow wl-danger">'+esc(t('wel.delete'))+'</span>'
    +'<button class="btn btn-ghost btn-sm" id="wlDelete"><span class="wl-danger">'+esc(t('wel.delete'))+'</span></button></div>';
  h+='<div class="wl-setrow"><span class="grow">'+esc(W.enabled?t('wel.turnOff'):t('wel.turnOn'))+'</span>'
    +'<button class="wl-toggle'+(W.enabled?' on':'')+'" id="wlTrackTgl" role="switch" aria-checked="'+(!!W.enabled)+'"></button></div>';
  h+='</div><p class="hint" style="margin:6px 2px 0">'+esc(t('wel.disclaimer'))+'</p>';
  return h;
}
/* ---------- biometrics (WebAuthn platform authenticator; hidden if unsupported) ---------- */
function b64e(buf){ var s='',b=new Uint8Array(buf); for(var i=0;i<b.length;i++) s+=String.fromCharCode(b[i]); return btoa(s); }
function b64d(s){ var bin=atob(s),b=new Uint8Array(bin.length); for(var i=0;i<bin.length;i++) b[i]=bin.charCodeAt(i); return b.buffer; }
function bioSupported(cb){
  try{
    if(window.PublicKeyCredential&&PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable)
      PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable().then(function(ok){ cb(!!ok); }).catch(function(){ cb(false); });
    else cb(false);
  }catch(e){ cb(false); }
}
function bioEnroll(cb){
  try{
    var ch=new Uint8Array(32); crypto.getRandomValues(ch);
    var uid=new Uint8Array(16); crypto.getRandomValues(uid);
    navigator.credentials.create({publicKey:{challenge:ch,rp:{name:'Onaro'},
      user:{id:uid,name:'wellness',displayName:t('wel.title')},
      pubKeyCredParams:[{type:'public-key',alg:-7},{type:'public-key',alg:-257}],
      authenticatorSelection:{userVerification:'required'},timeout:60000}})
    .then(function(c){ W.credId=b64e(c.rawId); W.lockBio=true; save(); cb(true); })
    .catch(function(){ cb(false); });
  }catch(e){ cb(false); }
}
function bioAuth(cb){
  try{
    var ch=new Uint8Array(32); crypto.getRandomValues(ch);
    navigator.credentials.get({publicKey:{challenge:ch,
      allowCredentials:[{id:b64d(W.credId),type:'public-key'}],
      userVerification:'required',timeout:60000}})
    .then(function(){ cb(true); }).catch(function(){ cb(false); });
  }catch(e){ cb(false); }
}
function paintLock(p){
  p.innerHTML='<div class="wl-lockwrap"><div class="wl-setup-mark" aria-hidden="true">'+ic('shield')+'</div>'
    +'<h2>'+esc(t('wel.lockT'))+'</h2>'
    +'<p class="sub" style="margin:8px 0 16px">'+esc(t('wel.privD'))+'</p>'
    +'<button class="btn wl-btn wl-shimmer btn-block" id="wlUnlockBtn">'+esc(t('wel.unlock'))+'</button>'
    +'<button class="btn btn-ghost btn-block" id="wlBack2" style="margin-top:8px">'+esc(t('wel.backDaily'))+'</button></div>';
  document.getElementById('wlUnlockBtn').onclick=function(){
    bioAuth(function(ok){ if(ok){ unlocked=true; paintDash(); } else ui().toast(t('wel.unlockFail')); });
  };
  document.getElementById('wlBack2').onclick=function(){ closeDash(); };
}
/* ================= dashboard bindings ================= */
function bindDash(p){
  load(); var ds=todayS();
  function q(id){ return p.querySelector('#'+id); }
  var back=q('wlBack'); if(back) back.onclick=function(){ closeDash(); refreshCard(); };
  var lb=q('wlLogBtn'); if(lb) lb.onclick=logSheet;
  var cp=q('wlCalPrev'); if(cp) cp.onclick=function(){ calDir=-1; calCur.m--; if(calCur.m<0){calCur.m=11;calCur.y--;} paintDash(); };
  var cn=q('wlCalNext'); if(cn) cn.onclick=function(){ calDir=1; calCur.m++; if(calCur.m>11){calCur.m=0;calCur.y++;} paintDash(); };
  /* symptoms */
  p.querySelectorAll('#wlSymChips .wl-chip').forEach(function(ch){
    ch.onclick=function(){
      var en=entry(ds), k=ch.dataset.sym, i=en.symptoms.indexOf(k);
      if(i>=0) en.symptoms.splice(i,1); else en.symptoms.push(k);
      save(); paintDash('[data-sym="'+k+'"]');
    };
  });
  var so=q('wlSymOther'); if(so) so.onchange=function(){ entry(ds).symOther=so.value; save(); };
  /* mood */
  p.querySelectorAll('#wlMoods .wl-mood').forEach(function(m){
    m.onclick=function(){ entry(ds).mood=m.dataset.mood; save(); paintDash('[data-mood="'+m.dataset.mood+'"]'); };
  });
  var mn=q('wlMoodNote'); if(mn) mn.onchange=function(){ entry(ds).moodNote=mn.value; save(); };
  /* hydration */
  p.querySelectorAll('#wlGlasses .wl-glass').forEach(function(g){
    g.onclick=function(){ var en=entry(ds), i=+g.dataset.g; en.hyd.n=(en.hyd.n===i+1?i:i+1); save();
      /* in-place update so the water fill animates instead of re-rendering */
      p.querySelectorAll('#wlGlasses .wl-glass').forEach(function(gg,gi){ gg.classList.toggle('full',gi<en.hyd.n); });
      var cnt=q('wlHydCount'); if(cnt) cnt.innerHTML='<b>'+en.hyd.n+' / '+en.hyd.goal+'</b> '+esc(t('wel.glasses'));
      refreshCard(); };
  });
  var gd=q('wlGoalDown'); if(gd) gd.onclick=function(){ var en=entry(ds); en.hyd.goal=Math.max(4,en.hyd.goal-1); if(en.hyd.n>en.hyd.goal) en.hyd.n=en.hyd.goal; save(); paintDash(); };
  var gu=q('wlGoalUp'); if(gu) gu.onclick=function(){ var en=entry(ds); en.hyd.goal=Math.min(16,en.hyd.goal+1); save(); paintDash(); };
  /* trackers */
  p.querySelectorAll('#wlTrackers .wl-tracker').forEach(function(tr){
    tr.onclick=function(){ var en=entry(ds), k=tr.dataset.tr; en.trackers[k]=!en.trackers[k]; save(); paintDash('[data-tr="'+k+'"]'); };
  });
  /* articles */
  p.querySelectorAll('.wl-article').forEach(function(a){
    a.onclick=function(){ a.classList.toggle('open'); };
  });
  /* notes */
  var na=q('wlNoteAdd');
  if(na) na.onclick=function(){
    var tx=q('wlNoteTxt').value.trim(); if(!tx){ ui().toast(t('wel.noteNeed')); return; }
    W.notes.push({id:'n'+Date.now(),at:Date.now(),text:tx}); save(); ui().toast(t('wel.noteSaved')); paintDash();
  };
  p.querySelectorAll('[data-ndel]').forEach(function(b){
    b.onclick=function(){ W.notes=(W.notes||[]).filter(function(n){ return n.id!==b.dataset.ndel; }); save(); paintDash(); };
  });
  /* history drill-down */
  p.querySelectorAll('[data-hid]').forEach(function(b){
    b.onclick=function(){
      var hid=b.dataset.hid, c=null;
      if(hid==='cur') c={start:W.lastPeriodStart,end:W.lastPeriodEnd||'',current:true,id:'cur'};
      else (W.periodHistory||[]).forEach(function(h){ if(h.id===hid) c=h; });
      if(c&&c.start) cycleDetailSheet(c);
    };
  });
  /* reminder toggles */
  p.querySelectorAll('[data-rem]').forEach(function(tg){
    tg.onclick=function(){ var k=tg.dataset.rem; W.reminders[k]=!W.reminders[k]; save(); paintDash(); };
  });
  /* privacy */
  var bio=q('wlBioBtn');
  if(bio) bio.onclick=function(){
    if(W.lockBio){ W.lockBio=false; save(); paintDash(); return; }
    bioSupported(function(ok){
      if(!ok){ ui().toast(t('wel.lockBioUnsup')); return; }
      bioEnroll(function(done){ if(done){ ui().toast(t('wel.saved')); } else ui().toast(t('wel.unlockFail')); paintDash(); });
    });
  };
  var ht=q('wlHideTgl'); if(ht) ht.onclick=function(){ W.hideCard=!W.hideCard; save(); paintDash(); refreshCard(); };
  var ex=q('wlExport');
  if(ex) ex.onclick=function(){
    try{
      var blob=new Blob([JSON.stringify(W,null,2)],{type:'application/json'});
      var a=document.createElement('a'); a.href=URL.createObjectURL(blob);
      a.download='wellness-export.json'; document.body.appendChild(a); a.click();
      setTimeout(function(){ try{URL.revokeObjectURL(a.href);}catch(e){} a.remove(); },600);
      ui().toast(t('wel.exported'));
    }catch(e){ ui().toast(t('wel.exportFail')); }
  };
  var del=q('wlDelete');
  if(del) del.onclick=function(){
    ui().openSheet('<h2>⚠️ '+esc(t('wel.delete'))+'</h2><p class="sub">'+esc(t('wel.delQ'))+'</p>'
      +'<div class="row" style="gap:8px"><button class="btn btn-ghost" data-close style="flex:1">'+esc(t('wel.no'))+'</button>'
      +'<button class="btn btn-dark" id="wlDelYes" style="flex:1">'+esc(t('wel.yes'))+'</button></div>');
    document.getElementById('wlDelYes').onclick=function(){
      var keepHide=false;
      wipe(); ui().closeSheet(); ui().toast(t('wel.deleted')); paintDash(); refreshCard();
    };
  };
  var tt=q('wlTrackTgl');
  if(tt) tt.onclick=function(){
    if(W.enabled){ W.enabled=false; save(); }
    else{
      ui().openSheet('<h2>'+ic('heart')+' '+esc(t('wel.turnOn'))+'</h2><p class="sub">'+esc(t('wel.offQ'))+'</p>'
        +'<div class="row" style="gap:8px"><button class="btn btn-ghost" data-close style="flex:1">'+esc(t('wel.no'))+'</button>'
        +'<button class="btn wl-btn wl-shimmer" id="wlOnYes" style="flex:1">'+esc(t('wel.yes'))+'</button></div>');
      document.getElementById('wlOnYes').onclick=function(){ W.enabled=true; save(); ui().closeSheet(); paintDash(); refreshCard(); };
      return;
    }
    paintDash(); refreshCard();
  };
}

HUB.wellness={
  cardHTML:cardHTML, bind:bind, bindCard:bindCard,
  openDashboard:openDash, closeDashboard:closeDash, refreshCard:refreshCard,
  /* QA hooks (no sensitive data leaves through these) */
  _access:access, _key:function(){ return KEY; }, _load:load, _est:estNext,
  _avg:avgCycle, _heavy:heavyEntry, _phase:currentPhase
};
})();
