/* ============================================================================
   authplanet.js — ORIGINAL animated Saturn-planet scene behind the login /
   signup overlay (Onaro brand artwork, drawn 100% procedurally — nothing
   copied, no image assets). Classic script, IIFE. Registers:
     HUB.authplanet = { start, stop }

   Wiring (see js/auth.js): ensureRoot() inserts <canvas class="auth-planet">,
   open() calls start(), close() calls stop().

   Performance design (PraBin's iPhone is the definition of done):
   - Everything heavy is pre-rendered ONCE into offscreen canvases:
       * starfield + nebula wash baked together (stars never redrawn)
       * 3 planet rotation frames (bands phase-shifted; cycled every ~0.7s)
       * one volt ring canvas (rotated cheaply at draw time)
   - Per frame: 1 starfield drawImage, ~14 twinkle dots, back particles,
     ring drawImage, planet drawImage, ring front-half clip, front particles.
   - devicePixelRatio capped at 2; canvas resized only on debounced resize.
   - rAF pauses on tab hide (visibilitychange); prefers-reduced-motion
     renders exactly ONE static frame, no loop.
   - Brand: #0D100A base, volt #D4F53F accents, NO purple anywhere.
   ============================================================================ */
(function(){
'use strict';
var HUB=window.HUB=window.HUB||{};

var VOLT='#D4F53F', VOLT_RGB='212,245,63';
var TAU=6.2832;
var st=null; /* singleton scene state */

/* deterministic PRNG so the starfield is stable across opens */
function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;
  var t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;
  return((t^t>>>14)>>>0)/4294967296;};}
function clamp(v,a,b){return v<a?a:(v>b?b:v);}
function easeOutCubic(x){x=clamp(x,0,1);return 1-Math.pow(1-x,3);}
function dpr(){return Math.min(window.devicePixelRatio||1,2);}

/* ---------- pre-render: starfield + soft nebula wash (one canvas) ---------- */
function bakeStars(w,h,rng){
  var d=dpr(), pad=40;
  var cv=document.createElement('canvas');
  cv.width=Math.ceil((w+pad*2)*d); cv.height=Math.ceil((h+pad*2)*d);
  var c=cv.getContext('2d'); c.scale(d,d); c.translate(pad,pad);
  /* nebula wash: 3 large soft radial blobs — dark gold/olive, very subtle */
  var blobs=[
    {x:w*0.18,y:h*0.20,r:Math.max(w,h)*0.44,a:0.10,col:'196,152,74'},
    {x:w*0.86,y:h*0.62,r:Math.max(w,h)*0.48,a:0.08,col:'148,158,66'},
    {x:w*0.55,y:h*0.97,r:Math.max(w,h)*0.38,a:0.07,col:'170,132,52'}
  ];
  for(var i=0;i<blobs.length;i++){var b=blobs[i];
    var g=c.createRadialGradient(b.x,b.y,0,b.x,b.y,b.r);
    g.addColorStop(0,'rgba('+b.col+','+b.a+')');
    g.addColorStop(1,'rgba('+b.col+',0)');
    c.fillStyle=g;
    c.fillRect(b.x-b.r,b.y-b.r,b.r*2,b.r*2);}
  /* stars */
  var n=Math.floor(w*h/9000);
  for(i=0;i<n;i++){
    var x=rng()*w, y=rng()*h, r=rng();
    var rad=r<0.86 ? rng()*0.9+0.3 : rng()*1.4+0.9;
    var al=0.25+rng()*0.65;
    var col=rng()<0.12 ? VOLT_RGB : '255,255,255';
    c.fillStyle='rgba('+col+','+al.toFixed(3)+')';
    c.beginPath(); c.arc(x,y,rad,0,TAU); c.fill();}
  return cv;
}

