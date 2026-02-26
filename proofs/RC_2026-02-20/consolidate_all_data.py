#!/usr/bin/env python3
"""
CONSOLIDATION EXHAUSTIVE — Travail d'orfèvre
=============================================
Lit TOUTES les données extraites du dump PostgreSQL du 20 fév 2026,
les croise avec le BILAN_AFFECTATIONS.md, le bilan_walid.tex,
et produit reconstitution_data_v2.json — le fichier UNIQUE qui contient
TOUT ce qu'il faut pour reconstituer Korrigo à l'identique.

Données consolidées:
- Barèmes détaillés J1 et J2 (grading_structure avec IDs)
- Dispatching exact: chaque copie → son correcteur assigné
- 105 scores détaillés (scores_data par question)
- 544 annotations (position, texte, type, page, créateur)
- 1075 remarques par question
- 2221 événements de correction (audit trail)
- 42 appréciations globales
- 42 bilans LLM
- 209 variantes de sujet (A/B)
- Templates d'annotation (corrigé type)
- Drafts de correction en cours
- Mapping complet copie ↔ élève ↔ correcteur
- Info post-dump: bilan_walid.tex (Walid=8.25/20)
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
EXTRACTED = os.path.join(BASE, "extracted_data")
OUTPUT = os.path.join(BASE, "reconstitution_data_v2.json")


def load_json(filename):
    """Charge un fichier JSON depuis extracted_data/."""
    path = os.path.join(EXTRACTED, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_grading_structure(raw):
    """Parse grading_structure qui peut être une string JSON ou déjà un objet."""
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    return raw if raw else []


def compute_total(scores_data_raw):
    """Calcule le total d'un scores_data (string JSON ou dict)."""
    if isinstance(scores_data_raw, str):
        try:
            sd = json.loads(scores_data_raw)
        except:
            return 0
    else:
        sd = scores_data_raw
    if not sd:
        return 0
    return sum(float(v) for v in sd.values() if v not in (None, "", "null"))


