#!/usr/bin/env python3
"""
Production Rebuild Script
Recreates the production data after accidental volume cleanup:
- Cleans seed data
- Creates admin + teachers
- Imports students from CSV (J1 + J2)
- Creates exams BB_J1 and BB_J2
- Imports individual PDF copies with rasterization

Usage: docker compose exec backend python rebuild_production.py
"""
import os
import sys
import csv
import re
import unicodedata
from pathlib import Path
from datetime import date, datetime

# Setup Django
sys.path.append(str(Path(__file__).resolve().parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files import File
from django.db import transaction

from exams.models import Exam, Copy, Booklet, ExamPDF
from students.models import Student
from grading.services import GradingService
from grading.models import GradingEvent

User = get_user_model()

# ─── Configuration ───────────────────────────────────────────────────────────

# Paths inside the Docker container (files copied via docker compose cp)
SCAN_J1_DIR = Path("/tmp/scan_J1_BB_maths")
SCAN_J2_DIR = Path("/tmp/scan_J2_BB_maths")
CSV_J1 = Path("/tmp/eleves_maths_J1.csv")
CSV_J2 = Path("/tmp/eleves_maths_J2.csv")

EXAM_DATE_J1 = date(2026, 2, 6)
EXAM_DATE_J2 = date(2026, 2, 7)


def normalize_name(name: str) -> str:
    """
    Normalize a name for matching: uppercase, remove accents, replace hyphens/spaces.
    'BEN ABDESSALEM ELYES' -> 'BEN_ABDESSALEM_ELYES'
    """
    # Remove accents
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_name = nfkd.encode('ASCII', 'ignore').decode('ASCII')
    # Uppercase
    ascii_name = ascii_name.upper()
    # Replace spaces and hyphens with underscore
    ascii_name = re.sub(r'[\s\-]+', '_', ascii_name.strip())
    # Remove any other non-alphanumeric chars except underscore
    ascii_name = re.sub(r'[^A-Z0-9_]', '', ascii_name)
    return ascii_name


def filename_to_key(filename: str) -> str:
    """
    Extract normalized name from filename.
    'copie_BEN_ABDESSALEM_ELYES.pdf' -> 'BEN_ABDESSALEM_ELYES'
    """
    name = filename.replace("copie_", "").replace(".pdf", "")
    # Normalize accents
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_name = nfkd.encode('ASCII', 'ignore').decode('ASCII')
    return ascii_name.upper()


def csv_name_to_key(full_name: str) -> str:
    """
    Convert CSV full name to matching key.
    'BEN ABDESSALEM ELYES' -> 'BEN_ABDESSALEM_ELYES'
    """
    return normalize_name(full_name)


def parse_date(date_str: str) -> date:
    """Parse DD/MM/YYYY date string."""
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
    except ValueError:
        return date(2008, 1, 1)


def read_csv_students(csv_path: Path) -> list:
    """
    Read student CSV and return list of dicts.
    CSV format: Élèves,Né(e) le,Adresse E-mail,Classe,Groupe
    """
    students = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            full_name = row.get('Élèves', '').strip()
            if not full_name:
                continue
            parts = full_name.split(' ', 1)
            last_name = parts[0] if parts else full_name
            first_name = parts[1] if len(parts) > 1 else ''
            students.append({
                'full_name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'date_naissance': parse_date(row.get('Né(e) le', '')),
                'email': row.get('Adresse E-mail', '').strip(),
                'class_name': row.get('Classe', '').strip(),
                'groupe': row.get('Groupe', '').strip(),
                'key': csv_name_to_key(full_name),
            })
    return students


def setup_users():
    """Create admin and teacher users."""
    print("\n👥 Creating user groups...")
    admin_group, _ = Group.objects.get_or_create(name='admin')
    teacher_group, _ = Group.objects.get_or_create(name='teacher')
    student_group, _ = Group.objects.get_or_create(name='student')

    print("📋 Creating admin user...")
    admin, created = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@korrigo.tn', 'is_staff': True, 'is_superuser': True}
    )
    if created:
        admin.set_password(os.environ['DEFAULT_PASSWORD'])
        admin.save()
        admin.groups.add(admin_group)
        print("  ✓ Created admin (admin/<DEFAULT_PASSWORD>)")
    else:
        print("  ↻ Admin already exists")

    print("👨‍🏫 Creating teachers...")
    teachers = []
    teacher_data = [
        ('prof1', 'prof1@korrigo.tn', 'Professeur', 'Un'),
        ('prof2', 'prof2@korrigo.tn', 'Professeur', 'Deux'),
        ('prof3', 'prof3@korrigo.tn', 'Professeur', 'Trois'),
    ]
    for username, email, first, last in teacher_data:
        prof, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': first,
                'last_name': last,
                'is_staff': True,
                'is_superuser': False,
            }
        )
        if created:
            prof.set_password(os.environ['DEFAULT_PASSWORD'])
            prof.save()
            prof.groups.add(teacher_group)
            print(f"  ✓ Created {username}")
        else:
            print(f"  ↻ {username} already exists")
        teachers.append(prof)

    return admin, teachers


