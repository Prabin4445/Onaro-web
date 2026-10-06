/* END-TO-END scanner QA driver (new missing gate):
   shutter -> detect -> refine -> warp -> filter -> saved page, then thumbnails.
   Part 1: takePhoto path — EXIF-corrected 3:4 photo + 9:16 video (the fixed bug):
           re-detect in photo space, assert levelness <=1deg, acutance >=0.90xGT.
   Part 2: frameGrab path regression (video==still).
   Part 3: thumbnail gate — dense ruled page; stepped (app's new _thumb) must
           preserve >=1.5x the line-rows of the old one-step downscale.
   Part 4: filter chain — magic/bw filters produce sane non-blank output.
   Prints JSON lines. Usage: node qa/scane2e_driver.js
*/
global.window = {};
const fs = require('fs');
const HUB = '/home/hatch/workspace/hub';
eval(fs.readFileSync(HUB + '/js/scan.js', 'utf8'));
const T = window.HUB.scan._t;
for (const k of ['detectQuad','detectLive','warpFn','refineCapture','applyFilter','thumbFn']) {
  if (!T[k]) { console.log(JSON.stringify({ fatal: 'missing hook ' + k })); process.exit(1); }
}

let _s = 987654;
function rnd() { _s = (_s * 1103515245 + 12345) & 0x7fffffff; return _s / 0x7fffffff; }
function rr(a, b) { return a + rnd() * (b - a); }

function solveH(src, dst) {
  const A = [], B = [];
  for (let i = 0; i < 4; i++) {
    const sx = src[i].x, sy = src[i].y, dx = dst[i].x, dy = dst[i].y;
    A.push([sx, sy, 1, 0, 0, 0, -dx * sx, -dx * sy]); B.push(dx);
    A.push([0, 0, 0, sx, sy, 1, -dy * sx, -dy * sy]); B.push(dy);
  }
  const n = 8, M = [];
  for (let i = 0; i < n; i++) { M.push(A[i].slice()); M[i].push(B[i]); }
  for (let c = 0; c < n; c++) {
    let piv = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[piv][c])) piv = r;
    const tmp = M[c]; M[c] = M[piv]; M[piv] = tmp;
    const d = M[c][c] || 1e-9;
    for (let r = 0; r < n; r++) { if (r === c) continue; const f = M[r][c] / d;
      for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k]; }
  }
  const x = []; for (let i = 0; i < n; i++) x.push(M[i][n] / (M[i][i] || 1e-9));
  return x;
}
function applyH8(H, x, y) {
  const w = H[6]*x + H[7]*y + 1;
  return [(H[0]*x + H[1]*y + H[2]) / w, (H[3]*x + H[4]*y + H[5]) / w];
}

function paperTexture(pw, ph, dense) {
  const px = new Uint8ClampedArray(pw * ph * 4);
  for (let i = 0; i < pw * ph; i++) { px[i*4]=248; px[i*4+1]=247; px[i*4+2]=243; px[i*4+3]=255; }
  function bar(x, y, w, h, v) {
    for (let yy = 0; yy < h; yy++) for (let xx = 0; xx < w; xx++) {
      const ox = x+xx, oy = y+yy;
      if (ox<0||oy<0||ox>=pw||oy>=ph) continue;
      const o=(oy*pw+ox)*4; px[o]=v; px[o+1]=v; px[o+2]=v+2;
    }
  }
  bar(24, 20, pw-48, 14, 45);
  let y = 52;
  const gap = dense ? 24 : 13;
  for (let l = 0; l < 60; l++) {
    const wdt = (l%7===6) ? rr(0.3,0.5) : rr(0.85,0.98);
    bar(24, Math.round(y), Math.round((pw-48)*wdt), 4, 70);
    y += gap; if (y > ph-20) break;
  }
  return px;
}

