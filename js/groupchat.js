/* HUB group chat: per-group threads for community groups (2026-09-22).
   Reuses the 1:1 chat overlay (#chatRoot) with group-only polish under the
   .gc-panel class. Message kinds: text | image | file | gif | meme | sys.
   GIF/meme pickers serve ORIGINAL bundled art from chat/memes/ — no external
   APIs, no keys. Browser-local demo data: the thread carries an honest demo
   note, and real multi-device messaging needs a backend.

   Beautification (2026-09-22): elevated bubbles with sender chips +
   deterministic avatar colors, date dividers, reply/quote, reactions,
   presence dots, typing indicators (demo hook + backend-feedable API),
   glass composer with attach sheet + sticker hook, rich group header with
   member grid, join/leave system pills. Read receipts keep working exactly
   as before (HUB.receipts.markSeen / seenCount "Seen by N"). */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };
const root=()=>document.getElementById('chatRoot');
const panel=()=>document.getElementById('chatPanel');

const ART_DIR='chat/memes/';
const STK_DIR='chat/stickers/';
const GIFS=[
  {f:'gif-hype.png',label:'Hype'},
  {f:'gif-facepalm.png',label:'Facepalm'},
  {f:'gif-shocked.png',label:'Shocked'},
  {f:'gif-laugh.png',label:'Laughing'},
  {f:'gif-thumbsup.png',label:'Thumbs up'},
  {f:'gif-clap.png',label:'Clap'},
  {f:'gif-dance.png',label:'Dance'},
  {f:'gif-shrug.png',label:'Shrug'},
  {f:'gif-yes.png',label:'Yes'},
  {f:'gif-no.png',label:'No'},
  {f:'gif-party.png',label:'Party'},
  {f:'gif-goodmorning.png',label:'Good morning'}
];
const MEMES=[
  {f:'meme-morning.png',label:'6AM hike'},
  {f:'meme-approved.png',label:'Approved!'},
  {f:'meme-whiteboard.png',label:'5th time'},
  {f:'meme-snacks.png',label:'Snacks?'},
  {f:'meme-lurker.png',label:'Lurker'}
];
/* Original volt-pack stickers (2026-09-22): AI-generated original art in the
   Onaro Saturn/volt style — no third-party IP. Labels double as search keys. */
const STICKERS=[
  {f:'st-planet.png',label:'Planet'},
  {f:'st-saturn.png',label:'Spin'},
  {f:'st-rocket.png',label:'Rocket'},
  {f:'st-bolt.png',label:'Bolt'},
  {f:'st-thumbsup.png',label:'Thumbs up'},
  {f:'st-laugh.png',label:'LOL'},
  {f:'st-facepalm.png',label:'Facepalm'},
  {f:'st-shocked.png',label:'Shocked'},
  {f:'st-party.png',label:'Party'},
  {f:'st-fire.png',label:'Fire'},
  {f:'st-hundred.png',label:'100'},
  {f:'st-hearts.png',label:'Hearts'},
  {f:'st-clap.png',label:'Clap'},
  {f:'st-sleep.png',label:'Sleepy'},
  {f:'st-coffee.png',label:'Coffee'},
  {f:'st-dumbbell.png',label:'Gym'},
  {f:'st-books.png',label:'Books'},
  {f:'st-pizza.png',label:'Pizza'},
  {f:'st-controller.png',label:'Gaming'},
  {f:'st-trophy.png',label:'Trophy'},
  {f:'st-eyes.png',label:'Eyes'},
  {f:'st-wave.png',label:'Wave'},
  {f:'st-cool.png',label:'Cool'},
  {f:'st-mindblown.png',label:'Mind blown'}
];
/* Standard Unicode emoji only — no IP, renders natively on every device. */
const EMOJI=('😀 😂 🤣 😍 🥰 😎 😭 😤 😴 🤯 🥳 😅 😇 🤔 🙄 🤗 😬 🫡 🥺 🤝 '
  +'👍 👏 🙌 👀 ✌️ 👋 🤙 💪 🔥 💯 ❤️ 💚 🚀 ⚡ 🪐 🌙 ☕ 🍕 🎮 🏆 📚 💡 🎉 ⭐').split(' ');
const MAX_FILE_MB=2;
/* reaction palette for the emoji row sheet (long-press / react button) */
const EMOJIS=['❤️','😂','👍','🔥','😮','😢','🎉','👏'];
/* deterministic sender/avatar palette: [tint bg, strong text]. No purple. */
const AVP=[
  ['#E9F7C4','#40610A'],  /* volt green */
  ['#FDE68A','#92400E'],  /* amber */
  ['#FECACA','#991B1B'],  /* red */
  ['#BFDBFE','#1E40AF'],  /* blue */
  ['#FBCFE8','#9D174D'],  /* pink */
  ['#99F6E4','#0F766E'],  /* teal */
  ['#FED7AA','#9A3412'],  /* orange */
  ['#A7F3D0','#065F46']   /* emerald */
];
function avColor(name){
  const s=String(name||'?'); let h=0;
  for(let i=0;i<s.length;i++) h=(h*31+s.charCodeAt(i))>>>0;
  return AVP[h%AVP.length];
}

