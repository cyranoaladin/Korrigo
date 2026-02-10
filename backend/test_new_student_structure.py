#!/usr/bin/env python
"""
Test d'intégration rapide pour vérifier la nouvelle structure Student
(nom + prénom + date_naissance au lieu de INE)

Usage:
    python test_new_student_structure.py
"""
import os
import sys
import django
from datetime import date
from io import StringIO

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.test import Client
from students.models import Student
from django.contrib.auth import get_user_model

User = get_user_model()


def cleanup():
    """Nettoyer les données de test."""
    print("🧹 Nettoyage des données de test...")
    Student.objects.filter(last_name__startswith="TEST_").delete()


def test_student_model():
    """Test 1: Vérifier que le modèle Student fonctionne sans INE."""
    print("\n📝 Test 1: Modèle Student sans INE")
    
    # Créer un étudiant
    student = Student.objects.create(
        last_name="TEST_DUPONT",
        first_name="Jean",
        date_naissance=date(2005, 3, 15),
        class_name="TS1",
        groupe="G2",
        email="test.dupont@example.com"
    )
    
    print(f"  ✅ Étudiant créé: {student}")
    print(f"     - ID: {student.id}")
    print(f"     - Nom complet: {student.first_name} {student.last_name}")
    print(f"     - Date de naissance: {student.date_naissance}")
    print(f"     - Classe/Groupe: {student.class_name}/{student.groupe}")
    
    # Vérifier contrainte unique
    try:
        Student.objects.create(
            last_name="TEST_DUPONT",
            first_name="Jean",
            date_naissance=date(2005, 3, 15),  # Même clé unique
            class_name="TS2"
        )
        print("  ❌ ERREUR: La contrainte unique n'a pas fonctionné!")
        return False
    except Exception as e:
        print(f"  ✅ Contrainte unique fonctionne (doublon rejeté)")
    
    # Créer un homonyme avec date différente (devrait passer)
    student2 = Student.objects.create(
        last_name="TEST_DUPONT",
        first_name="Jean",
        date_naissance=date(2005, 7, 20),  # Date différente -> OK
        class_name="TS2",
        groupe="G1"
    )
    print(f"  ✅ Homonyme avec date différente accepté: {student2.date_naissance}")
    
    return True


def test_student_login():
    """Test 2: Vérifier l'authentification élève."""
    print("\n🔐 Test 2: Authentification Élève (API)")
    
    # Créer un étudiant
    student = Student.objects.create(
        last_name="TEST_MARTIN",
        first_name="Sophie",
        date_naissance=date(2006, 5, 10),
        class_name="TS1"
    )
    print(f"  📌 Étudiant créé: {student.first_name} {student.last_name}")
    
    client = Client()
    
    # Test login avec bons credentials
    response = client.post('/api/students/login/', {
        'last_name': 'TEST_MARTIN',
        'first_name': 'Sophie',
        'date_naissance': '2006-05-10'
    }, content_type='application/json')
    
    if response.status_code == 200:
        print(f"  ✅ Login réussi (HTTP {response.status_code})")
        data = response.json()
        print(f"     - Message: {data.get('message')}")
        if 'student' in data:
            print(f"     - Student ID: {data['student']['id']}")
    else:
        print(f"  ❌ Login échoué (HTTP {response.status_code})")
        print(f"     - Erreur: {response.content.decode()}")
        return False
    
    # Test login avec mauvais credentials
    response = client.post('/api/students/login/', {
        'last_name': 'TEST_MARTIN',
        'first_name': 'Sophie',
        'date_naissance': '2006-05-11'  # Mauvaise date
    }, content_type='application/json')
    
    if response.status_code == 401:
        print(f"  ✅ Mauvais credentials rejetés (HTTP {response.status_code})")
    else:
        print(f"  ❌ Mauvais credentials acceptés! (HTTP {response.status_code})")
        return False
    
    # Test format de date alternatif (DD/MM/YYYY)
    response = client.post('/api/students/login/', {
        'last_name': 'TEST_MARTIN',
        'first_name': 'Sophie',
        'date_naissance': '10/05/2006'  # Format français
    }, content_type='application/json')
    
    if response.status_code == 200:
        print(f"  ✅ Format date DD/MM/YYYY accepté")
    else:
        print(f"  ⚠️ Format date DD/MM/YYYY rejeté (peut être normal)")
    
    return True


