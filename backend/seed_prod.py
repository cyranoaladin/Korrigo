#!/usr/bin/env python3
"""
Production Seed Script - Idempotent
Creates realistic data for production validation:
- 3 professors (Django Users with is_staff=True)
- 10 students (students.Student model)
- 1 exam
- 3 copies READY
- 1 copy GRADED (with PDF)

Idempotent: Can be run multiple times without errors or duplicates.
"""
import os
import django
import sys
from pathlib import Path

# Setup Django environment
sys.path.append(str(Path(__file__).resolve().parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from exams.models import Exam, Copy
from students.models import Student
from datetime import date

User = get_user_model()

def seed_prod():
    """
    Idempotent production seed.
    """
    print("🌱 Starting Production Seed (Idempotent)...")

    # 0. Create Groups
    print("\n👥 Creating User Groups...")
    teacher_group, _ = Group.objects.get_or_create(name='teacher')
    admin_group, _ = Group.objects.get_or_create(name='admin')
    print(f"  ✓ Groups ready: teacher, admin")

    # 1. Create Admin User
    print("\n📋 Creating Admin User...")
    admin, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@viatique.local',
            'is_staff': True,
            'is_superuser': True,
        }
    )
    if created:
        admin.set_password('admin')
        admin.save()
        print(f"  ✓ Created admin: {admin.username}")
    else:
        print(f"  ↻ Admin already exists: {admin.username}")

    # Add to admin group
    if not admin.groups.filter(name='admin').exists():
        admin.groups.add(admin_group)
        print(f"  ✓ Added {admin.username} to admin group")

    # 2. Create Professors
    print("\n👨‍🏫 Creating Professors...")
    professors = []
    for i in range(1, 4):  # 3 professors
        prof, created = User.objects.get_or_create(
            username=f'prof{i}',
            defaults={
                'email': f'prof{i}@viatique.local',
                'first_name': f'Professor{i}',
                'last_name': f'Smith{i}',
                'is_staff': True,
                'is_superuser': False,
            }
        )
        if created:
            prof.set_password('prof')
            prof.save()
            print(f"  ✓ Created professor: {prof.username}")
        else:
            print(f"  ↻ Professor already exists: {prof.username}")

        # Add to teacher group
        if not prof.groups.filter(name='teacher').exists():
            prof.groups.add(teacher_group)
            print(f"    ✓ Added {prof.username} to teacher group")

        professors.append(prof)

    # 3. Create Students
    print("\n👨‍🎓 Creating Students...")
    students = []
    for i in range(1, 11):  # 10 students
        student, created = Student.objects.get_or_create(
            ine=f"INE{i:03d}PROD",
            defaults={
                'first_name': f'Élève{i}',
                'last_name': f'Dupont{i}',
                'class_name': 'Terminale S',
                'email': f'eleve{i}@viatique.local',
            }
        )
        if created:
            print(f"  ✓ Created student: {student.ine} - {student.first_name} {student.last_name}")
        else:
            print(f"  ↻ Student already exists: {student.ine}")
        students.append(student)

    # 4. Create Exam
    print("\n📝 Creating Exam...")
    exam, created = Exam.objects.get_or_create(
        name='Prod Validation Exam - Bac Blanc Maths',
        defaults={
            'date': date.today(),
        }
    )
    if created:
        print(f"  ✓ Created exam: {exam.name} (ID: {exam.id})")
    else:
        print(f"  ↻ Exam already exists: {exam.name} (ID: {exam.id})")

    # Attach PDF if not present
    if not exam.pdf_source:
        # Try to find a fixture PDF
        backend_root = Path(__file__).parent
        fixture_candidates = [
            backend_root / 'grading/tests/fixtures/pdfs/copy_2p_simple.pdf',
            backend_root / 'test_exam.pdf',
        ]

        fixture_path = None
        for candidate in fixture_candidates:
            if candidate.exists():
                fixture_path = candidate
                break

        if fixture_path:
            with open(fixture_path, 'rb') as f:
                exam.pdf_source.save('exam_prod_validation.pdf', f, save=True)
            print(f"  ✓ Attached PDF to exam: {fixture_path.name}")
        else:
            print(f"  ⚠ Warning: No PDF fixture found, exam has no source PDF")

    # 5. Create Copies via Real Import Workflow (with page extraction)
    print("\n📄 Creating Copies via Import (with page extraction)...")

    # Import 3 READY copies using the real workflow
    from grading.services import GradingService
    from django.core.files import File

    for i in range(1, 4):
        # Check if copy already exists
        existing = Copy.objects.filter(anonymous_id=f"PROD-READY-{i}").first()

        if existing:
            print(f"  ↻ READY copy already exists: {existing.anonymous_id}")
            # Ensure it has booklets with pages (re-import if necessary)
            if not existing.booklets.exists():
                print(f"    ⚠️  Copy has no booklets, re-importing...")
                existing.delete()  # Delete and re-create
                existing = None

        if not existing and exam.pdf_source:
            # Import PDF to create copy with pages
            with open(exam.pdf_source.path, 'rb') as f:
                imported_copy = GradingService.import_pdf(exam, File(f), professors[0])

            # Set custom anonymous_id and status
            imported_copy.anonymous_id = f"PROD-READY-{i}"
            imported_copy.status = Copy.Status.READY
            imported_copy.save()

            # Verify booklets and pages
            booklet_count = imported_copy.booklets.count()
            page_count = sum([len(b.pages_images) if b.pages_images else 0 for b in imported_copy.booklets.all()])

            print(f"  ✓ Imported READY copy: {imported_copy.anonymous_id} (ID: {imported_copy.id})")
            print(f"    - Booklets: {booklet_count}, Pages: {page_count}")

    # Create 1 GRADED copy (with student identification)
    copy_graded, created = Copy.objects.get_or_create(
        exam=exam,
        anonymous_id="PROD-GRADED-1",
        defaults={
            'status': Copy.Status.GRADED,
            'student': students[0],  # Assign to first student
            'is_identified': True,
        }
    )
    if created:
        print(f"  ✓ Created GRADED copy: {copy_graded.anonymous_id} (ID: {copy_graded.id})")
    else:
        # Update status and student if different
        if copy_graded.status != Copy.Status.GRADED or copy_graded.student != students[0]:
            copy_graded.status = Copy.Status.GRADED
            copy_graded.student = students[0]
            copy_graded.is_identified = True
            copy_graded.save(update_fields=['status', 'student', 'is_identified'])
            print(f"  ↻ Updated GRADED copy: {copy_graded.anonymous_id}")
        else:
            print(f"  ↻ GRADED copy already exists: {copy_graded.anonymous_id}")

    # Ensure GRADED copy has a PDF
    if not copy_graded.final_pdf:
        # Create a minimal valid PDF (ASCII only)
        minimal_pdf = b"%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer << /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF\n"
        copy_graded.final_pdf.save('prod_graded_copy.pdf', ContentFile(minimal_pdf), save=True)
        print(f"  ✓ Attached PDF to GRADED copy: {copy_graded.id}")
    else:
        print(f"  ↻ GRADED copy already has PDF: {copy_graded.id}")

    # Summary
    print("\n" + "="*60)
    print("✅ Production Seed Completed Successfully!")
    print("="*60)
    print(f"  Admin: {admin.username}")
    print(f"  Professors: {', '.join([p.username for p in professors])}")
    print(f"  Students: {len(students)} students created")
    print(f"  Exam: {exam.name} (ID: {exam.id})")
    print(f"  Copies: 3 READY + 1 GRADED")
    print("\n📊 Database Summary:")
    print(f"  - Total Users: {User.objects.count()}")
    print(f"  - Total Students: {Student.objects.count()}")
    print(f"  - Total Exams: {Exam.objects.count()}")
    print(f"  - Total Copies: {Copy.objects.count()}")
    print(f"    - READY: {Copy.objects.filter(status=Copy.Status.READY).count()}")
    print(f"    - GRADED: {Copy.objects.filter(status=Copy.Status.GRADED).count()}")
    print(f"    - LOCKED: {Copy.objects.filter(status=Copy.Status.LOCKED).count()}")
    print("="*60)

if __name__ == "__main__":
    seed_prod()
