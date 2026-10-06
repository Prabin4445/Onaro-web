#!/usr/bin/env python3
"""qa_scane2e.py — END-TO-END scanner gate (the missing one).

Covers the full shutter->saved-page plumbing that component QA never
exercised together:
  Part 1: takePhoto path (EXIF/aspect) — photo-space re-detection gives a
          level (<=1deg), sharp (>=0.90x GT acutance) final page.
  Part 2: frameGrab path regression — level + sharp.
  Part 3: thumbnail helper — correct dims, unbiased, multi-pass.
  Part 4: filter chain — color/gray/bw/magic all produce sane output.
Static gates on js/scan.js:
  S1: EXIF orientation handled on takePhoto (imageOrientation from-image).
  S2: photo-space re-detection wired (finish(fc,isPhoto) + SCAN.detectQuad(fc)).
  S3: all three thumbnail sites use SCAN._thumb (no raw one-step downscale).
  S4: no double warp — cur.cv is only ever assigned raw pixels (mkItem/rotate).
"""
import json, subprocess, sys, os

HUB = os.path.expanduser('~/workspace/hub')
JS = os.path.join(HUB, 'js', 'scan.js')

passed, failed = 0, []
def check(name, cond, detail=''):
    global passed
    if cond:
        passed += 1
    else:
        failed.append(name + (': ' + detail if detail else ''))

# ---- run node driver ----
r = subprocess.run(['node', os.path.join(HUB, 'qa', 'scane2e_driver.js')],
                   capture_output=True, text=True, timeout=300)
check('driver runs', r.returncode == 0, r.stderr[:300])
results = {}
if r.returncode == 0:
    for line in r.stdout.strip().split('\n'):
        line = line.strip()
        if not line.startswith('{'):
            continue
        try:
            o = json.loads(line)
            results[(o.get('part'), o.get('name'))] = o
        except Exception as e:
            failed.append('driver json: %s' % e)

def get(part, name):
    return results.get((part, name), {})

# Part 1: takePhoto path
for nm in ('takePhoto-clean', 'takePhoto-angled'):
    o = get(1, nm)
    check('p1 %s detected' % nm, o.get('detected') is True, str(o))
    check('p1 %s level<=1deg' % nm,
          o.get('maxDeg') is not None and o['maxDeg'] <= 1.0, str(o))
    check('p1 %s acutance>=0.90' % nm,
          o.get('acutRatio') is not None and o['acutRatio'] >= 0.90, str(o))

# Part 2: frameGrab regression
o = get(2, 'frameGrab')
check('p2 frameGrab locked', o.get('locked') is True, str(o))
check('p2 frameGrab level<=1deg',
      o.get('maxDeg') is not None and o['maxDeg'] <= 1.0, str(o))
check('p2 frameGrab acutance>=0.90',
      o.get('acutRatio') is not None and o['acutRatio'] >= 0.90, str(o))

# Part 3: thumbnail helper
o = get(3, 'thumbnail')
check('p3 thumb dims 160w', o.get('w') == 160 and o.get('h') == 200, str(o))
check('p3 thumb unbiased', o.get('meanBias') is not None and abs(o['meanBias']) < 12, str(o))
check('p3 thumb multi-pass', o.get('differsFromOneStep') is True, str(o))

# Part 4: filter chain
o = get(4, 'filters')
means = o.get('means', {})
for f in ('color', 'gray', 'bw', 'magic'):
    m = means.get(f)
    check('p4 filter %s sane' % f, m is not None and 40 < m < 250, str(means))

# ---- static gates on scan.js ----
src = open(JS, encoding='utf-8').read()
check('S1 EXIF from-image', "imageOrientation:'from-image'" in src or 'imageOrientation: "from-image"' in src)
check('S2 finish isPhoto flag', 'function finish(fc,isPhoto)' in src)
check('S2 photo-space redetect', 'SCAN.detectQuad(fc)' in src)
check('S3 thumb pagesView', 'SCAN._thumb(p.cv,160)' in src)
check('S3 thumb previewPage', 'SCAN._thumb(p.cv,900)' in src)
check('S3 thumb pill', 'SCAN._thumb(SCAN.pages[n-1].cv,72)' in src)
check('S3 no old 160 one-step', '160/p.cv.width' not in src)
check('S3 no old 900 one-step', '900/p.cv.width' not in src)
check('S3 no old pill one-step', 'tw=72, thh=' not in src)
# S4: every .cv assignment must come from raw input (mkItem param or rotate of raw)
import re
cv_writes = re.findall(r'^\s*(?:\S+\s+)?(\w[\w.]*\.cv)\s*=\s*([^;]+);', src, re.M)
bad = []
for lhs, rhs in cv_writes:
    rhs_s = rhs.strip()
    # allowed: cv:cv in object literal is 'cv:cv' (no =), rotate assigns nc (raw-rotated)
    if lhs.endswith('.cv') and 'cur.cv' in lhs:
        if not rhs_s.startswith('nc'):
            bad.append('%s = %s' % (lhs, rhs_s))
check('S4 no warped writes to cur.cv', not bad, '; '.join(bad))

print('qa_scane2e: %d passed, %d failed' % (passed, len(failed)))
for f in failed:
    print('FAIL:', f)
sys.exit(1 if failed else 0)
