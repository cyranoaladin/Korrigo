import requests
import json
import time

API_URL = "http://localhost:8088/api"

def wait_for_server():
    print("Waiting for server...")
    for i in range(30):
        try:
            requests.get("http://localhost:8088/admin/login/")
            print("Server is up!")
            return True
        except:
            time.sleep(1)
            print(".", end="", flush=True)
    return False

def test_flow():
    # 1. Upload Exam (Simulated)
    # We need a dummy PDF file
    with open("dummy.pdf", "wb") as f:
        f.write(b"%PDF-1.4 empty pdf")
    
    print("\n[1] Uploading Exam...")
    files = {'pdf_source': open('dummy.pdf', 'rb')}
    data = {'name': 'E2E Test Exam', 'date': '2026-06-01'}
    
    try:
        res = requests.post(f"{API_URL}/exams/upload/", files=files, data=data)
        if res.status_code == 201:
            print("✅ Exam Created:", res.json())
            exam_id = res.json()['id']
        else:
            print("❌ Creation Failed:", res.text)
            return
    except Exception as e:
         print(f"❌ Connection Error: {e}")
         return

    # 2. Update Grading Structure (Editor)
    print("\n[2] Updating Grading Structure...")
    structure = [
        {"id": "ex1", "label": "Exercice 1", "points": 10, "children": [
            {"id": "q1", "label": "Q1", "points": 5},
            {"id": "q2", "label": "Q2", "points": 5}
        ]}
    ]
    res = requests.patch(f"{API_URL}/exams/{exam_id}/", json={'grading_structure': structure})
    if res.status_code == 200:
         print("✅ Structure Updated")
    else:
         print("❌ Update Failed:", res.text)

    # 3. Simulate Booklet Merging (Stapler)
    # Booklets are created automatically by upload mock logic (5 booklets)
    print("\n[3] Fetching Booklets...")
    res = requests.get(f"{API_URL}/exams/{exam_id}/booklets/")
    booklets = res.json()
    print(f"✅ Found {len(booklets)} booklets")
    
    if len(booklets) >= 2:
        print("\n[4] Merging Booklets into Copy...")
        ids = [b['id'] for b in booklets[:2]]
        res = requests.post(f"{API_URL}/exams/{exam_id}/merge/", json={'booklet_ids': ids})
        if res.status_code == 201:
            print("✅ Copy Created:", res.json())
        else:
             print("❌ Merge Failed:", res.text)

    # 4. Trigger Export
    print("\n[5] Triggering Export...")
    res = requests.post(f"{API_URL}/exams/{exam_id}/export_all/")
    if res.status_code == 200:
        print("✅ Export Triggered:", res.json())
    else:
        print("❌ Export Failed:", res.text)

if __name__ == "__main__":
    if wait_for_server():
        test_flow()
    else:
        print("Server failed to start.")
