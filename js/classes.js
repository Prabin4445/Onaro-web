/* HUB CLASS REMINDERS (Workstream H1): student class schedule with a live
   countdown on Home and in-app reminder notifications.
   - Schedule: subject, days of week, start/end times, room — local form,
     stored in store.state.classes (localStorage, 'hub_v1').
   - Home shows a "next class" card whose countdown is recomputed from
     Date.now() on every 15s tick (synced to the clock, no drift).
   - Reminders: browser-local only. A 15s scheduler fires once per class
     occurrence when start time minus lead time is reached: an in-app toast
     plus a notification-center entry (via HUB.notifications). No service
     workers, no push — the UI labels these honestly as in-app demo
     reminders; real push needs the production backend + FCM.
   IIFE module exposing HUB.classes. */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };

const LS_DAYS=7, MS_MIN=60e3;
let tickTimer=null;

function ensureState(){
  const st=store.state;
  if(!Array.isArray(st.classes)) st.classes=[];
  if(!Array.isArray(st.classFires)) st.classFires=[];
  if(!st.prefs) st.prefs={};
  if(typeof st.prefs.classLead!=='number') st.prefs.classLead=15;
  if(typeof st.prefs.classRemOn!=='boolean') st.prefs.classRemOn=true;
}
function list(){ ensureState(); return store.state.classes; }
/* Community members (non-students) see the same schedule engine as
   "work shifts" instead of "classes". Same countdowns, same reminders. */
function isShiftMode(){ return (store.state.profile||{}).audience==='community'; }
function locLabel(room){
  if(!room) return '';
  return isShiftMode()? ui.esc(room) : ui.esc(t('class.room',{room:room}));
}
function getLead(){ ensureState(); return store.state.prefs.classLead; }
function remOn(){ ensureState(); return store.state.prefs.classRemOn; }

function addClass(o){
  ensureState();
  store.state.classes.push({
    id:store.uid(), subject:String(o.subject||'').slice(0,60),
    room:String(o.room||'').slice(0,30),
    days:(o.days||[]).map(Number).filter(d=>d>=0&&d<7).sort(),
    start:o.start||'', end:o.end||'', sample:!!o.sample, createdAt:Date.now()
  });
  store.save();
  try{ if(window.HUB&&HUB.emit) HUB.emit('classes:changed'); }catch(e){}
}
function removeClass(id){
  ensureState();
  store.state.classes=store.state.classes.filter(c=>c.id!==id);
  store.save();
  try{ if(window.HUB&&HUB.emit) HUB.emit('classes:changed'); }catch(e){}
}
function setLead(min){ ensureState(); store.state.prefs.classLead=min; store.save(); }
function setRemOn(on){ ensureState(); store.state.prefs.classRemOn=!!on; store.save(); }

/* 'HH:MM' (24h from <input type=time>) -> '10:30 AM' */
function fmtTime(hm){
  if(!hm||hm.indexOf(':')===-1) return '';
  const parts=hm.split(':'); let h=+parts[0]; const m=parts[1]||'00';
  const ap=h>=12?'PM':'AM'; h=h%12; if(h===0) h=12;
  return h+':'+m+' '+ap;
}
/* timestamp -> '10:30 AM' */
function fmtTs(ts){
  const d=new Date(ts);
  return fmtTime(d.getHours()+':'+String(d.getMinutes()).padStart(2,'0'));
}

/* Next occurrence of ONE class at/after nowTs: {startTs,endTs} or null.
   Scans the next 8 days for the class's weekdays. */
function nextOccurrence(c,nowTs){
  if(!c.days||!c.days.length||!c.start||c.start.indexOf(':')===-1) return null;
  const sp=c.start.split(':'), sh=+sp[0], sm=+(sp[1]||0);
  const nowD=new Date(nowTs);
  for(let d=0; d<8; d++){
    const wd=(nowD.getDay()+d)%LS_DAYS;
    if(c.days.indexOf(wd)===-1) continue;
    const dt=new Date(nowD);
    dt.setDate(nowD.getDate()+d); dt.setHours(sh,sm,0,0);
    const ts=dt.getTime();
    if(ts<=nowTs) continue;
    let endTs=ts+50*MS_MIN;
    if(c.end&&c.end.indexOf(':')!==-1){
      const ep=c.end.split(':');
      const ed=new Date(dt); ed.setHours(+ep[0],+(ep[1]||0),0,0);
      if(ed.getTime()>ts) endTs=ed.getTime();
    }
    return {startTs:ts,endTs:endTs};
  }
  return null;
}
/* Next class occurrence at/after nowTs. Returns
   {cls, startTs, endTs} or null. */