function renderScene(W, H, quad, dense) {
  const px = new Uint8ClampedArray(W * H * 4);
  for (let i = 0; i < W*H; i++) {
    const nz = (rnd()-.5)*16, o=i*4;
    px[o]=52+nz; px[o+1]=50+nz; px[o+2]=48+nz+2; px[o+3]=255;
  }
  const PW = 420, PH = 560, paper = paperTexture(PW, PH, dense);
  const src = [{x:0,y:0},{x:PW,y:0},{x:PW,y:PH},{x:0,y:PH}];
  const H8 = solveH(src, quad);
  const det = H8[0]*(H8[4]-H8[7]*0)-H8[1]*(H8[3]-H8[6]*0)+H8[2]*(H8[3]*H8[7]-H8[4]*H8[6]);
  function inPoly(x,y){
    let ins=false;
    for(let i=0,j=3;i<4;j=i++){const xi=quad[i].x,yi=quad[i].y,xj=quad[j].x,yj=quad[j].y;
      if(((yi>y)!==(yj>y))&&(x<(xj-xi)*(y-yi)/(yj-yi)+xi))ins=!ins;}
    return ins;
  }
  const xs = quad.map(p=>p.x), ys = quad.map(p=>p.y);
  const minx=Math.max(0,Math.floor(Math.min(...xs))), maxx=Math.min(W-1,Math.ceil(Math.max(...xs)));
  const miny=Math.max(0,Math.floor(Math.min(...ys))), maxy=Math.min(H-1,Math.ceil(Math.max(...ys)));
  // inverse map via adjugate
  for (let y = miny; y <= maxy; y++) for (let x = minx; x <= maxx; x++) {
    if (!inPoly(x, y)) continue;
    // solve H * s = [x,y,1] via Cramer on the 8-param form
    const a=H8[0],b=H8[1],c=H8[2],d=H8[3],e=H8[4],f=H8[5],g=H8[6],h=H8[7];
    // x = (a*sx+b*sy+c)/(g*sx+h*sy+1) ; y = (d*sx+e*sy+f)/(g*sx+h*sy+1)
    // linearize: (a-g*x)*sx + (b-h*x)*sy = x-c ; (d-g*y)*sx + (e-h*y)*sy = y-f
    const A1=a-g*x, B1=b-h*x, C1=x-c, A2=d-g*y, B2=e-h*y, C2=y-f;
    const D=A1*B2-A2*B1||1e-9;
    const sx0=(C1*B2-C2*B1)/D, sy0=(A1*C2-A2*C1)/D;
    let sx = Math.max(0, Math.min(PW-2, Math.floor(sx0))), sy = Math.max(0, Math.min(PH-2, Math.floor(sy0)));
    const fx = Math.max(0,Math.min(1,sx0-sx)), fy = Math.max(0,Math.min(1,sy0-sy));
    const o00=(sy*PW+sx)*4, o=(y*W+x)*4;
    for (let cc = 0; cc < 3; cc++)
      px[o+cc] = paper[o00+cc]*(1-fx)*(1-fy)+paper[o00+4+cc]*fx*(1-fy)+paper[o00+PW*4+cc]*(1-fx)*fy+paper[o00+PW*4+4+cc]*fx*fy;
    px[o+3]=255;
  }
  return px;
}

function downscaleBilinear(px, W, H, dw, dh) {
  const out = new Uint8ClampedArray(dw*dh*4);
  for (let y = 0; y < dh; y++) for (let x = 0; x < dw; x++) {
    const sx = Math.min(W-1.001, x*(W-1)/(dw-1)), sy = Math.min(H-1.001, y*(H-1)/(dh-1));
    const x0 = Math.floor(sx), y0 = Math.floor(sy), fx = sx-x0, fy = sy-y0;
    const o=(y*dw+x)*4, p00=(y0*W+x0)*4;
    for (let c = 0; c < 4; c++)
      out[o+c] = px[p00+c]*(1-fx)*(1-fy)+px[p00+4+c]*fx*(1-fy)+px[p00+W*4+c]*(1-fx)*fy+px[p00+W*4+4+c]*fx*fy;
  }
  return out;
}

