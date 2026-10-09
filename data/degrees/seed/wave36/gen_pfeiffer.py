"""Wave 36: Pfeiffer University (Misenheimer, NC, private) - BSN Nursing.

Source: 2025-2026 Undergraduate BSN Student Handbook (Dept. of Nursing, revised 08.2025),
Chapter III "BSN PLAN OF STUDY" / "Suggested 4-Year Plan of Study" / "4-Year Plan of Study".
Two phases: 63 SH lower-division (freshman+sophomore) + 57 SH upper-division (junior+senior) = 120.
Semester totals verified against the handbook's printed totals: 14+17+16+16+14+15+14+14 = 120.

Quirks handled honestly:
- Plan tables label A&P I/II as "BIOL 265/266", but the authoritative NURSING PLAN OF STUDY
  requirements list and the course descriptions name them EXSC 265/266. Seeds use EXSC codes.
- EXSC 265 prereq per course description is BIOL 175 or BIOL 211 (not in the plan).
- UNIV 375 Pfeiffer Seminar is sequenced in Spring Year 2 (3 cr); the Junior Fall/Spring tables
  list it only conditionally ("if not already taken", no credits shown, totals sum without it).
- Prereq-marked (*) courses must be completed with a grade of C or better.
- All NURS 312+ courses require admission into the upper-division nursing major.
Source: https://www.pfeiffer.edu/wp-content/uploads/2025/10/2025-2026-BSN-Handbook-Revised-08.2025.pdf
"""
import json, os

OUT = os.path.dirname(os.path.abspath(__file__))
INST = {"name": "Pfeiffer University", "city": "Misenheimer, NC", "state": "NC", "kind": "private"}
URL = "https://www.pfeiffer.edu/wp-content/uploads/2025/10/2025-2026-BSN-Handbook-Revised-08.2025.pdf"


def c(code, title, credits, category="major", choice=False, options=None,
      choice_note="", prereq=None):
    return {"code": code, "title": title, "credits": credits, "category": category,
            "choice": choice, "options": options or [], "choice_note": choice_note,
            "prereq": prereq or [], "required_zero": False, "tccns": ""}


def g(code, title, credits, choice_note=""):
    return c(code, title, credits, category="gen_ed", choice=True, choice_note=choice_note)


def sem(n, label, courses):
    return {"n": n, "label": label, "courses": courses}


