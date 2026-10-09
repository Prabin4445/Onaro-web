"""Wave 36: Cabarrus College of Health Sciences (Concord, NC, private).
Official curriculum plan pages (cabarruscollege.edu); pages carry no explicit catalog year (noted honestly).
ASN: http://cabarruscollege.edu/academic-programs/nursing-programs/associate-of-science-in-nursing/curriculum
BSN: http://cabarruscollege.edu/academic-programs/nursing-programs/bachelor-of-science-in-nursing/curriculum
RN-BSN: https://atriumhealth.org/education/cabarrus-college-of-health-sciences/academic-programs/bachelor-science-nursing/curriculum
"""
import json, os

OUT = os.path.dirname(os.path.abspath(__file__))
INST = {"name": "Cabarrus College of Health Sciences", "city": "Concord, NC", "state": "NC", "kind": "private"}

def c(code, title, credits, category, choice=False, options=None, choice_note="", prereq=None):
    return {"code": code, "title": title, "credits": credits, "category": category,
            "choice": choice, "options": options or [], "choice_note": choice_note, "prereq": prereq or []}

def sem(n, label, courses):
    return {"n": n, "label": label, "courses": courses}

def plan(pid, major, degree, notes, semesters, source_url, catalog_year="2026-2027"):
    total = sum(x["credits"] for s in semesters for x in s["courses"])
    p = {"institution": INST,
         "plan": {"id": pid, "major": major, "degree": degree,
                  "catalog_year": catalog_year, "notes": notes,
                  "semesters": semesters, "source_url": source_url,
                  "total_credits": total, "external_prereqs": [], "transfer_confidence": ""}}
    with open(os.path.join(OUT, pid + ".json"), "w") as f:
        json.dump(p, f)
    print(pid, "total =", total)

# --- ASN (Associate of Science in Nursing), 72 hrs; college notes "intended for transfer"
plan("cabarrus-college-of-health-sciences-asn-nursing", "Nursing (Associate of Science in Nursing)", "AS",
     "Official Cabarrus College of Health Sciences 'Curriculum Plan - Associate of Science in Nursing Program'. "
     "Term totals verified as printed: 16+3+17+16+6+14 = 72, matching Total Degree Hours 72. "
     "* = General Education course, ** = Major course per the page. "
     "The college notes this degree is intended for transfer. "
     "No catalog year is printed on the program page; plan transcribed from the live official page (checked 2026-10-09), so catalog_year is recorded as the current academic year 2026-2027. "
     "No TCCNS in NC; no equivalencies invented.",
     [sem(1, "Spring", [
        c("BIO 100", "Medical Terminology", 1, "gened"),
        c("BIO 210", "Human Anatomy & Physiology I", 4, "gened"),
        c("NSG 101", "Introduction to Professional Nursing", 1, "major"),
        c("NSG 111", "Foundations in Nursing-Health Promotion", 7, "major"),
        c("PSY 101", "General Psychology", 3, "gened")]),
      sem(2, "Summer", [
        c("ENG 101", "English Composition I", 3, "gened")]),
      sem(3, "Fall", [
        c("BIO 220", "Human Anatomy & Physiology II", 4, "gened"),
        c("MATHELEC-A", "Math Elective", 3, "gened", choice=True,
          choice_note="Math elective (3 cr); specific options not listed on the plan page"),
        c("NSG 121", "Foundations in Nursing - Chronic Conditions", 7, "major"),
        c("PSY 150", "Human Growth and Development", 3, "gened")]),
      sem(4, "Spring", [
        c("BIO 190", "Principles of Microbiology", 4, "gened"),
        c("NSG 202", "Application of Nutrition in Nursing", 2, "major"),
        c("NSG 203", "Application of Pharmacology in Nursing", 2, "major"),
        c("NSG 212", "Foundations in Nursing - Family Health", 8, "major")]),
      sem(5, "Summer", [
        c("NSG 131", "Foundations in Nursing - Mental Health", 6, "major")]),
      sem(6, "Fall", [
        c("HUMFA-A", "Humanities/Fine Arts Elective", 3, "gened", choice=True,
          choice_note="Humanities/Fine Arts elective (3 cr); specific options not listed on the plan page"),
        c("NSG 231", "Transition to Professional Practice", 2, "major"),
        c("NSG 241", "Foundations in Nursing - Acute Illness", 9, "major")])],
     "http://cabarruscollege.edu/academic-programs/nursing-programs/associate-of-science-in-nursing/curriculum")