function nextClass(nowTs){
  nowTs=nowTs||Date.now();
  let best=null;
  for(const c of list()){
    const occ=nextOccurrence(c,nowTs);
    if(occ&&(!best||occ.startTs<best.startTs)) best={cls:c,startTs:occ.startTs,endTs:occ.endTs};
  }
  return best;
}
/* In-session occurrence of ONE class right now: {startTs,endTs} or null. */
function sessionNow(c,nowTs){
  if(!c.days||!c.days.length||!c.start) return null;
  const wd=new Date(nowTs).getDay();
  if(c.days.indexOf(wd)===-1) return null;
  const sp=c.start.split(':'), dt=new Date(nowTs);
  dt.setHours(+sp[0],+(sp[1]||0),0,0);
  let end=dt.getTime()+50*MS_MIN;
  if(c.end&&c.end.indexOf(':')!==-1){
    const ep=c.end.split(':'); const ed=new Date(dt);
    ed.setHours(+ep[0],+(ep[1]||0),0,0);
    if(ed.getTime()>dt.getTime()) end=ed.getTime();
  }
  return (nowTs>=dt.getTime()&&nowTs<end)?{startTs:dt.getTime(),endTs:end}:null;
}
/* Class currently in session (now within [start,end)). */
function currentClass(nowTs){
  nowTs=nowTs||Date.now();
  for(const c of list()){
    const s=sessionNow(c,nowTs);
    if(s) return {cls:c,startTs:s.startTs,endTs:s.endTs};
  }
  return null;
}
/* Every class with its live/upcoming occurrence, soonest first. */
function allUpcoming(nowTs){
  nowTs=nowTs||Date.now();
  const out=[];
  for(const c of list()){
    const s=sessionNow(c,nowTs);
    if(s){ out.push({cls:c,startTs:s.startTs,endTs:s.endTs,live:true}); continue; }
    const occ=nextOccurrence(c,nowTs);
    if(occ) out.push({cls:c,startTs:occ.startTs,endTs:occ.endTs,live:false});
  }
  out.sort((a,b)=>a.startTs-b.startTs);
  return out;
}
/* ms -> human 'in 14h 52m' / 'in 3d 4h' (hours may exceed 99 for classes days away). */
function fmtFriendly(ms){
  const s=Math.max(0,Math.floor(ms/1000));
  const d=Math.floor(s/86400), h=Math.floor(s%86400/3600), m=Math.floor(s%3600/60);
  const dur=d>0? d+'d '+h+'h' : h>0? h+'h '+m+'m' : m>0? m+'m' : s+'s';
  return t('class.inAt',{t:dur});
}
/* ms -> 'HH:MM:SS' (hours may exceed 99 for classes days away). */
function fmtHMS(ms){
  const s=Math.max(0,Math.floor(ms/1000));
  const h=Math.floor(s/3600), m=Math.floor(s%3600/60), sec=s%60;
  const p=n=>String(n).padStart(2,'0');
  return p(h)+':'+p(m)+':'+p(sec);
}
/* Days-aware twin for capsule countdowns: {d, h, m, s} strings. */
function fmtDHMS(ms){
  const s=Math.max(0,Math.floor(ms/1000));
  const d=Math.floor(s/86400), h=Math.floor(s%86400/3600), m=Math.floor(s%3600/60), sec=s%60;
  const p=n=>String(n).padStart(2,'0');
  return {d:String(d), h:p(h), m:p(m), s:p(sec)};
}

