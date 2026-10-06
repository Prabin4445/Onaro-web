/* Headless QA driver: synthetic frames through CV.detectLive.
   Usage: node /tmp/camdet_driver.js  -> prints JSON per line. */
global.window = {};
const fs = require('fs');
eval(fs.readFileSync('/home/hatch/workspace/hub/js/scan.js', 'utf8'));
const T = window.HUB.scan._t;
if (!T || !T.detectLive) { console.log(JSON.stringify({fatal: 'detectLive missing'})); process.exit(1); }

/* deterministic LCG */
let _s = 123456789;
function rnd() { _s = (_s * 1103515245 + 12345) & 0x7fffffff; return _s / 0x7fffffff; }

function makeFrame(w, h) { return { w, h, px: new Uint8ClampedArray(w * h * 4) }; }
function fillBG(fr, r, g, b) {
  for (let i = 0; i < fr.w * fr.h; i++) { fr.px[i*4]=r; fr.px[i*4+1]=g; fr.px[i*4+2]=b; fr.px[i*4+3]=255; }
}
function inPoly(x, y, q) {
  let inside = false;
  for (let i = 0, j = 3; i < 4; j = i++) {
    const xi=q[i].x, yi=q[i].y, xj=q[j].x, yj=q[j].y;
    if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) inside = !inside;
  }
  return inside;
}
function drawPoly(fr, q, r, g, b) {
  for (let y = 0; y < fr.h; y++) for (let x = 0; x < fr.w; x++)
    if (inPoly(x + .5, y + .5, q)) { const o=(y*fr.w+x)*4; fr.px[o]=r; fr.px[o+1]=g; fr.px[o+2]=b; }
}
/* rotated rect centered at (cx,cy), width rw, height rh, rotation deg */
function paperQuad(cx, cy, rw, rh, deg) {
  const a = deg * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
  return [{x:-rw/2,y:-rh/2},{x:rw/2,y:-rh/2},{x:rw/2,y:rh/2},{x:-rw/2,y:rh/2}]
    .map(p => ({ x: cx + p.x*c - p.y*s, y: cy + p.x*s + p.y*c }));
}
function addNoise(fr, amt) {
  for (let i = 0; i < fr.w * fr.h; i++) {
    const n = (rnd() - .5) * amt, o = i*4;
    for (let ch = 0; ch < 3; ch++) { let v = fr.px[o+ch] + n; fr.px[o+ch] = v<0?0:(v>255?255:v); }
  }
}
function polyIoU(a, b, w, h) {
  let inter = 0, union = 0;
  for (let y = 0; y < h; y += 3) for (let x = 0; x < w; x += 3) {
    const ia = inPoly(x, y, a), ib = inPoly(x, y, b);
    if (ia && ib) inter++; if (ia || ib) union++;
  }
  return union ? inter / union : 0;
}
function quadAspect(q) {
  const L = [];
  for (let i = 0; i < 4; i++) L.push(Math.hypot(q[i].x-q[(i+1)%4].x, q[i].y-q[(i+1)%4].y));
  return Math.max(...L) / Math.min(...L);
}
function touchesEdge(q, w, h) {
  const m = Math.min(w, h); /* mirrors the app's 1% touch-penalty zone */
  return q.some(p => p.x < m*.01 || p.x > w - m*.01 || p.y < m*.01 || p.y > h - m*.01);
}
function runFrames(fr, n, st) {
  st = st || { q: null, score: 0, lost: 0 };
  let r = null;
  for (let i = 0; i < n; i++) r = T.detectLive(fr.px, fr.w, fr.h, st);
  return { st, r };
}
const out = [];
function check(name, cond, detail) { out.push({ name, pass: !!cond, detail: detail || '' }); }

