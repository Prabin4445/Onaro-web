/* HUB store: localStorage-backed state, sample seeds, UI helpers.
   Everything user-created is REAL local data. Seeds are flagged sample:true. */
(function(){
'use strict';
const KEY='hub_v1';
const uid=()=> 'id'+Date.now().toString(36)+Math.random().toString(36).slice(2,7);
/* ---- people-discovery seeds (Workstream D) ----
   Sample people discoverable at their community. Schema:
   {id,name,phone,campus,skills[],stars,verified,jobsDone,exchanges,
    knownFor,mutualGroups[],avatarColor,discoverable,sample} */
function seedPeople(){
  const P=(name,phone,campus,skills,stars,verified,jobsDone,exchanges,knownFor,mutualGroups,avatarColor)=>({
    id:uid(),name,phone,campus,skills,stars,verified,jobsDone,exchanges,knownFor,
    mutualGroups:mutualGroups||[],avatarColor:avatarColor||0,discoverable:true,sample:true
  });
  return [
    P('Maya Chen','+1 555-902-1173','Riverside State',['Photography','Poster design','Video editing'],4.9,true,12,8,'Campus event photos & poster design',['Apartment 204'],1),
    P('Alex Rivera','+1 555-014-2288','Riverside State',['Moving help','Furniture assembly','Driving'],4.5,true,7,5,'Fast moves & IKEA builds',['Apartment 204'],0),
    P('Jordan Lee','+1 555-773-9041','Riverside State',['Math tutoring','Physics','Study guides'],5.0,false,4,3,'MATH 201 cram sessions',[],6),
    P('Sam Ortiz','+1 555-331-8870','Riverside State',['Bike repair','Cooking','Gardening'],4.2,false,9,11,'Flat fixes & Sunday curry nights',[],4),
    P('Casey Kim','+1 555-210-4471','Riverside State',['Web design','Coding','Logo design'],4.7,true,6,4,'Landing pages in a weekend',[],2),
    P('Riley Patel','+1 555-220-4816','Riverside State',['Dog sitting','Plant care','House cleaning'],4.8,false,5,9,'Plant rescues & puppy walks',[],3),
    P('Nora Feld','+1 555-410-2290','Maplewood Apartments',['Gardening','Compost','Seed swaps'],4.6,true,3,7,'Balcony gardens & seed swaps',[],0),
    P('Omar Haddad','+1 555-410-8834','Maplewood Apartments',['Grilling','Carpentry','Tool lending'],4.9,false,8,6,'Courtyard BBQs & shelf builds',[],5),
  ];
}
const esc=s=> String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt$=n=> '$'+Number(n).toFixed(2).replace(/\.00$/,'');
const timeAgo=ts=>{const s=(Date.now()-ts)/1e3;if(s<60)return'just now';if(s<3600)return Math.floor(s/60)+'m ago';if(s<86400)return Math.floor(s/3600)+'h ago';return Math.floor(s/86400)+'d ago';};
const todayStr=()=> new Date().toISOString().slice(0,10);

function seeds(){
  const now=Date.now(), H=3600e3;
  return {
    profile:{name:'',email:'',phone:'',campus:'',audience:'',avatarColor:0,verified:false,stars:4.5,jobsDone:3,createdAt:now,sample:false,discoverable:true},
    prefs:{dark:false},
    people:seedPeople(),
    listings:[
      {id:uid(),type:'BORROW',title:'📚 Calculus textbook (Stewart, 9th ed)',price:0,borrowFor:'2 weeks',desc:'Need it for MATH 201 this semester. Will return in perfect condition!',campus:'Riverside State',seller:'Alex Rivera',phone:'+1 555-014-2288',createdAt:now-5*H,sample:true},
      {id:uid(),type:'SWAP',title:'🖥️ 24" Monitor — swap for keyboard',price:0,swapFor:'mechanical keyboard',desc:'Dell 24 inch, 1080p, works great. Looking to swap for a mechanical keyboard.',campus:'Riverside State',seller:'Maya Chen',phone:'+1 555-902-1173',createdAt:now-9*H,sample:true},
      {id:uid(),type:'SELL',title:'💡 Desk lamp with USB port',price:15,desc:'Barely used, warm light, has a USB charging port on the base.',campus:'Riverside State',seller:'Jordan Lee',phone:'+1 555-773-9041',createdAt:now-26*H,sample:true},
      {id:uid(),type:'FREE',title:'📦 Moving boxes (12) — free pickup',price:0,desc:'Sturdy boxes from my move last week. First come first served!',campus:'Riverside State',seller:'Sam Ortiz',phone:'+1 555-331-8870',createdAt:now-30*H,sample:true},
      {id:uid(),type:'FREE',title:'🪴 Cherry tomato seedlings — free',price:0,desc:'Started way too many. Porch pickup in Maplewood, bring a small pot!',campus:'Maplewood Apartments',seller:'Sam Rivera',phone:'+1 555-220-4816',createdAt:now-8*H,sample:true},
      {id:uid(),type:'SELL',title:'🚲 City commuter bike',price:120,desc:'7-speed, new brake pads. Perfect for getting around the Arts District.',campus:'Downtown Arts District',seller:'Jordan Blake',phone:'+1 555-773-2094',createdAt:now-14*H,sample:true},
    ],
    jobs:[
      {id:uid(),title:'Need someone to move furniture',pay:40,desc:'Couch + bookshelf, 2nd floor to ground. ~1 hour, Saturday morning.',poster:'Taylor Brooks',status:'open',acceptedBy:null,createdAt:now-3*H,sample:true},
      {id:uid(),title:'Need a logo designed',pay:25,desc:'Simple logo for my study-group app. Can be done remotely.',poster:'Casey Kim',status:'open',acceptedBy:null,createdAt:now-12*H,sample:true},
      {id:uid(),title:'Help assemble IKEA desk',pay:30,desc:'Malm desk, all parts ready. Need an extra pair of hands ~45 min.',poster:'Riley Patel',status:'open',acceptedBy:null,createdAt:now-20*H,sample:true},
    ],
    events:[
      {id:uid(),emoji:'🍕',title:'Free pizza — Student Union',time:'Today · 12:00 PM',where:'Student Union lobby',sample:true},
      {id:uid(),emoji:'💼',title:'Career fair',time:'Today · 3:00 PM',where:'Main gym',sample:true},
      {id:uid(),emoji:'🏀',title:'Basketball pickup game',time:'Today · 7:00 PM',where:'Rec center courts',sample:true},
      {id:uid(),emoji:'📚',title:'Study group — MATH 201',time:'Today · 8:00 PM',where:'Library room 204',sample:true},
      {id:uid(),emoji:'🎨',title:'First Friday art walk',time:'Friday · 6:00 PM',where:'Main St, Downtown Arts District',sample:true},
      {id:uid(),emoji:'🧹',title:'Maplewood block cleanup',time:'Saturday · 9:00 AM',where:'Maplewood courtyard',sample:true},
    ],
    households:[
      {id:uid(),name:'Apartment 204',members:['Prabin','Alex','Maya'],
       bills:[
         {id:uid(),item:'Rent',amount:2100,paidBy:'Prabin',due:'1st'},
         {id:uid(),item:'Electricity',amount:146,paidBy:'Alex',due:'15th'},
         {id:uid(),item:'Internet',amount:70,paidBy:'Maya',due:'10th'},
         {id:uid(),item:'Groceries',amount:238,paidBy:'Prabin',due:'—'},
       ],
       chores:[{id:uid(),task:'Take out trash',who:'Alex',done:false},{id:uid(),task:'Clean bathroom',who:'Maya',done:false},{id:uid(),task:'Vacuum living room',who:'Prabin',done:true}],
       shopping:[{id:uid(),item:'Oat milk',done:false},{id:uid(),item:'Dish soap',done:false},{id:uid(),item:'Trash bags',done:true}],
       notes:[{id:uid(),text:'Landlord visiting Friday — keep common areas clean 🙏',at:now-8*H}],
       polls:[{id:uid(),q:'Movie night Friday?',opts:[{t:'Yes 🍿',v:2},{t:'Saturday instead',v:1}],voted:false}],
       sample:true},
    ],
    campusPosts:[
      {id:uid(),author:'Priya N.',text:'Anyone selling a bike? Budget $80 🚲',at:now-2*H,sample:true},
      {id:uid(),author:'Devon A.',text:'Room available in 3BR near Riverside State from next month. DM me! 🏠',at:now-6*H,sample:true},
      {id:uid(),author:'Jordan P.',text:'Lost grey cat near Northside park — answers to Miso 🐱 please DM if seen',at:now-4*H,sample:true},
      {id:uid(),author:'Sam R.',text:'Courtyard BBQ Sunday at Maplewood 🌭 bring something to share!',at:now-13*H,sample:true},
      {id:uid(),author:'Lena K.',text:'Guitar club meeting Thursday 6 PM, music room 🎸 beginners welcome',at:now-11*H,sample:true},
    ],
    memory:[
      {id:uid(),kind:'receipt',title:'Laptop receipt — Best Buy',note:'MacBook Air, $999. Warranty 1 year.',fileName:'receipt.jpg',expiry:now+300*24*H,createdAt:now-40*24*H,sample:true},
      {id:uid(),kind:'note',title:'Internship website',note:'apply.techinterns.io — deadline Nov 15',createdAt:now-5*24*H,sample:true},
      {id:uid(),kind:'document',title:'Apartment lease 2026',note:'Lease ends Aug 2027. Deposit $800.',fileName:'lease.pdf',createdAt:now-60*24*H,sample:true},
    ],
    contacts:[
      {id:uid(),name:'Alex Rivera',phone:'+1 555-014-2288',sample:true},
      {id:uid(),name:'Maya Chen',phone:'+1 555-902-1173',sample:true},
    ],
    threads:[
      {id:uid(),contactId:null,listingId:null,title:'Alex Rivera',messages:[{from:'them',text:'Hey! Is the textbook still available?',at:now-2*H}],unread:1,sample:true},
    ],
    campuses:['Riverside State','City College','Northlake University','Westfield Tech','Maplewood Apartments','Downtown Arts District','Northside','Riverside Heights'],
  };
}

let state;
try{ state=JSON.parse(localStorage.getItem(KEY))||null; }catch(e){ state=null; }
if(!state){ state=seeds(); save(); }
if(!state.reports) state.reports=[];
if(!state.blocked) state.blocked=[];
if(state.prefs.privacyCampus==null) state.prefs.privacyCampus=true;
if(state.prefs.privacyLocation==null) state.prefs.privacyLocation=false;
/* Workstream D: people-discovery seeds + the discoverability privacy flag.
   Legacy saved profiles default to discoverable so the demo surface is alive. */
if(!Array.isArray(state.people)) state.people=seedPeople();
if(state.profile&&state.profile.discoverable==null) state.profile.discoverable=true;
function save(){ try{ localStorage.setItem(KEY,JSON.stringify(state)); }catch(e){} }

/* ---- derived helpers ---- */
function myName(){ return state.profile.name||'you'; }
function householdOwed(){ // {owedToMe, billDue}
  let owedToMe=0, billDue=null, earliest='';
  for(const h of state.households){
    const n=h.members.length||1, me=myName();
    for(const b of h.bills){
      const share=b.amount/n;
      if(b.paidBy===me) owedToMe+=(b.amount-share);
    }
    for(const b of h.bills){ if(!billDue||String(b.due)<earliest){billDue=b;earliest=String(b.due);} }
  }
  return {owedToMe:Math.max(0,Math.round(owedToMe*100)/100),billDue};
}
function unreadCount(){ return state.threads.reduce((a,t)=>a+(t.unread||0),0); }
function isBlocked(name){ return !!name && state.blocked.some(b=>b.toLowerCase()===String(name).toLowerCase()); }
function openReportCount(){ return (state.reports||[]).filter(r=>!r.resolved).length; }
function clearSamples(){
  for(const k of ['listings','jobs','events','campusPosts','memory','contacts','threads','people']) state[k]=state[k].filter(x=>!x.sample);
  state.households=state.households.filter(h=>!h.sample);
  save();
}

/* ---- ui helpers ---- */
function toast(msg){ const h=document.getElementById('toastHost'); const d=document.createElement('div'); d.className='toast'; d.textContent=msg; h.appendChild(d); setTimeout(()=>{d.style.opacity='0';d.style.transition='opacity .3s';setTimeout(()=>d.remove(),320);},2400); }
function openSheet(html){ const host=document.getElementById('sheetHost'),box=document.getElementById('sheetBox'); box.innerHTML=html; host.hidden=false; box.scrollTop=0;
  host.onclick=e=>{ if(e.target===host) closeSheet(); }; }
function closeSheet(){ document.getElementById('sheetHost').hidden=true; }
function stars(n){ const f=Math.round(n); return '★'.repeat(f)+'☆'.repeat(5-f); }
function sampleBadge(s){ return s?'<span class="badge sample">Sample</span>':''; }
function initials(name){ return (name||'?').trim().split(/\s+/).map(w=>w[0]).join('').slice(0,2).toUpperCase(); }
function greeting(){ const h=new Date().getHours(); return h<12?'Good morning':h<17?'Good afternoon':'Good evening'; }

/* ---- Communities picker (Workstream C: Campus → Communities reframe) ----
   state.campuses keeps its storage key for legacy localStorage compatibility.
   Seeds mix sample campuses + sample neighborhoods/areas; the picker groups
   them and labels each group as sample. Orphaned values (e.g. from older
   seeds) are appended so a stored choice never silently unselects. */
const CAMPUS_NAMES=['Riverside State','City College','Northlake University','Westfield Tech'];
function isCampusCommunity(name){ return CAMPUS_NAMES.indexOf(name)!==-1; }
function communityOptions(selected){
  const list=state.campuses||[];
  const opt=c=>'<option value="'+esc(c)+'"'+(c===selected?' selected':'')+'>'+esc(c)+'</option>';
  const campuses=list.filter(isCampusCommunity), areas=list.filter(c=>!isCampusCommunity(c));
  let html='';
  if(campuses.length) html+='<optgroup label="🎓 Campuses (sample)">'+campuses.map(opt).join('')+'</optgroup>';
  if(areas.length) html+='<optgroup label="🏘️ Neighborhoods & areas (sample)">'+areas.map(opt).join('')+'</optgroup>';
  if(selected&&list.indexOf(selected)===-1) html+='<option value="'+esc(selected)+'" selected>'+esc(selected)+'</option>';
  return html;
}

window.HUB=Object.assign(window.HUB||{},{
  store:{get state(){return state;},save,uid,clearSamples,householdOwed,unreadCount,myName,todayStr,
    add(k,obj){state[k].unshift(Object.assign({id:uid(),createdAt:Date.now(),sample:false},obj));save();},
    remove(k,id){state[k]=state[k].filter(x=>x.id!==id);save();},
    find(k,id){return state[k].find(x=>x.id===id);},
  },
  ui:{toast,openSheet,closeSheet,esc,fmt$,timeAgo,stars,sampleBadge,initials,greeting,isBlocked,communityOptions,isCampusCommunity},
});
})();
