/* HUB group voice calls (2026-09-22): real WebRTC voice for community groups.
   - HUB.call.start(groupId) captures the mic (getUserMedia) and opens the
     full-screen glass call UI. One RTCPeerConnection per peer, FREE Google
     STUN (stun:stun.l.google.com:19302), full-mesh offer/answer/ICE with a
     deterministic offer rule (smaller peerId offers) so there is no glare.
   - Pluggable signaling. HUB.call.signal is the ACTIVE adapter; two ship:
       LoopbackSignal (default) — same-browser tabs only, via localStorage
         message keys + storage events. Honestly labeled everywhere as demo.
       WorkerSignal — WebSocket client for the free Cloudflare Worker in
         server/signaling-worker.js. Real multi-device calls once PraBin
         deploys it from his own Cloudflare account (free tier) and pastes
         the URL (tap the demo label in the call UI).
     The UI NEVER claims a real call without the worker: loopback sessions
     carry "Demo — deploy the free signaling worker for real calls."
   - Speaking indicator (PraBin's order): a 3D volt glow on the tile — the
     tile lifts toward the viewer with a glowing volt ring + halo while the
     person talks, fully off when silent. Real VAD: AnalyserNode on every
     remote stream AND the local mic, RMS threshold with ~500ms hangover so
     it doesn't flicker on syllables. prefers-reduced-motion gets a static
     ring with no pulse.
   - Admins: the group creator (g.mine) can mute anyone and promote members
     to subadmin (persisted g.callAdmins=[names]); subadmins can mute members
     (never the admin). Mute is enforced on the target's client (mic track
     disabled) and shown as "Muted by Name"; the muted user gets an honest
     notice + "request unmute". No fake participants: tiles exist only for
     the local user and peers that actually announced over signaling.
   - Speaker button (PraBin's order): one tap mutes ALL incoming call audio
     (remote <audio> elements), tap again restores — clear OFF state with a
     slash icon and sunken dome. Loudspeaker<->earpiece routing is a SEPARATE
     compact pill in the call header, enabled only where the platform really
     allows web audio routing (setSinkId + 2+ outputs); elsewhere it is
     disabled with an honest note — never a fake switch.
   - Raise hand (PraBin's order): hand dome in the dock; raised = volt glow
     + volt hand badge on the tile for everyone. Admins/subadmins get a
     "Let speak" action that unmutes the raiser (if muted) and lowers the
     hand; the raiser can lower their own hand by tapping the dome again.
     Wired as raise-hand/lower-hand messages on both signaling adapters.
   - Browser-local demo state: onaro_call_active (incoming-call banner across
     tabs), store.state.callRoster (call membership).
   - Escape: app.js defers its global Escape handler while .callroot is
     visible; this module closes the admin sheet first, otherwise leaves.
   Load order: after js/groupchat.js (uses HUB.gchat.findGroup/isMember). */
(function(){
'use strict';
const {store,ui}=HUB;
const t=function(k,v){ return HUB.i18n.t(k,v); };
const STUN={iceServers:[{urls:'stun:stun.l.google.com:19302'}]};
const LS_ACTIVE='onaro_call_active';
const LS_MSGP='onaro_call_msg_';
/* VAD: 512-sample analyser, RMS over the time domain, ~0.02 threshold,
   500ms hangover, checked every 120ms. */
const VAD={fft:512,threshold:0.02,hangover:500,interval:120};
const PEER_TIMEOUT=25000, PING_EVERY=10000;
/* custom 3D-dock icons: hand-drawn stroke SVGs in the app's visual language
   (no emoji glyphs). currentColor so CSS drives the state colors. */
const IC_MIC='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="2.5" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0"/><path d="M12 17.5V21"/><path d="M9 21h6"/></svg>';
const IC_MICMUTED='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="2.5" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0"/><path d="M12 17.5V21"/><path d="M9 21h6"/><path d="M4 4l16 16"/></svg>';
const IC_SPK='<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" stroke="none" d="M11 5 6.8 9H4a1 1 0 0 0-1 1v4a1 1 0 0 0 1 1h2.8L11 19V5z"/><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M15 9.5a4 4 0 0 1 0 5"/></svg>';
const IC_SPKON='<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" stroke="none" d="M11 5 6.8 9H4a1 1 0 0 0-1 1v4a1 1 0 0 0 1 1h2.8L11 19V5z"/><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M15 9.5a4 4 0 0 1 0 5"/><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M17.8 7a8 8 0 0 1 0 10"/></svg>';
/* speaker-output muted (PraBin's order: one tap mutes ALL incoming audio):
   speaker body + waves + slash, same hand-drawn stroke language. */
const IC_SPKOFF='<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" stroke="none" d="M11 5 6.8 9H4a1 1 0 0 0-1 1v4a1 1 0 0 0 1 1h2.8L11 19V5z"/><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M15 9.5a4 4 0 0 1 0 5"/><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M4 4l16 16"/></svg>';
/* raise-hand: hand-drawn raised hand in the same stroke language. */
const IC_HAND='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 11.5V6a1.5 1.5 0 0 1 3 0v4.5"/><path d="M12 10.5V4.8a1.5 1.5 0 0 1 3 0V11"/><path d="M15 11V6.2a1.5 1.5 0 0 1 3 0v7.3c0 3.4-2.2 6-5.4 6-2.3 0-3.9-1.1-5.1-3.1L5.3 13a1.55 1.55 0 0 1 2.7-1.5l1 1.7"/></svg>';
/* loudspeaker<->earpiece route switch (PraBin's refinement): earpiece is the
   classic handset glyph; loudspeaker reuses IC_SPKON (speaker+double waves). */
const IC_EAR='<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/></svg>';

/* ---- demo-20: 20 simulated participants (PraBin's order) ----
   Clearly separated from the real call path: demo peers never touch
   signaling, produce no audio, and carry demo20:true so nothing leaks
   into real calls. PraBin is always admin here so he can try every
   admin control (mute/unmute, subadmin, let-speak) on fake people. */
const DEMO20_NAMES=['Aarav Sharma','Bianca Reyes','Chandra Rai','Diya Patel','Ethan Lim',
  'Fatima Noor','Gaurav Thapa','Hana Sato','Ishaan Verma','Julia Karki',
  'Kabir Singh','Luna Park','Milan Shrestha','Nina Gurung','Oscar Rai',
  'Priya Nair','Rohan Adhikari','Sara Tamang','Tenzin Lama','Uma Devi'];
const IC_END='<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z" transform="rotate(135 12 12)"/></svg>';

function findGroup(id){ return HUB.gchat?HUB.gchat.findGroup(id):(store.state.cgroups||[]).find(function(g){ return g.id===id; }); }
function isMember(g){ return HUB.gchat?HUB.gchat.isMember(g):!!g; }
function myName(){ return store.myName(); }
function lower(s){ return String(s||'').toLowerCase(); }
function isSelfName(n){ return lower(n)===lower(myName()); }

/* ================= signaling adapters =================
   Adapter contract:
     connect(opts:{groupId,callId,peerId,name,role,watch}) -> Promise
     send(m)            m:{to?,kind,...} kind: hello|welcome|bye|ping|offer|answer|ice|role
     mute(targetPeerId,byName) / unmute(targetPeerId,byName)
     requestUnmute(adminPeerIds,fromName)
     on(evt,fn)        evt: peer|left|sdp|ice|mute|unmute|role|unmuteReq|hand|handLower|closed|call-started|call-ended
     leave()
     raiseHand(raised) broadcasts my hand state; lowerHand(target,byName)
       asks the target's client to drop its hand (admin "Let speak"). */
function LoopbackSignal(){
  const handlers={};
  let me=null, groupId=null, nm='', rl='member', bound=false, pruned=false;
  function emit(kind,m){ (handlers[kind]||[]).forEach(function(fn){ try{fn(m);}catch(e){} }); }
  function route(m){
    if(!m||m.g!==groupId||m.from===me) return;
    if(m.to&&m.to!==me) return;
    const k=m.kind;
    if(k==='hello'){ emit('peer',{peerId:m.from,name:m.name,role:m.role}); api.send({to:m.from,kind:'welcome',name:nm,role:rl}); }
    else if(k==='welcome'){ emit('peer',{peerId:m.from,name:m.name,role:m.role}); }
    else if(k==='bye'){ emit('left',{peerId:m.from}); }
    else if(k==='ping'){ emit('ping',{peerId:m.from}); }
    else if(k==='offer'||k==='answer'){ emit('sdp',{from:m.from,kind:k,sdp:m.sdp}); }
    else if(k==='ice'){ emit('ice',{from:m.from,candidate:m.candidate}); }
    else if(k==='mute'){ emit('mute',{target:me,byName:m.byName,muted:true}); }
    else if(k==='unmute'){ emit('unmute',{target:me,byName:m.byName}); }
    else if(k==='mute-state'){ emit(m.muted?'mute':'unmute',{target:m.target,byName:m.byName,muted:!!m.muted}); }
    else if(k==='role'){ emit('role',{name:m.name,role:m.role,byName:m.byName}); }
    else if(k==='unmute-request'){ emit('unmuteReq',{from:m.from,fromName:m.fromName}); }
    else if(k==='raise-hand'){ emit('hand',{from:m.from,name:m.name,raised:!!m.raised}); }
    else if(k==='lower-hand'){ emit('handLower',{byName:m.byName}); }
  }
  function onStorage(e){
    if(!e.key||e.key.indexOf(LS_MSGP)!==0||!e.newValue) return;
    let m=null; try{ m=JSON.parse(e.newValue); }catch(err){ return; }
    route(m);
  }
  function prune(){
    /* drop stale message keys so a crashed tab doesn't fill localStorage */
    try{
      const cut=Date.now()-120000, rm=[];
      for(let i=0;i<localStorage.length;i++){
        const k=localStorage.key(i);
        if(k&&k.indexOf(LS_MSGP+groupId)===0){
          let at=0; try{ at=JSON.parse(localStorage.getItem(k)).at||0; }catch(e){}
          if(at<cut) rm.push(k);
        }
      }
      rm.forEach(function(k){ localStorage.removeItem(k); });
    }catch(e){}
  }
  const api={
    mode:'loopback',
    connect:function(opts){
      me=opts.peerId; groupId=opts.groupId; nm=opts.name; rl=opts.role;
      if(!pruned){ pruned=true; prune(); }
      if(!bound){ bound=true; window.addEventListener('storage',onStorage); }
      api.send({to:null,kind:'hello',name:nm,role:rl});
      return Promise.resolve();
    },
    send:function(m){
      if(!me) return;
      m.g=groupId; m.from=me; m.at=Date.now();
      try{ localStorage.setItem(LS_MSGP+groupId+'_'+me+'_'+Math.random().toString(36).slice(2),JSON.stringify(m)); }
      catch(e){}
    },
    mute:function(target,byName){
      api.send({to:target,kind:'mute',byName:byName});
      api.send({to:null,kind:'mute-state',target:target,byName:byName,muted:true});
    },
    unmute:function(target,byName){
      api.send({to:target,kind:'unmute',byName:byName});
      api.send({to:null,kind:'mute-state',target:target,byName:byName,muted:false});
    },
    requestUnmute:function(adminIds,fromName){
      (adminIds||[]).forEach(function(id){ api.send({to:id,kind:'unmute-request',fromName:fromName}); });
    },
    raiseHand:function(raised){
      api.send({to:null,kind:'raise-hand',name:nm,raised:!!raised});
    },
    lowerHand:function(target,byName){
      api.send({to:target,kind:'lower-hand',byName:byName});
    },
    setRole:function(name,role,byName){
      api.send({to:null,kind:'role',name:name,role:role,byName:byName||nm});
    },
    isLive:function(){ return false; }, /* loopback is always the demo path */
    on:function(kind,fn){ (handlers[kind]=handlers[kind]||[]).push(fn); },
    leave:function(){
      try{ api.send({to:null,kind:'bye'}); }catch(e){}
      if(bound){ bound=false; window.removeEventListener('storage',onStorage); }
      me=null;
    }
  };
  return api;
}
function WorkerSignal(url){
  const handlers={};
  let ws=null, me=null, connected=false;
  function emit(kind,m){ (handlers[kind]||[]).forEach(function(fn){ try{fn(m);}catch(e){} }); }
  function handle(m){
    /* Validate inbound shape: a malformed server message must never throw
       uncaught inside ws.onmessage. */
    if(!m||typeof m!=='object') return;
    const ty=typeof m.type==='string'?m.type:'';
    const str=function(v){ return typeof v==='string'?v:''; };
    if(ty==='welcome'){
      const peers=Array.isArray(m.peers)?m.peers:[];
      peers.forEach(function(p){
        if(!p||typeof p!=='object') return;
        emit('peer',{peerId:str(p.peerId),name:str(p.name),role:str(p.role),muted:!!p.muted,mutedBy:str(p.mutedBy)});
      });
      emit('welcomeInfo',{isFirst:!!m.isFirst,callId:str(m.callId)});
    }
    else if(ty==='peer-join'){ const p=(m.peer&&typeof m.peer==='object')?m.peer:null; if(p) emit('peer',{peerId:str(p.peerId),name:str(p.name),role:str(p.role)}); }
    else if(ty==='peer-leave'){ emit('left',{peerId:str(m.peerId)}); }
    else if(ty==='signal'){
      if(m.kind==='offer'||m.kind==='answer') emit('sdp',{from:str(m.from),kind:m.kind,sdp:m.data});
      else if(m.kind==='ice') emit('ice',{from:str(m.from),candidate:m.data});
    }
    else if(ty==='muted'){ emit('mute',{target:str(m.target),byName:str(m.byName),muted:true}); }
    else if(ty==='unmuted'){ emit('unmute',{target:str(m.target),byName:str(m.byName)}); }
    else if(ty==='unmute-request'){ emit('unmuteReq',{from:str(m.from),fromName:str(m.fromName)}); }
    else if(ty==='role-changed'){ emit('role',{name:str(m.name),role:str(m.role),byName:str(m.by)}); }
    else if(ty==='hand'){ if(m.from!==me) emit('hand',{from:str(m.from),name:str(m.name),raised:!!m.raised}); }
    else if(ty==='lower-hand'){ emit('handLower',{}); }
    else if(ty==='call-started'){ emit('call-started',{callId:str(m.callId),by:str(m.by),at:m.at}); }
    else if(ty==='call-ended'){ emit('call-ended',{}); }
    else if(ty==='error'){ emit('wsError',{message:str(m.message)}); }
  }
  const api={
    mode:'worker',
    connect:function(opts){
      me=opts.peerId;
      return new Promise(function(res,rej){
        let u=url;
        if(u.indexOf('https://')===0) u='wss://'+u.slice(8); /* allow pasting https://… */
        else if(u.indexOf('http://')===0) u='ws://'+u.slice(7);
        try{ ws=new WebSocket(u+(u.indexOf('?')>=0?'&':'?')+'room='+encodeURIComponent(opts.groupId)); }
        catch(e){ rej(e); return; }
        const to=setTimeout(function(){ rej(new Error('timeout')); },12000);
        ws.onopen=function(){
          clearTimeout(to);
          connected=true;
          ws.send(JSON.stringify(opts.watch
            ? {type:'join',room:opts.groupId,watch:true}
            : {type:'join',room:opts.groupId,name:opts.name,role:opts.role,peerId:opts.peerId}));
          res();
        };
        ws.onmessage=function(ev){ let m=null; try{ m=JSON.parse(ev.data); }catch(e){} handle(m); };
        ws.onerror=function(){ clearTimeout(to); rej(new Error('ws')); };
        ws.onclose=function(){ connected=false; emit('closed',{}); };
      });
    },
    send:function(m){
      if(!ws||ws.readyState!==1) return;
      ws.send(JSON.stringify({type:'signal',to:m.to||null,kind:m.kind,data:m.kind==='offer'||m.kind==='answer'?m.sdp:(m.kind==='ice'?m.candidate:undefined)}));
    },
    mute:function(target,byName){ if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'mute',target:target})); },
    unmute:function(target,byName){ if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'unmute',target:target})); },
    requestUnmute:function(adminIds,fromName){ if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'request-unmute'})); },
    raiseHand:function(raised){ if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'raise-hand',raised:!!raised})); },
    lowerHand:function(target){ if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'lower-hand',target:target})); },
    setRole:function(name,role){ if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'role',name:name,role:role})); },
    isLive:function(){ return connected&&!!ws&&ws.readyState===1; },
    on:function(kind,fn){ (handlers[kind]=handlers[kind]||[]).push(fn); },
    leave:function(){ try{ if(ws) ws.send(JSON.stringify({type:'leave'})); }catch(e){} try{ if(ws) ws.close(); }catch(e){} ws=null; me=null; }
  };
  return api;
}

