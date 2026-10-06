/* HUB.api — optional backend data layer (Phase 1, 2026-10-05).
   When an API base URL is configured, degree plans, professor directory and
   horoscopes load from the FastAPI backend instead of the bundled static
   JSON files. API responses are adapted back into the EXACT shapes the app
   already expects, so no other app code changes.

   Configuration (first match wins):
     1. window.__ONARO_API_BASE  (build/deploy-time flag)
     2. localStorage 'onaro_api_base' (operator override, e.g. for testing)
   When neither is set, everything works exactly as before (static JSON).
   If the API is reachable but a request fails, each loader falls back to
   the static file — the app never hard-depends on the backend. */
(function(){
  'use strict';
  var LS_KEY='onaro_api_base';
  var TOKEN_KEY='onaro_auth_token';
  var USER_KEY='onaro_auth_user';
  function base(){
    try{
      if(window.__ONARO_API_BASE) return String(window.__ONARO_API_BASE).replace(/\/+$/,'');
      var v=null;
      try{ v=localStorage.getItem(LS_KEY); }catch(e){}
      if(v) return String(v).replace(/\/+$/,'');
    }catch(e){}
    return '';
  }
  function on(){ return !!base(); }
  /* ---------- auth token management ---------- */
  function getToken(){
    try{ return localStorage.getItem(TOKEN_KEY)||''; }catch(e){ return ''; }
  }
  function setToken(t){
    try{
      if(t) localStorage.setItem(TOKEN_KEY,t);
      else localStorage.removeItem(TOKEN_KEY);
    }catch(e){}
  }
  function getUser(){
    try{
      var s=localStorage.getItem(USER_KEY);
      return s?JSON.parse(s):null;
    }catch(e){ return null; }
  }
  function setUser(u){
    try{
      if(u) localStorage.setItem(USER_KEY,JSON.stringify(u));
      else localStorage.removeItem(USER_KEY);
    }catch(e){}
  }
  function isLoggedIn(){ return !!getToken(); }
  function authHeaders(){
    var t=getToken();
    return t?{'Authorization':'Bearer '+t}:{};
  }
  function aj(path){
    /* Use the safe fetch with retries (js/safeboot.js) — Render free tier
       sleeps and needs 30-60s to wake. Plain fetch fails once and gives up,
       leaving the app with "0 plans". Use generous retries for cold starts. */
    var f=(window.HUB&&HUB.safe&&HUB.safe.fetchJSON)||function(u){
      return fetch(u).then(function(r){
        if(!r.ok&&r.status!==0) throw new Error('http '+r.status);
        return r.json();
      });
    };
    /* 5 retries × 15s timeout = up to ~75s for Render cold start */
    return f(base()+path, {retries:5, timeout:15000});
  }

  /* ---------- degree plans ---------- */
  // -> {plans:[{slug,school,school_slug,city,state,kind,degree,major,credits,
  //             semesters,catalog,source,transfer_confidence,level}], schools:[...]}
  function degreeIndex(){
    return Promise.all([
      aj('/api/degrees/search?limit=20000'),
      aj('/api/schools?limit=20000').catch(function(){ return {items:[]}; })
    ]).then(function(res){
      var dj=res[0], sj=res[1];
      var plans=(dj.items||[]).map(function(p){
        return {
          slug:p.plan_slug, school:p.institution_name, school_slug:p.institution_slug,
          city:p.city||'', state:p.state||'', kind:p.kind||'',
          degree:p.degree, major:p.major,
          credits:p.total_credits, semesters:null,
          catalog:p.catalog_year||'', source:p.source_url||'',
          transfer_confidence:'', level:p.level||''
        };
      });
      var schools=(sj.items||[]).map(function(s){
        return {slug:s.slug, name:s.name, city:s.city||'', state:s.state||'',
                kind:s.kind||'', country:s.country||'US', programs:[],
                programs_collected:0, programs_total:0};
      });
      /* Group plans by school to build the programs array the UI expects */
      var schoolBySlug={};
      schools.forEach(function(sch){ schoolBySlug[sch.slug]=sch; });
      plans.forEach(function(pl){
        var sch=schoolBySlug[pl.school_slug];
        if(sch){
          sch.programs.push({
            status:'collected', plan_id:pl.slug,
            program:pl.major, degree:pl.degree
          });
          sch.programs_collected++;
          sch.programs_total++;
        }
      });
      return {plans:plans, schools:schools};
    });
  }
  // -> {institution:{name,slug}, plan:{id,degree,major,catalog_year,total_credits,
  //        source_url,transfer_confidence,last_verified,notes,semesters:[...]}}
  //    course: {slot_id,code,title,credits,category,choice,choice_note,prereq,tccns}
  function degreeFile(slug){
    return aj('/api/degrees/'+encodeURIComponent(slug)).then(function(p){
      return {
        institution:{name:p.institution_name, slug:p.institution_slug},
        plan:{
          id:p.plan_slug, degree:p.degree, major:p.major,
          catalog_year:p.catalog_year, total_credits:p.total_credits,
          source_url:p.source_url, transfer_confidence:p.transfer_confidence,
          content_hash:'', last_verified:p.last_verified, notes:p.notes,
          semesters:(p.semesters||[]).map(function(s){
            return {n:s.n, label:s.label, courses:(s.courses||[]).map(function(c){
              return {slot_id:c.slot_id, code:c.code, title:c.title,
                      credits:c.credits, category:c.category,
                      choice:!!c.is_choice, choice_note:c.choice_note,
                      prereq:c.prereq||[], tccns:c.tccns,
                      xfer:c.xfer||c.transfer_to||[]};
            })};
          })
        }
      };
    });
  }

  /* ---------- professor directory ---------- */
  // -> {colleges:[{slug,name,country,match,source,retrieved,count}]}
  function facultyIndex(){
    return aj('/api/schools?limit=20000').then(function(j){
      return {colleges:(j.items||[]).map(function(s){
        return {slug:s.slug, name:s.name, country:s.country||'US', match:[],
                source:s.source_url||'', retrieved:'', count:0};
      })};
    });
  }
  // -> {professors:[{name,title,dept,courses}]}
  function facultyFile(slug){
    return aj('/v1/institutions/'+encodeURIComponent(slug)+'/professors?limit=20000')
      .then(function(j){
        return {professors:(j.items||[]).map(function(p){
          return {name:p.name, title:p.title, dept:p.dept, courses:p.courses||[]};
        })};
      });
  }

  /* ---------- horoscopes ---------- */
  // -> {date, signs:{...}} — same shape the app already reads.
  function horoscopeURL(){ return base()+'/api/horoscopes/today'; }

  /* ---------- auth (Phase 2) ---------- */
  function apiPost(path, body){
    var b=base();
    if(!b) return Promise.reject(new Error('no api'));
    var headers=Object.assign({'Content-Type':'application/json'}, authHeaders());
    return fetch(b+path, {
      method:'POST',
      headers:headers,
      body:JSON.stringify(body||{})
    }).then(function(r){
      return r.json().then(function(j){
        if(!r.ok) throw new Error((j&&j.detail)||('http '+r.status));
        return j;
      });
    });
  }
  function apiGet(path){
    var b=base();
    if(!b) return Promise.reject(new Error('no api'));
    return fetch(b+path, {headers:authHeaders()}).then(function(r){
      return r.json().then(function(j){
        if(!r.ok) throw new Error((j&&j.detail)||('http '+r.status));
        return j;
      });
    });
  }
  function authSignup(data){
    return apiPost('/v1/auth/signup', data).then(function(j){
      // j = {user_id, verification_required}
      return j;
    });
  }
  function authVerify(userId, code, via){
    return apiPost('/v1/auth/verify', {user_id:userId, code:code, via:via||'email'}).then(function(j){
      // j = {token, user}
      if(j.token) setToken(j.token);
      if(j.user) setUser(j.user);
      return j;
    });
  }
  function authLogin(identifier, password){
    return apiPost('/v1/auth/login', {identifier:identifier, password:password}).then(function(j){
      if(j.token) setToken(j.token);
      if(j.user) setUser(j.user);
      return j;
    });
  }
  function authMe(){
    return apiGet('/v1/auth/me');
  }
  function authLogout(){
    setToken(''); setUser(null);
    return Promise.resolve({ok:true});
  }
  function authFirebase(idToken, phone, country, name){
    return apiPost('/v1/auth/firebase', {
      id_token: idToken,
      phone: phone||'',
      country: country||'',
      name: name||''
    }).then(function(j){
      // j = {access_token, user_id, existing}
      if(j.access_token) setToken(j.access_token);
      // fetch full user profile
      return authMe().then(function(u){
        setUser(u);
        return {token:j.access_token, user:u, existing:j.existing};
      }).catch(function(){
        return {token:j.access_token, user:{id:j.user_id}, existing:j.existing};
      });
    });
  }

  function authGoogle(idToken, phone, country, name){
    return apiPost('/v1/auth/google', {
      id_token:idToken, phone:phone||'', country:country||'', name:name||''
    }).then(function(j){
      // j = {access_token, user_id, existing}
      if(j.access_token) setToken(j.access_token);
      // fetch full user profile
      return authMe().then(function(u){
        setUser(u);
        return {token:j.access_token, user:u, existing:j.existing};
      }).catch(function(){
        return {token:j.access_token, user:{id:j.user_id}, existing:j.existing};
      });
    });
  }

  /* ---------- read receipts (Phase 2) ---------- */
  function markRead(messageId){
    if(!isLoggedIn()) return Promise.resolve({ok:false, reason:'not_logged_in'});
    return apiPost('/v1/receipts/messages/'+encodeURIComponent(messageId)+'/read', {});
  }
  function getReads(messageId){
    if(!isLoggedIn()) return Promise.resolve({reads:[]});
    return apiGet('/v1/receipts/messages/'+encodeURIComponent(messageId)+'/reads');
  }
  function markGroupRead(groupId, messageKeys){
    if(!isLoggedIn()) return Promise.resolve({ok:false, reason:'not_logged_in'});
    return apiPost('/v1/receipts/groups/'+encodeURIComponent(groupId)+'/read', {message_keys:messageKeys});
  }
  function getGroupReads(groupId){
    if(!isLoggedIn()) return Promise.resolve({reads:{}});
    return apiGet('/v1/receipts/groups/'+encodeURIComponent(groupId)+'/reads');
  }

  /* ---------- 1-on-1 messaging (Phase 2) ---------- */
  function createConversation(otherUserId){
    if(!isLoggedIn()) return Promise.reject(new Error('not_logged_in'));
    return apiPost('/v1/messages/conversations', {other_user_id:otherUserId});
  }
  function listConversations(){
    if(!isLoggedIn()) return Promise.resolve({conversations:[]});
    return apiGet('/v1/messages/conversations');
  }
  function sendMessage(convId, body, clientId){
    if(!isLoggedIn()) return Promise.reject(new Error('not_logged_in'));
    return apiPost('/v1/messages/conversations/'+encodeURIComponent(convId)+'/messages',
      {body:body, client_id:clientId||''});
  }
  function getMessages(convId, limit, before){
    if(!isLoggedIn()) return Promise.resolve({messages:[]});
    var q='?limit='+(limit||100)+(before?'&before='+encodeURIComponent(before):'');
    return apiGet('/v1/messages/conversations/'+encodeURIComponent(convId)+'/messages'+q);
  }

  /* ---------- group messaging (Phase 2) ---------- */
  function sendGroupMessage(groupId, body){
    if(!isLoggedIn()) return Promise.reject(new Error('not_logged_in'));
    return apiPost('/v1/groups/'+encodeURIComponent(groupId)+'/messages', {body:body});
  }
  function getGroupMessages(groupId, limit, before){
    if(!isLoggedIn()) return Promise.resolve({messages:[]});
    var q='?limit='+(limit||100)+(before?'&before='+encodeURIComponent(before):'');
    return apiGet('/v1/groups/'+encodeURIComponent(groupId)+'/messages'+q);
  }

  window.HUB=window.HUB||{};
  window.HUB.api={
    on:on, base:base,
    degreeIndex:degreeIndex, degreeFile:degreeFile,
    facultyIndex:facultyIndex, facultyFile:facultyFile,
    horoscopeURL:horoscopeURL,
    // auth
    getToken:getToken, setToken:setToken, getUser:getUser, isLoggedIn:isLoggedIn,
    authSignup:authSignup, authVerify:authVerify, authLogin:authLogin,
    authMe:authMe, authLogout:authLogout, authGoogle:authGoogle, authFirebase:authFirebase,
    // receipts
    markRead:markRead, getReads:getReads,
    markGroupRead:markGroupRead, getGroupReads:getGroupReads,
    // 1-on-1 messaging
    createConversation:createConversation, listConversations:listConversations,
    sendMessage:sendMessage, getMessages:getMessages,
    // group messaging
    sendGroupMessage:sendGroupMessage, getGroupMessages:getGroupMessages
  };
})();
