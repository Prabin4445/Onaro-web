/* HUB trust & safety: reports, blocking, safe-meetup guidance, reputation,
   and privacy settings. All persisted to localStorage state.
   Honest: reports are stored locally (labeled as demo in the UI).
   Block filtering enforcement is the coordinator's job — this only stores. */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };

/* ---- defensive seeds ----
   blocked[] must be plain name strings: ui.isBlocked() (store.js) and the
   ME blocked-manager both call .toLowerCase() on entries. Legacy object
   entries {name,at} from earlier builds are migrated to strings here so
   old localStorage can never throw. Reports are normalized to the single
   schema {id,kind,title,reason,details,at,resolved,sample} for the same
   reason (legacy reports may lack id/resolved/title). */
if(!Array.isArray(store.state.reports)) store.state.reports=[];
if(!Array.isArray(store.state.blocked)) store.state.blocked=[];
store.state.blocked=[...new Set(
  store.state.blocked.map(b=>typeof b==='string'?b:(b&&b.name)||'').map(s=>String(s).trim()).filter(Boolean)
)];
store.state.reports.forEach(r=>{
  if(!r.id) r.id=store.uid();
  if(typeof r.resolved!=='boolean') r.resolved=false;
  if(typeof r.sample!=='boolean') r.sample=false;
  if(!r.title) r.title=r.details||t('trust.rep.aboutDefault');
  if(!r.kind) r.kind='listing';
});
if(store.state.prefs){
  if(typeof store.state.prefs.privacyCampus!=='boolean') store.state.prefs.privacyCampus=true;
  if(typeof store.state.prefs.privacyLocation!=='boolean') store.state.prefs.privacyLocation=false;
}

const REPORT_REASONS=['trust.reason.spam','trust.reason.scam','trust.reason.inap','trust.reason.wrong','trust.reason.other'];
/* Report kinds are stored as stable English keys; display is localized. */
function kindLabel(k){ return k==='listing'?t('trust.rep.kindListing'):(k||t('trust.rep.aboutDefault')); }

/* ---- reportSheet(kind, id, title) ---- */
function reportSheet(kind,id,title){
  let reason='';
  ui.openSheet(
    '<h2>'+t('trust.rep.title',{kind:ui.esc(kindLabel(kind))})+'</h2>'+
    '<p class="sub" style="margin-bottom:12px">'+t('trust.rep.about',{title:ui.esc(title||t('trust.rep.aboutDefault'))})+'</p>'+
    '<div class="chips" id="repChips" style="margin-bottom:6px">'+
      REPORT_REASONS.map(rk=>'<button class="chip" data-r="'+ui.esc(rk)+'">'+ui.esc(t(rk))+'</button>').join('')+
    '</div>'+
    '<div class="field"><label>'+t('trust.rep.details')+'</label>'+
    '<textarea class="textarea" id="repDetails" placeholder="'+ui.esc(t('trust.rep.detailsPh'))+'"></textarea></div>'+
    '<button class="btn btn-primary btn-block" id="repSubmit">'+t('trust.rep.submit')+'</button>'+
    '<p class="hint" style="text-align:center;margin-top:10px">'+t('trust.rep.demoNote')+'</p>'
  );
  const chips=Array.prototype.slice.call(document.querySelectorAll('#repChips .chip'));
  chips.forEach(c=>{ c.onclick=()=>{ chips.forEach(x=>x.classList.remove('on')); c.classList.add('on'); reason=c.dataset.r; }; });
  document.getElementById('repSubmit').onclick=()=>{
    if(!reason){ ui.toast(t('trust.rep.needReason')); return; }
    store.state.reports.push({id:store.uid(), kind:'listing', refId:id||null,
      title:title||t('trust.rep.aboutDefault'), reason:reason,
      details:String(document.getElementById('repDetails').value||'').trim(),
      at:Date.now(), resolved:false, sample:false});
    store.save(); ui.closeSheet();
    ui.toast(t('trust.rep.saved'));
  };
}

/* ---- blockUser(name): confirm sheet, then store the block ---- */
function blockUser(name){
  const label=name||t('trust.block.userDefault');
  ui.openSheet(
    '<h2>'+t('trust.block.title',{name:ui.esc(label)})+'</h2>'+
    '<p class="sub" style="margin-bottom:16px">'+t('trust.block.sub')+'</p>'+
    '<div class="grid2">'+
      '<button class="btn btn-ghost" id="blkCancel">'+t('common.cancel')+'</button>'+
      '<button class="btn btn-primary" id="blkGo" style="background:var(--danger)">'+t('trust.block.go')+'</button>'+
    '</div>'
  );
  document.getElementById('blkCancel').onclick=ui.closeSheet;
  document.getElementById('blkGo').onclick=()=>{
    /* stored as a plain string — ui.isBlocked() and the ME blocked-manager
       both expect strings (objects threw "b.toLowerCase is not a function"). */
    const exists=store.state.blocked.some(b=>String(b).toLowerCase()===label.toLowerCase());
    if(!exists){
      store.state.blocked.push(label);
      store.save();
    }
    ui.closeSheet();
    ui.toast(t('trust.block.done'));
  };
}

/* ---- safeMeetupHTML(): honest safety guidance ---- */
function safeMeetupHTML(){
  const tips=[
    ['🏟️','trust.tip.1t','trust.tip.1d'],
    ['👯','trust.tip.2t','trust.tip.2d'],
    ['☀️','trust.tip.3t','trust.tip.3d'],
    ['📍','trust.tip.4t','trust.tip.4d'],
    ['📱','trust.tip.5t','trust.tip.5d'],
    ['🚩','trust.tip.6t','trust.tip.6d']
  ];
  return '<div class="card"><h3 style="margin-bottom:10px">'+t('trust.meetupTitle')+'</h3>'+
    tips.map(tp=>'<div class="row" style="align-items:flex-start;margin-bottom:10px">'+
      '<div style="font-size:22px;flex:0 0 auto">'+tp[0]+'</div>'+
      '<div class="grow"><strong>'+t(tp[1])+'</strong><div class="sub">'+t(tp[2])+'</div></div></div>').join('')+
    '</div>';
}

