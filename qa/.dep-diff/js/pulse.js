/* HUB Pulse: live activity feed derived from REAL store timestamps.
   Newest first, capped at 20. No fake activity — if there's no data, the
   empty state invites the user to post first. Sample-seeded items keep
   their Sample badge. Nothing here is labeled AI. */
(function(){
'use strict';
const {store,ui}=HUB;

const ROOT_ID='hubPulseRoot';
const FEED_CAP=20;

function threadName(t){ return (t&&t.title)||'Chat'; }
function lastMsg(t){ return (t.messages&&t.messages.length)?t.messages[t.messages.length-1]:null; }
function preview(t){
  const m=lastMsg(t);
  if(!m) return 'No messages yet';
  return (m.from==='me'?'You: ':'')+String(m.text||'');
}

/* ---- build the feed from real timestamps ----
   Note: bills carry no createdAt in the store schema, so "bills added" is
   honestly omitted here. If a createdAt is ever added to bill objects,
   push them below the same way listings are handled. */
function buildFeed(){
  const st=store.state, items=[];
  (st.listings||[]).forEach(l=>items.push({
    ts:l.createdAt||0, emoji:'📝', tag:'Market', tab:'market',
    title:l.title, meta:'New marketplace listing', sample:l.sample
  }));
  (st.jobs||[]).forEach(j=>items.push({
    ts:j.createdAt||0, emoji:'💼', tag:'Work', tab:'work',
    title:j.title, meta:'New job · '+ui.fmt$(j.pay)+' · '+(j.status||'open'), sample:j.sample
  }));
  (st.campusPosts||[]).forEach(p=>items.push({
    ts:p.at||0, emoji:'🏘️', tag:'Community', tab:'discover',
    title:p.author, meta:String(p.text||'').slice(0,90), sample:p.sample
  }));
  (st.memory||[]).forEach(m=>items.push({
    ts:m.createdAt||0, emoji:'🧠', tag:'Vault', tab:'me',
    title:m.title, meta:'Saved to your memory vault', sample:m.sample
  }));
  (st.threads||[]).forEach(t=>{
    const m=lastMsg(t); if(!m) return;
    items.push({
      ts:m.at||0, emoji:'💬', tag:'Chats', tab:'chats',
      title:threadName(t), meta:String(preview(t)).slice(0,90),
      sample:t.sample, unread:t.unread||0
    });
  });
  // Events "starting soon": any event whose time starts with 'Today'.
  // No timestamp exists for events, so we surface the event's own time
  // string honestly (never timeAgo) and sort them as happening-now.
  (st.events||[]).filter(e=>String(e.time||'').indexOf('Today')===0).forEach(e=>items.push({
    ts:Date.now(), emoji:e.emoji||'🎉', tag:'Community', tab:'discover',
    title:e.title, meta:e.time+(e.where?' · '+e.where:''), sample:e.sample, fixedTime:e.time
  }));
  items.sort((a,b)=>(b.ts||0)-(a.ts||0));
  return items.slice(0,FEED_CAP);
}

function tagPill(tag){
  return '<span style="font-size:10px;font-weight:800;color:var(--muted);background:var(--surface2);'+
    'border-radius:999px;padding:4px 9px;text-transform:uppercase;letter-spacing:.5px;flex:0 0 auto">'+
    ui.esc(tag)+'</span>';
}

function rowHTML(it){
  const when=it.fixedTime?ui.esc(it.fixedTime):ui.esc(ui.timeAgo(it.ts));
  return '<div class="item" data-tab="'+ui.esc(it.tab)+'" style="cursor:pointer" role="button" tabindex="0">'+
    '<div style="font-size:26px;flex:0 0 auto">'+ui.esc(it.emoji)+'</div>'+
    '<div class="grow">'+
      '<h3>'+ui.esc(it.title)+'</h3>'+
      '<div class="meta" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+ui.esc(it.meta)+'</div>'+
    '</div>'+
    '<div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex:0 0 auto">'+
      '<span class="hint">'+when+'</span>'+
      tagPill(it.tag)+
      (it.sample?ui.sampleBadge(it.sample):'')+
      (it.unread?'<span class="unread">'+ui.esc(String(it.unread))+'</span>':'')+
    '</div>'+
  '</div>';
}

function ensureClosed(){
  const old=document.getElementById(ROOT_ID);
  if(old) old.remove();
  document.removeEventListener('keydown',onKey);
}
function close(){ ensureClosed(); }
function onKey(e){ if(e.key==='Escape') close(); }
function goto(tab){
  close();
  if(tab==='chats'){ const f=document.getElementById('chatFab'); if(f){ f.click(); return; } }
  if(HUB.showTab) HUB.showTab(tab);
}

function open(){
  ensureClosed();
  // Mutually exclusive with bottom sheets and sibling overlays: never stack.
  ui.closeSheet();
  ['search','notifications'].forEach(k=>{ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
  try{ if(HUB.chat&&HUB.chat.close) HUB.chat.close(); }catch(e){}
  const app=document.getElementById('app')||document.body;
  const feed=buildFeed();
  const d=document.createElement('div');
  d.className='chatroot'; d.id=ROOT_ID;
  d.innerHTML=
    '<div class="chatpanel" style="height:92%">'+
      '<div class="chathead">'+
        '<div class="grow"><h2 style="margin:0">'+HUB.icons.icon('ic-pulse')+' Pulse</h2><div class="sub">Live across your Orbit</div></div>'+
        '<button class="iconbtn" id="hubPulseClose" aria-label="Close pulse">✕</button>'+
      '</div>'+
      '<div id="hubPulseRows" style="flex:1;overflow-y:auto;padding:12px 14px"></div>'+
    '</div>';
  app.appendChild(d);
  d.addEventListener('click',e=>{ if(e.target===d) close(); });
  document.getElementById('hubPulseClose').onclick=close;
  document.addEventListener('keydown',onKey);
  const host=document.getElementById('hubPulseRows');
  if(!feed.length){
    host.innerHTML='<div class="empty"><div class="big">⚡</div>'+
      '<p style="margin-bottom:16px">Nothing happening yet.<br>Be the first to make some noise.</p>'+
      '<button class="btn btn-primary" id="hubPulsePost">Post in Market →</button></div>';
    document.getElementById('hubPulsePost').onclick=()=>goto('market');
    return;
  }
  host.innerHTML=feed.map(rowHTML).join('');
  host.querySelectorAll('.item').forEach(el=>{
    const go=()=>goto(el.dataset.tab);
    el.onclick=go;
    el.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); } };
  });
}

HUB.pulse={open:open, close:close};
})();
