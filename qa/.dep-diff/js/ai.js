/* HUB ai domain: keyword intent engine for Ask Orbit + shared answer cards.
   Honestly labeled demo assistant — reads real local store data, no AI claims. */
(function(){
'use strict';
const {store,ui}=HUB;

/* ---------- Ask Orbit (keyword-based DEMO assistant; reads real store data) ---------- */
function askAnswer(q){
  const s=q.toLowerCase();
  if(/mov/.test(s)){
    return '<h3>🚚 Moving game-plan</h3><p class="sub" style="margin:8px 0 12px">Here\'s how the pieces fit across Orbit:</p>'+
      planRow('nav-home','HOME · Household','Create a roommate group to split rent, bills & chores.','groups','Create roommate group')+
      planRow('nav-market','MARKET','Find used furniture & moving boxes nearby.','market','Find used furniture')+
      planRow('nav-work','WORK','Hire movers — open jobs like "Need someone to move furniture".','work','Hire movers')+
      planRow('act-memory','MEMORY','Store your lease so it\'s always handy.','me','Store your lease')+
      planRow('nav-groups','GROUPS · Community','Find people nearby in your community.','groups','Find people nearby')+
      planRow('nav-discover','DISCOVER','Local events to explore your new area.','discover','Local events');
  }
  if(/money|owe|bill/.test(s)){
    const o=store.householdOwed();
    let bills=store.state.households.flatMap(h=>h.bills.map(b=>({h:h.name,b})));
    let html='<h3>'+HUB.icons.icon('stat-money')+' Money snapshot</h3><div style="margin:8px 0 12px"><span class="money pos">'+ui.fmt$(o.owedToMe)+'</span> <span class="sub">owed to you</span></div>';
    if(!bills.length) html+='<p class="sub">No bills tracked yet. Create a household in GROUPS to split costs.</p>';
    else html+='<div>'+bills.slice(0,6).map(x=>'<div class="kv"><span>'+ui.esc(x.b.item)+' <span class="sub">· '+ui.esc(x.h)+'</span></span><span>'+ui.fmt$(x.b.amount)+'</span></div>').join('')+(bills.length>6?'<p class="sub" style="margin-top:6px">+'+(bills.length-6)+' more in GROUPS</p>':'')+'</div>';
    html+='<button class="btn btn-ghost btn-sm" data-goto="groups" style="margin-top:12px">Open households →</button>';
    return html;
  }
  if(/job/.test(s)){
    const open=store.state.jobs.filter(j=>j.status==='open');
    let html='<h3>'+HUB.icons.icon('nav-work')+' Open jobs</h3>';
    if(!open.length) html+='<p class="sub" style="margin-top:8px">No open jobs right now. Post one in WORK.</p>';
    else html+='<div style="margin-top:8px">'+open.slice(0,5).map(j=>'<div class="kv"><span>'+ui.esc(j.title)+' '+ui.sampleBadge(j.sample)+'</span><span class="money">'+ui.fmt$(j.pay)+'</span></div>').join('')+'</div>';
    html+='<button class="btn btn-ghost btn-sm" data-goto="work" style="margin-top:12px">See all jobs →</button>';
    return html;
  }
  if(/sell/.test(s)){
    return '<h3>'+HUB.icons.icon('act-sell')+' How to post</h3><p class="sub" style="margin:8px 0 12px">List anything in under a minute: pick SELL, BUY, SWAP, BORROW or FREE, add a title, price and your community. Chats open right from each listing.</p>'+
      '<button class="btn btn-primary btn-sm" data-goto="market">Post in MARKET →</button>';
  }
  if(/roommate|rent/.test(s)){
    const hs=store.state.households;
    let html='<h3>'+HUB.icons.icon('nav-groups')+' Households</h3>';
    if(!hs.length) html+='<p class="sub" style="margin-top:8px">No household yet. Create one in GROUPS to split rent, bills, chores and groceries.</p>';
    else html+=hs.map(h=>'<div style="margin-top:10px"><strong>'+ui.esc(h.name)+'</strong> '+ui.sampleBadge(h.sample)+'<div class="meta sub">'+h.members.map(ui.esc).join(' · ')+'</div>'+
      h.bills.map(b=>'<div class="kv"><span>'+ui.esc(b.item)+'</span><span>'+ui.fmt$(b.amount)+' <span class="sub">by '+ui.esc(b.paidBy)+'</span></span></div>').join('')+'</div>').join('');
    html+='<button class="btn btn-ghost btn-sm" data-goto="groups" style="margin-top:12px">Open GROUPS →</button>';
    return html;
  }
  if(/desk|textbook|bike|monitor|furniture|couch|lamp|buy|swap|borrow/.test(s)){
    const ls=store.state.listings.filter(l=>!ui.isBlocked(l.seller));
    let html='<h3>'+HUB.icons.icon('nav-market')+' Nearby listings</h3>';
    if(!ls.length) html+='<p class="sub" style="margin-top:8px">Nothing listed yet — be the first to post in MARKET.</p>';
    else html+='<div style="margin-top:8px">'+ls.slice(0,5).map(l=>'<div class="kv"><span>'+ui.esc(l.title)+' '+ui.sampleBadge(l.sample)+'</span><span class="money">'+(l.type==='SELL'&&l.price?ui.fmt$(l.price):ui.esc(l.type))+'</span></div>').join('')+'</div>';
    html+='<button class="btn btn-primary btn-sm" data-goto="market" style="margin-top:12px">Browse MARKET →</button>';
    return html;
  }
  return '<h3>'+HUB.icons.icon('ask-hub')+' Hi, I\'m the demo assistant</h3><p class="sub" style="margin-top:8px">I can answer from your real Orbit data — try <b>moving</b>, <b>money</b>, <b>jobs</b>, <b>sell</b>, or <b>roommate</b>.</p>';
}

function planRow(icon,title,desc,tab,cta){
  return '<div class="item"><div class="grow"><h3>'+HUB.icons.icon(icon)+' '+ui.esc(title)+'</h3><div class="meta">'+ui.esc(desc)+'</div></div>'+
    '<button class="btn btn-ghost btn-sm" data-goto="'+tab+'">'+ui.esc(cta)+'</button></div>';
}

function bindGotos(root){
  root.querySelectorAll('[data-goto]').forEach(el=>{
    el.onclick=()=>HUB.showTab(el.dataset.goto);
  });
}


HUB.ai={
  answer:function(q){ return askAnswer(q); },
  bindGotos:bindGotos,
  parseIntent:function(q){
    const s=String(q||'').toLowerCase();
    if(/mov/.test(s)) return 'moving';
    if(/money|owe|bill/.test(s)) return 'money';
    if(/job/.test(s)) return 'jobs';
    if(/sell/.test(s)) return 'sell';
    if(/roommate|rent/.test(s)) return 'roommate';
    if(/desk|textbook|bike|monitor|furniture|couch|lamp|buy|swap|borrow/.test(s)) return 'market';
    return 'default';
  }
};
})();