def test_csv_import():
    """Test 3: Vérifier l'import CSV."""
    print("\n📊 Test 3: Import CSV (nouveau format)")
    
    # Créer un fichier CSV test
    csv_content = """Élèves,Né(e) le,Adresse E-mail,Classe,Groupe
TEST_BENALI AHMED,12/04/2005,ahmed.benali@test.tn,T.01,G3
TEST_LEGRAND MARIE,25/09/2005,marie.legrand@test.tn,T.02,G2
TEST_KERBEJ SANDRA-INES,15/11/2005,sandra.kerbej@test.tn,T.03,G1"""
    
    # Simuler l'upload via API
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.contrib.auth.models import Group
    from core.auth import UserRole
    
    # Créer un utilisateur admin pour l'import
    admin_user = User.objects.create_user(
        username='test_admin',
        password='testpass123',
        is_staff=True,
        is_superuser=True
    )
    teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    admin_user.groups.add(teacher_group)
    
    client = Client()
    client.force_login(admin_user)
    
    csv_file = SimpleUploadedFile(
        "test_students.csv",
        csv_content.encode('utf-8'),
        content_type="text/csv"
    )
    
    response = client.post('/api/students/import/', {
        'file': csv_file
    })
    
    if response.status_code in [200, 207]:
        print(f"  ✅ Import CSV réussi (HTTP {response.status_code})")
        data = response.json()
        print(f"     - Créés: {data.get('created', 0)}")
        print(f"     - Mis à jour: {data.get('updated', 0)}")
        if data.get('errors'):
            print(f"     - Erreurs: {len(data['errors'])}")
            for err in data['errors'][:3]:  # Afficher max 3 erreurs
                print(f"       • Ligne {err['line']}: {err['error']}")
    else:
        print(f"  ❌ Import CSV échoué (HTTP {response.status_code})")
        print(f"     - Erreur: {response.content.decode()[:200]}")
        admin_user.delete()
        return False
    
    # Vérifier que les étudiants ont été créés
    imported = Student.objects.filter(last_name__startswith="TEST_")
    print(f"\n  📋 Étudiants importés ({imported.count()}):")
    for s in imported:
        print(f"     - {s.last_name} {s.first_name} (né le {s.date_naissance})")
        print(f"       Classe: {s.class_name}, Groupe: {s.groupe}, Email: {s.email}")
    
    # Cleanup admin
    admin_user.delete()
    
    return True


def test_no_ine_references():
    """Test 4: Vérifier absence de références INE dans models/serializers."""
    print("\n🔍 Test 4: Absence de références INE")
    
    # Vérifier le modèle Student
    from students.models import Student
    fields = [f.name for f in Student._meta.get_fields()]
    
    if 'ine' in fields:
        print(f"  ❌ Champ 'ine' trouvé dans Student! Champs: {fields}")
        return False
    else:
        print(f"  ✅ Aucun champ 'ine' dans Student")
        print(f"     - Champs actuels: {', '.join(fields[:10])}...")
    
    # Vérifier le serializer
    from students.serializers import StudentSerializer
    serializer_fields = StudentSerializer.Meta.fields
    
    if 'ine' in serializer_fields:
        print(f"  ❌ Champ 'ine' trouvé dans StudentSerializer!")
        return False
    else:
        print(f"  ✅ Aucun champ 'ine' dans StudentSerializer")
        print(f"     - Champs: {', '.join(serializer_fields)}")
    
    return True


def main():
    """Exécuter tous les tests."""
    print("=" * 60)
    print("🧪 Test de la Nouvelle Structure Student")
    print("   (Nom + Prénom + Date de Naissance)")
    print("=" * 60)
    
    cleanup()
    
    tests = [
        ("Modèle Student", test_student_model),
        ("Authentification", test_student_login),
        ("Import CSV", test_csv_import),
        ("Absence INE", test_no_ine_references),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n  ❌ ERREUR: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}  {name}")
    
    print("-" * 60)
    print(f"  Total: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n  🎉 TOUS LES TESTS ONT RÉUSSI!")
        print("  ✅ La nouvelle structure fonctionne correctement")
    else:
        print(f"\n  ⚠️ {total - passed} test(s) ont échoué")
        print("  ❌ Vérifier les erreurs ci-dessus")
    
    cleanup()
    print("\n" + "=" * 60)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
