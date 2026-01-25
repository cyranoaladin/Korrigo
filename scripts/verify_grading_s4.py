import requests
import sys
import os
import time

BASE_URL = "http://127.0.0.1:8088"
API_LOGIN = f"{BASE_URL}/api/login/"
API_EXAMS = f"{BASE_URL}/api/exams/"

def create_dummy_pdf(filename="grading_test.pdf"):
    # Minimal 1-page PDF
    content = (
        b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        b"2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
        b"3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 595 842]\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/Contents 5 0 R\n>>\nendobj\n"
        b"4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n"
        b"5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Grading Test PDF) Tj\nET\nendstream\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n0000000300 00000 n \n0000000390 00000 n \ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n500\n%%EOF"
    )
    with open(filename, "wb") as f:
        f.write(content)
    return filename

def run_test():
    session = requests.Session()
    session.get(f"{BASE_URL}/admin/")
    csrf = session.cookies.get('csrftoken')
    headers = {'X-CSRFToken': csrf, 'Referer': BASE_URL}

    print("\n[1] LOGIN TEACHER...")
    resp = session.post(API_LOGIN, json={'username': 'prof1', 'password': 'password'}, headers=headers)
    if resp.status_code != 200:
        print(f"FAIL: Login failed {resp.status_code}")
        return False
    
    # Refresh CSRF
    csrf = session.cookies.get('csrftoken')
    headers['X-CSRFToken'] = csrf

    print("\n[2] SETUP EXAM & IMPORT COPY (S2/S3)...")
    resp = session.post(API_EXAMS, json={"name": "S4 Grading Exam", "date": "2026-08-01"}, headers=headers)
    exam_id = resp.json()['id']
    
    # Upload PDF
    pdf_path = create_dummy_pdf()
    api_import = f"{BASE_URL}/api/exams/{exam_id}/copies/import/"
    with open(pdf_path, 'rb') as f:
        files =({'pdf_file': (os.path.basename(pdf_path), f, 'application/pdf')})
        resp = session.post(api_import, files=files, headers={'X-CSRFToken': csrf, 'Referer': BASE_URL})
    
    if resp.status_code != 201:
        print(f"FAIL: Import failed ({resp.status_code})")
        return False
    
    copy_data = resp.json()
    copy_id = copy_data['id']
    print(f"PASS: Copy {copy_id} created (STAGING).")

    print("\n[3] TRANSITION TO READY...")
    # Endpoint: POST /api/copies/<id>/ready/
    api_ready = f"{BASE_URL}/api/copies/{copy_id}/ready/"
    resp = session.post(api_ready, headers=headers)
    
    if resp.status_code != 200:
        print(f"FAIL: Ready transition failed ({resp.status_code}) - {resp.text}")
        return False
    
    print(f"PASS: Copy status is {resp.json().get('status')}")

    print("\n[3.5] ACQUIRE LOCK (Soft Lock)...")
    api_lock = f"{BASE_URL}/api/copies/{copy_id}/lock/"
    resp = session.post(api_lock, headers=headers)
    if resp.status_code not in [200, 201]:
         print(f"FAIL: Lock acquisition failed ({resp.status_code}) - {resp.text}")
         return False
    print("PASS: Lock acquired.")

    print("\n[4] ANNOTATE (GRADE)...")
    # Endpoint: POST /api/copies/<id>/annotations/
    api_annotate = f"{BASE_URL}/api/copies/{copy_id}/annotations/"
    payload = {
        "x": 0.5, "y": 0.5, "w": 0.1, "h": 0.1,
        "page_index": 0,
        "score_delta": 5,
        "type": "score",
        "content": "Good job"
    }
    resp = session.post(api_annotate, json=payload, headers=headers)
    
    if resp.status_code != 201:
        print(f"FAIL: Annotation failed ({resp.status_code}) - {resp.text}")
        return False
    
    ann_id = resp.json()['id']
    print(f"PASS: Annotation created (Score +5). ID: {ann_id}")

    print("\n[5] FINALIZE (GRADED)...")
    # Endpoint: POST /api/copies/<id>/finalize/ (Requires LOCKED usually? Or Ready?)
    # Service says: LOCKED or READY.
    
    # Let's try direct Finalize from READY.
    api_finalize = f"{BASE_URL}/api/copies/{copy_id}/finalize/"
    resp = session.post(api_finalize, headers=headers)
    
    if resp.status_code != 200:
        print(f"FAIL: Finalize failed ({resp.status_code}) - {resp.text}")
        return False
    
    data = resp.json()
    print(f"PASS: Copy Finalized. Status: {data.get('status')}")
    
    # Optionally Verify Student View? 
    # Requires assigning student... we skipped that in S2. 
    # We can rely on 'status': 'GRADED' for S4 scope.

    return True

if __name__ == "__main__":
    if run_test():
        print("\nOVERALL: SUCCESS")
    else:
        print("\nOVERALL: FAILURE")
