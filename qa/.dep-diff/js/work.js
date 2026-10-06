/* HUB Work tab: micro-jobs board.
   Post a job -> open jobs; Accept -> accepted by you; Mark done -> done,
   profile.jobsDone increments. Payments are never faked in-app —
   settle outside Orbit. */
(function(){
'use strict';
let filter='all'; // 'all' | 'open' | 'accepted' | 'done'
let hostEl=null;

const FILTERS=[
  {id:'all',label:'All'},
  {id:'open',label:'Open'},
  {id:'accepted',label:'Accepted'},
  {id:'done',label:'Done'},
];

function statusBadge(j){
  if(j.status==='done') return '<span class="badge b-verified">Done</span>';
  if(j.status==='accepted') return '<span class="badge b-job">Accepted</span>';
  return '<span class="badge b-BORROW">Open</span>';
}

function jobCard(j,me){
  const {ui}=HUB;
  const mineAccepted=j.status==='accepted'&&j.acceptedBy&&j.acceptedBy===me;
  let action='';
  if(j.status==='open'){
    action='<button class="btn btn-primary btn-sm btn-block" style="margin-top:10px" data-accept="'+ui.esc(j.id)+'">Accept job</button>';
  }else if(j.status==='accepted'&&mineAccepted){
    action='<div class="row between" style="margin-top:10px"><span class="sub">✅ Accepted by you</span>'+
      '<button class="btn btn-dark btn-sm" data-done="'+ui.esc(j.id)+'">Mark done</button></div>';
  }else if(j.status==='accepted'){
    action='<div class="sub" style="margin-top:10px">🤝 Accepted by '+ui.esc(j.acceptedBy||'someone')+'</div>';
  }else{
    action='<div class="sub" style="margin-top:10px">✅ Completed'+(mineAccepted||j.acceptedBy===me?' by you':'')+'</div>';
  }
  return '<div class="card tight">'+
    '<div class="row between"><h3 style="padding-right:8px">'+ui.esc(j.title)+'</h3>'+
    '<span class="badge b-job">'+ui.esc(ui.fmt$(j.pay))+'</span></div>'+
    '<div class="sub" style="margin:6px 0;font-size:12.5px">Posted by '+ui.esc(j.poster||'someone')+' · '+ui.esc(ui.timeAgo(j.createdAt))+'</div>'+
    '<p class="sub">'+ui.esc(j.desc||'')+'</p>'+
    '<div class="row" style="gap:6px;margin-top:8px">'+statusBadge(j)+ui.sampleBadge(j.sample)+'</div>'+
    action+'</div>';
}

function openPostSheet(){
  const {ui,store}=HUB;
  ui.closeSheet();
  ['search','pulse','notifications'].forEach(k=>{ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
  ui.openSheet(
    '<h2>'+HUB.icons.icon('act-job')+' Post a job</h2>'+
    '<div class="field"><label>Title</label><input class="input" id="pjTitle" placeholder="e.g. Help me move a couch"></div>'+
    '<div class="field"><label>Pay ($)</label><input class="input" id="pjPay" type="number" min="1" step="1" placeholder="e.g. 30"></div>'+
    '<div class="field"><label>Description</label><textarea class="textarea" id="pjDesc" placeholder="What, where, how long…"></textarea></div>'+
    '<button class="btn btn-primary btn-block" id="pjGo">Post job</button>'+
    '<p class="hint">Posted jobs are real local entries. Payment is settled outside Orbit.</p>'
  );
  document.getElementById('pjGo').onclick=()=>{
    const title=document.getElementById('pjTitle').value.trim();
    const pay=Number(document.getElementById('pjPay').value);
    const desc=document.getElementById('pjDesc').value.trim();
    if(!title){ui.toast('Give the job a title');return;}
    if(!pay||!isFinite(pay)||pay<=0){ui.toast('Enter a pay amount over $0');return;}
    store.add('jobs',{title:title,pay:Math.round(pay*100)/100,desc:desc||'No description yet.',poster:store.myName(),status:'open',acceptedBy:null});
    ui.closeSheet();ui.toast('Job posted ✅');render(hostEl);
  };
}

function acceptJob(id){
  const {store,ui}=HUB;
  const j=store.find('jobs',id);
  if(!j||j.status!=='open'){ui.toast('That job is no longer open');render(hostEl);return;}
  const me=store.myName();
  if(j.poster===me){ui.toast("That's your own job 🙂");return;}
  j.status='accepted';j.acceptedBy=me;store.save();
  ui.toast('Job accepted — good luck! 💪');render(hostEl);
}

function markDone(id){
  const {store,ui}=HUB;
  const j=store.find('jobs',id);
  if(!j||j.status!=='accepted'||j.acceptedBy!==store.myName()){ui.toast('Only the accepter can mark this done');render(hostEl);return;}
  j.status='done';
  store.state.profile.jobsDone=(store.state.profile.jobsDone||0)+1;
  store.save();
  ui.toast('+1 reputation ⭐');render(hostEl);
}

function render(el){
  hostEl=el;
  const {store,ui}=HUB, st=store.state, me=store.myName(), p=st.profile;
  const chips=FILTERS.map(f=>'<button class="chip'+(filter===f.id?' on':'')+'" data-f="'+f.id+'">'+f.label+'</button>').join('');
  const jobs=st.jobs.filter(j=>!ui.isBlocked(j.poster)).filter(j=>filter==='all'||j.status===filter);
  let body;
  if(jobs.length) body=jobs.map(j=>jobCard(j,me)).join('');
  else body='<div class="empty"><div class="big">💼</div><p>No '+(filter==='all'?'':filter+' ')+'jobs yet.'+(filter!=='open'&&filter!=='all'?'':' Be the first to post one!')+'</p></div>';
  el.innerHTML=
    '<div class="row between" style="margin-bottom:4px"><h1>Micro-jobs</h1>'+
    '<span class="sub"><span class="stars">'+ui.esc(ui.stars(p.stars||0))+'</span> · '+ui.esc(String(p.jobsDone||0))+' done</span></div>'+
    '<p class="sub" style="margin-bottom:12px">Quick gigs around your community. Accept a job, get it done, build your reputation.</p>'+
    '<button class="btn btn-primary btn-block" id="postJobBtn" style="margin-bottom:12px">＋ Post a job</button>'+
    '<div class="chips">'+chips+'</div>'+
    '<div id="jobList">'+body+'</div>';
  document.getElementById('postJobBtn').onclick=openPostSheet;
  el.querySelectorAll('.chip').forEach(b=>{b.onclick=()=>{filter=b.dataset.f;render(hostEl);};});
  el.querySelectorAll('[data-accept]').forEach(b=>{b.onclick=()=>acceptJob(b.dataset.accept);});
  el.querySelectorAll('[data-done]').forEach(b=>{b.onclick=()=>markDone(b.dataset.done);});
}

HUB.views=HUB.views||{};
HUB.views.work={render:render};
})();