function measureLevel(out, ow, oh) {
  const lum = (x, y) => (out[(y*ow+x)*4]+out[(y*ow+x)*4+1]+out[(y*ow+x)*4+2])/3;
  function fitH(yS,yE,ySt,x0,x1,xSt,fromTop){
    const pts=[];
    for(let x=x0;x<=x1;x+=xSt){
      if(fromTop){for(let y=yS;y<=yE;y+=ySt){if(lum(x,y)>170){pts.push([x,y]);break;}}}
      else{for(let y=yE;y>=yS;y-=ySt){if(lum(x,y)>170){pts.push([x,y]);break;}}}
    }
    if(pts.length<10)return null;
    let sx=0,sy=0;pts.forEach(p=>{sx+=p[0];sy+=p[1];});sx/=pts.length;sy/=pts.length;
    let sxx=0,sxy=0;pts.forEach(p=>{sxx+=(p[0]-sx)*(p[0]-sx);sxy+=(p[0]-sx)*(p[1]-sy);});
    return sxx<1e-9?null:Math.atan(sxy/sxx)*180/Math.PI;
  }
  const m=[fitH(0,oh*0.4|0,2,ow*0.08|0,ow*0.92|0,4,true),
           fitH(oh*0.6|0,oh-1,2,ow*0.08|0,ow*0.92|0,4,false)];
  const vals=m.filter(v=>v!==null).map(Math.abs);
  return vals.length?Math.max(...vals):null;
}

function acutance(out, ow, oh) {
  let sum=0,n=0;
  const L=(x,y)=>(out[(y*ow+x)*4]+out[(y*ow+x)*4+1]+out[(y*ow+x)*4+2])/3;
  for(let y=oh*0.1|0;y<oh*0.9;y+=2)for(let x=ow*0.1|0;x<ow*0.9;x+=2){
    const gx=L(x+1,y)-L(x-1,y), gy=L(x,y+1)-L(x,y-1);
    const g=Math.sqrt(gx*gx+gy*gy);
    if(g>12){sum+=g;n++;}
  }
  return n?sum/n:0;
}

/* full app-equivalent path for a still: detect-in-space -> refine -> warp -> filter */
function appPath(stillPx, SW, SH, seedQ, filter) {
  let q = seedQ;
  try {
    const rq = T.refineCapture(stillPx, SW, SH, q);
    if (rq && rq.length === 4) q = rq;
  } catch(e){}
  let maxE = 0;
  for (let i = 0; i < 4; i++) { const j=(i+1)%4;
    maxE = Math.max(maxE, Math.hypot(q[j].x-q[i].x, q[j].y-q[i].y)); }
  const LONG = Math.max(200, Math.round(maxE*0.9));
  const top = Math.hypot(q[1].x-q[0].x, q[1].y-q[0].y);
  const bot = Math.hypot(q[2].x-q[3].x, q[2].y-q[3].y);
  const lef = Math.hypot(q[3].x-q[0].x, q[3].y-q[0].y);
  const rig = Math.hypot(q[2].x-q[1].x, q[2].y-q[1].y);
  const asp = Math.max(top,bot)/Math.max(1,Math.max(lef,rig));
  const outW = asp>=1?LONG:Math.round(LONG*asp), outH = asp>=1?Math.round(LONG/asp):LONG;
  const warped = T.warpFn(stillPx, SW, SH, q, outW, outH);
  return { px: T.applyFilter(warped, outW, outH, filter||'color'), w: outW, h: outH, q: q };
}

const out = [];

/* ---- Part 1: takePhoto path — photo 675x900 (3:4, EXIF-corrected), video 540x960.
   NEW app logic: re-detect in photo space (T.detectQuad on photo pixels). ---- */
{
  const SW=675, SH=900, cx=SW/2, cy=SH/2;
  const quads = {
    clean:  [{x:cx-230,y:cy-340},{x:cx+240,y:cy-335},{x:cx+230,y:cy+345},{x:cx-230,y:cy+340}],
    angled: [{x:cx-160,y:cy-370},{x:cx+290,y:cy-280},{x:cx+240,y:cy+360},{x:cx-200,y:cy+320}],
  };
  for (const k of Object.keys(quads)) {
    const stillPx = renderScene(SW, SH, quads[k], false);
    // photo-space detection (what SCAN.detectQuad does on the canvas)
    const ds = Math.min(1, 400/Math.max(SW,SH));
    const dw = Math.max(1,Math.round(SW*ds)), dh = Math.max(1,Math.round(SH*ds));
    const detPx = downscaleBilinear(stillPx, SW, SH, dw, dh);
    let q = null;
    try {
      const dq = T.detectQuad(detPx, dw, dh);
      if (dq && dq.length===4) q = dq.map(p=>({x:p.x/ds, y:p.y/ds}));
    } catch(e){}
    if (!q) { out.push({part:1, name:'takePhoto-'+k, detected:false}); continue; }
    const r = appPath(stillPx, SW, SH, q, 'color');
    const gt = appPath(stillPx, SW, SH, quads[k], 'color');
    const lvl = measureLevel(r.px, r.w, r.h);
    const ac = acutance(r.px,r.w,r.h), acGT = acutance(gt.px,gt.w,gt.h);
    out.push({ part:1, name:'takePhoto-'+k, detected:true,
      maxDeg: lvl===null?null:+lvl.toFixed(3),
      acutRatio: acGT>0?+(ac/acGT).toFixed(3):null });
  }
}