function dayName(wd){ return t('class.day.'+wd); }
/* 'Today · 10:30 AM' / 'Tomorrow · …' / 'Wed · …' for an occurrence ts. */
function whenLabel(startTs, nowTs){
  nowTs=nowTs||Date.now();
  const a=new Date(nowTs), b=new Date(startTs);
  const dayA=new Date(a.getFullYear(),a.getMonth(),a.getDate()).getTime();
  const dayB=new Date(b.getFullYear(),b.getMonth(),b.getDate()).getTime();
  const diffDays=Math.round((dayB-dayA)/86400e3);
  const tm=fmtTs(startTs);
  if(diffDays<=0) return t('class.atToday',{time:tm});
  if(diffDays===1) return t('class.atTomorrow',{time:tm});
  return t('class.atDay',{day:dayName(b.getDay()),time:tm});
}
/* The live countdown line for the Home card. */
function countdownLine(nowTs){
  nowTs=nowTs||Date.now();
  const cur=currentClass(nowTs);
  if(cur) return {kind:'now', cls:cur.cls, startTs:cur.startTs,
    text:t('class.startsNow',{subject:cur.cls.subject})};
  const nx=nextClass(nowTs);
  if(!nx) return null;
  const mins=Math.max(1,Math.round((nx.startTs-nowTs)/MS_MIN));
  const key=mins>=60?'class.inHr':'class.inMin';
  const n=mins>=60?Math.floor(mins/60):mins;
  return {kind:'next', cls:nx.cls, startTs:nx.startTs,
    text:t(key,{subject:nx.cls.subject,n:n})};
}

/* ---- reminder scheduler (browser-local) ---- */
function fireKey(clsId,startTs,lead){
  const d=new Date(startTs);
  return clsId+'|'+d.getFullYear()+'-'+(d.getMonth()+1)+'-'+d.getDate()+'|'+lead;
}
function pruneFires(){
  ensureState();
  const cut=Date.now()-48*3600e3;
  store.state.classFires=store.state.classFires.filter(f=>f.firedAt>cut);
}
function checkReminders(nowTs){
  nowTs=nowTs||Date.now();
  ensureState();
  if(!remOn()) return;
  pruneFires();
  const lead=getLead(), horizon=nowTs+lead*MS_MIN;
  const fired=store.state.classFires;
  let changed=false;
  /* per-class nearest occurrence (not the global one — every class gets its reminder) */
  for(const c of list()){
    if(!c.days||!c.days.length||!c.start||c.start.indexOf(':')===-1) continue;
    const sp=c.start.split(':'), sh=+sp[0], sm=+(sp[1]||0);
    const nowD=new Date(nowTs);
    for(let d=0; d<8; d++){
      const wd=(nowD.getDay()+d)%LS_DAYS;
      if(c.days.indexOf(wd)===-1) continue;
      const dt=new Date(nowD);
      dt.setDate(nowD.getDate()+d); dt.setHours(sh,sm,0,0);
      const ts=dt.getTime();
      if(ts<=nowTs) continue;
      const fk=fireKey(c.id,ts,lead);
      if(ts<=horizon && !fired.some(f=>f.fid===fk)){
        const mins=Math.max(1,Math.ceil((ts-nowTs)/MS_MIN)); /* actual time remaining, not just the lead */
        fired.push({fid:fk, clsId:c.id, subject:c.subject, room:c.room||'',
          startTs:ts, lead:lead, mins:mins, firedAt:nowTs, sample:!!c.sample});
        changed=true;
        ui.toast(t('notif.classT',{subject:c.subject,n:mins}));
        try{ if(HUB.refreshDots) HUB.refreshDots(); }catch(e){}
      }
      break;
    }
  }
  if(changed) store.save();
}
/* Entries for the notification center: fired within the last 24h. */
function dueEntries(){
  ensureState(); pruneFires();
  const cut=Date.now()-24*3600e3;
  return store.state.classFires.filter(f=>f.firedAt>cut);
}

