#!/usr/bin/env python
"""
Script d'extraction READ-ONLY des données de correction Korrigo.
Exécuté via: python manage.py shell < extract_correction_data.py

Produit un répertoire /tmp/korrigo_extract/ contenant :
  - copies_data.json : toutes les copies avec notes, annotations, remarques, appréciations
  - pages_manifest.json : mapping copy_id -> liste des chemins d'images scannées
  - exams_bareme.json : barèmes des examens
  - summary.json : statistiques globales

AUCUNE ÉCRITURE en base de données.
"""
import json
import os
import sys
import pathlib
from datetime import datetime

# Django models
from exams.models import Copy, Exam, Booklet
from grading.models import Annotation, Score, QuestionRemark, GradingEvent
from students.models import Student
from django.conf import settings

OUTPUT_DIR = "/tmp/korrigo_extract"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"[{datetime.now().isoformat()}] Starting Korrigo data extraction (READ-ONLY)...")
print(f"Output directory: {OUTPUT_DIR}")
print(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")


def serialize_uuid(obj):
    """JSON serializer for UUID, datetime, and pathlib objects."""
    if hasattr(obj, 'hex'):
        return str(obj)
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    if isinstance(obj, pathlib.PurePath):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# =============================================================================
# 1. Extract exam barèmes
# =============================================================================
print("\n--- Extracting exam barèmes ---")
exams_data = []
for exam in Exam.objects.all():
    exam_dict = {
        "id": str(exam.id),
        "name": exam.name,
        "date": str(exam.date) if exam.date else None,
        "grading_structure": exam.grading_structure if hasattr(exam, 'grading_structure') else None,
        "results_released_at": exam.results_released_at.isoformat() if exam.results_released_at else None,
        "copies_count": exam.copies.count(),
    }
    exams_data.append(exam_dict)
    print(f"  Exam: {exam.name} | {exam.copies.count()} copies")

with open(os.path.join(OUTPUT_DIR, "exams_bareme.json"), "w", encoding="utf-8") as f:
    json.dump(exams_data, f, indent=2, ensure_ascii=False, default=serialize_uuid)
print(f"  -> exams_bareme.json written ({len(exams_data)} exams)")


# =============================================================================
# 2. Extract all copies with full data
# =============================================================================
print("\n--- Extracting copies with scores, annotations, remarks, appreciations ---")

copies_data = []
pages_manifest = {}
stats = {
    "total_copies": 0,
    "copies_with_scores": 0,
    "copies_with_annotations": 0,
    "copies_with_remarks": 0,
    "copies_with_appreciation": 0,
    "copies_with_llm_summary": 0,
    "total_annotations": 0,
    "total_remarks": 0,
    "by_exam": {},
    "by_corrector": {},
    "by_status": {},
}

all_copies = Copy.objects.select_related(
    'exam', 'student', 'student__user', 'assigned_corrector'
).prefetch_related(
    'booklets', 'annotations', 'scores', 'question_remarks'
).order_by('exam__name', 'anonymous_id')

for copy in all_copies:
    stats["total_copies"] += 1
    exam_name = copy.exam.name
    stats["by_exam"].setdefault(exam_name, 0)
    stats["by_exam"][exam_name] += 1
    stats["by_status"].setdefault(copy.status, 0)
    stats["by_status"][copy.status] += 1

    corrector_name = copy.assigned_corrector.username if copy.assigned_corrector else "unassigned"
    stats["by_corrector"].setdefault(corrector_name, {"total": 0, "with_scores": 0})
    stats["by_corrector"][corrector_name]["total"] += 1

    # --- Student info ---
    student_info = None
    if copy.student and copy.student.user:
        student_info = {
            "id": copy.student.id,
            "first_name": copy.student.user.first_name,
            "last_name": copy.student.user.last_name,
            "email": copy.student.user.email,
        }

    # --- Scores ---
    score_obj = Score.objects.filter(copy=copy).first()
    scores_dict = None
    total_score = None
    final_comment = None
    if score_obj:
        scores_dict = score_obj.scores_data or {}
        final_comment = score_obj.final_comment or ""
        if scores_dict:
            total_score = sum(
                float(v) for v in scores_dict.values()
                if v is not None and v != ''
            )
            stats["copies_with_scores"] += 1
            stats["by_corrector"][corrector_name]["with_scores"] += 1

    # --- Annotations ---
    annotations_list = []
    for annot in copy.annotations.all().order_by('page_index', 'created_at'):
        annotations_list.append({
            "id": str(annot.id),
            "page_index": annot.page_index,
            "x": annot.x,
            "y": annot.y,
            "w": annot.w,
            "h": annot.h,
            "content": annot.content,
            "type": annot.type,
            "score_delta": annot.score_delta,
            "created_by": annot.created_by.username if annot.created_by else None,
            "created_at": annot.created_at.isoformat() if annot.created_at else None,
        })
    if annotations_list:
        stats["copies_with_annotations"] += 1
        stats["total_annotations"] += len(annotations_list)

    # --- Question Remarks ---
    remarks_list = []
    for remark in copy.question_remarks.all().order_by('question_id'):
        remarks_list.append({
            "id": str(remark.id),
            "question_id": remark.question_id,
            "remark": remark.remark,
            "created_by": remark.created_by.username if remark.created_by else None,
            "created_at": remark.created_at.isoformat() if remark.created_at else None,
        })
    if remarks_list:
        stats["copies_with_remarks"] += 1
        stats["total_remarks"] += len(remarks_list)

    # --- Global appreciation ---
    if copy.global_appreciation:
        stats["copies_with_appreciation"] += 1

    # --- LLM summary ---
    if copy.llm_summary:
        stats["copies_with_llm_summary"] += 1

    # --- Pages (scanned images) ---
    page_paths = []
    for booklet in copy.booklets.all().order_by('start_page'):
        if booklet.pages_images:
            page_paths.extend(booklet.pages_images)
    pages_manifest[str(copy.id)] = {
        "anonymous_id": copy.anonymous_id,
        "exam": exam_name,
        "pages": page_paths,
        "pages_count": len(page_paths),
        "media_root": settings.MEDIA_ROOT,
    }

    # --- Build copy record ---
    copy_record = {
        "id": str(copy.id),
        "anonymous_id": copy.anonymous_id,
        "exam_name": exam_name,
        "exam_id": str(copy.exam.id),
        "status": copy.status,
        "student": student_info,
        "corrector": corrector_name,
        "subject_variant": copy.subject_variant,
        # Scores
        "total_score": total_score,
        "scores_data": scores_dict,
        "final_comment": final_comment,
        # Appreciation & LLM
        "global_appreciation": copy.global_appreciation or "",
        "llm_summary": copy.llm_summary or "",
        # Annotations
        "annotations": annotations_list,
        "annotations_count": len(annotations_list),
        # Remarks
        "question_remarks": remarks_list,
        "remarks_count": len(remarks_list),
        # Pages info
        "pages_count": len(page_paths),
        "pages_paths": page_paths,
        # Timestamps
        "graded_at": copy.graded_at.isoformat() if copy.graded_at else None,
        "assigned_at": copy.assigned_at.isoformat() if copy.assigned_at else None,
    }
    copies_data.append(copy_record)

# Write copies
with open(os.path.join(OUTPUT_DIR, "copies_data.json"), "w", encoding="utf-8") as f:
    json.dump(copies_data, f, indent=2, ensure_ascii=False, default=serialize_uuid)
print(f"  -> copies_data.json written ({len(copies_data)} copies)")

# Write pages manifest
with open(os.path.join(OUTPUT_DIR, "pages_manifest.json"), "w", encoding="utf-8") as f:
    json.dump(pages_manifest, f, indent=2, ensure_ascii=False, default=serialize_uuid)
print(f"  -> pages_manifest.json written ({len(pages_manifest)} entries)")

# Write summary
stats["extraction_date"] = datetime.now().isoformat()
with open(os.path.join(OUTPUT_DIR, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(stats, f, indent=2, ensure_ascii=False, default=serialize_uuid)
print(f"  -> summary.json written")

# =============================================================================
# 3. Print summary
# =============================================================================
print("\n" + "=" * 60)
print("EXTRACTION SUMMARY")
print("=" * 60)
print(f"Total copies:            {stats['total_copies']}")
print(f"Copies with scores:      {stats['copies_with_scores']}")
print(f"Copies with annotations: {stats['copies_with_annotations']}")
print(f"Copies with remarks:     {stats['copies_with_remarks']}")
print(f"Copies with appreciation:{stats['copies_with_appreciation']}")
print(f"Copies with LLM summary: {stats['copies_with_llm_summary']}")
print(f"Total annotations:       {stats['total_annotations']}")
print(f"Total remarks:           {stats['total_remarks']}")
print(f"\nBy exam: {json.dumps(stats['by_exam'])}")
print(f"By status: {json.dumps(stats['by_status'])}")
print(f"\nBy corrector:")
for c, v in sorted(stats['by_corrector'].items()):
    print(f"  {c}: {v['total']} copies, {v['with_scores']} with scores")
print(f"\nAll data written to {OUTPUT_DIR}/")
print(f"[{datetime.now().isoformat()}] Extraction complete.")
