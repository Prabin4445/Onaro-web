#!/usr/bin/env node
/* Compute the i18n keyHash() exactly as js/i18n.js does, without a browser.
   Usage: node qa/kh_compute.js   -> prints base36 hash */
'use strict';
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync(__dirname + '/../js/i18n.js', 'utf8');
const sandbox = {
  console: console,
  // i18n.js only touches window/localStorage inside functions; load-time is pure.
  window: {},
  HUB: {},
};
vm.createContext(sandbox);
vm.runInContext(src, sandbox, {filename: 'i18n.js'});
const DICT = sandbox.HUB.i18n._dict('en');
const keys = Object.keys(DICT).join('\n');
let h = 5381;
for (let i = 0; i < keys.length; i++) h = (((h << 5) + h + keys.charCodeAt(i)) >>> 0);
console.log('en keys: ' + Object.keys(DICT).length);
console.log('kh: ' + h.toString(36));
