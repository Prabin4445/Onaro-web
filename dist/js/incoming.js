/* ==================== incoming.js — full-screen incoming-call UI ==========
   WhatsApp/iPhone-style answer screen. It lives INSIDE the app: iOS only
   grants lock-screen call takeover to native apps, so this is the web's
   honest equivalent — a full-bleed screen with big Answer / Decline targets,
   the user's selected ringtone on loop, a 45s missed-call timeout, and a
   notification-center entry for the missed call.

   Public API: HUB.incoming.show({name, avatar, kind, groupName, demo,
   accept(), reject()}). call.js's real incoming-call event delegates here.
   Closed-app alerts are Web Push groundwork in js/push.js + sw.js.
   Classic IIFE, no modules. */
(function(){
'use strict';
/* module translation helper — never name a local/param `t` (shadowing bug) */
const t=function(k,v){ return HUB.i18n.t(k,v); };
const TIMEOUT_MS=45000;
const LS_MISSED_MAX=10;
const PHONE_SVG='<svg viewBox="0 0 24 24" fill="none" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.13.96.36 1.9.7 2.8a2 2 0 0 1-.45 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.45c.9.34 1.84.57 2.8.7A2 2 0 0 1 22 16.9z"/></svg>';

let cur=null; /* {accept,reject,timerId,name,done} */

function rootEl(){ return document.getElementById('incallRoot'); }
function esc(s){ return HUB.ui?HUB.ui.esc(String(s==null?'':s)):String(s==null?'':s); }

function ensureRoot(){
  if(rootEl()) return;
  const d=document.createElement('div');
  d.className='incallroot'; d.id='incallRoot'; d.hidden=true;
  d.setAttribute('role','dialog'); d.setAttribute('aria-modal','true');
  d.innerHTML='<div class="incall">'
    +'<span class="inc-tag" id="incTag" hidden></span>'
    +'<div class="inc-ava" id="incAva" aria-hidden="true"></div>'
    +'<h2 class="inc-name" id="incName"></h2>'
    +'<p class="inc-sub" id="incSub" hidden></p>'
    +'<div class="inc-kind" id="incKind"></div>'
    +'<div class="inc-actions">'
    +'<button class="inc-btn inc-decline" id="incDecline"><span class="inc-circle" style="color:#fff">'+PHONE_SVG.replace('<svg','<svg style="transform:rotate(135deg);stroke:#fff"')+'</span><span class="inc-label" id="incDeclineL"></span></button>'
    +'<button class="inc-btn inc-answer" id="incAnswer"><span class="inc-circle" style="color:#0d100a">'+PHONE_SVG.replace('<svg','<svg style="stroke:#0d100a"')+'</span><span class="inc-label" id="incAnswerL"></span></button>'
    +'</div>'
    +'<p class="inc-note" id="incNote"></p>'
    +'</div>';
  document.body.appendChild(d);
  document.getElementById('incAnswer').onclick=function(){ answer(); };
  document.getElementById('incDecline').onclick=function(){ decline(); };
}
/* Escape owns this layer while visible (app.js defers to .incallroot): a
   deliberate keypress declines the call. */
document.addEventListener('keydown',function(e){
  if(e.key!=='Escape'||!cur) return;
  const r=rootEl();
  if(r&&!r.hidden){ e.stopPropagation(); decline(); }
},true);

function avatarHTML(name,url){
  if(url) return '<img src="'+esc(url)+'" alt="">';
  const ch=(String(name||'?').trim()[0]||'?').toUpperCase();
  return esc(ch);
}
function stopRing(){ try{ if(HUB.sound) HUB.sound.stopRingtone(); }catch(e){} stopVibrate(); }
var vibTimer=0;
/* Pulse the vibration motor in sync with the ~6s ring loop (2s ring / 4s silence).
   navigator.vibrate exists on Android Chrome and some desktop browsers; iOS Safari
   never implemented it, so iPhones stay silent — an Apple platform limit, not a bug. */
function startVibrate(){
  stopVibrate();
  try{
    if(!navigator.vibrate) return;
    var pulse=function(){ try{ navigator.vibrate([2000,4000]); }catch(e){} };
    pulse();
    vibTimer=setInterval(pulse,6000);
  }catch(e){}
}
function stopVibrate(){
  if(vibTimer){ clearInterval(vibTimer); vibTimer=0; }
  try{ if(navigator.vibrate) navigator.vibrate(0); }catch(e){}
}

function show(opts){
  opts=opts||{};
  ensureRoot();
  if(cur) hide(true); /* replace a stale screen silently */
  const r=rootEl();
  const name=opts.name||t('inc.demoCaller');
  const ava=document.getElementById('incAva');
  ava.innerHTML=avatarHTML(name,opts.avatar);
  document.getElementById('incName').textContent=name;
  const sub=document.getElementById('incSub');
  if(opts.groupName){ sub.hidden=false; sub.textContent=opts.groupName; }
  else sub.hidden=true;
  document.getElementById('incKind').textContent=opts.kind==='video'?t('inc.videoCall'):t('inc.voiceCall');
  const tag=document.getElementById('incTag');
  if(opts.demo){ tag.hidden=false; tag.textContent=opts.demoLabel||t('inc.previewTag'); }
  else tag.hidden=true;
  document.getElementById('incAnswerL').textContent=t('inc.answer');
  document.getElementById('incDeclineL').textContent=t('inc.decline');
  document.getElementById('incNote').textContent=t('inc.note');
  r.setAttribute('aria-label',t('inc.voiceCall')+': '+name);
  r.hidden=false;
  /* the user's selected ringtone, on loop — stops on answer/decline/timeout */
  try{ if(HUB.sound) HUB.sound.playRingtone(); }catch(e){}
  startVibrate(); /* vibration pulses with the ring where the platform allows it */
  const rec={name:name,accept:opts.accept||function(){},reject:opts.reject||function(){},done:false,timerId:0};
  rec.timerId=setTimeout(function(){ onTimeout(rec); },TIMEOUT_MS);
  cur=rec;
}
function finish(rec,how){
  if(!rec||rec.done) return;
  rec.done=true;
  if(rec.timerId) clearTimeout(rec.timerId);
  stopRing();
  hide(true);
  if(how==='answer'){ try{ rec.accept(); }catch(e){} }
  else { try{ rec.reject(); }catch(e){} }
}
function answer(){ finish(cur,'answer'); }
function decline(){ finish(cur,'decline'); }
function hide(silent){
  const r=rootEl();
  if(r) r.hidden=true;
  if(!silent) stopRing();
  /* Always disarm the replaced record's 45s timer: show() replaces a stale
     screen via hide(true), and an orphaned timer would later kill the NEW
     screen, stop its ringtone, and log a bogus missed call. */
  if(cur&&cur.timerId){ try{ clearTimeout(cur.timerId); }catch(e){} cur.timerId=0; }
  cur=null;
}
function recordMissed(name){
  try{
    const st=HUB.store.state;
    st.missedCalls=st.missedCalls||[];
    st.missedCalls.push({name:String(name||'?'),ts:Date.now()});
    while(st.missedCalls.length>LS_MISSED_MAX) st.missedCalls.shift();
    HUB.store.save();
  }catch(e){}
}
function onTimeout(rec){
  if(!rec||rec.done) return;
  rec.done=true;
  stopRing();
  recordMissed(rec.name);
  try{ if(HUB.ui&&HUB.ui.toast) HUB.ui.toast(t('inc.missedFrom',{name:rec.name})); }catch(e){}
  try{ if(HUB.sound) HUB.sound.playNotification(); }catch(e){} /* now a silent no-op (2026-09-29: only the ringtone remains) */
  hide(true);
  try{ rec.reject(); }catch(e){} /* suppress re-ring on the signaling path */
}

HUB.incoming={
  show:show, hide:hide, answer:answer, decline:decline,
  isShowing:function(){ return !!cur; },
  /* QA-only introspection + timeout trigger (no waiting 45s in tests) */
  _debug:function(){
    const r=rootEl();
    return {showing:!!cur, visible:!!(r&&!r.hidden),
      name:cur?cur.name:null, ringing:!!(HUB.sound&&HUB.sound.isRinging())};
  },
  _missedNow:function(){ if(cur) onTimeout(cur); return !!cur; }
};
})();
