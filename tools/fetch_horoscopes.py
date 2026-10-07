#!/usr/bin/env python3
"""Daily horoscope fetch with a fallback source lineup.

Tries each source in order until one delivers all 12 signs, then bakes them
into data/horoscopes.json (the app reads it same-origin; phones cannot call
the APIs directly because they send no CORS headers). Pushes to GitHub only
when the baked content actually changed (Cloudflare Pages auto-deploys on
push since the 2026-10-06 migration off Surge). Never invents readings: if no source
delivers all 12 signs, the old file is left untouched and the run exits
non-zero so the miss is reported honestly.

Robustness (added 2026-10-02 after a double failure: shell egress down AND
surge deploy down on 2026-10-02 00:19 CDT):
- fetch_one falls back to curl when urllib fails (the sandbox egress proxy
  intermittently kills urllib connections while curl succeeds).
- the idempotent skip now checks the LIVE file's date too: local-fresh but
  live-stale still deploys instead of skipping forever.
"""
import json, sys, time, urllib.request, datetime, subprocess, os

SIGNS = ["aries","taurus","gemini","cancer","leo","virgo","libra","scorpio",
         "sagittarius","capricorn","aquarius","pisces"]
HUB = os.path.expanduser("~/workspace/hub")
OUT = os.path.join(HUB, "data", "horoscopes.json")

REQ_TIMEOUT = 12        # seconds per HTTP request
ATTEMPTS = 2            # attempts per sign per source
BACKOFF = 5             # seconds between attempts
FETCH_DEADLINE = 240    # seconds max for the whole fetch phase
DEPLOY_ATTEMPTS = 2
DEPLOY_TIMEOUT = 180

T0 = time.monotonic()

def _parse_fhapi(payload):
    d = payload["data"]
    return d["date"], d["horoscope"]

def _parse_ohmanda(payload):
    return payload["date"], payload["horoscope"]

# Ordered lineup: first source to deliver all 12 signs wins. The file's
# `date` always comes from the winning source, so it is never invented.
SOURCES = [
    ("freehoroscopeapi",
     "https://freehoroscopeapi.com/api/v1/get-horoscope/daily?sign={sign}",
     _parse_fhapi),
    ("vercel-mirror",
     "https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily?sign={sign}&day=TODAY",
     _parse_fhapi),
    ("ohmanda",
     "https://ohmanda.com/api/horoscope/{sign}",
     _parse_ohmanda),
]

def fetch_one(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "OrbitApp/1.0"})
        with urllib.request.urlopen(req, timeout=REQ_TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        # Sandbox quirk (2026-10-01): the egress proxy intermittently kills
        # Python urllib connections while curl on the identical URL returns
        # 200. Fall back to curl before giving up on this URL.
        print("urllib failed (%s: %s); trying curl fallback" % (type(e).__name__, e))
    r = subprocess.run(["curl", "-s", "--max-time", str(REQ_TIMEOUT),
                        "-A", "OrbitApp/1.0", url],
                       capture_output=True, text=True, timeout=REQ_TIMEOUT + 5)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError("curl fallback failed: rc=%s err=%s"
                           % (r.returncode, (r.stderr or "")[:160]))
    return json.loads(r.stdout)

def live_date():
    """Date baked into the file currently served on the live preview.

    Returns the date string, or None if it cannot be determined. Used to
    avoid the stale-skip trap: local fresh + live stale must still deploy.
    """
    try:
        r = subprocess.run(
            ["curl", "-s", "--max-time", "15",
             "https://onaro-web.pages.dev/data/horoscopes.json"],
            capture_output=True, text=True, timeout=20)
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout).get("date")
    except Exception as e:
        print("live date check failed:", type(e).__name__, e)
    return None

