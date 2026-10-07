#!/bin/bash
# Retry deploy of the scanner sharpness fix to hub-preview.surge.sh.
# Exits quietly unless the deploy + live verification both succeed.
DONE=/tmp/sharp-deploy-done
HUB=~/workspace/hub
STASH=~/workspace/png-stash-sharp
MARKER="boxBlurMean"   # new code marker unique to the sharpness fix

[ -f "$DONE" ] && exit 0

# Egress check: if we can't reach the internet, stay silent and try next run.
curl -s -o /dev/null --max-time 15 https://www.google.com >/dev/null 2>&1 || exit 0

cd "$HUB" || exit 0
node --check js/scan.js >/dev/null 2>&1 || { echo "SYNTAX_FAIL"; exit 0; }
node --check js/degree.js >/dev/null 2>&1 || { echo "SYNTAX_FAIL_DEGREE"; exit 0; }

mkdir -p "$STASH"
mv qa/*.png "$STASH"/ 2>/dev/null

OK=0
for i in 1 2 3; do
  if npx --yes surge@latest ./ hub-preview.surge.sh 2>&1 | grep -q "Success!"; then OK=1; break; fi
  sleep 10
done

mv "$STASH"/*.png qa/ 2>/dev/null

[ "$OK" = "1" ] || exit 0
sleep 5
if curl -s --max-time 25 "https://hub-preview.surge.sh/js/scan.js" | grep -q "$MARKER" \
  && curl -s --max-time 25 "https://hub-preview.surge.sh/js/degree.js" | grep -q "normOptions" \
  && curl -s --max-time 25 "https://hub-preview.surge.sh/js/degree.js" | grep -q "normSemNumbers"; then
  touch "$DONE"
  echo "DEPLOYED_AND_VERIFIED"
else
  echo "DEPLOY_OK_VERIFY_FAIL"
fi
