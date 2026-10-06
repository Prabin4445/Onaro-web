/* HUB GROUPS tab: Households (Roommate OS) + Communities.
   Sub-tab state and open-household state live in module vars so
   render() stays idempotent. All user data escaped. Seeds flagged. */
(function(){
'use strict';
const {store,ui}=HUB;
HUB.views=HUB.views||{};

let sub='households';   // 'households' | 'campus' ('campus' = Communities view; key kept as internal identifier)
let openHh=null;        // household id in detail view, or null

function rerender(){ const el=document.getElementById('view-groups'); if(el) HUB.views.groups.render(el); }

function fmtShare(n){ return ui.fmt$(Math.round(n*100)/100); }
function oweName(n){ return n===store.myName()?'you':n; }

/* ---------- aggregated balances for a household ----------
   Per bill: share = amount / members; every member except paidBy
   owes share to paidBy. Aggregate pairwise. */
function balances(h){
  const n=h.members.length||1, agg={};
  for(const b of h.bills){
    const amt=Number(b.amount)||0; if(amt<=0) continue;
    const share=amt/n;
    for(const m of h.members){
      if(m===b.paidBy) continue;
      const k=m+'\u0000'+b.paidBy;
      agg[k]=(agg[k]||0)+share;
    }
  }
  return Object.keys(agg).map(k=>{
    const [from,to]=k.split('\u0000');
    return {from,to,amt:Math.round(agg[k]*100)/100};
  }).filter(r=>r.amt>0.004);
}

/* ================= HOUSEHOLDS LIST ================= */
function renderHouseholdsList(el){
  const hs=store.state.households;
  let html='<h1 class="greet">Groups</h1><p class="sub" style="margin:4px 0 12px">Split bills, chores & life with the people you live with.</p>';
  html+='<div class="seg"><button class="on">🏠 Households</button><button data-sub="campus">🏘️ Communities</button><button data-sub="people">👤 People</button></div>';
  html+='<button class="btn btn-ghost btn-block" id="newHh">＋ New household</button><div style="height:12px"></div>';
  if(!hs.length){
    html+='<div class="empty"><div class="big">🏠</div><p>No households yet. Start one with your roommates!</p></div>';
  }
  for(const h of hs){
    const tot=h.bills.reduce((a,b)=>a+(Number(b.amount)||0),0);
    const bal=balances(h).filter(r=>r.to===store.myName());
    const owedIn=bal.reduce((a,r)=>a+r.amt,0);
    const openChores=h.chores.filter(c=>!c.done).length;
    html+='<div class="card tight hh-card" data-hh="'+h.id+'" style="cursor:pointer">'
      +'<div class="row between"><h3>'+ui.esc(h.name)+'</h3>'+ui.sampleBadge(h.sample)+'</div>'
      +'<div class="meta" style="margin-top:4px">'+ui.esc(h.members.join(' · '))+'</div>'
      +'<div class="row between" style="margin-top:10px"><span class="sub">'+h.bills.length+' bill'+(h.bills.length===1?'':'s')+' · '+openChores+' chore'+(openChores===1?'':'s')+' open</span>'
      +'<span class="money '+(owedIn>0?'pos':'')+'" style="font-size:16px">'+(owedIn>0?('💸 '+ui.fmt$(owedIn)+' owed to you'):ui.fmt$(tot)+' total')+'</span></div>'
      +'</div>';
  }
  el.innerHTML=html;
  el.querySelector('[data-sub="campus"]').onclick=()=>{sub='campus';rerender();};
  el.querySelector('[data-sub="people"]').onclick=()=>{sub='people';rerender();};
  el.querySelector('#newHh').onclick=newHouseholdSheet;
  el.querySelectorAll('.hh-card').forEach(c=>{ c.onclick=()=>{ openHh=c.dataset.hh; rerender(); }; });
}

function newHouseholdSheet(){
  const me=store.myName();
  ui.openSheet(
    '<h2>＋ New household</h2>'
    +'<div class="field"><label>Household name</label><input class="input" id="nhName" placeholder="e.g. Apartment 204"></div>'
    +'<div class="field"><label>Members (comma separated — you are added automatically)</label><input class="input" id="nhMembers" placeholder="Alex, Maya" value="'+ui.esc(me)+'"></div>'
    +'<button class="btn btn-primary btn-block" id="nhSave">Create household</button>'
  );
  document.getElementById('nhSave').onclick=()=>{
    const name=document.getElementById('nhName').value.trim();
    if(!name){ui.toast('Give your household a name');return;}
    const raw=document.getElementById('nhMembers').value.split(',').map(s=>s.trim()).filter(Boolean);
    const seen=new Set(), members=[];
    for(const m of raw){ if(!seen.has(m.toLowerCase())){seen.add(m.toLowerCase());members.push(m);} }
    if(!members.some(m=>m===me)) members.unshift(me);
    store.state.households.unshift({id:store.uid(),name,members,bills:[],chores:[],shopping:[],notes:[],polls:[],sample:false});
    store.save(); ui.closeSheet(); openHh=store.state.households[0].id; sub='households'; rerender();
    ui.toast('Household created 🏠');
  };
}

/* ================= HOUSEHOLD DETAIL ================= */
function renderHouseholdDetail(el, h){
  const me=store.myName();
  let html='<button class="linklike" id="hhBack" style="margin-bottom:10px">← Back to households</button>';
  html+='<h1 class="greet">'+ui.esc(h.name)+' '+ui.sampleBadge(h.sample)+'</h1>'
    +'<p class="sub" style="margin:4px 0 14px">'+ui.esc(h.members.join(' · '))+'</p>';

  /* ---- Bills ---- */
  html+='<div class="card"><div class="row between"><h2>🧾 Bills</h2><button class="btn btn-sm btn-ghost" id="addBill">＋ Add bill</button></div>';
  if(!h.bills.length){ html+='<p class="sub" style="margin-top:8px">No bills yet — add the first one.</p>'; }
  else{
    for(const b of h.bills){
      const n=h.members.length||1, share=b.amount/n;
      html+='<div class="kv"><div><div style="font-weight:700">'+ui.esc(b.item)+'</div>'
        +'<div class="sub" style="font-size:12px">paid by '+ui.esc(oweName(b.paidBy))+' · due '+ui.esc(b.due||'—')+' · share '+fmtShare(share)+'</div></div>'
        +'<div class="money" style="font-size:16px">'+fmtShare(Number(b.amount)||0)+'</div></div>';
    }
  }
  const bal=balances(h);
  html+='<div class="divider"></div><h3 style="margin-bottom:6px">💸 Balances</h3>';
  if(!bal.length) html+='<p class="sub">All settled up. 🎉</p>';
  else for(const r of bal) html+='<div class="kv"><span>'+ui.esc(oweName(r.from))+' owes '+ui.esc(oweName(r.to))+'</span><span class="money" style="font-size:15px;color:var(--amber)">'+fmtShare(r.amt)+'</span></div>';
  html+='</div>';

  /* ---- Chores ---- */
  html+='<div class="card"><div class="row between"><h2>🧹 Chores</h2><button class="btn btn-sm btn-ghost" id="addChore">＋ Add</button></div><div style="margin-top:8px">';
  if(!h.chores.length) html+='<p class="sub">No chores yet.</p>';
  for(const c of h.chores){
    html+='<div class="item tight chore" data-cid="'+c.id+'" style="cursor:pointer;margin-bottom:8px;padding:10px 12px">'
      +'<span style="font-size:20px">'+(c.done?'✅':'⬜')+'</span>'
      +'<div class="grow"><h3 style="'+(c.done?'text-decoration:line-through;color:var(--faint)':'')+'">'+ui.esc(c.task)+'</h3>'
      +'<div class="meta">'+ui.esc(c.who||'anyone')+'</div></div></div>';
  }
  html+='</div></div>';

  /* ---- Shopping ---- */
  const bought=h.shopping.filter(s=>s.done).length;
  html+='<div class="card"><div class="row between"><h2>🛒 Shopping</h2><div class="row" style="gap:6px"><button class="btn btn-sm btn-line" id="clearBought">Clear bought</button><button class="btn btn-sm btn-ghost" id="addShop">＋ Add</button></div></div><div style="margin-top:8px">';
  if(!h.shopping.length) html+='<p class="sub">List is empty.</p>';
  for(const s of h.shopping){
    html+='<div class="item tight shop" data-sid="'+s.id+'" style="cursor:pointer;margin-bottom:8px;padding:10px 12px">'
      +'<span style="font-size:20px">'+(s.done?'✅':'⬜')+'</span>'
      +'<div class="grow"><h3 style="'+(s.done?'text-decoration:line-through;color:var(--faint)':'')+'">'+ui.esc(s.item)+'</h3></div></div>';
  }
  if(bought) html+='<p class="hint">'+bought+' bought ✓</p>';
  html+='</div></div>';

  /* ---- Announcements ---- */
  html+='<div class="card"><h2 style="margin-bottom:8px">📣 Announcements</h2>'
    +'<div class="askbox"><input class="input" id="noteText" placeholder="Note for the house…"><button class="btn btn-primary btn-sm" id="notePost">Post</button></div><div style="margin-top:10px">';
  if(!h.notes.length) html+='<p class="sub">Nothing posted yet.</p>';
  const notes=[...h.notes].sort((a,b)=>(b.at||0)-(a.at||0));
  for(const n of notes) html+='<div class="item tight" style="padding:10px 12px;margin-bottom:8px"><div class="grow"><div style="font-size:14px">'+ui.esc(n.text)+'</div><div class="meta">'+ui.timeAgo(n.at||Date.now())+'</div></div></div>';
  html+='</div></div>';

  /* ---- Polls ---- */
  html+='<div class="card"><div class="row between"><h2>🗳️ Polls</h2><button class="btn btn-sm btn-ghost" id="addPoll">＋ New poll</button></div><div style="margin-top:10px">';
  if(!h.polls.length) html+='<p class="sub">No polls yet — start a roommate vote!</p>';
  for(const p of h.polls){
    const total=p.opts.reduce((a,o)=>a+(o.v||0),0);
    html+='<div style="margin-bottom:14px"><div class="row between"><strong style="font-size:15px">'+ui.esc(p.q)+'</strong>'+ui.sampleBadge(p.sample)+'</div>';
    p.opts.forEach((o,i)=>{
      const pct=total?Math.round(o.v/total*100):0;
      if(p.voted){
        html+='<div style="margin-top:6px"><div class="row between"><span style="font-size:13.5px">'+ui.esc(o.t)+'</span><span class="meta">'+o.v+' · '+pct+'%</span></div><div class="pollbar"><i style="width:'+pct+'%"></i></div></div>';
      }else{
        html+='<button class="btn btn-line btn-sm btn-block vote" data-pid="'+p.id+'" data-oi="'+i+'" style="margin-top:6px">'+ui.esc(o.t)+'</button>';
      }
    });
    if(p.voted) html+='<p class="hint">You voted · '+total+' vote'+(total===1?'':'s')+'</p>';
    html+='</div>';
  }
  html+='</div></div>';

  el.innerHTML=html;
  document.getElementById('hhBack').onclick=()=>{openHh=null;rerender();};

  /* bills */
  document.getElementById('addBill').onclick=()=>{
    const opts=h.members.map(m=>'<option'+(m===me?' selected':'')+'>'+ui.esc(m)+'</option>').join('');
    ui.openSheet(
      '<h2>＋ Add bill</h2>'
      +'<div class="field"><label>Item</label><input class="input" id="bItem" placeholder="Rent, electricity…"></div>'
      +'<div class="field"><label>Amount ($)</label><input class="input" id="bAmt" type="number" min="0.01" step="0.01" inputmode="decimal" placeholder="0.00"></div>'
      +'<div class="field"><label>Paid by</label><select class="input" id="bBy">'+opts+'</select></div>'
      +'<div class="field"><label>Due</label><input class="input" id="bDue" placeholder="e.g. 1st, Fri, —"></div>'
      +'<button class="btn btn-primary btn-block" id="bSave">Add bill</button>'
    );
    document.getElementById('bSave').onclick=()=>{
      const item=document.getElementById('bItem').value.trim();
      const amount=parseFloat(document.getElementById('bAmt').value);
      if(!item){ui.toast('Name the bill');return;}
      if(!(amount>0)){ui.toast('Enter a valid amount');return;}
      h.bills.push({id:store.uid(),item,amount:Math.round(amount*100)/100,paidBy:document.getElementById('bBy').value,due:document.getElementById('bDue').value.trim()||'—'});
      store.save(); ui.closeSheet(); rerender(); ui.toast('Bill added 🧾');
    };
  };

  /* chores */
  document.getElementById('addChore').onclick=()=>{
    const opts=h.members.map(m=>'<option'+(m===me?' selected':'')+'>'+ui.esc(m)+'</option>').join('');
    ui.openSheet(
      '<h2>＋ Add chore</h2>'
      +'<div class="field"><label>Task</label><input class="input" id="cTask" placeholder="e.g. Mop the kitchen"></div>'
      +'<div class="field"><label>Who</label><select class="input" id="cWho">'+opts+'</select></div>'
      +'<button class="btn btn-primary btn-block" id="cSave">Add chore</button>'
    );
    document.getElementById('cSave').onclick=()=>{
      const task=document.getElementById('cTask').value.trim();
      if(!task){ui.toast('Describe the chore');return;}
      h.chores.push({id:store.uid(),task,who:document.getElementById('cWho').value,done:false});
      store.save(); ui.closeSheet(); rerender(); ui.toast('Chore added 🧹');
    };
  };
  el.querySelectorAll('.chore').forEach(c=>{ c.onclick=()=>{ const x=h.chores.find(z=>z.id===c.dataset.cid); if(x){x.done=!x.done;store.save();rerender();} }; });

  /* shopping */
  document.getElementById('addShop').onclick=()=>{
    ui.openSheet('<h2>＋ Add to shopping list</h2><div class="field"><label>Item</label><input class="input" id="sItem" placeholder="e.g. Oat milk"></div><button class="btn btn-primary btn-block" id="sSave">Add item</button>');
    document.getElementById('sSave').onclick=()=>{
      const item=document.getElementById('sItem').value.trim();
      if(!item){ui.toast('Name the item');return;}
      h.shopping.push({id:store.uid(),item,done:false});
      store.save(); ui.closeSheet(); rerender(); ui.toast('Added 🛒');
    };
  };
  el.querySelectorAll('.shop').forEach(c=>{ c.onclick=()=>{ const x=h.shopping.find(z=>z.id===c.dataset.sid); if(x){x.done=!x.done;store.save();rerender();} }; });
  document.getElementById('clearBought').onclick=()=>{ h.shopping=h.shopping.filter(s=>!s.done); store.save(); rerender(); ui.toast('Bought items cleared'); };

  /* notes */
  document.getElementById('notePost').onclick=()=>{
    const t=document.getElementById('noteText').value.trim();
    if(!t){ui.toast('Write something first');return;}
    h.notes.push({id:store.uid(),text:t,at:Date.now()});
    store.save(); rerender(); ui.toast('Posted 📣');
  };

  /* polls */
  document.getElementById('addPoll').onclick=()=>{
    ui.openSheet(
      '<h2>＋ New poll</h2>'
      +'<div class="field"><label>Question</label><input class="input" id="pQ" placeholder="Movie night Friday?"></div>'
      +'<div class="field"><label>Options (one per line, 2–4)</label><textarea class="textarea" id="pOpts" placeholder="Yes 🍿&#10;Saturday instead"></textarea></div>'
      +'<button class="btn btn-primary btn-block" id="pSave">Create poll</button>'
    );
    document.getElementById('pSave').onclick=()=>{
      const q=document.getElementById('pQ').value.trim();
      const opts=document.getElementById('pOpts').value.split('\n').map(s=>s.trim()).filter(Boolean).slice(0,4);
      if(!q){ui.toast('Add a question');return;}
      if(opts.length<2){ui.toast('Add at least 2 options');return;}
      h.polls.unshift({id:store.uid(),q,opts:opts.map(t=>({t,v:0})),voted:false});
      store.save(); ui.closeSheet(); rerender(); ui.toast('Poll live 🗳️');
    };
  };
  el.querySelectorAll('.vote').forEach(b=>{ b.onclick=()=>{ const p=h.polls.find(z=>z.id===b.dataset.pid); if(p&&!p.voted){ p.opts[Number(b.dataset.oi)].v+=1; p.voted=true; store.save(); rerender(); ui.toast('Vote counted ✓'); } }; });
}

/* ================= COMMUNITIES ================= */
function renderCampus(el){
  const s=store.state, me=store.myName();
  const opts=ui.communityOptions(s.profile.campus);
  let html='<h1 class="greet">Groups</h1><p class="sub" style="margin:4px 0 12px">What\'s happening around your community today.</p>';
  html+='<div class="seg"><button data-sub="households">🏠 Households</button><button class="on">🏘️ Communities</button><button data-sub="people">👤 People</button></div>';

  html+='<div class="card tight"><div class="row between"><div><div class="sub" style="font-size:12px">YOUR COMMUNITY</div><h2>'+ui.esc(s.profile.campus||'—')+'</h2></div>'
    +'<select class="input" id="campusPick" style="width:auto;max-width:170px" aria-label="Change community">'+opts+'</select></div>'
    +'<p class="hint" style="margin:8px 0 0">Sample communities — real communities go live with the production backend.</p></div>';

  html+='<button class="btn btn-primary btn-block" id="campusPost">＋ Post to community</button><div style="height:12px"></div>';

  /* marketplace cross-link */
  const nList=s.listings.length;
  html+='<button class="btn btn-line btn-block" id="goMarket" style="margin-bottom:14px">📚 '+nList+' marketplace item'+(nList===1?'':'s')+' →</button>';

  html+='<h2 style="margin-bottom:10px">TODAY</h2>';
  for(const e of s.events){
    html+='<div class="item"><div class="avatar" style="background:var(--surface2);color:var(--ink)">'+ui.esc(e.emoji)+'</div>'
      +'<div class="grow"><h3>'+ui.esc(e.title)+'</h3><div class="meta">'+ui.esc(e.time)+' · '+ui.esc(e.where)+'</div></div>'+ui.sampleBadge(e.sample)+'</div>';
  }
  const posts=[...s.campusPosts].filter(p=>!ui.isBlocked(p.author)).sort((a,b)=>(b.at||0)-(a.at||0));
  for(const p of posts){
    html+='<div class="item"><div class="avatar">'+ui.initials(p.author)+'</div>'
      +'<div class="grow"><h3>'+ui.esc(p.author)+' <span class="meta">· '+ui.timeAgo(p.at||Date.now())+'</span></h3>'
      +'<div style="font-size:14.5px;line-height:1.45">'+ui.esc(p.text)+'</div></div>'+ui.sampleBadge(p.sample)+'</div>';
  }
  if(!s.events.length&&!posts.length) html+='<div class="empty"><div class="big">🏘️</div><p>Quiet in your community — post something!</p></div>';

  el.innerHTML=html;
  el.querySelector('[data-sub="households"]').onclick=()=>{sub='households';rerender();};
  el.querySelector('[data-sub="people"]').onclick=()=>{sub='people';rerender();};
  document.getElementById('campusPick').onchange=e=>{ s.profile.campus=e.target.value; store.save(); rerender(); ui.toast('Community set to '+e.target.value+' 🏘️'); };
  document.getElementById('goMarket').onclick=()=>HUB.showTab('market');
  document.getElementById('campusPost').onclick=()=>{
    ui.openSheet(
      '<h2>＋ Post to community</h2>'
      +'<div class="field"><label>Emoji (optional)</label><input class="input" id="cpEmoji" maxlength="4" placeholder="💬"></div>'
      +'<div class="field"><label>What\'s up?</label><textarea class="textarea" id="cpText" placeholder="Share something with your community…"></textarea></div>'
      +'<button class="btn btn-primary btn-block" id="cpSave">Post</button>'
    );
    document.getElementById('cpSave').onclick=()=>{
      const text=document.getElementById('cpText').value.trim();
      if(!text){ui.toast('Write something first');return;}
      let emoji=document.getElementById('cpEmoji').value.trim()||'💬';
      store.add('campusPosts',{author:me,text:(emoji+' '+text).trim(),at:Date.now()});
      ui.closeSheet(); rerender(); ui.toast('Posted to your community 🏘️');
    };
  };
}

/* ================= VIEW ================= */
HUB.views.groups={ render(el){
  /* Workstream D: the People discovery surface renders here when active.
     Guarded so groups.js keeps working if people.js hasn't loaded. */
  if(sub==='people'){
    if(HUB.people&&HUB.people.renderSurface) HUB.people.renderSurface(el);
    else el.innerHTML='<div class="empty"><div class="big">👤</div><p>People is loading…</p></div>';
    return;
  }
  if(sub==='campus'){ renderCampus(el); return; }
  const h=openHh?store.state.households.find(x=>x.id===openHh):null;
  if(h) renderHouseholdDetail(el,h);
  else { if(openHh){openHh=null;} renderHouseholdsList(el); }
},
/* lets the people module (and anyone else) switch the groups sub-tab */
setSub(s){ sub=s; rerender(); }
};})();
