import os
import django
from pathlib import Path

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.core.files import File
from exams.models import Exam
from grading.models import Copy, Annotation, GradingEvent
from datetime import date

User = get_user_model()

def seed_e2e():
    """Deterministic E2E seeding - creates fresh test data"""
    
    print("🌱 Starting E2E seed...")
    
    # 1. Clear existing E2E data
    print("  Clearing existing data...")
    Copy.objects.all().delete()
    Exam.objects.all().delete()
    User.objects.filter(username__in=['admin', 'teacher', 'teacher2', 'student_e2e']).delete()
    
    # 2. Create users
    print("  Creating users...")
    admin = User.objects.create_superuser('admin', 'admin@test.com', 'admin')
    print(f"    ✓ Admin: {admin.username}")
    
    teacher = User.objects.create_user('teacher', 'teacher@test.com', 'teacher')
    teacher.is_staff = True
    teacher.save()
    print(f"    ✓ Teacher: {teacher.username}")

    teacher2 = User.objects.create_user('teacher2', 'teacher2@test.com', 'teacher')
    teacher2.is_staff = True
    teacher2.save()
    print(f"    ✓ Teacher 2: {teacher2.username}")
    
    student = User.objects.create_user('student_e2e', 'student@test.com', 'password')
    print(f"    ✓ Student: {student.username}")
    
    # 3. Create exam with fixture
    print("  Creating exam...")
    exam = Exam.objects.create(
        name='E2E Test Exam - Bac Blanc Maths',
        date=date.today()
    )
    
    # Attach PDF fixture
    # Attach PDF fixture
    # Path is relative to backend root (where this file is)
    backend_root = Path(__file__).parent
    fixture_path = backend_root / 'grading/tests/fixtures/pdfs/copy_2p_simple.pdf'
    fallback_path = backend_root / 'test_exam.pdf'
    
    final_pdf_path = None
    if fixture_path.exists():
        final_pdf_path = fixture_path
    elif fallback_path.exists():
        print(f"    ⚠ Warning: Main fixture not found at {fixture_path}, using fallback {fallback_path}")
        final_pdf_path = fallback_path
    else:
        print(f"    ⚠ Warning: No PDF fixture found at {fixture_path} or {fallback_path}")

    if final_pdf_path:
        with open(final_pdf_path, 'rb') as f:
            exam.pdf_source.save('exam_e2e.pdf', File(f), save=True)
        print(f"    ✓ Exam created with PDF: {exam.name} (ID: {exam.id})")
    
    # 4. Import copies (if PDF was attached)
    created_copy_ids = []
    if exam.pdf_source:
        print("  Importing copies from PDF...")
        from grading.services import GradingService
        service = GradingService()
        
        try:
            with open(exam.pdf_source.path, 'rb') as f:
                # import_pdf expects (exam, pdf_file, user) and returns a SINGLE Copy
                copy = service.import_pdf(exam, File(f), teacher)
                copies = [copy]
            
            created_copy_ids = [str(c.id) for c in copies]
            print(f"    ✓ Imported {len(copies)} copies")
            
            # Set first copy to READY for testing
            if copies:
                first_copy = copies[0]
                first_copy.status = 'READY'
                first_copy.save()
                print(f"    ✓ Set copy {first_copy.id} to READY status")
        except Exception as e:
            print(f"    ⚠ Import failed: {e}")
    
    print("✅ E2E seed completed successfully!")
    return {
        'admin': admin.id,
        'teacher': teacher.id,
        'teacher2': teacher2.id,
        'student': student.id,
        'exam': exam.id if exam else None,
        'copy_ids': created_copy_ids,
    }

if __name__ == "__main__":
    result = seed_e2e()
    print(f"\nCreated IDs: {result}")