semesters = [
    # ---- Freshman Year (lower division prereqs) ----
    sem(1, "Freshman Year - Fall", [
        c("UNIV 125", "Pfeiffer Seminar", 1, category="gen_ed"),
        c("CHEM 110N", "General, Organic, Biochemistry", 4, choice=False,
          choice_note=""),
        c("PSYC 222M", "Statistics & Data Analysis (or MATH 220 College Algebra)", 3,
          choice=True,
          options=[{"code": "PSYC 222M", "credits": 3, "title": "Statistics & Data Analysis"},
                   {"code": "MATH 220", "credits": 3, "title": "College Algebra"}],
          choice_note="MATH 220 College Algebra only if math assessment scores indicate need to take it prior to the Statistics course"),
        g("ENGL 101 / ENGL 102", "General Education: ENGL 101 or 102", 3,
          choice_note="ENGL 101 or 102 per the published plan; titles per general catalog"),
        g("GENED-A", "General Education Course", 3,
          choice_note="General Education course - specific course not listed in the published plan"),
    ]),
    sem(2, "Freshman Year - Spring", [
        c("UNIV 126", "Pfeiffer Seminar", 1, category="gen_ed"),
        c("BIOL 224", "Principles of Microbiology", 4, prereq=["CHEM 110N"]),
        c("PSYC 202S", "Introduction to Psychology", 3, category="gen_ed",
          choice_note=""),
        g("GENED-B", "General Education: ENGL 102 or other General Education", 3,
          choice_note="ENGL 102 or another General Education course per the published plan"),
        g("GENED-C", "General Education Course", 3,
          choice_note="General Education course - specific course not listed in the published plan"),
        g("GENED-D", "General Education Course or Elective", 3,
          choice_note="General Education course or elective - specific course not listed in the published plan"),
    ]),
    # ---- Sophomore Year (lower division prereqs) ----
    sem(3, "Sophomore Year - Fall", [
        c("EXSC 265", "Human Anatomy and Physiology I", 4,
          prereq=[{"one_of": ["BIOL 175", "BIOL 211"]}],
          choice_note="Catalog prerequisite for EXSC 265 is BIOL 175 or BIOL 211 per the course description; neither is sequenced in the published plan - listed in external_prereqs"),
        c("PSYC 295", "Developmental Psychology", 3, prereq=["PSYC 202S"]),
        c("NURS 309", "Healthcare and the Aging Population", 3),
        c("UNIV 275", "Pfeiffer Seminar (or PSYC 222M Statistics and Data Analysis)", 3,
          category="gen_ed", choice=True,
          options=[{"code": "UNIV 275", "credits": 3, "title": "Pfeiffer Seminar"},
                   {"code": "PSYC 222M", "credits": 3, "title": "Statistics & Data Analysis"}],
          choice_note="UNIV 275 Pfeiffer Seminar, or PSYC 222M Statistics and Data Analysis if the student did not complete it in the freshman year"),
        c("EXSC 300", "Nutrition", 3),
    ]),
    sem(4, "Sophomore Year - Spring", [
        c("EXSC 266", "Human Anatomy and Physiology II", 4, prereq=["EXSC 265"]),
        g("GENED-E", "General Education Course or Elective", 3,
          choice_note="General Education course or elective - specific course not listed in the published plan"),
        c("NURS 201", "Introduction to Professional Nursing and Healthcare Technology", 3,
          prereq=["ENGL 101 / ENGL 102"]),
        g("GENED-F", "General Education Course or Elective", 3,
          choice_note="General Education course or elective - specific course not listed in the published plan"),
        c("UNIV 375", "Pfeiffer Seminar", 3, category="gen_ed"),
    ]),
    # ---- Junior Year (upper division nursing) ----
    sem(5, "Junior Year - Fall", [
        c("NURS 312", "Foundations and Concepts for Professional Nursing Practice", 5),
        c("NURS 314", "Communications and Informatics in Nursing", 4),
        c("NURS 316", "Health Assessment", 3),
        c("NURS 326", "Pathophysiology for Nursing", 2),
    ]),
    sem(6, "Junior Year - Spring", [
        c("NURS 320", "Nursing Care of Adults I and Clinical Practicum", 6),
        c("NURS 318", "Pharmacology for Nursing", 3),
        c("NURS 322", "Nursing Care of the Childbearing/Childrearing Family and Clinical Practicum", 6),
    ]),
    # ---- Senior Year (upper division nursing) ----
    sem(7, "Senior Year - Fall", [
        c("NURS 412", "Psychiatric/Mental Health Nursing", 5),
        c("NURS 410", "Nursing Care of Adults II", 6),
        c("NURS 418", "Nursing Leadership Values, Trends, and Perspectives", 3),
    ]),
    sem(8, "Senior Year - Spring", [
        c("NURS 416", "Community Health Nursing", 5),
        c("NURS 414", "Introduction to Nursing Research", 3),
        c("NURS 501", "Transition to Professional Nursing: Senior Internship", 3),
        c("NURS 510", "Synthesis for Professional Nursing Practice", 3),
    ]),
]

total = sum(x["credits"] for s in semesters for x in s["courses"])
assert total == 120, total

notes = (
    "Source: Pfeiffer University 2025-2026 Undergraduate BSN Student Handbook (Department of "
    "Nursing, revised 08.2025), Chapter III 'BSN Plan of Study' / 'Suggested 4-Year Plan of "
    "Study'. This is a SUGGESTED sequence as published. Two phases: 63 SH lower-division "
    "liberal-arts/nursing-prerequisite work + 57 SH upper-division nursing = 120 hours. "
    "Semester totals verified as printed: 14+17+16+16+14+15+14+14 = 120. "
    "Prerequisite-marked courses (CHEM 110N, BIOL 224, PSYC 202S, PSYC 222M, PSYC 295, "
    "EXSC 265/266, EXSC 300, NURS 201, NURS 309) must be completed with a grade of C or better; "
    "all NURS 312-and-above courses require admission into the upper-division nursing major. "
    "Course-code note: the plan tables label Anatomy & Physiology I/II as BIOL 265/266, but the "
    "authoritative Nursing Plan of Study requirements list and the handbook's course descriptions "
    "name them EXSC 265/266 - EXSC codes used here. EXSC 265's catalog prerequisite is BIOL 175 "
    "or BIOL 211, which is not in the published plan. Generic 'General Education Course' slots "
    "have no specific courses listed in the plan. UNIV 375 (3 cr) is sequenced in Spring Year 2; "
    "the Junior Fall/Spring tables list it only conditionally ('if not already taken') with no "
    "credits shown and totals summing without it. Prerequisites shown were verified in the "
    "handbook's course descriptions, not inferred from sequence order. No TCCNS in NC."
)

p = {"institution": INST,
     "plan": {"id": "pfeiffer-university-bs-nursing",
              "major": "Nursing", "degree": "BSN",
              "catalog_year": "2025-2026",
              "notes": notes,
              "semesters": semesters,
              "source_url": URL,
              "total_credits": total,
              "external_prereqs": ["BIOL 175", "BIOL 211"],
              "transfer_confidence": ""}}
with open(os.path.join(OUT, "pfeiffer-university-bs-nursing.json"), "w") as f:
    json.dump(p, f)
print("pfeiffer-university-bs-nursing total =", total)
