/* HUB Pulse: live activity feed derived from REAL store timestamps.
   Newest first, capped at 20. No fake activity — if there's no data, the
   empty state invites the user to post first. Sample-seeded items keep
   their Sample badge. Nothing here is labeled AI. */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };

const ROOT_ID='hubPulseRoot';
const FEED_CAP=20;

function threadName(th){ return (th&&th.title)||t('chat.title'); }
function lastMsg(th){ return (th.messages&&th.messages.length)?th.messages[th.messages.length-1]:null; }
function preview(th){
  const m=lastMsg(th);
  if(!m) return t('pulse.m.noMessages');
  return (m.from==='me'?t('chat.youPrefix'):'')+String(m.text||'');
}

/* ---- build the feed from real timestamps ----
   Note: bills carry no createdAt in the store schema, so "bills added" is
   honestly omitted here. If a createdAt is ever added to bill objects,
   push them below the same way listings are handled. */
function buildFeed(){
  const st=store.state, items=[];
  (st.listings||[]).forEach(l=>items.push({
    ts:l.createdAt||0, emoji:'📝', tag:t('pulse.tag.market'), tab:'market',
    title:l.title, meta:t('pulse.m.newListing'), sample:l.sample
  }));
  (st.jobs||[]).forEach(j=>items.push({
    ts:j.createdAt||0, emoji:'💼', tag:t('pulse.tag.work'), tab:'work',
    title:j.title, meta:t('pulse.m.newJob',{p:ui.fmt$(j.pay),s:(j.status||'open')}), sample:j.sample
  }));
  (st.campusPosts||[]).forEach(p=>items.push({
    ts:p.at||0, emoji:'🏘️', tag:t('pulse.tag.community'), tab:'groups',
    title:p.author, meta:String(p.text||'').slice(0,90), sample:p.sample
  }));
  (st.memory||[]).forEach(m=>items.push({
    ts:m.createdAt||0, emoji:'🧠', tag:t('pulse.tag.vault'), tab:'me',
    title:m.title, meta:t('pulse.m.vault'), sample:m.sample
  }));
  (st.threads||[]).forEach(th=>{
    const m=lastMsg(th); if(!m) return;
    items.push({
      ts:m.at||0, emoji:'💬', tag:t('pulse.tag.chats'), tab:'chats',
      title:threadName(th), meta:String(preview(th)).slice(0,90),
      sample:th.sample, unread:th.unread||0
    });
  });
  // Events "starting soon": any event whose time starts with 'Today'.
  // No timestamp exists for events, so we surface the event's own time
  // string honestly (never timeAgo) and sort them as happening-now.
  (st.events||[]).filter(e=>String(e.time||'').indexOf('Today')===0).forEach(e=>items.push({
    ts:Date.now(), emoji:e.emoji||'🎉', tag:t('pulse.tag.community'), tab:'daily',
    title:e.title, meta:(e.where||''), sample:e.sample, fixedTime:e.time,
    evId:e.id
  }));
  items.sort((a,b)=>(b.ts||0)-(a.ts||0));
  return items.slice(0,FEED_CAP);
}

function tagPill(tag){
  return '<span style="font-size:10px;font-weight:800;color:var(--muted);background:var(--surface2);'+
    'border-radius:999px;padding:4px 9px;text-transform:uppercase;letter-spacing:.5px;flex:0 0 auto">'+
    ui.esc(tag)+'</span>';
}

/* Crystal-clear glassmorphic row: layered translucency, volt-tinted art
   tile, subtle depth — the same premium language as the job cards. */
function rowHTML(it){
  const when=it.fixedTime?ui.esc(it.fixedTime):ui.esc(ui.timeAgo(it.ts));
  return '<div class="prow" data-tab="'+ui.esc(it.tab)+'"'+(it.evId?' data-ev="'+ui.esc(it.evId)+'"':'')+' role="button" tabindex="0">'+
    '<div class="prow-art" aria-hidden="true">'+ui.esc(it.emoji)+'</div>'+
    '<div class="grow">'+
      '<h3>'+ui.esc(it.title)+'</h3>'+
      '<div class="meta" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+ui.esc(it.meta)+'</div>'+
      '<div style="display:flex;gap:6px;margin-top:7px;flex-wrap:wrap;align-items:center">'+
        tagPill(it.tag)+
        (it.sample?ui.sampleBadge(it.sample):'')+
        (it.unread?'<span class="unread">'+ui.esc(String(it.unread))+'</span>':'')+
      '</div>'+
    '</div>'+
    '<div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex:0 0 auto">'+
      '<span class="hint">'+when+'</span>'+
      '<span style="font-size:18px;color:var(--faint)">›</span>'+
    '</div>'+
  '</div>';
}

function ensureClosed(){
  const old=document.getElementById(ROOT_ID);
  if(old) old.remove();
  document.removeEventListener('keydown',onKey);
}
function close(){ ensureClosed(); }
function onKey(e){
  if(e.key!=='Escape') return;
  const sh=document.getElementById('sheetHost');
  if(sh&&!sh.hidden) return; /* a sheet above us owns this Escape (the global handler closes it) */
  close();
}
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
        '<div class="grow"><h2 style="margin:0">'+HUB.icons.icon('ic-pulse')+' '+t('pulse.title')+'</h2><div class="sub">'+t('pulse.sub')+'</div></div>'+
        '<button class="iconbtn" id="hubPulseClose" aria-label="'+ui.esc(t('pulse.closeAria'))+'">✕</button>'+
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
      '<p style="margin-bottom:16px">'+t('pulse.empty')+'</p>'+
      '<button class="btn btn-primary" id="hubPulsePost">'+t('pulse.post')+'</button></div>';
    document.getElementById('hubPulsePost').onclick=()=>goto('market');
    return;
  }
  host.innerHTML=feed.map(rowHTML).join('');
  host.querySelectorAll('.prow').forEach(el=>{
    const go=()=>{
      /* event rows open the full detail sheet (same one Home/Daily use);
         every other row keeps its existing destination */
      if(el.dataset.ev&&HUB.views&&HUB.views.daily&&HUB.views.daily.openEventSheet){
        close();
        HUB.views.daily.openEventSheet(el.dataset.ev);
        return;
      }
      goto(el.dataset.tab);
    };
    el.onclick=go;
    el.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); } };
  });
}

HUB.pulse={open:open, close:close};
})();
