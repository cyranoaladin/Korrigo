import os
import sys
import django
from decimal import Decimal

# Add backend directory to sys.path
sys.path.append('/home/alaeddine/viatique__PMF/backend')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from exams.models import Exam, Copy
from grading.models import QuestionScore, Annotation
from grading.services import GradingService
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

def verify_grading_flow():
    print("--- Starting Grading Flow Verification ---")
    
    # 1. Setup Data
    user, _ = User.objects.get_or_create(username="test_teacher", defaults={"email": "teacher@test.com"})
    exam, _ = Exam.objects.get_or_create(name="Test Exam Verification", defaults={"date": "2024-01-01"})
    
    copy_id = uuid.uuid4()
    copy = Copy.objects.create(
        id=copy_id,
        exam=exam,
        anonymous_id=f"TEST-{str(copy_id)[:8]}",
        status=Copy.Status.LOCKED  # Simulate ongoing grading
    )
    print(f"Created Copy: {copy.anonymous_id}")
    
    # 2. Add Scores (Simulate Sidebar Input)
    # Exercise 1.1: 2.5 pts
    qs1, _ = QuestionScore.objects.update_or_create(
        copy=copy,
        question_id="ex1.1",
        defaults={'score': 2.5, 'created_by': user}
    )
    # Exercise 1.2: 3.0 pts
    qs2, _ = QuestionScore.objects.update_or_create(
        copy=copy,
        question_id="ex1.2",
        defaults={'score': 3.0, 'created_by': user}
    )
    print(f"Added Scores: {qs1.score} + {qs2.score}")
    
    # 3. Add Annotation (Simulate Bonus)
    # Bonus: +1 pt
    ann = Annotation.objects.create(
        copy=copy,
        page_index=0,
        x=0.1, y=0.1, w=0.1, h=0.1,
        type=Annotation.Type.BONUS,
        score_delta=1,
        created_by=user
    )
    print(f"Added Annotation Bonus: {ann.score_delta}")
    
    # 4. Verify GradingService.compute_score
    total_score = GradingService.compute_score(copy)
    expected_score = 2.5 + 3.0 + 1.0
    
    print(f"Computed Total: {total_score}")
    print(f"Expected Total: {expected_score}")
    
    if abs(total_score - expected_score) < 0.01:
        print("✅ SUCCESS: Total Score Calculation is Correct")
    else:
        print("❌ FAILURE: Total Score mismatch!")
        
    # 5. Clean up
    copy.delete()
    exam.delete()
    print("--- Verification Complete ---")

if __name__ == "__main__":
    try:
        verify_grading_flow()
    except Exception as e:
        print(f"❌ ERROR: {e}")