/* ================= session ================= */
let sess=null;
let bannerSuppressed={};
/* which callId is currently shown as incoming (idempotency: the 20s
   announcement heartbeat rewrites LS_ACTIVE, which fires storage events in
   other tabs — without this guard the full-screen incoming UI would re-pop
   on every heartbeat). Cleared by hideBanner(). */
let shownIncomingId=null;
const watchers={};

function root(){ return document.getElementById('callRoot'); }
function bannerEl(){ return document.getElementById('callBanner'); }
function defaultRole(g){
  if(g.mine) return 'admin';
  const me=lower(myName());
  if((g.callAdmins||[]).some(function(n){ return lower(n)===me; })) return 'subadmin';
  return 'member';
}
function canAdmin(){ return !!sess&&(sess.role==='admin'||sess.role==='subadmin'); }
function canMutePeer(p){
  if(!canAdmin()||!p) return false;
  if(p.role==='admin') return false;
  if(sess.role==='subadmin'&&p.role==='subadmin') return false;
  return true;
}
function fmtDur(ms){
  const s=Math.max(0,Math.floor(ms/1000)), h=Math.floor(s/3600), m=Math.floor(s%3600/60), ss=s%60;
  const p=function(n){ return (n<10?'0':'')+n; };
  return (h?h+':':'')+p(m)+':'+p(ss);
}

function ensureRoot(){
  if(root()) return;
  const d=document.createElement('div');
  d.className='callroot'; d.id='callRoot'; d.hidden=true;
  d.innerHTML=
    '<div class="callwrap">'
    +'<div class="callhead"><div class="grow"><h2 id="callTitle"></h2><div class="meta" id="callSub"></div></div>'
    +'<button class="callroute" id="callRoute" hidden><span class="cb-face"></span><span class="cb-cap" id="callRouteCap"></span></button>'
    +'<div class="calltimer" id="callTimer">0:00</div></div>'
    +'<div class="callroutenote" id="callRouteNote" hidden></div>'
    +'<div class="calldemo" id="callDemoLabel" role="button" tabindex="0" style="cursor:pointer"></div>'
    +'<div class="calladminrow" id="callAdminRow" hidden><button class="callmuteall" id="callMuteAll">'+HUB.icons.icon('call-micmute','mab-ico')+'<span>'+ui.esc(t('call.muteAll'))+'</span></button></div>'
    +'<div class="calltiles" id="callTiles"></div>'
    +'<div class="callhint" id="callHint" hidden></div>'
    +'<div class="callnotice" id="callNotice" hidden></div>'
    +'<div class="callerror" id="callError" hidden></div>'
    +'<div class="callcontrols" id="callControls" hidden>'
    +'<div class="cb-wrap"><button class="callbtn cblive" id="callMic" aria-label="'+ui.esc(t('call.micMute'))+'"><span class="cb-ic"><span class="cb-face cb-front">'+IC_MIC+'</span><span class="cb-face cb-back">'+IC_MICMUTED+'</span></span></button><span class="cb-label" id="callMicCap"></span></div>'
    +'<div class="cb-wrap"><button class="callbtn" id="callSpk" aria-label="'+ui.esc(t('call.speaker'))+'"><span class="cb-ic"><span class="cb-face cb-front">'+IC_SPK+'</span><span class="cb-face cb-back">'+IC_SPKOFF+'</span></span></button><span class="cb-label" id="callSpkCap"></span></div>'
    +'<div class="cb-wrap"><button class="callbtn" id="callHand" aria-label="'+ui.esc(t('call.raiseHand'))+'"><span class="cb-ic"><span class="cb-face">'+IC_HAND+'</span></span></button><span class="cb-label" id="callHandCap"></span></div>'
    +'<div class="cb-wrap"><button class="callbtn callleave" id="callLeave" aria-label="'+ui.esc(t('call.leaveAria'))+'"><span class="cb-ic"><span class="cb-face">'+IC_END+'</span></span></button><span class="cb-label" id="callLeaveCap"></span></div>'
    +'</div>'
    +'<div class="callremoteaudio" id="callAudio" aria-hidden="true"></div>'
    +'<div class="callsheet" id="callSheet" hidden><div class="callsheet-box" id="callSheetBox"></div></div>'
    +'</div>';
  document.body.appendChild(d);
  /* incoming-call banner (top, glass) */
  const b=document.createElement('div');
  b.className='callbanner'; b.id='callBanner'; b.hidden=true;
  document.body.appendChild(b);
  document.getElementById('callMic').onclick=toggleMic;
  document.getElementById('callSpk').onclick=toggleSpeaker;
  document.getElementById('callHand').onclick=toggleHand;
  document.getElementById('callRoute').onclick=cycleRoute;
  document.getElementById('callLeave').onclick=function(){ leave(); };
  document.getElementById('callMuteAll').onclick=muteAll;
  document.getElementById('callDemoLabel').onclick=openWorkerSheet;
  document.getElementById('callDemoLabel').onkeydown=function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); openWorkerSheet(); } };
}

