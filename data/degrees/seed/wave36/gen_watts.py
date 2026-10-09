"""Wave 36: Watts College of Nursing (Durham, NC, private).
Official 2025-2026 Catalogue, CURRICULUM PLAN (pp. 31-32): 4 levels = 4 fifteen-week semesters of
nursing content, 60 credits, verified against the catalog's TOTAL FOR PROGRAM (60 credit hours).
Students transfer in 60 general-education credits prior to matriculation -> modeled as external_prereqs.
Source: https://wattscollegeofnursing.edu/sites/default/files/90021_Watts-College-of-Nursing-Catalogue-2025-26_9.10.25.pdf
"""
import json, os

OUT = os.path.dirname(os.path.abspath(__file__))
INST = {"name": "Watts College of Nursing", "city": "Durham, NC", "state": "NC", "kind": "private"}

def c(code, title, credits):
    return {"code": code, "title": title, "credits": credits, "category": "major",
            "choice": False, "options": [], "choice_note": "", "prereq": []}

def sem(n, label, courses):
    return {"n": n, "label": label, "courses": courses}

semesters = [
    sem(1, "Level 1", [
        c("NURS 3000", "Nursing Concepts I", 7),
        c("NURS 3100", "Nursing Health Assessment", 3),
        c("NURS 3200", "Nursing Pathophysiology", 3),
        c("NURS 3450", "Introduction to Professional Nursing", 2)]),
    sem(2, "Level 2", [
        c("NURS 3500", "Nursing Concepts II", 11),
        c("NURS 3700", "Nursing Pharmacology", 2),
        c("NURS 3800", "Introduction to Nursing Research", 2)]),
    sem(3, "Level 3", [
        c("NURS 4000", "Nursing Concepts III", 9),
        c("NURS 4200", "Nursing Pathopharmacology", 2),
        c("NURS 4300", "Nursing Research - Evidence Based Practice (EBP)", 2),
        c("NURS 4400", "Leadership and Management in Nursing", 2)]),
    sem(4, "Level 4", [
        c("NURS 4500", "Nursing Concepts IV", 6),
        c("NURS 4600", "Transition to Practice", 2),
        c("NURS 4650", "Capstone Clinical", 5),
        c("NURS 4900", "Legal and Ethical Issues in Nursing", 2)]),
]

total = sum(x["credits"] for s in semesters for x in s["courses"])
p = {"institution": INST,
     "plan": {"id": "watts-college-of-nursing-bsn-nursing",
              "major": "Nursing (Bachelor of Science in Nursing)", "degree": "BSN",
              "catalog_year": "2025-2026",
              "notes": "program_type=professional-phase: only the professional (nursing) phase is "
                       "sequenced, per the official 2025-2026 Catalogue Curriculum Plan (pp. 31-32). "
                       "Official Watts College of Nursing 2025-2026 Catalogue, Curriculum Plan (pp. 31-32). "
                       "Level totals verified as printed: 15+15+15+15 = 60, matching the catalog's TOTAL FOR PROGRAM "
                       "(60 credit hours nursing content). Levels are four 15-week semesters (no summer sessions). "
                       "The 60 general-education credits are completed and transferred PRIOR to matriculation "
                       "(student handbook lists the required gen-ed courses); they are not sequenced by Watts and "
                       "are modeled here as external_prereqs, not in the semester flow. "
                       "No TCCNS in NC; no equivalencies invented.",
              "program_type": "professional-phase",
              "semesters": semesters,
              "source_url": "https://wattscollegeofnursing.edu/sites/default/files/90021_Watts-College-of-Nursing-Catalogue-2025-26_9.10.25.pdf",
              "total_credits": total,
              "external_prereqs": ["60 semester hours of general education transferred in prior to matriculation per the 2025-2026 Student Handbook (English Composition I/II, Literature, Speech, A&P I/II with lab, Microbiology with lab, Biology with lab, Chemistry with lab, Nutrition, Fine Arts/Humanities 7 cr, College Math, Statistics, Intro to Psychology, Human Growth and Development, Intro to Sociology, History)"],
              "transfer_confidence": ""}}
with open(os.path.join(OUT, "watts-college-of-nursing-bsn-nursing.json"), "w") as f:
    json.dump(p, f)
print("watts-college-of-nursing-bsn-nursing total =", total)
