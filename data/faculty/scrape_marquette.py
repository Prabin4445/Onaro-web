#!/usr/bin/env python3
"""Marquette University college directories -> marquette-university.json"""
import sys, re; sys.path.insert(0, '.')
from _scrape_lib import polite_get, save_json, clean
from bs4 import BeautifulSoup

SOURCES = [
    ("https://www.marquette.edu/civil-construction-environmental-engineering/directory/", "Department of Civil, Construction and Environmental Engineering"),
    ("https://www.marquette.edu/electrical-computer-engineering/directory/", "Department of Electrical and Computer Engineering"),
    ("https://www.marquette.edu/mechanical-engineering/directory/", "Department of Mechanical Engineering"),
    ("https://mcw.marquette.edu/biomedical-engineering/directory/index.php", "Joint Department of Biomedical Engineering"),
    ("https://www.marquette.edu/business/directory/", "College of Business Administration"),
    ("https://www.marquette.edu/nursing/directory/index.php?dept=Faculty", "College of Nursing"),
    ("https://www.marquette.edu/education/directory/", "College of Education"),
]

profs, seen = [], set()
def add(name, title, dept):
    name = clean(re.sub(r"\s+", " ", name))
    title = clean(re.sub(r"\s+", " ", title))
    name = re.sub(r"^(Dr|Mr|Mrs|Ms|Miss)\.\s+", "", name)
    if not name or not re.search(r"Professor|Instructor|Lecturer", title, re.I):
        return
    if "emerit" in title.lower():
        return
    key = name.lower()
    if key in seen:
        return
    seen.add(key)
    profs.append({"name": name, "title": title, "dept": dept, "courses": []})

for url, dept in SOURCES:
    html = polite_get(url)
    soup = BeautifulSoup(html, "lxml")
    n = 0
    for span in soup.find_all("span", class_="title"):
        a = span.find_previous_sibling("a")
        if not a:
            continue
        add(a.get_text(" ", strip=True), span.get_text(" ", strip=True), dept)
        n += 1
    print(dept, "entries scanned:", n)

print("faculty:", len(profs))
save_json("marquette-university.json",
          {"college": "Marquette University", "country": "US",
           "professors": profs})