/* ---- 1-5: paper at rotations/positions/aspects ---- */
const W = 320, H = 568;
function paperCase(name, deg, cxr, cyr, areaFrac, aspect) {
  const fr = makeFrame(W, H); fillBG(fr, 52, 54, 58);
  const area = W * H * areaFrac;
  let rh = Math.sqrt(area / aspect), rw = rh * aspect;
  /* the sheet must actually fit inside the frame (a real user frames it fully):
     account for rotation swing of the corners, not just the unrotated size */
  const a = deg * Math.PI / 180, ca = Math.abs(Math.cos(a)), sa = Math.abs(Math.sin(a));
  const hx0 = (rw / 2) * ca + (rh / 2) * sa, hy0 = (rw / 2) * sa + (rh / 2) * ca;
  const cx = W * cxr, cy = H * cyr, mg = 6;
  const s2 = Math.min(1, (cx - mg) / hx0, (W - mg - cx) / hx0, (cy - mg) / hy0, (H - mg - cy) / hy0);
  rw *= s2; rh *= s2;
  const gt = paperQuad(cx, cy, rw, rh, deg);
  drawPoly(fr, gt, 244, 243, 240); addNoise(fr, 14);
  if (process.env.DBG_CASE === name) {
    const d = T.dbgLive(fr.px, W, H);
    console.log('DBG ' + name + ' ed=' + d.edgeDens + ' lines=' + d.nLines + ' cands=' + d.nCands + ' kept=' + d.kept.length + ' rej=' + JSON.stringify(d.rej));
    console.log('DBG topLines=' + JSON.stringify(d.topLines));
    d.kept.slice(0, 4).forEach((k, i) => console.log('DBG kept' + i + ' s=' + k.s.toFixed(3) + ' ' + JSON.stringify(k.parts)));
  }
  const t0 = Date.now();
  const { st, r } = runFrames(fr, 6);
  const ms = (Date.now() - t0) / 6;
  const iou = st.q ? polyIoU(st.q, gt, W, H) : 0;
  const asp = st.q ? quadAspect(st.q) : 0;
  check(name + ' locks (not guide)', !r.guide && !!st.q, 'guide=' + r.guide);
  check(name + ' IoU>0.85', iou > 0.85, 'iou=' + iou.toFixed(3));
  check(name + ' aspect paper-like', asp > 1.12 && asp < 1.85, 'aspect=' + asp.toFixed(3));
  check(name + ' no edge touch', st.q ? !touchesEdge(st.q, W, H) : false, '');
  return { ms, iou };
}
let tSum = 0, tN = 0;
[['p1 rot8 center A4', 8, .5, .5, .5, 1.4142],
 ['p2 rot-14 offset A4', -14, .44, .52, .45, 1.4142],
 ['p3 rot0 big A4', 0, .5, .48, .68, 1.4142],
 ['p4 rot20 small A4', 20, .55, .5, .18, 1.4142],
 ['p5 letter aspect', 6, .5, .5, .5, 1.2941],
].forEach(c => { const r = paperCase.apply(null, c); tSum += r.ms; tN++; });

/* landscape frame */
(function () {
  const w = 568, h = 320, fr = makeFrame(w, h); fillBG(fr, 52, 54, 58);
  const gt = paperQuad(w*.5, h*.5, 300, 300/1.4142, -6);
  drawPoly(fr, gt, 244, 243, 240); addNoise(fr, 14);
  if (process.env.DBG) {
    const d = T.dbgLive(fr.px, w, h);
    console.log('DBG p6 lines=' + d.nLines + ' cands=' + d.nCands + ' kept=' + d.kept.length + ' rej=' + JSON.stringify(d.rej));
    console.log('DBG p6 topLines=' + JSON.stringify(d.topLines));
    d.kept.slice(0, 6).forEach((k, i) => console.log('DBG p6 kept' + i + ' s=' + k.s.toFixed(3) + ' ' + JSON.stringify(k.parts)));
  }
  const { st, r } = runFrames(fr, 6);
  const iou = st.q ? polyIoU(st.q, gt, w, h) : 0;
  check('p6 landscape locks', !r.guide && !!st.q, '');
  check('p6 landscape IoU>0.85', iou > 0.85, 'iou=' + iou.toFixed(3));
})();

/* ---- 7: strong background edges must NOT win ---- */
(function () {
  const fr = makeFrame(W, H); fillBG(fr, 60, 58, 55);
  const gt = paperQuad(W*.5, H*.46, 190, 190/1.4142, 5);
  drawPoly(fr, gt, 245, 244, 241);
  /* table edges: full-width horizontal bar + vertical bar (the wild-quad bait) */
  drawPoly(fr, [{x:0,y:40},{x:W,y:40},{x:W,y:58},{x:0,y:58}], 18, 18, 20);
  drawPoly(fr, [{x:20,y:0},{x:34,y:0},{x:34,y:H},{x:20,y:H}], 18, 18, 20);
  addNoise(fr, 12);
  const { st, r } = runFrames(fr, 6);
  const iou = st.q ? polyIoU(st.q, gt, W, H) : 0;
  check('p7 bg-edges: paper wins', !r.guide && iou > 0.85, 'iou=' + iou.toFixed(3));
  check('p7 bg-edges: winner not edge-touching', st.q ? !touchesEdge(st.q, W, H) : false, '');
})();

