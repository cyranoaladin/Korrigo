import requests
import sys
import os

BASE_URL = "http://127.0.0.1:8088"
API_LOGIN = f"{BASE_URL}/api/login/"
API_EXAMS = f"{BASE_URL}/api/exams/"

def get_csrf_token(session):
    try:
        response = session.get(f"{BASE_URL}/api/me/")
        if 'csrftoken' in session.cookies:
            return session.cookies['csrftoken']
    except:
        pass
    return None

def create_dummy_pdf(filename="dummy_subject.pdf"):
    # Create 4-page PDF to satisfy PDFSplitter (4 pages per booklet)
    # Using simple minimal PDF structure with 4 pages
    content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        b"2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R 5 0 R 7 0 R 9 0 R]\n/Count 4\n>>\nendobj\n"
        # Page 1
        b"3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 595 842]\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/Contents 11 0 R\n>>\nendobj\n"
        # Page 2
        b"5 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 595 842]\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/Contents 12 0 R\n>>\nendobj\n"
        # Page 3
        b"7 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 595 842]\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/Contents 13 0 R\n>>\nendobj\n"
        # Page 4
        b"9 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 595 842]\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/Contents 14 0 R\n>>\nendobj\n"
        # Font
        b"4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n"
        # Contents
        b"11 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Page 1) Tj\nET\nendstream\nendobj\n"
        b"12 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Page 2) Tj\nET\nendstream\nendobj\n"
        b"13 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Page 3) Tj\nET\nendstream\nendobj\n"
        b"14 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Page 4) Tj\nET\nendstream\nendobj\n"
        b"xref\n0 15\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000140 00000 n \n0000000600 00000 n \n0000000250 00000 n \n0000000000 00000 f \n0000000360 00000 n \n0000000000 00000 f \n0000000470 00000 n \n0000000000 00000 f \n0000000700 00000 n \n0000000800 00000 n \n0000000900 00000 n \n0000001000 00000 n \ntrailer\n<<\n/Size 15\n/Root 1 0 R\n>>\nstartxref\n1100\n%%EOF"
    )
    with open(filename, "wb") as f:
        f.write(content)
    return filename

def run_test():
    session = requests.Session()
    session.get(f"{BASE_URL}/admin/") # Seed CSRF
    csrf = session.cookies.get('csrftoken')
    headers = {'X-CSRFToken': csrf, 'Referer': BASE_URL}

    print("\n[1] LOGIN TEACHER (prof1)...")
    resp = session.post(API_LOGIN, json={'username': 'prof1', 'password': 'password'}, headers=headers)
    if resp.status_code != 200:
        print(f"FAIL: Login failed ({resp.status_code})")
        return False
    print("PASS: Logged in.")

    # Refresh CSRF token (Rotated on login)
    csrf = session.cookies.get('csrftoken')
    headers['X-CSRFToken'] = csrf

    print("\n[2] CREATE EXAM...")
    exam_data = {
        "name": "Maths Validation S2",
        "date": "2026-06-15"
    }
    resp = session.post(API_EXAMS, json=exam_data, headers=headers)
    if resp.status_code != 201:
        print(f"FAIL: Create Exam failed ({resp.status_code}) - {resp.text}")
        return False
    exam = resp.json()
    exam_id = exam['id']
    print(f"PASS: Exam Created (ID: {exam_id})")

    print("\n[3] UPLOAD SUBJECT PDF...")
    pdf_path = create_dummy_pdf()
    api_upload = f"{BASE_URL}/api/exams/{exam_id}/upload/"
    
    # We need to re-fetch CSRF maybe? Or reuse. Session keeps it.
    # Note: Requests automatically sets multipart header if files provided, 
    # BUT we must NOT set Content-Type manually then.
    # We need to set X-CSRFToken though.
    
    with open(pdf_path, 'rb') as f:
        files = {'pdf_source': (os.path.basename(pdf_path), f, 'application/pdf')}
        # Don't set Content-Type in headers, requests does it with boundary
        upload_headers = {'X-CSRFToken': csrf, 'Referer': BASE_URL}
        
        resp = session.post(api_upload, files=files, headers=upload_headers)
    
    if resp.status_code != 201:
        print(f"FAIL: Upload failed ({resp.status_code}) - {resp.text}")
        return False
    
    data = resp.json()
    print(f"PASS: Upload Successful. Message: {data.get('message')}")
    print(f"      Booklets Created: {data.get('booklets_created')}")

    print("\n[4] VERIFY BOOKLETS & COPIES (STAGING)...")
    # Check Booklets
    resp = session.get(f"{BASE_URL}/api/exams/{exam_id}/booklets/")
    data = resp.json()
    
    if 'results' in data:
        booklets = data['results']
        print(f"INFO: Found {data['count']} booklets (Pagination active).")
    else:
        booklets = data
        print(f"INFO: Found {len(booklets)} booklets.")
    
    # Check Copies
    resp = session.get(f"{BASE_URL}/api/exams/{exam_id}/copies/")
    data = resp.json()
    
    if 'results' in data:
        copies = data['results']
        print(f"INFO: Found {data['count']} copies (Pagination active).")
    else:
        copies = data
        print(f"INFO: Found {len(copies)} copies.")
    
    if len(copies) > 0:
        sample = copies[0]
        print(f"PASS: Copy {sample['anonymous_id']} status is {sample['status']}")
        if sample['status'] == 'STAGING':
            print("PASS: Status is correctly STAGING.")
        else:
             print(f"WARN: Expected STAGING, got {sample['status']}")
    else:
        print("FAIL: No copies found!")
        # Don't fail the whole test if this part fails? 
        # Actually we expect copies if splitting worked.
        return False

    print("\n[5] DEFINE GRID (Barème)...")
    grading_data = {
        "grading_structure": [
            {"id": "Q1", "label": "Question 1", "max_points": 5, "type": "number"},
            {"id": "Q2", "label": "Question 2", "max_points": 10, "type": "number"}
        ]
    }
    resp = session.patch(f"{BASE_URL}/api/exams/{exam_id}/", json=grading_data, headers=headers)
    if resp.status_code != 200:
        print(f"FAIL: Update Grid failed ({resp.status_code}) - {resp.text}")
        return False
    
    # Verify persistence
    resp = session.get(f"{BASE_URL}/api/exams/{exam_id}/", headers=headers)
    exam = resp.json()
    if len(exam.get('grading_structure', [])) == 2:
        print(f"PASS: Grading Structure updated. {exam['grading_structure']}")
    else:
        print(f"FAIL: Grading Structure did not persist. Got: {exam.get('grading_structure')}")
        return False

    return True

if __name__ == "__main__":
    if run_test():
        print("\nOVERALL: SUCCESS")
    else:
        print("\nOVERALL: FAILURE")
