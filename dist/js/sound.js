/* ==================== sound.js — Onaro original sounds ====================
   100% synthesized audio (see audio/README.md): the built-in call ringtones.
   (2026-09-29: ALL other sound effects removed on PraBin's order — first the
   calculator key clicks and group-call mute cue, then the notification bird
   whistle too ("make it all silent, only need ringtone"). Only the call
   ringtone remains audible. playNotification/playMuteCue stay as silent
   no-ops so existing callers keep working without changes.)

   Ringtone preview: HUB.sound.preview(name) plays any ringtone once WITHOUT
   changing the saved selection; previewing() reports the key or null;
   onPreviewEnd(cb) fires when a preview ends or is stopped. Starting a
   preview stops any other preview and the looping ringtone.

   Custom ringtone: the user can pick their own audio file ("Use my own").
   The blob is stored in IndexedDB (localStorage can't hold audio reliably)
   and never leaves the device. If the custom file is missing/corrupt at
   play time, we honestly fall back to Aurora Soft with a toast.

   Autoplay policy: browsers may block audio until the user has interacted
   with the page once. playRingtone()/playNotification()/preview() never
   throw — a blocked play() is caught, and a blocked ringtone is retried
   after the first tap/keypress. Classic IIFE, no modules. */
(function(){
  'use strict';
  /* built-in ringtones (audio/README.md):
     - aurora: "Aurora Soft" — modern 2026 ambient tone, soft pads + gentle
       pluck motif + sub-bass pulse (PraBin's 2026-09-23 ask). Default for
       fresh installs.
     - breeze: "Aurora Breeze" — slightly brighter alt of the same piece.
     - phone: classic old-telephone bell (kept for existing users). */
  const DEFAULT_RING='aurora';
  /* Bump RING_VER whenever the built-in audio files change: iOS Safari
     aggressively caches audio by URL, so a new query string forces every
     phone to fetch the fresh file instead of replaying the stale one. */
  const RING_VER='5';
  const RINGS={aurora:'audio/ringtone-aurora',breeze:'audio/ringtone-breeze',phone:'audio/ringtone-phone'};
  const RING_KEYS=['aurora','breeze','phone','custom'];
  /* custom ringtone: IndexedDB blob, ~10MB cap */
  const IDB_DB='onaro', IDB_STORE='ringtones', IDB_KEY='custom-ring';
  const CUSTOM_MAX=10*1024*1024;

  let ringEl=null, ringElBase=null;
  let ringWanted=false, unlocked=false, ringTok=null;
  /* preview state */
  let pvEl=null, pvKey=null, pvTok=null, pvEndCb=null;
  /* custom ringtone: cached object URL for the IndexedDB blob */
  let customUrl=null;

  function prefs(){ return HUB.store.state.prefs; }
  function soundOn(){ return prefs().soundOn!==false; } /* default ON */
  function ringName(){
    const r=prefs().ringtone;
    if(RING_KEYS.indexOf(r)>=0) return r;
    /* one-time silent migration: all removed music ringtones
       (classic/warm/piano/violin/guitar/vocal) -> the new default */
    try{ prefs().ringtone=DEFAULT_RING; HUB.store.save(); }catch(e){}
    return DEFAULT_RING;
  }
  function ringBase(){ const r=ringName(); return RINGS[r]||RINGS.phone; }
  function toast(msg){ try{ if(HUB.ui&&HUB.ui.toast) HUB.ui.toast(msg); }catch(e){} }
  function tr(k){ try{ return HUB.i18n.t(k); }catch(e){ return k; } }

  /* pick the first format this browser can actually play */
  function srcFor(base){
    const q='?v='+RING_VER;
    try{
      const probe=new Audio();
      if(probe.canPlayType&&probe.canPlayType('audio/mpeg')) return base+'.mp3'+q;
    }catch(e){}
    return base+'.wav'+q;
  }
  function makeEl(base,loop){
    const el=new Audio();
    el.preload='auto'; el.loop=!!loop;
    el.src=srcFor(base);
    return el;
  }
  function makeElUrl(url,loop){
    const el=new Audio();
    el.preload='auto'; el.loop=!!loop;
    el.src=url;
    return el;
  }

  /* Preload + prime the SELECTED ringtone at boot (and on selection change)
     so an incoming call never pays a network fetch + decode on its critical
     path. Before this, playRingtone() built the Audio element lazily at call
     time — on iOS Safari over cellular the first audible sample waited for
     the whole 316KB mp3 to download and the media pipeline to spin up,
     which PraBin heard as "~10 seconds late". Priming moves all of that to
     boot; the call-time play() then starts from cache immediately. */
  function primeRingtone(){
    try{
      if(!soundOn()) return;
      if(ringName()==='custom'){
        customUrlAsync().then(function(url){
          if(!url) return;
          try{
            if(!ringEl||ringElBase!=='custom:'){ ringEl=makeElUrl(url,true); ringElBase='custom:'; }
            ringEl.load();
          }catch(e){}
        });
        return;
      }
      const base=ringBase();
      if(!ringEl||ringElBase!==base){ ringEl=makeEl(base,true); ringElBase=base; }
      ringEl.load(); /* preload='auto' + explicit load: fetch now, play later */
    }catch(e){}
  }

  /* Warm up on the first user gesture so a blocked ringtone can start.
     Registered once, lazily. */
  function armUnlock(){
    if(armUnlock.done) return; armUnlock.done=true;
    const unlock=function(){
      if(unlocked) return; unlocked=true;
      try{
        const Ctx=window.AudioContext||window.webkitAudioContext;
        if(Ctx){ const cx=new Ctx(); if(cx.state==='suspended') cx.resume().catch(function(){}); }
      }catch(e){}
      if(ringWanted&&ringEl&&ringEl.paused){
        try{ const pr=ringEl.play(); if(pr&&pr.catch) pr.catch(function(){}); }catch(e){}
      }
    };
    ['pointerdown','keydown','touchend'].forEach(function(ev){
      document.addEventListener(ev,unlock,{once:true,passive:true});
    });
  }

  /* ---------- custom ringtone (IndexedDB) ---------- */
  function idbOpen(){
    return new Promise(function(res,rej){
      try{
        const rq=indexedDB.open(IDB_DB,1);
        rq.onupgradeneeded=function(){ try{ rq.result.createObjectStore(IDB_STORE); }catch(e){} };
        rq.onsuccess=function(){ res(rq.result); };
        rq.onerror=function(){ rej(rq.error||new Error('idb')); };
      }catch(e){ rej(e); }
    });
  }
  function idbGet(){
    return idbOpen().then(function(db){
      return new Promise(function(res,rej){
        try{
          const rq=db.transaction(IDB_STORE,'readonly').objectStore(IDB_STORE).get(IDB_KEY);
          rq.onsuccess=function(){ res(rq.result||null); };
          rq.onerror=function(){ rej(rq.error||new Error('idb')); };
        }catch(e){ rej(e); }
      });
    });
  }
  function dropCustomUrl(){
    if(customUrl){ try{ URL.revokeObjectURL(customUrl); }catch(e){} }
    customUrl=null;
  }
  function customUrlAsync(){
    if(customUrl) return Promise.resolve(customUrl);
    return idbGet().then(function(blob){
      if(!blob||!blob.size){ dropCustomUrl(); return null; }
      try{ customUrl=URL.createObjectURL(blob); return customUrl; }
      catch(e){ return null; }
    }).catch(function(){ return null; });
  }
  /* honest fallback when the custom file can't be played */
  function customMissing(fromPreview){
    if(!fromPreview&&prefs().ringtone==='custom'){
      prefs().ringtone=DEFAULT_RING;
      try{ HUB.store.save(); }catch(e){}
    }
    toast(tr('me.set.ringBadFile'));
    if(fromPreview) return;
    /* fall back to the default tone and ring */
    try{
      ringEl=makeEl(RINGS[DEFAULT_RING],true); ringElBase=RINGS[DEFAULT_RING];
      ringEl.currentTime=0;
      const pr=ringEl.play();
      if(pr&&pr.catch) pr.catch(function(){});
    }catch(e){}
  }
  function setCustom(file){
    return new Promise(function(res,rej){
      if(!file||!file.size){ const err=new Error('nofile'); rej(err); return; }
      if(file.size>CUSTOM_MAX){ const err=new Error('toobig'); err.tooBig=true; rej(err); return; }
      idbOpen().then(function(db){
        const tx=db.transaction(IDB_STORE,'readwrite');
        tx.objectStore(IDB_STORE).put(file,IDB_KEY);
        tx.oncomplete=function(){
          dropCustomUrl();
          try{ prefs().customRingName=String(file.name||'').slice(0,80); HUB.store.save(); }catch(e){}
          res(true);
        };
        tx.onerror=function(){ rej(tx.error||new Error('idb')); };
      }).catch(rej);
    });
  }
  function hasCustom(){
    return idbGet().then(function(b){ return !!(b&&b.size); }).catch(function(){ return false; });
  }
  function customName(){
    try{ return prefs().customRingName||null; }catch(e){ return null; }
  }
  function removeCustom(){
    const done=function(){
      dropCustomUrl();
      try{
        if(prefs().ringtone==='custom') prefs().ringtone=DEFAULT_RING;
        prefs().customRingName=null;
        HUB.store.save();
      }catch(e){}
      return true;
    };
    return idbOpen().then(function(db){
      return new Promise(function(res){
        try{
          const tx=db.transaction(IDB_STORE,'readwrite');
          tx.objectStore(IDB_STORE).delete(IDB_KEY);
          tx.oncomplete=function(){ res(done()); };
          tx.onerror=function(){ res(done()); };
        }catch(e){ res(done()); }
      });
    }).catch(function(){ return done(); });
  }

  /* ---------- ringtone preview (plays once, never changes selection) ---------- */
  function stopPreview(silent){
    const was=pvKey;
    pvKey=null; pvTok=null;
    try{ if(pvEl){ pvEl.onended=null; pvEl.pause(); pvEl.currentTime=0; } }catch(e){}
    pvEl=null;
    if(was&&!silent&&pvEndCb){ try{ pvEndCb(null); }catch(e){} }
    return was;
  }
  function preview(name){
    armUnlock();
    if(!soundOn()){ toast(tr('me.set.ringNeedSound')); return 'off'; }
    if(RING_KEYS.indexOf(name)<0) name=DEFAULT_RING;
    if(pvKey===name){ stopPreview(); return 'stopped'; }
    stopPreview(true);
    stopRingtone(); /* a preview never overlaps the real ringtone */
    const tok={}; pvTok=tok;
    const startUrl=function(url){
      if(pvTok!==tok) return;
      try{
        pvEl=makeElUrl(url,false); pvKey=name;
        pvEl.onended=function(){ const k=pvKey; pvKey=null; pvTok=null; pvEl=null; if(pvEndCb){ try{ pvEndCb(k); }catch(e){} } };
        const pr=pvEl.play();
        if(pr&&pr.catch) pr.catch(function(){ if(pvTok===tok) stopPreview(); });
      }catch(e){ if(pvTok===tok) stopPreview(); }
    };
    if(name==='custom'){
      customUrlAsync().then(function(url){
        if(pvTok!==tok) return;
        if(url) startUrl(url); else customMissing(true);
      }).catch(function(){ if(pvTok===tok) customMissing(true); });
    }else{
      startUrl(srcFor(RINGS[name]||RINGS.phone));
    }
    return 'playing';
  }

  /* ---------- main API ---------- */
  function playRingtone(){
    armUnlock();
    if(!soundOn()) return;
    stopPreview(true);
    try{
      ringWanted=true;
      if(ringName()==='custom'){
        const tok={}; ringTok=tok;
        customUrlAsync().then(function(url){
          if(ringTok!==tok||!ringWanted) return;
          if(url){
            try{
              ringEl=makeElUrl(url,true); ringElBase='custom:';
              ringEl.currentTime=0;
              const pr=ringEl.play();
              if(pr&&pr.catch) pr.catch(function(){});
            }catch(e){}
          }else{
            customMissing(false);
          }
        }).catch(function(){ if(ringTok===tok&&ringWanted) customMissing(false); });
        return;
      }
      const base=ringBase();
      if(!ringEl||ringElBase!==base){ ringEl=makeEl(base,true); ringElBase=base; }
      ringEl.currentTime=0;
      const pr=ringEl.play();
      /* blocked by autoplay policy: unlock() retries after first gesture */
      if(pr&&pr.catch) pr.catch(function(){});
    }catch(e){ /* never throw out of a sound call */ }
  }
  function stopRingtone(){
    ringWanted=false; ringTok=null;
    try{ if(ringEl){ ringEl.pause(); ringEl.currentTime=0; } }catch(e){}
  }
  function isRinging(){
    try{ return !!(ringEl&&!ringEl.paused&&!ringEl.ended); }catch(e){ return false; }
  }
  /* Notification chime: REMOVED 2026-09-29 on PraBin's order
     ("make it all silent, I don't want any sound effect. Only need ringtone").
     Silent no-op so existing callers (store.js toast, incoming.js) keep
     working without changes. The bird-whistle audio files are deleted. */
  function playNotification(){ /* intentionally silent */ }
  /* Dedicated mute-feedback cue: REMOVED 2026-09-29 on PraBin's order
     ("remove sound effect from all except ringtone and notification").
     playMuteCue stays as a silent no-op so existing callers (call.js)
     keep working without changes. */
  function playMuteCue(){ /* intentionally silent */ }
  function setOn(v){
    prefs().soundOn=!!v;
    try{ HUB.store.save(); }catch(e){}
    if(!v){ stopRingtone(); stopPreview(true); }
    else { primeRingtone(); } /* re-enable: prime now so the next call rings instantly */
  }
  function setRingtone(name){
    if(RING_KEYS.indexOf(name)<0) return;
    prefs().ringtone=name;
    try{ HUB.store.save(); }catch(e){}
    /* the new selection takes effect on the next playRingtone(); prime it now
       so that next call doesn't pay a first-fetch delay */
    dropCustomUrl();
    if(!isRinging()){ ringEl=null; ringElBase=null; primeRingtone(); }
  }

  HUB.sound={
    playRingtone:playRingtone, stopRingtone:stopRingtone,
    playNotification:playNotification, isRinging:isRinging,
    playMuteCue:playMuteCue,
    enabled:soundOn, setOn:setOn,
    getRingtone:ringName, setRingtone:setRingtone,
    /* preload the selected ringtone now (boot / selection change) */
    primeRingtone:primeRingtone,
    /* preview: hear before you pick (selection untouched) */
    preview:preview, stopPreview:stopPreview,
    previewing:function(){ return pvKey; },
    onPreviewEnd:function(cb){ pvEndCb=cb; },
    /* custom ringtone (user's own file, IndexedDB, stays on device) */
    setCustom:setCustom, hasCustom:hasCustom,
    removeCustom:removeCustom, customName:customName,
    /* QA-only introspection (not user-facing) */
    _debug:function(){
      return {on:soundOn(),ringing:isRinging(),wanted:ringWanted,
        unlocked:unlocked,chimes:chimeCount,ringtone:ringName(),
        ringSrc:ringEl?ringEl.src:null,noteSrc:noteEl?noteEl.src:null,
        ringReady:ringEl?ringEl.readyState:-1,ringBase:ringElBase,
        previewing:pvKey,customUrl:!!customUrl,maxCustom:CUSTOM_MAX};
    }
  };
})();

