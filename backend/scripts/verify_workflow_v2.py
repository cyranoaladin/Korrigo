
import os
import sys
import django
from unittest.mock import MagicMock, patch

# Setup Django
sys.path.append('/home/alaeddine/viatique__PMF/backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from exams.models import Exam, Copy, Booklet
from exams.services.dispatch import DispatchService
from processing.services.batch_processor import BatchA3Processor
from students.models import Student
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

def verify_workflow():
    print("=== STARTING EXAM WORKFLOW V2 VERIFICATION ===")
    
    # 1. Setup Data
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        admin = User.objects.create_superuser('admin_v2', 'admin@test.com', 'pass')
    
    corrector1 = User.objects.create_user('corr_1', 'c1@test.com', 'pass')
    corrector2 = User.objects.create_user('corr_2', 'c2@test.com', 'pass')
    
    print(f"[OK] Users setup: Admin={admin}, C1={corrector1}, C2={corrector2}")

    # 2. Create Exam with CSV
    csv_content = b"Nom,Date de naissance\nDoe John,01/01/2005"
    csv_file = SimpleUploadedFile("students.csv", csv_content, content_type="text/csv")
    
    exam = Exam.objects.create(
        name="Verif Exam V2",
        date="2024-06-15",
        student_csv=csv_file
    )
    exam.correctors.add(corrector1, corrector2)
    
    print(f"[OK] Exam created with CSV: {exam.student_csv.name}")
    
    # 3. Verify Adaptive Logic (Mocked)
    # We simulate that UploadView detected A3 and created copies
    print("--- Simulating Adaptive Upload (A3 detected) ---")
    
    # Create 4 dummy copies
    copies = []
    for i in range(4):
        c = Copy.objects.create(
            exam=exam,
            anonymous_id=f"ANON_{i}",
            status=Copy.Status.READY # Simulating validated copies
        )
        copies.append(c)
        
    print(f"[OK] Created {len(copies)} copies in READY status")
    
    # 4. Verify Dispatch Service
    print("--- Verifying Equitability Dispatch ---")
    
    assignments = DispatchService.dispatch_copies(exam)
    print(f"Dispatch Result: {assignments}")
    
    # Check distribution
    c1_count = Copy.objects.filter(exam=exam, assigned_corrector=corrector1).count()
    c2_count = Copy.objects.filter(exam=exam, assigned_corrector=corrector2).count()
    
    print(f"Corrector 1 has {c1_count} copies")
    print(f"Corrector 2 has {c2_count} copies")
    
    assert c1_count == 2
    assert c2_count == 2
    assert c1_count + c2_count == 4
    
    print("[SUCCESS] Dispatch is equitable (50/50)")

    # 5. Review OpenAI Service Import (Static check)
    from students.services.openai_identification import OpenAIService
    service = OpenAIService(api_key="fake-key")
    assert service.api_key == "fake-key"
    print("[SUCCESS] OpenAIService importable and instantiable")
    
    print("=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    try:
        verify_workflow()
    except Exception as e:
        print(f"[FAILED] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
