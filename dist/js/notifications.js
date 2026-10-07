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
const t=function(k,v){ return HUB.i18n.t(k,v); };

const ROOT_ID='hubNotifRoot';
const NOTIF_CAP=15;
const PRIO_ORDER={high:0,normal:1,low:2};
const PRIO_COLOR={high:'#DC2626',normal:'#D97706',low:'#16A34A'};
const SYSTEMS=[
  {key:'trust',  label:'notif.sys.trust'},
  {key:'home',   label:'notif.sys.home'},
  {key:'market', label:'notif.sys.market'},
  {key:'work',   label:'notif.sys.work'},
  {key:'campus', label:'notif.sys.campus'},
  {key:'chats',  label:'notif.sys.chats'},
  {key:'calls',  label:'notif.sys.calls'},
  {key:'people', label:'notif.sys.people'},
  {key:'badges', label:'notif.sys.badges'},
  {key:'groups', label:'cg.sys.groups'},
  {key:'calendar', label:'notif.sys.calendar'}
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
    title:t('notif.chatT',{n:unread}), sub:t('notif.chatS'),
    tab:'chats', ts:0, intrinsic:true});

  // 📞 Calls — high: missed calls recorded by the incoming-call screen.
  // Browser-local until the signaling worker exists; never faked.
  try{
    for(const m of (st.missedCalls||[]).slice(-3)){
      push({nid:'missed-'+m.ts, system:'calls', prio:'high', emoji:'📞',
        title:t('inc.missedFrom',{name:m.name||'?'}), sub:t('inc.missedSub'),
        tab:'groups', ts:m.ts||0});
    }
  }catch(e){}

  // 🛡️ Trust — high: open reports still in local moderation queue
  const openReports=(st.reports||[]).filter(r=>!r.resolved);
  if(openReports.length) push({nid:'reports-open', system:'trust', prio:'high', emoji:'🛡️',
    title:t('notif.repT',{n:openReports.length}),
    sub:t('notif.repS'), tab:'groups', trustReview:true, ts:0});

  // 💰 Home — high: the bill the household view flags as due this period
  const owed=store.householdOwed();
  if(owed.billDue) push({nid:'bill-'+owed.billDue.id, system:'home', prio:'high', emoji:'🧾',
    title:t('notif.billT',{item:owed.billDue.item,amount:ui.fmt$(owed.billDue.amount)}),
    sub:t('notif.billS',{name:(owed.billDue.paidBy||t('work.someone')),due:(owed.billDue.due||'—')}),
    tab:'groups', ts:0});

  // 🔄 Market — normal: listings added in the last 7 days
  const freshL=(st.listings||[]).filter(l=>Date.now()-(l.createdAt||0)<7*DAY);
  if(freshL.length){
    const newest=freshL.reduce((a,b)=>(b.createdAt||0)>(a.createdAt||0)?b:a);
    push({nid:'market-new', system:'market', prio:'normal', emoji:'🆕',
      title:t('notif.marketT',{n:freshL.length}),
      sub:t('notif.marketS',{t:newest.title}), tab:'market', ts:newest.createdAt||0, sample:newest.sample});
  }

  // 💼 Work — normal: open jobs count
  const open=(st.jobs||[]).filter(j=>j.status==='open');
  if(open.length){
    const newest=open.reduce((a,b)=>(b.createdAt||0)>(a.createdAt||0)?b:a);
    push({nid:'work-open', system:'work', prio:'normal', emoji:'💼',
      title:t('notif.workT',{n:open.length}),
      sub:t('notif.workS',{p:ui.fmt$(Math.max.apply(null,open.map(j=>j.pay||0)))}), tab:'work',
      ts:newest.createdAt||0});
  }

  // 📌 Appointments — high: in-app appointment reminders fired by the local scheduler.
  // Browser-local only — no push backend.
  try{
    if(HUB.appts){
      for(const f of HUB.appts.dueEntries()){
        push({nid:'appt-'+f.fid, system:'home', prio:'high', emoji:'📌',
          title:t('notif.apptT',{title:f.title}),
          sub:HUB.classes? HUB.classes.whenLabel(f.ts) : '',
          tab:'home', ts:f.firedAt, sample:false});
      }
    }
  }catch(e){}

  // 🎓 Classes — high: in-app class reminders fired by the local scheduler
  // (Workstream H1). Browser-local only — labeled as in-app demo reminders.
  try{
    if(HUB.classes){
      for(const f of HUB.classes.dueEntries()){
        const tm=HUB.classes.fmtTs(f.startTs);
        const sub=f.room
          ? t('notif.classS',{room:t('class.room',{room:f.room}), time:tm})
          : t('notif.classSNoRoom',{time:tm});
        push({nid:'class-'+f.fid, system:'campus', prio:'high', emoji:'🔔',
          title:t('notif.classT',{subject:f.subject,n:(f.mins||f.lead)}),
          sub:sub,
          tab:'home', ts:f.firedAt, sample:f.sample});
      }
    }
  }catch(e){}

  // 🏘️ Community — low: events whose time starts with 'Today'
  const todayEv=(st.events||[]).filter(e=>String(e.time||'').indexOf('Today')===0);
  if(todayEv.length) push({nid:'campus-today', system:'campus', prio:'low', emoji:'🎉',
    title:t('notif.evT',{n:todayEv.length}),
    sub:todayEv.slice(0,2).map(e=>e.title).join(' · '), tab:'daily', ts:0,
    sample:todayEv.every(e=>e.sample)});

  // 🏘️ Community — low: memory items expiring within 30 days
  (st.memory||[]).filter(m=>m.expiry && (m.expiry-Date.now())>0 && (m.expiry-Date.now())<30*DAY)
    .slice(0,3).forEach(m=>{
      const days=Math.ceil((m.expiry-Date.now())/DAY);
      push({nid:'mem-exp-'+m.id, system:'campus', prio:'low', emoji:'⏳',
        title:t('notif.memT',{t:m.title}), sub:t('notif.memS',{n:days}),
        tab:'me', ts:0, sample:m.sample});
    });

  // 👤 People — normal: people who followed you (tap opens their profile
  // overview so you can follow back and/or start messaging)
  const fevs=(st.followerEvents||[]).filter(e=>e&&e.id).slice(-3);
  for(const ev of fevs){
    const p=store.find('people',ev.id); if(!p) continue;
    push({nid:'follow-'+ev.id, system:'people', prio:'normal', emoji:'👤',
      title:t('notif.followT',{name:p.name}), sub:t('notif.followS'),
      personId:ev.id, tab:'groups', ts:ev.ts||0, sample:!!p.sample});
  }

  // 👥 Groups — normal: pending join requests on groups you administer
  // (tap opens the group page so you can approve/decline). Derived honestly
  // from local group state; browser-local demo until a backend exists.
  try{
    for(const g of (st.cgroups||[])){
      if(!g.mine||!g.live) continue;
      for(const rq of (g.requests||[]).slice(-2)){
        push({nid:'cgreq-'+g.id+'-'+String(rq.name||'').toLowerCase(), system:'groups',
          prio:'normal', emoji:'👥',
          title:t('cg.notifT',{name:rq.name,group:g.name}), sub:t('cg.notifS'),
          groupId:g.id, tab:'groups', ts:rq.at||0, sample:!!g.sample});
      }
    }
  }catch(e){}

  // 🏠 Households — normal: pending join requests on households you administer
  // (tap opens the household page so you can approve/decline). Derived
  // honestly from local household state; browser-local demo until a backend.
  try{
    for(const h of (st.households||[])){
      const admin=h.admin||((h.members||[])[0]||'');
      if(!ui.isMe(admin)) continue;
      for(const rq of (h.requests||[]).slice(-2)){
        push({nid:'hhreq-'+h.id+'-'+String(rq.name||'').toLowerCase(), system:'groups',
          prio:'normal', emoji:'🏠',
          title:t('hh.join.notifT',{name:rq.name,group:h.name}), sub:t('hh.join.notifS'),
          householdId:h.id, tab:'groups', ts:rq.at||0, sample:!!h.sample});
      }
    }
  }catch(e){}
  // 💬 Groups — normal: unread group-chat messages from other members.
  // Tap opens that group's chat. Browser-local demo data until a backend.
  try{
    const seenCg=st.cgChatSeen||{};
    for(const g of (st.cgroups||[])){
      if(HUB.gchat&&!HUB.gchat.isMember(g)) continue; /* members only */
      const unread=(g.chat||[]).filter(m=>m.from!=='me'&&(m.at||0)>(seenCg[g.id]||0));
      if(!unread.length) continue;
      const last=unread[unread.length-1];
      push({nid:'cgchat-'+g.id, system:'groups', prio:'normal', emoji:'💬',
        title:t('gc.notifT',{group:g.name}),
        sub:t('gc.notifS',{n:unread.length,preview:HUB.gchat?HUB.gchat.previewOf(last):''}),
        groupChatId:g.id, tab:'groups', ts:last.at||0, intrinsic:true, sample:!!g.sample});
    }
  }catch(e){}

  // 📅 Calendar — high: day notes with "remind me" that fall on today
  // (derived honestly from browser-local calNotes; in-app only)
  try{
    if(HUB.astro&&HUB.astro.reminderItems){
      for(const n of HUB.astro.reminderItems()) push(n);
    }
  }catch(e){}

  /* 🏅 Badge unlocks — honest local unlock log (last 30 days, never invented) */
  try{
    const pf=st.profile||{};
    const feed=Array.isArray(pf.badgeFeed)?pf.badgeFeed:[];
    const TH={new:0,silver:90,gold:180,legend:365};
    feed.slice(-5).forEach(function(u){
      if(!u||!u.id||!u.ts) return;
      if(Date.now()-u.ts>30*86400e3) return;
      const bid=u.id;
      const why=bid==='specialist'?t('bdg.whySpec'):t('bdg.whyTier',{n:TH[bid]||0});
      push({nid:'bdg-'+bid, system:'badges', prio:'normal', emoji:'🏅',
        title:t('bdg.earnT'), sub:t('bdg.'+bid)+' — '+why,
        tab:'me', badgeShow:true, ts:u.ts});
    });
  }catch(e){}

  out.sort((a,b)=>(PRIO_ORDER[a.prio]-PRIO_ORDER[b.prio])||((b.ts||0)-(a.ts||0)));
  return out.slice(0,NOTIF_CAP);
}

