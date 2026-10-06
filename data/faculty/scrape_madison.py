#!/usr/bin/env python3
"""Madison Area Technical College directory -> madison-area-technical-college.json"""
import sys, re, time; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean
from bs4 import BeautifulSoup

BASE = "https://madisoncollege.edu/about/directory?name_title=a&page={}"
profs, seen = [], set()
page = 0
while True:
    html = polite_get(BASE.format(page))
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("table.cols-5 tbody tr")
    if not rows:
        break
    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue
        name = clean(tds[0].get_text(" ", strip=True).split("|")[0])
        name = re.sub(r"\s+", " ", name)
        title = clean(tds[1].get_text(" ", strip=True))
        dept = clean(tds[3].get_text(" ", strip=True))
        if not re.search(r"Instructor|Professor|Lecturer|Faculty", title, re.I):
            continue
        if "emerit" in title.lower():
            continue
        key = name.lower()
        if key in seen or not name:
            continue
        seen.add(key)
        profs.append({"name": name, "title": title, "dept": dept or "Madison College", "courses": []})
    # next page?
    nxt = soup.select_one('.pager a[rel="next"], .pager__item--next a')
    page += 1
    if not nxt:
        break
    if page > 400:
        break

print("pages:", page, "faculty:", len(profs))
save_json("madison-area-technical-college.json",
          {"college": "Madison Area Technical College", "country": "US",
           "professors": profs})
