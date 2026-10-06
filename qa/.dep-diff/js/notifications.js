/* HUB notifications center: derived HONESTLY from real local store data.
   No spam, no invented alerts — every row comes from localStorage state.
   Groups: 💰 Home / 🔄 Market / 💼 Work / 🏘️ Community / 💬 Chats.
   Priorities: high (red dot) / normal (amber dot) / low (green dot).
   Unread logic (kept simple, documented):
     unreadNow = intrinsic-unread flag (e.g. chat threads with unread
     messages) OR the item's ts is newer than prefs.lastSeenNotifications.
     Items the user dismissed via prefs.dismissedNotifications are excluded
     entirely. "Mark all read" stamps prefs.lastSeenNotifications = now. */
(function(){
'use strict';
const {store,ui}=HUB;

const ROOT_ID='hubNotifRoot';
const NOTIF_CAP=15;
const PRIO_ORDER={high:0,normal:1,low:2};
const PRIO_COLOR={high:'#DC2626',normal:'#D97706',low:'#16A34A'};
const SYSTEMS=[
  {key:'trust',  label:'🛡️ Safety'},
  {key:'home',   label:'💰 Home'},
  {key:'market', label:'🔄 Market'},
  {key:'work',   label:'💼 Work'},
  {key:'campus', label:'🏘️ Community'},
  {key:'chats',  label:'💬 Chats'}
];
const DAY=86400e3;

function prefs(){
  const p=store.state.prefs=store.state.prefs||{};
  if(typeof p.lastSeenNotifications!=='number') p.lastSeenNotifications=0;
  if(!Array.isArray(p.dismissedNotifications)) p.dismissedNotifications=[];
  return p;
}
function lastSeen(){ return prefs().lastSeenNotifications; }

/* ---- build the honest notification list ---- */
function build(){
  const st=store.state, seen=lastSeen(), dismissed=new Set(prefs().dismissedNotifications);
  const out=[];
  const push=n=>{
    if(dismissed.has(n.nid)) return;
    n.unreadNow=!!n.intrinsic || (n.ts||0)>seen;
    out.push(n);
  };

  // 💬 Chats — high: real unread messages (intrinsic unread state)
  const unread=store.unreadCount();
  if(unread>0) push({nid:'chats-unread', system:'chats', prio:'high', emoji:'💬',
    title:unread+' unread message'+(unread>1?'s':''), sub:'Tap to open chats',
    tab:'chats', ts:0, intrinsic:true});

  // 🛡️ Trust — high: open reports still in local moderation queue
  const openReports=(st.reports||[]).filter(r=>!r.resolved);
  if(openReports.length) push({nid:'reports-open', system:'trust', prio:'high', emoji:'🛡️',
    title:openReports.length+' open report'+(openReports.length===1?'':'s')+' to review',
    sub:'Stored locally (demo) · tap to review', tab:'groups', trustReview:true, ts:0});

  // 💰 Home — high: the bill the household view flags as due this period
  const owed=store.householdOwed();
  if(owed.billDue) push({nid:'bill-'+owed.billDue.id, system:'home', prio:'high', emoji:'🧾',
    title:'Bill due: '+owed.billDue.item+' · '+ui.fmt$(owed.billDue.amount),
    sub:'Paid by '+(owed.billDue.paidBy||'someone')+' · due '+(owed.billDue.due||'—'),
    tab:'groups', ts:0});

  // 🔄 Market — normal: listings added in the last 7 days
  const freshL=(st.listings||[]).filter(l=>Date.now()-(l.createdAt||0)<7*DAY);
  if(freshL.length){
    const newest=freshL.reduce((a,b)=>(b.createdAt||0)>(a.createdAt||0)?b:a);
    push({nid:'market-new', system:'market', prio:'normal', emoji:'🆕',
      title:freshL.length+' new marketplace listing'+(freshL.length>1?'s':''),
      sub:'Latest: '+newest.title, tab:'market', ts:newest.createdAt||0, sample:newest.sample});
  }

  // 💼 Work — normal: open jobs count
  const open=(st.jobs||[]).filter(j=>j.status==='open');
  if(open.length){
    const newest=open.reduce((a,b)=>(b.createdAt||0)>(a.createdAt||0)?b:a);
    push({nid:'work-open', system:'work', prio:'normal', emoji:'💼',
      title:open.length+' open job'+(open.length>1?'s':'')+' near you',
      sub:'Top pay: '+ui.fmt$(Math.max.apply(null,open.map(j=>j.pay||0))), tab:'work',
      ts:newest.createdAt||0});
  }

  // 🏘️ Community — low: events whose time starts with 'Today'
  const todayEv=(st.events||[]).filter(e=>String(e.time||'').indexOf('Today')===0);
  if(todayEv.length) push({nid:'campus-today', system:'campus', prio:'low', emoji:'🎉',
    title:todayEv.length+' event'+(todayEv.length>1?'s':'')+' today',
    sub:todayEv.slice(0,2).map(e=>e.title).join(' · '), tab:'discover', ts:0,
    sample:todayEv.every(e=>e.sample)});

  // 🏘️ Community — low: memory items expiring within 30 days
  (st.memory||[]).filter(m=>m.expiry && (m.expiry-Date.now())>0 && (m.expiry-Date.now())<30*DAY)
    .slice(0,3).forEach(m=>{
      const days=Math.ceil((m.expiry-Date.now())/DAY);
      push({nid:'mem-exp-'+m.id, system:'campus', prio:'low', emoji:'⏳',
        title:'Expiring soon: '+m.title, sub:days+' day'+(days>1?'s':'')+' left',
        tab:'me', ts:0, sample:m.sample});
    });

  out.sort((a,b)=>(PRIO_ORDER[a.prio]-PRIO_ORDER[b.prio])||((b.ts||0)-(a.ts||0)));
  return out.slice(0,NOTIF_CAP);
}

function unreadCount(){ return build().filter(n=>n.unreadNow).length; }

/* ---- overlay ---- */
function prioDot(prio){
  return '<span title="'+prio+' priority" style="display:inline-block;width:9px;height:9px;'+
    'border-radius:50%;background:'+PRIO_COLOR[prio]+';flex:0 0 auto"></span>';
}
function rowHTML(n){
  return '<div class="item" data-tab="'+ui.esc(n.tab)+'" data-nid="'+ui.esc(n.nid)+'" style="cursor:pointer" role="button" tabindex="0">'+
    '<div style="font-size:26px;flex:0 0 auto">'+ui.esc(n.emoji)+'</div>'+
    '<div class="grow">'+
      '<h3 style="display:flex;align-items:center;gap:7px">'+prioDot(n.prio)+'<span>'+ui.esc(n.title)+'</span></h3>'+
      '<div class="meta">'+ui.esc(n.sub)+'</div>'+
    '</div>'+
    '<div style="flex:0 0 auto;display:flex;gap:6px;align-items:center">'+
      (n.sample?ui.sampleBadge(n.sample):'')+
      (n.unreadNow?'<span class="unread">●</span>':'')+
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
  ['search','pulse'].forEach(k=>{ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
  try{ if(HUB.chat&&HUB.chat.close) HUB.chat.close(); }catch(e){}
  const app=document.getElementById('app')||document.body;
  const notifs=build();
  const d=document.createElement('div');
  d.className='chatroot'; d.id=ROOT_ID;
  d.innerHTML=
    '<div class="chatpanel" style="height:92%">'+
      '<div class="chathead">'+
        '<div class="grow"><h2 style="margin:0">'+HUB.icons.icon('ic-bell')+' Notifications</h2></div>'+
        '<button class="btn btn-ghost btn-sm" id="hubNotifRead">Mark all read</button>'+
        '<button class="iconbtn" id="hubNotifClose" aria-label="Close notifications">✕</button>'+
      '</div>'+
      '<div id="hubNotifRows" style="flex:1;overflow-y:auto;padding:12px 14px"></div>'+
    '</div>';
  app.appendChild(d);
  d.addEventListener('click',e=>{ if(e.target===d) close(); });
  document.getElementById('hubNotifClose').onclick=close;
  document.getElementById('hubNotifRead').onclick=()=>{
    prefs().lastSeenNotifications=Date.now(); store.save();
    ui.toast('All caught up ✓'); open(); // rebuild to refresh unread dots
  };
  document.addEventListener('keydown',onKey);

  const host=document.getElementById('hubNotifRows');
  if(!notifs.length){
    host.innerHTML='<div class="empty"><div class="big">🔕</div><p>All quiet. No notifications from your Orbit activity.</p></div>';
    return;
  }
  host.innerHTML=SYSTEMS.map(s=>{
    const rows=notifs.filter(n=>n.system===s.key);
    if(!rows.length) return '';
    return '<h3 style="margin:14px 0 8px">'+ui.esc(s.label)+'</h3>'+rows.map(rowHTML).join('');
  }).join('');
  host.querySelectorAll('.item').forEach(el=>{
    const go=()=>{
      const notif=notifs.find(x=>x.nid===el.dataset.nid);
      if(notif&&notif.trustReview){ close(); if(HUB.trust&&HUB.trust.moderationQueue) HUB.trust.moderationQueue(); else ui.toast('Trust tools are not ready yet'); return; }
      goto(el.dataset.tab);
    };
    el.onclick=go;
    el.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); } };
  });
}

HUB.notifications={open:open, close:close, unreadCount:unreadCount};
})();
