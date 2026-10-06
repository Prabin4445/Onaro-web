/* Fixture generator + IoU measurement driver for the rebuilt scanner detection.
   Renders synthetic document photos (perspective, rotation, lighting, textured
   backgrounds, plus no-paper adversarial scenes), runs CV.detectLive /
   CV.detectQuad on them, measures polygon IoU vs ground truth, saves PNGs
   (flat under qa/ so the deploy PNG-stash catches them) + truth JSON.

   Usage: node qa/scandet2_driver.js   -> prints JSON per line + writes fixtures
*/
global.window = {};
const fs = require('fs'), zlib = require('zlib'), path = require('path');
const HUB = '/home/hatch/workspace/hub';
eval(fs.readFileSync(path.join(HUB, 'js', 'scan.js'), 'utf8'));
const T = window.HUB.scan._t;
if (!T || !T.detectLive) { console.log(JSON.stringify({fatal: 'detectLive missing'})); process.exit(1); }

/* deterministic LCG */
let _s = 20261001;
function rnd() { _s = (_s * 1103515245 + 12345) & 0x7fffffff; return _s / 0x7fffffff; }
function rr(a, b) { return a + rnd() * (b - a); }

const FW = 320, FH = 568;
function makeFrame() { return new Uint8ClampedArray(FW * FH * 4); }
function setPx(px, x, y, r, g, b) {
  if (x < 0 || y < 0 || x >= FW || y >= FH) return;
  const o = (y * FW + x) * 4; px[o] = r; px[o + 1] = g; px[o + 2] = b; px[o + 3] = 255;
}

/* ---------- paper texture (with text lines for interior-edge realism) ---------- */
function paperTexture(pw, ph, dense) {
  const px = new Uint8ClampedArray(pw * ph * 4);
  for (let i = 0; i < pw * ph; i++) { px[i*4] = 246; px[i*4+1] = 244; px[i*4+2] = 239; px[i*4+3] = 255; }
  function bar(x, y, w, h, v) {
    for (let yy = 0; yy < h; yy++) for (let xx = 0; xx < w; xx++) {
      const ox = x + xx, oy = y + yy;
      if (ox < 0 || oy < 0 || ox >= pw || oy >= ph) continue;
      const o = (oy * pw + ox) * 4; px[o] = v; px[o+1] = v; px[o+2] = v + 2;
    }
  }
  bar(28, 24, pw - 56, 15, 42);                       /* title bar */
  bar(28, 46, Math.round((pw - 56) * 0.55), 6, 90);    /* subtitle */
  let y = 66; const n = dense ? 40 : 24;
  for (let l = 0; l < n; l++) {
    const wdt = (l % 6 === 5) ? rr(0.25, 0.45) : rr(0.7, 0.96);
    bar(28, Math.round(y), Math.round((pw - 56) * wdt), 5, 62);
    y += 12.5;
    if (y > ph - 24) break;
  }
  for (let i = 0; i < pw * ph; i++) {                  /* paper grain */
    const nz = (rnd() - .5) * 7;
    for (let c = 0; c < 3; c++) { let v = px[i*4+c] + nz; px[i*4+c] = v < 0 ? 0 : (v > 255 ? 255 : v); }
  }
  return { w: pw, h: ph, px: px };
}

