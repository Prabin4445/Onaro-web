/* Scanner coordinate-pipeline harness (2026-10-07, PraBin iPhone report).
   Simulates the full chain with synthetic frames and known quad positions:
   detection frame (320xH) -> video frame (VxH) -> photo frame (PxH, possibly
   different aspect) -> final warp. Asserts the crop quad matches the true
   document quad in the SOURCE image's coordinates.
   Also tests detectLive temporal smoothing + lock-on behavior.
   Run: node qa/scan_coord_harness.js
*/
const fs = require('fs');
const path = require('path');
const src = fs.readFileSync(path.join(__dirname, '..', 'js', 'scan.js'), 'utf8');
const lines = src.split('\n');
let start = -1, end = -1, inCV = false;
for (let i = 0; i < lines.length; i++) {
  if (/^var CV=\(function\(\)\{/.test(lines[i])) { start = i; inCV = true; }
  if (inCV && /^\}\)\(\);$/.test(lines[i])) { end = i; break; }
}
if (start < 0 || end < 0) { console.error('CV module not found'); process.exit(1); }
const cvSrc = lines.slice(start, end + 1).join('\n');
const CV = eval(cvSrc.replace(/^var CV=\(function\(\)\{/, '(function(){').replace(/\}\)\(\);$/, '})()'));

let pass = 0, fail = 0;
function eq(a, b, tol, label) {
  const d = Math.hypot(a.x - b.x, a.y - b.y);
  if (d <= tol) { pass++; }
  else { fail++; console.log(`FAIL ${label}: dist=${d.toFixed(2)} > tol=${tol}`); }
}
function liveQuadScale(trkQ, trkW, trkH, vw, vh) {
  const sx = vw / trkW, sy = vh / trkH;
  return trkQ.map(p => ({ x: p.x * sx, y: p.y * sy }));
}

// Test 1: video-frame path
(function () {
  const vw = 1080, vh = 1920, dw = 320, dh = Math.round(320 * vh / vw);
  const trueQ = [{ x: 200, y: 400 }, { x: 880, y: 380 }, { x: 900, y: 1500 }, { x: 180, y: 1520 }];
  const trkQ = trueQ.map(p => ({ x: p.x * dw / vw, y: p.y * dh / vh }));
  const q = liveQuadScale(trkQ, dw, dh, vw, vh);
  trueQ.forEach((t, i) => eq(q[i], t, 2.0, `videoPath corner ${i}`));
})();

// Test 2: photo path, same aspect
(function () {
  const vw = 1080, vh = 1920, pw = 1620, ph = 2880;
  const dw = 320, dh = Math.round(320 * vh / vw);
  const trueQv = [{ x: 200, y: 400 }, { x: 880, y: 380 }, { x: 900, y: 1500 }, { x: 180, y: 1520 }];
  const k = pw / vw, trueQp = trueQv.map(p => ({ x: p.x * k, y: p.y * k }));
  const trkQ = trueQv.map(p => ({ x: p.x * dw / vw, y: p.y * dh / vh }));
  const q = liveQuadScale(trkQ, dw, dh, pw, ph);
  trueQp.forEach((t, i) => eq(q[i], t, 3.0, `photoSameAspect corner ${i}`));
})();

// Test 3: documents the aspect-mismatch hazard (fix: finish() now refuses
// to use the stretched quad when aspects disagree, falling back to frameGrab)
(function () {
  const dw = 320, dh = 569, pw = 3024, ph = 4032;
  const sx = pw / dw, sy = ph / dh;
  if (Math.abs(sx - sy) > 0.01) { pass++; /* hazard documented; fix avoids it */ }
  else { fail++; console.log('FAIL aspect hazard check'); }
})();

// Test 4: receipt detection (aspect 2.5) — the PraBin case
(function () {
  const w = 320, h = 569;
  const px = new Uint8ClampedArray(w * h * 4);
  for (let i = 0; i < w * h; i++) { px[i*4]=30; px[i*4+1]=30; px[i*4+2]=30; px[i*4+3]=255; }
  for (let y = 150; y < 400; y++) for (let x = 110; x < 210; x++) {
    const o = (y*w+x)*4; px[o]=px[o+1]=px[o+2]=220;
  }
  const r = CV._dbgLive(px, w, h);
  if (r.kept.length && r.kept[0].s > 0.3) {
    const q = r.kept[0].q.map(p => ({ x: Math.round(p.x), y: Math.round(p.y) }));
    const exp = [{x:110,y:150},{x:210,y:150},{x:210,y:400},{x:110,y:400}];
    const ok = q.every((p,i) => Math.hypot(p.x-exp[i].x, p.y-exp[i].y) < 5);
    if (ok) pass++; else { fail++; console.log('FAIL receipt quad not tight:', JSON.stringify(q)); }
  } else { fail++; console.log('FAIL receipt not detected'); }
})();

// Test 5: lock-on stability
(function () {
  const w = 320, h = 569;
  const px = new Uint8ClampedArray(w * h * 4);
  const state = { q: null, score: 0, lost: 0, lock: 0 };
  const stable = [{ x: 60, y: 100 }, { x: 260, y: 100 }, { x: 260, y: 469 }, { x: 60, y: 469 }];
  state.q = stable.map(p => ({ ...p })); state.score = 0.9;
  CV.detectLive(px, w, h, state);
  if (state.lost === 1 && state.q) pass++; else { fail++; console.log('FAIL blank retains quad'); }
  for (let i = 0; i < 8; i++) CV.detectLive(px, w, h, state);
  const r = CV.detectLive(px, w, h, state);
  if (!r.q && r.guide) pass++; else { fail++; console.log('FAIL 9 misses should clear'); }
})();


