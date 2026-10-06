/* Levelness QA driver: measures whether the scanner's warp output is truly
   level (page edges within +/-1deg of horizontal/vertical), CamScanner-style.
   For each synthetic fixture with known ground-truth quad:
     test=detect : CV.detectQuad -> warp -> measure edge angles
     test=refine : perturb GT quad +/-10px (simulated live-tracker error) ->
                   CV.refineCapture -> warp -> measure edge angles
   Prints one JSON object per line. Hard gate: maxDeg <= 1.0 when IoU >= 0.85.
   Usage: node qa/scanlevel_driver.js
*/
global.window = {};
const fs = require('fs'), path = require('path');
const HUB = '/home/hatch/workspace/hub';
eval(fs.readFileSync(path.join(HUB, 'js', 'scan.js'), 'utf8'));
const T = window.HUB.scan._t;
if (!T || !T.detectQuad || !T.warpFn || !T.refineCapture) {
  console.log(JSON.stringify({ fatal: 'missing hooks' })); process.exit(1);
}

let _s = 777123;
function rnd() { _s = (_s * 1103515245 + 12345) & 0x7fffffff; return _s / 0x7fffffff; }
function rr(a, b) { return a + rnd() * (b - a); }

const FW = 800, FH = 1000;

/* homography solve (8-dof), copied pattern from scandet2_driver */
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
  return [[x[0], x[1], x[2]], [x[3], x[4], x[5]], [x[6], x[7], 1]];
}
function inv3(m) {
  const a=m[0][0],b=m[0][1],c=m[0][2],d=m[1][0],e=m[1][1],f=m[1][2],g=m[2][0],h=m[2][1],i=m[2][2];
  const A=e*i-f*h,B=-(d*i-f*g),C=d*h-e*g,det=a*A+b*B+c*C||1e-9;
  return [[A/det,(c*h-b*i)/det,(b*f-c*e)/det],[B/det,(a*i-c*g)/det,(c*d-a*f)/det],[C/det,(b*g-a*h)/det,(a*e-b*d)/det]];
}
function applyH(H, x, y) {
  const w = H[2][0]*x + H[2][1]*y + H[2][2];
  return [(H[0][0]*x + H[0][1]*y + H[0][2]) / w, (H[1][0]*x + H[1][1]*y + H[1][2]) / w];
}
function inPoly(x, y, q) {
  let ins = false;
  for (let i = 0, j = 3; i < 4; j = i++) {
    const xi=q[i].x, yi=q[i].y, xj=q[j].x, yj=q[j].y;
    if (((yi > y) !== (yj > y)) && (x < (xj-xi)*(y-yi)/(yj-yi) + xi)) ins = !ins;
  }
  return ins;
}
function polyIoU(a, b) {
  let inter = 0, union = 0;
  for (let y = 2; y < FH; y += 4) for (let x = 2; x < FW; x += 4) {
    const ia = inPoly(x, y, a), ib = inPoly(x, y, b);
    if (ia && ib) inter++; if (ia || ib) union++;
  }
  return union ? inter / union : 0;
}

/* paper texture: bright page with title bar + text lines */
function paperTexture(pw, ph, dim) {
  const px = new Uint8ClampedArray(pw * ph * 4);
  const base = dim ? 198 : 246;
  for (let i = 0; i < pw * ph; i++) { px[i*4]=base; px[i*4+1]=base-2; px[i*4+2]=base-6; px[i*4+3]=255; }
  function bar(x, y, w, h, v) {
    for (let yy = 0; yy < h; yy++) for (let xx = 0; xx < w; xx++) {
      const ox = x+xx, oy = y+yy;
      if (ox<0||oy<0||ox>=pw||oy>=ph) continue;
      const o=(oy*pw+ox)*4; px[o]=v; px[o+1]=v; px[o+2]=v+2;
    }
  }
  bar(30, 26, pw-60, 16, 40);
  bar(30, 50, Math.round((pw-60)*0.55), 7, 88);
  let y = 72;
  for (let l = 0; l < 34; l++) {
    const wdt = (l%6===5) ? rr(0.25,0.45) : rr(0.7,0.96);
    bar(30, Math.round(y), Math.round((pw-60)*wdt), 5, 60);
    y += 13; if (y > ph-26) break;
  }
  return { w: pw, h: ph, px: px };
}