/* ---- Home card: every class with its own live HH:MM:SS countdown ---- */
function cardHTML(){
  ensureState();
  const classes=list();
  const shift=isShiftMode();
  const K=shift?{title:'class.shiftTitle',none:'class.shiftNone',noneSub:'class.shiftNoneSub',addCta:'class.shiftAddCta'}
               :{title:'class.allTitle',none:'class.none',noneSub:'class.noneSub',addCta:'class.addCta'};
  const head='<div class="hsec-hd"><h2>'+ui.esc(t(K.title))+'</h2>'+
    '<button class="hsec-act" data-class-manage>'+t('class.manage')+'</button></div>';
  if(!classes.length){
    return '<div class="hsec">'+head+'<div class="card ccard" id="classCard"><div class="empty" style="padding:18px 14px"><div class="big">'+(shift?'💼':'🎓')+'</div>'+
      '<h3 style="margin:6px 0 4px">'+t(K.none)+'</h3>'+
      '<p class="sub" style="margin-bottom:10px">'+t(K.noneSub)+'</p>'+
      '<button class="btn btn-primary btn-sm" data-class-manage>'+t(K.addCta)+'</button></div></div></div>';
  }
  const now=Date.now();
  const up=allUpcoming(now);
  if(!up.length){
    return '<div class="hsec">'+head+'<div class="card ccard" id="classCard">'+
      '<div class="row between"><div class="grow"><div class="meta">'+t(K.none)+'</div></div></div></div></div>';
  }
  const rows=up.map((u,i)=>{
    const room=u.cls.room?locLabel(u.cls.room)+' · ':'';
    const timer=u.live
      ? '<span class="clive">● '+ui.esc(t('class.liveNow'))+'</span>'
      : '<span class="ctimer" data-cd-ts="'+u.startTs+'">'+fmtFriendly(u.startTs-now)+'</span>';
    return '<div class="crow'+(i===0?' first':'')+'">'+
      '<div class="grow"><div class="csubj">'+(i===0?'<span class="cupnext">'+ui.esc(t('class.nextUp'))+'</span>':'')+HUB.icons.subjectIcon(u.cls.subject,shift)+ui.esc(u.cls.subject)+'</div>'+
      '<div class="meta">'+room+ui.esc(whenLabel(u.startTs,now))+'</div></div>'+
      (u.cls.sample?ui.sampleBadge(true):'')+timer+'</div>';
  }).join('');
  return '<div class="hsec">'+head+'<div class="card ccard" id="classCard">'+rows+'</div></div>';
}

/* Ticker: live HH:MM:SS countdowns every second (synced to the clock, no
   drift) + the reminder schedulers every 15s. Cheap: text updates only.
   [data-cd-ts] is generic so appointment timers tick here too. */
function updateTimers(){
  const now=Date.now();
  let expired=false;
  document.querySelectorAll('[data-cd-ts]').forEach(el=>{
    const ms=+el.getAttribute('data-cd-ts')-now;
    if(ms<=0){ expired=true; return; }
    el.textContent=fmtFriendly(ms);
  });
  /* appointment timers: live HH:MM:SS (own attribute so class chips keep
     their friendly "in 14h 52m" format) */
  document.querySelectorAll('[data-appt-ts]').forEach(el=>{
    const ms=+el.getAttribute('data-appt-ts')-now;
    if(ms<=0){ expired=true; return; }
    el.textContent=fmtHMS(ms);
  });
  /* capsule countdowns: segmented days/hrs/min/sec cells, or a compact
     single-text countdown when there are no cells */
  document.querySelectorAll('[data-capcd-ts]').forEach(el=>{
    const ms=+el.getAttribute('data-capcd-ts')-now;
    if(ms<=0){ expired=true; return; }
    const p=fmtDHMS(ms);
    if(el.querySelector('[data-cd-d]')){
      const set=(k,v)=>{ const n=el.querySelector('[data-cd-'+k+']'); if(n) n.textContent=v; };
      set('d',p.d); set('h',p.h); set('m',p.m); set('s',p.s);
    }else{
      el.textContent=p.d+'d '+p.h+':'+p.m+':'+p.s;
    }
  });
  if(expired) refreshHome(); /* a class/appointment started or a capsule unlocked -> re-render rows */
}
function startTicker(){
  stopTicker();
  let n=0;
  const tick=()=>{
    /* Countdown text only matters while the page is visible; reminders must
       still fire app-wide every 15s even in a background tab. */
    if(!document.hidden) updateTimers();
    if(n%15===0){
      try{ checkReminders(Date.now()); }catch(e){}
      try{ if(HUB.appts) HUB.appts.checkReminders(Date.now()); }catch(e){}
    }
    n++;
  };
  tick();
  tickTimer=setInterval(tick,1000);
}
function stopTicker(){ if(tickTimer){ clearInterval(tickTimer); tickTimer=null; } }