/* ---- 8: no-paper -> guide ---- */
(function () {
  const fr = makeFrame(W, H);
  for (let y = 0; y < H; y += 16) for (let x = 0; x < W; x += 16) {
    const v = 40 + rnd() * 60;
    drawPoly(fr, [{x,y},{x:x+16,y},{x:x+16,y:y+16},{x,y:y+16}], v, v, v+4);
  }
  addNoise(fr, 20);
  const { st, r } = runFrames(fr, 14);
  check('p8 no-paper shows guide', r.guide && !st.q, 'guide=' + r.guide);
  const g = T.guideRect(W, H);
  const ga = quadAspect(g);
  check('p8 guide is A4', Math.abs(ga - 1.4142) < 0.03, 'aspect=' + ga.toFixed(4));
})();

/* ---- 9: temporal stability — no jitter on identical frames ---- */
(function () {
  const fr = makeFrame(W, H); fillBG(fr, 52, 54, 58);
  const gt = paperQuad(W*.5, H*.5, 200, 200/1.4142, 7);
  drawPoly(fr, gt, 244, 243, 240); addNoise(fr, 14);
  const st = { q: null, score: 0, lost: 0 };
  let maxDrift = 0, prev = null;
  for (let i = 0; i < 8; i++) {
    T.detectLive(fr.px, W, H, st);
    if (prev && st.q) {
      let d = 0;
      for (let c = 0; c < 4; c++) d = Math.max(d, Math.hypot(st.q[c].x-prev[c].x, st.q[c].y-prev[c].y));
      if (i >= 2) maxDrift = Math.max(maxDrift, d);
    }
    prev = st.q ? st.q.map(p => ({x:p.x, y:p.y})) : null;
  }
  check('p9 stable (drift<5px)', maxDrift < 5, 'maxDrift=' + maxDrift.toFixed(2));
})();

/* ---- 10: loss -> freeze, then guide (never snaps to garbage) ---- */
(function () {
  const fr = makeFrame(W, H); fillBG(fr, 52, 54, 58);
  const gt = paperQuad(W*.5, H*.5, 200, 200/1.4142, 4);
  drawPoly(fr, gt, 244, 243, 240); addNoise(fr, 14);
  const st = { q: null, score: 0, lost: 0 };
  runFrames(fr, 6, st);
  const locked = st.q.map(p => ({x:p.x, y:p.y}));
  /* wild frame: strong full-frame border edges, no paper */
  const wf = makeFrame(W, H); fillBG(wf, 52, 54, 58);
  drawPoly(wf, [{x:2,y:2},{x:W-2,y:2},{x:W-2,y:H-2},{x:2,y:H-2}], 52, 54, 58);
  for (let x = 0; x < W; x += 3) { /* border stripes */
    let o = (2*W+x)*4; wf.px[o]=wf.px[o+1]=wf.px[o+2]=200;
    o = ((H-3)*W+x)*4; wf.px[o]=wf.px[o+1]=wf.px[o+2]=200;
  }
  for (let i = 0; i < 3; i++) T.detectLive(wf.px, W, H, st);
  let move = 0;
  if (st.q) for (let c = 0; c < 4; c++)
    move = Math.max(move, Math.hypot(st.q[c].x-locked[c].x, st.q[c].y-locked[c].y));
  check('p10 loss freezes (no snap)', !!st.q && move < 30, 'move=' + move.toFixed(1));
  for (let i = 0; i < 12; i++) T.detectLive(wf.px, W, H, st);
  check('p10 long loss -> guide', !st.q, '');
})();

/* ---- 11: still-photo path untouched ---- */
(function () {
  const fr = makeFrame(W, H); fillBG(fr, 52, 54, 58);
  drawPoly(fr, paperQuad(W*.5, H*.5, 200, 200/1.4142, 5), 244, 243, 240);
  addNoise(fr, 14);
  const q = T.detectQuad(fr.px, W, H);
  check('p11 legacy detectQuad intact', q && q.length === 4, '');
})();

check('perf avg ms/frame < 120', (tSum / tN) < 120, 'avg=' + (tSum/tN).toFixed(1) + 'ms');

out.forEach(o => console.log(JSON.stringify(o)));
