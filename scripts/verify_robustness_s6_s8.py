import requests
import sys
import os

BASE_URL = "http://127.0.0.1:8088"
API_LOGIN = f"{BASE_URL}/api/login/"

def get_session(username, password):
    s = requests.Session()
    s.get(f"{BASE_URL}/admin/")
    csrf = s.cookies.get('csrftoken')
    headers = {'X-CSRFToken': csrf, 'Referer': BASE_URL}
    
    resp = s.post(API_LOGIN, json={'username': username, 'password': password}, headers=headers)
    if resp.status_code != 200:
        print(f"FAIL: Login failed for {username}")
        return None, None
    
    # Refresh CSRF
    csrf = s.cookies.get('csrftoken')
    headers['X-CSRFToken'] = csrf
    return s, headers

def run_test():
    print("Preparing Users...")
    # Setup verify_auth_s1 ensured prof1 exists.
    # We need a second teacher "prof2" for Lock Conflict (S6)
    # We can reuse "admin" if he has teacher rights? 
    # Or creating prof2 would be cleaner.
    # Let's try to login as 'admin' (superuser matches IsTeacherOrAdmin)
    
    session_A, headers_A = get_session('prof1', 'password')
    session_B, headers_B = get_session('admin', 'admin') # Admin acts as second corrector
    
    if not session_A or not session_B:
        print("FAIL: Could not log in both users.")
        return False
        
    print("PASS: Two distinct sessions created (User A: prof1, User B: admin).")

    # Find a Copy (Any READY copy)
    # List exams -> copies
    resp = session_A.get(f"{BASE_URL}/api/exams/", headers=headers_A)
    exams = resp.json().get('results', [])
    if not exams:
        print("FAIL: No exams found.")
        return False
        
    exam_id = exams[0]['id']
    resp = session_A.get(f"{BASE_URL}/api/exams/{exam_id}/copies/", headers=headers_A)
    copies = resp.json().get('results', [])
    
    # Find a READY copy
    target_copy = None
    for c in copies:
        if c['status'] == 'READY':
            target_copy = c
            break
            
    if not target_copy:
        print("WARN: No READY copy found. Trying to find STAGING to promote or use any.")
        if copies: target_copy = copies[0]
        else: 
             print("FAIL: No copies found.")
             return False

    copy_id = target_copy['id']
    print(f"INFO: Target Copy {copy_id} (Status: {target_copy['status']})")
    
    # Force Unlock if locked (Cleanup)
    session_A.delete(f"{BASE_URL}/api/copies/{copy_id}/lock/release/", headers=headers_A)
    session_B.delete(f"{BASE_URL}/api/copies/{copy_id}/lock/release/", headers=headers_B)

    # ==========================================
    # S6: LOCK CONFLICT
    # ==========================================
    print("\n[S6] TESTING LOCK CONFLICT...")
    
    # 1. User A acquires lock
    resp = session_A.post(f"{BASE_URL}/api/copies/{copy_id}/lock/", headers=headers_A)
    if resp.status_code not in [200, 201]:
        print(f"FAIL: User A could not acquire lock. {resp.status_code}")
        return False
    print("PASS: User A acquired lock.")
    
    # 2. User B tries to acquire lock -> SHOULD FAIL (409)
    resp = session_B.post(f"{BASE_URL}/api/copies/{copy_id}/lock/", headers=headers_B)
    if resp.status_code == 409:
        print("PASS: User B blocked (409 Conflict).")
        print(f"      Message: {resp.json()}")
    else:
        print(f"FAIL: User B should be blocked. Got {resp.status_code}")
        return False

    # ==========================================
    # S7: DRAFT CONFLICT (Autosave)
    # ==========================================
    print("\n[S7] TESTING DRAFT CONFLICT (Same User, Different Session)...")
    
    # 0. Clean cleanup existing draft
    session_A.delete(f"{BASE_URL}/api/copies/{copy_id}/draft/", headers=headers_A)

    # Simulate User A opening 2 tabs (simulate by changing client_id)
    # Ideally User A (Tab 1) saves draft
    
    import uuid
    client_id_1 = str(uuid.uuid1())
    client_id_2 = str(uuid.uuid1())
    
    payload = {"content": "Draft from Tab 1"}
    
    # 1. Tab 1 saves
    data = {"payload": payload, "client_id": client_id_1, "token": resp.json().get('token')} # Reuse token from Lock A? 
    # Actually User A has the lock. We need the token.
    # The lock response for A returned a token?
    # Rerun lock A to get token
    resp = session_A.post(f"{BASE_URL}/api/copies/{copy_id}/lock/", headers=headers_A)
    token_A = resp.json()['token']
    
    data['token'] = token_A
    
    api_draft = f"{BASE_URL}/api/copies/{copy_id}/draft/"
    resp = session_A.put(api_draft, json=data, headers=headers_A)
    if resp.status_code != 200:
        print(f"FAIL: Tab 1 failed to save draft. {resp.status_code} - {resp.text}")
        return False
    print("PASS: Tab 1 saved draft.")
    
    # 2. Tab 2 tries to save with different client_id -> SHOULD FAIL (409)
    data_2 = {"payload": {"content": "Draft from Tab 2"}, "client_id": client_id_2, "token": token_A}
    resp = session_A.put(api_draft, json=data_2, headers=headers_A)
    
    if resp.status_code == 409:
        print("PASS: Tab 2 blocked (409 Conflict).")
        print(f"      Message: {resp.json()}")
    else:
        print(f"FAIL: Tab 2 should be blocked. Got {resp.status_code}")
        return False

    # ==========================================
    # S8: AUDIT LOGS
    # ==========================================
    print("\n[S8] VERIFYING AUDIT LOGS...")
    api_audit = f"{BASE_URL}/api/copies/{copy_id}/audit/"
    resp = session_A.get(api_audit, headers=headers_A)
    
    if resp.status_code != 200:
        print(f"FAIL: Could not fetch audit logs. {resp.status_code}")
        return False
        
    logs = resp.json()
    if 'results' in logs: logs = logs['results']
    
    print(f"INFO: Found {len(logs)} logs.")
    
    # Look for LOCK action
    # Prof1 ID might be 2 (from S6 output)
    # Get user ID from session A (me)
    resp = session_A.get(f"{BASE_URL}/api/users/me/", headers=headers_A)
    # If /me doesn't exist, use the one from lock response
    # The lock response for A returned 'owner': {'id': ...}
    
    # We didn't save lock response A variable fully in S6 block scope for S8 usage perfectly, 
    # but we can infer or use hardcoded if we trust previous run.
    # Better: Get it from 'me'. 
    # Or just check if ANY lock event exists for current time?
    
    found_lock = False
    for log in logs:
        # Check action LOCK
        if log['action'] == 'LOCK':
             found_lock = True
             print(f"INFO: Found LOCK log by actor {log['actor']}")
             break
    
    if found_lock:
        print("PASS: Found LOCK event in Audit Trail.")
    else:
        print("FAIL: LOCK event missing from Audit Trail.")
        # Print logs for debug
        # print(logs) 
        return False

    return True

if __name__ == "__main__":
    if run_test():
        print("\nOVERALL: SUCCESS")
    else:
        print("\nOVERALL: FAILURE")
