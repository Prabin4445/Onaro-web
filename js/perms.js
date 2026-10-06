/* ============================================================
   HUB.perms — app-wide permission manager (2026-09-30)
   Pre-prompt explainers in Onaro style, real browser prompts,
   per-profile memory (hub_perms_v1), and a blocked-state rescue
   sheet with exact platform steps. Used by the Student Scanner
   (camera capture + photo/file picking) and anywhere else that
   needs camera / photos / location / notifications.
   ============================================================ */
(function(){
'use strict';
var HUB=window.HUB||(window.HUB={});
var t=function(k,v){ return HUB.i18n.t(k,v); };
var ui=function(){ return HUB.ui||{}; };
var esc=function(s){ var u=ui(); return u.esc?u.esc(String(s==null?'':s)):String(s==null?'':s); };

var LS='hub_perms_v1';
var PERMS={
  camera:       {icon:'\uD83D\uDCF7'},
  photos:       {icon:'\uD83D\uDDBC\uFE0F'},
  location:     {icon:'\uD83D\uDCCD'},
  notifications:{icon:'\uD83D\uDD14'}
};

function load(){ try{ return JSON.parse(localStorage.getItem(LS)||'{}'); }catch(e){ return {}; } }
function save(d){ try{ localStorage.setItem(LS,JSON.stringify(d)); }catch(e){} }
function me(){
  try{ var p=HUB.store&&HUB.store.state&&HUB.store.state.profile; return (p&&p.name)||'anon'; }
  catch(e){ return 'anon'; }
}
function bucket(){
  var d=load(); d.profiles=d.profiles||{};
  var m=me(); d.profiles[m]=d.profiles[m]||{};
  return {d:d,r:d.profiles[m]};
}
function getSt(name){ return bucket().r[name]||null; }
function setSt(name,st){ var x=bucket(); x.r[name]=st; save(x.d); }

function platform(){
  var ua=navigator.userAgent||'';
  if(/iPad|iPhone|iPod/.test(ua)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1)) return 'ios';
  if(/Android/.test(ua)) return 'android';
  return 'other';
}

/* ---- sheet plumbing: resolve false if the user dismisses via ✕/backdrop/Escape ----
   Sheets open only after the boot splash is gone (splash z-1000 sits above
   the sheet host z-70); a sheet opened during boot waits instead of hiding
   behind the splash where it can't be seen or tapped. */
function splashGone(){
  var s=document.getElementById('splash');
  return !s||s.classList.contains('splash-out');
}
function openSheetWhenReady(html){
  return new Promise(function(res){
    var u=ui();
    if(!u.openSheet){ res(false); return; }
    var t0=Date.now();
    (function tick(){
      if(splashGone()||Date.now()-t0>15000){ u.openSheet(html); res(true); }
      else setTimeout(tick,250);
    })();
  });
}
function sheetDone(resolve,val){
  var u=ui(); if(u.closeSheet) u.closeSheet();
  resolve(val);
}
function watchDismiss(resolve){
  var iv=setInterval(function(){
    var host=document.getElementById('sheetHost');
    if(host&&host.hidden){ clearInterval(iv); resolve(false); }
  },300);
  return iv;
}

/* ---- 1. pre-prompt explainer (first time per permission) ---- */
function explainer(name){
  return new Promise(function(resolve){
    var P=PERMS[name];
    var html='<div class="pm-sheet">'+
      '<div class="pm-ic" aria-hidden="true">'+P.icon+'</div>'+
      '<div class="pm-title">'+esc(t('perm.'+name+'Title'))+'</div>'+
      '<div class="pm-why">'+esc(t('perm.'+name+'Why'))+'</div>'+
      '<div class="pm-row">'+
      '<button class="pm-btn pm-ghost" data-pm-no>'+esc(t('perm.notNow'))+'</button>'+
      '<button class="pm-btn pm-go" data-pm-yes>'+esc(t('perm.allow'))+'</button>'+
      '</div></div>';
    openSheetWhenReady(html).then(function(opened){
      if(!opened){ resolve(true); return; } /* no sheet system: skip straight through */
      var iv=watchDismiss(resolve);
      var box=document.getElementById('sheetBox');
      var by=box&&box.querySelector('[data-pm-yes]'), bn=box&&box.querySelector('[data-pm-no]');
      if(by) by.onclick=function(){ clearInterval(iv); sheetDone(resolve,true); };
      if(bn) bn.onclick=function(){ clearInterval(iv); sheetDone(resolve,false); };
    });
  });
}

/* ---- 2. real browser prompts ---- */
function errKind(e){
  var n=e&&(e.name||e.code);
  if(n==='NotAllowedError'||n===1) return 'denied';
  if(n==='NotFoundError'||n==='DevicesNotFoundError') return 'nocam';
  if(n==='NotReadableError'||n==='TrackStartError') return 'busy';
  return 'error';
}
function realPrompt(name){
  if(name==='camera'){
    if(!(navigator.mediaDevices&&navigator.mediaDevices.getUserMedia))
      return Promise.resolve({ok:false,reason:'unsupported'});
    return navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'},audio:false})
      .then(function(stream){
        try{ stream.getTracks().forEach(function(tr){ tr.stop(); }); }catch(e){}
        return {ok:true};
      })
      .catch(function(e){ return {ok:false,reason:errKind(e)}; });
  }
  if(name==='photos'){
    /* <input type=file> has no OS-level prompt; the explainer is the permission step */
    return Promise.resolve({ok:true});
  }
  if(name==='location'){
    if(!navigator.geolocation) return Promise.resolve({ok:false,reason:'unsupported'});
    return new Promise(function(res){
      var done=false;
      function fin(v){ if(!done){ done=true; res(v); } }
      try{
        navigator.geolocation.getCurrentPosition(
          function(){ fin({ok:true}); },
          function(e){ fin({ok:false,reason:(e&&e.code===1)?'denied':'error'}); },
          {timeout:15000,maximumAge:600000});
      }catch(e){ fin({ok:false,reason:'error'}); }
      setTimeout(function(){ fin({ok:false,reason:'error'}); },16000);
    });
  }
  if(name==='notifications'){
    if(!('Notification' in window)||!Notification.requestPermission)
      return Promise.resolve({ok:false,reason:'unsupported'});
    try{
      var r=Notification.requestPermission();
      if(r&&r.then) return r.then(function(p){ return p==='granted'?{ok:true}:{ok:false,reason:'denied'}; });
      return Promise.resolve(Notification.permission==='granted'?{ok:true}:{ok:false,reason:'denied'});
    }catch(e){ return Promise.resolve({ok:false,reason:'error'}); }
  }
  return Promise.resolve({ok:false,reason:'unsupported'});
}

/* ---- simple message sheet (no camera / camera busy / unexpected error) ---- */
function noteSheet(titleKey,msgKey){
  return new Promise(function(resolve){
    openSheetWhenReady('<div class="pm-sheet"><div class="pm-title">'+esc(t(titleKey))+'</div>'+
      '<div class="pm-why">'+esc(t(msgKey))+'</div>'+
      '<div class="pm-row"><button class="pm-btn pm-go" data-pm-ok>'+esc(t('perm.ok'))+'</button></div></div>')
    .then(function(opened){
      if(!opened){ resolve(false); return; }
      var iv=watchDismiss(resolve);
      var box=document.getElementById('sheetBox');
      var b=box&&box.querySelector('[data-pm-ok]');
      if(b) b.onclick=function(){ clearInterval(iv); sheetDone(resolve,false); };
    });
  });
}

/* ---- 4. blocked-state rescue sheet with exact platform steps ---- */
function rescue(name,reason){
  return new Promise(function(resolve){
    var pf=platform();
    var setting=t('perm.set_'+name);
    var steps=pf==='ios'?t('perm.iosSteps',{setting:setting})
      :pf==='android'?t('perm.andSteps',{setting:setting})
      :t('perm.desktopSteps',{setting:setting});
    var title=reason==='nocam'?t('perm.noCamera')
      :reason==='busy'?t('perm.camBusy')
      :t('perm.offTitle',{name:t('perm.name_'+name)});
    var html='<div class="pm-sheet">'+
      '<div class="pm-ic" aria-hidden="true">\u26A0\uFE0F</div>'+
      '<div class="pm-title">'+esc(title)+'</div>'+
      '<div class="pm-why">'+esc(t('perm.offMsg'))+'</div>'+
      '<div class="pm-steps">'+esc(steps)+'</div>'+
      '<div class="pm-webnote">'+esc(t('perm.webNote'))+'</div>'+
      '<div class="pm-row">'+
      '<button class="pm-btn pm-ghost" data-pm-cancel>'+esc(t('perm.cancel'))+'</button>'+
      '<button class="pm-btn pm-go" data-pm-retry>'+esc(t('perm.tryAgain'))+'</button>'+
      '</div></div>';
    openSheetWhenReady(html).then(function(opened){
      if(!opened){ resolve(false); return; }
      var iv=watchDismiss(resolve);
      var box=document.getElementById('sheetBox');
      var br=box&&box.querySelector('[data-pm-retry]'), bc=box&&box.querySelector('[data-pm-cancel]');
      if(br) br.onclick=function(){ clearInterval(iv); sheetDone(resolve,true); };
      if(bc) bc.onclick=function(){ clearInterval(iv); sheetDone(resolve,false); };
    });
  });
}

/* one real-prompt attempt; records the outcome; never loops the rescue sheet */
function attempt(name){
  return realPrompt(name).then(function(r){
    if(r.ok){ setSt(name,'granted'); return true; }
    if(r.reason==='denied'){ setSt(name,'denied'); return 'denied'; }
    if(r.reason==='unsupported'){
      var u=ui(); if(u.toast) u.toast(t('perm.unsupported'));
      return false;
    }
    return r.reason; /* 'nocam' | 'busy' | 'error' */
  });
}

/* ---- non-blocking one-time explainer ("nudge") ----
   iOS Safari SILENTLY ignores input.click() on file inputs when the call is
   not synchronous inside the user's tap handler. File picking must therefore
   NEVER be gated on the async ensure() chain. nudge() shows the explainer
   fire-and-forget (once per profile) and returns immediately, so the caller
   can still input.click() synchronously in the same gesture. */
function nudge(name){
  if(!PERMS[name]) return;
  try{
    var x=bucket();
    if(x.r[name]||x.r[name+'_seen']) return; /* granted already, or nudged before */
    x.r[name+'_seen']=1; save(x.d);
    explainer(name).then(function(){},function(){});
  }catch(e){}
}

/* ---- public API ---- */
function ensure(name){
  if(!PERMS[name]) return Promise.resolve(false);
  var st=getSt(name);
  if(st==='granted') return Promise.resolve(true);
  if(st==='denied'){
    return rescue(name,'denied').then(function(again){
      if(!again) return false;
      return attempt(name).then(function(r){ return r===true; });
    });
  }
  return explainer(name).then(function(want){
    if(!want) return false; /* "Not now" — explainer shows again next time */
    return attempt(name).then(function(r){
      if(r===true) return true;
      if(r==='denied'){
        return rescue(name,'denied').then(function(again){
          if(!again) return false;
          return attempt(name).then(function(x){ return x===true; });
        });
      }
      if(r===false) return false;
      return noteSheet(r==='nocam'?'perm.noCamera':r==='busy'?'perm.camBusy':'perm.somethingWrong',
        r==='nocam'?'perm.noCameraMsg':r==='busy'?'perm.camBusyMsg':'perm.somethingWrongMsg').then(function(){ return false; });
    });
  });
}

function status(name){
  if(!PERMS[name]) return 'unknown';
  return getSt(name)||'prompt';
}

HUB.perms={
  ensure:ensure,
  nudge:nudge,
  status:status,
  rescue:rescue,
  supported:function(name){
    if(name==='camera') return !!(navigator.mediaDevices&&navigator.mediaDevices.getUserMedia);
    if(name==='photos') return true;
    if(name==='location') return !!navigator.geolocation;
    if(name==='notifications') return ('Notification' in window)&&!!Notification.requestPermission;
    return false;
  },
  _t:{
    reset:function(){ var x=bucket(); x.r={}; save(x.d); },
    setState:function(name,st){ setSt(name,st); },
    platform:platform
  }
};
})();