/* ---------- pre-render: one planet rotation frame (band phase shifts) ----- */
function planetFrame(R,frame){
  var d=dpr(), pad=Math.ceil(R*0.25), S=(R+pad)*2;
  var cv=document.createElement('canvas');
  cv.width=cv.height=Math.ceil(S*d);
  var c=cv.getContext('2d'); c.scale(d,d); c.translate(S/2,S/2);
  /* sphere base: light from upper-left */
  var g=c.createRadialGradient(-R*0.38,-R*0.42,R*0.1,0,0,R);
  g.addColorStop(0,'#e9cf7e'); g.addColorStop(0.45,'#b8944a');
  g.addColorStop(0.78,'#5d4a1e'); g.addColorStop(1,'#1a1408');
  c.fillStyle=g;
  c.beginPath(); c.arc(0,0,R,0,TAU); c.fill();
  /* horizontal bands, clipped to the disc; phase shift per frame = rotation */
  c.save();
  c.beginPath(); c.arc(0,0,R,0,TAU); c.clip();
  var bands=[
    [-0.72,0.10,'rgba(255,240,200,0.20)'],[-0.45,0.14,'rgba(60,45,15,0.28)'],
    [-0.18,0.12,'rgba(255,235,190,0.16)'],[0.10,0.16,'rgba(70,52,18,0.26)'],
    [0.38,0.11,'rgba(255,238,195,0.14)'],[0.62,0.13,'rgba(50,38,14,0.30)']];
  for(var i=0;i<bands.length;i++){
    var wob=Math.sin(frame*1.05+i*1.7)*R*0.012;
    c.fillStyle=bands[i][2];
    c.beginPath();
    c.ellipse(0,bands[i][0]*R+wob,R*1.02,bands[i][1]*R,0,0,TAU);
    c.fill();}
  c.fillStyle='rgba(255,244,210,0.10)';
  c.fillRect(-R,-R*0.03,R*2,R*0.06); /* bright equatorial band */
  c.restore();
  /* limb darkening + top-left highlight */
  var lg=c.createRadialGradient(0,0,R*0.72,0,0,R);
  lg.addColorStop(0,'rgba(0,0,0,0)'); lg.addColorStop(1,'rgba(8,6,2,0.55)');
  c.fillStyle=lg; c.beginPath(); c.arc(0,0,R,0,TAU); c.fill();
  var hg=c.createRadialGradient(-R*0.45,-R*0.5,0,-R*0.45,-R*0.5,R*0.7);
  hg.addColorStop(0,'rgba(255,250,235,0.28)');
  hg.addColorStop(1,'rgba(255,250,235,0)');
  c.fillStyle=hg; c.beginPath(); c.arc(0,0,R,0,TAU); c.fill();
  return cv;
}

/* ---------- pre-render: volt ring (un-tilted; tilt applied at draw) -------- */
function ringCanvas(R){
  var d=dpr(), RW=R*4.0, RH=R*2.2;
  var cv=document.createElement('canvas');
  cv.width=Math.ceil(RW*d); cv.height=Math.ceil(RH*d);
  var c=cv.getContext('2d'); c.scale(d,d); c.translate(RW/2,RH/2);
  var rx=R*1.72, ry=rx*0.30;
  function stroke(rx2,ry2,lw,style,blur){
    c.save();
    if(blur){c.shadowColor=VOLT; c.shadowBlur=blur;}
    c.strokeStyle=style; c.lineWidth=lw;
    c.beginPath(); c.ellipse(0,0,rx2,ry2,0,0,TAU); c.stroke();
    c.restore();}
  stroke(rx,ry,10,'rgba('+VOLT_RGB+',0.16)',22);   /* halo */
  stroke(rx,ry,3.5,'rgba('+VOLT_RGB+',0.85)',10);  /* main volt band */
  stroke(rx*0.86,ry*0.86,1.6,'rgba('+VOLT_RGB+',0.45)',0); /* inner strand */
  stroke(rx*1.14,ry*1.14,1.2,'rgba('+VOLT_RGB+',0.30)',0); /* outer wisp */
  return cv;
}

