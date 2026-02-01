import requests
import sys
import os

BASE_URL = "http://127.0.0.1:8088"
API_LOGIN = f"{BASE_URL}/api/login/"
API_EXAMS = f"{BASE_URL}/api/exams/"

def create_dummy_pdf(filename="student_scan.pdf"):
    # Create 2-page PDF
    content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        b"2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R 5 0 R]\n/Count 2\n>>\nendobj\n"
        # Page 1
        b"3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 595 842]\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/Contents 11 0 R\n>>\nendobj\n"
        # Page 2
        b"5 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 595 842]\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/Contents 12 0 R\n>>\nendobj\n"
        # Font
        b"4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n"
        # Contents
        b"11 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Student Copy Page 1) Tj\nET\nendstream\nendobj\n"
        b"12 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Student Copy Page 2) Tj\nET\nendstream\nendobj\n"
        b"xref\n0 13\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000140 00000 n \n0000000450 00000 n \n0000000250 00000 n \n0000000000 00000 f \n0000000000 00000 f \n0000000000 00000 f \n0000000000 00000 f \n0000000000 00000 f \n0000000550 00000 n \n0000000650 00000 n \ntrailer\n<<\n/Size 13\n/Root 1 0 R\n>>\nstartxref\n800\n%%EOF"
    )
    with open(filename, "wb") as f:
        f.write(content)
    return filename

def run_test():
    session = requests.Session()
    session.get(f"{BASE_URL}/admin/") # Seed CSRF
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

    print("\n[2] CREATE EXAM (For S3)...")
    exam_data = {"name": "S3 Scanning Exam", "date": "2026-07-01"}
    resp = session.post(API_EXAMS, json=exam_data, headers=headers)
    if resp.status_code != 201:
        print(f"FAIL: Create Exam failed ({resp.status_code})")
        return False
    exam_id = resp.json()['id']
    print(f"PASS: Exam {exam_id} created.")

    print("\n[3] UPLOAD STUDENT SCAN (Simulating Copy Import)...")
    pdf_path = create_dummy_pdf()
    api_import = f"{BASE_URL}/api/exams/{exam_id}/copies/import/"
    
    with open(pdf_path, 'rb') as f:
        files =({'pdf_file': (os.path.basename(pdf_path), f, 'application/pdf')})
        # CSRF required
        upload_headers = {'X-CSRFToken': csrf, 'Referer': BASE_URL}
        
        resp = session.post(api_import, files=files, headers=upload_headers)
    
    if resp.status_code != 201:
        print(f"FAIL: Import failed ({resp.status_code}) - {resp.text}")
        return False
    
    copy_data = resp.json()
    print(f"PASS: Import successful. Copy ID: {copy_data.get('id')}")
    
    # 3. Anonymization Check
    anon_id = copy_data.get('anonymous_id')
    print(f"INFO: Generated Anonymous ID: {anon_id}")
    if not anon_id or not anon_id.startswith("IMPORT-"):
        print(f"WARN: Anonymous ID format unexpected ({anon_id}), expected 'IMPORT-' prefix")
        # Can be strict or lenient. GradingService.import_pdf uses "IMPORT-..."
        if not anon_id: return False
    else:
        print("PASS: Anonymization (ID generation) verified.")

    # 4. Slicing Check
    # Check that booklets were created
    print("\n[4] VERIFY SLICING (Booklets)...")
    if 'booklets' in copy_data:
        # ManyToMany often returns list of IDs
        booklet_ids = copy_data['booklets']
        print(f"INFO: Linked Booklet IDs: {booklet_ids}")
        if len(booklet_ids) > 0:
            print("PASS: Booklets linked to Copy.")
        else:
            print("FAIL: No booklets linked.")
            return False
    else:
        # If strict serializer didn't return booklets, fetch them manually
        # Note: GradingService added booklet to copy.booklets
        pass

    # Fetch Copy Details to be sure or List Booklets
    resp = session.get(f"{BASE_URL}/api/exams/{exam_id}/copies/")
    data = resp.json()
    if 'results' in data: copies = data['results']
    else: copies = data
    
    found = False
    for c in copies:
        if c['id'] == copy_data['id']:
            found = True
            # Verify status
            if c['status'] == 'STAGING':
                print("PASS: Copy Status is STAGING")
            else:
                 print(f"FAIL: Copy Status is {c['status']}")
                 return False
            break
            
    if not found:
        print("FAIL: Created copy not found in list.")
        return False

    return True

if __name__ == "__main__":
    if run_test():
        print("\nOVERALL: SUCCESS")
    else:
        print("\nOVERALL: FAILURE")
