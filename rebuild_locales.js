/* Rebuild the 24 lazy locale JSONs after adding keys to js/i18n.js.
   - Executes the REAL js/i18n.js in a node vm sandbox (browser stubs) and
     runs its REAL keyHash() in situ (appended as window.__kh).
   - For each data/locales/<code>.json: keep every existing translation,
     fill MISSING keys with the English fallback (never overwrite real ones).
   - de gets real German translations from DE_OVERRIDES below.
   Usage: node rebuild_locales.js  (run from ~/workspace/hub) */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HUB = path.join(__dirname);
const SRC = fs.readFileSync(path.join(HUB, 'js/i18n.js'), 'utf8');

const DE_OVERRIDES = {
  'prof.dupProf': 'Dieser Professor ist bereits gelistet \u2014 suche nach ihm, um ihn zu bewerten.',
  'calc.entrySub': 'Wissenschaftlicher + grafischer Taschenrechner',
};

/* minimal browser stubs — i18n.js only touches these when functions are
   CALLED, but provide them anyway for safety */
const store = {};
const sandbox = {
  window: {},
  localStorage: {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: k => { delete store[k]; },
  },
  document: { documentElement: { setAttribute(){}, dir: '' }, querySelector(){ return null; } },
  fetch: () => Promise.reject(new Error('no fetch in rebuild')),
  navigator: { language: 'en-US' },
  console,
};
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(SRC, sandbox, { filename: 'i18n.js' });

const enDict = sandbox.window.HUB.i18n._dict('en');
const enKeys = Object.keys(enDict);
/* execute the REAL keyHash body from the file against the real DICT.en
   (never hand-computed, never a partial key list) */
const khBody = SRC.match(/function keyHash\(\)\{([\s\S]*?)\n\}/);
if (!khBody) { console.error('keyHash not found'); process.exit(1); }
const kh = new Function('DICT', khBody[1])({ en: enDict });
console.log('English keys:', enKeys.length, '| real kh:', kh);

const LOCALE_DIR = path.join(HUB, 'data/locales');
const files = fs.readdirSync(LOCALE_DIR).filter(f => f.endsWith('.json')).sort();
let fail = 0;
for (const f of files) {
  const code = f.slice(0, -5);
  const p = path.join(LOCALE_DIR, f);
  const payload = JSON.parse(fs.readFileSync(p, 'utf8'));
  const values = payload.values || {};
  let added = 0, overwritten = 0;
  for (const k of enKeys) {
    if (!(k in values)) {
      if (code === 'de' && k in DE_OVERRIDES) values[k] = DE_OVERRIDES[k];
      else values[k] = enDict[k];
      added++;
    }
  }
  /* safety: never drop keys, never shrink */
  const before = Object.keys(payload.values || {}).length;
  if (Object.keys(values).length < enKeys.length) {
    console.log('FAIL', code, 'still short:', Object.keys(values).length, 'vs', enKeys.length);
    fail++;
    continue;
  }
  fs.writeFileSync(p, JSON.stringify({ kh, v: 1, values }));
  console.log(`${code}: ${Object.keys(values).length} keys (+${added} new, ${before} kept)`);
}
if (fail) { console.error('FAILED locales:', fail); process.exit(1); }
console.log('done. kh=' + kh);