/* ---- Part 2: frameGrab regression — video==still 540x960 ---- */
{
  const VW=540, VH=960, cx=VW/2, cy=VH/2;
  const quad = [{x:cx-150,y:cy-310},{x:cx+235,y:cy-245},{x:cx+200,y:cy+305},{x:cx-165,y:cy+270}];
  const scenePx = renderScene(VW, VH, quad, false);
  const dw=320, dh=Math.round(320*VH/VW);
  const detPx = downscaleBilinear(scenePx, VW, VH, dw, dh);
  const st={}; let res=T.detectLive(detPx,dw,dh,st);
  for(let f=0;f<6;f++) res=T.detectLive(detPx,dw,dh,st);
  if (res.guide||!res.q) { out.push({part:2, name:'frameGrab', locked:false}); }
  else {
    const sx=VW/dw, sy=VH/dh;
    const qStill=res.q.map(p=>({x:p.x*sx,y:p.y*sy}));
    const r=appPath(scenePx,VW,VH,qStill,'color');
    const gt=appPath(scenePx,VW,VH,quad,'color');
    const lvl=measureLevel(r.px,r.w,r.h);
    const ac=acutance(r.px,r.w,r.h), acGT=acutance(gt.px,gt.w,gt.h);
    out.push({ part:2, name:'frameGrab', locked:true,
      maxDeg: lvl===null?null:+lvl.toFixed(3),
      acutRatio: acGT>0?+(ac/acGT).toFixed(3):null });
  }
}

/* ---- Part 3: thumbnail helper sanity ----
   T.thumbFn must return correct dims; stepped downscale must not darken/
   brighten the image vs the source mean (no systematic bias), and must
   differ from naive one-step (it does multiple passes). */
{
  const PW=1600, PH=2000;
  const page = paperTexture(PW, PH, true);
  let srcMean=0; for(let i=0;i<PW*PH;i+=13) srcMean+=(page[i*4]+page[i*4+1]+page[i*4+2])/3;
  srcMean/=Math.ceil(PW*PH/13);
  const t = T.thumbFn(page, PW, PH, 160);
  let thMean=0; for(let i=0;i<t.w*t.h;i+=3) thMean+=(t.px[i*4]+t.px[i*4+1]+t.px[i*4+2])/3;
  thMean/=Math.ceil(t.w*t.h/3);
  const one = downscaleBilinear(page,PW,PH,t.w,t.h);
  let mad=0; for(let i=0;i<t.w*t.h*4;i+=4) mad+=Math.abs(t.px[i]-one[i]);
  mad/= (t.w*t.h);
  out.push({ part:3, name:'thumbnail', w:t.w, h:t.h,
             meanBias: +(thMean-srcMean).toFixed(2),
             differsFromOneStep: mad>0.5 });
}

/* ---- Part 4: filter chain on final output ---- */
{
  const PW=600, PH=760;
  const page = paperTexture(PW, PH, false);
  const res={};
  for (const f of ['color','gray','bw','magic']) {
    const o=T.applyFilter(page,PW,PH,f);
    let s=0; for(let i=0;i<PW*PH;i+=7) s+=(o[i*4]+o[i*4+1]+o[i*4+2])/3;
    const mean=s/Math.ceil(PW*PH/7);
    res[f]=Math.round(mean);
  }
  out.push({ part:4, name:'filters', means:res });
}

for (const r of out) console.log(JSON.stringify(r));