/* ---------- build / rebuild the whole scene (called on start + resize) ---- */
function build(s){
  var cv=s.cv;
  var w=cv.clientWidth||window.innerWidth, h=cv.clientHeight||window.innerHeight;
  if(!w||!h) return false;
  var d=dpr();
  cv.width=Math.round(w*d); cv.height=Math.round(h*d);
  s.w=w; s.h=h; s.d=d;
  s.R=Math.min(w,h)*(w<520?0.23:0.19);
  s.cx=w*0.5;
  s.cy=h*(w<520?0.27:0.30); /* upper third, above the centered card */
  s.tilt=-0.34;
  var rng=mulberry32(20261007);
  s.stars=bakeStars(w,h,rng);
  s.frames=[planetFrame(s.R,0),planetFrame(s.R,1),planetFrame(s.R,2)];
  s.ring=ringCanvas(s.R);
  var r2=mulberry32(77);
  s.tw=[];
  for(var i=0;i<14;i++)
    s.tw.push({x:r2()*w,y:r2()*h,r:r2()*1.2+0.5,
               ph:r2()*TAU,sp:1.2+r2()*2.2,volt:r2()<0.25});
  var r3=mulberry32(4242);
  s.p=[];
  for(i=0;i<26;i++)
    s.p.push({a:r3()*TAU,sp:(0.10+r3()*0.22)*(r3()<0.5?1:-1),
              rx:1.55+r3()*0.75});
  return true;
}

/* ---------- ring particles: back half behind planet, front half above ----- */
function drawParticles(s,ctx,back,cx,cy,tilt,e,t){
  var ct=Math.cos(tilt), sn=Math.sin(tilt);
  var n=Math.floor(s.p.length*e); /* particles fade in during the intro */
  ctx.fillStyle=VOLT;
  for(var i=0;i<n;i++){
    var p=s.p[i];
    var a=p.a+t*p.sp;
    if((Math.sin(a)<0)!==back) continue;
    var rx=p.rx*s.R, ry=rx*0.30;
    var dx=Math.cos(a)*rx, dy=Math.sin(a)*ry;
    var x=cx+dx*ct-dy*sn, y=cy+dx*sn+dy*ct;
    var dep=0.5+0.5*Math.sin(a); /* depth: alpha + size */
    ctx.globalAlpha=(0.25+0.6*dep)*e;
    var r=(0.8+1.6*dep)*s.d*0.6;
    ctx.beginPath(); ctx.arc(x,y,r,0,TAU); ctx.fill();}
  ctx.globalAlpha=1;
}

/* ---------- one frame ------------------------------------------------------ */
function draw(s,now){
  var ctx=s.ctx, w=s.w, h=s.h;
  /* rAF timestamps can predate the performance.now() sampled in start()
     (synthetic BeginFrames in headless, vsync edge on device): a negative t
     would make Math.floor(t*1.4)%3 === -1 and kill the loop with a TypeError
     on s.frames[-1].width — and the throw would skip the next rAF schedule,
     freezing the scene. Clamp. */
  var t=Math.max(0,(now-s.t0)/1000);
  var e=easeOutCubic((now-s.t0)/2000); /* 2s intro: fade + scale + ring sweep */
  ctx.setTransform(s.d,0,0,s.d,0,0);
  ctx.clearRect(0,0,w,h);
  var px=s.px, py=s.py;
  /* starfield + nebula (baked), shallow parallax */
  ctx.drawImage(s.stars,px*0.35-40,py*0.35-40,w+80,h+80);
  /* twinkling overlay stars */
  for(var i=0;i<s.tw.length;i++){var tw=s.tw[i];
    var al=0.25+0.65*(0.5+0.5*Math.sin(t*tw.sp+tw.ph));
    ctx.fillStyle=tw.volt
      ? 'rgba('+VOLT_RGB+','+al.toFixed(2)+')'
      : 'rgba(255,255,255,'+al.toFixed(2)+')';
    ctx.beginPath();
    ctx.arc(tw.x+px*0.35,tw.y+py*0.35,tw.r,0,TAU);
    ctx.fill();}
  var R=s.R, cx=s.cx+px, cy=s.cy+py;
  var tilt=s.tilt+(1-e)*0.55; /* rings sweep in during intro */
  var sc=0.86+0.14*e;        /* planet scales up during intro */
  var RW=R*4.0, RH=R*2.2;
  /* back particles (behind planet) */
  drawParticles(s,ctx,true,cx,cy,tilt,e,t);
  /* full ring behind planet */
  ctx.save();
  ctx.globalAlpha=e*0.95;
  ctx.translate(cx,cy); ctx.rotate(tilt);
  ctx.drawImage(s.ring,-RW/2,-RH/2,RW,RH);
  ctx.restore();
  /* planet */
  var f=s.frames[Math.floor(t*1.4)%3];
  var fs=f.width/s.d; /* CSS size of the pre-rendered frame */
  ctx.save();
  ctx.globalAlpha=e;
  ctx.translate(cx,cy); ctx.scale(sc,sc);
  ctx.drawImage(f,-fs/2,-fs/2,fs,fs);
  ctx.restore();
  /* ring front half (passes in front of the planet) */
  ctx.save();
  ctx.globalAlpha=e*0.95;
  ctx.beginPath(); ctx.rect(0,cy,w,h-cy); ctx.clip();
  ctx.translate(cx,cy); ctx.rotate(tilt);
  ctx.drawImage(s.ring,-RW/2,-RH/2,RW,RH);
  ctx.restore();
  /* front particles */
  drawParticles(s,ctx,false,cx,cy,tilt,e,t);
}

