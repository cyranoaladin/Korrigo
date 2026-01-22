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
    User.objects.filter(username__in=['admin', 'teacher', 'student_e2e']).delete()
    
    # 2. Create users
    print("  Creating users...")
    admin = User.objects.create_superuser('admin', 'admin@test.com', 'password')
    print(f"    ✓ Admin: {admin.username}")
    
    teacher = User.objects.create_user('teacher', 'teacher@test.com', 'password')
    teacher.is_staff = True
    teacher.save()
    print(f"    ✓ Teacher: {teacher.username}")
    
    student = User.objects.create_user('student_e2e', 'student@test.com', 'password')
    print(f"    ✓ Student: {student.username}")
    
    # 3. Create exam with fixture
    print("  Creating exam...")
    exam = Exam.objects.create(
        name='E2E Test Exam - Bac Blanc Maths',
        date=date.today()
    )
    
    # Attach PDF fixture
    fixture_path = Path(__file__).parent.parent / 'grading/tests/fixtures/pdfs/copy_2p_simple.pdf'
    if fixture_path.exists():
        with open(fixture_path, 'rb') as f:
            exam.pdf_source.save('exam_e2e.pdf', File(f), save=True)
        print(f"    ✓ Exam created: {exam.name} (ID: {exam.id})")
    else:
        print(f"    ⚠ Warning: Fixture not found at {fixture_path}")
    
    # 4. Import copies (if PDF was attached)
    if exam.pdf_source:
        print("  Importing copies from PDF...")
        from grading.services import GradingService
        service = GradingService()
        
        try:
            copies = service.import_pdf(exam.pdf_source.path, exam, teacher)
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
        'student': student.id,
        'exam': exam.id if exam else None,
    }

if __name__ == "__main__":
    result = seed_e2e()
    print(f"\nCreated IDs: {result}")
