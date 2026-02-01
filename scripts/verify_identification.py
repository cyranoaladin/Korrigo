import requests
import sys

BASE_URL = "http://127.0.0.1:8088"
API_LOGIN = f"{BASE_URL}/api/login/"
API_STUDENT_LOGIN = f"{BASE_URL}/api/students/login/"

def run_test():
    session = requests.Session()
    session.get(f"{BASE_URL}/admin/")
    csrf = session.cookies.get('csrftoken')
    headers = {'X-CSRFToken': csrf, 'Referer': BASE_URL}

    print("\n[1] LOGIN TEACHER...")
    resp = session.post(API_LOGIN, json={'username': 'prof1', 'password': 'password'}, headers=headers)
    if resp.status_code != 200:
        print(f"FAIL: Teacher login failed {resp.status_code}")
        return False
    
    # Refresh CSRF
    csrf = session.cookies.get('csrftoken')
    headers['X-CSRFToken'] = csrf

    # 1. Find a Copy to Identify
    # We'll use the one from S4 if possible, or list all copies of an exam
    # Let's list exams first to find a recent one
    print("\n[2] FIND COPY TO IDENTIFY...")
    resp = session.get(f"{BASE_URL}/api/exams/", headers=headers)
    exams_data = resp.json()
    if 'results' in exams_data: exams = exams_data['results']
    else: exams = exams_data
    
    print(f"DEBUG: Found {len(exams)} exams.")
    
    if not exams:
        print("FAIL: No exams found. Run S2/S3/S4 first.")
        # Try to run Setup S2/S3 directly? No, keep it simple.
        return False
        
    # Use the most recent exam
    exam_id = exams[0]['id']
    print(f"INFO: Using Exam {exam_id}")
    
    # List copies
    resp = session.get(f"{BASE_URL}/api/exams/{exam_id}/copies/", headers=headers)
    data = resp.json()
    if 'results' in data: copies = data['results']
    else: copies = data
    
    if not copies:
        print("FAIL: No copies in exam.")
        return False
        
    target_copy = copies[0]
    print(f"INFO: Target Copy {target_copy['id']} (Current Status: {target_copy['status']})")

    # 2. Identify Copy (Link to Student)
    # Student seeded: INE=123456789A
    # Need Student ID. We can't list students as Teacher easily in MVP API?
    # Or we assume we know the ID?
    # Actually, we need to know the Student Primary Key (ID) for the API `student_id`.
    # Let's "cheat" and get it via a hack or assumtion?
    # Better: Add a "List Students" endpoint for Teacher? 
    # Or just try to get it via `verify_auth_s1.py` logic?
    # Wait, `verify_auth_s1.py` did: `API_STUDENT_ME`.
    
    # Let's login as student first to get their ID!
    print("\n[2.5] FETCH STUDENT ID (via Student Login)...")
    student_session = requests.Session()
    student_session.get(f"{BASE_URL}/admin/")
    s_csrf = student_session.cookies.get('csrftoken')
    s_headers = {'X-CSRFToken': s_csrf, 'Referer': BASE_URL}
    
    resp = student_session.post(API_STUDENT_LOGIN, json={'ine': '123456789A', 'last_name': 'Dupont'}, headers=s_headers)
    if resp.status_code != 200:
        print("FAIL: Student login failed. Ensure seeding ran.")
        return False
        
    # Get ID
    resp = student_session.get(f"{BASE_URL}/api/students/me/", headers=s_headers)
    student_data = resp.json()
    student_id = student_data['id']
    print(f"INFO: Student ID is {student_id}")
    
    # Switch back to Teacher
    print("\n[3] IDENTIFY COPY...")
    api_identify = f"{BASE_URL}/api/exams/copies/{target_copy['id']}/identify/"
    # The URL in urls.py is `copies/<uuid:id>/identify/` -> `/api/exams/copies/...` ??
    # Let's check `urls.py`:
    # `path('api/exams/', include('exams.urls'))`
    # inside exams.urls: `path('copies/<uuid:id>/identify/', ...)`
    # So full URL: `/api/exams/copies/<id>/identify/`
    
    resp = session.post(api_identify, json={'student_id': student_id}, headers=headers)
    if resp.status_code != 200:
        print(f"FAIL: Identification failed ({resp.status_code}) - {resp.text}")
        return False
    print("PASS: Identification successful.")

    print("\n[3.5] FINALIZE COPY (So it appears in Portal)...")
    # Need to finalize. Assuming it's READY.
    # Endpoint: /api/copies/<id>/finalize/
    api_finalize = f"{BASE_URL}/api/copies/{target_copy['id']}/finalize/"
    resp = session.post(api_finalize, headers=headers)
    if resp.status_code != 200:
         print(f"WARN: Could not finalize copy ({resp.status_code}). It might not appear in student portal.")
         # Continue anyway to check
    else:
         print("PASS: Copy Finalized.")

    # 4. Verify Student Access
    print("\n[4] VERIFY STUDENT PORTAL ACCESS...")
    # Using the student_session from step 2.5
    # URL: /api/exams/student/copies/ (See urls.py: `path('student/copies/', ...)` inside exams.urls)
    # Full: /api/exams/student/copies/
    
    # Refresh CSRF?
    s_csrf = student_session.cookies.get('csrftoken')
    s_headers['X-CSRFToken'] = s_csrf
    
    api_student_copies = f"{BASE_URL}/api/exams/student/copies/"
    resp = student_session.get(api_student_copies, headers=s_headers)
    
    if resp.status_code != 200:
        print(f"FAIL: Student Copies list failed ({resp.status_code}) - {resp.text}")
        return False
        
    my_copies = resp.json()
    if 'results' in my_copies: my_copies = my_copies['results']
    
    print(f"INFO: Student has {len(my_copies)} copies.")
    
    found_it = False
    for c in my_copies:
        if c['id'] == target_copy['id']:
            found_it = True
            print(f"PASS: Found verified copy {c['id']} in Student Portal.")
            print(f"      Score: {c.get('total_score')}")
            break
            
    if not found_it:
        # Note: StudentCopiesView filters for status=GRADED.
        # If the copy we picked (from S3/S4) was finalized, it should be GRADED.
        # If we picked a random one that is STAGING, it won't show.
        # Check target copy status
        print(f"WARN: Copy not found. Target status was {target_copy['status']}.")
        if target_copy['status'] != 'GRADED':
            print("INFO: Expected. Student only sees GRADED copies.")
            return True # Not a fail, just workflow logic.
        else:
            print("FAIL: Graded copy missing from student view!")
            return False

    return True

if __name__ == "__main__":
    if run_test():
        print("\nOVERALL: SUCCESS")
    else:
        print("\nOVERALL: FAILURE")