/* ---------- public entry ---------- */
/* ---- call-kind picker (PraBin's order): a real voice call, or an
   honestly-labeled demo with 20 simulated people to try the admin
   controls on. The demo never touches signaling or real audio. */
/* ================= outgoing ringback tone =================
   Classic North American ringback: 440Hz + 480Hz dual tone, 2s on / 4s off,
   looping. WebAudio only — no audio files. Heard ONLY by the caller while
   waiting for someone to pick up: starts on outgoing start(), stops when the
   first peer joins ('peer' event), on mic-denied, on switchToDemo20, and on
   EVERY teardown path via leave(). The callee side never plays it (they get
   the Aurora Soft ringtone through HUB.sound instead). Explicitly requested
   call audio — same allowed category as the ringtone, not a UI sound. */
let rbTimer=0, rbNodes=null;
/* WhatsApp/carrier-style no-answer timeout: an unanswered call hangs up by
   itself after NO_ANSWER_MS (45s, like WhatsApp's ring window) instead of
   ringing forever. Caller side: ringback stops, the call tears down, and a
   popup says no user is available. Callee side: the incoming ringtone/UI
   just goes quiet. PraBin's order, 2026-09-30. */
let NO_ANSWER_MS=45000, rbNoAnswerT=0, incNoAnswerT=0;
function noAnswerTimeout(){
  rbNoAnswerT=0;
  /* someone joined in the meantime — the peer handler already stopped us */
  if(!sess||!sess.outgoing) return;
  if(sess.peers&&Object.keys(sess.peers).length) return;
  ringbackStop();
  leave(); /* full teardown first — it closes sheets, then we pop the message */
  ui.openSheet(
    '<div class="sheeticon">📞</div>'+
    '<h3 style="margin:0 0 8px">'+ui.esc(t('call.noAnswerT'))+'</h3>'+
    '<p style="margin:0 0 14px">'+ui.esc(t('call.noAnswerD'))+'</p>'+
    '<button class="btn btn-primary btn-block" id="callNoAnswerOk">'+ui.esc(t('common.ok'))+'</button>'
  );
  document.getElementById('callNoAnswerOk').onclick=ui.closeSheet;
}
function ringbackStart(){
  if(rbTimer||rbNodes) return; /* already ringing */
  try{
    const AC=window.AudioContext||window.webkitAudioContext;
    if(!AC) return;
    const ctx=new AC();
    if(ctx.state==='suspended'){ try{ ctx.resume().catch(function(){}); }catch(e){} }
    const gain=ctx.createGain();
    gain.gain.value=0.0001;
    gain.connect(ctx.destination);
    const o1=ctx.createOscillator(), o2=ctx.createOscillator();
    o1.type='sine'; o2.type='sine';
    o1.frequency.value=440; o2.frequency.value=480;
    o1.connect(gain); o2.connect(gain);
    o1.start(); o2.start();
    rbNodes={ctx:ctx,gain:gain,osc:[o1,o2]};
    const burst=function(){
      if(!rbNodes||rbNodes.ctx!==ctx) return;
      const t0=ctx.currentTime+0.02, g=gain.gain;
      g.cancelScheduledValues(t0);
      g.setValueAtTime(0.0001,t0);
      g.exponentialRampToValueAtTime(0.22,t0+0.12); /* gentle attack, no click */
      g.setValueAtTime(0.22,t0+1.88);
      g.exponentialRampToValueAtTime(0.0001,t0+2.0); /* gentle release */
      /* silent for the remaining 4s of each 6s cadence */
    };
    burst();
    rbTimer=setInterval(burst,6000);
    if(rbNoAnswerT) clearTimeout(rbNoAnswerT);
    rbNoAnswerT=setTimeout(noAnswerTimeout,NO_ANSWER_MS); /* nobody picks up -> hang up + popup */
  }catch(e){ ringbackStop(); }
}
function ringbackStop(){
  if(rbTimer){ clearInterval(rbTimer); rbTimer=0; }
  if(rbNoAnswerT){ clearTimeout(rbNoAnswerT); rbNoAnswerT=0; } /* answered / left / failed */
  const n=rbNodes; rbNodes=null;
  if(n){
    n.osc.forEach(function(o){ try{ o.stop(); }catch(e){} });
    try{ n.gain.disconnect(); }catch(e){}
    try{ const p=n.ctx.close(); if(p&&p.catch) p.catch(function(){}); }catch(e){}
  }
}
function ringbackActive(){ return !!(rbTimer||rbNodes); }

function pickKind(groupId){
  const g=findGroup(groupId);
  if(!g){ ui.toast(t('call.noGroup')); return; }
  if(!isMember(g)){ ui.toast(t('call.notMember')); return; }
  ui.openSheet(
    '<h2 style="margin:0 0 4px">'+ui.esc(t('call.pickCallT'))+'</h2>'
    +'<p class="sub" style="margin:0 0 12px">'+ui.esc(g.name||'')+'</p>'
    +'<button class="btn btn-primary btn-block" id="callPickVoice" style="margin-bottom:8px">📞 '+ui.esc(t('call.start'))+'</button>'
    +'<p class="sub" style="margin:0 0 12px">'+ui.esc(t('call.voiceCallS'))+'</p>'
    +'<button class="btn btn-line btn-block" id="callPickDemo20" style="margin-bottom:8px">🎭 '+ui.esc(t('call.demo20T'))+'</button>'
    +'<p class="sub" style="margin:0">'+ui.esc(t('call.demo20S'))+'</p>'
  );
  document.getElementById('callPickVoice').onclick=function(){ ui.closeSheet(); start(groupId,{outgoing:true}); };
  document.getElementById('callPickDemo20').onclick=function(){ ui.closeSheet(); start(groupId,{demo20:true}); };
}
function start(groupId,opts){
  opts=opts||{};
  /* Calls need internet for signaling */
  if(window.HUB&&HUB.offline&&HUB.offline.check()) return;
  const g=findGroup(groupId);
  if(!g){ ui.toast(t('call.noGroup')); return; }
  if(!isMember(g)){ ui.toast(t('call.notMember')); return; }
  if(sess&&sess.groupId!==groupId) leave();
  hideBanner();
  ensureRoot();
  if(sess&&sess.groupId===groupId){ root().hidden=false; renderAll(); return; }
  sess={groupId:groupId,group:g,callId:'c'+store.uid(),peerId:'p'+Math.random().toString(36).slice(2,7),
    meName:myName(),role:opts.demo20?'admin':(opts.role||defaultRole(g)),peers:{},pcs:{},analysers:{},
    levels:{},speaking:{},lastSeen:{},muted:false,mutedBy:null,starter:false,
    handRaised:false,speakerMuted:false,routeIdx:0,routeDevs:[],
    demo20:!!opts.demo20,demoInt:0,
    localStream:null,actx:null,startTs:0,timerInt:0,vadInt:0,pingInt:0,sweepInt:0,announceInt:0,adapter:null,micGen:0,
    usingWorker:!!store.state.callWorkerUrl,sigCount:{offer:0,answer:0},
    outgoing:!!(opts.outgoing&&!opts.demo20)};
  document.getElementById('callTitle').textContent=g.name||'';
  setConn('connecting');
  root().hidden=false;
  acquireMic();
  if(sess.outgoing) ringbackStart(); /* caller hears ring-ring until someone joins */
}
function acquireMic(){
  setConn('connecting');
  if(!sess) return;
  /* Generation token: if start() runs twice, the FIRST getUserMedia grant
     must not attach to the SECOND session — its tracks would be orphaned
     with the mic left hot. A stale grant's tracks are stopped on arrival. */
  const gen=++sess.micGen;
  if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){ onMicFail({name:'NotSupportedError'}); return; }
  navigator.mediaDevices.getUserMedia({audio:true}).then(function(s){ onMicOk(s,gen); },onMicFail);
}
function onMicOk(stream,gen){
  function stopStale(){ stream.getTracks().forEach(function(tr){ try{tr.stop();}catch(e){} }); }
  if(!sess||gen!==sess.micGen) { stopStale(); return; }
  sess.localStream=stream;
  sess.startTs=Date.now();
  if(sess.demo20){
    /* demo-20: real mic + real VAD for self, simulated crowd, no signaling */
    setConn('active');
    startDemo20();
    startTimer(); startVad(); refreshRoute();
    return;
  }
  const ad=sess.usingWorker?WorkerSignal(store.state.callWorkerUrl):LoopbackSignal();
  sess.adapter=ad;
  wireAdapter(ad);
  ad.connect({groupId:sess.groupId,callId:sess.callId,peerId:sess.peerId,name:sess.meName,role:sess.role})
    .then(function(){
      if(!sess) return;
      if(!sess.usingWorker){
        /* loopback: announce so other tabs of this browser show the banner */
        let cur=null; try{ cur=JSON.parse(localStorage.getItem(LS_ACTIVE)||'null'); }catch(e){}
        if(!cur||cur.groupId!==sess.groupId) persistActive();
      }
      setConn('active');
      startTimer(); startVad(); startHeartbeat();
      persistRoster(); refreshRoute();
    },function(){
      if(!sess) return;
      ui.toast(t('call.wsFail'));
      setConn('active'); /* stay in demo on this device */
      sess.usingWorker=false; sess.adapter=LoopbackSignal();
      wireAdapter(sess.adapter);
      sess.adapter.connect({groupId:sess.groupId,callId:sess.callId,peerId:sess.peerId,name:sess.meName,role:sess.role});
      startTimer(); startVad(); startHeartbeat(); persistRoster(); refreshRoute();
    });
}
function onMicFail(){
  if(!sess) return;
  ringbackStop(); /* call can't proceed — never leave the tone looping */
  setConn('micdenied');
}

