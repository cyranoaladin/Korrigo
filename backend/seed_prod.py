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

Security: Uses env vars for passwords or generates random secure passwords for local dev.
"""
import os
import django
import sys
from pathlib import Path
import secrets
import string

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

def generate_secure_password(length=24):
    """Generate a cryptographically secure random password."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def get_or_generate_password(env_var, default_for_local=None):
    """
    Get password from environment or generate a secure one.

    Args:
        env_var: Environment variable name (e.g., 'ADMIN_PASSWORD')
        default_for_local: Optional default for local dev (insecure, warns user)

    Returns:
        tuple: (password, is_generated)
    """
    password = os.environ.get(env_var)

    if password:
        return password, False

    # No env var set - check if we're in a dev/local context
    is_local = os.environ.get('DJANGO_ENV', 'development') != 'production'

    if is_local and default_for_local:
        print(f"  ⚠️  WARNING: Using default password for {env_var} (LOCAL DEV ONLY)")
        print(f"      DO NOT USE IN PRODUCTION!")
        return default_for_local, False

    # Generate secure random password
    generated = generate_secure_password()
    print(f"  🔐 Generated secure password for {env_var}")
    print(f"      Password: {generated}")
    print(f"      ⚠️  SAVE THIS - it won't be shown again!")
    return generated, True

def seed_prod():
    """
    Idempotent production seed.
    """
    print("🌱 Starting Production Seed (Idempotent)...")

    # 0. Create Groups
    print("\n👥 Creating User Groups...")
    teacher_group, _ = Group.objects.get_or_create(name='teacher')
    admin_group, _ = Group.objects.get_or_create(name='admin')
    student_group, _ = Group.objects.get_or_create(name='student')
    print(f"  ✓ Groups ready: teacher, admin, student")

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
        # Secure password handling: env var or generated
        admin_password, was_generated = get_or_generate_password(
            'ADMIN_PASSWORD',
            default_for_local='admin'  # Only for local dev
        )
        admin.set_password(admin_password)
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

    # Get professor password once (same for all profs in local dev)
    prof_password, was_generated = get_or_generate_password(
        'TEACHER_PASSWORD',
        default_for_local='prof'  # Only for local dev
    )

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
            prof.set_password(prof_password)
            prof.save()
            print(f"  ✓ Created professor: {prof.username}")
        else:
            print(f"  ↻ Professor already exists: {prof.username}")

        # Add to teacher group
        if not prof.groups.filter(name='teacher').exists():
            prof.groups.add(teacher_group)
            print(f"    ✓ Added {prof.username} to teacher group")

        professors.append(prof)

    # 3. Create Students (with User accounts)
    print("\n👨‍🎓 Creating Students...")
    students = []

    # Get student password once (same for all students in local dev)
    student_password, was_generated = get_or_generate_password(
        'STUDENT_PASSWORD',
        default_for_local='eleve'  # Only for local dev
    )

    for i in range(1, 11):  # 10 students
        email = f'eleve{i}@viatique.local'

        # Create User Django first
        user, user_created = User.objects.get_or_create(
            username=f'student_INE{i:03d}PROD',
            defaults={
                'email': email,
                'first_name': f'Élève{i}',
                'last_name': f'Dupont{i}',
                'is_staff': False,
                'is_superuser': False,
            }
        )
        if user_created:
            user.set_password(student_password)
            user.save()
            print(f"  ✓ Created user: {user.username}")
        else:
            print(f"  ↻ User already exists: {user.username}")

        # Add to student group
        if not user.groups.filter(name='student').exists():
            user.groups.add(student_group)
            print(f"    ✓ Added {user.username} to student group")

        # Create Student profile
        student, created = Student.objects.get_or_create(
            ine=f"INE{i:03d}PROD",
            defaults={
                'user': user,
                'first_name': f'Élève{i}',
                'last_name': f'Dupont{i}',
                'class_name': 'Terminale S',
                'email': email,
                'date_of_birth': date(2008, 1, min(i, 28)),  # Valid dates
            }
        )
        if created:
            print(f"  ✓ Created student: {student.ine} - {student.first_name} {student.last_name}")
        else:
            # Update user if needed (in case student existed but had no user)
            if student.user != user:
                student.user = user
                student.save(update_fields=['user'])
                print(f"  ↻ Student already exists, updated user: {student.ine}")
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

    # FAIL FAST: Verify PDF source exists
    if not exam.pdf_source:
        raise RuntimeError(
            "❌ CRITICAL: No PDF fixture found for exam. "
            "Cannot create annotatable copies. "
            "This is a P0 blocker for production validation."
        )

    for i in range(1, 4):
        # Check if copy already exists
        existing = Copy.objects.filter(anonymous_id=f"PROD-READY-{i}").first()

        needs_reimport = False
        if existing:
            print(f"  ↻ READY copy already exists: {existing.anonymous_id}")

            # ROBUST CHECK: Verify booklets AND pages_images
            has_valid_pages = False
            for booklet in existing.booklets.all():
                if booklet.pages_images and len(booklet.pages_images) > 0:
                    has_valid_pages = True
                    break

            if not has_valid_pages:
                print(f"    ⚠️  Copy has no booklets with pages_images, re-importing...")
                existing.delete()  # Delete and re-create
                needs_reimport = True
                existing = None

        if not existing or needs_reimport:
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

            # VALIDATION: Ensure pages > 0 (P0 requirement)
            if page_count <= 0:
                raise RuntimeError(
                    f"❌ CRITICAL: Copy {imported_copy.anonymous_id} created but has 0 pages. "
                    "PDF import failed. This breaks annotation workflow."
                )

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

    # Ensure GRADED copy has a PDF (use same fixture as exam)
    if not copy_graded.final_pdf:
        # Reuse the same fixture PDF used for exam (already verified to exist)
        with open(exam.pdf_source.path, 'rb') as f:
            copy_graded.final_pdf.save('prod_graded_copy.pdf', f, save=True)
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
    print("\n" + "="*60)
    print("🔐 IDENTIFIANTS CRÉÉS")
    print("="*60)
    print("\nADMIN:")
    print(f"  Username: admin")
    print(f"  Password: {os.environ.get('ADMIN_PASSWORD', 'admin')}")
    print("\nPROFESSEURS (x3):")
    print(f"  Username: prof1, prof2, prof3")
    print(f"  Email: prof1@viatique.local, prof2@..., prof3@...")
    print(f"  Password: {os.environ.get('TEACHER_PASSWORD', 'prof')}")
    print("\nÉTUDIANTS (x10):")
    print(f"  Email: eleve1@viatique.local, eleve2@..., ..., eleve10@...")
    print(f"  Password: {os.environ.get('STUDENT_PASSWORD', 'eleve')}")
    print("\n⚠️  IMPORTANT: Changer ces mots de passe en production!")
    print("="*60)

if __name__ == "__main__":
    seed_prod()