/* ---------- homography helpers ---------- */
function solveH(src, dst) {
  const A = [], B = [];
  for (let i = 0; i < 4; i++) {
    const sx = src[i].x, sy = src[i].y, dx = dst[i].x, dy = dst[i].y;
    A.push([sx, sy, 1, 0, 0, 0, -dx*sx, -dx*sy]); B.push(dx);
    A.push([0, 0, 0, sx, sy, 1, -dy*sx, -dy*sy]); B.push(dy);
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
function sampleBilinear(px, pw, ph, x, y) {
  let x0 = Math.floor(x), y0 = Math.floor(y);
  const fx = x - x0, fy = y - y0;
  x0 = Math.max(0, Math.min(pw - 2, x0)); y0 = Math.max(0, Math.min(ph - 2, y0));
  const o00 = (y0*pw+x0)*4, o10 = o00+4, o01 = o00+pw*4, o11 = o01+4;
  const a = (1-fx)*(1-fy), b = fx*(1-fy), c = (1-fx)*fy, d = fx*fy;
  return [px[o00]*a+px[o10]*b+px[o01]*c+px[o11]*d,
          px[o00+1]*a+px[o10+1]*b+px[o01+1]*c+px[o11+1]*d,
          px[o00+2]*a+px[o10+2]*b+px[o01+2]*c+px[o11+2]*d];
}

/* ---------- backgrounds ---------- */
function paintBG(px, kind) {
  for (let y = 0; y < FH; y++) for (let x = 0; x < FW; x++) {
    let r, g, b;
    if (kind === 'wood') {
      const band = Math.sin(y * 0.11 + Math.sin(x * 0.021) * 3) * 14 + Math.sin(y * 0.031) * 10;
      r = 108 + band; g = 74 + band * 0.7; b = 46 + band * 0.5;
    } else if (kind === 'carpet') {
      const nz = (rnd() - .5) * 46;
      r = 74 + nz; g = 72 + nz; b = 80 + nz;
    } else if (kind === 'checker') {
      const c = ((x >> 5) + (y >> 5)) & 1;
      r = c ? 86 : 52; g = c ? 84 : 50; b = c ? 88 : 54;
    } else { /* plain */
      const v = 58 - y * 0.03;
      r = v; g = v + 1; b = v + 3;
    }
    const o = (y * FW + x) * 4; px[o] = r; px[o+1] = g; px[o+2] = b; px[o+3] = 255;
  }
  if (kind === 'carpet' || kind === 'wood') return;
  for (let i = 0; i < FW * FH; i++) {
    const nz = (rnd() - .5) * 8, o = i * 4;
    for (let c = 0; c < 3; c++) { let v = px[o+c] + nz; px[o+c] = v < 0 ? 0 : (v > 255 ? 255 : v); }
  }
}

/* ---------- grille scene (PraBin's equipment-case mimic, NO paper) ---------- */
function paintGrilleScene(px) {
  for (let y = 0; y < FH; y++) for (let x = 0; x < FW; x++) {
    const o = (y * FW + x) * 4; px[o] = 46; px[o+1] = 47; px[o+2] = 50; px[o+3] = 255;
  }
  function grille(cx, cy, R) {
    for (let y = Math.max(0, cy-R-2); y < Math.min(FH, cy+R+2); y++)
      for (let x = Math.max(0, cx-R-2); x < Math.min(FW, cx+R+2); x++) {
        const dx = x - cx, dy = y - cy, d = Math.sqrt(dx*dx + dy*dy);
        if (d < R) {
          const ring = Math.abs(d % 9 - 4.5) < 1.2;
          const spoke = Math.abs(((Math.atan2(dy, dx) * 180 / Math.PI) % 30 + 30) % 30 - 15) < 2;
          if (ring || spoke) { const o = (y*FW+x)*4; px[o] = 150; px[o+1] = 150; px[o+2] = 152; }
        }
      }
  }
  [[100,290],[205,290],[100,420],[205,420],[100,160],[205,160]].forEach(p => grille(p[0], p[1], 50));
  for (let x = 52; x < 62; x++) for (let y = 50; y < 520; y++) setPx(px, x, y, 170, 170, 172);
  for (let x = 250; x < 260; x++) for (let y = 50; y < 520; y++) setPx(px, x, y, 170, 170, 172);
  for (let y = 112; y < 120; y++) for (let x = 34; x < 280; x++) setPx(px, x, y, 160, 160, 162);
  for (let y = 486; y < 494; y++) for (let x = 34; x < 280; x++) setPx(px, x, y, 160, 160, 162);
  for (let i = 0; i < FW * FH; i++) {
    const nz = (rnd() - .5) * 16, o = i * 4;
    for (let c = 0; c < 3; c++) { let v = px[o+c] + nz; px[o+c] = v < 0 ? 0 : (v > 255 ? 255 : v); }
  }
}

/* ---------- composite paper over bg with lighting ---------- */
function lightFactor(x, y, lighting) {
  let f = 1;
  f *= 1 - 0.22 * (Math.pow((x / FW - .5) * 2, 2) + Math.pow((y / FH - .5) * 2, 2)) / 2; /* vignette */
  if (lighting === 'dim') f *= 0.55;
  else if (lighting === 'shadow') {
    const d = (x * 0.6 + y) / (FW * 0.6 + FH);          /* diagonal shadow band */
    const inSh = d > 0.3 && d < 0.62;
    const edge = Math.min(Math.abs(d - 0.3), Math.abs(d - 0.62));
    f *= inSh ? 0.45 + 0.55 * Math.min(1, edge / 0.06) : 1;
  }
  return Math.max(0.2, f);
}
function compositePaper(px, paper, dst, lighting) {
  const srcC = [{x:0,y:0},{x:paper.w,y:0},{x:paper.w,y:paper.h},{x:0,y:paper.h}];
  const I = inv3(solveH(srcC, dst));
  const x0 = Math.max(0, Math.floor(Math.min(dst[0].x, dst[1].x, dst[2].x, dst[3].x)));
  const x1 = Math.min(FW - 1, Math.ceil(Math.max(dst[0].x, dst[1].x, dst[2].x, dst[3].x)));
  const y0 = Math.max(0, Math.floor(Math.min(dst[0].y, dst[1].y, dst[2].y, dst[3].y)));
  const y1 = Math.min(FH - 1, Math.ceil(Math.max(dst[0].y, dst[1].y, dst[2].y, dst[3].y)));
  const i00=I[0][0],i01=I[0][1],i02=I[0][2],i10=I[1][0],i11=I[1][1],i12=I[1][2],i20=I[2][0],i21=I[2][1],i22=I[2][2];
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    const wq = i20*x + i21*y + i22;
    const sx = (i00*x + i01*y + i02) / wq, sy = (i10*x + i11*y + i12) / wq;
    if (sx < 0 || sy < 0 || sx > paper.w - 1 || sy > paper.h - 1) continue;
    const s = sampleBilinear(paper.px, paper.w, paper.h, sx, sy);
    const f = lightFactor(x, y, lighting), o = (y * FW + x) * 4;
    px[o] = s[0] * f; px[o+1] = s[1] * f; px[o+2] = s[2] * f;
  }
  /* lighting also affects the bare background */
  for (let y = 0; y < FH; y++) for (let x = 0; x < FW; x++) {
    const f = lightFactor(x, y, lighting);
    if (f >= 0.999) continue;
    const o = (y * FW + x) * 4;
    px[o] *= f; px[o+1] *= f; px[o+2] *= f;
  }
}
function cameraFinish(px) {
  const src = Buffer.from(px.buffer, px.byteOffset, px.byteLength);
  const tmp = Buffer.from(src);
  for (let y = 1; y < FH - 1; y++) for (let x = 1; x < FW - 1; x++) {
    let r = 0, g = 0, b = 0;
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      const o = ((y+dy) * FW + x+dx) * 4; r += tmp[o]; g += tmp[o+1]; b += tmp[o+2];
    }
    const o = (y * FW + x) * 4; px[o] = r/9; px[o+1] = g/9; px[o+2] = b/9;
  }
  for (let i = 0; i < FW * FH; i++) {
    const nz = (rnd() - .5) * 11, o = i * 4;
    for (let c = 0; c < 3; c++) { let v = px[o+c] + nz; px[o+c] = v < 0 ? 0 : (v > 255 ? 255 : v); }
  }
}

