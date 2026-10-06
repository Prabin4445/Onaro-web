/* HUB ai domain: Ask Onaro — the in-app guide that knows the whole app.
   Keyword intent engine + step-by-step walkthroughs. Honestly labeled demo
   assistant — reads real local store data, no AI claims. (Upgraded 2026-09-24:
   full-app guide knowledge base + step walker per PraBin.) */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };

/* ---------- guide knowledge base ----------
   id, icon, tab (deep-link), act (direct open), keys (match words), n (steps).
   All user-facing strings live in i18n as askg.<id>.t/.d/.s1..sN. */
const GUIDE=[
  {id:'rate',   icon:'nav-prof',  tab:'home', act:'professors', n:5,
   keys:['rate','rating','professor','teacher','review','stars','stars']},
  {id:'addprof',icon:'nav-prof',  tab:'home', act:'professors', n:4,
   keys:['missing','cannot find','cant find','not listed','not there','add professor','create professor','new professor']},
  {id:'groups', icon:'nav-groups', tab:'groups', n:4,
   keys:['group','groups','join','community','club','communities']},
  {id:'chat',   icon:'nav-groups', tab:'groups', n:4,
   keys:['chat','message','messages','messaging','gif','gifs','talk','text']},
  {id:'calls',  icon:'nav-groups', tab:'groups', n:4,
   keys:['call','calls','calling','voice','mute','ring','speak','audio']},
  {id:'market', icon:'nav-market', tab:'market', n:4,
   keys:['sell','selling','buy','buying','market','marketplace','listing','swap','textbook','furniture','bike']},
  {id:'gym',    icon:'nav-daily',  tab:'daily', n:4,
   keys:['gym','workout','fitness','calorie','calories','weight','diet','protein','exercise','muscle']},
  {id:'calc',   icon:'nav-daily',  tab:'daily', n:4,
   keys:['calculator','calculate','calculation','math','graph','graphing','scientific']},
  {id:'gpa',    icon:'nav-home',   tab:'home', n:4,
   keys:['gpa','grade','grades','grading']},
  {id:'capsule',icon:'nav-daily',  tab:'daily', n:4,
   keys:['capsule','time capsule','letter','future self','future']},
  {id:'badges', icon:'nav-me',     tab:'me', n:4,
   keys:['badge','badges','premium','gold','silver','legend','specialist','new badge']},
  {id:'verify', icon:'nav-me',     tab:'me', n:4,
   keys:['verif','verified','verification']},
  {id:'settings',icon:'nav-me',    tab:'me', n:4,
   keys:['setting','settings','language','spanish','nepali','hindi','dark','light','theme','country','countries','notification','notifications']},
  {id:'events', icon:'nav-daily',  tab:'daily', n:4,
   keys:['event','events','happening','party','meetup','concert']},
];
function guideById(id){ for(let i=0;i<GUIDE.length;i++) if(GUIDE[i].id===id) return GUIDE[i]; return null; }
function guideSteps(g){
  const out=[];
  for(let i=1;i<=g.n;i++) out.push(t('askg.'+g.id+'.s'+i));
  return out;
}
/* topics that live on each tab — for "help with this page" */
const TAB_TOPICS={home:['rate','gpa'],daily:['events','gym','calc','capsule'],market:['market'],
  work:[],groups:['groups','chat','calls'],me:['badges','verify','settings']};

