import uuid
from datetime import date
from django.core.files.base import ContentFile
from exams.models import Exam, Booklet, Copy

def run():
    exam_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
    
    # 1. Create Exam
    exam, created = Exam.objects.get_or_create(
        id=exam_id,
        defaults={
            'name': 'Bac Blanc Maths (Demo)',
            'date': date.today(),
            'is_processed': True
        }
    )
    if created:
        print(f"Created Exam: {exam.name} ({exam.id})")
    else:
        print(f"Exam already exists: {exam.name}")

    # 2. Create Bundles/Copies for Video Coding
    # We need a Copy that is NOT identified
    
    # Copy 1
    copy1, c_created = Copy.objects.get_or_create(
        exam=exam,
        anonymous_id='ANON-001',
        defaults={'status': Copy.Status.READY, 'is_identified': False}
    )
    
    # Create Booklet for Copy 1 (needed for header image visualization)
    booklet1, b_created = Booklet.objects.get_or_create(
        id=uuid.uuid4(),
        exam=exam,
        start_page=1,
        end_page=4,
        defaults={'student_name_guess': 'Unknown'}
    )
    # Assign booklet to copy
    copy1.booklets.add(booklet1)
    
    # We ideally need a dummy image for the header_image field so the frontend doesn't break
    # But creating a real image file programmatically is verbose.
    # The frontend checks `header_url`. If None, it might show broken image.
    # Let's trust the frontend handles nulls or we provide a placeholder if possible.
    
    print(f"Created/Verified Copy {copy1.anonymous_id} (Identified: {copy1.is_identified})")

    # Copy 2
    copy2, _ = Copy.objects.get_or_create(
        exam=exam,
        anonymous_id='ANON-002',
        defaults={'status': Copy.Status.READY, 'is_identified': False}
    )
    booklet2 = Booklet.objects.create(exam=exam, start_page=5, end_page=8)
    copy2.booklets.add(booklet2)
    print(f"Created Copy {copy2.anonymous_id}")

if __name__ == '__main__':
    run()
