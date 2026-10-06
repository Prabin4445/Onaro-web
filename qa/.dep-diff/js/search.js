/* HUB universal search: intent-aware search over REAL local store data.
   No fake users, no fake results — every row comes from localStorage state.
   Intent routing: events | jobs | memory | market | mixed (default).
   Sample-seeded items keep their Sample badge. Nothing here is labeled AI. */
(function(){
'use strict';
const {store,ui}=HUB;

const ROOT_ID='hubSearchRoot';
const SUGGESTIONS=[
  'things happening tonight',
  'someone to move my couch',
  'my laptop receipt'
];
const STOP=new Set(['the','a','an','to','for','of','in','on','at','with','my','me','is','are','was','were','do','does','did','someone','something','things','anyone','there','and','or','i','you','your','this','that','it','as']);
const INTENTS=[
  {mode:'events', label:'🎉 Events', tab:'discover', re:/tonight|today|happening|events?|part(?:y|ies)|gig|meetup|concert|club/i},
  {mode:'jobs',   label:'💼 Jobs',   tab:'work',     re:/\bmove\b|moving|couch|furniture|assemble|lift|carry|help me|need help|need a|someone to|extra hands/i},
  {mode:'memory', label:'🧠 Memory',  tab:'me',       re:/receipt|warranty|laptop|lease|document|contract|invoice|ticket|passport/i},
  {mode:'market', label:'🔄 Market',  tab:'market',   re:/\bbuy\b|\bsell\b|textbook|bike|monitor|\bfree\b|\bswap\b|borrow|price|cost|pickup/i},
  {mode:'report', label:'🚩 Reports', tab:'reports',  re:/report|abuse|spam|\bflag\b|harass|unsafe|moderate/i}
];

function detectIntent(q){ for(const it of INTENTS){ if(it.re.test(q)) return it; } return null; }
function tokens(q){
  return String(q).toLowerCase().split(/[^a-z0-9+]+/)
    .filter(t=>t.length>1 && !STOP.has(t));
}
function haystack(parts){ return parts.filter(Boolean).join(' ').toLowerCase(); }
function matches(text, toks){ if(!toks.length) return true; return toks.every(t=>text.indexOf(t)!==-1); }
function snippet(s,n){ s=String(s||''); return s.length>n ? s.slice(0,n-1)+'…' : s; }

/* ---- collectors: raw rows from real store data ---- */
function rowListing(l){
  return {kind:'listing', id:l.id, emoji:'🏷️', title:l.title,
    meta:(l.type||'LIST')+' · '+(l.price?ui.fmt$(l.price):'Free')+' · '+(l.campus||''),
    tab:'market', sample:l.sample,
    text:haystack([l.title,l.desc,l.type,l.seller,l.campus])};
}
function rowJob(j){
  return {kind:'job', id:j.id, emoji:'💼', title:j.title,
    meta:ui.fmt$(j.pay)+' · '+(j.poster||''),
    tab:'work', sample:j.sample,
    text:haystack([j.title,j.desc,j.poster])};
}
function rowEvent(e){
  return {kind:'event', id:e.id, emoji:e.emoji||'🎉', title:e.title,
    meta:(e.time||'')+(e.where?' · '+e.where:''),
    tab:'discover', sample:e.sample,
    text:haystack([e.title,e.time,e.where])};
}
function rowPost(p){
  return {kind:'post', id:p.id, emoji:'💬', title:p.author,
    meta:ui.timeAgo(p.at)+' · community board',
    tab:'discover', sample:p.sample, sub:p.text,
    text:haystack([p.author,p.text])};
}
function rowReport(r){
  return {kind:'report', id:r.id, emoji:'🚩', title:(r.title||'reported item'),
    meta:(r.kind||'item')+' · '+(r.reason||'')+' · '+ui.timeAgo(r.at||Date.now())+(r.resolved?' · resolved':''),
    tab:'reports', sub:r.details,
    text:haystack([r.kind,r.title,r.reason,r.details])};
}
function rowMemory(m){
  return {kind:'memory', id:m.id, emoji:'🧠', title:m.title,
    meta:(m.kind||'note')+(m.fileName?' · '+m.fileName:''),
    tab:'me', sample:m.sample, sub:m.note,
    text:haystack([m.title,m.note,m.kind,m.fileName])};
}
function searchEvents(toks){
  return store.state.events.map(rowEvent)
    .concat(store.state.campusPosts.filter(p=>!ui.isBlocked(p.author)).map(rowPost))
    .filter(r=>matches(r.text,toks));
}
function searchJobs(toks){
  return store.state.jobs.filter(j=>j.status==='open'&&!ui.isBlocked(j.poster)).map(rowJob)
    .filter(r=>matches(r.text,toks));
}
function searchMemory(toks){
  return store.state.memory.map(rowMemory).filter(r=>matches(r.text,toks));
}
function searchMarket(toks){
  return store.state.listings.filter(l=>!ui.isBlocked(l.seller)).map(rowListing).filter(r=>matches(r.text,toks));
}
function searchReports(toks){
  return (store.state.reports||[]).map(rowReport).filter(r=>matches(r.text,toks));
}

/* ---- overlay ---- */
function ensureClosed(){
  const old=document.getElementById(ROOT_ID);
  if(old) old.remove();
  document.removeEventListener('keydown',onKey);
}
function close(){ ensureClosed(); }
function onKey(e){ if(e.key==='Escape') close(); }

function rowHTML(r){
  return '<div class="item" data-tab="'+ui.esc(r.tab)+'" data-kind="'+ui.esc(r.kind)+'" data-id="'+ui.esc(r.id)+
    '" style="cursor:pointer" role="button" tabindex="0">'+
    '<div style="font-size:26px;flex:0 0 auto">'+ui.esc(r.emoji)+'</div>'+
    '<div class="grow">'+
      '<h3>'+ui.esc(r.title)+'</h3>'+
      (r.sub?'<div class="meta" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+ui.esc(snippet(r.sub,70))+'</div>':'')+
      '<div class="meta">'+ui.esc(r.meta)+'</div>'+
    '</div>'+
    '<div style="flex:0 0 auto">'+ui.sampleBadge(r.sample)+'</div>'+
  '</div>';
}
function groupHTML(label,rows){
  if(!rows.length) return '';
  return '<h3 style="margin:14px 0 8px">'+ui.esc(label)+'</h3>'+
    rows.slice(0,3).map(rowHTML).join('');
}

function render(q){
  const host=document.getElementById('hubSearchResults');
  const tag=document.getElementById('hubSearchTag');
  if(!host) return;
  q=String(q||'').trim();
  if(!q){
    if(tag) tag.innerHTML='';
    host.innerHTML='<div class="empty"><div class="big">🔍</div>'+
      '<p style="margin-bottom:14px">Search everything in your Orbit.<br>Try:</p>'+
      SUGGESTIONS.map(s=>'<button class="chip" data-q="'+ui.esc(s)+'" style="margin:0 6px 8px 0">“'+ui.esc(s)+'”</button>').join('')+
      '</div>';
    host.querySelectorAll('[data-q]').forEach(b=>{
      b.onclick=()=>{ const inp=document.getElementById('hubSearchInput'); inp.value=b.dataset.q; render(inp.value); inp.focus(); };
    });
    return;
  }
  const intent=detectIntent(q), toks=tokens(q);
  let html='';
  if(intent){
    if(tag) tag.innerHTML='<span class="badge b-event" style="margin-right:8px">'+ui.esc(intent.label)+'</span><span class="hint">intent detected</span>';
    const collectors={events:searchEvents,jobs:searchJobs,memory:searchMemory,market:searchMarket,report:searchReports};
    let rows=collectors[intent.mode](toks);
    // The intent alone already scopes the domain: if strict token matching
    // yields nothing (e.g. our own "things happening tonight" suggestion),
    // relax to all rows of that domain rather than dead-ending.
    if(!rows.length&&toks.length) rows=collectors[intent.mode]([]);
    html=rows.length
      ? rows.slice(0,12).map(rowHTML).join('')
      : '<div class="empty"><div class="big">🤷</div><p>No matches for “'+ui.esc(q)+'” in '+ui.esc(intent.label)+'.<br>Try different words.</p></div>';
  }else{
    if(tag) tag.innerHTML='<span class="hint">mixed results</span>';
    const m=searchMarket(toks), j=searchJobs(toks), e=searchEvents(toks), v=searchMemory(toks), r=searchReports(toks);
    html=groupHTML('🔄 Market',m)+groupHTML('💼 Jobs',j)+groupHTML('🎉 Events & community',e)+groupHTML('🧠 Memory vault',v)+groupHTML('🚩 Reports',r);
    if(!html) html='<div class="empty"><div class="big">🤷</div><p>No matches for “'+ui.esc(q)+'”.<br>Try different words.</p></div>';
  }
  host.innerHTML=html;
  host.querySelectorAll('.item').forEach(el=>{
    const go=()=>{
      close();
      if(el.dataset.kind==='report'){
        if(HUB.trust&&HUB.trust.moderationQueue) HUB.trust.moderationQueue();
        else ui.toast('Trust tools are not ready yet');
        return;
      }
      goto(el.dataset.tab);
    };
    el.onclick=go;
    el.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); } };
  });
}

