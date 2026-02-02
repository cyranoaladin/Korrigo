"""Script de création des profils de test pour l'authentification (Admin, Prof, Élève)."""
import os
import django
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from exams.models import Exam, Copy
from students.models import Student

User = get_user_model()

def run():
    print("--- Création des Profils de Test ---")

    # 1. Admin
    admin, created = User.objects.get_or_create(username="admin_test")
    if created:
        admin.set_password("password123")
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        print(f"✅ Admin créé: {admin.username} / password123")
    else:
        print(f"ℹ️ Admin existe déjà: {admin.username}")

    # 2. Enseignant
    teacher_group, _ = Group.objects.get_or_create(name="Teachers")
    teacher, created = User.objects.get_or_create(username="prof_test")
    if created:
        teacher.set_password("password123")
        teacher.save()
        teacher.groups.add(teacher_group)
        print(f"✅ Enseignant créé: {teacher.username} / password123")
    else:
        print(f"ℹ️ Enseignant existe déjà: {teacher.username}")

    # 3. Élève
    student, created = Student.objects.get_or_create(
        email="jean.dupont@test.com",
        defaults={
            "first_name": "Jean",
            "last_name": "DUPONT",
            "class_name": "TG2",
        }
    )
    if created:
        print(f"✅ Élève créé: {student.first_name} {student.last_name} (Email: {student.email})")
    else:
        print(f"ℹ️ Élève existe déjà: {student.email}")

    # 4. Données de Test (Copie pour l'élève)
    exam, _ = Exam.objects.get_or_create(
        name="Bac Blanc Maths Test",
        defaults={"date": timezone.now().date()}
    )
    
    # Copie corrigée (GRADED) pour que l'élève puisse la voir
    copy, created = Copy.objects.get_or_create(
        anonymous_id="TEST-COPY-01",
        defaults={
            "exam": exam,
            "status": "GRADED", # Important pour visibility portail élève
            "student": student,
            "is_identified": True
        }
    )
    if created:
        print(f"✅ Copie de test créée pour l'élève (Statut GRADED)")
    else:
        if copy.student != student:
            copy.student = student
            copy.save()
            print(f"ℹ️ Copie réassignée à l'élève de test")
        if copy.status != "GRADED":
            copy.status = "GRADED"
            copy.save()
            print(f"ℹ️ Copie passée en statut GRADED")

    print("\n--- Terminé ---")

if __name__ == "__main__":
    run()
