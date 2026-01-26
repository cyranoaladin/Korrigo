"""
Test de backup/restore destroy & recover
Test complet: créer données → backup → destroy → restore → vérifier intégrité
"""
import os
import tempfile
import shutil
from django.test import TestCase
from django.core.management import call_command
from django.conf import settings
from exams.models import Exam, Copy, Booklet
from students.models import Student
from grading.models import Annotation, GradingEvent
from django.contrib.auth.models import User, Group
from core.auth import UserRole
from django.core.files.base import ContentFile
import json
from io import StringIO
from django.core import serializers


class BackupRestoreDestroyRecoverTest(TestCase):
    """
    Test complet de backup/restore avec destruction et récupération
    """

    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        self.user.groups.add(self.teacher_group)

        # Create test data
        self.student = Student.objects.create(
            ine="TEST123456789A",
            first_name="Jean",
            last_name="Test",
            class_name="TG2",
            email="jean.test@example.com"
        )

        self.exam = Exam.objects.create(
            name="Test Backup Exam",
            date="2026-01-01"
        )

        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="BACKUP_TEST_001",
            status=Copy.Status.GRADED,
            is_identified=True,
            student=self.student
        )

        self.booklet = Booklet.objects.create(
            exam=self.exam,
            start_page=1,
            end_page=4,
            student_name_guess="Jean Test"
        )
        self.copy.booklets.add(self.booklet)

        # Create annotation
        self.annotation = Annotation.objects.create(
            copy=self.copy,
            page_index=0,
            x=0.1, y=0.2, w=0.3, h=0.1,
            content="Test annotation for backup",
            type=Annotation.Type.COMMENT,
            score_delta=5,
            created_by=self.user
        )

        # Create grading event
        self.event = GradingEvent.objects.create(
            copy=self.copy,
            action=GradingEvent.Action.FINALIZE,
            actor=self.user,
            metadata={'test': True, 'score': 15}
        )

    def test_backup_restore_destroy_recover_full_cycle(self):
        """
        Test complet: créer données → backup → détruire → restaurer → vérifier
        """
        # 1. Vérifier les données initiales
        initial_counts = {
            'exams': Exam.objects.count(),
            'students': Student.objects.count(),
            'copies': Copy.objects.count(),
            'booklets': Booklet.objects.count(),
            'annotations': Annotation.objects.count(),
            'events': GradingEvent.objects.count()
        }

        print(f"Initial counts: {initial_counts}")

        # 2. Créer un backup
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = os.path.join(temp_dir, 'backup_test')
            os.makedirs(backup_dir)

            # Appeler la commande de backup
            out = StringIO()
            call_command(
                'backup_restore',
                'backup',
                '--output-dir', backup_dir,
                '--include-media',
                stdout=out
            )

            output = out.getvalue()
            print(f"Backup output: {output}")

            # Vérifier que le backup a été créé
            backup_dirs = os.listdir(backup_dir)
            self.assertGreater(len(backup_dirs), 0, "Backup directory should exist")

            backup_path = os.path.join(backup_dir, backup_dirs[0])
            manifest_path = os.path.join(backup_path, 'manifest.json')
            self.assertTrue(os.path.exists(manifest_path), "Manifest should exist")

            # Lire le manifest
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)

            print(f"Backup manifest: {manifest}")

            # 3. Détruire les données (destroy)
            # Sauvegarder les IDs pour vérification post-restore
            exam_id = self.exam.id
            student_id = self.student.id
            copy_id = self.copy.id

            Exam.objects.all().delete()
            Student.objects.all().delete()
            Copy.objects.all().delete()
            Booklet.objects.all().delete()
            Annotation.objects.all().delete()
            GradingEvent.objects.all().delete()

            # Vérifier que tout est parti
            after_destroy_counts = {
                'exams': Exam.objects.count(),
                'students': Student.objects.count(),
                'copies': Copy.objects.count(),
                'booklets': Booklet.objects.count(),
                'annotations': Annotation.objects.count(),
                'events': GradingEvent.objects.count()
            }

            print(f"After destroy counts: {after_destroy_counts}")

            all_zero = all(count == 0 for count in after_destroy_counts.values())
            self.assertTrue(all_zero, "All data should be deleted after destroy")

            # 4. Restaurer les données (recover)
            out_restore = StringIO()
            call_command(
                'backup_restore',
                'restore',
                '--backup-path', backup_path,
                stdout=out_restore
            )

            restore_output = out_restore.getvalue()
            print(f"Restore output: {restore_output}")

            # 5. Vérifier que les données sont revenues
            final_counts = {
                'exams': Exam.objects.count(),
                'students': Student.objects.count(),
                'copies': Copy.objects.count(),
                'booklets': Booklet.objects.count(),
                'annotations': Annotation.objects.count(),
                'events': GradingEvent.objects.count()
            }

            print(f"Final counts: {final_counts}")

            # Vérifier que les données sont revenues
            for key, initial_count in initial_counts.items():
                final_count = final_counts[key]
                # Pour les tests, on peut avoir plus d'objets que l'initial à cause des objets de test
                # mais on vérifie qu'au moins autant que l'initial sont présents
                self.assertGreaterEqual(final_count, initial_count,
                                      f"Should have at least {initial_count} {key}, got {final_count}")

            # Vérifier que les objets spécifiques sont revenus
            restored_copy = Copy.objects.get(anonymous_id="BACKUP_TEST_001")
            self.assertEqual(restored_copy.status, Copy.Status.GRADED)
            self.assertIsNotNone(restored_copy.student)
            self.assertEqual(restored_copy.student.ine, "TEST123456789A")

            restored_student = Student.objects.get(ine="TEST123456789A")
            self.assertEqual(restored_student.first_name, "Jean")
            self.assertEqual(restored_student.last_name, "Test")

            restored_exam = Exam.objects.get(name="Test Backup Exam")
            self.assertEqual(str(restored_exam.date), "2026-01-01")

            restored_annotation = Annotation.objects.filter(copy=restored_copy).first()
            self.assertIsNotNone(restored_annotation)
            self.assertEqual(restored_annotation.content, "Test annotation for backup")

            restored_event = GradingEvent.objects.filter(copy=restored_copy).first()
            self.assertIsNotNone(restored_event)
            self.assertEqual(restored_event.action, GradingEvent.Action.FINALIZE)

            print("✅ Backup/Restore Destroy & Recover test passed!")
            print(f"   - Initial objects: {sum(initial_counts.values())}")
            print(f"   - Final objects: {sum(final_counts.values())}")
            print(f"   - Data integrity: Verified")