#!/usr/bin/env python3
"""Fetch EIA weekly retail fuel prices from the public bulk file (no API key)
and bake them into data/gas_avg.json for the Onaro Daily tab.

Source: U.S. Energy Information Administration, PET.zip bulk file
(https://api.eia.gov/bulk/PET.zip) — official weekly retail gasoline/diesel
prices. EIA publishes gasoline weekly for 9 states + 5 PADD regions + U.S.;
diesel for CA + PADDs + U.S. Every state resolves to the most specific level
available (state -> PADD -> U.S.) and the JSON records which, so the app can
label the average honestly (e.g. "Texas avg" vs "Gulf Coast avg").

Runs weekly via cron; the app reads data/gas_avg.json same-origin
(no CORS, no key in the client).
"""
import datetime
import io
import json
import os
import urllib.request
import zipfile

PET_ZIP_URL = "https://api.eia.gov/bulk/PET.zip"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "gas_avg.json")

GRADE_CODES = {"regular": "EPMR", "midgrade": "EPMM", "premium": "EPMP"}
PADD_NAMES = {"R10": "East Coast", "R20": "Midwest", "R30": "Gulf Coast",
              "R40": "Rocky Mountain", "R50": "West Coast"}
STATE_PADD = {
    "ME": "R10", "NH": "R10", "VT": "R10", "MA": "R10", "RI": "R10",
    "CT": "R10", "NY": "R10", "NJ": "R10", "PA": "R10", "DE": "R10",
    "MD": "R10", "DC": "R10", "VA": "R10", "WV": "R10", "NC": "R10",
    "SC": "R10", "GA": "R10", "FL": "R10",
    "WI": "R20", "MI": "R20", "IL": "R20", "IN": "R20", "OH": "R20",
    "KY": "R20", "TN": "R20", "MN": "R20", "IA": "R20", "MO": "R20",
    "ND": "R20", "SD": "R20", "NE": "R20", "KS": "R20", "OK": "R20",
    "TX": "R30", "LA": "R30", "AR": "R30", "MS": "R30", "AL": "R30",
    "NM": "R30",
    "MT": "R40", "ID": "R40", "WY": "R40", "UT": "R40", "CO": "R40",
    "WA": "R50", "OR": "R50", "CA": "R50", "NV": "R50", "AZ": "R50",
    "AK": "R50", "HI": "R50",
}
STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "Dist. of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana",
    "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}


def candidate_ids(st):
    """Most-specific-first series IDs for one state: state, PADD, U.S."""
    cands = []
    for grade, code in GRADE_CODES.items():
        cands.append(("PET.EMM_%s_PTE_S%s_DPG.W" % (code, st), grade))
    cands.append(("PET.EMD_EPD2D_PTE_S%s_DPG.W" % st, "diesel"))
    padd = STATE_PADD.get(st)
    if padd:
        for grade, code in GRADE_CODES.items():
            cands.append(("PET.EMM_%s_PTE_%s_DPG.W" % (code, padd), grade))
        cands.append(("PET.EMD_EPD2D_PTE_%s_DPG.W" % padd, "diesel"))
    for grade, code in GRADE_CODES.items():
        cands.append(("PET.EMM_%s_PTE_NUS_DPG.W" % code, grade))
    cands.append(("PET.EMD_EPD2D_PTE_NUS_DPG.W", "diesel"))
    return cands


def main():
    want = {}
    for st in STATE_PADD:
        for sid, grade in candidate_ids(st):
            want.setdefault(sid, []).append((st, grade))
    found = {}
    req = urllib.request.Request(PET_ZIP_URL, headers={"User-Agent": "OnaroApp/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        blob = r.read()
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        with z.open(z.namelist()[0]) as f:
            for raw in f:
                try:
                    line = raw.decode("utf-8", "ignore")
                except Exception:
                    continue
                if '"series_id"' not in line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                sid = obj.get("series_id")
                if sid in want and sid not in found:
                    data = obj.get("data") or []
                    if data:
                        found[sid] = (data[0][0], float(data[0][1]))
    states, week = {}, None
    for st in STATE_PADD:
        entry, levels = {}, {}
        for sid, grade in candidate_ids(st):
            if grade in entry or sid not in found:
                continue
            date, val = found[sid]
            week = week or date
            entry[grade] = round(val, 3)
            if "_S%s_" % st in sid:
                levels[grade] = ("state", STATE_NAMES[st])
            elif any("_%s_" % p in sid for p in PADD_NAMES):
                padd = next(p for p in PADD_NAMES if "_%s_" % p in sid)
                levels[grade] = ("padd", PADD_NAMES[padd])
            else:
                levels[grade] = ("us", "U.S.")
        if entry:
            states[st] = {"prices": entry,
                          "levels": {g: {"level": lv, "region": rg}
                                     for g, (lv, rg) in levels.items()}}
    payload = {
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "week_ending": week,
        "source": "U.S. Energy Information Administration, weekly retail prices",
        "states": states,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(payload, f)
    print("wrote %s: %d states, week_ending=%s" % (OUT, len(states), week))
    if not states or len(states) < 50:
        print("REFUSING: incomplete payload")
        raise SystemExit(1)
    # deploy so phones get this week's file
    import subprocess
    hub = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run(["npx", "--yes", "surge@latest", "./", "hub-preview.surge.sh"],
                       cwd=hub, capture_output=True, text=True, timeout=180)
    print(r.stdout[-200:] if r.returncode == 0 else r.stderr[-500:])
    raise SystemExit(0 if r.returncode == 0 else 2)


if __name__ == "__main__":
    main()
