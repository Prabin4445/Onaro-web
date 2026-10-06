/* HUB safeboot — self-healing safety net. Loads FIRST (before i18n.js).
   - Captures window.onerror + unhandledrejection from the very start.
   - Bounded, LOCAL-ONLY error ring buffer. Nothing is ever sent anywhere.
   - Boot watchdog: if the app fails to initialize, a branded safe-recovery
     screen appears (Reload / Reset local data) instead of a blank page.
   - fetchJSON(): retries with backoff + timeout for data files.
   - loadState/saveState(): schema-versioned localStorage with corrupt backup
     and missing-key backfill — repairs state instead of crashing on it.
   Silent by design (no audio). No dependencies. Never throws. */
(function(){
'use strict';
/* namespace first — every later script expects window.HUB to exist */
var HUB = window.HUB || (window.HUB = {});

var ERR_MAX = 30;             /* ring buffer cap */
var BOOT_TIMEOUT_MS = 15000;  /* watchdog */
var SCHEMA_V = 3;             /* hub_v1 schema version */
var errors = [];
var booted = false;
var errCount = 0;
try{ errCount = parseInt(localStorage.getItem('hub_errcount')||'0',10)||0; }catch(e){}

function stamp(){ return new Date().toISOString(); }

function record(kind, msg, file, line){
  try{
    errors.push({t: stamp(), kind: kind, msg: String(msg==null?'':msg).slice(0,300),
                 file: String(file||'').slice(-80), line: line||0});
    if(errors.length > ERR_MAX) errors.splice(0, errors.length - ERR_MAX);
    errCount++;
    try{ localStorage.setItem('hub_errcount', String(errCount)); }catch(e){}
  }catch(e){}
}

/* Capture from the earliest possible moment. These handlers never throw,
   never show UI by themselves, and never exfiltrate anything. */
try{
  window.addEventListener('error', function(ev){
    record('error', ev && ev.message, ev && ev.filename, ev && ev.lineno);
    softRecover();
  }, true);
  window.addEventListener('unhandledrejection', function(ev){
    var r = ev && ev.reason;
    record('unhandledrejection', (r && (r.message || r)) || 'rejection', '', 0);
    try{ if(ev && ev.preventDefault) ev.preventDefault(); }catch(e){}
    softRecover();
  }, true);
}catch(e){}

/* If the app shell is up, surface one quiet toast per burst so a repeated
   fault doesn't spam. If the shell isn't up, stay silent — the watchdog
   owns that case. */
var lastToast = 0;
function softRecover(){
  try{
    if(booted) return;
    if(!document || !document.body) return;
    var now = Date.now();
    if(now - lastToast < 8000) return;
    lastToast = now;
    if(HUB.ui && HUB.ui.toast){
      HUB.ui.toast('Hmm, that hiccuped — recovered.');
    }
  }catch(e){}
}

/* ---------- boot watchdog ---------- */
function showRecovery(reason){
  try{
    if(document.getElementById('saferecov')) return;
    var ov = document.createElement('div');
    ov.id = 'saferecov';
    ov.setAttribute('role','alert');
    ov.style.cssText = 'position:fixed;inset:0;z-index:99999;display:block;background:#0D100A;color:#F2F5E9;font-family:system-ui,-apple-system,sans-serif;padding:24px;box-sizing:border-box;';
    ov.innerHTML =
      '<div style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:calc(100% - 48px);max-width:340px;text-align:center;">'+
      '<div style="font-size:44px;margin-bottom:12px;">🪐</div>'+
      '<div style="font-size:20px;font-weight:800;margin-bottom:8px;">Onaro couldn\'t start</div>'+
      '<div style="font-size:14px;opacity:.75;margin-bottom:20px;">Something blocked the app from loading. Your data is safe — pick a fix below.</div>'+
      '<button id="srReload" style="display:block;width:100%;padding:14px;margin-bottom:10px;border:0;border-radius:14px;background:#C6F135;color:#0D100A;font-size:16px;font-weight:800;cursor:pointer;">Reload app</button>'+
      '<button id="srReset" style="display:block;width:100%;padding:14px;border:1px solid rgba(255,255,255,.2);border-radius:14px;background:transparent;color:#F2F5E9;font-size:15px;font-weight:600;cursor:pointer;">Reset local data &amp; reload</button>'+
      '<div style="font-size:11px;opacity:.5;margin-top:14px;">Reset backs up your data first — nothing is lost silently.</div>'+
      '</div>';
    document.body.appendChild(ov);
    document.getElementById('srReload').onclick = function(){ location.reload(); };
    document.getElementById('srReset').onclick = function(){
      try{
        var raw = null;
        try{ raw = localStorage.getItem('hub_v1'); }catch(e){}
        if(raw){
          try{ localStorage.setItem('hub_v1.reset.'+Date.now(), raw); }catch(e){}
          pruneBackups('hub_v1.reset.');
        }
        try{ localStorage.removeItem('hub_v1'); }catch(e){}
      }catch(e){}
      location.reload();
    };
    record('watchdog', 'recovery shown: '+(reason||'boot timeout'), '', 0);
  }catch(e){}
}

function pruneBackups(prefix){
  try{
    var ks = [];
    for(var i=0;i<localStorage.length;i++){ var k=localStorage.key(i); if(k&&k.indexOf(prefix)===0) ks.push(k); }
    ks.sort();
    while(ks.length > 3){ try{ localStorage.removeItem(ks.shift()); }catch(e){} }
  }catch(e){}
}

try{
  setTimeout(function(){
    if(!booted) showRecovery('boot timeout');
  }, BOOT_TIMEOUT_MS);
}catch(e){}

/* ---------- fetch with resilience ---------- */
function fetchJSON(url, opts){
  opts = opts || {};
  var retries = (opts.retries==null)?2:opts.retries;
  var timeout = opts.timeout||9000;
  var attempt = 0;
  function one(){
    attempt++;
    var ctrl = null, timer = null;
    try{
      if(typeof AbortController!=='undefined'){
        ctrl = new AbortController();
        timer = setTimeout(function(){ try{ ctrl.abort(); }catch(e){} }, timeout);
      }
    }catch(e){}
    var p;
    try{
      p = fetch(url, ctrl?{signal:ctrl.signal}:undefined);
    }catch(e){
      return Promise.reject(e);
    }
    return p.then(function(r){
      if(timer) clearTimeout(timer);
      /* file:// yields status 0 with a real body — accept it */
      if(!r.ok && r.status!==0) throw new Error('http '+r.status+' '+url);
      return r.json();
    }).catch(function(err){
      if(timer) clearTimeout(timer);
      if(attempt <= retries){
        var wait = 500*Math.pow(2, attempt-1);
        return new Promise(function(res){ setTimeout(res, wait); }).then(one);
      }
      throw err;
    });
  }
  return one();
}

/* ---------- self-repairing state ---------- */
function loadState(key, seedFn){
  var raw = null, parsed = null, corrupt = false;
  try{ raw = localStorage.getItem(key); }catch(e){ raw = null; }
  if(raw){
    try{ parsed = JSON.parse(raw); }
    catch(e){ corrupt = true; parsed = null; }
  }
  if(corrupt){
    /* back the damaged bytes up BEFORE replacing them — never wipe silently */
    try{
      localStorage.setItem(key+'.corrupt.'+Date.now(), raw);
      pruneBackups(key+'.corrupt.');
    }catch(e){}
    record('state', 'corrupt state backed up, defaults restored', key, 0);
  }
  var fresh = null;
  try{ fresh = seedFn(); }catch(e){ fresh = {}; }
  var st = (parsed && typeof parsed==='object' && !Array.isArray(parsed)) ? parsed : null;
  if(!st){
    st = fresh;
  }else{
    /* fill any missing top-level keys from fresh seeds — repairs partial or
       legacy states without touching the user's existing data */
    try{
      for(var k in fresh){
        if(Object.prototype.hasOwnProperty.call(fresh,k) && st[k]===undefined) st[k]=fresh[k];
      }
    }catch(e){}
  }
  try{ st._v = SCHEMA_V; }catch(e){}
  return st;
}

function saveState(key, obj){
  try{
    localStorage.setItem(key, JSON.stringify(obj));
    return true;
  }catch(e){
    /* quota: drop oldest backups and retry once */
    try{
      pruneBackups(key+'.corrupt.');
      pruneBackups(key+'.reset.');
      localStorage.setItem(key, JSON.stringify(obj));
      return true;
    }catch(e2){
      record('state', 'save failed (quota)', key, 0);
      return false;
    }
  }
}

/* Public surface. report() is local-only diagnostics for QA. */
HUB.safe = {
  booted: function(){ booted = true; },
  isBooted: function(){ return booted; },
  errors: function(){ return errors.slice(); },
  errCount: function(){ return errCount; },
  report: function(){ return {booted: booted, errCount: errCount, recent: errors.slice()}; },
  fetchJSON: fetchJSON,
  loadState: loadState,
  saveState: saveState,
  showRecovery: showRecovery,
  schemaV: SCHEMA_V
};
})();
