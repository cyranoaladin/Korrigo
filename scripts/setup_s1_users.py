import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from students.models import Student

User = get_user_model()

# 1. Admin
if not User.objects.filter(username='admin').exists():
    print("Creating superuser 'admin'...")
    u = User.objects.create_superuser('admin', 'admin@example.com', 'admin')
else:
    print("Superuser 'admin' already exists. Resetting password.")
    u = User.objects.get(username='admin')
    u.set_password('admin')
    u.save()

from django.contrib.auth.models import Group

# 2. Teacher
teacher_group, _ = Group.objects.get_or_create(name='Teachers')

if not User.objects.filter(username='prof1').exists():
    print("Creating teacher 'prof1'...")
    u = User.objects.create_user('prof1', 'prof1@example.com', 'password')
    u.is_staff = False
    u.is_superuser = False
    u.save()
    u.groups.add(teacher_group)
else:
    print("Teacher 'prof1' already exists. Resetting permissions & password.")
    u = User.objects.get(username='prof1')
    u.set_password('password')
    u.is_staff = False
    u.is_superuser = False
    u.save()
    u.groups.add(teacher_group)

# 3. Student
ine_val = '123456789A'
if not Student.objects.filter(ine=ine_val).exists():
    print("Creating student '123456789A'...")
    Student.objects.create(
        ine=ine_val,
        last_name='Dupont',
        first_name='Jean',
        class_name='Terminale 1',
        email='student@example.com'
    )
else:
    print("Student '123456789A' already exists. Updating details.")
    s = Student.objects.get(ine=ine_val)
    s.last_name = 'Dupont'
    s.first_name = 'Jean'
    s.save()

print("S1 Users Setup Complete (Passwords Enforced).")
