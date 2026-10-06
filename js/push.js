/* ==================== push.js — Web Push groundwork for incoming calls ======
   What a website CAN do when the app is closed: Web Push. What it can NEVER
   do: a native lock-screen call takeover on iOS (CallKit is native-only) —
   the in-app full-screen screen is js/incoming.js. This module is the honest
   groundwork: service-worker registration, notification permission, VAPID
   subscription, and delivery of the subscription to the signaling worker.

   Closed-app alerts need ALL of: (a) Onaro installed to the home screen,
   (b) notification permission granted, (c) the free signaling worker deployed
   AND sending pushes (see server/DEPLOY.md), (d) on iOS, iOS 16.4+.
   Without any of these the toggle degrades honestly instead of pretending.
   Classic IIFE, no modules. */
(function(){
'use strict';
/* module translation helper — never name a local/param `t` (shadowing bug) */
const t=function(k,v){ return HUB.i18n.t(k,v); };
const BC_NAME='onaro-call';
/* >>> OPERATOR: generate a real pair (e.g. `npx web-push generate-vapid-keys`)
   and paste the PUBLIC key here. The worker needs the private half.
   Until then subscribe() refuses honestly instead of failing cryptically. */
const VAPID_PUBLIC_KEY='REPLACE_WITH_YOUR_VAPID_PUBLIC_KEY';
const SW_PATH='sw.js';

let regPromise=null;

function prefs(){ return HUB.store.state.prefs; }
function toast(msg){ try{ if(HUB.ui&&HUB.ui.toast) HUB.ui.toast(msg); }catch(e){} }
function workerUrl(){ try{ return HUB.store.state.callWorkerUrl||''; }catch(e){ return ''; } }

function supported(){
  try{
    return ('serviceWorker' in navigator)&&('PushManager' in window)&&('Notification' in window);
  }catch(e){ return false; }
}
function permission(){
  try{ return ('Notification' in window)?Notification.permission:'unsupported'; }
  catch(e){ return 'unsupported'; }
}
function isOn(){ try{ return prefs().pushOn===true; }catch(e){ return false; } }

function registerSW(){
  if(regPromise) return regPromise;
  regPromise=(function(){
    if(!supported()) return Promise.resolve(null);
    /* file:// and other non-http(s) origins can't host a worker — degrade */
    if(!/^https?:$/.test(location.protocol)) return Promise.resolve(null);
    try{
      return navigator.serviceWorker.register(SW_PATH).catch(function(){ return null; });
    }catch(e){ return Promise.resolve(null); }
  })();
  return regPromise;
}
function urlBase64ToUint8Array(base64){
  const pad='='.repeat((4-base64.length%4)%4);
  const bin=atob((base64+pad).replace(/-/g,'+').replace(/_/g,'/'));
  const out=new Uint8Array(bin.length);
  for(let i=0;i<bin.length;i++) out[i]=bin.charCodeAt(i);
  return out;
}
function pushEndpoint(){
  /* worker URL looks like wss://host/call — pushes go to https://host/push */
  const u=workerUrl();
  if(!u) return '';
  return u.replace(/^wss:/i,'https:').replace(/^ws:/i,'http:').replace(/\/call\/?$/i,'/push');
}

function subscribe(){
  if(!supported()) return Promise.resolve({ok:false,reason:'unsupported'});
  if(!workerUrl()) return Promise.resolve({ok:false,reason:'needWorker'});
  if(VAPID_PUBLIC_KEY.indexOf('REPLACE_')===0)
    return Promise.resolve({ok:false,reason:'noVapid'});
  const perm=permission();
  const go=perm==='granted'
    ? Promise.resolve('granted')
    : (perm==='denied'
        ? Promise.resolve('denied')
        : Notification.requestPermission().catch(function(){ return 'denied'; }));
  return go.then(function(p){
    if(p!=='granted') return {ok:false,reason:'denied'};
    return registerSW().then(function(reg){
      if(!reg) return {ok:false,reason:'swFail'};
      return reg.pushManager.subscribe({
        userVisibleOnly:true,
        applicationServerKey:urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
      }).then(function(sub){
        return fetch(pushEndpoint(),{
          method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({subscription:sub.toJSON?sub.toJSON():sub})
        }).then(function(r){
          if(!r.ok) throw new Error('http '+r.status);
          try{
            prefs().pushOn=true; prefs().pushSub={endpoint:sub.endpoint||'',ts:Date.now()};
            HUB.store.save();
          }catch(e){}
          return {ok:true};
        });
      }).catch(function(){ return {ok:false,reason:'subFail'}; });
    });
  }).catch(function(){ return {ok:false,reason:'subFail'}; });
}
function unsubscribe(){
  try{ prefs().pushOn=false; prefs().pushSub=null; HUB.store.save(); }catch(e){}
  registerSW().then(function(reg){
    if(!reg||!reg.pushManager) return;
    reg.pushManager.getSubscription().then(function(sub){
      if(sub){ try{ sub.unsubscribe(); }catch(e){} }
    }).catch(function(){});
  });
  /* best-effort: tell the worker to forget this endpoint */
  try{
    const ep=pushEndpoint();
    if(ep) fetch(ep,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({remove:true})}).catch(function(){});
  }catch(e){}
  return Promise.resolve({ok:true});
}
function setOn(v){
  if(!v) return unsubscribe();
  return subscribe().then(function(r){
    if(!r.ok){
      try{ prefs().pushOn=false; HUB.store.save(); }catch(e){}
      toast(reasonCopy(r.reason));
    }
    return r;
  });
}
function reasonCopy(reason){
  if(reason==='needWorker') return t('push.needWorker');
  if(reason==='denied'||reason==='blocked') return t('push.blocked');
  if(reason==='noVapid') return t('push.noVapid');
  return t('push.failed');
}

/* Answer/Decline from the service worker, and the #call= deep link. */
function joinCall(groupId){
  if(!groupId||!HUB.call) return;
  try{
    if(HUB.call.isActive&&HUB.call.isActive()) return; /* already in a call */
    HUB.call.start(groupId);
  }catch(e){}
}
function init(){
  registerSW();
  /* service-worker taps while the app is open: Answer joins, Decline dismisses */
  try{
    const bc=new BroadcastChannel(BC_NAME);
    bc.onmessage=function(ev){
      const m=ev&&ev.data;
      if(!m) return;
      if(m.type==='decline'){
        try{ if(HUB.incoming&&HUB.incoming.isShowing()) HUB.incoming.decline(); }catch(e){}
      }else if(m.type==='answer'){
        joinCall(m.groupId);
      }
    };
  }catch(e){}
  /* deep link from a push tap on a closed app: ./#call=<groupId> */
  window.addEventListener('load',function(){
    setTimeout(function(){
      try{
        const h=String(location.hash||'');
        const m=h.match(/#call=([^&]*)/);
        if(m&&m[1]){
          history.replaceState(null,'',location.pathname+location.search);
          joinCall(decodeURIComponent(m[1]));
        }
      }catch(e){}
    },800);
  });
}

HUB.push={
  supported:supported, permission:permission,
  subscribe:subscribe, unsubscribe:unsubscribe,
  isOn:isOn, setOn:setOn, init:init,
  _debug:function(){
    return {supported:supported(),permission:permission(),on:isOn(),
      vapidSet:VAPID_PUBLIC_KEY.indexOf('REPLACE_')!==0,
      worker:!!workerUrl()};
  }
};
init();
})();