function loop(now){
  if(!st||!st.running) return;
  if(document.hidden){st.running=false; st.raf=0; st.paused=true; return;}
  st.px+=(st.tpx-st.px)*0.08; /* smooth parallax easing */
  st.py+=(st.tpy-st.py)*0.08;
  draw(st,now);
  st.raf=requestAnimationFrame(loop);
}

function stopLoop(){
  if(st&&st.raf){cancelAnimationFrame(st.raf); st.raf=0;}
  if(st) st.running=false;
}

/* ---------- input: pointer parallax (desktop) + orientation (mobile) ------ */
function bindInput(s){
  if(s.bound) return; s.bound=true;
  var lastOri=0, lastPtr=0;
  window.addEventListener('pointermove',function(ev){
    lastPtr=Date.now();
    s.tpx=clamp((ev.clientX/window.innerWidth-0.5)*24,-12,12);
    s.tpy=clamp((ev.clientY/window.innerHeight-0.5)*24,-12,12);
  },{passive:true});
  window.addEventListener('deviceorientation',function(ev){
    var now=Date.now();
    if(now-lastOri<250||now-lastPtr<3000) return; /* throttled; pointer wins */
    if(ev.gamma==null&&ev.beta==null) return;
    lastOri=now;
    s.tpx=clamp((ev.gamma||0)/45*12,-12,12);
    s.tpy=clamp(((ev.beta||0)-45)/45*10,-12,12);
  });
  var rto=null;
  window.addEventListener('resize',function(){ /* debounced; no layout thrash */
    if(rto) clearTimeout(rto);
    rto=setTimeout(function(){
      if(st&&st.running) build(st);
    },200);
  });
  document.addEventListener('visibilitychange',function(){
    if(!st) return;
    if(document.hidden){
      if(st.raf){cancelAnimationFrame(st.raf); st.raf=0; st.running=false; st.paused=true;}
    }else if(st.paused){
      var root=document.getElementById('authRoot');
      if(root&&!root.hidden){
        st.paused=false; st.running=true; st.raf=requestAnimationFrame(loop);}
    }
  });
}

function start(){
  var cv=document.getElementById('authPlanet');
  if(!cv) return;
  if(!st){
    st={cv:cv,ctx:cv.getContext('2d'),px:0,py:0,tpx:0,tpy:0,
        raf:0,t0:0,running:false,paused:false,bound:false};
    bindInput(st);
  }
  if(!build(st)) return;
  st.t0=performance.now();
  st.px=st.py=st.tpx=st.tpy=0; /* reset parallax each open */
  st.paused=false;
  var rm=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(rm){ stopLoop(); draw(st,st.t0+2000); return; } /* ONE static frame */
  stopLoop();
  st.running=true;
  st.raf=requestAnimationFrame(loop);
}

function stop(){ stopLoop(); }

HUB.authplanet={start:start,stop:stop};
})();
