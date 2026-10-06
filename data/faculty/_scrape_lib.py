#!/usr/bin/env python3
"""Polite scraping helper for the faculty pipeline."""
import json, re, time, urllib.parse
import requests

UA = "Onaro-FacultyBot/1.0 (+faculty directory research; contact: faculty-pipeline@onaro.app)"
_last = {}
_robots_cache = {}

class Blocked(Exception):
    def __init__(self, host, reason):
        self.host = host; self.reason = reason

def _robots_rules(host):
    """Fetch robots.txt with requests; return (disallows, allows) path patterns
    from the User-agent: * group. Manual parse: urllib.robotparser is flaky
    through this proxy."""
    if host in _robots_cache:
        return _robots_cache[host]
    dis, allow = [], []
    try:
        r = requests.get(f"https://{host}/robots.txt", timeout=15,
                         headers={"User-Agent": UA, "Connection": "close"})
        if r.status_code == 200:
            in_star = False
            for line in r.text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.lower().startswith("user-agent:"):
                    in_star = line.split(":", 1)[1].strip() == "*"
                    continue
                if not in_star:
                    continue
                low = line.lower()
                if low.startswith("disallow:"):
                    p = line.split(":", 1)[1].strip()
                    if p:
                        dis.append(p)
                elif low.startswith("allow:"):
                    p = line.split(":", 1)[1].strip()
                    if p:
                        allow.append(p)
    except Exception:
        pass
    _robots_cache[host] = (dis, allow)
    return dis, allow

def _rule_match(pattern, path):
    rx = ""
    for ch in pattern:
        if ch == "*":
            rx += ".*"
        elif ch == "$":
            rx += "$"
        else:
            rx += re.escape(ch)
    return re.match(rx, path) is not None

def _robots_allowed(host, url):
    path = urllib.parse.urlparse(url).path or "/"
    dis, allow = _robots_rules(host)
    best_d, best_a = -1, -1
    for p in dis:
        if _rule_match(p, path):
            best_d = max(best_d, len(p))
    for p in allow:
        if _rule_match(p, path):
            best_a = max(best_a, len(p))
    if best_d < 0 and best_a < 0:
        return True
    return best_a >= best_d

def polite_get(url, timeout=30):
    host = urllib.parse.urlparse(url).netloc
    if not _robots_allowed(host, url):
        raise Blocked(host, f"robots.txt disallows {url}")
    now = time.time()
    wait = 1.0 - (now - _last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    _last[host] = time.time()
    last_err = None
    for attempt in range(3):
        try:
            r = requests.get(url, headers={"User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml",
                "Connection": "close"}, timeout=timeout)
            break
        except requests.RequestException as e:
            last_err = e
            time.sleep(2 ** attempt)
    else:
        raise Blocked(host, f"request failed after retries: {last_err}")
    if r.status_code in (429, 403):
        raise Blocked(host, f"HTTP {r.status_code} on {url}")
    r.raise_for_status()
    return r.text

def save_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    print(f"saved {path}")

def clean(s):
    return re.sub(r"\s+", " ", (s or "").strip())