# --- BSN (Bachelor of Science in Nursing), 120 hrs, 8 terms
plan("cabarrus-college-of-health-sciences-bsn-nursing", "Nursing (Bachelor of Science in Nursing)", "BSN",
     "Official Cabarrus College of Health Sciences 'Curriculum Plan - Bachelor of Science in Nursing Program'. "
     "Term totals verified as printed: 16+16+13+15+16+14+14+16 = 120, matching Total Degree Hours 120. "
     "Before beginning Term V courses, students must have taken a Nursing Assistant I class within 14 months "
     "and/or be on the Nursing Assistant Registry, and all Terms I-IV general education courses must be complete. "
     "No catalog year is printed on the program page; plan transcribed from the live official page (checked 2026-10-09), so catalog_year is recorded as the current academic year 2026-2027. "
     "No TCCNS in NC; no equivalencies invented.",
     [sem(1, "Fall (Term I)", [
        c("BIO 101", "General Biology I with Lab", 4, "gened"),
        c("ENG 101", "English Composition I", 3, "gened"),
        c("MAT 171", "Pre-calculus Algebra", 3, "gened"),
        c("PSY 101", "General Psychology", 3, "gened"),
        c("SOC 101", "Introduction to Sociology", 3, "gened")]),
      sem(2, "Spring (Term II)", [
        c("BIO 190", "Microbiology with Lab", 4, "gened"),
        c("ENG 102", "English Composition II", 3, "gened"),
        c("ELEC-A", "Elective", 3, "gened", choice=True, choice_note="Elective (3 cr); specific options not listed on the plan page"),
        c("NTR 210", "Nutrition Across the Lifespan", 3, "gened"),
        c("PSY 150", "Human Growth and Development", 3, "gened")]),
      sem(3, "Fall (Term III)", [
        c("BIO 210", "Anatomy & Physiology I with Lab", 4, "gened"),
        c("ELEC-B", "Elective", 3, "gened", choice=True, choice_note="Elective (3 cr); specific options not listed on the plan page"),
        c("MAT 201", "Introductory Statistics", 3, "gened"),
        c("SPA 201", "Introduction to Hispanic Culture", 3, "gened")]),
      sem(4, "Spring (Term IV)", [
        c("BIO 220", "Anatomy & Physiology II with Lab", 4, "gened"),
        c("CHW 330", "Interdisciplinary Collaborative Practice", 3, "major"),
        c("COM 301", "Communication, Culture, and the Community", 3, "major"),
        c("ELEC-C", "Elective", 2, "gened", choice=True, choice_note="Elective (2 cr); specific options not listed on the plan page"),
        c("IHS 350", "Mindfulness for Self-Care", 3, "major")]),
      sem(5, "Fall (Term V)", [
        c("NSG 304", "Foundations of Nursing", 7, "major"),
        c("NSG 315", "Pathophysiology and Pharmacology for Nursing I", 3, "major"),
        c("NSG 320", "Health Assessment of Diverse Patients & Populations", 3, "major"),
        c("NSG 320L", "Physical Assessment Skills", 1, "major"),
        c("NSG 330", "Introductory Concepts of the Professional Role", 2, "major")]),
      sem(6, "Spring (Term VI)", [
        c("NSG 350", "Nursing Care for Adult Medical-Surgical Clients", 7, "major"),
        c("NSG 350L", "Advanced Nursing Skills Lab", 1, "major"),
        c("NSG 360", "Pathophysiology and Pharmacology for Nursing II", 3, "major"),
        c("NSG 370", "Healthcare Informatics", 3, "major")]),
      sem(7, "Fall (Term VII)", [
        c("NSG 380", "Population Focused Community Nursing", 4, "major"),
        c("NSG 400", "Nursing Care of Older Adults", 2, "major"),
        c("NSG 415", "Nursing Care of Women and Childbearing Families", 4, "major"),
        c("NSG 420", "Nursing Care of Childrearing Families", 4, "major")]),
      sem(8, "Spring (Term VIII)", [
        c("NSG 430", "Care of Patients & Their Families Experiencing Emotional or Mental Health Disruptions", 4, "major"),
        c("NSG 440", "Evidence Based Practice and Research in Nursing", 3, "major"),
        c("NSG 450", "Managing Complex Nursing Care in Diverse Populations", 6, "major"),
        c("NSG 460", "Nursing Leadership and Transition into Practice", 3, "major")])],
     "http://cabarruscollege.edu/academic-programs/nursing-programs/bachelor-of-science-in-nursing/curriculum")