/* ================= demo-20 simulation (NOT the real call path) ==========
   20 fake participants with lifelike activity: random speaking turns (the
   3D volt glow lights up), occasional self mute/unmute, hands that raise
   and drop. PraBin's own tile uses his REAL mic + real VAD. Everything
   stays inside this section; demo peers never reach signaling/audio. */
function startDemo20(){
  if(!sess) return;
  DEMO20_NAMES.forEach(function(nm,ix){
    const pid='d'+ix;
    sess.peers[pid]={peerId:pid,name:nm,role:'member',muted:false,mutedBy:null,
      handRaised:false,stream:null,demo20:true};
    sess.lastSeen[pid]=Date.now();
  });
  /* two hands up from the start so PraBin can try "let speak" right away */
  sess.peers.d3.handRaised=true; sess.peers.d11.handRaised=true;
  renderLabel(); renderTiles(); renderHint();
  if(sess.demoInt) clearInterval(sess.demoInt);
  sess.demoInt=setInterval(demo20Tick,1400);
}
function demo20Tick(){
  if(!sess||!sess.demo20) return;
  const ids=Object.keys(sess.peers);
  if(!ids.length) return;
  /* rotate speaking turns (self is driven by the real VAD — never touched) */
  Object.keys(sess.speaking).forEach(function(k){ if(k!=='self') sess.speaking[k]=false; });
  const n=1+Math.floor(Math.random()*2);
  for(let ix=0;ix<n;ix++){
    const p=sess.peers[ids[Math.floor(Math.random()*ids.length)]];
    if(p&&!p.muted&&!p.handRaised) sess.speaking[p.peerId]=true;
  }
  /* someone mutes/unmutes themselves now and then */
  if(Math.random()<0.16){
    const p=sess.peers[ids[Math.floor(Math.random()*ids.length)]];
    if(p){ p.muted=!p.muted; p.mutedBy=p.muted?p.name:null; }
  }
  /* hands raise … */
  if(Math.random()<0.14){
    const cands=ids.filter(function(pid){ return !sess.peers[pid].handRaised; });
    if(cands.length) sess.peers[cands[Math.floor(Math.random()*cands.length)]].handRaised=true;
  }
  /* … and drop again once a few are up (they spoke or gave up) */
  if(Math.random()<0.14){
    const raised=ids.filter(function(pid){ return sess.peers[pid].handRaised; });
    if(raised.length>2) sess.peers[raised[Math.floor(Math.random()*raised.length)]].handRaised=false;
  }
  renderTiles();
}
function stopDemo20(s){
  if(s&&s.demoInt){ clearInterval(s.demoInt); s.demoInt=0; }
}
/* Flip an already-running (empty) call into the demo-20 simulation:
   disconnect the signaling adapter, clear the signaling-only intervals
   (the presence sweep would drop demo peers after PEER_TIMEOUT), force
   admin, then run the same demo path as the pre-call picker. Idempotent. */
function switchToDemo20(){
  if(!sess||sess.demo20) return;
  ringbackStop(); /* simulated crowd is "already there" — no more ringback */
  try{ if(sess.adapter&&sess.adapter.leave) sess.adapter.leave(); }catch(e){}
  sess.adapter=null; sess.usingWorker=false;
  if(sess.pingInt){ clearInterval(sess.pingInt); sess.pingInt=0; }
  if(sess.sweepInt){ clearInterval(sess.sweepInt); sess.sweepInt=0; }
  if(sess.announceInt){ clearInterval(sess.announceInt); sess.announceInt=0; }
  sess.demo20=true; sess.role='admin';
  startDemo20();
}
function setConn(state){
  const sub=document.getElementById('callSub'), tiles=document.getElementById('callTiles'),
    ctrls=document.getElementById('callControls'), err=document.getElementById('callError'),
    hint=document.getElementById('callHint');
  renderLabel();
  if(state==='micdenied'){
    sub.textContent=t('call.micDeniedT');
    tiles.hidden=true; ctrls.hidden=true; hint.hidden=true;
    err.hidden=false;
    err.innerHTML='<div class="big">🎙️🚫</div><h2>'+ui.esc(t('call.micDeniedT'))+'</h2>'
      +'<p>'+ui.esc(t('call.micDeniedS'))+'</p>'
      +'<button class="btn btn-primary" id="callRetry">'+ui.esc(t('call.retry'))+'</button>';
    document.getElementById('callRetry').onclick=function(){ if(sess&&sess.outgoing) ringbackStart(); acquireMic(); };
    return;
  }
  err.hidden=true; tiles.hidden=false; ctrls.hidden=false;
  sub.textContent=state==='connecting'?t('call.connecting'):'';
  if(state==='active') renderAll();
}
function renderLabel(){
  const el=document.getElementById('callDemoLabel');
  if(!el) return;
  if(sess&&sess.demo20){ el.textContent=t('call.demo20Note'); return; }
  /* honest: "Live" only while the worker socket is actually connected —
     a saved URL alone never earns it */
  const live=!!(sess&&sess.adapter&&sess.adapter.isLive&&sess.adapter.isLive());
  el.textContent=live?t('call.liveNote'):t('call.demoNote');
}
function renderAll(){ renderTiles(); renderControls(); renderHint(); renderNotice(); }

/* ---------- tiles ---------- */
function roleLabel(r){ return r==='admin'?t('call.admin'):(r==='subadmin'?t('call.subadmin'):t('call.member')); }
function tileHTML(key,name,role,o){
  o=o||{};
  const muted=o.muted||!!o.mutedBy;
  return '<div class="calltile" data-tile="'+ui.esc(key)+'"'+(o.clickable?' role="button" tabindex="0" style="cursor:pointer"':'')+'>'
    +(muted?'<span class="micon">'+HUB.icons.icon('call-micmute','micon-ico')+'</span>':'')
    +(o.handRaised?'<span class="handbadge" title="'+ui.esc(t('call.handRaised'))+'">'+IC_HAND+'<span class="hb-t">'+ui.esc(t('call.handRaised'))+'</span></span>':'')
    +'<div class="avatar">'+ui.avatarFor(name)+'</div>'
    +'<div class="nm">'+ui.esc(name)+(o.self?' · '+ui.esc(t('call.you')):'')+'</div>'
    +'<span class="role">'+ui.esc(roleLabel(role))+'</span>'
    +'<div class="mutedby">'+(o.mutedBy?ui.esc(t('call.mutedBy',{name:o.mutedBy})):(muted?ui.esc(t('call.muted')):''))+'</div>'
    +'<div class="conn">'+ui.esc(o.conn||'')+'</div>'
    +'</div>';
}
function renderTiles(){
  const box=document.getElementById('callTiles');
  if(!box||!sess) return;
  box.classList.toggle('demo20',!!sess.demo20);
  const ids=Object.keys(sess.peers);
  let html=tileHTML('self',sess.meName,sess.role,{self:true,muted:sess.muted,mutedBy:sess.mutedBy,handRaised:sess.handRaised});
  ids.forEach(function(pid){
    const p=sess.peers[pid];
    const st=sess.pcs[pid]?sess.pcs[pid].connectionState:'';
    html+=tileHTML(pid,p.name,p.role,{muted:p.muted,mutedBy:p.mutedBy,handRaised:p.handRaised,
      conn:p.demo20?'':((st==='connected'||st==='completed')?'':t('call.connecting')),
      clickable:canMutePeer(p)});
  });
  box.innerHTML=html;
  /* re-apply live speaking classes (rebuild wipes them; VAD repaints fast) */
  Object.keys(sess.speaking).forEach(function(k){
    if(sess.speaking[k]){ const el=box.querySelector('[data-tile="'+k+'"]'); if(el) el.classList.add('speaking'); }
  });
  if(canAdmin()){
    box.querySelectorAll('.calltile[data-tile]').forEach(function(el){
      const k=el.getAttribute('data-tile');
      if(k!=='self'&&canMutePeer(sess.peers[k])){
        el.onclick=function(){ openAdminSheet(k); };
        el.onkeydown=function(e){ if(e.key==='Enter'){ e.preventDefault(); openAdminSheet(k); } };
      }
    });
  }
  renderAdminRow();
}
function renderControls(){
  const mic=document.getElementById('callMic'), spk=document.getElementById('callSpk');
  if(!mic||!sess) return;
  /* visual-only: .off = muted (sunken terracotta), .cblive = mic hot (volt glow).
     The 3D flip between the two icon faces is pure CSS on these classes. */
  const muted=sess.muted||!!sess.mutedBy;
  mic.classList.toggle('off',muted);
  mic.classList.toggle('cblive',!muted);
  const mcap=document.getElementById('callMicCap');
  if(mcap) mcap.textContent=t(muted?'call.unmute':'call.mute');
  mic.setAttribute('aria-label',t(muted?'call.micUnmute':'call.micMute'));
  mic.title=t(muted?'call.micUnmute':'call.micMute');
  /* Speaker (PraBin's order): one tap mutes ALL incoming call audio — a real
     mute of the remote <audio> elements, not just visual. .off = sunken
     terracotta dome + slash icon + "Speaker off" caption, unmistakable. */
  const sm=sess.speakerMuted;
  spk.classList.toggle('off',sm);
  spk.classList.remove('live','cblive');
  const scap=document.getElementById('callSpkCap');
  if(scap) scap.textContent=t(sm?'call.speakerOff':'call.speaker');
  spk.setAttribute('aria-label',t(sm?'call.speakerOff':'call.speaker'));
  spk.title=t(sm?'call.speakerOff':'call.speaker');
  /* Raise hand: volt glow dome while raised, caption flips to Lower hand. */
  const hand=document.getElementById('callHand');
  if(hand){
    const hr=sess.handRaised;
    hand.classList.toggle('cblive',hr);
    const hcap=document.getElementById('callHandCap');
    if(hcap) hcap.textContent=t(hr?'call.lowerHand':'call.raiseHand');
    hand.setAttribute('aria-label',t(hr?'call.lowerHand':'call.raiseHand'));
    hand.title=t(hr?'call.lowerHand':'call.raiseHand');
  }
  const lv=document.getElementById('callLeave');
  if(lv){
    const lcap=document.getElementById('callLeaveCap');
    if(lcap) lcap.textContent=t('call.leaveAria');
    lv.setAttribute('aria-label',t('call.leaveAria'));
    lv.title=t('call.leaveAria');
  }
}
function renderHint(){
  const h=document.getElementById('callHint');
  if(!h||!sess) return;
  const n=Object.keys(sess.peers).length;
  if(!n&&!sess.usingWorker&&!sess.demo20){
    /* PraBin's order: the demo-20 entry was buried in the pre-call picker,
       so he landed in an empty call and never found it. Unmissable button
       right here: one tap flips this call into the 20-person simulation. */
    h.hidden=false;
    h.innerHTML='<div>'+ui.esc(t('call.aloneHint'))+'</div>'
      +'<button class="callsim20" id="callSim20Btn">✨ '+ui.esc(t('call.sim20'))+'</button>'
      +'<button class="callsim20 ghost" id="callIncPrevBtn">🔔 '+ui.esc(t('inc.previewBtn'))+'</button>';
    document.getElementById('callSim20Btn').onclick=switchToDemo20;
    /* Preview the full-screen incoming-call UI (clearly labeled demo). */
    document.getElementById('callIncPrevBtn').onclick=function(){
      if(HUB.incoming) HUB.incoming.show({name:t('inc.demoCaller'),kind:'voice',
        groupName:sess&&sess.group?sess.group.name:'',demo:true,
        accept:function(){},reject:function(){}});
    };
  }
  /* PraBin's order 2026-09-22: the "As admin, tap a tile to manage it."
     banner is gone — no dead space. Tiles are tappable; the admin sheet
     explains the rest. The empty-state branch above is untouched. */
  else { h.hidden=true; h.innerHTML=''; }
}
function renderNotice(){
  const n=document.getElementById('callNotice');
  if(!n||!sess) return;
  if(sess.mutedBy){
    n.hidden=false;
    n.innerHTML=ui.esc(t('call.mutedNotice',{name:sess.mutedBy}))
      +' <button class="linklike" id="callReqUnmute" style="font-weight:700">'+ui.esc(t('call.reqUnmute'))+'</button>';
    document.getElementById('callReqUnmute').onclick=requestUnmute;
  } else n.hidden=true;
}