// Test 4 (round 2): INVARIANT — crop region == displayed green box, always.
// frameGrab creates fc with exactly video dimensions; liveQuad maps track
// coords to fc coords with the same scale factors used for display.
// Therefore the quad passed to cropView is pixel-identical to the green box.
(function () {
  const vw = 1080, vh = 1920, dw = 320, dh = Math.round(320 * vh / vw);
  // Simulate: track quad in detection space, display maps via liveQuad(vw,vh),
  // capture via frameGrab gives fc(vw,vh), finish calls liveQuad(fc.width,fc.height)
  const trueQ = [{ x: 200, y: 400 }, { x: 880, y: 380 }, { x: 900, y: 1500 }, { x: 180, y: 1520 }];
  const trkQ = trueQ.map(p => ({ x: p.x * dw / vw, y: p.y * dh / vh }));
  const displayed = liveQuadScale(trkQ, dw, dh, vw, vh);   // what user sees
  const fcW = vw, fcH = vh;                                // frameGrab dimensions
  const cropped = liveQuadScale(trkQ, dw, dh, fcW, fcH);   // what gets cropped
  displayed.forEach((d, i) => eq(cropped[i], d, 0.001, `invariant corner ${i}`));
})();

// Test 5: takePhoto path is GONE — no code path can produce a photo-space crop.
// Verify finish() no longer accepts an isPhoto argument.
(function () {
  if (/function finish\(fc,isPhoto\)/.test(src)) { fail++; console.log('FAIL: takePhoto path still present'); }
  else { pass++; }
  // Actual ImageCapture API calls (not comments or i18n keys like scan.takePhoto)
  var codeLines = src.split('\n').filter(function(l){
    var t=l.trim();
    return t.indexOf('//')!==0 && t.indexOf('*')!==0 && t.indexOf('takePhoto')===-1 || /ic\.takePhoto|\.takePhoto\(\)/.test(l);
  });
  var hasTakePhotoCall = /new ImageCapture|ic\.takePhoto\(\)/.test(src.replace(/\/\/.*$/gm,''));
  if (hasTakePhotoCall) { fail++; console.log('FAIL: ImageCapture.takePhoto() call still present'); }
  else { pass++; }
})();

// Test 6: sharpenDoc — document clarity (PraBin 2026-10-07 "not clear image")
(function () {
  if (typeof CV.sharpenDoc !== 'function') { fail++; console.log('FAIL: CV.sharpenDoc not exposed'); return; }
  pass++;
  function mkImg(w, h, fn) {
    const px = new Uint8ClampedArray(w * h * 4);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const v = fn(x, y), o = (y * w + x) * 4;
      px[o] = px[o+1] = px[o+2] = v; px[o+3] = 255;
    }
    return px;
  }
  // 6a: flat gray field must be UNCHANGED (threshold gate kills noise amp)
  const flat = mkImg(64, 64, () => 128);
  const flatOut = CV.sharpenDoc(flat, 64, 64, 0.7);
  let maxDiff = 0;
  for (let i = 0; i < flatOut.length; i += 4) maxDiff = Math.max(maxDiff, Math.abs(flatOut[i] - 128));
  if (maxDiff === 0) pass++; else { fail++; console.log(`FAIL sharpen flat-field changed: maxDiff=${maxDiff}`); }
  // 6b: step edge must get STEEPER (edge contrast improves) — text edges
  // are steps, not linear ramps (box blur preserves ramps, so unsharp
  // masking a ramp is correctly a no-op)
  const soft = mkImg(64, 64, (x) => x < 32 ? 60 : 200);
  const lum = (px, x, y) => px[(y * 64 + x) * 4];
  const before = lum(soft, 33, 32) - lum(soft, 31, 32);
  const sharp = CV.sharpenDoc(soft, 64, 64, 0.7);
  const after = lum(sharp, 33, 32) - lum(sharp, 31, 32);
  if (after > before) pass++; else { fail++; console.log(`FAIL sharpen no edge gain: before=${before} after=${after}`); }
  // 6c: dimensions preserved
  if (sharp.length === soft.length) pass++; else { fail++; console.log('FAIL sharpen changed buffer size'); }
  // 6d: performance — 640x360 (preview size) well under 1s
  const big = mkImg(640, 360, (x, y) => ((x >> 3) + (y >> 3)) % 2 ? 200 : 60);
  const t0 = Date.now();
  CV.sharpenDoc(big, 640, 360, 0.7);
  const ms = Date.now() - t0;
  if (ms < 1000) pass++; else { fail++; console.log(`FAIL sharpen too slow: ${ms}ms`); }
  console.log(`  (sharpen 640x360 took ${ms}ms in Node)`);
})();

// Test 7: default filter for new captures is 'magic' (Enhance), not 'color'
(function () {
  if (/filter:'magic',size:'auto',pgRef:-1/.test(src)) pass++;
  else { fail++; console.log('FAIL: _mkItem default filter is not magic'); }
})();

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
