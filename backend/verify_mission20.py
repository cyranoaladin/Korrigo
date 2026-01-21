from rest_framework.test import APIClient
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from exams.models import Exam, Copy

def run():
    print("--- Starting Verification ---")
    try:
        u = User.objects.get(username='alaeddine.benrhouma@ert.tn')
    except User.DoesNotExist:
        print("Admin user not found! Did init_pmf run?")
        return

    client = APIClient()
    client.force_authenticate(user=u)
    
    pdf = SimpleUploadedFile("dynamic_test.pdf", b"%PDF-1.4...", content_type="application/pdf")
    print("Uploading PDF...")
    resp = client.post('/api/exams/upload/', {'pdf_source': pdf, 'name': 'Dynamic Exam 2026', 'date': '2026-06-01'})
    
    print(f"Response Status: {resp.status_code}")
    
    if resp.status_code == 201:
        exam_id = resp.data['id']
        print(f"Exam Created: {resp.data['name']} ({exam_id})")
        
        copies = Copy.objects.filter(exam_id=exam_id)
        count = copies.count()
        print(f"Copies created: {count}")
        
        if count > 0:
            print("SUCCESS: Copies exist. Video-Coding will work.")
        else:
            print("FAILURE: Exam created but NO copies found.")
    else:
        print(f"FAILURE: Upload failed. Status: {resp.status_code}")
        try:
            print(f"Content: {resp.data}")
        except:
            print(f"Content: {resp.content.decode()}")

if __name__ == "__main__":
    run()
