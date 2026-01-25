import os
import sys
# START ENV SETUP
os.environ["RATELIMIT_ENABLE"] = "false"
# END ENV SETUP
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import GlobalSettings
from rest_framework.test import APIRequestFactory, force_authenticate
from core.views import GlobalSettingsView, LoginView

def test_manual():
    print("--- Starting Manual Audit ---")
    
    # 1. Test Admin User Creation
    admin, _ = User.objects.get_or_create(username='audit_admin')
    admin.is_superuser = True
    admin.set_password('pass')
    admin.save()
    print("1. Admin user ready")

    # 2. Test GlobalSettings Load
    try:
        s = GlobalSettings.load()
        print(f"2. GlobalSettings loaded: {s.institution_name}")
    except Exception as e:
        print(f"2. GlobalSettings FAIL: {e}")

    # 3. Test View directly
    factory = APIRequestFactory()
    view = GlobalSettingsView.as_view()

    # GET
    req = factory.get('/api/settings/')
    force_authenticate(req, user=admin)
    res = view(req)
    print(f"3. GET Settings Status: {res.status_code}")
    if res.status_code != 200:
        print(f"   Error: {res.data}")

    # POST
    req = factory.post('/api/settings/', {'institutionName': 'Manual Audit School'}, format='json')
    force_authenticate(req, user=admin)
    res = view(req)
    print(f"4. POST Settings Status: {res.status_code}")
    
    s.refresh_from_db()
    print(f"   New Name in DB: {s.institution_name}")

    # 4. Test Import CSV
    from students.views import StudentImportView
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    print("5. Testing CSV Import...")
    csv_content = b"ine,last_name,first_name,email\n999888777,TEST,Manu,test@manual.com"
    file = SimpleUploadedFile("import.csv", csv_content, content_type="text/csv")
    
    view_import = StudentImportView.as_view()
    req = factory.post('/api/students/import/', {'file': file}, format='multipart')
    force_authenticate(req, user=admin)
    res = view_import(req)
    
    print(f"   Import Status: {res.status_code}")
    if res.status_code == 200:
        print(f"   Created: {res.data.get('created')}")
    else:
        print(f"   Error: {res.data}")



        print(f"   Error: {res.data}")

    # 5. Test Student Login (using imported student)
    print("6. Testing Student Login...")
    # The import created a student with INE '999888777' and Last Name 'TEST'
    from students.views import StudentLoginView
    
    view_student_login = StudentLoginView.as_view()
    # Payload matches frontend: { ine, last_name }
    req = factory.post('/api/students/login/', {'ine': '999888777', 'last_name': 'TEST'}, format='json')
    
    # Manually add session for testing
    from django.contrib.sessions.middleware import SessionMiddleware
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(req)
    req.session.save()
    
    # No auth required for login
    res = view_student_login(req)
    
    print(f"   Student Login Status: {res.status_code}")
    if res.status_code == 200:
        print(f"   Token/Session: Success (User ID: {res.data.get('id')})")
    else:
        print(f"   Error: {res.data}")

if __name__ == "__main__":
    test_manual()