/* fixture: dark textured bg + paper quad (class controls geometry/contrast) */
function makeFixture(cls) {
  const px = new Uint8ClampedArray(FW * FH * 4);
  const bgV = cls === 'lowcontrast' ? 120 : 52;
  for (let y = 0; y < FH; y++) for (let x = 0; x < FW; x++) {
    const band = cls === 'lowcontrast' ? 0 : Math.sin(y*0.05+x*0.013)*10;
    const nz = (rnd()-.5) * (cls === 'lowcontrast' ? 6 : 14);
    const o = (y*FW+x)*4;
    let r = bgV+band+nz, g = bgV+band*0.8+nz, b = bgV+band*0.6+nz+2;
    if (cls === 'shadow') { const sh = 0.45 + 0.55*((x+y)/(FW+FH)); r*=sh; g*=sh; b*=sh; }
    px[o]=r; px[o+1]=g; px[o+2]=b; px[o+3]=255;
  }
  const paper = paperTexture(500, 650, cls === 'lowcontrast');
  const cx = FW/2, cy = FH/2;
  let quad;
  if (cls === 'clean') {
    quad = [{x:cx-230,y:cy-300},{x:cx+235,y:cy-295},{x:cx+225,y:cy+305},{x:cx-225,y:cy+300}];
  } else if (cls === 'angled') {
    quad = [{x:cx-160,y:cy-330},{x:cx+290,y:cy-250},{x:cx+240,y:cy+320},{x:cx-200,y:cy+280}];
  } else if (cls === 'rotated') {
    const ang = rr(0.5, 1.0), ca = Math.cos(ang), sa = Math.sin(ang);
    const base = [{x:-230,y:-300},{x:230,y:-300},{x:230,y:300},{x:-230,y:300}];
    quad = base.map(p => ({ x: cx + p.x*ca - p.y*sa, y: cy + p.x*sa + p.y*ca }));
  } else { /* lowcontrast, shadow: moderate perspective */
    quad = [{x:cx-210,y:cy-310},{x:cx+250,y:cy-290},{x:cx+230,y:cy+300},{x:cx-215,y:cy+315}];
  }
  /* render paper via inverse homography sampling */
  const src = [{x:0,y:0},{x:500,y:0},{x:500,y:650},{x:0,y:650}];
  const H = solveH(src, quad), I = inv3(H);
  const minx = Math.max(0, Math.floor(Math.min(...quad.map(p=>p.x))));
  const maxx = Math.min(FW-1, Math.ceil(Math.max(...quad.map(p=>p.x))));
  const miny = Math.max(0, Math.floor(Math.min(...quad.map(p=>p.y))));
  const maxy = Math.min(FH-1, Math.ceil(Math.max(...quad.map(p=>p.y))));
  for (let y = miny; y <= maxy; y++) for (let x = minx; x <= maxx; x++) {
    if (!inPoly(x, y, quad)) continue;
    const sxy = applyH(I, x, y);
    let sx = Math.max(0, Math.min(498, Math.floor(sxy[0]))), sy = Math.max(0, Math.min(648, Math.floor(sxy[1])));
    const fx = sxy[0]-sx, fy = sxy[1]-sy;
    const o00=(sy*500+sx)*4;
    const o=(y*FW+x)*4;
    for (let c = 0; c < 3; c++) {
      px[o+c] = paper.px[o00+c]*(1-fx)*(1-fy) + paper.px[o00+4+c]*fx*(1-fy) +
                paper.px[o00+500*4+c]*(1-fx)*fy + paper.px[o00+500*4+4+c]*fx*fy;
    }
    px[o+3] = 255;
  }
  return { px: px, gt: quad };
}

