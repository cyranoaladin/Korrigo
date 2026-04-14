#!/usr/bin/env python3
"""
Import J1 copies into the existing BB_J1 exam.
Run inside the backend container: python import_j1_copies.py
"""
import os
import sys
import csv
import re
import unicodedata
from pathlib import Path
from datetime import date, datetime

sys.path.append(str(Path(__file__).resolve().parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from django.contrib.auth import get_user_model
from django.core.files import File
from django.utils import timezone

from exams.models import Exam, Copy
from students.models import Student
from grading.services import GradingService

User = get_user_model()

SCAN_J1_DIR = Path("/tmp/scan_J1_BB_maths")
CSV_J1 = Path("/tmp/eleves_maths_J1.csv")


def normalize_name(name: str) -> str:
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_name = nfkd.encode('ASCII', 'ignore').decode('ASCII').upper()
    ascii_name = re.sub(r'[\s\-]+', '_', ascii_name.strip())
    ascii_name = re.sub(r'[^A-Z0-9_]', '', ascii_name)
    return ascii_name


def filename_to_key(filename: str) -> str:
    name = filename.replace("copie_", "").replace(".pdf", "")
    nfkd = unicodedata.normalize('NFKD', name)
    return nfkd.encode('ASCII', 'ignore').decode('ASCII').upper()


def build_student_map():
    """Build key -> Student map from CSV J1 emails."""
    student_map = {}
    with open(CSV_J1, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            full_name = row.get('Élèves', '').strip()
            email = row.get('Adresse E-mail', '').strip()
            if not full_name or not email:
                continue
            key = normalize_name(full_name)
            try:
                student = Student.objects.get(email=email)
                student_map[key] = student
            except Student.DoesNotExist:
                pass
    return student_map


def main():
    print("=" * 60)
    print("📝 IMPORT J1 COPIES INTO BB_J1")
    print("=" * 60)

    # Get or verify exam
    try:
        exam = Exam.objects.get(name="BB_J1")
    except Exam.DoesNotExist:
        print("❌ Exam BB_J1 not found!")
        sys.exit(1)

    existing = Copy.objects.filter(exam=exam).count()
    if existing > 0:
        print(f"⚠ BB_J1 already has {existing} copies. Skipping.")
        return

    admin = User.objects.get(username="admin")
    student_map = build_student_map()
    print(f"  Student map: {len(student_map)} entries")

    pdf_files = sorted(SCAN_J1_DIR.glob("copie_*.pdf"))
    print(f"  PDF files: {len(pdf_files)}")

    imported = 0
    matched = 0
    errors = []

    for i, pdf_path in enumerate(pdf_files, 1):
        file_key = filename_to_key(pdf_path.name)
        student = student_map.get(file_key)

        try:
            with open(pdf_path, 'rb') as f:
                django_file = File(f, name=pdf_path.name)
                copy = GradingService.import_pdf(exam, django_file, admin)

            student_name = pdf_path.stem.replace("copie_", "")
            copy.anonymous_id = f"BB_J1-{student_name}"
            copy.status = Copy.Status.READY
            copy.validated_at = timezone.now()

            if student:
                copy.student = student
                copy.is_identified = True
                matched += 1

            copy.save()
            imported += 1

            if i % 10 == 0 or i == len(pdf_files):
                print(f"  [{i}/{len(pdf_files)}] {imported} imported, {matched} matched")

        except Exception as e:
            errors.append((pdf_path.name, str(e)))
            print(f"  ❌ {pdf_path.name}: {e}")

    print(f"\n✅ BB_J1: {imported} copies imported, {matched} matched to students")
    if errors:
        print(f"⚠ {len(errors)} errors:")
        for name, err in errors:
            print(f"  - {name}: {err}")

    # Final summary
    print(f"\n📊 Total copies in DB: {Copy.objects.count()}")
    print(f"  BB_J1: {Copy.objects.filter(exam__name='BB_J1').count()}")
    print(f"  BB_J2: {Copy.objects.filter(exam__name='BB_J2').count()}")


if __name__ == "__main__":
    main()