/* ---------- voice activity detection ----------
   Real VAD: RMS of the time-domain samples per analyser. When the level
   crosses the threshold the tile's 3D glow turns on and stays on for the
   hangover window, so it doesn't flicker on every syllable. */
function startVad(){
  const Ctx=window.AudioContext||window.webkitAudioContext;
  if(!Ctx||!sess) return;
  try{
    sess.actx=sess.actx||new Ctx();
    if(sess.actx.state==='suspended') sess.actx.resume().catch(function(){});
    addAnalyser('self',sess.localStream);
    sess.vadInt=setInterval(vadTick,VAD.interval);
  }catch(e){}
}
function addAnalyser(key,stream){
  if(!sess||!sess.actx||!stream) return;
  try{
    const src=sess.actx.createMediaStreamSource(stream);
    const an=sess.actx.createAnalyser();
    an.fftSize=VAD.fft; src.connect(an);
    sess.analysers[key]={an:an,src:src,buf:new Uint8Array(an.fftSize),hotUntil:0};
  }catch(e){}
}
function vadTick(){
  if(!sess) return;
  const now=Date.now(), box=document.getElementById('callTiles');
  ['self'].concat(Object.keys(sess.peers)).forEach(function(key){
    if(key!=='self'&&sess.demo20) return; /* demo-20: peers are sim-driven */
    const a=sess.analysers[key];
    let rms=0;
    if(a){
      try{
        a.an.getByteTimeDomainData(a.buf);
        let sum=0;
        for(let i=0;i<a.buf.length;i++){ const v=(a.buf[i]-128)/128; sum+=v*v; }
        rms=Math.sqrt(sum/a.buf.length);
      }catch(e){}
    }
    sess.levels[key]=rms;
    if(rms>VAD.threshold&&a) a.hotUntil=now+VAD.hangover;
    const hot=!!(a&&now<a.hotUntil);
    if(sess.speaking[key]!==hot){
      sess.speaking[key]=hot;
      if(box){ const el=box.querySelector('[data-tile="'+key+'"]'); if(el) el.classList.toggle('speaking',hot); }
    }
  });
}

/* ---------- timer / heartbeat / roster ---------- */
function startTimer(){
  const el=document.getElementById('callTimer');
  const tick=function(){ if(sess&&el) el.textContent=fmtDur(Date.now()-sess.startTs); };
  tick();
  sess.timerInt=setInterval(tick,1000);
}
function startHeartbeat(){
  if(sess.demo20) return; /* demo-20: no signaling, no presence sweep */
  sess.lastSeen[sess.peerId]=Date.now();
  sess.pingInt=setInterval(function(){ if(sess&&sess.adapter) sess.adapter.send({to:null,kind:'ping'}); },PING_EVERY);
  sess.sweepInt=setInterval(function(){
    if(!sess) return;
    const now=Date.now();
    Object.keys(sess.lastSeen).forEach(function(pid){
      if(pid!==sess.peerId&&now-sess.lastSeen[pid]>PEER_TIMEOUT) dropPeer(pid);
    });
  },5000);
  /* Announcement heartbeat: refresh the LS_ACTIVE `at` stamp while this tab
     owns a live call. Lets other tabs tell a live call from a stale record
     (owner tab closed/crashed without cleanup) — see checkActiveCallAtLoad. */
  sess.announceInt=setInterval(function(){ if(sess) persistActive(); },20000);
}
function persistActive(){
  if(!sess) return;
  try{ localStorage.setItem(LS_ACTIVE,JSON.stringify({groupId:sess.groupId,callId:sess.callId,by:sess.meName,at:Date.now()})); }catch(e){}
}
function persistRoster(){
  if(!sess||sess.demo20) return; /* demo-20: never persist fake people */
  const peers=Object.keys(sess.peers).map(function(pid){
    const p=sess.peers[pid]; return {name:p.name,role:p.role,muted:!!p.muted};
  });
  store.state.callRoster={groupId:sess.groupId,callId:sess.callId,at:Date.now(),
    peers:[{name:sess.meName+'',role:sess.role,self:true,muted:!!sess.muted}].concat(peers)};
  try{ store.save(); }catch(e){}
}

/* ================= signaling -> session ================= */
function wireAdapter(ad){
  ad.on('peer',function(m){
    if(!sess||m.peerId===sess.peerId) return;
    sess.lastSeen[m.peerId]=Date.now();
    if(!sess.peers[m.peerId]){
      sess.peers[m.peerId]={peerId:m.peerId,name:m.name||'?',role:m.role||'member',muted:!!m.muted,mutedBy:m.mutedBy||null,stream:null};
      ringbackStop(); /* someone picked up / joined — the caller stops hearing ring-ring */
      renderTiles(); renderHint(); persistRoster();
      maybeOffer(m.peerId);
    }
  });
  ad.on('left',function(m){ if(sess) dropPeer(m.peerId); });
  ad.on('ping',function(m){ if(sess) sess.lastSeen[m.peerId]=Date.now(); });
  ad.on('sdp',function(m){ if(sess) onSdp(m.from,m.kind,m.sdp); });
  ad.on('ice',function(m){
    if(!sess) return;
    const pc=sess.pcs[m.from];
    if(pc&&m.candidate){ try{ pc.addIceCandidate(new RTCIceCandidate(m.candidate)); }catch(e){} }
  });
  ad.on('mute',function(m){
    if(!sess) return;
    if(m.target===sess.peerId) forceMuteSelf(m.byName);
    else { const p=sess.peers[m.target]; if(p){ p.muted=true; p.mutedBy=m.byName; } }
    renderTiles(); renderControls(); persistRoster();
  });
  ad.on('unmute',function(m){
    if(!sess) return;
    if(m.target===sess.peerId){
      sess.muted=false; sess.mutedBy=null;
      if(sess.localStream) sess.localStream.getAudioTracks().forEach(function(tr){ tr.enabled=true; });
      ui.toast(t('call.canUnmute',{name:sess.meName}));
    }else { const p=sess.peers[m.target]; if(p){ p.muted=false; p.mutedBy=null; } }
    renderTiles(); renderControls(); renderNotice(); persistRoster();
  });
  ad.on('role',function(m){
    if(!sess) return;
    applyRole(m.name,m.role);
    if(isSelfName(m.name)) ui.toast(t(m.role==='subadmin'?'call.promoted':'call.demoted',{name:t('call.you')}));
  });
  ad.on('unmuteReq',function(m){
    if(sess&&canAdmin()) ui.toast(t('call.unmuteReqT',{name:m.fromName}));
  });
  ad.on('hand',function(m){
    /* a peer's hand state changed: badge on their tile for everyone */
    if(!sess||!m||m.from===sess.peerId) return;
    const p=sess.peers[m.from]; if(!p) return;
    p.handRaised=!!m.raised;
    if(m.raised) ui.toast(t('call.handRaisedToast',{name:p.name}));
    renderTiles();
  });
  ad.on('handLower',function(){
    /* an admin tapped "Let speak": drop my raised hand and broadcast it */
    if(!sess||!sess.handRaised) return;
    sess.handRaised=false;
    if(sess.adapter&&sess.adapter.raiseHand) sess.adapter.raiseHand(false);
    renderControls(); renderTiles();
  });
  ad.on('welcomeInfo',function(m){ if(sess&&m.isFirst) sess.starter=true; });
  ad.on('wsError',function(m){ if(sess&&sess.usingWorker) ui.toast(t('call.wsFail')); });
  ad.on('closed',function(){
    /* worker socket dropped mid-call: fall back to the demo path honestly */
    if(!sess||sess.adapter!==ad) return;
    if(sess.usingWorker){
      sess.usingWorker=false;
      const lb=LoopbackSignal(); sess.adapter=lb; wireAdapter(lb);
      lb.connect({groupId:sess.groupId,callId:sess.callId,peerId:sess.peerId,name:sess.meName,role:sess.role});
      ui.toast(t('call.wsFail')); renderLabel();
    } else renderLabel();
  });
}
function dropPeer(pid){
  if(!sess||!sess.peers[pid]) return;
  try{ if(sess.pcs[pid]) sess.pcs[pid].close(); }catch(e){}
  delete sess.pcs[pid]; delete sess.peers[pid]; delete sess.analysers[pid];
  delete sess.levels[pid]; delete sess.speaking[pid]; delete sess.lastSeen[pid];
  const au=document.getElementById('callAu_'+pid); if(au) au.remove();
  renderTiles(); renderHint(); persistRoster();
}

