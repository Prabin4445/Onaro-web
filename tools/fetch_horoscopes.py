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
import json, sys, time, urllib.request, urllib.error, datetime, subprocess, os
import base64, hashlib

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

GH_REPO = "Prabin4445/Onaro-web"
GH_PATH = "data/horoscopes.json"

def _gh_api(method, path, body=None):
    """GitHub API via the custom.github vault surrogate (same mechanism as
    the Orbit Post repo tools): the stored token is injected by authd and
    never read, printed, or written to disk by this script."""
    sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
    from dynamic_credentials import add_surrogate_to_request, read_json_response
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request("https://api.github.com" + path, data=data,
                                 headers=headers, method=method)
    add_surrogate_to_request(req, "custom.github",
                             allowed_hosts=("api.github.com",))
    with urllib.request.urlopen(req, timeout=60) as resp:
        return read_json_response(resp)

def _git(*args):
    """git wrapper that NEVER raises: a timeout (flaky egress can hang a
    fetch for minutes) becomes a plain failure result, so a slow network
    can degrade the deploy path but never crash it. (First version crashed
    the 2026-10-15 midday run exactly this way.)"""
    try:
        return subprocess.run(["git"] + list(args), cwd=HUB,
                              capture_output=True, text=True,
                              timeout=DEPLOY_TIMEOUT)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, "", "git timeout")
    except Exception as e:
        return subprocess.CompletedProcess(args, 1, "", str(e))

def _remote_head_sha():
    """Current origin/master sha via anonymous fetch (repo is public), or
    None when the fetch fails."""
    rf = _git("fetch", "origin", "master")
    if rf.returncode != 0:
        return None
    rr = _git("rev-parse", "origin/master")
    return rr.stdout.strip() if rr.returncode == 0 else None

def deploy_via_api(msg):
    """Alternative deploy (added 2026-10-15): commit ONLY data/horoscopes.json
    onto origin/master through the Git Data API, authenticated by the vault
    surrogate. Exists because the cron sandbox has no git credentials, so
    `git push` fails there every night ('could not read Username') while
    plain HTTPS to api.github.com works. Returns the new commit sha, the
    string 'current' when remote already holds this exact file, or None."""
    try:
        content = open(OUT, "rb").read()
        blob_sha = hashlib.sha1(b"blob %d\0" % len(content) + content).hexdigest()
        ref = _gh_api("GET", "/repos/%s/git/ref/heads/master" % GH_REPO)
        head = ref["object"]["sha"]
        commit = _gh_api("GET", "/repos/%s/git/commits/%s" % (GH_REPO, head))
        tree_sha = commit["tree"]["sha"]
        # skip the commit entirely when remote already has this exact blob
        data_tree = None
        for e in _gh_api("GET", "/repos/%s/git/trees/%s" % (GH_REPO, tree_sha))["tree"]:
            if e["path"] == "data":
                data_tree = e["sha"]
        if data_tree:
            for e in _gh_api("GET", "/repos/%s/git/trees/%s" % (GH_REPO, data_tree))["tree"]:
                if e["path"] == "horoscopes.json" and e["sha"] == blob_sha:
                    print("deploy api: remote already holds this exact file")
                    return "current"
        blob = _gh_api("POST", "/repos/%s/git/blobs" % GH_REPO,
                       {"content": base64.b64encode(content).decode(),
                        "encoding": "base64"})
        tree = _gh_api("POST", "/repos/%s/git/trees" % GH_REPO,
                       {"base_tree": tree_sha,
                        "tree": [{"path": GH_PATH, "mode": "100644",
                                  "type": "blob", "sha": blob["sha"]}]})
        new_commit = _gh_api("POST", "/repos/%s/git/commits" % GH_REPO,
                             {"message": msg, "tree": tree["sha"],
                              "parents": [head]})
        _gh_api("PATCH", "/repos/%s/git/refs/heads/master" % GH_REPO,
                {"sha": new_commit["sha"], "force": False})
        print("deploy ok via GitHub API: commit %s" % new_commit["sha"][:12])
        return new_commit["sha"]
    except Exception as e:
        print("deploy api fallback failed: %s" % str(e)[:300])
        return None