/* measure edge angles of the bright page in a warped output */
function measureLevel(out, ow, oh) {
  const lum = (x, y) => (out[(y*ow+x)*4] + out[(y*ow+x)*4+1] + out[(y*ow+x)*4+2]) / 3;
  function fitH(yStart, yEnd, yStep, x0, x1, xStep, fromTop) {
    const pts = [];
    for (let x = x0; x <= x1; x += xStep) {
      if (fromTop) { for (let y = yStart; y <= yEnd; y += yStep) { if (lum(x, y) > 170) { pts.push([x, y]); break; } } }
      else { for (let y = yEnd; y >= yStart; y -= yStep) { if (lum(x, y) > 170) { pts.push([x, y]); break; } } }
    }
    if (pts.length < 10) return null;
    let sx=0, sy=0; pts.forEach(p=>{sx+=p[0];sy+=p[1];});
    sx/=pts.length; sy/=pts.length;
    let sxx=0, sxy=0;
    pts.forEach(p=>{ sxx+=(p[0]-sx)*(p[0]-sx); sxy+=(p[0]-sx)*(p[1]-sy); });
    if (sxx < 1e-9) return null;
    return Math.atan(sxy/sxx) * 180 / Math.PI;
  }
  function fitV(xStart, xEnd, xStep, y0, y1, yStep, fromLeft) {
    const pts = [];
    for (let y = y0; y <= y1; y += yStep) {
      if (fromLeft) { for (let x = xStart; x <= xEnd; x += xStep) { if (lum(x, y) > 170) { pts.push([x, y]); break; } } }
      else { for (let x = xEnd; x >= xStart; x -= xStep) { if (lum(x, y) > 170) { pts.push([x, y]); break; } } }
    }
    if (pts.length < 10) return null;
    let sx=0, sy=0; pts.forEach(p=>{sx+=p[0];sy+=p[1];});
    sx/=pts.length; sy/=pts.length;
    let syy=0, sxy=0;
    pts.forEach(p=>{ syy+=(p[1]-sy)*(p[1]-sy); sxy+=(p[0]-sx)*(p[1]-sy); });
    if (syy < 1e-9) return null;
    return Math.atan(sxy/syy) * 180 / Math.PI; /* 0 = perfectly vertical */
  }
  const top = fitH(0, Math.floor(oh*0.4), 2, Math.floor(ow*0.08), Math.floor(ow*0.92), 4, true);
  const bot = fitH(Math.floor(oh*0.6), oh-1, 2, Math.floor(ow*0.08), Math.floor(ow*0.92), 4, false);
  const left = fitV(0, Math.floor(ow*0.4), 2, Math.floor(oh*0.08), Math.floor(oh*0.92), 4, true);
  const right = fitV(Math.floor(ow*0.6), ow-1, 2, Math.floor(oh*0.08), Math.floor(oh*0.92), 4, false);
  return { top: top, bot: bot, left: left, right: right };
}

function outDims(q) {
  const e = (a,b) => Math.hypot(a.x-b.x, a.y-b.y);
  const w = Math.max(e(q[0],q[1]), e(q[3],q[2]));
  const h = Math.max(e(q[0],q[3]), e(q[1],q[2]));
  const L = 600, s = L / Math.max(w, h);
  return [Math.max(1, Math.round(w*s)), Math.max(1, Math.round(h*s))];
}

const classes = ['clean', 'angled', 'rotated', 'lowcontrast', 'shadow'];
let fi = 0;
for (const cls of classes) {
  for (let k = 0; k < 3; k++) {
    const fx = makeFixture(cls), gt = fx.gt;
    /* test=detect: full still pipeline */
    const dq = T.detectQuad(fx.px, FW, FH);
    const iouD = polyIoU(dq, gt);
    const dd = outDims(dq);
    const outD = T.warpFn(fx.px, FW, FH, dq, dd[0], dd[1]);
    const mD = measureLevel(outD, dd[0], dd[1]);
    /* test=refine: perturb GT like a live-tracker quad, then capture-refine */
    const pq = gt.map(p => ({ x: p.x + rr(-10,10), y: p.y + rr(-10,10) }));
    const rq = T.refineCapture(fx.px, FW, FH, pq) || pq;
    const iouR = polyIoU(rq, gt);
    const rd = outDims(rq);
    const outR = T.warpFn(fx.px, FW, FH, rq, rd[0], rd[1]);
    const mR = measureLevel(outR, rd[0], rd[1]);
    console.log(JSON.stringify({ fixture: cls+'-'+k, test: 'detect', iou: +iouD.toFixed(3),
      edges: mD, maxDeg: maxAbs(mD) }));
    console.log(JSON.stringify({ fixture: cls+'-'+k, test: 'refine', iou: +iouR.toFixed(3),
      edges: mR, maxDeg: maxAbs(mR) }));
    fi++;
  }
}
function maxAbs(m) {
  const v = [m.top, m.bot, m.left, m.right].filter(x => x !== null).map(Math.abs);
  return v.length ? +Math.max(...v).toFixed(3) : null;
}