/* ---------- guide cards ---------- */
function topicChips(ids){
  return ids.map(id=>{ const g=guideById(id); if(!g) return '';
    return '<button class="chip" data-askq="'+ui.esc(t('askg.'+id+'.q'))+'">'+ui.esc(t('askg.'+id+'.t'))+'</button>'; }).join('');
}
function guideCard(g, related){
  const steps=guideSteps(g);
  let h='<h3>'+HUB.icons.icon(g.icon)+' '+ui.esc(t('askg.'+g.id+'.t'))+'</h3>'+
    '<p class="sub" style="margin:8px 0 10px">'+ui.esc(t('askg.'+g.id+'.d'))+'</p>'+
    '<ol class="asksteps">'+steps.map(s=>'<li>'+ui.esc(s)+'</li>').join('')+'</ol>'+
    '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px">'+
    '<button class="btn btn-dark btn-sm" data-walk="'+g.id+'">'+ui.esc(t('ask.walk'))+'</button>';
  if(g.act||g.tab) h+='<button class="btn btn-ghost btn-sm" data-takeme="'+g.id+'">'+ui.esc(t('ask.takeMe'))+'</button>';
  h+='</div>';
  if(related&&related.length)
    h+='<div class="meta" style="margin:12px 0 6px">'+ui.esc(t('ask.related'))+'</div><div class="chips">'+topicChips(related)+'</div>';
  return h;
}
function guideIndex(ids, title){
  const list=ids||GUIDE.map(g=>g.id);
  return '<h3>'+HUB.icons.icon('ask-hub')+' '+ui.esc(title||t('ask.guideTitle'))+'</h3>'+
    '<p class="sub" style="margin:8px 0 10px">'+ui.esc(t('ask.guideSub'))+'</p>'+
    '<div>'+list.map(id=>{ const g=guideById(id);
      return '<button class="askrow" data-askq="'+ui.esc(t('askg.'+id+'.q'))+'">'+
        '<span class="askrow-ico">'+HUB.icons.icon(g.icon)+'</span>'+
        '<span class="grow"><b>'+ui.esc(t('askg.'+id+'.t'))+'</b><span class="meta">'+ui.esc(t('askg.'+id+'.d'))+'</span></span>'+
        '<span aria-hidden="true">›</span></button>'; }).join('')+'</div>';
}

/* ---------- step walker ---------- */
function takeMe(g){
  ui.closeSheet();
  if(g.act==='professors'&&HUB.professors){ HUB.showTab(g.tab||'home'); HUB.professors.open(null); }
  else if(g.tab) HUB.showTab(g.tab);
}
function walkHTML(g, idx){
  const steps=guideSteps(g), i=Math.max(0,Math.min(idx,steps.length-1));
  const dots=steps.map((_,k)=>'<span class="askdot'+(k===i?' on':'')+'"></span>').join('');
  let h='<div class="askwalk"><div class="meta">'+ui.esc(t('ask.stepOf',{a:i+1,b:steps.length}))+' · '+ui.esc(t('askg.'+g.id+'.t'))+'</div>'+
    '<div class="askwalk-step"><span class="askwalk-n">'+(i+1)+'</span><span>'+ui.esc(steps[i])+'</span></div>'+
    '<div class="askwalk-dots">'+dots+'</div>'+
    '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">';
  if(i>0) h+='<button class="btn btn-ghost btn-sm" data-walkgo="'+g.id+':'+(i-1)+'">'+ui.esc(t('ask.back'))+'</button>';
  if(i<steps.length-1) h+='<button class="btn btn-dark btn-sm" data-walkgo="'+g.id+':'+(i+1)+'">'+ui.esc(t('ask.next'))+'</button>';
  else h+='<button class="btn btn-dark btn-sm" data-walkdone="'+g.id+'">'+ui.esc(t('ask.done'))+'</button>';
  if(g.act||g.tab) h+='<button class="btn btn-ghost btn-sm" data-takeme="'+g.id+'">'+ui.esc(t('ask.takeMe'))+'</button>';
  return h+'</div></div>';
}
/* wire a results card: walker nav, take-me-there, topic question chips.
   askAbout(q) is the sheet's "answer another question" callback. */
function bindWalk(root, askAbout){
  root.querySelectorAll('[data-walk]').forEach(b=>{ b.onclick=()=>{
    const g=guideById(b.dataset.walk); if(!g) return;
    const card=b.closest('.card'); if(card){ card.innerHTML=walkHTML(g,0); bindWalk(card,askAbout); }
  };});
  root.querySelectorAll('[data-walkgo]').forEach(b=>{ b.onclick=()=>{
    const p=b.dataset.walkgo.split(':'), g=guideById(p[0]); if(!g) return;
    const card=b.closest('.card'); if(card){ card.innerHTML=walkHTML(g,+p[1]||0); bindWalk(card,askAbout); }
    const sc=card&&card.closest('.sheet'); if(sc) sc.scrollTop=0;
  };});
  root.querySelectorAll('[data-walkdone]').forEach(b=>{ b.onclick=()=>{
    ui.toast(t('ask.done'));
  };});
  root.querySelectorAll('[data-takeme]').forEach(b=>{ b.onclick=()=>{
    const g=guideById(b.dataset.takeme); if(g) takeMe(g);
  };});
  if(askAbout) root.querySelectorAll('[data-askq]').forEach(b=>{ b.onclick=()=>askAbout(b.dataset.askq); });
  root.querySelectorAll('[data-askindex]').forEach(b=>{ b.onclick=()=>{
    const card=b.closest('.card'); if(card) card.innerHTML=guideIndex(null);
    if(card) bindWalk(card, askAbout);
  };});
}

