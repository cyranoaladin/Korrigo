#!/usr/bin/env python3
"""
Full production rebuild v3:
- Clean seed data (copies, exams, seed students)
- Import students from CSV (full list)
- Create BB_J1 and BB_J2 exams
- Import all PDF copies with rasterization
- Match copies to students using eleves_terminale_maths.csv
- Assign correctors
"""
import os
import sys
import csv
import re
import unicodedata
from pathlib import Path
from datetime import datetime, date

sys.path.append(str(Path(__file__).resolve().parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files import File
from django.utils import timezone

from exams.models import Exam, Copy
from students.models import Student
from grading.services import GradingService
from grading.models import GradingEvent
from core.models import UserProfile

User = get_user_model()

SCAN_J1_DIR = Path("/tmp/scan_J1_BB_maths")
SCAN_J2_DIR = Path("/tmp/scan_J2_BB_maths")
CSV_J1 = Path("/tmp/eleves_maths_J1.csv")
CSV_J2 = Path("/tmp/eleves_maths_J2.csv")
CSV_FULL = Path("/tmp/eleves_terminale_maths.csv")


def sa(s):
    return unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('ASCII')

def norm(s):
    return re.sub(r'[^A-Z0-9_]', '', re.sub(r'[\s\-]+', '_', sa(s).upper().strip()))

def parse_dob(s):
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except ValueError:
        return date(2008, 1, 1)


def build_full_csv_index():
    """Build normalized name -> student info from the full CSV."""
    index = {}
    with open(CSV_FULL, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            full = row.get('Élèves', '').strip()
            email = row.get('Adresse E-mail', '').strip()
            dob_str = row.get('Né(e) le', '').strip()
            classe = row.get('Classe', '').strip()
            groupe = row.get('Groupe', '').strip()
            if not full or not email:
                continue
            parts = full.split()
            last = parts[0] if parts else full
            first = ' '.join(parts[1:]) if len(parts) > 1 else ''
            key = norm(full)
            index[key] = {
                'full': full, 'last': last, 'first': first,
                'email': email, 'dob': parse_dob(dob_str),
                'classe': classe, 'groupe': groupe,
            }
    return index


def clean_seed_data():
    """Remove seed data."""
    print("\n━━ CLEAN SEED DATA ━━")
    from exams.models import Booklet, ExamPDF
    GradingEvent.objects.all().delete()
    ExamPDF.objects.all().delete()
    Booklet.objects.all().delete()
    Copy.objects.all().delete()
    Exam.objects.all().delete()
    Student.objects.all().delete()
    print("  Cleaned: booklets, copies, exams, students, grading events")


def import_students(csv_index):
    """Import all students from the full CSV."""
    print("\n━━ IMPORT STUDENTS ━━")
    student_grp, _ = Group.objects.get_or_create(name='student')
    created_count = 0

    for key, info in csv_index.items():
        student, created = Student.objects.get_or_create(
            email=info['email'],
            defaults={
                'first_name': info['first'],
                'last_name': info['last'],
                'date_naissance': info['dob'],
                'class_name': info['classe'],
                'groupe': info['groupe'],
            }
        )
        if created:
            user = User.objects.create_user(
                username=info['email'],
                email=info['email'],
                password=os.environ.get('DEFAULT_PASSWORD', 'changeme')
            )
            user.groups.add(student_grp)
            student.user = user
            student.save()
            created_count += 1

    print("  Students: %d created, %d total" % (created_count, Student.objects.count()))


def create_exam(name, date_val):
    """Create an exam."""
    exam = Exam.objects.create(
        name=name,
        date=date_val,
        upload_mode=Exam.UploadMode.INDIVIDUAL_A4,
    )
    return exam


def import_copies(exam, scan_dir, csv_index, admin):
    """Import all PDF copies for an exam and match to students."""
    pdf_files = sorted(scan_dir.glob("copie_*.pdf"))
    print("  PDFs found: %d" % len(pdf_files))

    imported = 0
    matched = 0
    errors = []

    for i, pdf_path in enumerate(pdf_files, 1):
        try:
            with open(pdf_path, 'rb') as f:
                django_file = File(f, name=pdf_path.name)
                copy = GradingService.import_pdf(exam, django_file, admin)

            student_name = pdf_path.stem.replace("copie_", "")
            copy.anonymous_id = "%s-%s" % (exam.name, student_name)
            copy.status = Copy.Status.READY
            copy.validated_at = timezone.now()

            # Match to student using full CSV
            file_key = norm(student_name)
            info = csv_index.get(file_key)
            if info:
                try:
                    student = Student.objects.get(email=info['email'])
                    copy.student = student
                    copy.is_identified = True
                    matched += 1
                except Student.DoesNotExist:
                    pass

            copy.save()
            imported += 1

            if i % 20 == 0 or i == len(pdf_files):
                print("  [%d/%d] %d imported, %d matched" % (i, len(pdf_files), imported, matched))

        except Exception as e:
            errors.append((pdf_path.name, str(e)))

    if errors:
        print("  Errors (%d):" % len(errors))
        for name, err in errors[:5]:
            print("    - %s: %s" % (name, err))

    return imported, matched


def assign_correctors():
    """Assign the real teachers as correctors."""
    print("\n━━ ASSIGN CORRECTORS ━━")
    j1_emails = [
        "alaeddine.benrhouma@ert.tn", "philippe.carr@ert.tn",
        "patrick.dupont@ert.tn", "selima.klibi@ert.tn",
    ]
    j2_emails = [
        "chawki.saadi@ert.tn", "sami.bentiba@ert.tn",
        "laroussi.laroussi@ert.tn", "edouard.rousseau@ert.tn",
    ]

    for exam_name, emails in [("BB_J1", j1_emails), ("BB_J2", j2_emails)]:
        try:
            exam = Exam.objects.get(name=exam_name)
            exam.correctors.clear()
            for email in emails:
                try:
                    exam.correctors.add(User.objects.get(username=email))
                except User.DoesNotExist:
                    print("  WARNING: teacher %s not found" % email)
            names = list(exam.correctors.values_list("last_name", flat=True))
            print("  %s correctors: %s" % (exam_name, names))
        except Exam.DoesNotExist:
            print("  ERROR: exam %s not found" % exam_name)


def main():
    print("=" * 60)
    print("FULL PRODUCTION REBUILD")
    print("=" * 60)

    admin = User.objects.get(username="admin")

    # Build CSV index
    csv_index = build_full_csv_index()
    print("Full CSV: %d students" % len(csv_index))

    # Clean
    clean_seed_data()

    # Import students
    import_students(csv_index)

    # Create exams
    print("\n━━ CREATE EXAMS ━━")
    exam_j1 = create_exam("BB_J1", date(2026, 2, 6))
    exam_j2 = create_exam("BB_J2", date(2026, 2, 10))
    print("  Created: BB_J1, BB_J2")

    # Import copies
    print("\n━━ IMPORT BB_J1 COPIES ━━")
    j1_imported, j1_matched = import_copies(exam_j1, SCAN_J1_DIR, csv_index, admin)

    print("\n━━ IMPORT BB_J2 COPIES ━━")
    j2_imported, j2_matched = import_copies(exam_j2, SCAN_J2_DIR, csv_index, admin)

    # Assign correctors
    assign_correctors()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("  Students: %d" % Student.objects.count())
    print("  BB_J1: %d copies (%d identified)" % (
        Copy.objects.filter(exam=exam_j1).count(),
        Copy.objects.filter(exam=exam_j1, is_identified=True).count()
    ))
    print("  BB_J2: %d copies (%d identified)" % (
        Copy.objects.filter(exam=exam_j2).count(),
        Copy.objects.filter(exam=exam_j2, is_identified=True).count()
    ))
    print("  Teachers: %d" % User.objects.filter(groups__name='teacher').count())
    print("  Admin: %s" % admin.username)
    print("=" * 60)


if __name__ == "__main__":
    main()