def resync_local():
    """After an API deploy, local master and origin/master hold the same
    tree under different commit shas. Realign local master to origin/master
    ONLY when provably lossless:
    - every local-ahead commit touches just data/horoscopes.json,
    - the two HEAD trees are identical,
    - the working tree has no tracked changes besides data/horoscopes.json
      itself (and that file's content must match origin's blob exactly).
    Anything else: refuse and leave local git untouched."""
    try:
        remote = _remote_head_sha()
        if not remote:
            print("resync: fetch failed; leaving local git as-is")
            return
        local = _git("rev-parse", "HEAD").stdout.strip()
        if local == remote:
            return
        ahead = _git("log", "--format=%H", "origin/master..HEAD").stdout.split()
        for sha in ahead:
            files = _git("diff-tree", "--no-commit-id", "--name-only", "-r",
                         sha).stdout.split()
            if files != [GH_PATH]:
                print("resync: local commit %s touches %s; not realigning"
                      % (sha[:8], files))
                return
        lt = _git("rev-parse", "HEAD^{tree}").stdout.strip()
        rt = _git("rev-parse", "origin/master^{tree}").stdout.strip()
        if lt != rt:
            print("resync: trees differ; not realigning")
            return
        dirty = _git("status", "--porcelain").stdout.splitlines()
        for line in dirty:
            if line.startswith("??"):
                continue  # untracked: reset --hard never touches these
            path = line[3:].split(" -> ")[-1].strip()
            if path != GH_PATH:
                print("resync: uncommitted changes in %s; not realigning"
                      % path)
                return
            want = _git("rev-parse", "origin/master:" + GH_PATH).stdout.strip()
            content = open(OUT, "rb").read()
            have = hashlib.sha1(b"blob %d\0" % len(content) + content).hexdigest()
            if have != want:
                print("resync: working horoscopes.json differs from origin; "
                      "not realigning")
                return
        _git("reset", "--hard", "origin/master")
        print("resync: local master realigned to origin/master (%s)"
              % remote[:12])
    except Exception as e:
        print("resync skipped: %s" % str(e)[:200])

def deploy():
    """Publish the baked file; Cloudflare Pages auto-deploys onaro-web on
    push. Primary path: git commit + push. Fallback (2026-10-15): the same
    one-file commit via the GitHub API + vault surrogate, for environments
    with no git credentials (the cron sandbox). Replaces the pre-2026-10-06
    surge deploy path (Surge was abandoned)."""
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    msg = "Daily horoscope refresh: %s readings" % today
    _git("add", GH_PATH)
    rr = _git("diff", "--cached", "--quiet")
    if rr.returncode != 0:
        for a in range(DEPLOY_ATTEMPTS):
            rc = _git("commit", "-m", msg)
            if rc.returncode == 0:
                break
            out = ((rc.stdout or "") + (rc.stderr or "")).lower()
            if "nothing to commit" in out or \
               "no changes added to commit" in out:
                break  # already committed on an earlier attempt/run
            print("deploy attempt %d commit failed: %s"
                  % (a + 1, (rc.stderr or rc.stdout)[-300:]))
            time.sleep(10)
    # already published? (also heals the old 'nothing staged' false success:
    # an unpushed local commit must never count as deployed)
    remote = _remote_head_sha()
    local = _git("rev-parse", "HEAD").stdout.strip()
    if remote and remote == local:
        print("deploy: origin/master already at local HEAD; nothing to push")
        return True
    rp = _git("push", "origin", "HEAD")
    if rp.returncode == 0:
        print("deploy ok: pushed data/horoscopes.json for date=%s" % today)
        return True
    print("deploy: git push failed (%s); trying GitHub API fallback"
          % (rp.stderr or rp.stdout)[-200:].strip())
    res = deploy_via_api(msg)
    if res:
        resync_local()
        return True
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