def import_students(csv_path: Path, label: str) -> dict:
    """
    Import students from CSV. Returns dict of key -> Student.
    Students are deduplicated by email.
    """
    print(f"\n👨‍🎓 Importing students from {label}...")
    csv_students = read_csv_students(csv_path)
    student_map = {}

    for s in csv_students:
        student, created = Student.objects.get_or_create(
            email=s['email'],
            defaults={
                'first_name': s['first_name'],
                'last_name': s['last_name'],
                'date_naissance': s['date_naissance'],
                'class_name': s['class_name'],
                'groupe': s['groupe'],
            }
        )
        if created:
            # Create linked Django User for student login
            grp, _ = Group.objects.get_or_create(name='student')
            user = User.objects.create_user(
                username=s['email'],
                email=s['email'],
                password=os.environ.get('DEFAULT_PASSWORD', 'changeme')
            )
            user.groups.add(grp)
            student.user = user
            student.save()

        student_map[s['key']] = student
        if created:
            print(f"  ✓ {s['full_name']} ({s['email']})")

    print(f"  Total: {len(student_map)} students imported for {label}")
    return student_map


def create_exam_with_copies(exam_name: str, exam_date: date, scan_dir: Path,
                            student_map: dict, admin_user) -> Exam:
    """
    Create an exam and import all individual PDF copies.
    """
    print(f"\n📝 Creating exam: {exam_name}...")

    exam, created = Exam.objects.get_or_create(
        name=exam_name,
        defaults={
            'date': exam_date,
            'upload_mode': Exam.UploadMode.INDIVIDUAL_A4,
        }
    )
    if created:
        print(f"  ✓ Created exam: {exam_name} (ID: {exam.id})")
    else:
        print(f"  ↻ Exam already exists: {exam_name} (ID: {exam.id})")
        # Check if copies already exist
        existing_copies = Copy.objects.filter(exam=exam).count()
        if existing_copies > 0:
            print(f"  ⚠ Exam already has {existing_copies} copies, skipping import")
            return exam

    # List all PDFs in scan directory
    pdf_files = sorted(scan_dir.glob("copie_*.pdf"))
    print(f"  Found {len(pdf_files)} PDF files to import")

    imported = 0
    matched = 0
    errors = []

    for i, pdf_path in enumerate(pdf_files, 1):
        file_key = filename_to_key(pdf_path.name)

        # Try to match with a student
        student = student_map.get(file_key)

        try:
            with open(pdf_path, 'rb') as f:
                django_file = File(f, name=pdf_path.name)
                copy = GradingService.import_pdf(exam, django_file, admin_user)

            # Set anonymous_id from filename
            student_name = pdf_path.stem.replace("copie_", "")
            copy.anonymous_id = f"{exam_name}-{student_name}"
            copy.status = Copy.Status.READY
            copy.validated_at = django.utils.timezone.now()

            if student:
                copy.student = student
                copy.is_identified = True
                matched += 1

            copy.save()
            imported += 1

            if i % 10 == 0 or i == len(pdf_files):
                print(f"  [{i}/{len(pdf_files)}] Imported {imported} copies ({matched} matched to students)")

        except Exception as e:
            errors.append((pdf_path.name, str(e)))
            print(f"  ❌ Error importing {pdf_path.name}: {e}")

    print(f"\n  ✅ {exam_name}: {imported} copies imported, {matched} matched to students")
    if errors:
        print(f"  ⚠ {len(errors)} errors:")
        for name, err in errors:
            print(f"    - {name}: {err}")

    return exam