/* ================= WebRTC mesh ================= */
function ensurePC(pid){
  let pc=sess.pcs[pid];
  if(pc) return pc;
  /* Privacy: STUN (Google) is only needed for real worker-mode calls that
     cross NATs. Loopback/demo sessions stay fully local — no STUN binding,
     no IP disclosure to any third party. */
  const needStun=!!(sess&&sess.adapter&&sess.adapter.mode==='worker');
  pc=new RTCPeerConnection(needStun?STUN:undefined);
  sess.pcs[pid]=pc;
  if(sess.localStream) sess.localStream.getTracks().forEach(function(tr){ try{ pc.addTrack(tr,sess.localStream); }catch(e){} });
  pc.onicecandidate=function(e){ if(e.candidate&&sess&&sess.adapter) sess.adapter.send({to:pid,kind:'ice',candidate:e.candidate}); };
  pc.ontrack=function(e){ attachRemote(pid,e.streams[0]); };
  pc.onconnectionstatechange=function(){ if(sess) renderTiles(); };
  return pc;
}
function maybeOffer(pid){
  /* deterministic offerer: smaller peerId offers, so two joiners never glare */
  if(!sess||sess.peerId>=pid) return;
  try{
    const pc=ensurePC(pid);
    pc.createOffer().then(function(off){ return pc.setLocalDescription(off); }).then(function(){
      sess.sigCount.offer++;
      sess.adapter.send({to:pid,kind:'offer',sdp:pc.localDescription});
    }).catch(function(){});
  }catch(e){}
}
function onSdp(from,kind,sdp){
  if(!sess||!sdp) return;
  try{
    const pc=ensurePC(from);
    if(kind==='offer'){
      pc.setRemoteDescription(new RTCSessionDescription(sdp)).then(function(){ return pc.createAnswer(); })
        .then(function(ans){ return pc.setLocalDescription(ans); }).then(function(){
          sess.sigCount.answer++;
          sess.adapter.send({to:from,kind:'answer',sdp:pc.localDescription});
        }).catch(function(){});
    }else{
      pc.setRemoteDescription(new RTCSessionDescription(sdp)).catch(function(){});
    }
  }catch(e){}
}
function attachRemote(pid,stream){
  if(!sess||!sess.peers[pid]||!stream) return;
  sess.peers[pid].stream=stream;
  let au=document.getElementById('callAu_'+pid);
  if(!au){
    au=document.createElement('audio');
    au.id='callAu_'+pid; au.autoplay=true; au.setAttribute('playsinline','');
    document.getElementById('callAudio').appendChild(au);
  }
  try{ au.srcObject=stream; }catch(e){}
  /* new peer inherits the current output state (speaker mute + route) */
  try{ au.muted=!!sess.speakerMuted; }catch(e){}
  const rd=sess.routeDevs[sess.routeIdx];
  if(rd&&typeof au.setSinkId==='function'){ try{ au.setSinkId(rd.deviceId||'').catch(function(){}); }catch(e){} }
  addAnalyser(pid,stream);
  renderTiles();
}

/* ================= mic / speaker ================= */
function toggleMic(){
  if(!sess||!sess.localStream) return;
  if(sess.mutedBy){ requestUnmute(); return; } /* admin-muted: ask, don't fight */
  sess.muted=!sess.muted;
  sess.localStream.getAudioTracks().forEach(function(tr){ tr.enabled=!sess.muted; });
  renderControls(); renderTiles(); persistRoster();
}
function forceMuteSelf(byName){
  if(!sess) return;
  sess.muted=true; sess.mutedBy=byName;
  if(sess.localStream) sess.localStream.getAudioTracks().forEach(function(tr){ tr.enabled=false; });
  renderControls(); renderTiles(); renderNotice(); persistRoster(); muteCue();
}
function requestUnmute(){
  if(!sess||!sess.adapter) return;
  const admins=Object.keys(sess.peers).filter(function(pid){
    const r=sess.peers[pid].role; return r==='admin'||r==='subadmin';
  });
  sess.adapter.requestUnmute(admins,sess.meName);
  ui.toast(t('call.unmuteReqSent'));
}
function remoteAudioEls(){ return Array.prototype.slice.call(document.querySelectorAll('#callAudio audio')); }
/* Speaker (PraBin's order): ONE tap mutes all incoming call audio, tap again
   restores it. Real effect — the remote <audio> elements are the only path
   incoming voice takes, so el.muted IS the speaker being off. VAD keeps
   reading the (unmuted) tracks, so speaking glow still works while muted. */
function toggleSpeaker(){
  if(!sess) return;
  sess.speakerMuted=!sess.speakerMuted;
  applySpeakerMute();
  renderControls();
}
function applySpeakerMute(){
  if(!sess) return;
  const sm=sess.speakerMuted;
  remoteAudioEls().forEach(function(a){ try{ a.muted=sm; }catch(e){} });
}

/* ---- loudspeaker <-> earpiece route switch (PraBin's refinement) ----
   A SEPARATE compact pill in the call header — visually distinct from the
   speaker-mute dome so the two can't be confused. Honest by construction:
   the pill is enabled only where the platform really lets the web route
   audio (setSinkId exists AND 2+ audio outputs). Everywhere else (iOS
   Safari etc.) it renders DISABLED with an honest note — never a switch
   that does nothing. */
function refreshRoute(){
  const btn=document.getElementById('callRoute');
  if(!btn||!sess) return;
  const canSink=!!(window.HTMLMediaElement&&HTMLMediaElement.prototype.setSinkId);
  if(!canSink||!navigator.mediaDevices||!navigator.mediaDevices.enumerateDevices){ setRouteUI('unsupported'); return; }
  navigator.mediaDevices.enumerateDevices().then(function(devs){
    if(!sess) return;
    sess.routeDevs=devs.filter(function(d){ return d.kind==='audiooutput'; });
    if(sess.routeIdx>=sess.routeDevs.length) sess.routeIdx=0;
    setRouteUI(sess.routeDevs.length>=2?'ready':'unsupported');
  }).catch(function(){ if(sess) setRouteUI('unsupported'); });
}
function setRouteUI(state){
  const btn=document.getElementById('callRoute'), noteEl=document.getElementById('callRouteNote');
  if(!btn||!sess) return;
  const face=btn.querySelector('.cb-face'), cap=document.getElementById('callRouteCap');
  if(noteEl) noteEl.textContent=t('call.routeNote');
  if(state==='ready'){
    btn.hidden=false; btn.disabled=false;
    if(noteEl) noteEl.hidden=true;
    const d=sess.routeDevs[sess.routeIdx]||{};
    const lab=String(d.label||'').toLowerCase();
    const isEar=/earpiece|receiver|earphone/.test(lab)&&!/speaker/.test(lab);
    if(face) face.innerHTML=isEar?IC_EAR:IC_SPKON;
    if(cap) cap.textContent=t(isEar?'call.earpiece':'call.loudspeaker');
    btn.title=t('call.routeSwitch'); btn.setAttribute('aria-label',t('call.routeSwitch'));
  }else{
    /* honest: no fake switch — disabled pill + the plain-language note */
    btn.hidden=false; btn.disabled=true;
    if(noteEl) noteEl.hidden=false;
    if(face) face.innerHTML=IC_SPKON;
    if(cap) cap.textContent=t('call.loudspeaker');
    btn.title=t('call.routeNote'); btn.setAttribute('aria-label',t('call.routeNote'));
  }
}
function cycleRoute(){
  if(!sess||!sess.routeDevs||sess.routeDevs.length<2) return;
  sess.routeIdx=(sess.routeIdx+1)%sess.routeDevs.length;
  const id=sess.routeDevs[sess.routeIdx].deviceId||'';
  remoteAudioEls().forEach(function(a){ try{ a.setSinkId(id).catch(function(){}); }catch(e){} });
  setRouteUI('ready');
  const d=sess.routeDevs[sess.routeIdx];
  if(d&&d.label) ui.toast(d.label);
}
/* re-check routing when the OS plugs/unplugs audio devices mid-call */
if(navigator.mediaDevices&&navigator.mediaDevices.addEventListener){
  try{ navigator.mediaDevices.addEventListener('devicechange',function(){ if(sess) refreshRoute(); }); }catch(e){}
}

/* admin sheet + worker-URL sheet live INSIDE the call overlay (ui.openSheet
   is z-70, under the call UI at z-400) */