/* ---------- intent engine (scored) ---------- */
function scoreGuide(s){
  let best=null, bestScore=0;
  for(const g of GUIDE){
    let sc=0;
    for(const k of g.keys){ if(k&&s.indexOf(k)>=0) sc+=(k.length>4?2:1); }
    if(sc>bestScore){ bestScore=sc; best=g; }
  }
  return bestScore>0?best:null;
}
function relatedFor(id){
  const rel={rate:['addprof','gpa'],addprof:['rate'],groups:['chat','calls'],chat:['groups','calls'],
    calls:['groups','chat'],market:['events'],gym:['calc'],calc:['gym','gpa'],gpa:['calc'],
    capsule:['badges'],badges:['verify','capsule'],verify:['badges','rate'],settings:['verify'],
    events:['groups','market']};
  return rel[id]||[];
}

function askAnswer(q){
  const s=String(q||'').toLowerCase().trim();
  /* greetings */
  if(/^(hi|hii+|hello|hey|namaste|yo)\b/.test(s)||/\b(hi|hello|hey)\b/.test(s)&&s.length<14){
    return '<h3>'+HUB.icons.icon('ask-hub')+' '+ui.esc(t('ask.hiT'))+'</h3>'+
      '<p class="sub" style="margin:8px 0 10px">'+ui.esc(t('ask.hiD'))+'</p>'+
      '<div class="chips">'+topicChips(['rate','groups','market'])+'</div>';
  }
  if(/thank|dhanyabad|shukriya/.test(s)){
    return '<h3>'+HUB.icons.icon('ask-hub')+' '+ui.esc(t('ask.thanks'))+'</h3>';
  }
  /* help with the page I'm on — checked BEFORE the generic help regex below,
     which would otherwise swallow "help with this page" via its /help/ branch */
  if(/this page|this tab|this screen|here\?|right here/.test(s)){
    let tab='home';
    try{ const a=document.querySelector('.tab.active'); if(a&&a.dataset.tab) tab=a.dataset.tab; }catch(e){}
    const ids=TAB_TOPICS[tab]||[];
    if(ids.length) return guideIndex(ids, t('ask.onThisPage'));
    return guideIndex(null);
  }
  /* ---- live-data intents (read the real store) ----
     Roommate check comes before money: "roommate bills" belongs to Households. */
  if(/roommate|rent/.test(s)){
    const hs=store.state.households;
    let html='<h3>'+HUB.icons.icon('nav-groups')+' '+t('ai.room.title')+'</h3>';
    if(!hs.length) html+='<p class="sub" style="margin-top:8px">'+t('ai.room.none')+'</p>';
    else html+=hs.map(h=>'<div style="margin-top:10px"><strong>'+ui.esc(h.name)+'</strong> '+ui.sampleBadge(h.sample)+'<div class="meta sub">'+h.members.map(ui.esc).join(' · ')+'</div>'+
      h.bills.map(b=>'<div class="kv"><span>'+ui.esc(b.item)+'</span><span>'+ui.fmt$(b.amount)+' <span class="sub">by '+ui.esc(b.paidBy)+'</span></span></div>').join('')+'</div>').join('');
    html+='<button class="btn btn-ghost btn-sm" data-goto="groups" style="margin-top:12px">'+t('ai.room.open')+'</button>';
    return html;
  }
  if(/money|owe|bill/.test(s)){
    const o=store.householdOwed();
    let bills=store.state.households.flatMap(h=>h.bills.map(b=>({h:h.name,b})));
    let html='<h3>'+HUB.icons.icon('stat-money')+' '+t('ai.money.title')+'</h3><div style="margin:8px 0 12px"><span class="money pos">'+ui.fmt$(o.owedToMe)+'</span> <span class="sub">'+t('ai.money.owed')+'</span></div>';
    if(!bills.length) html+='<p class="sub">'+t('ai.money.none')+'</p>';
    else html+='<div>'+bills.slice(0,6).map(x=>'<div class="kv"><span>'+ui.esc(x.b.item)+' <span class="sub">· '+ui.esc(x.h)+'</span></span><span>'+ui.fmt$(x.b.amount)+'</span></div>').join('')+(bills.length>6?'<p class="sub" style="margin-top:6px">'+t('ai.money.more',{n:bills.length-6})+'</p>':'')+'</div>';
    html+='<button class="btn btn-ghost btn-sm" data-goto="groups" style="margin-top:12px">'+t('ai.money.open')+'</button>';
    return html;
  }
  if(/job/.test(s)){
    const open=store.state.jobs.filter(j=>j.status==='open');
    let html='<h3>'+HUB.icons.icon('nav-work')+' '+t('ai.jobs.title')+'</h3>';
    if(!open.length) html+='<p class="sub" style="margin-top:8px">'+t('ai.jobs.none')+'</p>';
    else html+='<div style="margin-top:8px">'+open.slice(0,5).map(j=>'<div class="kv"><span>'+ui.esc(j.title)+' '+ui.sampleBadge(j.sample)+'</span><span class="money">'+ui.fmt$(j.pay)+'</span></div>').join('')+'</div>';
    html+='<button class="btn btn-primary btn-sm" data-goto="work" style="margin-top:12px">'+t('ai.jobs.see')+'</button>';
    return html;
  }
  if(/mov/.test(s)){
    return '<h3>'+t('ai.mv.title')+'</h3><p class="sub" style="margin:8px 0 12px">'+t('ai.mv.sub')+'</p>'+
      planRow('nav-home',t('ai.mv.homeT'),t('ai.mv.homeD'),'groups',t('ai.mv.homeC'))+
      planRow('nav-market',t('ai.mv.marketT'),t('ai.mv.marketD'),'market',t('ai.mv.marketC'))+
      planRow('nav-work',t('ai.mv.workT'),t('ai.mv.workD'),'work',t('ai.mv.workC'))+
      planRow('act-memory',t('ai.mv.memT'),t('ai.mv.memD'),'me',t('ai.mv.memC'))+
      planRow('nav-groups',t('ai.mv.grpT'),t('ai.mv.grpD'),'groups',t('ai.mv.grpC'))+
      planRow('nav-daily',t('ai.mv.dailyT'),t('ai.mv.dailyD'),'daily',t('ai.mv.dailyC'));
  }
  /* full guide index — guide-aware: "where is the calculator" opens the
     calculator guide instead of dumping the whole index. Runs after the
     live-data intents so "help me move" still reaches the moving plan. */
  if(/help|what can you do|guide|how to use|features|how does this|where is|where do i/.test(s)){
    const gg=scoreGuide(s);
    if(gg) return guideCard(gg, relatedFor(gg.id));
    return guideIndex(null);
  }
  /* ---- guide intents (knows the whole app) ---- */
  const g=scoreGuide(s);
  if(g) return guideCard(g, relatedFor(g.id));
  /* ---- default: point at the guide ---- */
  return '<h3>'+HUB.icons.icon('ask-hub')+' '+t('ai.d.title')+'</h3><p class="sub" style="margin:8px 0 10px">'+t('ai.d.sub')+'</p>'+
    '<div class="chips">'+topicChips(['rate','groups','market'])+'</div>'+
    '<button class="btn btn-ghost btn-sm" data-askindex="1" style="margin-top:10px">'+t('ask.guideTitle')+'</button>';
}

