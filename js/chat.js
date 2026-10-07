/* HUB chat: contacts + threads in the #chatRoot overlay.
   Telegram/WhatsApp-style bubbles. All text escaped via ui.esc.
   Honesty: no auto-replies, no fake people — everything here is local data. */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };
const root=()=>document.getElementById('chatRoot');
const panel=()=>document.getElementById('chatPanel');
let listQuery='';
let openTid=null; /* thread id currently rendered in the panel, or null */

/* ---------- shared helpers ---------- */
/* Bottom sheets and the chatroot overlays (search/pulse/notifications) are
   mutually exclusive with chat — opening one closes the others so a chat
   thread never renders invisibly behind a bottom sheet (z-60 vs z-70). */
function closeSiblings(){
  ui.closeSheet();
  ['search','pulse','notifications'].forEach(k=>{ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
}
function threadContact(th){ return th.contactId?store.find('contacts',th.contactId):null; }
function threadName(th){ const c=threadContact(th); return (c&&c.name)||th.title||t('chat.unknown'); }
function threadPhone(th){ const c=threadContact(th); return (c&&c.phone)||''; }
function lastMsg(th){ return th.messages&&th.messages.length?th.messages[th.messages.length-1]:null; }
function threadSort(a,b){ const la=lastMsg(a),lb=lastMsg(b); return (lb?lb.at:0)-(la?la.at:0); }
function preview(th){
  const m=lastMsg(th);
  if(!m) return t('chat.noMessagesYet');
  const kind=m.kind||'text';
  if(kind==='image') return '📷 '+t('chat.photo');
  if(kind==='gif') return '🎞️ '+t('gc.gif');
  if(kind==='meme') return '😂 '+t('gc.meme');
  if(kind==='sticker') return '🪐 '+t('stk.sticker');
  if(kind==='file') return '📎 '+String(m.name||t('chat.file'));
  const pre=m.from==='me'?t('chat.youPrefix'):'';
  const pk=HUB.crypto&&HUB.crypto.peek?HUB.crypto.peek(m):null;
  if(pk!=null) return pre+pk;
  if(HUB.crypto&&HUB.crypto.locked(m)) return pre+'🔒 '+t('chat.encPreview');
  return pre+String(m.text||'');
}
function fmtSize(n){
  n=Number(n)||0;
  if(n<1024) return n+' B';
  if(n<1048576) return (n/1024).toFixed(1)+' KB';
  return (n/1048576).toFixed(1)+' MB';
}
/* linkify: escape everything, then wrap http(s) URLs in safe anchors */
function linkify(s){
  const parts=String(s||'').split(/(https?:\/\/[^\s<>"']+)/g);
  return parts.map((p,i)=> i%2===1
    ? '<a class="cblink" href="'+ui.esc(p)+'" target="_blank" rel="noopener">'+ui.esc(p)+'</a>'
    : ui.esc(p)).join('');
}

/* ---------- read receipts (2026-09-22, backend 2026-10-06) ----------
   Status model for my own messages: sent -> delivered -> seen.
   'delivered' means the message was persisted (locally or to server).
   'seen' advances when the other user opens the thread — via backend
   read receipts when logged in and online. Per-thread seenBy = {<name>: <ts>}. */
const RC={
  markSeen:function(th){
    if(!th) return;
    if(!th.seenBy||typeof th.seenBy!=='object') th.seenBy={};
    th.seenBy[store.myName()]=Date.now();
    store.save();
  },
  othersOf:function(th){
    const me=String(store.myName()).toLowerCase();
    const sb=(th&&th.seenBy&&typeof th.seenBy==='object')?th.seenBy:{};
    return Object.keys(sb).filter(function(n){ return String(n).toLowerCase()!==me; });
  },
  seenCount:function(th,others,at){
    const sb=(th&&th.seenBy&&typeof th.seenBy==='object')?th.seenBy:{};
    const low={}, me=String(store.myName()).toLowerCase();
    for(const k in sb) low[String(k).toLowerCase()]=Number(sb[k])||0;
    at=Number(at)||0;
    let n=0;
    (others||[]).forEach(function(on){
      if(String(on).toLowerCase()===me) return;
      if((low[String(on).toLowerCase()]||0)>=at) n++;
    });
    return n;
  },
  forMsg:function(th,m){
    if(!m||m.from!=='me') return null;
    if(RC.seenCount(th,RC.othersOf(th),m.at)>0) return 'seen';
    /* legacy/seed messages carry no status field -> delivered, never a crash */
    return m.status==='sent'?'sent':'delivered';
  },
  tickHTML:function(r){
    if(r==='sent') return ' <span class="tk tk-sent">✓</span>';
    if(r==='delivered') return ' <span class="tk tk-del">✓✓</span>';
    if(r==='seen') return ' <span class="tk tk-seen">✓✓</span>';
    return '';
  }
};
HUB.receipts=RC;

/* ---------- openList ---------- */
function openList(){
  closeSiblings();
  openTid=null;
  listQuery='';
  root().hidden=false;
  panel().classList.remove('gc-panel'); /* group-only bubble polish must not leak here */
  panel().innerHTML=
    '<div class="chathead">'+
      '<div class="grow"><h2 style="margin:0">'+HUB.icons.icon('ic-chat')+' '+t('chat.title')+'</h2></div>'+
      '<button class="btn btn-primary btn-sm" id="chatNew">'+t('chat.new')+'</button>'+
      '<button class="iconbtn" id="chatClose" aria-label="'+ui.esc(t('chat.closeAria'))+'">✕</button>'+
    '</div>'+
    '<div style="flex:1;overflow-y:auto;padding:12px 14px;">'+
      '<div class="field" style="margin-bottom:10px">'+
        '<input class="input" id="chatSearch" placeholder="'+ui.esc(t('chat.searchPh'))+'" autocomplete="off" value="">'+
      '</div>'+
      '<div id="chatRows"></div>'+
    '</div>';
  document.getElementById('chatNew').onclick=newContactSheet;
  document.getElementById('chatClose').onclick=close;
  const search=document.getElementById('chatSearch');
  search.oninput=()=>{ listQuery=search.value.trim().toLowerCase(); renderRows(); };
  renderRows();
  // keep focus on search if it was being used (renderRows doesn't touch the input)
}
function renderRows(){
  const host=document.getElementById('chatRows');
  if(!host) return;
  let threads=store.state.threads.slice().sort(threadSort);
  if(listQuery){
    threads=threads.filter(th=>
      threadName(th).toLowerCase().includes(listQuery)||
      threadPhone(th).toLowerCase().includes(listQuery)||
      preview(th).toLowerCase().includes(listQuery));
  }
  if(!threads.length){
    /* premium polish (2026-10-07): elevated empty state with a real CTA */
    host.innerHTML='<div class="empty ps-empty"><div class="big">💬</div><p class="ps-sub">'+
      (listQuery?t('chat.emptySearch'):t('chat.emptyNone'))+
      '</p>'+(listQuery?'':'<button class="btn btn-primary ps-cta" id="chatEmptyNew">'+t('chat.new')+'</button>')+'</div>';
    const cen=document.getElementById('chatEmptyNew');
    if(cen) cen.onclick=newContactSheet;
    return;
  }
  host.innerHTML=threads.map(th=>{
    const name=threadName(th), m=lastMsg(th);
    const blk=HUB.block.isBlockedThread(th);
    return '<div class="item" data-tid="'+th.id+'" style="cursor:pointer" role="button" tabindex="0">'+
      '<div class="avatar">'+ui.esc(ui.initials(name))+'</div>'+
      '<div class="grow">'+
        '<h3>'+ui.esc(name)+(blk?' <span class="meta" style="color:var(--danger)">⛔ '+ui.esc(t('chat.blockedTag'))+'</span>':'')+'</h3>'+
        '<div class="meta" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+ui.esc(preview(th))+'</div>'+
      '</div>'+
      '<div style="display:flex;flex-direction:column;align-items:flex-end;gap:5px;flex:0 0 auto">'+
        (m?'<span class="hint">'+ui.esc(ui.timeAgo(m.at))+'</span>':'')+
        (t.unread?'<span class="unread">'+ui.esc(String(t.unread))+'</span>':'')+
      '</div>'+
    '</div>';
  }).join('');
  host.querySelectorAll('.item').forEach(el=>{
    const go=()=>openThread(el.dataset.tid);
    el.onclick=go;
    el.onkeydown=e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); } };
  });
}

/* ---------- new contact sheet ---------- */
function newContactSheet(){
  ui.openSheet(
    '<h2>'+HUB.icons.icon('ic-chat')+' '+t('chat.newTitle')+'</h2>'+
    '<p class="sub" style="margin-bottom:14px">'+t('chat.newSub')+'</p>'+
    '<div class="field"><label>'+t('chat.nameLabel')+'</label><input class="input" id="ncName" placeholder="'+ui.esc(t('chat.namePh'))+'" autocomplete="off"></div>'+
    '<div class="field"><label>'+t('chat.phoneLabel')+'</label><input class="input" id="ncPhone" placeholder="+1 555-000-0000" inputmode="tel" autocomplete="off"></div>'+
    '<button class="btn btn-primary btn-block" id="ncGo">'+t('chat.addContact')+'</button>'
  );
  document.getElementById('ncGo').onclick=()=>{
    const name=document.getElementById('ncName').value.trim();
    const phone=document.getElementById('ncPhone').value.trim();
    if(!name){ ui.toast(t('chat.needName')); return; }
    // dedupe: reuse an existing contact by phone, else by name
    let c=null;
    if(phone) c=store.state.contacts.find(x=>String(x.phone||'').trim()===phone);
    if(!c) c=store.state.contacts.find(x=>String(x.name||'').trim().toLowerCase()===name.toLowerCase());
    if(!c){ store.add('contacts',{name,phone}); c=store.state.contacts[0]; } // store.add unshifts
    // every contact gets a thread — otherwise the new contact would be
    // invisible in the thread list (dead end reported in QA)
    let th=store.state.threads.find(x=>x.contactId===c.id);
    if(!th){ store.add('threads',{contactId:c.id,title:c.name,messages:[],unread:0}); th=store.state.threads.find(x=>x.contactId===c.id); }
    ui.closeSheet();
    ui.toast(t('chat.contactAdded'));
    openThread(th.id);
  };
}

/* ---------- demo-honest safety: checklist + scam-pattern hints ---------- */
// Safety checklist: shown once per seller before the first chat.
// A demo reminder only — HUB is a local demo, not a moderated marketplace.
const SAFETY_ITEMS=['chat.safety.1','chat.safety.2','chat.safety.3','chat.safety.4','chat.safety.5'];
function safetyChecklistSheet(ackKey,done){
  ui.openSheet(
    '<h2>'+t('chat.safetyTitle')+'</h2>'+
    '<p class="sub" style="margin:6px 0 12px">'+t('chat.safetySub')+'</p>'+
    '<div>'+SAFETY_ITEMS.map(k=>'<label class="check-row"><input type="checkbox" class="safetyCk"><span>'+ui.esc(t(k))+'</span></label>').join('')+'</div>'+
    '<button class="btn btn-primary btn-block" id="safetyGo" style="margin-top:14px">'+t('chat.safetyGo')+'</button>'+
    '<button class="btn btn-ghost btn-block" id="safetySkip" style="margin-top:8px">'+t('chat.safetySkip')+'</button>'
  );
  document.getElementById('safetyGo').onclick=()=>{
    const all=[...document.querySelectorAll('.safetyCk')].every(b=>b.checked);
    if(!all){ ui.toast(t('chat.safetyNeedAll')); return; }
    store.state.safetyAck=store.state.safetyAck||{};
    store.state.safetyAck[ackKey]=true; store.save();
    ui.closeSheet(); done();
  };
  document.getElementById('safetySkip').onclick=()=>{ ui.closeSheet(); done(); };
}

/* Scam-pattern hints: LOCAL keyword check only (small visible list below).
   Never claims AI moderation or real protection. */
const SCAM_PATTERNS=['wire money','gift card','pay first before','off the app','cashapp me first',
  "don't tell anyone",'venmo me first','zelle me first','send the code','pay before you see'];
function scamHit(text){
  const s=String(text||'').toLowerCase();
  for(const pat of SCAM_PATTERNS){ if(s.indexOf(pat)!==-1) return pat; }
  return null;
}
function scamBannerHTML(hit){
  return '<div class="demo-note" role="note">'+t('chat.scamBanner',{hit:hit})+'</div>';
}

/* ---------- openThread ---------- */
function openThread(threadId){
  closeSiblings();
  const th=store.find('threads',threadId);
  if(!th){ ui.toast(t('chat.notFound')); return; }
  root().hidden=false;
  openTid=threadId;
  panel().classList.remove('gc-panel'); /* group-only bubble polish must not leak here */
  th.unread=0; RC.markSeen(th); refreshDot();
  /* Phase 2: start polling for new messages + read receipts */
  startThreadPolling(th);
  const name=threadName(th), phone=threadPhone(th), cc=threadContact(th);
  /* verified identity: the contact record, or a matching person by name
     (sample threads are title-based and carry no contactId) */
  const cver=!!(cc&&cc.verified)||(store.state.people||[]).some(p=>p&&p.name===name&&p.verified);
  panel().innerHTML=
    '<div class="chathead">'+
      '<button class="iconbtn" id="chBack" aria-label="'+ui.esc(t('chat.backAria'))+'">←</button>'+
      '<div class="avatar">'+ui.esc(ui.initials(name))+'</div>'+
      '<div class="grow"><h3 style="margin:0;display:flex;align-items:center;gap:6px;flex-wrap:wrap">'+ui.esc(name)+(cver?ui.verifiedBadge():'')+'</h3>'+
        '<div class="meta">'+ui.esc(phone)+(th.sample?t('chat.sampleTag'):'')+'</div></div>'+
      '<button class="iconbtn" id="chMore" aria-label="'+ui.esc(t('chat.moreAria'))+'">⋯</button>'+
    '</div>'+
    '<div id="chatScroll" style="flex:1;overflow-y:auto;padding:12px 14px;"><div id="chatLock" style="margin-bottom:6px"></div><div class="bubbles" id="chatBubbles"></div></div>'+
    '<div class="chatinput">'+
      '<button class="iconbtn" id="chPhoto" aria-label="'+ui.esc(t('chat.attachPhoto'))+'">📷</button>'+
      '<button class="iconbtn" id="chFile" aria-label="'+ui.esc(t('chat.attachFile'))+'">📎</button>'+
      '<button class="iconbtn" id="chEmoji" aria-label="'+ui.esc(t('stk.emojiAria'))+'">😊</button>'+
      '<input type="file" id="chPhotoIn" accept="image/*" hidden>'+
      '<input type="file" id="chFileIn" hidden>'+
      '<input class="input" id="chatText" placeholder="'+ui.esc(t('chat.msgPh'))+'" autocomplete="off" maxlength="2000">'+
      '<button class="btn btn-primary" id="chatSend" style="border-radius:999px;padding:12px 18px;flex:0 0 auto" aria-label="'+ui.esc(t('chat.sendAria'))+'">➤</button>'+
    '</div>';
  document.getElementById('chBack').onclick=openList;
  document.getElementById('chMore').onclick=()=>threadSheet(th.id);
  /* blocked contact: composer is locked — show notice + unblock instead */
  const blk=HUB.block.isBlockedContact(cc||{name});
  if(blk){
    panel().querySelector('.chatinput').innerHTML=
      '<div style="display:flex;flex-direction:column;gap:8px;padding:14px;text-align:center;width:100%">'+
      '<div class="meta">⛔ '+ui.esc(t('chat.blockedComposer',{name}))+'</div>'+
      '<button class="btn btn-block" id="chUnblock">'+t('chat.unblock')+'</button></div>';
    document.getElementById('chUnblock').onclick=()=>{ HUB.block.unblockContact(cc||{name}); ui.toast(t('chat.unblockedToast',{name})); refreshDot(); openThread(threadId); };
    if(HUB.crypto&&HUB.crypto.lockHTML) HUB.crypto.lockHTML().then(h=>{ const l=document.getElementById('chatLock'); if(l) l.innerHTML=h; });
    renderBubbles(th.id);
    return;
  }
  document.getElementById('chatSend').onclick=()=>sendMessage(th.id);
  document.getElementById('chPhoto').onclick=()=>document.getElementById('chPhotoIn').click();
  document.getElementById('chFile').onclick=()=>document.getElementById('chFileIn').click();
  document.getElementById('chEmoji').onclick=()=>openStickerPicker(th.id);
  document.getElementById('chPhotoIn').onchange=e=>{ const f=e.target.files[0]; e.target.value=''; if(f) sendPhoto(th.id,f); };
  document.getElementById('chFileIn').onchange=e=>{ const f=e.target.files[0]; e.target.value=''; if(f) sendFile(th.id,f); };
  if(HUB.crypto&&HUB.crypto.lockHTML) HUB.crypto.lockHTML().then(h=>{ const l=document.getElementById('chatLock'); if(l) l.innerHTML=h; });
  const input=document.getElementById('chatText');
  input.onkeydown=e=>{ if(e.key==='Enter'){ e.preventDefault(); sendMessage(th.id); } };
  /* keyboard dodge (2026-09-22): same as the group thread — keep the message
     list visible above the iOS keyboard, like iPhone Messages */
  ui.dodgeKeyboard();
  input.addEventListener('focus',()=>ui.kbSnap());
  /* tap an art/image message to view it full-size (delegated; survives repaints) */
  document.getElementById('chatBubbles').onclick=e=>{
    const img=e.target.closest?e.target.closest('img[data-full]'):null;
    if(!img) return;
    ui.openSheet('<h2>'+ui.esc(t('chat.photo'))+'</h2>'
      +'<img src="'+ui.esc(img.dataset.full)+'" style="width:100%;border-radius:14px;margin-top:8px" alt="'+ui.esc(t('chat.imgAlt'))+'">');
  };
  renderBubbles(th.id);
  setTimeout(()=>input.focus(),60);
}
async function bubbleHTML(m,txt,th){
  /* job-scoped system lines (e.g. "You're chatting about 'Ride share'"):
     centered note, never a fake incoming bubble from the other person. */
  if(m&&m.from==='sys') return '<div class="csys">'+ui.esc(txt)+'</div>';
  const kind=m.kind||'text', cls=m.from==='me'?'out':'in';
  const ticks=RC.tickHTML(RC.forMsg(th,m));
  const time='<span class="t">'+ui.esc(ui.timeAgo(m.at||Date.now()))+ticks+'</span>';
  if(kind==='gif'||kind==='meme'||kind==='sticker'){
    const src=m.data||'';
    const badge=kind==='gif'?'<span class="gcbadge">GIF</span>'
      :kind==='meme'?'<span class="gcbadge">MEME</span>'
      :'<span class="gcbadge">STICKER</span>';
    const img=src?'<img class="cbimg'+(kind==='sticker'?' stkimg':'')+'" src="'+ui.esc(src)+'" data-full="'+ui.esc(src)+'" alt="'+ui.esc(t('gc.imgAlt'))+'" loading="lazy">':'';
    return '<div class="bubble '+cls+'">'+badge+img+time+'</div>';
  }
  if(kind==='image'){
    let src='';
    try{ src=await HUB.crypto.textOf(m); }catch(e){}
    src=src||m.data||'';
    const img=src?'<img class="cbimg" src="'+ui.esc(src)+'" alt="'+ui.esc(t('chat.imgAlt'))+'">':'<span class="meta">'+ui.esc(t('crypto.locked'))+'</span>';
    return '<div class="bubble '+cls+'">'+img+time+'</div>';
  }
  if(kind==='file'){
    let src='';
    try{ src=await HUB.crypto.textOf(m); }catch(e){}
    src=src||m.data||'';
    const dl=src?'<div style="margin-top:6px"><a class="cblink" href="'+ui.esc(src)+'" download="'+ui.esc(m.name||'file')+'">'+ui.esc(t('chat.download'))+'</a></div>':'';
    return '<div class="bubble '+cls+'"><div class="cbfile">📎 <b>'+ui.esc(m.name||t('chat.file'))+'</b>'
      +(m.size!=null?' <span class="meta">'+ui.esc(fmtSize(m.size))+'</span>':'')+'</div>'+dl+time+'</div>';
  }
  return '<div class="bubble '+cls+'">'+linkify(txt)+time+'</div>';
}
async function renderBubbles(threadId){
  const th=store.find('threads',threadId);
  const box=document.getElementById('chatBubbles');
  if(!th||!box) return;
  const msgs=th.messages||[];
  const texts=await Promise.all(msgs.map(m=>((m.kind||'text')==='text')?HUB.crypto.textOf(m):Promise.resolve('')));
  const hit=texts.map(scamHit).find(Boolean);
  const banner=hit?scamBannerHTML(hit):'';
  if(!msgs.length){
    box.innerHTML=banner+'<div class="empty"><div class="big">👋</div><p>'+t('chat.emptyThreadT')+'<br>'+t('chat.emptyThreadS')+'</p></div>';
  }else{
    const rows=await Promise.all(msgs.map((m,i)=>bubbleHTML(m,texts[i],th)));
    box.innerHTML=banner+rows.join('');
  }
  scrollBottom();
}
function scrollBottom(){
  const sc=document.getElementById('chatScroll');
  if(sc) sc.scrollTop=sc.scrollHeight;
}
async function pushMessage(th,msg){
  /* blocked contact: their messages never land (covers the backend transport later) */
  if(msg&&msg.from!=='me'&&HUB.block&&HUB.block.isBlockedThread(th)) return;
  th.messages.push(msg);
  store.save();
  await renderBubbles(th.id);
  /* sent -> delivered: no network exists in this browser-local demo, so
     'delivered' means the message reached the thread store. The short delay
     keeps the intermediate 'sent' state visible instead of flickering past. */
  if(msg.from==='me'&&msg.status==='sent'){
    setTimeout(function(){
      if(msg.status!=='sent') return;
      msg.status='delivered';
      try{ store.save(); }catch(e){}
      if(openTid===th.id) renderBubbles(th.id);
    },650);
  }
}
async function sendMessage(threadId){
  const th=store.find('threads',threadId);
  const input=document.getElementById('chatText');
  if(!th||!input) return;
  if(HUB.block.isBlockedThread(th)){ ui.toast(t('chat.blockedNoSend')); return; }
  const text=input.value.trim();
  if(!text) return;
  try{
    const enc=await HUB.crypto.encryptText(text);
    input.value='';
    const msg=Object.assign({from:'me',at:Date.now(),kind:'text',status:'sent',
      clientId:'c'+Date.now().toString(36)+Math.random().toString(36).slice(2,8)},
      enc?{enc}:{text});
    await pushMessage(th,msg);
    try{ if(window.HUB&&HUB.fx&&HUB.fx.haptic) HUB.fx.haptic('success'); }catch(e2){}
    /* Phase 2: sync to server when online + logged in */
    syncMessageToServer(th,msg);
  }catch(e){
    /* Never leave an unhandled rejection: the text stays in the composer
       so the user can retry. */
    try{ ui.toast(t('chat.sendFailed')); }catch(e2){}
  }
  // Honesty: no auto-replies — the other side is a real person (or a silent sample).
}
/* Phase 2: send a local message to the backend (fire-and-forget).
   The thread needs th.backendConvId (set when the conversation is created). */
function syncMessageToServer(th,msg){
  try{
    if(!(window.HUB&&HUB.api&&HUB.api.isLoggedIn())) return;
    if(HUB.offline&&HUB.offline.is()) return;
    if(!th.backendConvId) return;
    var body=msg.enc?JSON.stringify(msg.enc):msg.text;
    HUB.api.sendMessage(th.backendConvId,body,msg.clientId).then(function(j){
      msg.backendId=j.message_id;
      try{ store.save(); }catch(e){}
    }).catch(function(){ /* stays local; retry on next open */ });
  }catch(e){}
}
function readAsDataURL(file){
  return new Promise((res,rej)=>{ const r=new FileReader(); r.onload=()=>res(r.result); r.onerror=rej; r.readAsDataURL(file); });
}
function downscaleImg(src,maxDim){
  return new Promise(res=>{
    const img=new Image();
    img.onload=()=>{
      try{
        let w=img.width,h=img.height;
        const k=Math.min(1,maxDim/Math.max(w,h));
        w=Math.round(w*k); h=Math.round(h*k);
        const c=document.createElement('canvas'); c.width=w; c.height=h;
        c.getContext('2d').drawImage(img,0,0,w,h);
        res(c.toDataURL('image/jpeg',0.82));
      }catch(e){ res(src); }
    };
    img.onerror=()=>res(src);
    img.src=src;
  });
}
const MAX_ATTACH_MB=2.5;
async function sendPhoto(threadId,file){
  const th=store.find('threads',threadId);
  if(!th) return;
  if(HUB.block.isBlockedThread(th)){ ui.toast(t('chat.blockedNoSend')); return; }
  try{
    const raw=await readAsDataURL(file);
    const small=await downscaleImg(raw,1080);
    if(small.length>MAX_ATTACH_MB*1024*1024){ ui.toast(t('chat.fileTooBig',{n:MAX_ATTACH_MB})); return; }
    const enc=await HUB.crypto.encryptText(small);
    await pushMessage(th,Object.assign({from:'me',at:Date.now(),kind:'image',status:'sent',name:file.name||'photo.jpg',size:file.size},enc?{enc}:{data:small}));
  }catch(e){ ui.toast(t('chat.fileTooBig',{n:MAX_ATTACH_MB})); }
}
async function sendFile(threadId,file){
  const th=store.find('threads',threadId);
  if(!th) return;
  if(HUB.block.isBlockedThread(th)){ ui.toast(t('chat.blockedNoSend')); return; }
  if(file.size>MAX_ATTACH_MB*1024*1024){ ui.toast(t('chat.fileTooBig',{n:MAX_ATTACH_MB})); return; }
  try{
    const data=await readAsDataURL(file);
    const enc=await HUB.crypto.encryptText(data);
    await pushMessage(th,Object.assign({from:'me',at:Date.now(),kind:'file',status:'sent',name:file.name||'file',size:file.size},enc?{enc}:{data}));
  }catch(e){ ui.toast(t('chat.fileTooBig',{n:MAX_ATTACH_MB})); }
}

/* ---------- sticker/GIF/emoji picker (delegated to groupchat.js) ---------- */
function openStickerPicker(threadId){
  const th=store.find('threads',threadId);
  if(!th||!HUB.groupchat||!HUB.groupchat.openStickerPicker) return;
  HUB.groupchat.openStickerPicker({
    tab:'emoji',
    onEmoji:function(ch){ HUB.groupchat.insertEmoji('chatText',ch); },
    onArt:function(item){
      pushMessage(th,{from:'me',at:Date.now(),kind:item.kind,data:item.src,name:item.label,status:'sent'});
    }
  });
}
/* ---------- thread options sheet ---------- */
function threadSheet(threadId){
  const th=store.find('threads',threadId)||{};
  const cc=threadContact(th)||{name:threadName(th)};
  const blk=HUB.block.isBlockedContact(cc);
  ui.openSheet(
    '<h2>'+HUB.icons.icon('ic-chat')+' '+t('chat.threadTitle')+'</h2>'+
    '<p class="sub" style="margin-bottom:14px">'+ui.esc(threadName(th))+'</p>'+
    '<button class="btn btn-block" id="blkThread" style="margin-bottom:8px">'+(blk?t('chat.unblockUser'):t('chat.blockUser'))+'</button>'+
    '<button class="btn btn-block" id="delThread" style="background:#FEE2E2;color:var(--danger)">'+t('chat.delete')+'</button>'+
    '<button class="btn btn-ghost btn-block" id="cancelSheet" style="margin-top:8px">'+t('common.cancel')+'</button>'
  );
  document.getElementById('cancelSheet').onclick=ui.closeSheet;
  document.getElementById('blkThread').onclick=()=>{
    if(blk) HUB.block.unblockContact(cc);
    else HUB.block.blockContact(cc);
    ui.closeSheet();
    ui.toast(blk?t('chat.unblockedToast',{name:threadName(th)}):t('chat.blockedToast',{name:threadName(th)}));
    refreshDot();
    openThread(threadId); // rebuild the panel so the composer reflects the new block state
  };
  document.getElementById('delThread').onclick=()=>{
    store.remove('threads',threadId);
    ui.closeSheet();
    ui.toast(t('chat.deleted'));
    refreshDot();
    openList();
  };
}

/* ---------- openWith (called by MARKET "Message seller") ---------- */
function openWith(contact,contextMessage,opts){
  if(!contact) return;
  opts=opts||{};
  closeSiblings(); // e.g. the market detail sheet must not cover the chat thread
  const name=String(contact.name||'').trim()||t('chat.unknown');
  const phone=String(contact.phone||'').trim();
  // find or create contact by phone, else by name
  let c=null;
  if(phone) c=store.state.contacts.find(x=>String(x.phone||'').trim()===phone);
  if(!c) c=store.state.contacts.find(x=>String(x.name||'').trim().toLowerCase()===name.toLowerCase());
  if(!c){
    store.add('contacts',{name,phone});
    c=store.state.contacts[0]; // store.add unshifts
  }
  // find or create thread for that contact
  let th=store.state.threads.find(x=>x.contactId===c.id);
  if(!th){
    store.add('threads',{contactId:c.id,listingId:contact.listingId||null,title:c.name,messages:[],unread:0});
    th=store.state.threads.find(x=>x.contactId===c.id);
  }
  // seed first message from context (e.g. "Hi! I'm interested in your listing…")
  if(contextMessage&&th&&(!th.messages||!th.messages.length)){
    th.messages=[{from:'me',text:String(contextMessage),at:Date.now()}];
    store.save();
  }
  // safety checklist on the first chat with this seller (once per seller; persisted in state).
  // Skipped for non-marketplace flows (e.g. gym buddies) via opts.skipSafety.
  store.state.safetyAck=store.state.safetyAck||{};
  const ackKey='seller:'+(c.id||name.toLowerCase());
  if(!opts.skipSafety&&!store.state.safetyAck[ackKey]){ safetyChecklistSheet(ackKey,()=>openThread(th.id)); return; }
  if(th) openThread(th.id);
}

/* ---------- overlay + dot ---------- */
let _pollTimer=null;
function stopThreadPolling(){
  if(_pollTimer){ clearInterval(_pollTimer); _pollTimer=null; }
}
/* Phase 2: poll server for new messages + read receipts every 4s while open */
function startThreadPolling(th){
  stopThreadPolling();
  if(!(window.HUB&&HUB.api&&HUB.api.isLoggedIn())) return;
  if(!th.backendConvId) return;
  const tid=th.id;
  _pollTimer=setInterval(function(){
    if(openTid!==tid) { stopThreadPolling(); return; }
    if(HUB.offline&&HUB.offline.is()) return;
    HUB.api.getMessages(th.backendConvId,50).then(function(j){
      const msgs=j.messages||[];
      let changed=false;
      msgs.forEach(function(sm){
        /* merge: skip if we already have this backendId */
        const exists=(th.msgs||[]).some(function(m){ return m.backendId===sm.message_id; });
        if(exists) return;
        /* decrypt body (it's JSON ciphertext or plain) */
        let text=sm.body, enc=null;
        try{ const p=JSON.parse(sm.body); if(p&&p.ct){ enc=p; text=''; } }catch(e){}
        const isMe=sm.sender_id===(HUB.api.getUser()||{}).id;
        th.msgs.push({
          from:isMe?'me':'them', at:new Date(sm.created_at).getTime(),
          kind:'text', status:isMe?'delivered':'',
          backendId:sm.message_id, ...(enc?{enc}:{text:text})
        });
        /* mark their messages as seen on server */
        if(!isMe&&sm.message_id) HUB.api.markRead(sm.message_id).catch(function(){});
        changed=true;
      });
      /* update read receipts for my messages */
      (th.msgs||[]).forEach(function(m){
        if(m.from!=='me'||!m.backendId) return;
        const sm=msgs.find(function(x){ return x.message_id===m.backendId; });
        if(sm&&sm.read_by&&sm.read_by.length>0){
          /* someone saw it — update seenBy */
          if(!th.seenBy) th.seenBy={};
          sm.read_by.forEach(function(uid){
            if(uid!==(HUB.api.getUser()||{}).id) th.seenBy['user:'+uid]=Date.now();
          });
          changed=true;
        }
      });
      if(changed){
        try{ store.save(); }catch(e){}
        if(openTid===tid) renderMessages(th);
      }
    }).catch(function(){});
  },4000);
}
function close(){
  openTid=null;
  stopThreadPolling();
  const p=panel(); if(p){ p.style.height=''; p.style.maxHeight=''; p.style.transform=''; } /* drop any keyboard-dodge sizing */
  root().hidden=true;
  ui.closeSheet();
}
function refreshDot(){
  const dot=document.getElementById('chatDot');
  if(dot) dot.hidden=!(store.unreadCount()>0);
}

/* One-time overlay dismissal bindings: backdrop tap closes the overlay;
   Escape steps back from a thread to the list, or closes the list fully. */
(function(){
  const r=root(); if(!r||r.dataset.dismissBound) return; r.dataset.dismissBound='1';
  r.addEventListener('click',function(e){ if(e.target===r) close(); });
  document.addEventListener('keydown',function(e){
    if(e.key!=='Escape') return;
    const rr=root(); if(!rr||rr.hidden) return;
    const sh=document.getElementById('sheetHost');
    if(sh&&!sh.hidden) return; /* a sheet above us owns this Escape (the global handler closes it) */
    if(document.getElementById('chBack')){
      /* thread -> list step-back. A higher overlay owns this Escape instead
         (same defer list as the app.js global handler, plus the class-only
         .chatroot overlays and the gym drawer, all removed from the DOM or
         hidden when closed); otherwise stopImmediatePropagation keeps the
         global handler from also firing and closing the list we just
         stepped back to. */
      if(document.querySelector('.mkzoom,.callroot:not([hidden]),.incallroot:not([hidden]),.hpglass:not([hidden]),.authroot:not([hidden]),.chatroot:not(#chatRoot):not([hidden]),.gy-drawer')) return;
      e.stopImmediatePropagation();
      openList();
    }
    else close();
  });
})();

/* ---------- block list (browser-local; backend enforcement later) ---------- */
const BLOCK={
  /* key: 'id:<contactId>' for real contacts, 'nm:<lowercased name>' for
     title-only/sample threads. Persisted in store.state.blocked (array). */
  keyOf:function(c){
    if(c&&c.id) return 'id:'+c.id;
    const nm=String((c&&c.name)||'').trim().toLowerCase();
    return 'nm:'+nm;
  },
  list:function(){
    if(!Array.isArray(store.state.blocked)) store.state.blocked=[];
    return store.state.blocked;
  },
  isBlockedContact:function(c){ return BLOCK.list().indexOf(BLOCK.keyOf(c))!==-1; },
  isBlockedName:function(name){
    const nm=String(name||'').trim().toLowerCase();
    if(!nm) return false;
    /* try a real contact match first, then the name fallback key */
    const c=(store.state.contacts||[]).find(x=>String(x.name||'').trim().toLowerCase()===nm);
    return BLOCK.isBlockedContact(c||{name:name});
  },
  isBlockedThread:function(th){
    if(!th) return false;
    return BLOCK.isBlockedContact(threadContact(th)||{name:threadName(th)});
  },
  blockContact:function(c){
    const k=BLOCK.keyOf(c), l=BLOCK.list();
    if(l.indexOf(k)===-1){ l.push(k); store.save(); }
  },
  unblockContact:function(c){
    const k=BLOCK.keyOf(c), l=BLOCK.list(), i=l.indexOf(k);
    if(i!==-1){ l.splice(i,1); store.save(); }
  }
};
HUB.block=BLOCK;

HUB.chat={openList,openThread,openWith,close,refreshDot};
})();
