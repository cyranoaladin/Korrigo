import os
import django
import sys
from pathlib import Path

# Setup Django environment
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from exams.models import Exam, Copy
from students.models import Student
from core.auth import UserRole

User = get_user_model()

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
    student_email = os.environ.get("E2E_STUDENT_EMAIL", "jean.e2e@example.com")
    other_student_email = os.environ.get("E2E_OTHER_STUDENT_EMAIL", "other.student@example.com")

    def birth_password(date_value):
        return date_value.strftime("%d%m%Y")

    def ensure_student_user(email, password, username):
        student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={"email": email}
        )
        user.email = email
        user.set_password(password)
        user.is_staff = False
        user.is_superuser = False
        user.save()
        user.groups.add(student_group)
        return user

    # 1. Create Student
    student, created = Student.objects.get_or_create(
        first_name=student_firstname,
        last_name=student_lastname,
        date_naissance=student_date_naissance,
        defaults={
            "class_name": "Terminale S",
            "email": student_email
        }
    )
    student_password = birth_password(student.date_naissance)
    student_user = ensure_student_user(student_email, student_password, "student_e2e")
    student.email = student_email
    student.user = student_user
    student.class_name = student.class_name or "Terminale S"
    student.save(update_fields=["email", "user", "class_name"])
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
    other_student, _ = Student.objects.get_or_create(
        first_name="Student",
        last_name="OTHER",
        date_naissance="2005-05-20",
        defaults={
            "class_name": "Terminale S",
            "email": other_student_email
        }
    )
    other_student_password = birth_password(other_student.date_naissance)
    other_student_user = ensure_student_user(other_student_email, other_student_password, "other_student")
    other_student.email = other_student_email
    other_student.user = other_student_user
    other_student.class_name = other_student.class_name or "Terminale S"
    other_student.save(update_fields=["email", "user", "class_name"])
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