def main():
    print("=" * 70)
    print("  CONSOLIDATION EXHAUSTIVE — reconstitution_data_v2.json")
    print("=" * 70)

    # =====================================================================
    # 1. LOAD ALL DATA
    # =====================================================================
    exams = load_json("exams_exam.json")
    copies = load_json("exams_copy.json")
    booklets = load_json("exams_booklet.json")
    copy_booklets = load_json("exams_copy_booklets.json")
    exam_correctors = load_json("exams_exam_correctors.json")
    users = load_json("auth_user.json")
    students = load_json("students_student.json")
    scores = load_json("grading_score.json")
    annotations = load_json("grading_annotation.json")
    remarks = load_json("grading_questionremark.json")
    events = load_json("grading_gradingevent.json")
    templates = load_json("grading_annotationtemplate.json")
    drafts = load_json("grading_draftstate.json")
    profiles = load_json("core_userprofile.json")
    user_groups = load_json("auth_user_groups.json")

    # Build lookup maps
    user_map = {u["id"]: u for u in users}
    student_map = {s["id"]: s for s in students}
    exam_map = {e["id"]: e for e in exams}
    copy_map = {c["id"]: c for c in copies}

    # =====================================================================
    # 2. IDENTIFY REAL EXAMS (exclude test exam)
    # =====================================================================
    real_exams = [e for e in exams if "Prod Validation" not in e["name"]]
    real_exam_ids = {e["id"] for e in real_exams}
    real_copies = [c for c in copies if c["exam_id"] in real_exam_ids]

    print(f"\nExams réels: {len(real_exams)}")
    print(f"Copies réelles: {len(real_copies)}")

    # =====================================================================
    # 3. BARÈMES DÉTAILLÉS
    # =====================================================================
    baremes = {}
    for e in real_exams:
        gs = parse_grading_structure(e["grading_structure"])
        baremes[e["name"]] = {
            "exam_id": e["id"],
            "exam_date": e["date"],
            "upload_mode": e["upload_mode"],
            "pages_per_booklet": e["pages_per_booklet"],
            "results_released_at": e.get("results_released_at"),
            "grading_structure": gs,
        }
        # Compute total points
        def sum_points(items, depth=0):
            total = 0
            for item in items:
                pts = item.get("points", 0) or 0
                children = item.get("children", [])
                if children:
                    total += sum_points(children, depth + 1)
                else:
                    total += float(pts)
            return total

        total_pts = sum_points(gs)
        baremes[e["name"]]["total_points"] = total_pts
        print(f"  {e['name']}: {len(gs)} exercices, total={total_pts} pts")

    # =====================================================================
    # 4. TEACHERS (with password hashes for auth restoration)
    # =====================================================================
    # Identify real teachers (correctors + admin)
    corrector_user_ids = set()
    for ec in exam_correctors:
        if ec["exam_id"] in real_exam_ids:
            corrector_user_ids.add(ec["user_id"])

    # Add admin
    admin_user = None
    for u in users:
        if u.get("is_superuser") == "t" and u["username"] == "admin":
            admin_user = u
            corrector_user_ids.add(u["id"])

    teachers = []
    for u in users:
        if u["id"] in corrector_user_ids:
            teachers.append({
                "id": u["id"],
                "username": u["username"],
                "first_name": u["first_name"],
                "last_name": u["last_name"],
                "email": u["email"],
                "is_staff": u["is_staff"] == "t",
                "is_superuser": u["is_superuser"] == "t",
                "is_active": u["is_active"] == "t",
                "date_joined": u["date_joined"],
                "last_login": u["last_login"],
                "password": u.get("password", ""),
            })

    print(f"\nTeachers/correctors: {len(teachers)}")
    for t in teachers:
        print(f"  {t['username']} (id={t['id']}, staff={t['is_staff']}, super={t['is_superuser']})")

    # =====================================================================
    # 5. EXAM ↔ CORRECTORS MAPPING
    # =====================================================================
    exam_correctors_map = defaultdict(list)
    for ec in exam_correctors:
        if ec["exam_id"] in real_exam_ids:
            uname = user_map.get(ec["user_id"], {}).get("username", "???")
            ename = exam_map[ec["exam_id"]]["name"]
            exam_correctors_map[ename].append({
                "user_id": ec["user_id"],
                "username": uname,
            })

    print(f"\nExam→Correctors:")
    for ename, corrs in sorted(exam_correctors_map.items()):
        print(f"  {ename}: {[c['username'] for c in corrs]}")

    # =====================================================================
    # 6. DISPATCHING: EACH COPY → ITS CORRECTOR + STUDENT
    # =====================================================================
    dispatching = []
    for c in real_copies:
        ename = exam_map[c["exam_id"]]["name"]
        corrector_id = c.get("assigned_corrector_id")
        corrector_username = user_map.get(corrector_id, {}).get("username") if corrector_id else None
        student_id = c.get("student_id")
        student_info = None
        if student_id and student_id in student_map:
            s = student_map[student_id]
            student_info = {
                "id": s["id"],
                "first_name": s["first_name"],
                "last_name": s["last_name"],
                "class_name": s.get("class_name", ""),
                "groupe": s.get("groupe", ""),
                "email": s.get("email", ""),
                "date_naissance": s.get("date_naissance", ""),
                "user_id": s.get("user_id"),
            }

        dispatching.append({
            "copy_id": c["id"],
            "anonymous_id": c["anonymous_id"],
            "exam_name": ename,
            "exam_id": c["exam_id"],
            "status": c["status"],
            "assigned_corrector_id": corrector_id,
            "assigned_corrector_username": corrector_username,
            "student": student_info,
            "subject_variant": c.get("subject_variant"),
            "graded_at": c.get("graded_at"),
            "validated_at": c.get("validated_at"),
            "pdf_source": c.get("pdf_source", ""),
            "final_pdf": c.get("final_pdf", ""),
            "global_appreciation": c.get("global_appreciation"),
            "llm_summary": c.get("llm_summary"),
        })

    # Sort by exam then anonymous_id
    dispatching.sort(key=lambda x: (x["exam_name"], x["anonymous_id"]))
    print(f"\nDispatching: {len(dispatching)} copies")

    # Stats
    dispatch_stats = defaultdict(lambda: defaultdict(int))
    for d in dispatching:
        corr = d["assigned_corrector_username"] or "UNASSIGNED"
        dispatch_stats[d["exam_name"]][corr] += 1
    for ename, corrs in sorted(dispatch_stats.items()):
        print(f"  {ename}:")
        for corr, cnt in sorted(corrs.items()):
            print(f"    {corr}: {cnt}")

    # =====================================================================
    # 7. SCORES DÉTAILLÉS (105 scores)
    # =====================================================================
    scores_detailed = []
    for s in scores:
        c = copy_map.get(s["copy_id"])
        if not c or c["exam_id"] not in real_exam_ids:
            continue

        sd_raw = s["scores_data"]
        if isinstance(sd_raw, str):
            try:
                sd = json.loads(sd_raw)
            except:
                sd = {}
        else:
            sd = sd_raw or {}

        total = sum(float(v) for v in sd.values() if v not in (None, "", "null"))

        # Find corrector for this copy
        corr_id = c.get("assigned_corrector_id")
        corr_name = user_map.get(corr_id, {}).get("username") if corr_id else None

        scores_detailed.append({
            "score_id": s["id"],
            "copy_id": s["copy_id"],
            "anonymous_id": c["anonymous_id"],
            "exam_name": exam_map[c["exam_id"]]["name"],
            "scores_data": sd,
            "total": round(total, 2),
            "final_comment": s.get("final_comment", ""),
            "created_at": s["created_at"],
            "updated_at": s["updated_at"],
            "corrector_username": corr_name,
            "copy_status": c["status"],
        })

    scores_detailed.sort(key=lambda x: (x["exam_name"], -x["total"]))
    print(f"\nScores: {len(scores_detailed)}")
    for ename in sorted(set(s["exam_name"] for s in scores_detailed)):
        es = [s for s in scores_detailed if s["exam_name"] == ename]
        print(f"  {ename}: {len(es)} scores")

    # =====================================================================
    # 8. ANNOTATIONS COMPLÈTES (544)
    # =====================================================================
    annotations_detailed = []
    for a in annotations:
        c = copy_map.get(a["copy_id"])
        if not c or c["exam_id"] not in real_exam_ids:
            continue

        creator = user_map.get(a["created_by_id"], {}).get("username", "???")

        annotations_detailed.append({
            "annotation_id": a["id"],
            "copy_id": a["copy_id"],
            "anonymous_id": c["anonymous_id"],
            "exam_name": exam_map[c["exam_id"]]["name"],
            "page_index": int(a["page_index"]),
            "x": float(a["x"]),
            "y": float(a["y"]),
            "w": float(a["w"]),
            "h": float(a["h"]),
            "content": a["content"],
            "type": a["type"],
            "score_delta": int(a["score_delta"]) if a.get("score_delta") else None,
            "created_by_username": creator,
            "created_by_id": a["created_by_id"],
            "created_at": a["created_at"],
            "updated_at": a["updated_at"],
            "version": a.get("version", "0"),
        })

    annotations_detailed.sort(key=lambda x: (x["exam_name"], x["anonymous_id"], x["page_index"]))
    print(f"\nAnnotations: {len(annotations_detailed)}")

    # =====================================================================
    # 9. REMARQUES PAR QUESTION (1075)
    # =====================================================================
    remarks_detailed = []
    for r in remarks:
        c = copy_map.get(r["copy_id"])
        if not c or c["exam_id"] not in real_exam_ids:
            continue

        creator = user_map.get(r["created_by_id"], {}).get("username", "???")

        remarks_detailed.append({
            "remark_id": r["id"],
            "copy_id": r["copy_id"],
            "anonymous_id": c["anonymous_id"],
            "exam_name": exam_map[c["exam_id"]]["name"],
            "question_id": r["question_id"],
            "remark": r["remark"],
            "created_by_username": creator,
            "created_by_id": r["created_by_id"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        })

    remarks_detailed.sort(key=lambda x: (x["exam_name"], x["anonymous_id"], x["question_id"]))
    print(f"Remarques: {len(remarks_detailed)}")

    # =====================================================================
    # 10. GRADING EVENTS (2221) — AUDIT TRAIL
    # =====================================================================
    events_detailed = []
    for ev in events:
        c = copy_map.get(ev.get("copy_id"))
        if not c or c["exam_id"] not in real_exam_ids:
            continue

        actor = user_map.get(ev.get("actor_id"), {}).get("username") if ev.get("actor_id") else None

        events_detailed.append({
            "event_id": ev["id"],
            "copy_id": ev["copy_id"],
            "anonymous_id": c["anonymous_id"],
            "exam_name": exam_map[c["exam_id"]]["name"],
            "event_type": ev.get("event_type", ""),
            "actor_username": actor,
            "actor_id": ev.get("actor_id"),
            "created_at": ev.get("created_at", ""),
            "details": ev.get("details", ""),
        })

    events_detailed.sort(key=lambda x: x.get("created_at", ""))
    print(f"Events: {len(events_detailed)}")

    # =====================================================================
    # 11. ANNOTATION TEMPLATES (corrigé type)
    # =====================================================================
    templates_detailed = []
    for t in templates:
        if t.get("exam_id") not in real_exam_ids:
            continue
        templates_detailed.append({
            "template_id": t["id"],
            "exam_id": t["exam_id"],
            "exam_name": exam_map.get(t["exam_id"], {}).get("name", "???"),
            "exercise_number": t["exercise_number"],
            "question_number": t["question_number"],
            "sub_question": t.get("sub_question", ""),
            "criterion_type": t["criterion_type"],
            "severity": t["severity"],
            "text": t["text"],
            "is_active": t["is_active"] == "t",
            "tags": t.get("tags", "[]"),
        })

    templates_detailed.sort(key=lambda x: (x["exam_name"], x["exercise_number"], x["question_number"]))
    print(f"Templates: {len(templates_detailed)}")

    # =====================================================================
    # 12. BOOKLETS (mapping copie → booklet → pages)
    # =====================================================================
    booklet_map = {b["id"]: b for b in booklets}
    copy_booklet_links = []
    for cb in copy_booklets:
        copy_id = cb.get("copy_id")
        booklet_id = cb.get("booklet_id")
        c = copy_map.get(copy_id)
        if not c or c["exam_id"] not in real_exam_ids:
            continue
        b = booklet_map.get(booklet_id, {})
        pages_images = b.get("pages_images", "[]")
        if isinstance(pages_images, str):
            try:
                pages_images = json.loads(pages_images)
            except:
                pages_images = []

        copy_booklet_links.append({
            "copy_id": copy_id,
            "booklet_id": booklet_id,
            "anonymous_id": c["anonymous_id"],
            "start_page": b.get("start_page"),
            "end_page": b.get("end_page"),
            "pages_count": len(pages_images) if isinstance(pages_images, list) else 0,
        })

    print(f"Booklet links: {len(copy_booklet_links)}")

    # =====================================================================
    # 13. STUDENTS (220 students)
    # =====================================================================
    students_detailed = []
    for s in students:
        students_detailed.append({
            "id": s["id"],
            "first_name": s["first_name"],
            "last_name": s["last_name"],
            "date_naissance": s.get("date_naissance", ""),
            "email": s.get("email", ""),
            "class_name": s.get("class_name", ""),
            "groupe": s.get("groupe", ""),
            "user_id": s.get("user_id"),
        })

    # Add student usernames from user_map
    for sd in students_detailed:
        uid = sd.get("user_id")
        if uid and uid in user_map:
            sd["username"] = user_map[uid].get("username", "")
            sd["student_password"] = user_map[uid].get("password", "")
        else:
            sd["username"] = ""
            sd["student_password"] = ""

    print(f"Students: {len(students_detailed)}")

    # =====================================================================
    # 14. DRAFTS (correction en cours)
    # =====================================================================
    drafts_detailed = []
    for d in drafts:
        c = copy_map.get(d.get("copy_id"))
        if not c or c["exam_id"] not in real_exam_ids:
            continue
        drafts_detailed.append({
            "draft_id": d["id"],
            "copy_id": d["copy_id"],
            "anonymous_id": c["anonymous_id"],
            "exam_name": exam_map[c["exam_id"]]["name"],
            "state_data": d.get("state_data", ""),
            "created_at": d.get("created_at", ""),
            "updated_at": d.get("updated_at", ""),
        })

    print(f"Drafts: {len(drafts_detailed)}")

    # =====================================================================
    # 15. POST-DUMP DATA (bilan_walid.tex)
    # =====================================================================
    post_dump_corrections = [
        {
            "source": "bilan_walid.tex",
            "date": "2026-02-22",
            "anonymous_id": "0F8E-082",
            "student_name": "MEZIANE Walid",
            "exam": "BB_J1",
            "corrector": "philippe.carr",
            "note_total": 8.25,
            "detail": {
                "Exercice 1 (QCM)": 3.0,
                "Exercice 2 (Fonction x²ln(x))": 1.25,
                "Exercice 3 (Probabilités)": 1.75,
                "Exercice 4 (Suites)": 2.25,
            },
            "note_dump": 6.25,
            "corrector_dump": "selima.klibi",
            "comment": "Note révisée post-dump par philippe.carr. Le dump avait 6.25 par selima.klibi.",
        }
    ]

    # Annotated PDFs downloaded post-dump
    post_dump_pdfs = [
        {
            "filename": "BELCADHI_YOLDEZ.pdf",
            "date": "2026-02-23 16:09",
            "size_bytes": 2200000,
            "exam": "BB_J1",
            "source": "copies_lot1/",
            "comment": "PDF annoté téléchargé depuis Korrigo le 23 fév",
        },
        {
            "filename": "BEN_MRAD_YOUSSEF.pdf",
            "date": "2026-02-23 16:09",
            "size_bytes": 912000,
            "exam": "BB_J1",
            "source": "copies_lot1/",
            "comment": "PDF annoté téléchargé depuis Korrigo le 23 fév",
        },
        {
            "filename": "JERIBI_OMAR.pdf",
            "date": "2026-02-23 16:09",
            "size_bytes": 1600000,
            "exam": "BB_J1",
            "source": "copies_lot1/",
            "comment": "PDF annoté téléchargé depuis Korrigo le 23 fév",
        },
        {
            "filename": "MEZIANE_WALID.pdf",
            "date": "2026-02-23 16:09",
            "size_bytes": 730000,
            "exam": "BB_J1",
            "source": "copies_lot1/",
            "comment": "PDF annoté téléchargé depuis Korrigo le 23 fév",
        },
        {
            "filename": "copie_KTATA_EMNA.pdf",
            "date": "2026-02-25 14:36",
            "size_bytes": 2860000,
            "exam": "BB_J2",
            "source": "Téléchargements/",
            "comment": "PDF annoté téléchargé via pypdf le 25 fév",
        },
    ]

    # =====================================================================
    # 16. COPY REPLACEMENT HISTORY (5 copies replaced Feb 23)
    # =====================================================================
    copy_replacements = [
        {
            "anonymous_id": "0F8E-040",
            "student": "CHIHAOUI INES",
            "copy_id": "fff58503-361f-419f-b1d2-aa8b9d343a85",
            "corrector": "patrick.dupont",
            "pages_before": 13,
            "pages_after": 9,
            "date": "2026-02-23",
        },
        {
            "anonymous_id": "0F8E-066",
            "student": "GHORBAL SOPHIE",
            "copy_id": "a5bd614d-f5b7-4e66-abf8-2239fefd59c8",
            "corrector": "patrick.dupont",
            "pages_before": 21,
            "pages_after": 13,
            "date": "2026-02-23",
        },
        {
            "anonymous_id": "0F8E-029",
            "student": "GRATI MOHAMED-MEHDI",
            "copy_id": "de498607-727d-433a-baef-1128575788c5",
            "corrector": "philippe.carr",
            "pages_before": 9,
            "pages_after": 13,
            "date": "2026-02-23",
        },
        {
            "anonymous_id": "0F8E-094",
            "student": "KAMMOUN AYMAR",
            "copy_id": "72c35dc0-46f8-489d-8550-6eddc3223ea1",
            "corrector": "philippe.carr",
            "pages_before": 8,
            "pages_after": 9,
            "date": "2026-02-23",
        },
        {
            "anonymous_id": "0F8E-028",
            "student": "TRABELSI ABDERRAHMANE",
            "copy_id": "0835a2a5-4a84-439a-a449-d213e6f1562c",
            "corrector": "selima.klibi",
            "pages_before": 9,
            "pages_after": 9,
            "date": "2026-02-23",
        },
    ]

    # =====================================================================
    # 17. USER PROFILES
    # =====================================================================
    profiles_detailed = []
    for p in profiles:
        uid = p.get("user_id")
        uname = user_map.get(uid, {}).get("username", "")
        profiles_detailed.append({
            "user_id": uid,
            "username": uname,
            "role": p.get("role", ""),
            "bio": p.get("bio", ""),
        })

    # =====================================================================
    # ASSEMBLE FINAL OUTPUT
    # =====================================================================
    output = {
        "_metadata": {
            "generated_at": datetime.now().isoformat(),
            "source": "dump PostgreSQL du 20 février 2026 à 09:06 UTC+1",
            "description": "Reconstitution exhaustive de toutes les données Korrigo",
            "counts": {
                "exams": len(real_exams),
                "copies": len(dispatching),
                "scores": len(scores_detailed),
                "annotations": len(annotations_detailed),
                "remarks": len(remarks_detailed),
                "events": len(events_detailed),
                "templates": len(templates_detailed),
                "students": len(students_detailed),
                "teachers": len(teachers),
                "appreciations": sum(1 for d in dispatching if d.get("global_appreciation")),
                "llm_summaries": sum(1 for d in dispatching if d.get("llm_summary")),
                "drafts": len(drafts_detailed),
                "booklet_links": len(copy_booklet_links),
                "subject_variants_A": sum(1 for d in dispatching if d.get("subject_variant") == "A"),
                "subject_variants_B": sum(1 for d in dispatching if d.get("subject_variant") == "B"),
            },
        },
        "baremes": baremes,
        "exam_correctors": dict(exam_correctors_map),
        "teachers": teachers,
        "students": students_detailed,
        "dispatching": dispatching,
        "scores": scores_detailed,
        "annotations": annotations_detailed,
        "remarks": remarks_detailed,
        "events": events_detailed,
        "templates": templates_detailed,
        "booklet_links": copy_booklet_links,
        "drafts": drafts_detailed,
        "profiles": profiles_detailed,
        "post_dump_corrections": post_dump_corrections,
        "post_dump_pdfs": post_dump_pdfs,
        "copy_replacements": copy_replacements,
    }

    # =====================================================================
    # WRITE OUTPUT
    # =====================================================================
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    size_mb = os.path.getsize(OUTPUT) / (1024 * 1024)
    print(f"\n{'=' * 70}")
    print(f"  FICHIER GÉNÉRÉ: {OUTPUT}")
    print(f"  Taille: {size_mb:.2f} Mo")
    print(f"{'=' * 70}")

    # =====================================================================
    # VERIFICATION SUMMARY
    # =====================================================================
    print(f"\n--- VÉRIFICATION INTÉGRITÉ ---")
    counts = output["_metadata"]["counts"]
    for key, val in counts.items():
        print(f"  {key}: {val}")

    # Cross-check: every score has a matching copy in dispatching
    dispatch_copy_ids = {d["copy_id"] for d in dispatching}
    orphan_scores = [s for s in scores_detailed if s["copy_id"] not in dispatch_copy_ids]
    print(f"\n  Scores orphelins (sans copie): {len(orphan_scores)}")

    # Cross-check: every annotation has a matching copy
    orphan_annots = [a for a in annotations_detailed if a["copy_id"] not in dispatch_copy_ids]
    print(f"  Annotations orphelines: {len(orphan_annots)}")

    # Cross-check: copies with scores vs BILAN_AFFECTATIONS
    copies_with_scores = {s["anonymous_id"] for s in scores_detailed}
    copies_graded = {d["anonymous_id"] for d in dispatching if d["status"] == "GRADED"}
    copies_with_appreciation = {d["anonymous_id"] for d in dispatching if d.get("global_appreciation")}
    copies_with_llm = {d["anonymous_id"] for d in dispatching if d.get("llm_summary")}

    print(f"\n  Copies avec scores: {len(copies_with_scores)}")
    print(f"  Copies GRADED: {len(copies_graded)}")
    print(f"  Copies avec appréciation: {len(copies_with_appreciation)}")
    print(f"  Copies avec bilan LLM: {len(copies_with_llm)}")
    print(f"  GRADED sans appréciation: {copies_graded - copies_with_appreciation}")
    print(f"  Appréciation sans GRADED: {copies_with_appreciation - copies_graded}")

    print(f"\n=== CONSOLIDATION TERMINÉE ===")


if __name__ == "__main__":
    main()