/* ---- manage sheet: form + list + lead-time picker ---- */
function dayToggles(selected){
  const sel=selected||[];
  // Sun..Sat buttons matching JS getDay()
  let h='<div class="daypicks" role="group" aria-label="'+ui.esc(t('class.days'))+'">';
  for(let d=0; d<7; d++){
    h+='<button type="button" class="daypick'+(sel.indexOf(d)!==-1?' on':'')+'" data-day="'+d+'" aria-pressed="'+(sel.indexOf(d)!==-1)+'">'+ui.esc(dayName(d))+'</button>';
  }
  return h+'</div>';
}
function manageSheet(){
  ensureState();
  const classes=list(), lead=getLead(), on=remOn();
  const shift=isShiftMode();
  const rows=classes.length? classes.map(c=>{
    const days=(c.days||[]).map(dayName).join(' ');
    const tm=fmtTime(c.start)+(c.end?' – '+fmtTime(c.end):'');
    return '<div class="item tight"><div class="grow"><h3>'+ui.esc(c.subject)+'</h3>'+
      '<div class="meta">'+ui.esc(days)+' · '+ui.esc(tm)+(c.room?' · '+locLabel(c.room):'')+'</div></div>'+
      ui.sampleBadge(c.sample)+
      '<button class="btn btn-sm btn-line" data-class-del="'+c.id+'" aria-label="'+ui.esc(t('common.delete'))+'">✕</button></div>';
  }).join('') : '<p class="sub" style="margin:4px 0 10px">'+t(shift?'class.shiftNone':'class.none')+'</p>';

  ui.openSheet(
    '<h2>'+(shift?'💼 ':'🎓 ')+t(shift?'class.shiftFormTitle':'class.formTitle')+'</h2>'+
    '<div id="classRows" style="margin:10px 0">'+rows+'</div>'+
    '<div class="divider"></div>'+
    '<h3 style="margin-bottom:8px">'+t(shift?'class.shiftAddCta':'class.addCta').replace('＋ ','')+'</h3>'+
    '<div class="field"><label>'+t(shift?'class.shiftName':'class.subject')+'</label><input class="input" id="clsSubject" placeholder="'+ui.esc(t(shift?'class.shiftNamePh':'class.subjectPh'))+'" maxlength="60"></div>'+
    '<div class="field"><label>'+t(shift?'class.shiftLocL':'class.roomL')+'</label><input class="input" id="clsRoom" placeholder="'+ui.esc(t(shift?'class.shiftLocPh':'class.roomPh'))+'" maxlength="30"></div>'+
    '<div class="field"><label>'+t('class.days')+'</label>'+dayToggles([1,2,3,4,5])+'</div>'+
    '<div class="grid2"><div class="field"><label>'+t('class.start')+'</label><input class="input" id="clsStart" type="time" value="10:00"></div>'+
    '<div class="field"><label>'+t('class.end')+'</label><input class="input" id="clsEnd" type="time" value="11:00"></div></div>'+
    '<button class="btn btn-primary btn-block" id="clsAdd">'+t('common.add')+'</button>'+
    '<div class="divider"></div>'+
    '<div class="kv"><span>'+t('class.toggle')+'</span><div class="toggle'+(on?' on':'')+'" id="clsRemToggle" role="switch" aria-checked="'+on+'" tabindex="0" aria-label="'+ui.esc(t('class.toggle'))+'"></div></div>'+
    '<h3 style="margin:10px 0 6px">'+t('class.leadTitle')+'</h3>'+
    '<div class="chips">'+[30,15,5].map(m=>'<button class="chip'+(lead===m?' on':'')+'" data-lead="'+m+'">'+ui.esc(t('class.lead'+m))+'</button>').join('')+'</div>'+
    '<p class="hint" style="margin-top:10px">🔔 '+t('class.note')+'</p>'
  );

  const box=document.getElementById('sheetBox');
  box.querySelectorAll('.daypick').forEach(b=>{
    b.onclick=()=>{ b.classList.toggle('on'); b.setAttribute('aria-pressed',String(b.classList.contains('on'))); };
  });
  box.querySelectorAll('[data-class-del]').forEach(b=>{
    b.onclick=()=>{ removeClass(b.dataset.classDel); ui.toast(t('class.removed')); manageSheet(); refreshHome(); };
  });
  box.querySelectorAll('[data-lead]').forEach(b=>{
    b.onclick=()=>{ setLead(+b.dataset.lead); manageSheet(); };
  });
  const tg=box.querySelector('#clsRemToggle');
  const flip=()=>{ const now=!tg.classList.contains('on'); tg.classList.toggle('on',now); tg.setAttribute('aria-checked',String(now)); setRemOn(now); };
  tg.onclick=flip;
  tg.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); flip(); } };
  box.querySelector('#clsAdd').onclick=()=>{
    const subject=box.querySelector('#clsSubject').value.trim();
    const room=box.querySelector('#clsRoom').value.trim();
    const days=[...box.querySelectorAll('.daypick.on')].map(b=>+b.dataset.day);
    const start=box.querySelector('#clsStart').value, end=box.querySelector('#clsEnd').value;
    if(!subject){ ui.toast(t('class.needSubject')); return; }
    if(!days.length){ ui.toast(t('class.needDays')); return; }
    if(start&&end&&end<=start){ ui.toast(t('class.needTime')); return; }
    addClass({subject:subject,room:room,days:days,start:start,end:end});
    ui.toast(t('class.added')); ui.closeSheet(); refreshHome();
  };
}
function refreshHome(){
  try{
    const el=document.getElementById('view-home');
    if(el&&HUB.views&&HUB.views.home&&!document.getElementById('view-home').hidden) HUB.views.home.render(el);
  }catch(e){}
}
/* Targeted card swap for the 'classes:changed' event: replaces only the
   "Your classes" card's .hsec wrapper, never a full Home re-render.
   Delegated [data-class-manage] clicks + the global ticker survive the swap,
   so no re-binding is needed. No-op when Home isn't visible. */
