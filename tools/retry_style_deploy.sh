#!/bin/bash
# Retry deploying the finished Style Closet build to hub-preview.surge.sh.
# The 2026-10-01 15:57 CDT attempt failed on Surge-side "Error - Deployment did
# not succeed" (throwaway probe domain failed identically -> not the project).
# Prints DEPLOYED_AND_VERIFIED only on full success; otherwise exits silently.
set -u
DONE=/tmp/style-deploy-done
[ -f "$DONE" ] && exit 0
HUB=/home/hatch/workspace/hub
STASH=/home/hatch/workspace/png-stash-style3
mkdir -p "$STASH"
cd "$HUB" || exit 0

# keep the deploy small: stash QA screenshots out of the project
mv qa/*.png "$STASH"/ 2>/dev/null
RESTORE=1
restore_pngs(){ [ "$RESTORE" = "1" ] && mv "$STASH"/*.png qa/ 2>/dev/null; }
trap restore_pngs EXIT

# need a little /tmp headroom for the surge client
if ! df -h /tmp | awk 'NR==2{exit ($4 ~ /[0-9]+M/ && $4+0 < 50)}'; then
  exit 0
fi

deploy_once(){
  npx --yes surge@latest ./ hub-preview.surge.sh 2>&1 | tail -5
}
OUT=$(deploy_once)
echo "$OUT" | grep -qi "success" || OUT=$(deploy_once)   # one retry on transient failure
echo "$OUT" | grep -qi "success" || exit 0               # still failing -> silent, next run retries

# live-verify the exact files the Style Closet ships
for f in index.html js/style.js css/style.css; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 25 "https://hub-preview.surge.sh/$f")
  [ "$CODE" = "200" ] || exit 0
done

touch "$DONE"
echo "DEPLOYED_AND_VERIFIED"