function goto(tab){
  if(tab==='chats'){ const f=document.getElementById('chatFab'); if(f){ f.click(); return; } }
  if(HUB.showTab) HUB.showTab(tab);
}

function open(){
  ensureClosed();
  // Mutually exclusive with bottom sheets and sibling overlays: never stack.
  ui.closeSheet();
  ['pulse','notifications'].forEach(k=>{ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
  try{ if(HUB.chat&&HUB.chat.close) HUB.chat.close(); }catch(e){}
  const app=document.getElementById('app')||document.body;
  const d=document.createElement('div');
  d.className='chatroot'; d.id=ROOT_ID;
  d.innerHTML=
    '<div class="chatpanel" style="height:92%">'+
      '<div class="chathead">'+
        '<div class="grow"><h2 style="margin:0">'+HUB.icons.icon('ic-search')+' Search Orbit</h2></div>'+
        '<button class="iconbtn" id="hubSearchClose" aria-label="Close search">✕</button>'+
      '</div>'+
      '<div style="padding:12px 14px 0">'+
        '<input class="input" id="hubSearchInput" placeholder="Try “things happening tonight”…" autocomplete="off">'+
      '</div>'+
      '<div id="hubSearchTag" style="padding:8px 16px 0"></div>'+
      '<div id="hubSearchResults" style="flex:1;overflow-y:auto;padding:8px 14px 16px"></div>'+
    '</div>';
  app.appendChild(d);
  d.addEventListener('click',e=>{ if(e.target===d) close(); });
  document.getElementById('hubSearchClose').onclick=close;
  document.addEventListener('keydown',onKey);
  const inp=document.getElementById('hubSearchInput');
  inp.oninput=()=>render(inp.value);
  inp.focus();
  render('');
}

HUB.search={open:open, close:close};
})();