function refreshCard(){
  try{
    const view=document.getElementById('view-home');
    if(!view||view.hidden) return false;
    const old=view.querySelector('#classCard');
    if(!old) return false;
    const wrap=old.closest('.hsec');
    if(!wrap) return false;
    const tmp=document.createElement('div');
    tmp.innerHTML=cardHTML();
    const fresh=tmp.firstElementChild;
    if(!fresh) return false;
    wrap.replaceWith(fresh);
    return true;
  }catch(e){ return false; }
}

/* Delegated clicks for [data-class-manage] (Home card buttons survive re-renders). */
document.addEventListener('click',e=>{
  const b=e.target.closest('[data-class-manage]');
  if(b){ manageSheet(); }
});

HUB.classes={
  list:list, addClass:addClass, removeClass:removeClass,
  setLead:setLead, getLead:getLead, setRemOn:setRemOn, remOn:remOn,
  nextClass:nextClass, currentClass:currentClass, countdownLine:countdownLine,
  allUpcoming:allUpcoming, fmtHMS:fmtHMS, fmtDHMS:fmtDHMS, fmtFriendly:fmtFriendly, isShiftMode:isShiftMode,
  fmtTime:fmtTime, fmtTs:fmtTs, whenLabel:whenLabel,
  cardHTML:cardHTML, manageSheet:manageSheet,
  startTicker:startTicker, stopTicker:stopTicker,
  checkReminders:checkReminders, dueEntries:dueEntries, refreshHome:refreshHome, refreshCard:refreshCard
};
})();