function planRow(icon,title,desc,tab,cta){
  return '<div class="item"><div class="grow"><h3>'+HUB.icons.icon(icon)+' '+ui.esc(title)+'</h3><div class="meta">'+ui.esc(desc)+'</div></div>'+
    '<button class="btn btn-ghost btn-sm" data-goto="'+tab+'">'+ui.esc(cta)+'</button></div>';
}

function bindGotos(root){
  root.querySelectorAll('[data-goto]').forEach(el=>{
    el.onclick=()=>HUB.showTab(el.dataset.goto);
  });
}

HUB.ai={
  answer:function(q){ return askAnswer(q); },
  bindGotos:bindGotos,
  bindWalk:bindWalk,
  guide:guideById,
  guideIndex:function(ids,title){ return guideIndex(ids||null,title); },
  guideCard:function(id){ const g=guideById(id); return g?guideCard(g,relatedFor(id)):''; },
  walkHTML:function(id,idx){ const g=guideById(id); return g?walkHTML(g,idx):''; },
  parseIntent:function(q){
    const s=String(q||'').toLowerCase();
    if(/mov/.test(s)) return 'moving';
    if(/money|owe|bill/.test(s)) return 'money';
    if(/job/.test(s)) return 'jobs';
    if(/sell/.test(s)) return 'sell';
    if(/roommate|rent/.test(s)) return 'roommate';
    if(/desk|textbook|bike|monitor|furniture|couch|lamp|buy|swap|borrow/.test(s)) return 'market';
    const g=scoreGuide(s);
    return g?('guide:'+g.id):'default';
  }
};
})();
