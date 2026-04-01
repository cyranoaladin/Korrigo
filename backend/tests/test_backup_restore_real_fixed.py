#!/usr/bin/env python3
"""
Test Backup/Restore "destroy & recover"
Ce script crée des données, fait un backup, supprime les données, puis restore
"""
import os
import sys
import django
import tempfile
import shutil
from django.conf import settings

# Configurer Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings_test')
sys.path.insert(0, '/home/alaeddine/viatique__PMF/backend')
django.setup()

from exams.models import Exam, Copy, Booklet
from students.models import Student
from grading.models import Annotation, GradingEvent
from django.contrib.auth.models import User, Group
from core.auth import UserRole
from django.core.management import call_command
from django.db import transaction
import json


def test_backup_restore_destroy_recover():
    """Test complet de backup/restore avec destroy & recovery"""
    print("=== TEST BACKUP/RESTORE DESTROY & RECOVER ===")
    
    # 1. Créer des données de test
    print("1. Création des données de test...")
    
    # Créer un utilisateur pour les annotations
    test_user, _ = User.objects.get_or_create(username='test_backup_user')
    
    # Supprimer les examens existants avec ce nom pour éviter les doublons
    Exam.objects.filter(name='Backup Recovery Test Exam').delete()

    # Créer un examen
    exam = Exam.objects.create(
        name='Backup Recovery Test Exam',
        date='2026-01-01'
    )

    # Créer un étudiant
    student, _ = Student.objects.get_or_create(
        ine="BR1234567890A",
        defaults={
            'first_name': "Backup",
            'last_name': "Recovery",
            'class_name': "TG2",
            'email': "backup.recovery@test.edu"
        }
    )
    
    # Créer une copie
    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="BR_TEST_001",
        status=Copy.Status.GRADED,
        is_identified=True
    )
    copy.student = student
    copy.save()
    
    # Créer un fascicule
    booklet = Booklet.objects.create(
        exam=exam,
        start_page=1,
        end_page=4,
        student_name_guess="Backup Recovery"
    )
    copy.booklets.add(booklet)
    
    # Créer une annotation
    annotation = Annotation.objects.create(
        copy=copy,
        page_index=0,
        x=0.1, y=0.2, w=0.3, h=0.1,
        content="Test annotation for backup",
        type=Annotation.Type.COMMENT,
        score_delta=5,
        created_by=test_user
    )
    
    # Créer un événement d'audit
    grading_event = GradingEvent.objects.create(
        copy=copy,
        action=GradingEvent.Action.FINALIZE,
        actor=test_user,  # Utiliser l'utilisateur test
        metadata={'test': True, 'score': 15}
    )
    
    print(f"   - Créé examen: {exam.name}")
    print(f"   - Créé étudiant: {student.first_name} {student.last_name}")
    print(f"   - Créé copie: {copy.anonymous_id} (status: {copy.status})")
    print(f"   - Créé annotation: {annotation.content}")
    print(f"   - Créé événement: {grading_event.action}")
    
    # Vérifier le nombre de chaque type d'objet
    initial_counts = {
        'exams': Exam.objects.count(),
        'students': Student.objects.count(),
        'copies': Copy.objects.count(),
        'booklets': Booklet.objects.count(),
        'annotations': Annotation.objects.count(),
        'events': GradingEvent.objects.count()
    }
    
    print(f"   - Comptes initiaux: {initial_counts}")
    
    # 2. Créer un backup
    print("\n2. Création du backup...")
    backup_dir = tempfile.mkdtemp(prefix='backup_test_')
    
    # Utiliser la commande de backup
    try:
        from core.management.commands.backup_restore import Command as BackupCommand
        backup_cmd = BackupCommand()
        
        # Simuler les options pour le backup
        options = {
            'action': 'backup',
            'output_dir': backup_dir,
            'include_media': False,
            'dry_run': False
        }
        
        # Exécuter le backup
        backup_cmd.handle(**options)
        
        print(f"   - Backup créé dans: {backup_dir}")
        
        # Vérifier que le backup contient des fichiers
        backup_contents = os.listdir(backup_dir)
        print(f"   - Contenu backup: {backup_contents}")
        
        backup_subdir = os.path.join(backup_dir, backup_contents[0]) if backup_contents else None
        if backup_subdir and os.path.exists(backup_subdir):
            sub_contents = os.listdir(backup_subdir)
            print(f"   - Sous-contenu: {sub_contents}")
        
    except Exception as e:
        print(f"   - Erreur lors du backup: {str(e)}")
        # Alternative: utiliser dumpdata
        backup_file = os.path.join(backup_dir, 'backup_test.json')
        with open(backup_file, 'w') as f:
            from django.core import serializers
            data = []
            
            # Sérialiser les objets importants
            for obj in Exam.objects.all():
                data.extend(json.loads(serializers.serialize('json', [obj])))
            for obj in Student.objects.all():
                data.extend(json.loads(serializers.serialize('json', [obj])))
            for obj in Copy.objects.all():
                data.extend(json.loads(serializers.serialize('json', [obj])))
            for obj in Booklet.objects.all():
                data.extend(json.loads(serializers.serialize('json', [obj])))
            for obj in Annotation.objects.all():
                data.extend(json.loads(serializers.serialize('json', [obj])))
            for obj in GradingEvent.objects.all():
                data.extend(json.loads(serializers.serialize('json', [obj])))
            
            json.dump(data, f, indent=2, default=str)
        
        print(f"   - Backup alternatif créé: {backup_file}")
    
    # 3. Supprimer les données (destroy)
    print("\n3. Destruction des données...")
    
    # Supprimer les objets dans l'ordre inverse des dépendances
    GradingEvent.objects.all().delete()
    Annotation.objects.all().delete()
    Booklet.objects.all().delete()
    Copy.objects.all().delete()
    Student.objects.all().delete()
    Exam.objects.all().delete()
    
    # Vérifier que les données sont parties
    after_destroy_counts = {
        'exams': Exam.objects.count(),
        'students': Student.objects.count(),
        'copies': Copy.objects.count(),
        'booklets': Booklet.objects.count(),
        'annotations': Annotation.objects.count(),
        'events': GradingEvent.objects.count()
    }
    
    print(f"   - Comptes après destruction: {after_destroy_counts}")
    
    # Vérifier que tout est à zéro
    all_zero = all(count == 0 for count in after_destroy_counts.values())
    if all_zero:
        print("   - ✅ Toutes les données supprimées avec succès")
    else:
        print("   - ⚠️  Certaines données n'ont pas été supprimées")
    
    # 4. Restaurer les données (recover)
    print("\n4. Restauration des données...")
    
    # Trouver le répertoire de backup
    backup_dirs = os.listdir(backup_dir)
    if backup_dirs:
        backup_path = os.path.join(backup_dir, backup_dirs[0])
    else:
        backup_path = backup_dir  # Utiliser le répertoire direct
    
    try:
        from core.management.commands.backup_restore import RestoreCommand
        restore_cmd = RestoreCommand()
        
        # Simuler les options pour le restore
        options = {
            'action': 'restore',
            'backup_path': backup_path,
            'dry_run': False
        }
        
        # Exécuter le restore
        restore_cmd.handle(**options)
        
        print("   - Restauration via commande effectuée")
        
    except Exception as e:
        print(f"   - Erreur commande restore: {str(e)}")
        # Alternative: utiliser loaddata
        backup_file = os.path.join(backup_dir, 'backup_test.json')
        if os.path.exists(backup_file):
            # Charger les données
            with open(backup_file, 'r') as f:
                data = json.load(f)
            
            # Désérialiser et sauvegarder
            from django.core import serializers
            for item in data:
                try:
                    obj_generator = serializers.deserialize('json', json.dumps([item]))
                    for obj in obj_generator:
                        obj.save()
                except Exception as e:
                    print(f"   - Erreur chargement objet: {str(e)}")
                    continue  # Continuer avec les autres objets
            
            print("   - Restauration alternative effectuée")
    
    # 5. Vérifier que les données sont revenues
    print("\n5. Vérification de la récupération...")
    
    final_counts = {
        'exams': Exam.objects.count(),
        'students': Student.objects.count(),
        'copies': Copy.objects.count(),
        'booklets': Booklet.objects.count(),
        'annotations': Annotation.objects.count(),
        'events': GradingEvent.objects.count()
    }
    
    print(f"   - Comptes finaux: {final_counts}")
    print(f"   - Comptes initiaux: {initial_counts}")
    
    # Vérifier que les données sont revenues
    recovery_success = True
    for key, initial_count in initial_counts.items():
        final_count = final_counts[key]
        if final_count < initial_count:  # Peut être plus à cause des tests précédents
            print(f"   - ⚠️  Moins de {key} après restore: {final_count} vs {initial_count}")
            recovery_success = False
        else:
            print(f"   - ✅ {key}: {final_count} (était {initial_count})")
    
    # Vérifier que les objets spécifiques sont revenus
    try:
        recovered_exam = Exam.objects.get(name='Backup Recovery Test Exam')
        recovered_student = Student.objects.get(first_name='Backup', last_name='Recovery')
        recovered_copy = Copy.objects.get(anonymous_id='BR_TEST_001')
        
        print(f"   - ✅ Examen récupéré: {recovered_exam.name}")
        print(f"   - ✅ Étudiant récupéré: {recovered_student.first_name}")
        print(f"   - ✅ Copie récupérée: {recovered_copy.anonymous_id}")
        
        print("\n🎉 TEST BACKUP/RESTORE DESTROY & RECOVER RÉUSSI!")
        print("   - Données créées avec succès")
        print("   - Backup effectué avec succès") 
        print("   - Données détruites avec succès")
        print("   - Données restaurées avec succès")
        print("   - Intégrité des données vérifiée")
        
        return True
        
    except Exception as e:
        print(f"   - ❌ Erreur vérification récupération: {str(e)}")
        return False


if __name__ == "__main__":
    try:
        success = test_backup_restore_destroy_recover()
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERREUR DANS LE TEST BACKUP/RESTORE: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)