function unreadCount(){ return build().filter(n=>n.unreadNow).length; }

/* ---- overlay ---- */
function prioDot(prio){
  return '<span title="'+t('notif.prio',{p:prio})+'" style="display:inline-block;width:9px;height:9px;'+
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
  ['search','pulse'].forEach(k=>{ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
  try{ if(HUB.chat&&HUB.chat.close) HUB.chat.close(); }catch(e){}
  const app=document.getElementById('app')||document.body;
  const notifs=build();
  const d=document.createElement('div');
  d.className='chatroot'; d.id=ROOT_ID;
  d.innerHTML=
    '<div class="chatpanel" style="height:92%">'+
      '<div class="chathead">'+
        '<div class="grow"><h2 style="margin:0">'+HUB.icons.icon('ic-bell')+' '+t('notif.title')+'</h2></div>'+
        '<button class="btn btn-ghost btn-sm" id="hubNotifRead">'+t('notif.markRead')+'</button>'+
        '<button class="iconbtn" id="hubNotifClose" aria-label="'+t('notif.closeAria')+'">✕</button>'+
      '</div>'+
      '<div id="hubNotifRows" style="flex:1;overflow-y:auto;padding:12px 14px"></div>'+
    '</div>';
  app.appendChild(d);
  d.addEventListener('click',e=>{ if(e.target===d) close(); });
  document.getElementById('hubNotifClose').onclick=close;
  document.getElementById('hubNotifRead').onclick=()=>{
    prefs().lastSeenNotifications=Date.now(); store.save();
    ui.toast(t('notif.caughtUp')); open(); // rebuild to refresh unread dots
  };
  document.addEventListener('keydown',onKey);

  const host=document.getElementById('hubNotifRows');
  if(!notifs.length){
    host.innerHTML='<div class="empty"><div class="big">🔕</div><p>'+t('notif.emptyT')+' '+t('notif.emptyS')+'</p></div>';
    return;
  }
  host.innerHTML=SYSTEMS.map(s=>{
    const rows=notifs.filter(n=>n.system===s.key);
    if(!rows.length) return '';
    return '<h3 style="margin:14px 0 8px">'+ui.esc(t(s.label))+'</h3>'+rows.map(rowHTML).join('');
  }).join('');
  host.querySelectorAll('.item').forEach(el=>{
    const go=()=>{
      const notif=notifs.find(x=>x.nid===el.dataset.nid);
      if(notif&&notif.badgeShow){ close(); if(HUB.badges&&HUB.badges.openShowcase) HUB.badges.openShowcase(); else goto('groups'); return; }
      if(notif&&notif.trustReview){ close(); if(HUB.trust&&HUB.trust.moderationQueue) HUB.trust.moderationQueue(); else ui.toast(t('market.d.trustNotReady')); return; }
      if(notif&&notif.personId){ close(); if(HUB.people&&HUB.people.openProfile) HUB.people.openProfile(notif.personId); else goto('groups'); return; }
      if(notif&&notif.groupChatId){ close(); if(HUB.gchat&&HUB.gchat.open) HUB.gchat.open(notif.groupChatId); else goto('groups'); return; }
      if(notif&&notif.groupId){ close(); if(HUB.cgroups&&HUB.cgroups.openClub) HUB.cgroups.openClub(notif.groupId); else goto('groups'); return; }
      if(notif&&notif.householdId){ close(); if(HUB.households&&HUB.households.openHousehold) HUB.households.openHousehold(notif.householdId); else goto('groups'); return; }
      goto(el.dataset.tab);
    };
    el.onclick=go;
    el.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); } };
  });
}

HUB.notifications={open:open, close:close, unreadCount:unreadCount};
})();