def fetch_source(name, template, parse):
    signs, date = {}, None
    for s in SIGNS:
        if time.monotonic() - T0 > FETCH_DEADLINE:
            print("[%s] fetch deadline hit; giving up on this source" % name)
            return None
        url = template.format(sign=s)
        ok = False
        for a in range(ATTEMPTS):
            try:
                date_s, text = parse(fetch_one(url))
            except Exception as e:  # timeout, DNS, HTTP error, bad JSON, bad shape
                print("[%s] %s attempt %d failed: %s: %s"
                      % (name, s, a + 1, type(e).__name__, e))
            else:
                if text and len(text) >= 50 and date_s:
                    signs[s] = text
                    date = date or date_s
                    ok = True
                    break
                print("[%s] %s attempt %d: payload too short/empty" % (name, s, a + 1))
            if a < ATTEMPTS - 1:
                time.sleep(BACKOFF)
        if not ok:
            print("[%s] %s: all attempts failed" % (name, s))
            return None
    return date, signs

def deploy():
    """Publish the baked file: git commit + push; Cloudflare Pages
    auto-deploys the onaro-web.pages.dev site on push. Replaces the
    pre-2026-10-06 surge deploy path (Surge was abandoned)."""
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    subprocess.run(["git", "add", "data/horoscopes.json"], cwd=HUB,
                   capture_output=True, text=True, timeout=DEPLOY_TIMEOUT)
    rr = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=HUB,
                        capture_output=True, text=True, timeout=DEPLOY_TIMEOUT)
    if rr.returncode == 0:
        print("deploy: nothing staged; file unchanged")
        return True
    msg = "Daily horoscope refresh: %s readings" % today
    for a in range(DEPLOY_ATTEMPTS):
        rc = subprocess.run(["git", "commit", "-m", msg], cwd=HUB,
                            capture_output=True, text=True,
                            timeout=DEPLOY_TIMEOUT)
        if rc.returncode != 0:
            out = ((rc.stdout or "") + (rc.stderr or "")).lower()
            if "nothing to commit" not in out and \
               "no changes added to commit" not in out:
                print("deploy attempt %d commit failed: %s"
                      % (a + 1, (rc.stderr or rc.stdout)[-300:]))
                time.sleep(10)
                continue
            # already committed on an earlier attempt; just push
        rp = subprocess.run(["git", "push", "origin", "HEAD"], cwd=HUB,
                            capture_output=True, text=True,
                            timeout=DEPLOY_TIMEOUT)
        if rp.returncode == 0:
            print("deploy ok: pushed data/horoscopes.json for date=%s" % today)
            return True
        print("deploy attempt %d push failed: %s"
              % (a + 1, (rp.stderr or rp.stdout)[-300:]))
        time.sleep(10)
    return False

def main():
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    local_fresh = False
    try:
        old = json.load(open(OUT))
        old_signs = old.get("signs") or {}
        if old.get("date") == today and len(old_signs) == 12 \
                and all(len(v) >= 50 for v in old_signs.values()):
            local_fresh = True
    except Exception:
        pass  # missing/corrupt file: fetch below

    if local_fresh:
        # Stale-skip trap (2026-10-02): the local file can be fresh while the
        # live site still serves yesterday's file (e.g. a deploy failed after
        # the write). Only skip when the LIVE file is fresh too.
        ld = live_date()
        if ld == today:
            print("already fresh locally and live (date=%s); nothing to do" % today)
            return 0
        print("local fresh but live is stale (live date=%s); deploying" % ld)
        return 0 if deploy() else 2

    winner, result = None, None
    for name, template, parse in SOURCES:
        print("trying source:", name)
        result = fetch_source(name, template, parse)
        if result:
            winner = name
            break
        print("source failed:", name)
    if not result:
        print("REFUSING: no source delivered all 12 signs; keeping old file")
        return 1

    date, signs = result
    payload = {"date": date,
               "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "source": winner,
               "signs": signs}
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, OUT)
    print("wrote", OUT, "date=", date, "source=", winner)

    if deploy():
        return 0
    print("DATA WRITTEN BUT DEPLOY FAILED (exit 2): %s has date=%s; rerun to deploy"
          % (OUT, date))
    return 2

if __name__ == "__main__":
    sys.exit(main())
