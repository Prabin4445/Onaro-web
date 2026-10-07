/* HUB APPOINTMENTS: one-off dated appointments (doctor visit, car service,
   anything with a date) on the Home board.
   - Stored in store.state.appointments (localStorage, browser-local).
   - Home card lists upcoming appointments soonest-first. Under 24h away
     each gets a live HH:MM:SS countdown (ticks via the shared [data-cd-ts]
     updater in classes.js); further out shows "in N days".
   - Reminder: when an appointment is <=60 min away and "remind me" is on,
     one in-app notification-center entry + toast fire (browser-local only,
     like class reminders — no push backend).
   - Add / edit / delete through a sheet. Editable any time.
   IIFE module exposing HUB.appts. */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };

const MS_MIN=60e3, MS_HOUR=3600e3, MS_DAY=86400e3, LEAD=MS_HOUR;

function ensureState(){
  const st=store.state;
  if(!Array.isArray(st.appointments)) st.appointments=[];
  if(!Array.isArray(st.apptFires)) st.apptFires=[];
}
function list(){ ensureState(); return store.state.appointments; }

/* 'YYYY-MM-DD' + 'HH:MM' -> local timestamp. */
function tsOf(a){
  const dp=(a.date||'').split('-'), tp=(a.time||'').split(':');
  if(dp.length<3||tp.length<2) return NaN;
  return new Date(+dp[0],+dp[1]-1,+dp[2],+tp[0],+(tp[1]||0),0,0).getTime();
}
function toISODate(d){
  return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
}
function upcoming(nowTs){
  nowTs=nowTs||Date.now();
  return list()
    .map(a=>({a:a,ts:tsOf(a)}))
    .filter(o=>!isNaN(o.ts)&&o.ts>nowTs)
    .sort((x,y)=>x.ts-y.ts);
}

function addAppt(o){
  ensureState();
  store.state.appointments.push({
    id:store.uid(), title:String(o.title||'').slice(0,80),
    date:o.date||'', time:o.time||'', remind:o.remind!==false,
    createdAt:Date.now()
  });
  store.save();
  try{ if(window.HUB&&HUB.emit) HUB.emit('appts:changed'); }catch(e){}
}
function updateAppt(id,o){
  ensureState();
  const a=list().find(x=>x.id===id); if(!a) return;
  a.title=String(o.title||'').slice(0,80); a.date=o.date||''; a.time=o.time||'';
  a.remind=o.remind!==false;
  /* edited time -> allow the reminder to fire again for the new slot */
  store.state.apptFires=store.state.apptFires.filter(f=>f.apptId!==id);
  store.save();
  try{ if(window.HUB&&HUB.emit) HUB.emit('appts:changed'); }catch(e){}
}
function removeAppt(id){
  ensureState();
  store.state.appointments=store.state.appointments.filter(x=>x.id!==id);
  store.state.apptFires=store.state.apptFires.filter(f=>f.apptId!==id);
  store.save();
  try{ if(window.HUB&&HUB.emit) HUB.emit('appts:changed'); }catch(e){}
}

/* Targeted card swap for the 'appts:changed' event: replaces only the
   appointments card's .hsec wrapper. No-op when Home isn't visible. */
function refreshCard(){
  try{
    var view=document.getElementById('view-home');
    if(!view||view.hidden) return false;
    var old=view.querySelector('#apptCard');
    if(!old) return false;
    var wrap=old.closest('.hsec');
    if(!wrap) return false;
    var tmp=document.createElement('div');
    tmp.innerHTML=cardHTML();
    var fresh=tmp.firstElementChild;
    if(!fresh) return false;
    wrap.replaceWith(fresh);
    return true;
  }catch(e){ return false; }
}

/* ---- reminder scheduler (browser-local, in-app only) ---- */
function pruneFires(){
  ensureState();
  const cut=Date.now()-48*3600e3;
  store.state.apptFires=store.state.apptFires.filter(f=>f.firedAt>cut);
}
function checkReminders(nowTs){
  nowTs=nowTs||Date.now();
  ensureState(); pruneFires();
  const fired=store.state.apptFires;
  let changed=false;
  for(const a of list()){
    if(!a.remind) continue;
    const ts=tsOf(a);
    if(isNaN(ts)||ts<=nowTs||ts-nowTs>LEAD) continue;
    const fid=a.id+'|'+ts;
    if(fired.some(f=>f.fid===fid)) continue;
    fired.push({fid:fid, apptId:a.id, title:a.title, ts:ts, firedAt:nowTs});
    changed=true;
    ui.toast(t('notif.apptT',{title:a.title}));
    try{ if(HUB.refreshDots) HUB.refreshDots(); }catch(e){}
  }
  if(changed) store.save();
}
/* Entries for the notification center: fired within the last 24h. */
function dueEntries(){
  ensureState(); pruneFires();
  const cut=Date.now()-24*3600e3;
  return store.state.apptFires.filter(f=>f.firedAt>cut);
}

