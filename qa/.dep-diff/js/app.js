/* HUB app shell: tab router, onboarding, global wiring. */
(function(){
'use strict';
const {store,ui}=HUB;
HUB.views=HUB.views||{};

function applyTheme(){ document.body.classList.toggle('dark',!!store.state.prefs.dark); }

function showTab(name){
  /* chatroot overlays (search/pulse/notifications/chat) and bottom sheets are
     mutually exclusive with tabs — a tab switch always clears them so an
     overlay can never cover the newly shown tab. */
  try{ ui.closeSheet(); }catch(e){}
  ['search','pulse','notifications'].forEach(k=>{ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
  try{ if(HUB.chat&&HUB.chat.close) HUB.chat.close(); }catch(e){}
  document.querySelectorAll('#tabbar .tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));
  document.querySelectorAll('.view').forEach(v=>{ v.hidden = v.dataset.view!==name; });
  const el=document.getElementById('view-'+name);
  const view=HUB.views[name];
  if(view&&view.render){ try{ view.render(el); }catch(e){ console.error('render',name,e); el.innerHTML='<div class="empty"><div class="big">😕</div><p>Something went wrong loading this tab.</p></div>'; } }
  document.getElementById('views').scrollTop=0;
  refreshDots();
}
HUB.showTab=showTab;

function refreshDots(){
  if(HUB.chat) HUB.chat.refreshDot();
  const nd=document.getElementById('notifDot');
  if(nd&&HUB.notifications){ try{ nd.hidden = !(HUB.notifications.unreadCount()>0); }catch(e){} }
}
HUB.refreshDots=refreshDots;

/* ---------- 2026 chrome: 3D tab icons, header icons, Ask Orbit pill ---------- */
function paintChrome(){
  if(!HUB.icons) return;
  document.querySelectorAll('#tabbar .tab').forEach(b=>{
    const n=b.dataset.icon, s=b.querySelector('.tab-ico');
    if(n&&s) s.innerHTML=HUB.icons.icon(n);
  });
  const hdr={searchBtn:'ic-search',pulseBtn:'ic-pulse',notifBtn:'ic-bell',chatFab:'ic-chat'};
  Object.keys(hdr).forEach(id=>{
    const b=document.getElementById(id); if(!b) return;
    const dot=b.querySelector('.dot'); // preserved for refreshDots()
    b.innerHTML=HUB.icons.icon(hdr[id])+(dot?dot.outerHTML:'');
  });
  const pi=document.getElementById('askPillIco');
  if(pi) pi.innerHTML=HUB.icons.icon('ask-hub');
}

const ASK_CHIPS=['Split this bill','Find a desk under $100','Jobs this weekend','Moving help'];

/* Ask Orbit bottom sheet — reuses the ai domain (HUB.ai.answer / bindGotos).
   Quiet global entry: a pill above the tab bar, never a new page. */
function openAskSheet(prefill){
  ui.openSheet(
    '<div class="askhead">'+HUB.icons.icon('ask-hub')+'<h2>Ask Orbit</h2><span class="badge b-BUY">Demo assistant</span></div>'+
    '<p class="sub" style="margin:6px 0 4px">Keyword-based demo helper — answers read from your real Orbit data. Quiet and optional; everything stays in this browser.</p>'+
    '<div class="chips askchips">'+ASK_CHIPS.map(c=>'<button class="chip askchip" data-q="'+ui.esc(c)+'">'+ui.esc(c)+'</button>').join('')+'</div>'+
    '<div class="askbox"><input class="input" id="askSheetInput" placeholder="Try: moving, money, jobs…" value="'+ui.esc(prefill||'')+'"><button class="btn btn-dark btn-sm" id="askSheetSend">Send</button></div>'+
    '<div id="askSheetResults"></div>'
  );
  const input=document.getElementById('askSheetInput'), results=document.getElementById('askSheetResults');
  const run=()=>{
    const q=input.value.trim();
    if(!q){ ui.toast('Type a question first'); return; }
    const card=document.createElement('div');
    card.className='card tight'; card.style.marginTop='12px';
    card.innerHTML='<div class="sub" style="margin-bottom:8px">You asked: <b>'+ui.esc(q)+'</b></div>'+HUB.ai.answer(q);
    HUB.ai.bindGotos(card);
    results.prepend(card);
    input.value='';
  };
  document.getElementById('askSheetSend').onclick=run;
  input.addEventListener('keydown',e=>{ if(e.key==='Enter') run(); });
  document.querySelectorAll('.askchip').forEach(c=>{
    c.onclick=()=>{ input.value=c.dataset.q; input.focus(); };
  });
  if(prefill) input.focus();
}
HUB.askHUB={open:openAskSheet};

function mountAskPill(){
  const pill=document.getElementById('askPill'); if(!pill) return;
  try{ if(sessionStorage.getItem('hub_askpill_off')) return; }catch(e){}
  pill.hidden=false;
  document.getElementById('askPillMain').onclick=()=>openAskSheet('');
  document.getElementById('askPillX').onclick=()=>{
    try{ sessionStorage.setItem('hub_askpill_off','1'); }catch(e){}
    pill.hidden=true;
  };
}

/* ---------- first-run onboarding (Workstream C: Campus → Communities) ----------
   One question — "Are you a student or a community member?" — then a
   community picker. Students pick a campus; everyone else picks a
   neighborhood / apartment complex / city area / workplace community.
   If a choice already exists from a prior run, never force re-onboarding
   (ME keeps a "change community" picker). Local-only, demo-labeled. */
function ensureOnboarded(){
  const p=store.state.profile;
  if(p.name&&p.campus) return;
  let audience=''; // 'student' | 'community'
  function stepRole(){
    ui.openSheet(
      '<h2>Welcome to Orbit 🎉</h2><p class="sub" style="margin-bottom:6px">Your real-life youth network. Everything stays in this browser.</p>'+
      '<p style="font-weight:800;font-size:16px;margin:14px 0 4px">Are you a student or a community member?</p>'+
      '<div class="ob-roles">'+
        '<button class="ob-role" id="obStudent"><span class="ob-emoji">🎓</span><span class="ob-t">Student</span><span class="ob-d">Pick your campus — the radar finds food, events &amp; gigs around it.</span></button>'+
        '<button class="ob-role" id="obCommunity"><span class="ob-emoji">🏘️</span><span class="ob-t">Community member</span><span class="ob-d">Pick your neighborhood, apartment complex, or city area.</span></button>'+
      '</div>'+
      '<p class="hint" style="text-align:center">Demo preview — no account server yet. Verification lives in ME.</p>'
    );
    document.getElementById('obStudent').onclick=()=>{audience='student';stepPick();};
    document.getElementById('obCommunity').onclick=()=>{audience='community';stepPick();};
  }
  function stepPick(){
    const isStudent=audience==='student';
    ui.openSheet(
      '<button class="ob-back" id="obBack">← Back</button>'+
      '<h2>'+(isStudent?'🎓 Pick your campus':'🏘️ Pick your community')+'</h2>'+
      '<p class="sub" style="margin-bottom:14px">Students pick a campus; everyone else picks a neighborhood, apartment complex, city area, or workplace community.</p>'+
      '<div class="field"><label>Your name</label><input class="input" id="obName" placeholder="e.g. Prabin" value="'+ui.esc(p.name||'')+'"></div>'+
      '<div class="field"><label>'+(isStudent?'Campus':'Community')+'</label><select class="input" id="obCommunityPick"><option value="">Choose…</option>'+ui.communityOptions(p.campus)+'</select>'+
      '<p class="hint">Sample communities — real communities go live with the production backend.</p></div>'+
      '<button class="btn btn-primary btn-block" id="obGo">Get started →</button>'
    );
    document.getElementById('obBack').onclick=stepRole;
    document.getElementById('obGo').onclick=()=>{
      const name=document.getElementById('obName').value.trim();
      const community=document.getElementById('obCommunityPick').value;
      if(!name){ui.toast('Please enter your name');return;}
      if(!community){ui.toast('Please choose your '+(isStudent?'campus':'community'));return;}
      p.name=name;p.campus=community;p.audience=audience;store.save();
      ui.closeSheet();showTab('home');
      ui.toast('Welcome to Orbit, '+name+'! 🎉');
    };
  }
  stepRole();
}

document.addEventListener('DOMContentLoaded',()=>{
  applyTheme();
  /* Freeze the logo satellite animation for reduced-motion users (SMIL ignores CSS animation-duration). */
  try{
    if(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches){
      document.querySelectorAll('.brand-mark svg').forEach(s=>s.pauseAnimations());
    }
  }catch(e){}
  paintChrome();
  mountAskPill();
  document.getElementById('tabbar').addEventListener('click',e=>{
    const b=e.target.closest('.tab'); if(b) showTab(b.dataset.tab);
  });
  document.getElementById('chatFab').onclick=()=>{ if(HUB.chat) HUB.chat.openList(); };
  document.getElementById('searchBtn').onclick=()=>{ if(HUB.search) HUB.search.open(); };
  document.getElementById('pulseBtn').onclick=()=>{ if(HUB.pulse) HUB.pulse.open(); };
  document.getElementById('notifBtn').onclick=()=>{ if(HUB.notifications){ HUB.notifications.open(); setTimeout(refreshDots,600); } };
  document.addEventListener('keydown',e=>{ if(e.key==='Escape'){ ui.closeSheet(); if(HUB.chat) HUB.chat.close(); } });
  ensureOnboarded();
  showTab('home');
});
HUB.applyTheme=applyTheme;
})();
