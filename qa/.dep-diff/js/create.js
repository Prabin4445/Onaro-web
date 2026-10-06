/* HUB quick-create: central floating button + bottom-sheet with 9 actions.
   Routes to each domain's own post flow (DOM-triggered, zero edits to view files),
   or uses its own sheet writing straight to the store for bills/chores/events. */
(function(){
'use strict';
const {store,ui}=HUB;

function injectStyle(){
  if(document.getElementById('createFabStyle')) return;
  const s=document.createElement('style'); s.id='createFabStyle';
  s.textContent=
    /* central clay Create button — volt 3D clay "+", squish-on-press with spring release */
    '.createfab{position:fixed;bottom:calc(20px + env(safe-area-inset-bottom));left:50%;transform:translateX(-50%);'+
    'width:60px;height:60px;border-radius:50%;border:0;cursor:pointer;z-index:35;'+
    'font-size:30px;font-weight:300;line-height:1;color:#131A00;'+
    'background:radial-gradient(circle at 32% 28%,#EAF79A 0%,#C6F135 42%,#93B41B 68%,#5E7A00 100%);'+
    'box-shadow:inset 0 3px 6px rgba(255,255,255,.55),inset 0 -5px 10px rgba(94,122,0,.45),0 12px 28px rgba(198,241,53,.45);'+
    'transition:transform .45s cubic-bezier(.32,.72,0,1),box-shadow .2s}'+
    '.createfab:active{transform:translateX(-50%) scale(.9);'+
    'box-shadow:inset 0 3px 6px rgba(255,255,255,.55),inset 0 -5px 10px rgba(94,122,0,.45),0 5px 14px rgba(198,241,53,.4)}'+
    'body.dark .createfab{box-shadow:inset 0 3px 6px rgba(255,255,255,.4),inset 0 -5px 10px rgba(0,0,0,.5)}'+
    '.cgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:8px}'+
    '.caction{border:1px solid var(--line);background:var(--surface);border-radius:16px;padding:14px 4px;min-height:96px;'+
    'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;'+
    'font-family:var(--font);font-size:12px;font-weight:700;color:var(--ink);cursor:pointer;'+
    'transition:transform .4s cubic-bezier(.32,.72,0,1),background .15s}'+
    '.caction:active{transform:scale(.94)}';
  document.head.appendChild(s);
}

function after(ms,fn){ setTimeout(fn,ms); }
function clickSel(sel,ms){
  after(ms==null?80:ms,()=>{ const b=document.querySelector(sel); if(b) b.click(); });
}
function go(tab){ HUB.showTab(tab); }
/* Keep bottom sheets and chatroot overlays mutually exclusive. */
function closeOverlays(){
  ui.closeSheet();
  ['search','pulse','notifications'].forEach(k=>{ try{ if(HUB[k]&&HUB[k].close) HUB[k].close(); }catch(e){} });
  try{ if(HUB.chat&&HUB.chat.close) HUB.chat.close(); }catch(e){}
}

/* ----- own sheets: event / expense / household task ----- */
function eventSheet(){
  closeOverlays();
  ui.openSheet(
    '<h2>'+HUB.icons.icon('act-event')+' Create event</h2>'+
    '<div class="field"><label>Emoji</label><input class="input" id="evEmoji" placeholder="📌" maxlength="4" style="width:80px"></div>'+
    '<div class="field"><label>Title *</label><input class="input" id="evTitle" placeholder="e.g. Rooftop movie night" maxlength="80"></div>'+
    '<div class="field"><label>When *</label><input class="input" id="evTime" placeholder="e.g. Today · 8:00 PM" maxlength="40"></div>'+
    '<div class="field"><label>Where</label><input class="input" id="evWhere" placeholder="e.g. Dorm courtyard" maxlength="60"></div>'+
    '<button class="btn btn-primary btn-block" id="evSave">Create event</button>'
  );
  document.getElementById('evSave').onclick=()=>{
    const title=document.getElementById('evTitle').value.trim();
    const time=document.getElementById('evTime').value.trim();
    if(!title||!time){ui.toast('Title and time are required');return;}
    store.add('events',{emoji:document.getElementById('evEmoji').value.trim()||'📌',title,time,where:document.getElementById('evWhere').value.trim()});
    ui.closeSheet(); ui.toast('Event created 🎉');
  };
}

function householdOptions(){
  return store.state.households.map(h=>'<option value="'+h.id+'">'+ui.esc(h.name)+'</option>').join('');
}
function expenseSheet(){
  closeOverlays();
  const hs=store.state.households;
  if(!hs.length){ui.toast('Create a household first');go('groups');return;}
  ui.openSheet(
    '<h2>'+HUB.icons.icon('act-expense')+' Add expense</h2>'+
    '<div class="field"><label>Household</label><select class="input" id="exHh">'+householdOptions()+'</select></div>'+
    '<div class="field"><label>What for *</label><input class="input" id="exItem" placeholder="e.g. Groceries" maxlength="60"></div>'+
    '<div class="field"><label>Amount ($) *</label><input class="input" id="exAmt" type="number" min="0" step="0.01" placeholder="e.g. 42.50"></div>'+
    '<div class="field"><label>Paid by</label><input class="input" id="exBy" value="'+ui.esc(store.myName())+'" maxlength="40"></div>'+
    '<div class="field"><label>Due</label><input class="input" id="exDue" placeholder="e.g. 15th" maxlength="20"></div>'+
    '<button class="btn btn-primary btn-block" id="exSave">Add expense</button>'+
    '<p class="hint">Split is calculated automatically — everyone sees who owes what.</p>'
  );
  document.getElementById('exSave').onclick=()=>{
    const h=store.find('households',document.getElementById('exHh').value);
    const item=document.getElementById('exItem').value.trim();
    const amount=parseFloat(document.getElementById('exAmt').value);
    if(!h||!item||!(amount>0)){ui.toast('Add a description and amount');return;}
    h.bills.unshift({id:store.uid(),item,amount:Math.round(amount*100)/100,paidBy:document.getElementById('exBy').value.trim()||store.myName(),due:document.getElementById('exDue').value.trim()||'—'});
    if(!h.members.includes(document.getElementById('exBy').value.trim())&&document.getElementById('exBy').value.trim()) h.members.push(document.getElementById('exBy').value.trim());
    store.save(); ui.closeSheet(); ui.toast('Expense added 🧾');
  };
}

function taskSheet(){
  closeOverlays();
  const hs=store.state.households;
  if(!hs.length){ui.toast('Create a household first');go('groups');return;}
  const renderMembers=()=>{
    const h=store.find('households',document.getElementById('tkHh').value);
    document.getElementById('tkWho').innerHTML=(h?h.members:[]).map(m=>'<option>'+ui.esc(m)+'</option>').join('');
  };
  ui.openSheet(
    '<h2>'+HUB.icons.icon('act-task')+' Household task</h2>'+
    '<div class="field"><label>Household</label><select class="input" id="tkHh">'+householdOptions()+'</select></div>'+
    '<div class="field"><label>Task *</label><input class="input" id="tkTask" placeholder="e.g. Mop the kitchen" maxlength="80"></div>'+
    '<div class="field"><label>Assign to</label><select class="input" id="tkWho"></select></div>'+
    '<button class="btn btn-primary btn-block" id="tkSave">Add task</button>'
  );
  document.getElementById('tkHh').onchange=renderMembers; renderMembers();
  document.getElementById('tkSave').onclick=()=>{
    const h=store.find('households',document.getElementById('tkHh').value);
    const task=document.getElementById('tkTask').value.trim();
    if(!h||!task){ui.toast('Describe the task');return;}
    h.chores.unshift({id:store.uid(),task,who:document.getElementById('tkWho').value||h.members[0],done:false});
    store.save(); ui.closeSheet(); ui.toast('Task added 🧹');
  };
}

/* ----- the sheet ----- */
const ACTIONS=[
  {i:'act-sell',t:'Sell',fn(){go('market');clickSel('#mkPostBtn',120);after(420,()=>{const c=document.querySelector('#mkTypeChips .chip[data-t="SELL"]');if(c)c.click();});}},
  {i:'act-buy',t:'Buy request',fn(){go('market');clickSel('#mkPostBtn',120);after(420,()=>{const c=document.querySelector('#mkTypeChips .chip[data-t="BUY"]');if(c)c.click();});}},
  {i:'act-job',t:'Post a job',fn(){go('work');clickSel('#postJobBtn',120);}},
  {i:'act-event',t:'Create event',fn(){eventSheet();}},
  {i:'act-group',t:'Create group',fn(){go('groups');clickSel('#newHh',120);}},
  {i:'act-memory',t:'Add memory',fn(){go('me');after(150,()=>{const t=document.querySelector('#memTitle');if(t){t.scrollIntoView({block:'center'});t.focus();}});}},
  {i:'act-expense',t:'Add expense',fn(){expenseSheet();}},
  {i:'act-task',t:'Household task',fn(){taskSheet();}},
  {i:'act-post',t:'Community post',fn(){go('groups');after(120,()=>{const s=document.querySelector('[data-sub="campus"]');if(s)s.click();});after(320,()=>{const p=document.querySelector('#campusPost');if(p)p.click();});}},
];

function open(){
  closeOverlays();
  ui.openSheet(
    '<h2>Create</h2><p class="sub" style="margin-bottom:6px">What do you want to add to your Orbit?</p>'+
    '<div class="cgrid">'+ACTIONS.map((a,i)=>'<button class="caction" data-a="'+i+'"><span class="ca">'+HUB.icons.icon(a.i)+'</span><span>'+a.t+'</span></button>').join('')+'</div>'
  );
  document.querySelectorAll('.caction').forEach(b=>{
    b.onclick=()=>{ closeOverlays(); ACTIONS[+b.dataset.a].fn(); };
  });
}

function mount(){
  injectStyle();
  if(document.getElementById('createFab')) return;
  const b=document.createElement('button');
  b.id='createFab'; b.className='createfab'; b.textContent='＋'; b.setAttribute('aria-label','Create');
  b.onclick=open;
  document.getElementById('app').appendChild(b);
}

HUB.create={open,mount};
document.addEventListener('DOMContentLoaded',mount);
})();
