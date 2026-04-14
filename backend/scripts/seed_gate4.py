import os
import django
import sys
from pathlib import Path

# Setup Django environment
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.core.files.base import ContentFile
from django.contrib.auth.models import Group, User
from core.auth import UserRole
from core.models import UserProfile
from exams.models import Exam, Copy
from students.models import Student

def seed_gate4(student_date_naissance=None, student_lastname=None, student_firstname=None):
    """Seed Gate 4 data with parameterizable student credentials."""
    print("Seeding Gate 4 Data...")

    # Use env vars if not provided
    if student_date_naissance is None:
        student_date_naissance = os.environ.get("E2E_STUDENT_DOB", "2005-03-15")
    if student_lastname is None:
        student_lastname = os.environ.get("E2E_STUDENT_LASTNAME", "E2E_STUDENT")
    if student_firstname is None:
        student_firstname = os.environ.get("E2E_STUDENT_FIRSTNAME", "Jean")
    student_email = os.environ.get("E2E_STUDENT_EMAIL", "jean.e2e@example.com").strip().lower()
    student_password = os.environ.get("E2E_STUDENT_PASSWORD", "StudentE2E!2026")

    student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)

    student_user, _ = User.objects.get_or_create(
        username=student_email,
        defaults={
            "email": student_email,
            "first_name": student_firstname[:30],
            "last_name": student_lastname[:30],
            "is_active": True,
        },
    )
    student_user.email = student_email
    student_user.first_name = student_firstname[:30]
    student_user.last_name = student_lastname[:30]
    student_user.set_password(student_password)
    student_user.is_active = True
    student_user.save()
    student_user.groups.add(student_group)

    profile, _ = UserProfile.objects.get_or_create(user=student_user)
    if profile.must_change_password:
        profile.must_change_password = False
        profile.save(update_fields=["must_change_password"])

    # 1. Create Student
    student, created = Student.objects.get_or_create(
        first_name=student_firstname,
        last_name=student_lastname,
        date_naissance=student_date_naissance,
        defaults={
            "class_name": "Terminale S",
            "email": student_email,
            "user": student_user,
        }
    )
    updates = []
    if student.email != student_email:
        student.email = student_email
        updates.append("email")
    if student.user_id != student_user.id:
        student.user = student_user
        updates.append("user")
    if updates:
        student.save(update_fields=updates)
    print(f"Gate4: student_id={student.id} name={student.first_name} {student.last_name} dob={student.date_naissance} created={created}")
    
    # 2. Create Exam
    exam, _ = Exam.objects.get_or_create(name="Gate 4 Exam", date="2025-06-15")
    print(f"Gate4: exam_id={exam.id} name={exam.name} date={exam.date}")
    
    # 3. Create Copies
    
    # A) Graded & Owned (Should be visible & downloadable)
    copy_graded, _ = Copy.objects.get_or_create(
        exam=exam,
        anonymous_id="GATE4-GRADED",
        defaults={
            "status": Copy.Status.FINALIZED,
            "student": student,
            "is_identified": True
        }
    )
    # Ensure it is graded (idempotent seed)
    if copy_graded.status != Copy.Status.FINALIZED:
        copy_graded.status = Copy.Status.FINALIZED
        copy_graded.student = student
        copy_graded.is_identified = True
        copy_graded.save(update_fields=["status", "student", "is_identified"])

    # Ensure it has a PDF
    if not copy_graded.final_pdf:
        copy_graded.final_pdf.save("gate4_graded.pdf", ContentFile(b"%PDF-1.4 Mock Content"), save=True)
    try:
        pdf_size = copy_graded.final_pdf.size
    except Exception:
        pdf_size = None
    print(f"Gate4: copy_graded={copy_graded.id} status={copy_graded.status} pdf={bool(copy_graded.final_pdf)} size={pdf_size}")
    
    # B) Locked & Owned (Should NOT be visible in 'copies' list for student, nor downloadable)
    copy_locked, _ = Copy.objects.get_or_create(
        exam=exam,
        anonymous_id="GATE4-LOCKED",
        defaults={
            "status": Copy.Status.IN_PROGRESS,
            "student": student,
            "is_identified": True
        }
    )
    if copy_locked.status != Copy.Status.IN_PROGRESS:
        copy_locked.status = Copy.Status.IN_PROGRESS
        copy_locked.student = student
        copy_locked.is_identified = True
        copy_locked.save(update_fields=["status", "student", "is_identified"])
    print(f"Gate4: copy_locked={copy_locked.id} status={copy_locked.status} owner={copy_locked.student_id}")
    
    # C) Graded & Other (Should NOT be visible/downloadable)
    other_student_user, _ = User.objects.get_or_create(
        username="other.e2e@example.com",
        defaults={
            "email": "other.e2e@example.com",
            "first_name": "Student",
            "last_name": "OTHER",
            "is_active": True,
        },
    )
    other_student_user.set_password("OtherStudentE2E!2026")
    other_student_user.save()
    other_student_user.groups.add(student_group)

    other_student, _ = Student.objects.get_or_create(
        first_name="Student",
        last_name="OTHER",
        date_naissance="2005-05-20",
        defaults={
            "class_name": "Terminale S",
            "email": "other.e2e@example.com",
            "user": other_student_user,
        }
    )
    other_updates = []
    if other_student.email != "other.e2e@example.com":
        other_student.email = "other.e2e@example.com"
        other_updates.append("email")
    if other_student.user_id != other_student_user.id:
        other_student.user = other_student_user
        other_updates.append("user")
    if other_updates:
        other_student.save(update_fields=other_updates)
    copy_other, _ = Copy.objects.get_or_create(
        exam=exam,
        anonymous_id="GATE4-OTHER",
        defaults={
            "status": Copy.Status.FINALIZED,
            "student": other_student,
            "is_identified": True
        }
    )
    if copy_other.status != Copy.Status.FINALIZED:
        copy_other.status = Copy.Status.FINALIZED
        copy_other.student = other_student
        copy_other.is_identified = True
        copy_other.save(update_fields=["status", "student", "is_identified"])
    if not copy_other.final_pdf:
        copy_other.final_pdf.save("gate4_other.pdf", ContentFile(b"%PDF-1.4 Other"), save=True)
    print(f"Gate4: copy_other={copy_other.id} status={copy_other.status} owner={copy_other.student_id}")
    
    print("Seed Complete.")

if __name__ == "__main__":
    seed_gate4()
