#!/usr/bin/env python3
import sys, re, json; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean
from bs4 import BeautifulSoup

DEPTS = {"666": "Biology", "996": "Chemistry", "1441": "Mathematics",
         "1806": "Physics and Astronomy",
         "4816": "Electrical Engineering and Computer Science"}
KEEP_TITLE = re.compile(r"Professor|Lecturer|Instructor", re.I)
DROP_TITLE = re.compile(r"Emeritus|Postdoctoral|Postdoc", re.I)

profs, seen = [], set()
for tid in DEPTS:
    page = 0
    while True:
        url = (f"https://profiles.howard.edu/?search=&school=All&department={tid}"
               f"&type=All&page={page}")
        html = polite_get(url)
        soup = BeautifulSoup(html, "lxml")
        main = soup.find("main") or soup
        cards = [h for h in main.find_all(["h3", "h4"])
                 if h.find_next_sibling()]
        # entries are h3(name)/h4(title)/h5(dept) triples
        blocks = main.find_all("h3")
        got = 0
        for h3 in blocks:
            name = clean(h3.get_text(" "))
            h4 = h3.find_next_sibling("h4")
            h5 = h4.find_next_sibling("h5") if h4 else None
            if not h4 or not h5:
                continue
            title, dept = clean(h4.get_text(" ")), clean(h5.get_text(" "))
            if not KEEP_TITLE.search(title) or DROP_TITLE.search(title):
                continue
            name = re.sub(r",?\s*(Ph\.?D\.?|PHD|MS|M\.?S\.?|M\.?Ed\.?|Ed\.?D\.?|MD|J\.?D\.?)$",
                          "", name, flags=re.I).strip().rstrip(",")
            if len(name.split()) < 2 or len(name.split()) > 6:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            profs.append({"name": name, "title": title, "dept": dept, "courses": []})
            got += 1
        # pagination
        nxt = main.find("a", href=re.compile(r"page=%d\b" % (page + 1)))
        print(f"dept {tid} page {page}: {got} new")
        if nxt:
            page += 1
        else:
            break

# merge with existing EECS file
try:
    old = json.load(open("howard-university.json"))["professors"]
    for p in old:
        if p["name"].lower() not in seen:
            seen.add(p["name"].lower())
            profs.append(p)
    print("merged EECS:", len(old))
except FileNotFoundError:
    pass

print("total:", len(profs))
save_json("howard-university.json",
          {"college": "Howard University", "country": "US", "professors": profs})
