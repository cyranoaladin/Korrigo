import os
import django
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
import fitz # PyMuPDF
import shutil
import sys

# Setup Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, 'backend')
sys.path.append(BACKEND_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.conf import settings
# OVERRIDE SETTINGS FOR PROOFING (Simulate valid staging)
import tempfile
temp_media = tempfile.mkdtemp()
settings.MEDIA_ROOT = temp_media
settings.SECURE_SSL_REDIRECT = False
settings.SESSION_COOKIE_SECURE = False
settings.CSRF_COOKIE_SECURE = False
settings.ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
settings.DEBUG = True # To see errors if any


from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from exams.models import Exam, Copy
from grading.models import GradingEvent

User = get_user_model()

def create_real_pdf(path="test_real.pdf", pages=3):
    """Create a minimal real PDF using PyMuPDF"""
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"Page {i+1} - Real Content", fontsize=20)
    doc.save(path)
    doc.close()
    return path

def print_resp_debug(resp):
    try:
        print(f"Data: {resp.data}")
    except:
        print(f"Content: {resp.content.decode()}")

def run_proof():
    print(">>> 1. SETUP")
    # Clean media
    media_root = settings.MEDIA_ROOT
    print(f"MEDIA_ROOT (Override): {media_root}")
    
    # Create Users
    teacher, _ = User.objects.get_or_create(username="teacher_real", defaults={'is_staff': True})
    teacher.set_password('pass')
    teacher.save()
    
    student, _ = User.objects.get_or_create(username="student_real", defaults={'is_staff': False})
    
    # Create Exam
    exam = Exam.objects.create(name="ProdHardening Exam", date="2024-01-01")
    print(f"Exam: {exam.id}")

    # Create Real PDF
    pdf_path = create_real_pdf()
    print(f"Created real PDF: {pdf_path}")
    
    client = APIClient()

    print("\n>>> 2. AUTH MATRIX CHECKS")
    # 2.1 Anon -> 401/403 on Import
    resp = client.post(f"/api/exams/{exam.id}/copies/import/", {})
    print(f"Anon Import: {resp.status_code} (Expected 401/403)")
    if resp.status_code not in [401, 403]: print_resp_debug(resp)

    # 2.2 Student -> 403 on Import
    client.force_authenticate(user=student)
    resp = client.post(f"/api/exams/{exam.id}/copies/import/", {})
    print(f"Student Import: {resp.status_code} (Expected 403)")
    if resp.status_code != 403: print_resp_debug(resp)

    print("\n>>> 3. REAL IMPORT (TEACHER)")
    client.force_authenticate(user=teacher)
    with open(pdf_path, 'rb') as f:
        data = {'pdf_file': f}
        resp = client.post(f"/api/exams/{exam.id}/copies/import/", data, format='multipart')
    
    print(f"Teacher Import Status: {resp.status_code}")
    if resp.status_code != 201:
        print_resp_debug(resp)
        return

    copy_id = resp.data['id']
    print(f"Copy ID: {copy_id}")
    
    print("\n>>> 4. FILESYSTEM PROOF")
    copy = Copy.objects.get(id=copy_id)
    booklet = copy.booklets.first()
    print(f"Booklet Pages: {booklet.pages_images}")
    
    # Verify files exist
    for rel_path in booklet.pages_images:
        full_path = os.path.join(media_root, rel_path)
        exists = os.path.exists(full_path)
        size = os.path.getsize(full_path) if exists else 0
        print(f"File {rel_path}: Exists={exists}, Size={size} bytes")
        if not exists or size == 0:
            print("!!! FAILURE: Ghost file detected !!!")

    print("\n>>> 5. AUDIT TRAIL")
    events = GradingEvent.objects.filter(copy=copy).values_list('action', flat=True)
    print(f"Events: {list(events)}")
    
    print("\n>>> 6. FINAL PDF GATE")
    # LOCKED -> 403
    copy.status = 'LOCKED'
    copy.save()
    resp = client.get(f"/api/copies/{copy.id}/final-pdf/")
    print(f"LOCKED Final PDF: {resp.status_code} (Expected 403)")
    
    # GRADED -> 200 (if file existed)
    # We didn't generate final PDF here, but we check permission gate
    copy.status = 'GRADED'
    copy.save()
    # Mock file for download logic
    with open(pdf_path, 'rb') as f:
        copy.final_pdf.save('final.pdf', f)
    
    resp = client.get(f"/api/copies/{copy.id}/final-pdf/")
    print(f"GRADED Final PDF: {resp.status_code} (Expected 200)")

    # Clean up
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    # Don't clean up media to allow manual inspection if needed, or clean strict?
    # User asked for proofs, so keeping logs is key.

if __name__ == "__main__":
    run_proof()