function openCallSheet(html){
  const sh=document.getElementById('callSheet'), box=document.getElementById('callSheetBox');
  box.innerHTML=html; sh.hidden=false;
}
function closeCallSheet(){ const sh=document.getElementById('callSheet'); if(sh) sh.hidden=true; }
/* ================= admin ================= */
function openAdminSheet(pid){
  if(!sess||!sess.peers[pid]||!canAdmin()) return;
  const p=sess.peers[pid], isAdm=sess.role==='admin';
  const subAdm=p.role==='subadmin';
  let html='<h2 style="margin:0 0 2px">'+ui.esc(p.name)+'</h2>'
    +'<p class="sub" style="margin:0 0 12px">'+ui.esc(roleLabel(p.role))
    +(p.mutedBy?' · '+ui.esc(t('call.mutedBy',{name:p.mutedBy})):'')
    +(p.handRaised?' · '+ui.esc(t('call.handRaised')):'')+'</p>'
    +'<div class="row" style="gap:8px;flex-wrap:wrap">';
  if(p.handRaised&&canAdmin()){
    html+='<button class="btn btn-primary" id="callAdmLetSpeak">'+ui.esc(t('call.letSpeak'))+'</button>';
  }
  if(canMutePeer(p)){
    html+=p.muted
      ? '<button class="btn btn-primary" id="callAdmUnmute">'+ui.esc(t('call.unmute'))+'</button>'
      : '<button class="btn btn-primary" id="callAdmMute">'+ui.esc(t('call.mute'))+'</button>';
  }
  if(isAdm&&p.role!=='admin'){
    html+=subAdm
      ? '<button class="btn btn-line" id="callAdmDemote">'+ui.esc(t('call.removeSubadmin'))+'</button>'
      : '<button class="btn btn-line" id="callAdmPromote">'+ui.esc(t('call.makeSubadmin'))+'</button>';
  }
  html+='</div>';
  openCallSheet(html);
  const mb=document.getElementById('callAdmMute'), ub=document.getElementById('callAdmUnmute'),
    pr=document.getElementById('callAdmPromote'), dm=document.getElementById('callAdmDemote'),
    ls=document.getElementById('callAdmLetSpeak');
  if(mb) mb.onclick=function(){ mutePeer(pid); closeCallSheet(); };
  if(ub) ub.onclick=function(){ unmutePeer(pid); closeCallSheet(); };
  if(ls) ls.onclick=function(){ letSpeak(pid); closeCallSheet(); };
  if(pr) pr.onclick=function(){ setSubadmin(p.name,true); closeCallSheet(); };
  if(dm) dm.onclick=function(){ setSubadmin(p.name,false); closeCallSheet(); };
}
/* ---- admin row + mute-all (PraBin's order 2026-09-22) ----
   "Mute all" sits thumb-reachable right above the tiles, visible only to
   admins/subadmins while peers are on the call. One tap mutes every
   participant except self — no unmute-all (he didn't ask). It respects the
   same rules as per-tile mute: never an admin, and a subadmin can never
   mute another subadmin. */
function renderAdminRow(){
  const r=document.getElementById('callAdminRow');
  if(!r||!sess) return;
  r.hidden=!(canAdmin()&&Object.keys(sess.peers).length>0);
}
/* Soft original mute-feedback cue (audio/mutecue.* via js/sound.js): a gentle
   descending two-note chime, never the generic notification sound. Never throws. */
function muteCue(){ try{ if(HUB.sound&&HUB.sound.playMuteCue) HUB.sound.playMuteCue(); }catch(e){} }
function muteAll(){
  if(!sess||!canAdmin()) return;
  let n=0;
  Object.keys(sess.peers).forEach(function(pid){
    const p=sess.peers[pid];
    if(p&&!p.muted&&canMutePeer(p)){
      p.muted=true; p.mutedBy=sess.meName; n++;
      if(sess.adapter) sess.adapter.mute(pid,sess.meName);
    }
  });
  if(n>0){ ui.toast(t('call.mutedAll',{count:n}), true); muteCue(); }
  renderTiles(); persistRoster();
}
function mutePeer(pid){
  if(!sess||!canMutePeer(sess.peers[pid])) return;
  const p=sess.peers[pid];
  p.muted=true; p.mutedBy=sess.meName;
  if(sess.adapter) sess.adapter.mute(pid,sess.meName);
  ui.toast(t('call.mutedToast',{name:p.name}), true); muteCue();
  renderTiles(); persistRoster();
}
function unmutePeer(pid){
  if(!sess) return;
  const p=sess.peers[pid]; if(!p) return;
  p.muted=false; p.mutedBy=null;
  if(sess.adapter) sess.adapter.unmute(pid,sess.meName);
  ui.toast(t('call.unmutedToast',{name:p.name}), true); muteCue();
  renderTiles(); persistRoster();
}
/* ---- raise hand / request to speak (PraBin's order) ----
   tap the hand dome -> hand raised (volt glow) -> everyone sees a volt hand
   badge on that tile. Tap again (or an admin's "Let speak") -> lowered. */
function toggleHand(){
  if(!sess) return;
  sess.handRaised=!sess.handRaised;
  if(sess.adapter&&sess.adapter.raiseHand) sess.adapter.raiseHand(sess.handRaised);
  renderControls(); renderTiles();
}
function letSpeak(pid){
  /* admin/subadmin: unmute the raiser if muted AND lower their hand */
  if(!sess||!sess.peers[pid]||!canAdmin()) return;
  if(sess.peers[pid].muted) unmutePeer(pid);
  if(sess.adapter&&sess.adapter.lowerHand) sess.adapter.lowerHand(pid,sess.meName);
  else { sess.peers[pid].handRaised=false; renderTiles(); }
}
function setSubadmin(name,make){
  if(!sess||sess.role!=='admin') return;
  const g=sess.group;
  g.callAdmins=g.callAdmins||[];
  const ix=g.callAdmins.map(lower).indexOf(lower(name));
  if(make&&ix<0) g.callAdmins.push(name);
  if(!make&&ix>=0) g.callAdmins.splice(ix,1);
  try{ store.save(); }catch(e){}
  if(sess.adapter&&sess.adapter.setRole) sess.adapter.setRole(name,make?'subadmin':'member',sess.meName);
  applyRole(name,make?'subadmin':'member');
  ui.toast(t(make?'call.promoted':'call.demoted',{name:name}));
}
function applyRole(name,role){
  if(!sess) return;
  if(isSelfName(name)) sess.role=role;
  Object.keys(sess.peers).forEach(function(pid){
    if(lower(sess.peers[pid].name)===lower(name)) sess.peers[pid].role=role;
  });
  renderTiles(); persistRoster();
}

/* ================= worker URL sheet ================= */
function openWorkerSheet(){
  const cur=store.state.callWorkerUrl||'';
  openCallSheet('<h2 style="margin:0 0 4px">'+ui.esc(t('call.workerT'))+'</h2>'
    +'<p class="sub" style="margin:0 0 10px">'+ui.esc(t('call.workerS'))+'</p>'
    +'<div class="field"><input class="input" id="callWorkerIn" placeholder="wss://…" value="'+ui.esc(cur)+'" autocomplete="off"></div>'
    +'<div class="row" style="gap:8px;margin-top:12px;flex-wrap:wrap">'
    +'<button class="btn btn-primary" id="callWorkerSave">'+ui.esc(t('call.workerSave'))+'</button>'
    +'<button class="btn btn-line" id="callWorkerDemo">'+ui.esc(t('call.workerDemo'))+'</button></div>');
  document.getElementById('callWorkerSave').onclick=function(){
    const v=document.getElementById('callWorkerIn').value.trim();
    if(v) store.state.callWorkerUrl=v; else delete store.state.callWorkerUrl;
    try{ store.save(); }catch(e){}
    closeCallSheet(); ui.toast(t('call.workerSaved')); renderLabel();
  };
  document.getElementById('callWorkerDemo').onclick=function(){
    delete store.state.callWorkerUrl;
    try{ store.save(); }catch(e){}
    closeCallSheet(); renderLabel();
  };
}

/* ================= leave ================= */
function leave(){
  if(!sess) return;
  const s=sess; sess=null;
  ringbackStop(); /* never leak the looping tone — every teardown lands here */
  stopDemo20(s);
  try{ if(HUB.sound) HUB.sound.stopRingtone(); }catch(e){} /* belt & braces */
  try{ if(s.adapter) s.adapter.leave(); }catch(e){}
  Object.keys(s.pcs).forEach(function(pid){ try{ s.pcs[pid].close(); }catch(e){} });
  if(s.localStream) s.localStream.getTracks().forEach(function(tr){ try{ tr.stop(); }catch(e){} });
  [s.timerInt,s.vadInt,s.pingInt,s.sweepInt,s.announceInt].forEach(function(i){ if(i) clearInterval(i); });
  try{ if(s.actx&&s.actx.state!=='closed'){ s.actx.close().catch(function(){}); } }catch(e){}
  s.actx=null;
  try{ if(s.actx) s.actx.close(); }catch(e){}
  /* clear the loopback announcement, but only if it's still my call */
  try{ const cur=JSON.parse(localStorage.getItem(LS_ACTIVE)||'null'); if(cur&&cur.callId===s.callId) localStorage.removeItem(LS_ACTIVE); }catch(e){}
  try{ store.state.callRoster=null; store.save(); }catch(e){}
  const r=root(); if(r) r.hidden=true;
  const au=document.getElementById('callAudio'); if(au) au.innerHTML='';
  closeCallSheet(); ui.closeSheet(); hideBanner();
}