/* ---------- destination quads per class ---------- */
function baseRect(cx, cy, rw, rh) {
  return [{x:cx-rw/2,y:cy-rh/2},{x:cx+rw/2,y:cy-rh/2},{x:cx+rw/2,y:cy+rh/2},{x:cx-rw/2,y:cy+rh/2}];
}
function jitter(q, amt) {
  return q.map(p => ({x: p.x + rr(-amt, amt), y: p.y + rr(-amt, amt)}));
}
function rotateQ(q, cx, cy, deg) {
  const a = deg * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
  return q.map(p => ({x: cx + (p.x-cx)*c - (p.y-cy)*s, y: cy + (p.x-cx)*s + (p.y-cy)*c}));
}
/* shrink quad toward centroid until fully inside frame with margin */
function clampFit(q, mg) {
  const cx = (q[0].x+q[1].x+q[2].x+q[3].x)/4, cy = (q[0].y+q[1].y+q[2].y+q[3].y)/4;
  let s = 1;
  for (let it = 0; it < 40; it++) {
    let ok = true;
    for (const p of q) {
      const x = cx + (p.x - cx) * s, y = cy + (p.y - cy) * s;
      if (x < mg || x > FW - mg || y < mg || y > FH - mg) { ok = false; break; }
    }
    if (ok) break;
    s *= 0.96;
  }
  return q.map(p => ({x: cx + (p.x-cx)*s, y: cy + (p.y-cy)*s}));
}
function sizedRect(cx, cy, areaFrac, aspect) {
  const area = FW * FH * areaFrac;
  const rh = Math.sqrt(area / aspect), rw = rh * aspect;
  return baseRect(cx, cy, rw, rh);
}
function dstQuad(cls) {
  const cx = FW * rr(0.44, 0.56), cy = FH * rr(0.44, 0.54);
  let q;
  if (cls === 'clean') {
    q = jitter(sizedRect(cx, cy, rr(0.4, 0.55), 1.4142), 9);
    q = rotateQ(q, cx, cy, rr(-6, 6));
  } else if (cls === 'angled') {
    /* strong perspective: top edge pulled in (tilt) + rotation */
    q = sizedRect(cx, cy, rr(0.35, 0.5), 1.4142);
    const tilt = rr(0.6, 0.78);
    const ccx = (q[0].x+q[1].x+q[2].x+q[3].x)/4, ccy = (q[0].y+q[1].y+q[2].y+q[3].y)/4;
    q = q.map((p, i) => (i < 2) ? {x: ccx + (p.x-ccx)*tilt, y: ccy + (p.y-ccy)*rr(0.82,0.92)} : p);
    q = rotateQ(q, ccx, ccy, rr(-14, 14));
  } else if (cls === 'rotated') {
    q = jitter(sizedRect(cx, cy, rr(0.32, 0.45), 1.4142), 6);
    q = rotateQ(q, cx, cy, rnd() < 0.5 ? rr(28, 42) : rr(48, 62));
  } else if (cls === 'lowcontrast' || cls === 'shadow' || cls === 'textured') {
    q = jitter(sizedRect(cx, cy, rr(0.38, 0.52), 1.4142), 8);
    q = rotateQ(q, cx, cy, rr(-10, 10));
  } else if (cls === 'textheavy') {
    q = jitter(sizedRect(cx, cy, rr(0.4, 0.5), 1.4142), 7);
    q = rotateQ(q, cx, cy, rr(-8, 8));
  } else if (cls === 'partial') {
    q = sizedRect(FW * 0.62, FH * 0.5, 0.62, 1.4142);   /* runs off the right edge */
    q = rotateQ(q, FW*0.62, FH*0.5, 6);
    return q;                                            /* do NOT clamp: honesty test */
  }
  return clampFit(q, 8);
}

