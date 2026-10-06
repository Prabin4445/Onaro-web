/* HUB chat: contacts + threads in the #chatRoot overlay.
   Telegram/WhatsApp-style bubbles. All text escaped via ui.esc.
   Honesty: no auto-replies, no fake people — everything here is local data. */
(function(){
'use strict';
const {store,ui}=HUB;
const root=()=>document.getElementById('chatRoot');
const panel=()=>document.getElementById('chatPanel');
let listQuery='';

/* ---------- shared helpers ---------- */
/* Bottom sheets and the chatroot overlays (search/pulse/notifications) are
   mutually exclusive with chat — opening one closes the others so a chat
   thread never renders invisibly behind a bottom sheet (z-60 vs z-70). */
function closeSiblings(){
  ui.closeSheet();
  ['search','pulse','notifications'].forEach(k=>{ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
}
function threadContact(t){ return t.contactId?store.find('contacts',t.contactId):null; }
function threadName(t){ const c=threadContact(t); return (c&&c.name)||t.title||'Unknown'; }
function threadPhone(t){ const c=threadContact(t); return (c&&c.phone)||''; }
function lastMsg(t){ return t.messages&&t.messages.length?t.messages[t.messages.length-1]:null; }
function threadSort(a,b){ const la=lastMsg(a),lb=lastMsg(b); return (lb?lb.at:0)-(la?la.at:0); }
function preview(t){
  const m=lastMsg(t);
  if(!m) return 'No messages yet — say hi! 👋';
  const pre=m.from==='me'?'You: ':'';
  return pre+String(m.text||'');
}

/* ---------- openList ---------- */
function openList(){
  closeSiblings();
  listQuery='';
  root().hidden=false;
  panel().innerHTML=
    '<div class="chathead">'+
      '<div class="grow"><h2 style="margin:0">'+HUB.icons.icon('ic-chat')+' Chats</h2></div>'+
      '<button class="btn btn-primary btn-sm" id="chatNew">＋ New</button>'+
    '</div>'+
    '<div style="flex:1;overflow-y:auto;padding:12px 14px;">'+
      '<div class="field" style="margin-bottom:10px">'+
        '<input class="input" id="chatSearch" placeholder="🔍 Search chats" autocomplete="off" value="">'+
      '</div>'+
      '<div id="chatRows"></div>'+
    '</div>';
  document.getElementById('chatNew').onclick=newContactSheet;
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
    threads=threads.filter(t=>
      threadName(t).toLowerCase().includes(listQuery)||
      threadPhone(t).toLowerCase().includes(listQuery)||
      preview(t).toLowerCase().includes(listQuery));
  }
  if(!threads.length){
    host.innerHTML='<div class="empty"><div class="big">💬</div><p>'+
      (listQuery?'No chats match your search.':'No chats yet. Tap <b>＋ New</b> to add a contact and start one.')+
      '</p></div>';
    return;
  }
  host.innerHTML=threads.map(t=>{
    const name=threadName(t), m=lastMsg(t);
    return '<div class="item" data-tid="'+t.id+'" style="cursor:pointer" role="button" tabindex="0">'+
      '<div class="avatar">'+ui.esc(ui.initials(name))+'</div>'+
      '<div class="grow">'+
        '<h3>'+ui.esc(name)+'</h3>'+
        '<div class="meta" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+ui.esc(preview(t))+'</div>'+
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
    '<h2>'+HUB.icons.icon('ic-chat')+' New chat</h2>'+
    '<p class="sub" style="margin-bottom:14px">Add someone to start messaging. Everything stays in this browser.</p>'+
    '<div class="field"><label>Name</label><input class="input" id="ncName" placeholder="e.g. Jordan Lee" autocomplete="off"></div>'+
    '<div class="field"><label>Phone</label><input class="input" id="ncPhone" placeholder="+1 555-000-0000" inputmode="tel" autocomplete="off"></div>'+
    '<button class="btn btn-primary btn-block" id="ncGo">Add contact</button>'
  );
  document.getElementById('ncGo').onclick=()=>{
    const name=document.getElementById('ncName').value.trim();
    const phone=document.getElementById('ncPhone').value.trim();
    if(!name){ ui.toast('Please enter a name'); return; }
    // dedupe: reuse an existing contact by phone, else by name
    let c=null;
    if(phone) c=store.state.contacts.find(x=>String(x.phone||'').trim()===phone);
    if(!c) c=store.state.contacts.find(x=>String(x.name||'').trim().toLowerCase()===name.toLowerCase());
    if(!c){ store.add('contacts',{name,phone}); c=store.state.contacts[0]; } // store.add unshifts
    // every contact gets a thread — otherwise the new contact would be
    // invisible in the thread list (dead end reported in QA)
    let t=store.state.threads.find(x=>x.contactId===c.id);
    if(!t){ store.add('threads',{contactId:c.id,title:c.name,messages:[],unread:0}); t=store.state.threads.find(x=>x.contactId===c.id); }
    ui.closeSheet();
    ui.toast('Contact added');
    openThread(t.id);
  };
}

/* ---------- demo-honest safety: checklist + scam-pattern hints ---------- */
// Safety checklist: shown once per seller before the first chat.
// A demo reminder only — HUB is a local demo, not a moderated marketplace.
const SAFETY_ITEMS=[
  'Meet in a public place — never a private home',
  'Meet in daytime, and bring a friend if you can',
  "Don't share your home address",
  'Inspect the item before you pay',
  'Keep the deal inside Orbit — beware "off the app" requests'
];
function safetyChecklistSheet(ackKey,done){
  ui.openSheet(
    '<h2>🛡️ Quick safety check</h2>'+
    '<p class="sub" style="margin:6px 0 12px">First time chatting with this seller. A demo reminder — Orbit runs fully in this browser and is not a moderated marketplace.</p>'+
    '<div>'+SAFETY_ITEMS.map(x=>'<label class="check-row"><input type="checkbox" class="safetyCk"><span>'+ui.esc(x)+'</span></label>').join('')+'</div>'+
    '<button class="btn btn-primary btn-block" id="safetyGo" style="margin-top:14px">Got it — start chat</button>'+
    '<button class="btn btn-ghost btn-block" id="safetySkip" style="margin-top:8px">Skip for now</button>'
  );
  document.getElementById('safetyGo').onclick=()=>{
    const all=[...document.querySelectorAll('.safetyCk')].every(b=>b.checked);
    if(!all){ ui.toast('Please check all five items first'); return; }
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
  return '<div class="demo-note" role="note">⚠️ <b>Demo safety hint:</b> a message here looks like a common scam pattern (“'+ui.esc(hit)+'”). '+
    'Never pay before inspecting the item. This is a local keyword check — not AI moderation or real protection.</div>';
}

/* ---------- openThread ---------- */
function openThread(threadId){
  closeSiblings();
  const t=store.find('threads',threadId);
  if(!t){ ui.toast('Conversation not found'); return; }
  root().hidden=false;
  t.unread=0; store.save(); refreshDot();
  const name=threadName(t), phone=threadPhone(t);
  panel().innerHTML=
    '<div class="chathead">'+
      '<button class="iconbtn" id="chBack" aria-label="Back to chats">←</button>'+
      '<div class="avatar">'+ui.esc(ui.initials(name))+'</div>'+
      '<div class="grow"><h3 style="margin:0">'+ui.esc(name)+'</h3>'+
        '<div class="meta">'+ui.esc(phone)+(t.sample?' · Sample':'')+'</div></div>'+
      '<button class="iconbtn" id="chMore" aria-label="Conversation options">⋯</button>'+
    '</div>'+
    '<div id="chatScroll" style="flex:1;overflow-y:auto;padding:12px 14px;"><div class="bubbles" id="chatBubbles"></div></div>'+
    '<div class="chatinput">'+
      '<input class="input" id="chatText" placeholder="Message" autocomplete="off" maxlength="2000">'+
      '<button class="btn btn-primary" id="chatSend" style="border-radius:999px;padding:12px 18px;flex:0 0 auto" aria-label="Send">➤</button>'+
    '</div>';
  document.getElementById('chBack').onclick=openList;
  document.getElementById('chMore').onclick=()=>threadSheet(t.id);
  document.getElementById('chatSend').onclick=()=>sendMessage(t.id);
  const input=document.getElementById('chatText');
  input.onkeydown=e=>{ if(e.key==='Enter'){ e.preventDefault(); sendMessage(t.id); } };
  renderBubbles(t.id);
  setTimeout(()=>input.focus(),60);
}
function renderBubbles(threadId){
  const t=store.find('threads',threadId);
  const box=document.getElementById('chatBubbles');
  if(!t||!box) return;
  const hit=(t.messages||[]).map(m=>scamHit(m.text)).find(Boolean);
  const banner=hit?scamBannerHTML(hit):'';
  if(!t.messages||!t.messages.length){
    box.innerHTML=banner+'<div class="empty"><div class="big">👋</div><p>No messages yet.<br>Say hi to start the conversation.</p></div>';
  }else{
    box.innerHTML=banner+t.messages.map(m=>
      '<div class="bubble '+(m.from==='me'?'out':'in')+'">'+
        ui.esc(String(m.text||''))+
        '<span class="t">'+ui.esc(ui.timeAgo(m.at||Date.now()))+'</span>'+
      '</div>'
    ).join('');
  }
  scrollBottom();
}
function scrollBottom(){
  const sc=document.getElementById('chatScroll');
  if(sc) sc.scrollTop=sc.scrollHeight;
}
function sendMessage(threadId){
  const t=store.find('threads',threadId);
  const input=document.getElementById('chatText');
  if(!t||!input) return;
  const text=input.value.trim();
  if(!text) return;
  t.messages.push({from:'me',text,at:Date.now()});
  store.save();
  input.value='';
  renderBubbles(t.id);
  // Honesty: no auto-replies — the other side is a real person (or a silent sample).
}

/* ---------- thread options sheet ---------- */
function threadSheet(threadId){
  ui.openSheet(
    '<h2>'+HUB.icons.icon('ic-chat')+' Conversation</h2>'+
    '<p class="sub" style="margin-bottom:14px">'+ui.esc(threadName(store.find('threads',threadId)||{}))+'</p>'+
    '<button class="btn btn-block" id="delThread" style="background:#FEE2E2;color:var(--danger)">🗑 Delete conversation</button>'+
    '<button class="btn btn-ghost btn-block" id="cancelSheet" style="margin-top:8px">Cancel</button>'
  );
  document.getElementById('cancelSheet').onclick=ui.closeSheet;
  document.getElementById('delThread').onclick=()=>{
    store.remove('threads',threadId);
    ui.closeSheet();
    ui.toast('Conversation deleted');
    refreshDot();
    openList();
  };
}

/* ---------- openWith (called by MARKET "Message seller") ---------- */
function openWith(contact,contextMessage){
  if(!contact) return;
  closeSiblings(); // e.g. the market detail sheet must not cover the chat thread
  const name=String(contact.name||'').trim()||'Unknown';
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
  let t=store.state.threads.find(x=>x.contactId===c.id);
  if(!t){
    store.add('threads',{contactId:c.id,listingId:contact.listingId||null,title:c.name,messages:[],unread:0});
    t=store.state.threads.find(x=>x.contactId===c.id);
  }
  // seed first message from context (e.g. "Hi! I'm interested in your listing…")
  if(contextMessage&&t&&(!t.messages||!t.messages.length)){
    t.messages=[{from:'me',text:String(contextMessage),at:Date.now()}];
    store.save();
  }
  // safety checklist on the first chat with this seller (once per seller; persisted in state)
  store.state.safetyAck=store.state.safetyAck||{};
  const ackKey='seller:'+(c.id||name.toLowerCase());
  if(!store.state.safetyAck[ackKey]){ safetyChecklistSheet(ackKey,()=>openThread(t.id)); return; }
  if(t) openThread(t.id);
}

/* ---------- overlay + dot ---------- */
function close(){
  root().hidden=true;
  ui.closeSheet();
}
function refreshDot(){
  const dot=document.getElementById('chatDot');
  if(dot) dot.hidden=!(store.unreadCount()>0);
}

HUB.chat={openList,openThread,openWith,close,refreshDot};
})();
