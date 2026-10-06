#!/bin/bash
# Regenerate /tmp/keyhash.txt from the current js/i18n.js bundled English dict.
# The audit (/tmp/audit_locales.js) compares each lazy file's kh against this.
cd /home/hatch/workspace/hub || exit 1
node -e "
const fs=require('fs'),vm=require('vm');
const src=fs.readFileSync('js/i18n.js','utf8');
const sandbox={window:{},localStorage:{getItem:()=>null,setItem:()=>{}}};
sandbox.window.HUB=sandbox.HUB={};
vm.createContext(sandbox); vm.runInContext(src,sandbox);
const keys=Object.keys(sandbox.HUB.i18n._dict('en'));
const joined=keys.join('\n');
let h=5381;
for(let i=0;i<joined.length;i++) h=((h<<5)+h+joined.charCodeAt(i))>>>0;
fs.writeFileSync('/tmp/keyhash.txt', h.toString(36)+'\n');
console.log('keyhash:', h.toString(36), 'keys:', keys.length);
"
