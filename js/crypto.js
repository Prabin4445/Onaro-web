/* HUB CRYPTO: real device-level encryption at rest.
   - AES-GCM 256 via WebCrypto. One device key, generated with
     crypto.getRandomValues, stored non-extractable in IndexedDB
     (a separate storage bucket from localStorage, so a copied
     localStorage file alone only contains ciphertext).
   - Applied to: chat message text, chat image/file payloads,
     Daily task text, Daily note text.
   - HONESTY, READ THIS: this is ENCRYPTION ON THIS DEVICE — it protects
     data at rest on the phone/browser. It is NOT end-to-end encryption
     between two people: true E2EE needs per-user keys exchanged through
     a server with real accounts, which is a production-backend milestone.
     The UI label says "Encrypted on this device" and never claims E2EE.
   - If WebCrypto/IndexedDB is unavailable, content stays plaintext and
     NO lock label is shown (never display a lock you didn't earn). */
(function(){
'use strict';

const DB_NAME='onaro-keys', STORE_NAME='keys', KEY_ID='device-aes-gcm-v1';

function subtle(){
  try{ return (window.crypto&&window.crypto.subtle)||null; }catch(e){ return null; }
}
function idbOK(){ return typeof window.indexedDB!=='undefined'; }

/* base64 <-> bytes */
function b64enc(bytes){
  let s=''; const b=new Uint8Array(bytes);
  for(let i=0;i<b.length;i+=0x8000) s+=String.fromCharCode.apply(null,b.subarray(i,i+0x8000));
  return btoa(s);
}
function b64dec(s){
  const bin=atob(String(s||'')); const b=new Uint8Array(bin.length);
  for(let i=0;i<bin.length;i++) b[i]=bin.charCodeAt(i);
  return b;
}
function openDB(){
  return new Promise((res,rej)=>{
    try{
      const rq=window.indexedDB.open(DB_NAME,1);
      rq.onupgradeneeded=()=>{ rq.result.createObjectStore(STORE_NAME); };
      rq.onsuccess=()=>res(rq.result);
      rq.onerror=()=>rej(rq.error);
    }catch(e){ rej(e); }
  });
}
function idbGet(db){
  return new Promise((res,rej)=>{
    try{
      const tx=db.transaction(STORE_NAME,'readonly');
      const rq=tx.objectStore(STORE_NAME).get(KEY_ID);
      rq.onsuccess=()=>res(rq.result||null);
      rq.onerror=()=>rej(rq.error);
    }catch(e){ rej(e); }
  });
}
function idbSet(db,val){
  return new Promise((res,rej)=>{
    try{
      const tx=db.transaction(STORE_NAME,'readwrite');
      const rq=tx.objectStore(STORE_NAME).put(val,KEY_ID);
      rq.onsuccess=()=>res(true);
      rq.onerror=()=>rej(rq.error);
    }catch(e){ rej(e); }
  });
}

let keyPromise=null;
/* plaintext cache lives in a WeakMap — NEVER on the item itself, or the next
   store.save() would serialize decrypted text back into localStorage. */
const plainCache=new WeakMap();
function peek(item){ return (item&&plainCache.get(item))||null; }
function getKey(){
  if(keyPromise) return keyPromise;
  keyPromise=(async()=>{
    const s=subtle();
    if(!s||!idbOK()) return null;
    try{
      const db=await openDB();
      let k=await idbGet(db);
      if(!k){
        k=await s.generateKey({name:'AES-GCM',length:256},false,['encrypt','decrypt']);
        await idbSet(db,k);
      }
      return k;
    }catch(e){ return null; }
  })();
  return keyPromise;
}
/* kick off early so the key is warm by first use */
getKey();

function isEncShape(o){ return o&&typeof o==='object'&&typeof o.iv==='string'&&typeof o.ct==='string'; }

async function encryptText(plain){
  plain=String(plain==null?'':plain);
  if(!plain) return null;
  try{
    const s=subtle(), k=await getKey();
    if(!s||!k) return null;               // unavailable -> caller stores plaintext
    const iv=window.crypto.getRandomValues(new Uint8Array(12));
    const data=new TextEncoder().encode(plain);
    const ct=await s.encrypt({name:'AES-GCM',iv:iv},k,data);
    return {iv:b64enc(iv),ct:b64enc(ct)};
  }catch(e){ return null; }                // mid-flight WebCrypto failure -> plaintext fallback, never an unhandled rejection
}
async function decryptText(enc){
  if(!isEncShape(enc)) return null;
  try{
    const s=subtle(), k=await getKey();
    if(!s||!k) return null;
    const pt=await s.decrypt({name:'AES-GCM',iv:b64dec(enc.iv)},k,b64dec(enc.ct));
    return new TextDecoder().decode(pt);
  }catch(e){ return null; }
}
/* Resolve the readable text of an item shaped {text?, enc?}.
   Legacy plaintext keeps working; undecryptable content yields an
   honest placeholder instead of garbage. Result cached on the item. */
async function textOf(item){
  if(!item) return '';
  const hit=plainCache.get(item);
  if(hit!=null) return hit;
  let out;
  if(isEncShape(item.enc)){
    try{
      const p=await decryptText(item.enc);
      out=(p==null?t('crypto.locked'):p);
    }catch(e){ out=t('crypto.locked'); }
  }else{
    out=String(item.text==null?'':item.text);
  }
  plainCache.set(item,out);
  return out;
}
function locked(item){ return isEncShape(item&&item.enc); }
function t(k){ try{ return HUB.i18n.t(k); }catch(e){ return k; } }

/* lock label for UI — empty string when encryption isn't actually active */
async function available(){
  const k=await getKey();
  return !!k;
}
async function lockHTML(){
  if(!(await available())) return '';
  return '<span class="locknote">'+uiEsc('🔒')+' '+escHtml(t('crypto.onDevice'))+'</span>';
}
function escHtml(s){ return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function uiEsc(s){ return escHtml(s); }

HUB.crypto={encryptText,decryptText,textOf,peek,locked,available,lockHTML,isEncShape};
})();