/* ---------- polygon IoU (grid rasterization) ---------- */
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
  for (let y = 1; y < FH; y += 2) for (let x = 1; x < FW; x += 2) {
    const ia = inPoly(x, y, a), ib = inPoly(x, y, b);
    if (ia && ib) inter++; if (ia || ib) union++;
  }
  return union ? inter / union : 0;
}

/* ---------- minimal PNG writer ---------- */
let _crcT = null;
function crc32(b) {
  if (!_crcT) { _crcT = new Int32Array(256);
    for (let n = 0; n < 256; n++) { let c = n;
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
      _crcT[n] = c; } }
  let c = 0xFFFFFFFF;
  for (let i = 0; i < b.length; i++) c = _crcT[(c ^ b[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}
function pngWrite(w, h, rgba) {
  const raw = Buffer.alloc((w * 4 + 1) * h);
  const src = Buffer.from(rgba.buffer, rgba.byteOffset, rgba.byteLength);
  for (let y = 0; y < h; y++) { raw[y*(w*4+1)] = 0; src.copy(raw, y*(w*4+1)+1, y*w*4, (y+1)*w*4); }
  const comp = zlib.deflateSync(raw, { level: 6 });
  function chunk(t, d) {
    const L = Buffer.alloc(4); L.writeUInt32BE(d.length);
    const T = Buffer.from(t, 'ascii'), C = Buffer.alloc(4);
    C.writeUInt32BE(crc32(Buffer.concat([T, d])));
    return Buffer.concat([L, T, d, C]);
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 6;
  return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]), chunk('IHDR', ihdr),
                        chunk('IDAT', comp), chunk('IEND', Buffer.alloc(0))]);
}

