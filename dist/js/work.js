/* HUB Work tab: micro-jobs board with a full lifecycle.
   open -> accepted (ON HOLD) -> done; accepted can be reopened to open.
   - Anyone except the poster can accept an open job (confirm sheet).
   - On accept, the job goes ON HOLD: no one else can accept.
   - Poster controls (owner only): Mark done, Reopen, Delete job.
   - The accepter can release the job back to open ("Release job").
   - Poster + accepter get a job-scoped Chat (thread id "job:<id>").
   Payments are never faked in-app — settle outside Onaro. */
(function(){
'use strict';
const t=function(k,v){ return HUB.i18n.t(k,v); };
let filter='all'; // 'all' | 'open' | 'accepted' | 'done'
let hostEl=null;

const FILTERS=[
  {id:'all',key:'work.filter.all'},
  {id:'open',key:'work.filter.open'},
  {id:'accepted',key:'work.filter.accepted'},
  {id:'done',key:'work.filter.done'},
];

function statusBadge(j){
  if(j.status==='done') return '<span class="badge b-verified">'+t('work.st.done')+'</span>';
  if(j.status==='accepted') return '<span class="badge b-onhold">'+t('work.st.onhold')+'</span>';
  return '<span class="badge b-BORROW">'+t('work.st.open')+'</span>';
}

/* Category per job card, derived from the title's keywords: drives the art
   tile emoji AND the category pill label (wrk.cat.<id>). Purely presentational
   — no new data or strings invented; titles stay exactly as posted. */
const JOB_CATS=[
  {id:'moving',re:/mov|furniture|lift|haul|box|deliver/,emoji:'📦'},
  {id:'design',re:/logo|design|art|draw|paint|photo|video/,emoji:'🎨'},
  {id:'cleaning',re:/clean|yard|lawn|garden|mow/,emoji:'🧹'},
  {id:'tutor',re:/tutor|teach|math|study|homework|lesson/,emoji:'📚'},
  {id:'pets',re:/dog|pet|cat|walk|sit\b/,emoji:'🐾'},
  {id:'car',re:/car|ride|drive|wash/,emoji:'🚗'},
  {id:'food',re:/cook|food|meal|bake/,emoji:'🍳'},
  {id:'kids',re:/baby|kid|child|nanny/,emoji:'🧸'},
  {id:'tech',re:/tech|computer|phone|fix|repair|assembl|ikea|desk|mount/,emoji:'🛠️'},
];
function jobCat(title){
  const w=(title||'').toLowerCase();
  for(const c of JOB_CATS) if(c.re.test(w)) return c;
  return {id:'other',emoji:'💼'};
}
function jobArt(title){ return jobCat(title).emoji; }

function jobCard(j,me,idx){
  const {ui}=HUB;
  const mine=ui.isMe(j.poster);
  const iAccepted=ui.isMe(j.acceptedBy||'');
  const id=ui.esc(j.id);
  const cat=jobCat(j.title);
  let action='';
  if(j.status==='open'){
    if(mine){
      /* owner: only delete makes sense while the job is still open */
      action='<div class="row" style="gap:8px;margin-top:10px"><button class="btn btn-ghost btn-sm" data-jdel="'+id+'" style="color:var(--danger)">🗑 '+t('work.delete')+'</button></div>';
    }else{
      action='<button class="btn btn-primary btn-sm btn-block wu-accept" style="margin-top:10px" data-accept="'+id+'">'+t('work.accept')+'</button>';
    }
  }else if(j.status==='accepted'){
    if(mine){
      action='<div class="sub" style="margin-top:10px">'+t('work.acceptedBy',{name:ui.esc(j.acceptedBy||t('work.someone'))})+'</div>'+
        '<div class="row wu-actions" style="gap:8px;margin-top:10px;flex-wrap:wrap">'+
          '<button class="btn btn-primary btn-sm" data-jchat="'+id+'">💬 '+t('work.chat')+'</button>'+
          '<button class="btn btn-dark btn-sm" data-done="'+id+'">'+t('work.markDone')+'</button>'+
          '<button class="btn btn-ghost btn-sm" data-reopen="'+id+'">↩ '+t('work.reopen')+'</button>'+
          '<button class="btn btn-ghost btn-sm" data-jdel="'+id+'" style="color:var(--danger)">🗑 '+t('work.delete')+'</button>'+
        '</div>';
    }else if(iAccepted){
      action='<div class="sub" style="margin-top:10px">'+t('work.acceptedByYou')+'</div>'+
        '<div class="row wu-actions" style="gap:8px;margin-top:10px;flex-wrap:wrap">'+
          '<button class="btn btn-primary btn-sm" data-jchat="'+id+'">💬 '+t('work.chat')+'</button>'+
          '<button class="btn btn-ghost btn-sm" data-release="'+id+'">↩ '+t('work.release')+'</button>'+
        '</div>';
    }else{
      /* third party: on hold, read-only */
      action='<div class="sub" style="margin-top:10px">'+t('work.acceptedBy',{name:ui.esc(j.acceptedBy||t('work.someone'))})+'</div>';
    }
  }else{ /* done */
    action='<div class="sub" style="margin-top:10px">'+(t('work.completed')+((mine||iAccepted)?t('work.completedByYou'):''))+'</div>';
    if(mine){
      action+='<div class="row" style="gap:8px;margin-top:10px"><button class="btn btn-ghost btn-sm" data-jdel="'+id+'" style="color:var(--danger)">🗑 '+t('work.delete')+'</button></div>';
    }
  }
  return '<div class="job" data-job="'+id+'" style="--i:'+(idx||0)+'">'+
    '<div class="job-art" aria-hidden="true">'+jobArt(j.title)+'</div>'+
    '<div class="job-main">'+
      '<div class="row between" style="gap:8px"><h3>'+ui.esc(j.title)+'</h3>'+
      '<span class="job-pay">'+ui.esc(ui.fmt$(j.pay))+'</span></div>'+
      '<div class="job-meta">'+t('work.postedBy',{name:ui.esc(j.poster||t('work.someone')),ago:ui.esc(ui.timeAgo(j.createdAt))})+'</div>'+
      '<p class="job-desc">'+ui.esc(j.desc||'')+'</p>'+
      '<div class="row wu-tags" style="gap:6px;flex-wrap:wrap">'+statusBadge(j)+
      '<span class="wu-cat">'+ui.esc(t('wrk.cat.'+cat.id))+'</span>'+
      ui.sampleBadge(j.sample)+'</div>'+
      action+'</div></div>';
}

function openPostSheet(){
  const {ui,store}=HUB;
  ui.closeSheet();
  ['search','pulse','notifications'].forEach(k=>{ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
  ui.openSheet(
    '<h2>'+HUB.icons.icon('act-job')+' '+t('work.p.title')+'</h2>'+
    '<div class="field"><label>'+t('work.p.titleLabel')+'</label><input class="input" id="pjTitle" placeholder="'+t('work.p.titlePh')+'"></div>'+
    '<div class="field"><label>'+t('work.p.payLabel')+'</label><input class="input" id="pjPay" type="number" min="1" step="1" placeholder="'+t('work.p.payPh')+'"></div>'+
    '<div class="field"><label>'+t('work.p.descLabel')+'</label><textarea class="textarea" id="pjDesc" placeholder="'+t('work.p.descPh')+'"></textarea></div>'+
    '<button class="btn btn-primary btn-block" id="pjGo">'+t('work.p.go')+'</button>'+
    '<p class="hint">'+t('work.p.hint')+'</p>'
  );
  document.getElementById('pjGo').onclick=()=>{
    const title=document.getElementById('pjTitle').value.trim();
    const pay=Number(document.getElementById('pjPay').value);
    const desc=document.getElementById('pjDesc').value.trim();
    if(!title){ui.toast(t('work.p.needTitle'));return;}
    if(!pay||!isFinite(pay)||pay<=0){ui.toast(t('work.p.needPay'));return;}
    store.add('jobs',{title:title,pay:Math.round(pay*100)/100,desc:desc||t('work.noDesc'),poster:store.myName(),status:'open',acceptedBy:null});
    ui.closeSheet();ui.toast(t('work.p.posted'));render(hostEl);
  };
}

/* ---------- confirm sheets ---------- */
function confirmSheet(title,sub,goLabel,goClass,goStyle,onGo){
  const {ui}=HUB;
  ui.openSheet(
    '<h2>'+ui.esc(title)+'</h2>'+
    '<p class="sub" style="margin:6px 0 14px">'+ui.esc(sub)+'</p>'+
    '<button class="btn btn-block '+goClass+'" id="cfGo"'+(goStyle?' style="'+goStyle+'"':'')+'>'+ui.esc(goLabel)+'</button>'+
    '<button class="btn btn-ghost btn-block" id="cfNo" style="margin-top:8px">'+ui.esc(t('common.cancel'))+'</button>'
  );
  document.getElementById('cfNo').onclick=ui.closeSheet;
  document.getElementById('cfGo').onclick=()=>{ ui.closeSheet(); onGo(); };
}

/* ---------- lifecycle actions ---------- */
function confirmAccept(id){
  const {store,ui}=HUB;
  const j=store.find('jobs',id);
  if(!j||j.status!=='open'){ui.toast(t('work.closed'));render(hostEl);return;}
  if(ui.isMe(j.poster)){ui.toast(t('work.ownJob'));return;}
  confirmSheet(t('work.aT'),t('work.aS'),t('work.aGo'),'btn-primary','',()=>acceptJob(id));
}
function acceptJob(id){
  const {store,ui}=HUB;
  const j=store.find('jobs',id);
  if(!j||j.status!=='open'){ui.toast(t('work.closed'));render(hostEl);return;}
  if(ui.isMe(j.poster)){ui.toast(t('work.ownJob'));return;}
  j.status='accepted';j.acceptedBy=store.myName();store.save();
  ui.toast(t('work.accepted'));render(hostEl);
}
/* Owner reopens an accepted job: back to open, acceptedBy cleared. */
function confirmReopen(id){
  const {store,ui}=HUB;
  const j=store.find('jobs',id);
  if(!j||j.status!=='accepted'||!ui.isMe(j.poster)){ui.toast(t('work.onlyOwner'));render(hostEl);return;}
  confirmSheet(t('work.rT'),t('work.rS'),t('work.rGo'),'btn-dark','',()=>{
    j.status='open';j.acceptedBy=null;store.save();
    ui.toast(t('work.reopened'));render(hostEl);
  });
}
/* Accepter releases the job: back to open, acceptedBy cleared. */
function confirmRelease(id){
  const {store,ui}=HUB;
  const j=store.find('jobs',id);
  if(!j||j.status!=='accepted'||!ui.isMe(j.acceptedBy||'')){ui.toast(t('work.onlyAccepter'));render(hostEl);return;}
  confirmSheet(t('work.relT'),t('work.relS'),t('work.relGo'),'btn-dark','',()=>{
    j.status='open';j.acceptedBy=null;store.save();
    ui.toast(t('work.released'));render(hostEl);
  });
}
/* Owner marks an accepted job done. Reputation goes to the accepter. */
function markDone(id){
  const {store,ui}=HUB;
  const j=store.find('jobs',id);
  if(!j||j.status!=='accepted'||!ui.isMe(j.poster)){ui.toast(t('work.onlyOwner'));render(hostEl);return;}
  j.status='done';
  /* reputation goes to the accepter: their person record if we have one,
     otherwise the local profile (demo fallback). */
  const acc=String(j.acceptedBy||'').trim().toLowerCase();
  const person=(store.state.people||[]).find(p=>p&&String(p.name||'').trim().toLowerCase()===acc);
  if(person) person.jobsDone=(person.jobsDone||0)+1;
  else store.state.profile.jobsDone=(store.state.profile.jobsDone||0)+1;
  store.save();
  ui.toast(t('work.rep'));render(hostEl);
}
/* Owner deletes the job entirely. */
function confirmDelete(id){
  const {store,ui}=HUB;
  const j=store.find('jobs',id);
  if(!j||!ui.isMe(j.poster)){ui.toast(t('work.onlyOwner'));render(hostEl);return;}
  confirmSheet(t('work.dT'),t('work.dS'),t('work.dGo'),'','background:#FEE2E2;color:var(--danger)',()=>{
    store.remove('jobs',id);store.save();
    ui.toast(t('work.deleted'));render(hostEl);
  });
}

/* ---------- job-scoped chat ---------- */
/* Thread id "job:<jobId>" — bypasses the mutual-only gate because it is
   scoped to a real job both parties opted into, not a cold message. */
function openJobChat(id){
  const {store,ui}=HUB;
  const j=store.find('jobs',id);
  if(!j||j.status!=='accepted'){ui.toast(t('work.closed'));render(hostEl);return;}
  const mine=ui.isMe(j.poster), iAccepted=ui.isMe(j.acceptedBy||'');
  if(!mine&&!iAccepted){ui.toast(t('work.onlyOwner'));render(hostEl);return;}
  const other=mine?(j.acceptedBy||t('work.someone')):(j.poster||t('work.someone'));
  const tid='job:'+id;
  let th=store.find('threads',tid);
  if(!th){
    store.add('threads',{id:tid,jobId:id,title:'💼 '+j.title+' · '+other,unread:0,
      messages:[{from:'sys',text:t('work.chatSeed',{title:j.title}),at:Date.now(),kind:'text'}]});
    th=store.find('threads',tid);
  }
  HUB.chat.openThread(th.id);
}

function render(el){
  hostEl=el;
  el.classList.add('wu-root'); /* work-ui.css scope hook */
  const {store,ui}=HUB, st=store.state, me=store.myName(), p=st.profile;
  const chips=FILTERS.map(f=>'<button class="chip'+(filter===f.id?' on':'')+'" data-f="'+f.id+'">'+t(f.key)+'</button>').join('');
  const jobs=st.jobs.filter(j=>!ui.isBlocked(j.poster)).filter(j=>filter==='all'||j.status===filter);
  let body;
  if(jobs.length) body=jobs.map((j,idx)=>jobCard(j,me,idx)).join('');
  else body='<div class="empty wu-empty"><div class="wu-empty-ico">'+HUB.icons.icon('hm-mod-work')+'</div><p>'+t('work.emptyF.'+filter)+(filter!=='open'&&filter!=='all'?'':' '+t('work.emptyFirst'))+'</p></div>';
  el.innerHTML=
    '<div class="wu-hero">'+
    '<div class="wu-hero-in">'+
    '<div class="wu-hero-ico">'+HUB.icons.icon('hm-mod-work')+'</div>'+
    '<div class="wu-hero-tx"><h1>'+t('wrk.title')+'</h1>'+
    '<p class="wu-hero-sub">'+t('wrk.heroSub')+'</p>'+
    '<span class="wu-rep"><span class="stars">'+ui.esc(ui.stars(p.stars||0))+'</span><span class="wu-rep-sep">·</span>'+ui.esc(String(p.jobsDone||0))+' '+t('work.doneCount')+'</span></div>'+
    '</div>'+
    '<div class="wu-gloss" aria-hidden="true"></div>'+
    '<div class="wu-motes" aria-hidden="true"><i></i><i></i><i></i><i></i></div>'+
    '</div>'+
    '<button class="btn btn-primary btn-block wu-post" id="postJobBtn" style="margin-bottom:12px">'+t('work.post')+'</button>'+
    '<div class="chips wu-chips">'+chips+'</div>'+
    '<div id="jobList" class="wu-list">'+body+'</div>';
  document.getElementById('postJobBtn').onclick=openPostSheet;
  el.querySelectorAll('.chip').forEach(b=>{b.onclick=()=>{filter=b.dataset.f;render(hostEl);};});
  el.querySelectorAll('[data-accept]').forEach(b=>{b.onclick=()=>confirmAccept(b.dataset.accept);});
  el.querySelectorAll('[data-done]').forEach(b=>{b.onclick=()=>markDone(b.dataset.done);});
  el.querySelectorAll('[data-reopen]').forEach(b=>{b.onclick=()=>confirmReopen(b.dataset.reopen);});
  el.querySelectorAll('[data-release]').forEach(b=>{b.onclick=()=>confirmRelease(b.dataset.release);});
  el.querySelectorAll('[data-jdel]').forEach(b=>{b.onclick=()=>confirmDelete(b.dataset.jdel);});
  el.querySelectorAll('[data-jchat]').forEach(b=>{b.onclick=()=>openJobChat(b.dataset.jchat);});
}

HUB.views=HUB.views||{};
HUB.views.work={render:render,openJobChat:openJobChat};
})();