/* ---- reputationHTML(profile): stars + jobs/exchanges row ---- */
function reputationHTML(p){
  p=p||{};
  const jobs=Number(p.jobsDone)||0, ex=Number(p.exchanges)||0;
  return '<div class="row">'+
    '<div class="avatar">'+ui.esc(ui.initials(p.name||'?'))+'</div>'+
    '<div class="grow">'+
      '<h3>'+ui.esc(p.name||t('trust.rep.member'))+'</h3>'+
      '<div class="stars">'+ui.stars(Number(p.stars)||0)+'</div>'+
      '<div class="meta">'+t('trust.rep.jobsMeta',{j:jobs,e:ex})+(p.verified?t('trust.rep.verifiedSuffix'):'')+'</div>'+
    '</div>'+
  '</div>';
}

/* ---- privacySettingsHTML(): toggles bound to state.prefs ----
   Coordinator: drop this HTML into ME settings. Toggles self-bind after
   insertion (deferred by a tick so the coordinator's innerHTML can land). */
function privacyRow(key,label,desc){
  const p=store.state.prefs, on=!!p[key];
  return '<div class="item" style="cursor:default">'+
    '<div class="grow"><h3>'+ui.esc(label)+'</h3><div class="meta">'+ui.esc(desc)+'</div></div>'+
    '<div class="toggle'+(on?' on':'')+'" data-priv="'+key+'" role="switch" '+
    'aria-checked="'+(on?'true':'false')+'" aria-label="'+ui.esc(label)+'" tabindex="0"></div>'+
  '</div>';
}
function privacySettingsHTML(){
  const p=store.state.prefs=store.state.prefs||{};
  if(typeof p.privacyCampus!=='boolean') p.privacyCampus=true;
  if(typeof p.privacyLocation!=='boolean') p.privacyLocation=false;
  const html=privacyRow('privacyCampus',t('trust.priv.campus'),t('trust.priv.campusD'))+
             privacyRow('privacyLocation',t('trust.priv.loc'),t('trust.priv.locD'));
  setTimeout(bindPrivacyToggles,0); // run after coordinator inserts the HTML
  return html;
}
function bindPrivacyToggles(){
  document.querySelectorAll('.toggle[data-priv]').forEach(el=>{
    if(el.dataset.privBound) return; el.dataset.privBound='1';
    const flip=()=>{
      const k=el.dataset.priv, p=store.state.prefs;
      p[k]=!p[k]; store.save();
      el.classList.toggle('on',!!p[k]);
      el.setAttribute('aria-checked',p[k]?'true':'false');
      ui.toast(t('trust.priv.updated'));
    };
    el.onclick=flip;
    el.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); flip(); } };
  });
}


/* ---- moderation queue: local review of reports (demo) ---- */
function moderationQueue(){
  const reps=(store.state.reports||[]);
  const open=reps.filter(r=>!r.resolved);
  const done=reps.filter(r=>r.resolved);
  const row=r=>{
    const rtitle=r.title||r.details||t('trust.mq.reportItem');
    const rlabel=REPORT_REASONS.indexOf(r.reason)>=0?t(r.reason):r.reason;
    const rreason=[rlabel,r.details&&r.reason!==r.details?r.details:null].filter(Boolean).join(' · ');
    return '<div class="item"><div class="avatar" style="background:var(--surface2);font-size:18px">🚩</div>'+
    '<div class="grow"><h3>'+ui.esc(kindLabel(r.kind))+': '+ui.esc(rtitle)+'</h3>'+
    '<div class="meta">'+ui.esc(rreason||'—')+' · '+ui.timeAgo(r.at||Date.now())+'</div></div>'+
    (r.resolved?'<span class="badge b-verified">'+t('trust.mq.resolvedBadge')+'</span>':
      (r.id?'<button class="btn btn-sm btn-line" data-resolve="'+ui.esc(r.id)+'">'+t('trust.mq.resolve')+'</button>'
          :'<span class="meta">'+t('trust.mq.legacy')+'</span>'))+'</div>';
  };
  let html='<h2>'+t('trust.mq.title')+'</h2>'+
    '<p class="sub" style="margin-bottom:12px">'+t('trust.mq.sub')+'</p>'+
    '<h3 style="margin-bottom:8px">'+t('trust.mq.open',{n:open.length})+'</h3>'+
    (open.length? open.map(row).join('') : '<p class="sub" style="margin-bottom:12px">'+t('trust.mq.noneOpen')+'</p>')+
    (done.length? '<h3 style="margin:12px 0 8px">'+t('trust.mq.resolved',{n:done.length})+'</h3>'+done.map(row).join('') : '');
  ui.openSheet(html);
  document.querySelectorAll('[data-resolve]').forEach(b=>{
    b.onclick=()=>{ const r=reps.find(x=>String(x.id)===b.dataset.resolve); if(r){r.resolved=true;store.save();ui.closeSheet();moderationQueue();} };
  });
}

HUB.trust={
  reportSheet:reportSheet,
  blockUser:blockUser,
  safeMeetupHTML:safeMeetupHTML,
  reputationHTML:reputationHTML,
  privacySettingsHTML:privacySettingsHTML,
  moderationQueue:moderationQueue
};
})();