/* ---------- helpers ---------- */
function closeSiblings(){
  ui.closeSheet();
  ['search','pulse','notifications'].forEach(function(k){ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
}
function findGroup(id){ return (store.state.cgroups||[]).find(function(g){ return g.id===id; }); }
function isMember(g){
  if(!g) return false;
  if(g.mine) return true;
  const me=String(store.myName()).toLowerCase();
  return (g.members||[]).some(function(n){ return String(n).toLowerCase()===me; });
}
function msgs(g){ if(!Array.isArray(g.chat)) g.chat=[]; return g.chat; }
function findMsg(g,mid){ return msgs(g).find(function(m){ return m&&m.id===mid; }); }
function markSeen(g){
  store.state.cgChatSeen=store.state.cgChatSeen||{};
  store.state.cgChatSeen[g.id]=Date.now();
  /* per-user seen tracking for read receipts (g.seenBy); HUB.receipts is
     defined in chat.js which loads before this module. */
  if(HUB.receipts) HUB.receipts.markSeen(g);
  else store.save();
}
/* member display-names for seen-counts (mirrors groups.js cgMembers:
   mine-groups include the local admin even if not listed). */
function gcMemberNames(g){
  const me=String(store.myName()||'').toLowerCase(), list=(g.members||[]).filter(Boolean);
  if(g.mine&&!list.some(function(n){ return String(n).toLowerCase()===me; })) return list.concat([store.myName()]);
  return list;
}
function gcAdminName(g){ return g.mine?store.myName():(g.admin||''); }
/* demo presence: 'me' is always online; other names come from g.online,
   which the demo store seeds (nothing fake is invented for members). */
function isOnline(g,name){
  if(ui.isMe(name)) return true;
  const me=String(name||'').toLowerCase();
  return (g.online||[]).some(function(n){ return String(n).toLowerCase()===me; });
}
function dispName(m){ return m.from==='me'?t('gc.you'):(m.from||t('chat.unknown')); }
/* linkify: escape everything, then wrap http(s) URLs in safe anchors */
function linkify(s){
  const parts=String(s||'').split(/(https?:\/\/[^\s<>"']+)/g);
  return parts.map(function(p,i){ return i%2===1
    ? '<a class="cblink" href="'+ui.esc(p)+'" target="_blank" rel="noopener">'+ui.esc(p)+'</a>'
    : ui.esc(p); }).join('');
}
function fmtSize(n){
  n=Number(n)||0;
  if(n<1024) return n+' B';
  if(n<1048576) return (n/1024).toFixed(1)+' KB';
  return (n/1048576).toFixed(1)+' MB';
}
/* short preview for notifications, quotes and reply bars */
function previewOf(m){
  const kind=m.kind||'text';
  if(kind==='image') return '📷 '+t('gc.photo');
  if(kind==='gif') return '🎞️ '+t('gc.gif');
  if(kind==='meme') return '😂 '+t('gc.meme');
  if(kind==='sticker') return '🪐 '+t('stk.sticker');
  if(kind==='file') return '📎 '+String(m.name||t('gc.file'));
  if(kind==='sys') return String(m.text||'');
  return String(m.text||'').slice(0,80);
}

/* member count mirrors cgMembers(): mine-groups include the local admin */
function countMembers(g){
  const me=(store.myName()||'').toLowerCase(), list=(g.members||[]).filter(Boolean);
  return (g.mine&&!list.some(function(n){ return String(n).toLowerCase()===me; }))?list.length+1:list.length;
}

/* ---------- date dividers ---------- */
function dayKey(ts){ const d=new Date(Number(ts)||Date.now()); return d.getFullYear()+'-'+d.getMonth()+'-'+d.getDate(); }
function dayLabel(ts){
  const d=new Date(Number(ts)||Date.now()), now=new Date();
  const startOf=function(x){ return new Date(x.getFullYear(),x.getMonth(),x.getDate()).getTime(); };
  const diff=Math.round((startOf(now)-startOf(d))/86400000);
  if(diff===0) return t('gc.today');
  if(diff===1) return t('gc.yesterday');
  return d.toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric'});
}
function dayDivHTML(ts){
  return '<div class="gc-daydiv" aria-hidden="true"><span>'+ui.esc(dayLabel(ts))+'</span></div>';
}

/* ---------- avatar + sender chip ---------- */
function avatarHTML(name,px){
  const c=avColor(name);
  return '<span class="avatar gc-ava" style="--avbg:'+c[0]+';--avtx:'+c[1]+
    ';width:'+px+'px;height:'+px+'px;font-size:'+Math.round(px*0.38)+'px">'+ui.avatarFor(name)+'</span>';
}
function avatarWithDot(g,name,px){
  const c=avColor(name);
  return '<span class="avatar gc-ava" style="--avbg:'+c[0]+';--avtx:'+c[1]+
    ';width:'+px+'px;height:'+px+'px;font-size:'+Math.round(px*0.38)+'px">'+ui.avatarFor(name)+
    (isOnline(g,name)?'<span class="gc-pres" aria-hidden="true"></span>':'')+'</span>';
}
function chipHTML(name){
  const c=avColor(name);
  return '<span class="gc-chip" style="color:'+c[1]+';background:'+c[0]+'">'+ui.esc(name)+'</span>';
}

/* ---------- quote block (replies) ---------- */
function quoteHTML(q){
  if(!q) return '';
  const c=avColor(q.from);
  return '<div class="gc-quote"><div class="qfrom" style="color:'+c[1]+'">'+ui.esc(q.name)+'</div>'+
    '<div class="qprev">'+ui.esc(q.preview)+'</div></div>';
}

/* ---------- reactions ---------- */
function reactsHTML(m){
  if(!m||!m.reacts) return '';
  const keys=Object.keys(m.reacts).filter(function(e){ return (m.reacts[e]||[]).length; });
  if(!keys.length) return '';
  return '<div class="gc-reacts" role="group" aria-label="'+ui.esc(t('gc.reactTitle'))+'">'+keys.map(function(e){
    const arr=m.reacts[e], on=arr.indexOf('me')!==-1;
    return '<button class="gc-react'+(on?' on':'')+'" data-mid="'+m.id+'" data-emo="'+ui.esc(e)+
      '" aria-pressed="'+on+'">'+e+'<span class="n">'+arr.length+'</span></button>';
  }).join('')+'</div>';
}
function toggleReact(g,mid,emoji){
  const m=findMsg(g,mid);
  if(!m||m.from==='sys') return;
  m.reacts=m.reacts||{};
  const arr=m.reacts[emoji]=m.reacts[emoji]||[];
  const ix=arr.indexOf('me');
  if(ix>=0) arr.splice(ix,1); else arr.push('me');
  if(!arr.length) delete m.reacts[emoji];
  store.save();
  if(openGid===g.id) renderBubbles(g);
}
/* demo helper: plant another member's reaction (QA / future backend) */
function addReactAs(g,mid,emoji,name){
  const m=findMsg(g,mid); if(!m||m.from==='sys') return;
  m.reacts=m.reacts||{};
  const arr=m.reacts[emoji]=m.reacts[emoji]||[];
  if(arr.indexOf(name)===-1) arr.push(name);
  store.save();
  if(openGid===g.id) renderBubbles(g);
}

/* ---------- reply state ---------- */
let pendingReply=null; /* {id,from,name,preview,kind} or null */
function setReply(g,mid){
  const m=findMsg(g,mid);
  if(!m||m.from==='sys') return;
  pendingReply={id:mid,from:m.from,name:dispName(m),preview:previewOf(m),kind:m.kind||'text'};
  renderReplyBar();
}
function renderReplyBar(){
  const bar=document.getElementById('gcReplyBar');
  if(!bar) return;
  if(!pendingReply){ bar.hidden=true; bar.innerHTML=''; return; }
  bar.hidden=false;
  bar.innerHTML='<span class="gc-rqline" aria-hidden="true"></span>'+
    '<div class="grow"><div class="qfrom">↩ '+ui.esc(t('gc.replyingTo',{name:pendingReply.name}))+'</div>'+
    '<div class="qprev">'+ui.esc(pendingReply.preview)+'</div></div>'+
    '<button class="iconbtn" id="gcReplyX" aria-label="'+ui.esc(t('chat.closeAria'))+'" style="width:34px;height:34px;font-size:15px">✕</button>';
  document.getElementById('gcReplyX').onclick=function(){ pendingReply=null; renderReplyBar(); };
}

/* ---------- typing indicators ----------
   typingState: {<gid>: {<name>: timeoutId}}. simulateTyping(name,ms) drives
   the demo; onTyping(groupId,name,ms) is the backend-feedable entry point. */
const typingState={};
function onTyping(groupId,name,ms){
  const grp=typingState[groupId]=typingState[groupId]||{};
  if(grp[name]) clearTimeout(grp[name]);
  grp[name]=setTimeout(function(){
    delete grp[name];
    if(openGid===groupId) renderBubbles(findGroup(groupId));
  },Math.max(1000,Math.min(15000,Number(ms)||4000)));
  if(openGid===groupId) renderTypingRow();
}
function simulateTyping(name,ms){ if(openGid) onTyping(openGid,name,ms); }
function renderTypingRow(){
  const box=document.getElementById('gcBubbles');
  if(!box) return;
  const old=document.getElementById('gcTyping');
  if(old) old.remove();
  const grp=openGid?typingState[openGid]:null;
  const names=grp?Object.keys(grp):[];
  if(!names.length) return;
  const g=findGroup(openGid);
  const row=document.createElement('div');
  row.id='gcTyping';
  row.innerHTML=names.map(function(n){
    return '<div class="gc-typing">'+avatarHTML(n,28)+
      '<span class="gc-tdots" aria-hidden="true"><i></i><i></i><i></i></span>'+
      '<span class="gc-twho">'+ui.esc(t('gc.typing',{name:n}))+'</span></div>';
  }).join('');
  box.appendChild(row);
  if(g) scrollBottom();
}

/* ---------- join/leave system messages ---------- */
function systemMsg(groupId,key,vars){
  const g=findGroup(groupId);
  if(!g) return;
  msgs(g).push({id:store.uid(),from:'sys',at:Date.now(),kind:'sys',key:key,vars:vars||{}});
  store.save();
  if(openGid===groupId) renderBubbles(g);
}
function sysText(m){
  if(m.key) return t(m.key,m.vars||{});
  return String(m.text||'');
}

/* ---------- group header ---------- */
function groupAvatarHTML(g){
  if(g.photo) return '<span class="gc-gavatar"><img class="avimg" src="'+g.photo+'" alt=""></span>';
  const c=avColor(g.name||'G');
  return '<span class="gc-gavatar" style="background:'+c[0]+';color:'+c[1]+'">'+ui.esc(g.emoji||ui.initials(g.name))+'</span>';
}
function stackHTML(g){
  const names=gcMemberNames(g), shown=names.slice(0,4), extra=names.length-shown.length;
  let html=shown.map(function(n){ return avatarWithDot(g,n,24); }).join('');
  if(extra>0) html+='<span class="avatar gc-ava gc-more" style="--avbg:var(--surface2);--avtx:var(--faint);width:24px;height:24px;font-size:9px">+'+extra+'</span>';
  return html;
}

/* ---------- member grid sheet ---------- */
function gcSheet(html){
  const sh=document.getElementById('sheetHost');
  if(sh) sh.dataset.gcOwned='1'; /* Escape closes the sheet first, not the chat */
  ui.openSheet(html);
}
function clearGcOwned(){ const sh=document.getElementById('sheetHost'); if(sh) delete sh.dataset.gcOwned; }
function openMembers(gid){
  const g=typeof gid==='string'?findGroup(gid):gid;
  if(!g) return;
  const names=gcMemberNames(g), admin=gcAdminName(g);
  const me=String(store.myName()||'').toLowerCase();
  gcSheet(
    '<h2>'+ui.esc(t('gc.membersTitle'))+' · '+ui.esc(g.name)+'</h2>'+
    '<p class="sub" style="margin:6px 0 2px">'+ui.esc(names.length===1?t('gc.member1'):t('gc.members',{n:names.length}))+'</p>'+
    '<div class="gc-mgrid">'+names.map(function(n){
      const you=String(n).toLowerCase()===me;
      const isAd=admin&&String(n).toLowerCase()===String(admin).toLowerCase();
      return '<div class="gc-mem">'+avatarWithDot(g,n,52)+
        '<span class="gc-mname">'+ui.esc(you?t('gc.you'):n)+'</span>'+
        '<span class="gc-role'+(isAd?' admin':'')+'">'+(isAd?'👑 ':'')+ui.esc(isAd?t('gc.admin'):t('gc.memberRole'))+'</span>'+
        '</div>';
    }).join('')+'</div>'
  );
}

/* ---------- message actions sheet (long-press / react button) ---------- */
function openMsgActions(g,mid){
  const m=findMsg(g,mid);
  if(!m||m.from==='sys') return;
  gcSheet(
    '<h2>'+ui.esc(dispName(m))+'</h2>'+
    '<p class="sub" style="margin:6px 0 2px">'+ui.esc(previewOf(m))+'</p>'+
    '<div class="gc-emorow" role="group" aria-label="'+ui.esc(t('gc.reactTitle'))+'">'+
      EMOJIS.map(function(e){ return '<button data-emo="'+e+'" aria-label="'+ui.esc(t('gc.reactTitle'))+' '+e+'">'+e+'</button>'; }).join('')+
    '</div>'+
    '<button class="btn btn-block" id="gcActReply">↩ '+ui.esc(t('gc.reply'))+'</button>'
  );
  document.querySelectorAll('#sheetBox [data-emo]').forEach(function(b){
    b.onclick=function(){ clearGcOwned(); ui.closeSheet(); toggleReact(g,mid,b.getAttribute('data-emo')); };
  });
  document.getElementById('gcActReply').onclick=function(){ clearGcOwned(); ui.closeSheet(); setReply(g,mid); };
}

/* ---------- attach sheet (+) ---------- */
function plusSheet(g){
  gcSheet(
    '<h2>'+ui.esc(t('gc.shareTitle'))+'</h2>'+
    '<div class="gc-sharegrid">'+
      '<button data-sh="photo"><span class="ic">📷</span><span>'+ui.esc(t('gc.photo'))+'</span></button>'+
      '<button data-sh="file"><span class="ic">📎</span><span>'+ui.esc(t('gc.file'))+'</span></button>'+
      '<button data-sh="gif"><span class="ic">🎞️</span><span>'+ui.esc(t('gc.gif'))+'</span></button>'+
      '<button data-sh="meme"><span class="ic">😂</span><span>'+ui.esc(t('gc.meme'))+'</span></button>'+
    '</div>'
  );
  document.querySelectorAll('#sheetBox [data-sh]').forEach(function(b){
    b.onclick=function(){
      const which=b.getAttribute('data-sh');
      clearGcOwned(); ui.closeSheet();
      if(which==='photo') document.getElementById('gcPhotoIn').click();
      else if(which==='file') document.getElementById('gcFileIn').click();
      else artSheet(g,which);
    };
  });
}

/* ---------- thread ---------- */
let openGid=null;
function open(groupId){
  closeSiblings();
  const g=findGroup(groupId);
  if(!g){ ui.toast(t('gc.notFound')); return; }
  if(!isMember(g)){
    if(HUB.cgroups&&HUB.cgroups.openClub) HUB.cgroups.openClub(groupId);
    return;
  }
  openGid=groupId;
  pendingReply=null;
  root().hidden=false;
  panel().classList.add('gc-panel');
  markSeen(g);
  panel().innerHTML=
    '<div class="chathead gc-head">'+
      '<button class="iconbtn" id="gcBack" aria-label="'+ui.esc(t('chat.backAria'))+'">←</button>'+
      '<button class="gc-headinfo" id="gcHeadInfo" aria-label="'+ui.esc(t('gc.membersTitle'))+'">'+
        groupAvatarHTML(g)+
        '<span class="grow"><h3 style="margin:0">'+ui.esc(g.name)+'</h3>'+
          '<span class="meta">'+ui.esc((function(){ const n=countMembers(g); return n===1?t('gc.member1'):t('gc.members',{n:n}); })())+'</span>'+
          '<span class="gc-stack">'+stackHTML(g)+'</span></span>'+
      '</button>'+
      '<button class="iconbtn" id="gcCall" aria-label="'+ui.esc(t('call.startAria'))+'">📞</button>'+
      '<button class="iconbtn" id="gcClose" aria-label="'+ui.esc(t('chat.closeAria'))+'">✕</button>'+
    '</div>'+
    '<div id="gcScroll" style="flex:1;overflow-y:auto;padding:12px 14px;">'+
      '<div class="demo-note" style="margin-bottom:8px">'+ui.esc(t('gc.demoNote'))+'</div>'+
      '<div class="bubbles" id="gcBubbles"></div>'+
    '</div>'+
    '<div id="gcReplyBar" class="gc-replybar" hidden></div>'+
    '<div class="chatinput gc-composer">'+
      '<button class="iconbtn" id="gcPlus" aria-label="'+ui.esc(t('gc.shareTitle'))+'">＋</button>'+
      '<input type="file" id="gcPhotoIn" accept="image/*" hidden>'+
      '<input type="file" id="gcFileIn" hidden>'+
      '<input class="input" id="gcText" placeholder="'+ui.esc(t('gc.msgPh'))+'" autocomplete="off" maxlength="2000">'+
      '<button class="iconbtn" id="gcEmoji" aria-label="'+ui.esc(t('stk.emojiAria'))+'">😊</button>'+
      '<button id="gcSend" aria-label="'+ui.esc(t('gc.sendAria'))+'">➤</button>'+
    '</div>';
  document.getElementById('gcBack').onclick=close;
  document.getElementById('gcClose').onclick=close;
  /* group voice call entry (js/call.js): 📞 opens the call UI for this group */
  document.getElementById('gcCall').onclick=function(){ if(HUB.call){ if(HUB.call.pickKind) HUB.call.pickKind(groupId); else HUB.call.start(groupId,{outgoing:true}); } };
  if(HUB.call&&HUB.call.watch) HUB.call.watch(groupId); /* worker-mode incoming calls */
  document.getElementById('gcHeadInfo').onclick=function(){ openMembers(g); };
  document.getElementById('gcSend').onclick=function(){ sendText(g); };
  document.getElementById('gcPlus').onclick=function(){ plusSheet(g); };
  /* emoji button opens the existing sticker/art picker (Subagent 2 owns the
     Emoji/GIF/Stickers tabs — openStickerPicker is the clean hook). */
  document.getElementById('gcEmoji').onclick=function(){ HUB.groupchat.openStickerPicker(); };
  document.getElementById('gcPhotoIn').onchange=function(e){ const f=e.target.files[0]; e.target.value=''; if(f) sendPhotoFile(g,f); };
  document.getElementById('gcFileIn').onchange=function(e){ const f=e.target.files[0]; e.target.value=''; if(f) sendFileGeneric(g,f); };
  const input=document.getElementById('gcText');
  input.onkeydown=function(e){ if(e.key==='Enter'){ e.preventDefault(); sendText(g); } };
  /* keyboard dodge (2026-09-22): keep the message list visible above the iOS
     keyboard, like iPhone Messages — meta resizes-content handles modern iOS,
     ui.dodgeKeyboard()'s visualViewport fallback covers the rest */
  ui.dodgeKeyboard();
  input.addEventListener('focus',function(){ ui.kbSnap(); });
  /* delegated bubble taps: image zoom, reaction toggle, react button.
     Long-press (touch) and right-click open the message actions sheet. */
  const box=document.getElementById('gcBubbles');
  let lpTimer=null,lpMid=null,lpFired=false;
  box.addEventListener('touchstart',function(e){
    const row=e.target.closest?e.target.closest('.gc-msg'):null;
    if(!row||!row.dataset.mid) return;
    lpFired=false; lpMid=row.dataset.mid;
    lpTimer=setTimeout(function(){ lpFired=true; openMsgActions(g,lpMid); },550);
  },{passive:true});
  const cancelLp=function(){ if(lpTimer){ clearTimeout(lpTimer); lpTimer=null; } };
  box.addEventListener('touchend',cancelLp);
  box.addEventListener('touchmove',cancelLp);
  box.addEventListener('touchcancel',cancelLp);
  box.addEventListener('contextmenu',function(e){
    const row=e.target.closest?e.target.closest('.gc-msg'):null;
    if(row&&row.dataset.mid){ e.preventDefault(); openMsgActions(g,row.dataset.mid); }
  });
  box.onclick=function(e){
    if(lpFired){ lpFired=false; return; }
    const chip=e.target.closest?e.target.closest('.gc-react'):null;
    if(chip&&chip.dataset.mid){ toggleReact(g,chip.dataset.mid,chip.dataset.emo); return; }
    const rbtn=e.target.closest?e.target.closest('.gc-reactbtn'):null;
    if(rbtn&&rbtn.dataset.mid){ openMsgActions(g,rbtn.dataset.mid); return; }
    const img=e.target.closest?e.target.closest('img.gcimg'):null;
    if(!img||!img.dataset.full) return;
    gcSheet('<h2>'+ui.esc(t('gc.photo'))+'</h2>'
      +'<img src="'+img.dataset.full+'" style="width:100%;border-radius:14px;margin-top:8px" alt="'+ui.esc(t('gc.imgAlt'))+'">');
  };
  renderBubbles(g);
  setTimeout(function(){ const i2=document.getElementById('gcText'); if(i2) i2.focus(); },60);
}
function close(){
  openGid=null;
  pendingReply=null;
  clearGcOwned();
  panel().classList.remove('gc-panel');
  const p=panel(); if(p){ p.style.height=''; p.style.maxHeight=''; p.style.transform=''; } /* drop any keyboard-dodge sizing */
  root().hidden=true;
  ui.closeSheet();
}
function scrollBottom(){
  const sc=document.getElementById('gcScroll');
  if(sc) sc.scrollTop=sc.scrollHeight;
}
function contentHTML(m){
  const kind=m.kind||'text';
  if(kind==='image'||kind==='gif'||kind==='meme'||kind==='sticker'){
    const src=m.data||'';
    const badge=kind==='gif'?'<span class="gcbadge">GIF</span>'
      :kind==='meme'?'<span class="gcbadge">MEME</span>'
      :kind==='sticker'?'<span class="gcbadge">STICKER</span>':'';
    const img=src?'<img class="gcimg'+(kind==='sticker'?' stkimg':'')+'" src="'+src+'" data-full="'+ui.esc(src)+'" alt="'+ui.esc(t('gc.imgAlt'))+'" loading="lazy">':'';
    return badge+img;
  }
  if(kind==='file'){
    const src=m.data||'';
    const dl=src?'<div style="margin-top:6px"><a class="cblink" href="'+src+'" download="'+ui.esc(m.name||'file')+'">'+ui.esc(t('gc.download'))+'</a></div>':'';
    return '<div class="cbfile">📎 <b>'+ui.esc(m.name||t('gc.file'))+'</b>'
      +(m.size!=null?' <span class="meta">'+ui.esc(fmtSize(m.size))+'</span>':'')+'</div>'+dl;
  }
  return linkify(m.text);
}
function msgRowHTML(g,m,continued){
  if(m.from==='sys'||m.kind==='sys'){
    return '<div class="gc-sys" data-mid="'+m.id+'">'+ui.esc(sysText(m))+'</div>';
  }
  const mine=m.from==='me', side=mine?'out':'in';
  const who=mine?store.myName():m.from;
  const av=mine?'':avatarWithDot(g,who,30);
  const chip=mine?'':chipHTML(dispName(m));
  const time='<span class="t">'+ui.esc(ui.timeAgo(m.at||Date.now()))+'</span>';
  return '<div class="gc-msg'+(continued?' gc-cont':'')+'" data-mid="'+m.id+'">'+
    '<div class="gc-row '+side+'">'+av+
    '<div class="gc-bwrap">'+chip+
      '<div class="bubble '+side+'">'+quoteHTML(m.quote)+contentHTML(m)+time+'</div>'+
      reactsHTML(m)+
      '<button class="gc-reactbtn" data-mid="'+m.id+'" aria-label="'+ui.esc(t('gc.reactAria'))+'">＋</button>'+
    '</div></div></div>';
}
function renderBubbles(g){
  const box=document.getElementById('gcBubbles');
  if(!box) return;
  const list=msgs(g);
  if(!list.length){
    box.innerHTML='<div class="empty"><div class="big">👋</div><p>'+t('gc.emptyT')+'<br>'+t('gc.emptyS')+'</p></div>';
  }else{
    /* read receipts in groups: "Seen by N" under my latest own message,
       instead of per-message ticks. N counts members (not me) whose seenBy
       timestamp is at/after that message. */
    let lastMine=-1;
    for(let i=list.length-1;i>=0;i--){ if(list[i].from==='me'){ lastMine=i; break; } }
    const others=gcMemberNames(g);
    let html='', lastDay=null, lastFrom=null;
    list.forEach(function(m,i){
      const dk=dayKey(m.at||Date.now());
      if(dk!==lastDay){ html+=dayDivHTML(m.at); lastDay=dk; lastFrom=null; }
      html+=msgRowHTML(g,m,lastFrom===m.from&&m.from!=='sys');
      lastFrom=m.from;
      if(i===lastMine&&HUB.receipts){
        const n=HUB.receipts.seenCount(g,others,m.at);
        if(n>0) html+='<div class="seennote">'+ui.esc(t('chat.seenBy',{n:n}))+'</div>';
      }
    });
    box.innerHTML=html;
  }
  renderTypingRow();
  scrollBottom();
}
function pushMsg(g,msg){
  msgs(g).push(Object.assign({id:store.uid(),from:'me',at:Date.now()},msg));
  store.save();
  markSeen(g);
  renderBubbles(g);
}
function sendText(g){
  const input=document.getElementById('gcText');
  if(!input) return;
  const text=input.value.trim();
  if(!text) return;
  input.value='';
  const q=pendingReply;
  pendingReply=null;
  renderReplyBar();
  pushMsg(g,{kind:'text',text:text,quote:q?{from:q.from,name:q.name,preview:q.preview,kind:q.kind}:undefined});
}
function readAsDataURL(file){
  return new Promise(function(res,rej){ const r=new FileReader(); r.onload=function(){res(r.result);}; r.onerror=rej; r.readAsDataURL(file); });
}
function downscaleImg(src,maxDim){
  return new Promise(function(res){
    const img=new Image();
    img.onload=function(){
      try{
        let w=img.width,h=img.height;
        const k=Math.min(1,maxDim/Math.max(w,h));
        w=Math.round(w*k); h=Math.round(h*k);
        const c=document.createElement('canvas'); c.width=w; c.height=h;
        c.getContext('2d').drawImage(img,0,0,w,h);
        res(c.toDataURL('image/jpeg',0.8));
      }catch(e){ res(src); }
    };
    img.onerror=function(){ res(src); };
    img.src=src;
  });
}
function sendPhotoFile(g,file){
  readAsDataURL(file).then(function(raw){
    return downscaleImg(raw,800);
  }).then(function(small){
    if(small.length>MAX_FILE_MB*1024*1024){ ui.toast(t('gc.photoTooBig')); return; }
    const q=pendingReply; pendingReply=null; renderReplyBar();
    pushMsg(g,{kind:'image',data:small,name:file.name||'photo.jpg',size:file.size,
      quote:q?{from:q.from,name:q.name,preview:q.preview,kind:q.kind}:undefined});
  }).catch(function(){ ui.toast(t('gc.photoTooBig')); });
}
function sendFileGeneric(g,file){
  if(file.size>MAX_FILE_MB*1024*1024){ ui.toast(t('gc.fileTooBig',{n:MAX_FILE_MB})); return; }
  readAsDataURL(file).then(function(data){
    const q=pendingReply; pendingReply=null; renderReplyBar();
    pushMsg(g,{kind:'file',data:data,name:file.name||'file',size:file.size,
      quote:q?{from:q.from,name:q.name,preview:q.preview,kind:q.kind}:undefined});
  }).catch(function(){ ui.toast(t('gc.fileTooBig',{n:MAX_FILE_MB})); });
}

/* ---------- GIF / meme picker sheets (bundled original art) ---------- */
function artSheet(g,which){
  const list=which==='gif'?GIFS:MEMES;
  const title=t(which==='gif'?'gc.gifTitle':'gc.memeTitle');
  gcSheet(
    '<h2>'+ui.esc(title)+'</h2>'
    +'<p class="sub" style="margin:6px 0 2px">'+ui.esc(t('gc.artNote'))+'</p>'
    +'<div class="artgrid">'
    +list.map(function(a,i){
      return '<button class="artcell" data-art="'+i+'"><img src="'+ART_DIR+a.f+'" alt="'+ui.esc(a.label)+'" loading="lazy"><span>'+ui.esc(a.label)+'</span></button>';
    }).join('')+'</div>'
  );
  document.querySelectorAll('#sheetBox [data-art]').forEach(function(cell){
    cell.onclick=function(){
      const a=list[Number(cell.dataset.art)];
      if(!a) return;
      clearGcOwned();
      ui.closeSheet();
      const q=pendingReply; pendingReply=null; renderReplyBar();
      pushMsg(g,{kind:which,data:ART_DIR+a.f,name:a.label,
        quote:q?{from:q.from,name:q.name,preview:q.preview,kind:q.kind}:undefined});
    };
  });
}

/* ---------- unified sticker/GIF/emoji picker (2026-09-22) ----------
   Glass bottom sheet with three tabs: Emoji (unicode), GIFs (bundled original
   art, incl. memes), Stickers (original volt-pack in chat/stickers/).
   Recents persist browser-local in store.state.stickerRecents.
   This is the composer 😊 hook: HUB.groupchat.openStickerPicker(opts),
   opts={tab:'emoji'|'gifs'|'stickers', onArt(item), onEmoji(ch)};
   item={kind:'gif'|'meme'|'sticker', src, label}. With no opts it sends into
   the currently open group thread (quote-aware, like artSheet). */
let stkTab='stickers', stkQuery='';
function gifTabItems(){
  return GIFS.map(function(a){ return {kind:'gif',src:ART_DIR+a.f,label:a.label}; })
    .concat(MEMES.map(function(a){ return {kind:'meme',src:ART_DIR+a.f,label:a.label}; }));
}
function stickerItems(){
  return STICKERS.map(function(a){ return {kind:'sticker',src:STK_DIR+a.f,label:a.label}; });
}
function getRecents(){
  const r=store.state.stickerRecents;
  return Array.isArray(r)?r:[];
}
function pushRecent(item){
  const list=getRecents().filter(function(x){ return x.src!==item.src; });
  list.unshift({kind:item.kind,src:item.src,label:item.label});
  store.state.stickerRecents=list.slice(0,12);
  try{ store.save(); }catch(e){}
}
/* insert an emoji at the cursor of a composer input; the sheet stays open so
   people can stack several emoji before dismissing it */
function insertEmoji(inputId,ch){
  const el=document.getElementById(inputId);
  if(!el) return;
  const s=(el.selectionStart!=null)?el.selectionStart:el.value.length;
  const e=(el.selectionEnd!=null)?el.selectionEnd:s;
  el.value=el.value.slice(0,s)+ch+el.value.slice(e);
  const pos=s+ch.length;
  el.focus();
  try{ el.setSelectionRange(pos,pos); }catch(err){}
}
function paintPicker(opts){
  const recWrap=document.getElementById('stkRecWrap'), gridWrap=document.getElementById('stkGridWrap');
  if(!recWrap||!gridWrap) return;
  const q=stkQuery.trim().toLowerCase();
  const recs=getRecents();
  if(q||!recs.length){ recWrap.innerHTML=''; }
  else{
    recWrap.innerHTML='<div class="stkreclabel">'+ui.esc(t('stk.recents'))+'</div>'
      +'<div class="stkrec">'+recs.map(function(r,i){
        return '<button data-rec="'+i+'" aria-label="'+ui.esc(r.label)+'"><img src="'+ui.esc(r.src)+'" alt="" loading="lazy"></button>';
      }).join('')+'</div>';
    recWrap.querySelectorAll('[data-rec]').forEach(function(btn){
      btn.onclick=function(){
        const item=recs[Number(btn.dataset.rec)];
        if(!item) return;
        pickArt(opts,item);
      };
    });
  }
  if(stkTab==='emoji'){
    gridWrap.innerHTML=q
      ? '<div class="empty"><p>'+ui.esc(t('stk.none'))+'</p></div>'
      : '<div class="stkgrid">'+EMOJI.map(function(ch){
          return '<button class="stkcell emj" data-emj="'+ui.esc(ch)+'">'+ch+'</button>';
        }).join('')+'</div>';
    gridWrap.querySelectorAll('[data-emj]').forEach(function(btn){
      btn.onclick=function(){ if(opts.onEmoji) opts.onEmoji(btn.getAttribute('data-emj')); };
    });
    return;
  }
  const pool=stkTab==='stickers'?stickerItems():gifTabItems();
  const items=pool.filter(function(a){ return !q||a.label.toLowerCase().indexOf(q)!==-1; });
  gridWrap.innerHTML=items.length
    ? '<div class="'+(stkTab==='stickers'?'stkgrid':'artgrid')+'">'+items.map(function(a,i){
        return '<button class="artcell" data-art="'+i+'"><img src="'+ui.esc(a.src)+'" alt="'+ui.esc(a.label)+'" loading="lazy"><span>'+ui.esc(a.label)+'</span></button>';
      }).join('')+'</div>'
    : '<div class="empty"><p>'+ui.esc(t('stk.none'))+'</p></div>';
  gridWrap.querySelectorAll('[data-art]').forEach(function(cell){
    cell.onclick=function(){
      const item=items[Number(cell.dataset.art)];
      if(item) pickArt(opts,item);
    };
  });
}
function pickArt(opts,item){
  pushRecent(item);
  clearGcOwned();
  ui.closeSheet();
  if(opts.onArt) opts.onArt(item);
}
function openStickerPicker(opts){
  opts=opts||{};
  const g=findGroup(openGid);
  const inGroup=!!g;
  if(!opts.onArt&&!inGroup) return;
  stkTab=opts.tab||'stickers';
  stkQuery='';
  const eff={
    onArt:opts.onArt||function(item){
      const q=pendingReply; pendingReply=null; renderReplyBar();
      pushMsg(g,{kind:item.kind,data:item.src,name:item.label,
        quote:q?{from:q.from,name:q.name,preview:q.preview,kind:q.kind}:undefined});
    },
    onEmoji:opts.onEmoji||function(ch){ insertEmoji('gcText',ch); }
  };
  gcSheet(
    '<h2>😊 '+ui.esc(t('stk.title'))+'</h2>'
    +'<p class="sub" style="margin:6px 0 2px">'+ui.esc(t('stk.artNote'))+'</p>'
    +'<div class="stktabs" role="tablist">'
    +['emoji','gifs','stickers'].map(function(id){
        return '<button class="stktab'+(stkTab===id?' on':'')+'" data-stktab="'+id+'" role="tab">'+ui.esc(t('stk.'+id))+'</button>';
      }).join('')+'</div>'
    +'<input class="input" id="stkSearch" placeholder="'+ui.esc(t('stk.search'))+'" autocomplete="off" style="margin-bottom:4px">'
    +'<div id="stkRecWrap"></div>'
    +'<div id="stkGridWrap"></div>'
  );
  document.querySelectorAll('#sheetBox [data-stktab]').forEach(function(btn){
    btn.onclick=function(){
      stkTab=btn.dataset.stktab;
      document.querySelectorAll('#sheetBox [data-stktab]').forEach(function(b){
        b.classList.toggle('on',b===btn);
      });
      paintPicker(eff);
    };
  });
  const search=document.getElementById('stkSearch');
  if(search) search.oninput=function(){ stkQuery=search.value; paintPicker(eff); };
  paintPicker(eff);
}

/* ---------- overlay dismissal ----------
   Backdrop tap closes; Escape steps back through layers: an open group-owned
   sheet (members / actions / attach / zoom) closes first (capture phase, so
   app.js's global Escape handler and chat.js's fallback never also fire);
   otherwise chat.js's handler falls through to close() since our back button
   is #gcBack, not #chBack. */
(function(){
  const r=root(); if(!r||r.dataset.gcBound) return; r.dataset.gcBound='1';
  r.addEventListener('click',function(e){ if(e.target===r) close(); });
  document.addEventListener('keydown',function(e){
    if(e.key!=='Escape'||!openGid) return;
    const sh=document.getElementById('sheetHost');
    if(sh&&!sh.hidden&&sh.dataset.gcOwned){
      e.stopPropagation();
      delete sh.dataset.gcOwned;
      ui.closeSheet();
    }
  },true);
  /* never leak the group-owned marker into another module's sheet: the flag
     dies the moment the sheet host hides, on ANY close path (backdrop tap,
     ✕, programmatic). */
  const sh0=document.getElementById('sheetHost');
  if(sh0&&!sh0.dataset.gcObs){
    sh0.dataset.gcObs='1';
    new MutationObserver(function(){ if(sh0.hidden) delete sh0.dataset.gcOwned; })
      .observe(sh0,{attributes:true,attributeFilter:['hidden']});
  }
})();

HUB.gchat={open:open,close:close,isMember:isMember,previewOf:previewOf,markSeen:markSeen,findGroup:findGroup};
/* Extended namespace: same core plus the beautification hooks the track
   requires — sticker picker, typing (demo + backend-feedable), system
   messages, reply/member APIs. */
HUB.groupchat={open:open,close:close,isMember:isMember,previewOf:previewOf,markSeen:markSeen,findGroup:findGroup,
  openStickerPicker:openStickerPicker,insertEmoji:insertEmoji,simulateTyping:simulateTyping,onTyping:onTyping,
  systemMsg:systemMsg,setReply:setReply,toggleReact:toggleReact,addReactAs:addReactAs,openMembers:openMembers};
})();