/* ---------- fixture plan ---------- */
const PLAN = [
  ['clean', 3, 'plain', 'normal', false],
  ['angled', 3, 'plain', 'normal', false],
  ['rotated', 2, 'plain', 'normal', false],
  ['lowcontrast', 2, 'plain', 'dim', false],
  ['shadow', 2, 'plain', 'shadow', false],
  ['textured', 3, null, 'normal', false],       /* bg cycles carpet/wood/checker */
  ['textheavy', 2, 'wood', 'normal', true],
  ['partial', 1, 'plain', 'normal', false],
];
const NOPAPER = [
  ['grille-nopaper', 'grille'],
  ['checker-nopaper', 'checker'],
  ['blank-nopaper', 'plain'],
];
const TEX_BG = ['carpet', 'wood', 'checker'];

const results = [], truth = {};
let fxN = 0;
function runDetect(px) {
  const st = { q: null, score: 0, lost: 0 };
  let r = null, ms = 0;
  for (let i = 0; i < 8; i++) {
    const t0 = Date.now();
    r = T.detectLive(px, FW, FH, st);
    ms += Date.now() - t0;
  }
  return { st: st, r: r, ms: ms / 8 };
}

for (const [cls, count, bg, lighting, dense] of PLAN) {
  for (let n = 0; n < count; n++) {
    const bgKind = bg || TEX_BG[n % TEX_BG.length];
    const px = makeFrame();
    paintBG(px, bgKind);
    const paper = paperTexture(300, 424, dense);
    const gt = dstQuad(cls);
    compositePaper(px, paper, gt, lighting);
    cameraFinish(px);
    const name = 'fixture-' + cls + '-' + n;
    const det = runDetect(px);
    if (process.env.DBG_FX === name) {
      const dc = T.dbgContours(px, FW, FH);
      console.error('DBG contours: n=' + dc.n + ' ' + JSON.stringify(dc.info));
      const d = T.dbgLive(px, FW, FH);
      console.error('DBG ' + name + ' ed=' + d.edgeDens + ' lines=' + d.nLines +
        ' cands=' + d.nCands + ' kept=' + d.kept.length + ' rej=' + JSON.stringify(d.rej));
      d.kept.slice(0, 4).forEach((k, i) => console.error('DBG kept' + i + ' s=' + k.s.toFixed(3) +
        ' fail=' + (k.parts.fail || '-') + ' q=' + k.q.map(p => '(' + p.x.toFixed(0) + ',' + p.y.toFixed(0) + ')').join('')));
      /* which candidates came close to ground truth, and why did they die? */
      const da = T.dbgAll(px, FW, FH);
      let bestIoU = 0, bestInfo = null, bestQ = null, bestSrc = '-';
      const bySrc = {};
      for (const k of da.kept) {
        const iu = polyIoU(k.q, gt);
        const sk = (k.src || '-').split(':')[0];
        if (!bySrc[sk]) bySrc[sk] = { n: 0, best: 0 };
        bySrc[sk].n++;
        if (iu > bySrc[sk].best) bySrc[sk].best = iu;
        if (iu > bestIoU) { bestIoU = iu; bestInfo = (k.s ? 's=' + k.s.toFixed(3) : 'FAIL:' + k.fail); bestQ = k.q; bestSrc = k.src || '-'; }
      }
      console.error('DBG best candidate IoU vs GT: ' + bestIoU.toFixed(3) + ' ' + bestInfo + ' src=' + bestSrc);
      console.error('DBG by source: ' + JSON.stringify(bySrc));
      if (bestQ) {
        console.error('DBG bestQ: ' + bestQ.map(p => '(' + p.x.toFixed(1) + ',' + p.y.toFixed(1) + ')').join(' '));
        console.error('DBG gt:    ' + gt.map(p => '(' + p.x.toFixed(1) + ',' + p.y.toFixed(1) + ')').join(' '));
      }
      const fails = {};
      for (const k of da.kept) if (k.fail && polyIoU(k.q, gt) > 0.5) fails[k.fail] = (fails[k.fail] || 0) + 1;
      console.error('DBG near-GT candidates by fail reason: ' + JSON.stringify(fails));
    }
    const iouLive = det.st.q ? polyIoU(det.st.q, gt) : 0;
    let iouStill = 0;
    try {
      const t0 = Date.now();
      const qs = T.detectQuad(px, FW, FH);
      const stillMs = Date.now() - t0;
      iouStill = qs && qs.length === 4 ? polyIoU(qs, gt) : 0;
      results.push({ name: name, cls: cls, bg: bgKind, lighting: lighting,
        locked: !!det.st.q, guide: det.r.guide, score: +det.st.score.toFixed(3),
        iouLive: +iouLive.toFixed(4), iouStill: +iouStill.toFixed(4),
        msLive: +det.ms.toFixed(1), msStill: stillMs, partial: cls === 'partial' });
    } catch (e) {
      results.push({ name: name, cls: cls, err: String(e).slice(0, 120) });
    }
    fs.writeFileSync(path.join(HUB, 'qa', name + '.png'), pngWrite(FW, FH, px));
    truth[name] = gt.map(p => [+p.x.toFixed(1), +p.y.toFixed(1)]);
    fxN++;
  }
}
for (const [name, kind] of NOPAPER) {
  const px = makeFrame();
  if (kind === 'grille') paintGrilleScene(px);
  else { paintBG(px, kind); cameraFinish(px); }
  const fxName = 'fixture-' + name;
  const det = runDetect(px);
  if (process.env.DBG_FX === fxName) {
    const d = T.dbgLive(px, FW, FH);
    console.error('DBG ' + fxName + ' ed=' + d.edgeDens + ' kept=' + d.kept.length + ' rej=' + JSON.stringify(d.rej));
    d.kept.slice(0, 3).forEach((k, i) => console.error('DBG kept' + i + ' s=' + k.s.toFixed(3) +
      ' q=' + k.q.map(p => '(' + p.x.toFixed(0) + ',' + p.y.toFixed(0) + ')').join('') +
      ' terms=' + JSON.stringify(k.parts.terms || {})));
  }
  results.push({ name: 'fixture-' + name, cls: 'nopaper', bg: kind,
    locked: !!det.st.q, guide: det.r.guide, score: +det.st.score.toFixed(3),
    pass: det.r.guide && !det.st.q, msLive: +det.ms.toFixed(1) });
  fs.writeFileSync(path.join(HUB, 'qa', 'fixture-' + name + '.png'), pngWrite(FW, FH, px));
  truth['fixture-' + name] = null;
  fxN++;
}
fs.writeFileSync(path.join(HUB, 'qa', 'fixture-truth.json'), JSON.stringify(truth));
results.forEach(r => console.log(JSON.stringify(r)));
console.error('fixtures written: ' + fxN);
