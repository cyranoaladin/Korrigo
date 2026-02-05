import os
import django
import sys
from pathlib import Path

# Setup Django environment
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.core.files.base import ContentFile
from exams.models import Exam, Copy
from students.models import Student

def seed_gate4(student_email=None, student_lastname=None):
    """Seed Gate 4 data with parameterizable student credentials."""
    print("Seeding Gate 4 Data...")

    # Use env vars if not provided
    if student_email is None:
        student_email = os.environ.get("E2E_STUDENT_EMAIL", "e2e.student@test.com")
    if student_lastname is None:
        student_lastname = os.environ.get("E2E_STUDENT_LASTNAME", "E2E_STUDENT")

    # 1. Create Student
    student, created = Student.objects.get_or_create(
        email=student_email,
        defaults={
            "full_name": f"{student_lastname} Jean",
            "date_of_birth": "2008-01-15",
            "class_name": "TG2",
        }
    )
    print(f"Gate4: student_id={student.id} email={student.email} last={student.last_name} created={created}")
    
    # 2. Create Exam
    exam, _ = Exam.objects.get_or_create(name="Gate 4 Exam", date="2025-06-15")
    print(f"Gate4: exam_id={exam.id} name={exam.name} date={exam.date}")
    
    # 3. Create Copies
    
    # A) Graded & Owned (Should be visible & downloadable)
    copy_graded, _ = Copy.objects.get_or_create(
        exam=exam,
        anonymous_id="GATE4-GRADED",
        defaults={
            "status": Copy.Status.GRADED,
            "student": student,
            "is_identified": True
        }
    )
    # Ensure it is graded (idempotent seed)
    if copy_graded.status != Copy.Status.GRADED:
        copy_graded.status = Copy.Status.GRADED
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
            "status": Copy.Status.LOCKED,
            "student": student,
            "is_identified": True
        }
    )
    if copy_locked.status != Copy.Status.LOCKED:
        copy_locked.status = Copy.Status.LOCKED
        copy_locked.student = student
        copy_locked.is_identified = True
        copy_locked.save(update_fields=["status", "student", "is_identified"])
    print(f"Gate4: copy_locked={copy_locked.id} status={copy_locked.status} owner={copy_locked.student_id}")
    
    # C) Graded & Other (Should NOT be visible/downloadable)
    other_student, _ = Student.objects.get_or_create(
        email="other.student@test.com",
        defaults={
            "last_name": "OTHER",
            "first_name": "Student",
            "class_name": "TG2"
        }
    )
    copy_other, _ = Copy.objects.get_or_create(
        exam=exam,
        anonymous_id="GATE4-OTHER",
        defaults={
            "status": Copy.Status.GRADED,
            "student": other_student,
            "is_identified": True
        }
    )
    if copy_other.status != Copy.Status.GRADED:
        copy_other.status = Copy.Status.GRADED
        copy_other.student = other_student
        copy_other.is_identified = True
        copy_other.save(update_fields=["status", "student", "is_identified"])
    if not copy_other.final_pdf:
        copy_other.final_pdf.save("gate4_other.pdf", ContentFile(b"%PDF-1.4 Other"), save=True)
    print(f"Gate4: copy_other={copy_other.id} status={copy_other.status} owner={copy_other.student_id}")
    
    print("Seed Complete.")

if __name__ == "__main__":
    seed_gate4()
