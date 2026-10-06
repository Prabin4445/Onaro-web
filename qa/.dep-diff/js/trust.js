/* HUB trust & safety: reports, blocking, safe-meetup guidance, reputation,
   and privacy settings. All persisted to localStorage state.
   Honest: reports are stored locally (labeled as demo in the UI).
   Block filtering enforcement is the coordinator's job — this only stores. */
(function(){
'use strict';
const {store,ui}=HUB;

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
  if(!r.title) r.title=r.details||'Report';
  if(!r.kind) r.kind='Report';
});
if(store.state.prefs){
  if(typeof store.state.prefs.privacyCampus!=='boolean') store.state.prefs.privacyCampus=true;
  if(typeof store.state.prefs.privacyLocation!=='boolean') store.state.prefs.privacyLocation=false;
}

const REPORT_REASONS=['Spam','Scam','Inappropriate','Wrong info','Other'];

/* ---- reportSheet(kind, id, title) ---- */
function reportSheet(kind,id,title){
  let reason='';
  ui.openSheet(
    '<h2>🚩 Report this '+(ui.esc(kind)||'item')+'</h2>'+
    '<p class="sub" style="margin-bottom:12px">“'+ui.esc(title||'This item')+'”</p>'+
    '<div class="chips" id="repChips" style="margin-bottom:6px">'+
      REPORT_REASONS.map(r=>'<button class="chip" data-r="'+ui.esc(r)+'">'+ui.esc(r)+'</button>').join('')+
    '</div>'+
    '<div class="field"><label>Details (optional)</label>'+
    '<textarea class="textarea" id="repDetails" placeholder="What happened?"></textarea></div>'+
    '<button class="btn btn-primary btn-block" id="repSubmit">Submit report</button>'+
    '<p class="hint" style="text-align:center;margin-top:10px">(Demo: stored locally)</p>'
  );
  const chips=Array.prototype.slice.call(document.querySelectorAll('#repChips .chip'));
  chips.forEach(c=>{ c.onclick=()=>{ chips.forEach(x=>x.classList.remove('on')); c.classList.add('on'); reason=c.dataset.r; }; });
  document.getElementById('repSubmit').onclick=()=>{
    if(!reason){ ui.toast('Pick a reason first'); return; }
    store.state.reports.push({id:store.uid(), kind:kind||'item', refId:id||null,
      title:title||'Report', reason:reason,
      details:String(document.getElementById('repDetails').value||'').trim(),
      at:Date.now(), resolved:false, sample:false});
    store.save(); ui.closeSheet();
    ui.toast('Thanks — report saved. Our team reviews every report.');
  };
}

/* ---- blockUser(name): confirm sheet, then store the block ---- */
function blockUser(name){
  const label=name||'this user';
  ui.openSheet(
    '<h2>Block '+ui.esc(label)+'?</h2>'+
    '<p class="sub" style="margin-bottom:16px">You will no longer see their listings, jobs, posts or messages. You can unblock them later in settings.</p>'+
    '<div class="grid2">'+
      '<button class="btn btn-ghost" id="blkCancel">Cancel</button>'+
      '<button class="btn btn-primary" id="blkGo" style="background:var(--danger)">Block</button>'+
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
    ui.toast("Blocked. You won't see their content.");
  };
}

/* ---- safeMeetupHTML(): honest safety guidance ---- */
function safeMeetupHTML(){
  const tips=[
    ['🏟️','Meet in a public place','Cafes, community centers or police-station swap zones. Never a private home.'],
    ['👯','Bring a friend','Or share your live location with someone you trust.'],
    ['☀️','Meet in daylight','Daytime public meetups are the safest option.'],
    ['📍','Tell someone your plan','Who you are meeting, where, and when you expect to be back.'],
    ['📱','Keep your phone charged','And keep your own transport or fare money handy.'],
    ['🚩','Trust your instincts','If something feels off, walk away. No deal is worth the risk.']
  ];
  return '<div class="card"><h3 style="margin-bottom:10px">🛡️ Safe meetup tips</h3>'+
    tips.map(t=>'<div class="row" style="align-items:flex-start;margin-bottom:10px">'+
      '<div style="font-size:22px;flex:0 0 auto">'+t[0]+'</div>'+
      '<div class="grow"><strong>'+t[1]+'</strong><div class="sub">'+t[2]+'</div></div></div>').join('')+
    '</div>';
}

/* ---- reputationHTML(profile): stars + jobs/exchanges row ---- */
function reputationHTML(p){
  p=p||{};
  const jobs=Number(p.jobsDone)||0, ex=Number(p.exchanges)||0;
  return '<div class="row">'+
    '<div class="avatar">'+ui.esc(ui.initials(p.name||'?'))+'</div>'+
    '<div class="grow">'+
      '<h3>'+ui.esc(p.name||'Member')+'</h3>'+
      '<div class="stars">'+ui.stars(Number(p.stars)||0)+'</div>'+
      '<div class="meta">'+jobs+' jobs done · '+ex+' exchanges'+(p.verified?' · ✓ verified':'')+'</div>'+
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
  const html=privacyRow('privacyCampus','Show my community publicly','Your community name appears on your listings and profile.')+
             privacyRow('privacyLocation','Share approximate location','Lets Orbit show your general area for nearby results.');
  setTimeout(bindPrivacyToggles,0); // run after coordinator inserts the HTML
  return html;
}
function bindPrivacyToggles(){
  document.querySelectorAll('.toggle[data-priv]').forEach(t=>{
    if(t.dataset.privBound) return; t.dataset.privBound='1';
    const flip=()=>{
      const k=t.dataset.priv, p=store.state.prefs;
      p[k]=!p[k]; store.save();
      t.classList.toggle('on',!!p[k]);
      t.setAttribute('aria-checked',p[k]?'true':'false');
      ui.toast('Privacy updated');
    };
    t.onclick=flip;
    t.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); flip(); } };
  });
}


/* ---- moderation queue: local review of reports (demo) ---- */
function moderationQueue(){
  const reps=(store.state.reports||[]);
  const open=reps.filter(r=>!r.resolved);
  const done=reps.filter(r=>r.resolved);
  const row=r=>{
    const rtitle=r.title||r.details||'Report';
    const rreason=[r.reason,r.details&&r.reason!==r.details?r.details:null].filter(Boolean).join(' · ');
    return '<div class="item"><div class="avatar" style="background:var(--surface2);font-size:18px">🚩</div>'+
    '<div class="grow"><h3>'+ui.esc(r.kind||'Report')+': '+ui.esc(rtitle)+'</h3>'+
    '<div class="meta">'+ui.esc(rreason||'—')+' · '+ui.timeAgo(r.at||Date.now())+'</div></div>'+
    (r.resolved?'<span class="badge b-verified">Resolved</span>':
      (r.id?'<button class="btn btn-sm btn-line" data-resolve="'+ui.esc(r.id)+'">Mark resolved</button>'
          :'<span class="meta">legacy</span>'))+'</div>';
  };
  let html='<h2>🛡️ Moderation queue</h2>'+
    '<p class="sub" style="margin-bottom:12px">Reports are stored locally in this demo preview — nothing leaves this browser.</p>'+
    '<h3 style="margin-bottom:8px">Open ('+open.length+')</h3>'+
    (open.length? open.map(row).join('') : '<p class="sub" style="margin-bottom:12px">No open reports. 🎉</p>')+
    (done.length? '<h3 style="margin:12px 0 8px">Resolved ('+done.length+')</h3>'+done.map(row).join('') : '');
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
