import requests
import sys

base_url = "http://localhost:8088"

# 1. Login
session = requests.Session()
# Note: CSRF might be an issue if not handled, but LoginView is csrf_exempt
try:
    print("Attempting login...")
    # Using the credentials I know I created or exist
    resp = session.post(f"{base_url}/api/login/", json={'username': 'admin', 'password': 'adminpass'})
    print(f"Login Response: {resp.status_code}")
    
    if resp.status_code != 200:
        print("Login failed, trying to continue mostly to see if settings is accessible anyway (it shouldn't be)")
    
    # 2. Fetch Settings
    print("Fetching settings...")
    resp = session.get(f"{base_url}/api/settings/")
    print(f"Settings Response: {resp.status_code}")
    print(f"Settings Body: {resp.text}")

except Exception as e:
    print(f"Script error: {e}")