/* ---- Home card ---- */
function rowCountdown(o,nowTs){
  const ms=o.ts-nowTs;
  if(ms<MS_DAY){
    /* live HH:MM:SS via the shared ticker (data-appt-ts branch, fmtHMS) */
    return '<span class="ctimer" data-appt-ts="'+o.ts+'">'+HUB.classes.fmtHMS(ms)+'</span>';
  }
  const n=Math.round(ms/MS_DAY);
  return '<span class="ctimer" style="font-size:15px">'+ui.esc(t('appt.inDays',{n:n}))+'</span>';
}
function cardHTML(){
  ensureState();
  const now=Date.now();
  const up=upcoming(now);
  const head='<div class="hsec-hd"><h2>'+ui.esc(t('appt.title'))+'</h2>'+
    '<button class="hsec-act" data-appt-add>'+t('appt.add')+'</button></div>';
  if(!up.length){
    return '<div class="hsec">'+head+'<div class="card" id="apptCard">'+
      '<div class="empty" style="padding:14px"><div class="big">📌</div>'+
      '<p class="sub" style="margin:4px 0 10px">'+t('appt.noneSub')+'</p></div></div></div>';
  }
  const rows=up.map(o=>{
    return '<div class="crow">'+
      '<div class="grow"><div class="csubj">'+HUB.icons.apptIcon(o.a.title)+ui.esc(o.a.title)+'</div>'+
      '<div class="meta">'+ui.esc(HUB.classes.whenLabel(o.ts,now))+'</div></div>'+
      rowCountdown(o,now)+
      '<button class="btn btn-sm btn-line" data-appt-edit="'+o.a.id+'" aria-label="'+ui.esc(t('common.edit'))+'">✎</button>'+
      '<button class="btn btn-sm btn-line" data-appt-del="'+o.a.id+'" aria-label="'+ui.esc(t('common.delete'))+'">✕</button></div>';
  }).join('');
  return '<div class="hsec">'+head+'<div class="card" id="apptCard">'+rows+'</div></div>';
}

/* ---- add / edit sheet ---- */
function formSheet(id){
  ensureState();
  const a=id? list().find(x=>x.id===id) : null;
  const d=new Date();
  const defDate=toISODate(d), defTime='10:00';
  ui.openSheet(
    '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">'+
    '<h2 style="margin:0;flex:1">📌 '+t(a?'appt.editTitle':'appt.newTitle')+'</h2>'+
    '<button class="btn ghost" data-close style="font-size:12px;padding:6px 10px">✕</button></div>'+
    '<div class="field"><label>'+t('appt.name')+'</label>'+
    '<input class="input" id="apTitle" maxlength="80" placeholder="'+ui.esc(t('appt.namePh'))+'" value="'+ui.esc(a?a.title:'')+'"></div>'+
    '<div class="grid2"><div class="field"><label>'+t('appt.date')+'</label>'+
    '<input class="input" id="apDate" type="date" value="'+ui.esc(a?a.date:defDate)+'"></div>'+
    '<div class="field"><label>'+t('appt.time')+'</label>'+
    '<input class="input" id="apTime" type="time" value="'+ui.esc(a?a.time:defTime)+'"></div></div>'+
    '<div class="kv"><span>🔔 '+t('appt.remind')+'</span>'+
    '<div class="toggle'+((!a||a.remind)?' on':'')+'" id="apRemind" role="switch" aria-checked="'+((!a||a.remind)?'true':'false')+'" tabindex="0" aria-label="'+ui.esc(t('appt.remind'))+'"></div></div>'+
    '<button class="btn btn-primary btn-block" id="apSave" style="margin-top:12px">'+t('appt.save')+'</button>'+
    (a?'<button class="btn btn-line btn-block" id="apDel" style="margin-top:8px">'+t('appt.delete')+'</button>':'')
  );
  const box=document.getElementById('sheetBox');
  const tg=box.querySelector('#apRemind');
  const flip=()=>{ const nowOn=!tg.classList.contains('on'); tg.classList.toggle('on',nowOn); tg.setAttribute('aria-checked',String(nowOn)); };
  tg.onclick=flip;
  tg.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); flip(); } };
  box.querySelector('#apSave').onclick=()=>{
    const o={
      title:box.querySelector('#apTitle').value.trim(),
      date:box.querySelector('#apDate').value,
      time:box.querySelector('#apTime').value,
      remind:tg.classList.contains('on')
    };
    if(!o.title){ ui.toast(t('appt.needTitle')); return; }
    const ts=tsOf(o);
    if(isNaN(ts)||ts<=Date.now()){ ui.toast(t('appt.needWhen')); return; }
    if(a) updateAppt(a.id,o); else addAppt(o);
    ui.toast(t('appt.saved'));
    ui.closeSheet();
    try{ if(HUB.classes) HUB.classes.refreshHome(); }catch(e){}
  };
  const del=box.querySelector('#apDel');
  if(del) del.onclick=()=>{ removeAppt(a.id); ui.toast(t('appt.deleted')); ui.closeSheet(); try{ if(HUB.classes) HUB.classes.refreshHome(); }catch(e){} };
}

/* Delegated clicks (card buttons survive re-renders). */
document.addEventListener('click',e=>{
  const add=e.target.closest('[data-appt-add]');
  if(add){ formSheet(null); return; }
  const ed=e.target.closest('[data-appt-edit]');
  if(ed){ formSheet(ed.dataset.apptEdit); return; }
  const del=e.target.closest('[data-appt-del]');
  if(del){ removeAppt(del.dataset.apptDel); ui.toast(t('appt.deleted')); try{ if(HUB.classes) HUB.classes.refreshHome(); }catch(e2){} return; }
});

HUB.appts={
  list:list, addAppt:addAppt, updateAppt:updateAppt, removeAppt:removeAppt,
  upcoming:upcoming, tsOf:tsOf, cardHTML:cardHTML, formSheet:formSheet,
  checkReminders:checkReminders, dueEntries:dueEntries, refreshCard:refreshCard
};
})();