/* ================= incoming-call banner ================= */
function showBanner(info){
  if(sess&&sess.groupId===info.groupId) return;
  /* idempotency: the owner's 20s announcement heartbeat fires storage events
     in this tab — don't re-pop the incoming UI for the call already shown. */
  if(info.callId&&shownIncomingId===info.callId) return;
  const g=findGroup(info.groupId);
  if(!g||!isMember(g)) return;
  shownIncomingId=info.callId||null;
  /* no-answer timeout on the callee side too: an unanswered incoming call
     goes quiet by itself instead of ringing forever */
  if(incNoAnswerT) clearTimeout(incNoAnswerT);
  incNoAnswerT=setTimeout(function(){ incNoAnswerT=0; hideBanner(); },NO_ANSWER_MS);
  /* Full-screen incoming-call UI owns the real incoming event; the old top
     banner stays as the fallback if HUB.incoming isn't loaded. */
  if(HUB.incoming&&HUB.incoming.show){
    HUB.incoming.show({name:info.by||g.name||'?',kind:'voice',groupName:g.name||'',
      demo:!info.worker,demoLabel:!info.worker?t('call.incomingDemo'):null,
      accept:function(){ hideBanner(); start(info.groupId); },
      reject:function(){ bannerSuppressed[info.callId]=true; hideBanner(); }});
    return;
  }
  ensureRoot();
  const b=bannerEl();
  b.innerHTML='<div class="ring">📞</div>'
    +'<div class="grow"><h3>'+ui.esc(t('call.incomingT')+' · '+(g.name||''))+'</h3>'
    +'<div class="sub">'+ui.esc(t('call.startedBy',{name:info.by||'?'})+' · '+(info.worker?t('call.incomingLive'):t('call.incomingDemo')))+'</div></div>'
    +'<div class="row"><button class="btn btn-primary" id="callBannerJoin">'+ui.esc(t('call.join'))+'</button>'
    +'<button class="btn btn-line" id="callBannerNo">'+ui.esc(t('call.decline'))+'</button></div>';
  b.hidden=false;
  try{ if(HUB.sound) HUB.sound.playRingtone(); }catch(e){} /* original Onaro ringtone, loops */
  document.getElementById('callBannerJoin').onclick=function(){ hideBanner(); start(info.groupId); };
  document.getElementById('callBannerNo').onclick=function(){ bannerSuppressed[info.callId]=true; hideBanner(); };
}
function hideBanner(){ shownIncomingId=null; if(incNoAnswerT){ clearTimeout(incNoAnswerT); incNoAnswerT=0; } const b=bannerEl(); if(b) b.hidden=true; try{ if(HUB.incoming) HUB.incoming.hide(); }catch(e){} try{ if(HUB.sound) HUB.sound.stopRingtone(); }catch(e){} }
/* loopback incoming: another tab of this browser wrote onaro_call_active */
window.addEventListener('storage',function(e){
  if(e.key!==LS_ACTIVE) return;
  if(e.newValue){
    let info=null; try{ info=JSON.parse(e.newValue); }catch(err){}
    if(info&&!sess&&!bannerSuppressed[info.callId]) showBanner(info);
  }else hideBanner();
});
/* worker incoming: lightweight watch socket per group (loopback needs none).
   Failed connects are remembered with a timestamp so a dead worker doesn't
   spawn a fresh 12s-timeout attempt on every group open; every watcher closes
   on page unload so sockets can't accumulate. */
const watchFailAt={};
function watch(groupId){
  if(!store.state.callWorkerUrl||watchers[groupId]) return;
  if(watchFailAt[groupId]&&Date.now()-watchFailAt[groupId]<5*60*1000) return;
  const ad=WorkerSignal(store.state.callWorkerUrl);
  ad.on('call-started',function(m){
    if(!sess&&!bannerSuppressed[m.callId]) showBanner({groupId:groupId,callId:m.callId,by:m.by,worker:true});
  });
  ad.on('call-ended',function(){ hideBanner(); });
  ad.connect({groupId:groupId,watch:true,peerId:'w'+Math.random().toString(36).slice(2,7),name:myName(),role:'member'})
    .then(function(){ watchers[groupId]=ad; },function(){ watchFailAt[groupId]=Date.now(); });
}
window.addEventListener('beforeunload',function(){
  ringbackStop();
  if(sess){ try{ sess.adapter.leave(); }catch(e){} }
  for(const gid in watchers){ try{ watchers[gid].leave(); }catch(e){} delete watchers[gid]; }
});

/* Escape: app.js defers its global handler while .callroot is visible, so
   this owns Escape: close the admin sheet first, otherwise leave the call —
   never touching the layers underneath. */
document.addEventListener('keydown',function(e){
  if(e.key!=='Escape') return;
  const r=root();
  if(r&&!r.hidden){
    const cs=document.getElementById('callSheet');
    if(cs&&!cs.hidden){ closeCallSheet(); return; }
    leave(); return;
  }
  const b=bannerEl();
  if(b&&!b.hidden) hideBanner();
});
/* backdrop tap closes the in-call sheet */
document.addEventListener('click',function(e){
  const cs=document.getElementById('callSheet');
  if(cs&&!cs.hidden&&e.target===cs) closeCallSheet();
});

/* a tab opened while another tab already holds a loopback call: the storage
   event fired before this tab existed, so check once at load.
   Deferred to window 'load' (not script-eval time) so HUB.incoming exists and
   the fullscreen UI is used instead of the legacy banner fallback. */
/* a tab opened while another tab already holds a loopback call: the storage
   event fired before this tab existed, so check once at load.
   Deferred to window 'load' (not script-eval time) so HUB.incoming exists and
   the fullscreen UI is used instead of the legacy banner fallback.
   STALE-RECORD GUARD (2026-09-30): the owner tab refreshes `at` every 20s
   while its call is alive (see startHeartbeat). A record older than 120s
   means the owner is gone (tab closed/crashed without cleanup) — delete it
   silently instead of ringing a phantom incoming call, even before login. */
function checkActiveCallAtLoad(){
  let info=null;
  try{ info=JSON.parse(localStorage.getItem(LS_ACTIVE)||'null'); }catch(e){}
  if(!info||!info.callId||bannerSuppressed[info.callId]) return;
  if(info.at&&Date.now()-info.at>120000){
    try{ localStorage.removeItem(LS_ACTIVE); }catch(e){}
    return;
  }
  try{ showBanner(info); }catch(e){}
}
if(document.readyState==='complete') checkActiveCallAtLoad();
else window.addEventListener('load',checkActiveCallAtLoad);

/* ================= exports ================= */
HUB.call={
  start:start, pickKind:pickKind, leave:leave, watch:watch,
  LoopbackSignal:LoopbackSignal, WorkerSignal:WorkerSignal,
  useWorker:function(url){ store.state.callWorkerUrl=url; try{store.save();}catch(e){} if(sess) sess.usingWorker=true; renderLabel(); },
  useLoopback:function(){ delete store.state.callWorkerUrl; try{store.save();}catch(e){} if(sess) sess.usingWorker=false; renderLabel(); },
  isActive:function(){ return !!sess; },
  /* QA-only: is the outgoing ringback tone currently playing? */
  _ringback:function(){ return ringbackActive(); },
  /* QA-only: shorten/lengthen the no-answer timeout (ms) for tests */
  _noAnswerMs:function(ms){ if(ms>0) NO_ANSWER_MS=ms; },
  /* QA-only introspection (not user-facing): session snapshot + a way to
     force the speaking glow to verify the 3D CSS in isolation. */
  _debug:function(){
    if(!sess) return null;
    const pcs={};
    Object.keys(sess.pcs).forEach(function(pid){ try{ pcs[pid]=sess.pcs[pid].connectionState+'/'+sess.pcs[pid].iceConnectionState; }catch(e){ pcs[pid]='?'; } });
    return {groupId:sess.groupId,callId:sess.callId,peerId:sess.peerId,meName:sess.meName,role:sess.role,
      usingWorker:sess.usingWorker,muted:sess.muted,mutedBy:sess.mutedBy,
      speakerMuted:sess.speakerMuted,handRaised:sess.handRaised,
      routeDevs:(sess.routeDevs||[]).length,routeIdx:sess.routeIdx,
      demo20:!!sess.demo20,
      peers:Object.keys(sess.peers),peerNames:Object.keys(sess.peers).map(function(pid){ return sess.peers[pid].name; }),
      levels:sess.levels,speaking:sess.speaking,pcs:pcs,sig:sess.sigCount,
      hasLocalStream:!!sess.localStream,hasAnalyser:!!sess.analysers.self};
  },
  _debugSpeak:function(key,on){
    const box=document.getElementById('callTiles');
    if(!box) return false;
    const el=box.querySelector('[data-tile="'+key+'"]');
    if(!el) return false;
    el.classList.toggle('speaking',!!on);
    return true;
  },
  /* QA-only: detach/reattach the mic tap so silence is deterministic even
     when the platform fake mic beeps. Does not touch the RTCPeerConnection. */
  _debugMicTap:function(on){
    if(!sess||!sess.analysers.self||!sess.analysers.self.src) return false;
    const a=sess.analysers.self;
    try{ if(on) a.src.connect(a.an); else a.src.disconnect(a.an); }catch(e){}
    return true;
  },
  /* QA-only: pause/resume the demo-20 simulation tick so mute assertions are
     deterministic (the tick randomly toggles peer mute state). Not user-facing. */
  _demoPause:function(on){
    if(!sess||!sess.demo20) return false;
    if(on){ stopDemo20(sess); }
    else if(!sess.demoInt){ sess.demoInt=setInterval(demo20Tick,1400); }
    return true;
  },
  /* QA-only: inject a real 440Hz tone into the SELF analyser input so the
     production VAD (analyser -> RMS -> 0.02 threshold -> 500ms hangover ->
     .speaking class) can be asserted deterministically. The tone never
     reaches the peer connection (analyser is a sink-only tap). */
  _debugTone:function(on){
    if(!sess||!sess.actx||!sess.analysers.self) return false;
    if(on&&!sess._tone){
      try{
        const o=sess.actx.createOscillator(), gn=sess.actx.createGain();
        gn.gain.value=0.5; o.frequency.value=440;
        o.connect(gn); gn.connect(sess.analysers.self.an); o.start();
        sess._tone={o:o,g:gn};
      }catch(e){ return false; }
    }else if(!on&&sess._tone){
      try{ sess._tone.o.stop(); }catch(e){}
      try{ sess._tone.o.disconnect(); sess._tone.g.disconnect(); }catch(e){}
      sess._tone=null;
    }
    return true;
  }
};
Object.defineProperty(HUB.call,'signal',{get:function(){ return sess?sess.adapter:null; }});
})();