def clean_seed_data():
    """Remove seed data before rebuilding."""
    print("\n🧹 Cleaning seed data...")

    # Delete seed copies and exams
    seed_copies = Copy.objects.filter(anonymous_id__startswith="PROD-")
    count = seed_copies.count()
    if count > 0:
        # Delete related booklets first
        for copy in seed_copies:
            copy.booklets.all().delete()
        seed_copies.delete()
        print(f"  ✓ Deleted {count} seed copies")

    seed_exams = Exam.objects.filter(name__startswith="Prod Validation")
    count = seed_exams.count()
    if count > 0:
        seed_exams.delete()
        print(f"  ✓ Deleted {count} seed exams")

    # Delete seed students (korrigo.local emails)
    seed_students = Student.objects.filter(email__endswith="@korrigo.local")
    count = seed_students.count()
    if count > 0:
        seed_students.delete()
        print(f"  ✓ Deleted {count} seed students")

    # Delete seed users (korrigo.local emails, but keep admin/profs)
    seed_users = User.objects.filter(email__endswith="@korrigo.local").exclude(
        username__in=['admin', 'prof1', 'prof2', 'prof3']
    )
    count = seed_users.count()
    if count > 0:
        seed_users.delete()
        print(f"  ✓ Deleted {count} seed users")

    # Delete grading events for deleted copies
    orphan_events = GradingEvent.objects.filter(copy__isnull=True)
    count = orphan_events.count()
    if count > 0:
        orphan_events.delete()
        print(f"  ✓ Deleted {count} orphan grading events")

    print("  ✓ Cleanup complete")


def main():
    print("=" * 60)
    print("🔧 PRODUCTION REBUILD SCRIPT")
    print("=" * 60)

    # Verify directories exist
    for d in [SCAN_J1_DIR, SCAN_J2_DIR]:
        if not d.exists():
            print(f"❌ FATAL: Directory not found: {d}")
            sys.exit(1)
    for f in [CSV_J1, CSV_J2]:
        if not f.exists():
            print(f"❌ FATAL: CSV not found: {f}")
            sys.exit(1)

    print(f"  scan_J1: {len(list(SCAN_J1_DIR.glob('copie_*.pdf')))} PDFs")
    print(f"  scan_J2: {len(list(SCAN_J2_DIR.glob('copie_*.pdf')))} PDFs")
    print(f"  CSV J1:  {CSV_J1}")
    print(f"  CSV J2:  {CSV_J2}")

    # 1. Clean seed data
    clean_seed_data()

    # 2. Setup users
    admin, teachers = setup_users()

    # 3. Import students
    student_map_j1 = import_students(CSV_J1, "J1")
    student_map_j2 = import_students(CSV_J2, "J2")

    # 4. Create exams and import copies
    exam_j1 = create_exam_with_copies(
        "BB_J1", EXAM_DATE_J1, SCAN_J1_DIR, student_map_j1, admin
    )

    exam_j2 = create_exam_with_copies(
        "BB_J2", EXAM_DATE_J2, SCAN_J2_DIR, student_map_j2, admin
    )

    # 5. Assign correctors to exams
    print("\n👨‍🏫 Assigning correctors to exams...")
    for exam in [exam_j1, exam_j2]:
        for teacher in teachers:
            exam.correctors.add(teacher)
        print(f"  ✓ {exam.name}: {exam.correctors.count()} correctors assigned")

    # 6. Summary
    print("\n" + "=" * 60)
    print("✅ PRODUCTION REBUILD COMPLETE")
    print("=" * 60)
    print(f"  Users:    {User.objects.count()}")
    print(f"  Students: {Student.objects.count()}")
    print(f"  Exams:    {Exam.objects.count()}")
    print(f"  Copies:   {Copy.objects.count()}")
    print(f"    BB_J1:  {Copy.objects.filter(exam=exam_j1).count()} copies")
    print(f"    BB_J2:  {Copy.objects.filter(exam=exam_j2).count()} copies")
    print(f"  Booklets: {Booklet.objects.count()}")
    print("=" * 60)
    print("\n📌 Credentials:")
    print("  Admin:   admin / <DEFAULT_PASSWORD>")
    print("  Prof:    prof1 / <DEFAULT_PASSWORD>  (also prof2, prof3)")
    print("  Élèves:  <email> / <DEFAULT_PASSWORD>")


if __name__ == "__main__":
    main()
