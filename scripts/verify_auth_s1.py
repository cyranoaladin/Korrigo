import requests
import sys

BASE_URL = "http://127.0.0.1:8088"
API_LOGIN = f"{BASE_URL}/api/login/"
API_STUDENT_LOGIN = f"{BASE_URL}/api/students/login/"
API_ME = f"{BASE_URL}/api/me/"
API_STUDENT_ME = f"{BASE_URL}/api/students/me/"

# Endpoints that require Teacher permissions
API_EXAMS = f"{BASE_URL}/api/exams/" 
# Endpoints that require Admin permissions (Django Admin)
ADMIN_URL = f"{BASE_URL}/admin/"

def get_csrf_token(session):
    # Fetch a page to get the CSRF cookie
    try:
        response = session.get(API_ME)
        if 'csrftoken' in session.cookies:
            return session.cookies['csrftoken']
    except Exception as e:
        print(f"Error fetching CSRF: {e}")
    return None

def test_teacher_flow():
    print("\n--- Testing Teacher Flow ---")
    session = requests.Session()
    csrf = get_csrf_token(session)
    if not csrf:
        # If no cookie, maybe we need to hit a view that sets it. 
        # Django sets it on login, but we need it FOR login if we want to be safe, 
        # normally DRF SessionAuth requires it.
        # Let's try to hit admin login page to seed cookie
        session.get(ADMIN_URL)
        csrf = session.cookies.get('csrftoken')
    
    headers = {'X-CSRFToken': csrf, 'Referer': BASE_URL}
    
    # Login
    payload = {'username': 'prof1', 'password': 'password'}
    resp = session.post(API_LOGIN, json=payload, headers=headers)
    
    if resp.status_code != 200:
        print(f"FAIL: Teacher login failed: {resp.status_code} {resp.text}")
        return False
    
    print("PASS: Teacher Login successful")
    
    # Check Role
    resp = session.get(API_ME)
    if resp.status_code == 200:
        data = resp.json()
        role = data.get('role')
        if role == 'Teacher':
            print("PASS: Role identified as Teacher")
        else:
            print(f"FAIL: Role is {role}, expected Teacher")
    else:
        print(f"FAIL: Could not fetch /api/me/: {resp.status_code}")

    # Check Teacher Access (Exams)
    resp = session.get(API_EXAMS)
    if resp.status_code == 200:
         print("PASS: Teacher can access Exams API")
    else:
         print(f"FAIL: Teacher cannot access Exams API: {resp.status_code}")

    # Check Isolation (Admin)
    # Django Admin returns 200 if allowed (dashboard) or redirects (login)
    resp = session.get(ADMIN_URL, allow_redirects=False)
    # If authenticated as staff (Admin), this might be 200 or 302 to main page?
    # Actually, prof1 is NOT is_staff usually.
    if resp.status_code == 302:
        print(f"PASS: Teacher redirected from Admin (Isolation verified). Loc: {resp.headers.get('Location')}")
    elif resp.status_code == 200:
        # Check if we are on login page or dashboard
        if "Log in" in resp.text:
             print("PASS: Teacher sees Admin Login page (Isolation verified)")
        else:
             print("FAIL: Teacher accessed Admin Dashboard!")
    else:
        print(f"PASS: Teacher denied Admin access ({resp.status_code})")
        
    return True

def test_student_flow():
    print("\n--- Testing Student Flow ---")
    session = requests.Session()
    session.get(ADMIN_URL) # seed cookie
    csrf = session.cookies.get('csrftoken')
    headers = {'X-CSRFToken': csrf, 'Referer': BASE_URL}

    payload = {'ine': '123456789A', 'last_name': 'Dupont'}
    resp = session.post(API_STUDENT_LOGIN, json=payload, headers=headers)

    if resp.status_code != 200:
        print(f"FAIL: Student login failed: {resp.status_code} {resp.text}")
        return False
    
    print("PASS: Student Login successful")

    # Check Role
    resp = session.get(API_STUDENT_ME)
    if resp.status_code == 200:
        print("PASS: Retrieved Student connection info")
    else:
        print(f"FAIL: Could not fetch /api/students/me/: {resp.status_code}")

    # Check Isolation (Teacher API)
    resp = session.get(API_EXAMS)
    if resp.status_code == 403:
        print("PASS: Student denied access to Exams API (403 Forbidden)")
    elif resp.status_code == 200:
        print("FAIL: STUDENT ACCESSED EXAMS API!")
    else:
        print(f"INFO: Student API access status: {resp.status_code}")

    return True

if __name__ == "__main__":
    t_success = test_teacher_flow()
    s_success = test_student_flow()
    
    if t_success and s_success:
        print("\nOVERALL: SUCCESS")
    else:
        print("\nOVERALL: FAILURE")
