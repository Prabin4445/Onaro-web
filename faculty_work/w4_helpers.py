"""Shared helpers for wave1-w4 faculty collection."""
import json, subprocess, time, re, random

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 Contact:faculty-data-research@onaro.app"
FAC_DIR = "/home/hatch/workspace/hub/data/faculty"
_last_host = [None]
_last_t = [0.0]

def fetch(url, host=None, min_gap=1.1):
    """Fetch a URL with curl, polite UA, >=1s gap per host. Returns (ok, text_or_error)."""
    global _last_host, _last_t
    h = host or re.sub(r'^https?://', '', url).split('/')[0]
    gap = min_gap - (time.time() - _last_t[0]) if _last_host[0] == h else 0
    if gap > 0:
        time.sleep(gap)
    r = subprocess.run(
        ["curl", "-sS", "-m", "30", "-A", UA, "-L", "--compressed", url],
        capture_output=True, text=True)
    _last_t[0] = time.time()
    _last_host[0] = h
    code = r.returncode
    if r.stderr:
        m = re.search(r'HTTP/(\S+)', r.stderr)
    out = r.stdout
    if not out:
        return False, "empty response: " + r.stderr[:120]
    if out.lstrip().startswith("<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01") or "Moved Permanently" in out[:200]:
        return False, "redirect page, empty"
    return True, out

def http_status(url):
    r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-m", "25",
                        "-A", UA, "-L", url], capture_output=True, text=True)
    return r.stdout.strip()

def write_file(slug, college, professors):
    path = f"{FAC_DIR}/{slug}.json"
    with open(path, "w") as f:
        json.dump({"college": college, "country": "US", "professors": professors}, f, indent=1, ensure_ascii=False)
    return path, len(professors)

def dedupe(profs):
    seen = set()
    out = []
    for p in profs:
        k = p["name"].lower().strip()
        if k and k not in seen:
            seen.add(k)
            out.append(p)
    return out

def norm_title(t):
    return " ".join(t.split())
