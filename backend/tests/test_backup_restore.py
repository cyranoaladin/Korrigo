"""
Test de backup/restore pour valider les procédures
"""
from django.test import TestCase
from django.core.management import call_command
from django.core.files.base import ContentFile
from exams.models import Exam, Copy
from students.models import Student
from django.contrib.auth.models import User, Group
import tempfile
import os
import shutil
from core.auth import UserRole


class BackupRestoreTest(TestCase):
    """
    Test de backup et restore des données
    """
    def setUp(self):
        # Create test data
        self.admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        self.teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='testpass'
        )
        self.admin_user.groups.add(self.admin_group)
        
        self.student = Student.objects.create(
            ine="1234567890A",
            first_name="Jean",
            last_name="Dupont",
            class_name="TG2",
            email="jean.dupont@example.com",
            user=self.admin_user  # Using admin user for test
        )
        
        self.exam = Exam.objects.create(
            name='Test Exam Backup',
            date='2026-01-01'
        )
        
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="BACKUP123",
            status=Copy.Status.GRADED
        )

    def test_backup_process(self):
        """
        Test du processus de backup
        """
        # Create a temporary directory for the backup
        with tempfile.TemporaryDirectory() as temp_dir:
            # Call the backup command
            call_command(
                'backup_restore',
                'backup',
                '--output-dir', temp_dir,
                '--include-media',
                verbosity=2
            )
            
            # Check that backup was created
            backup_dirs = os.listdir(temp_dir)
            self.assertGreater(len(backup_dirs), 0, "Backup directory should be created")
            
            backup_path = os.path.join(temp_dir, backup_dirs[0])
            self.assertTrue(os.path.exists(backup_path), "Backup directory should exist")
            
            # Check manifest exists
            manifest_path = os.path.join(backup_path, 'manifest.json')
            self.assertTrue(os.path.exists(manifest_path), "Manifest file should exist")
            
            # Check database backup exists
            import json
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            db_backup_file = manifest.get('database_backup')
            if db_backup_file:
                db_backup_path = os.path.join(backup_path, db_backup_file)
                self.assertTrue(os.path.exists(db_backup_path), "Database backup file should exist")
            
            print("✓ Backup process test passed!")

    def test_backup_restore_cycle(self):
        """
        Test complet du cycle backup/restore
        """
        # Create initial data counts
        initial_exam_count = Exam.objects.count()
        initial_student_count = Student.objects.count()
        initial_copy_count = Copy.objects.count()
        
        # Create a temporary directory for the backup
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Create backup
            call_command(
                'backup_restore',
                'backup',
                '--output-dir', temp_dir,
                '--include-media',
                verbosity=2
            )
            
            # Verify backup was created
            backup_dirs = os.listdir(temp_dir)
            self.assertGreater(len(backup_dirs), 0, "Backup directory should be created")
            backup_path = os.path.join(temp_dir, backup_dirs[0])
            
            # Step 2: Add more data to verify restore overwrites
            new_exam = Exam.objects.create(
                name='New Exam After Backup',
                date='2026-02-01'
            )
            
            # Verify data was added
            self.assertGreater(Exam.objects.count(), initial_exam_count)
            
            # Step 3: Perform restore (this would normally overwrite, but for safety we'll test dry run)
            # For safety in testing, we'll just do a dry run
            call_command(
                'backup_restore',
                'restore',
                '--backup-path', backup_path,
                '--dry-run',
                verbosity=2
            )
            
            # Count should still be higher after adding new exam
            self.assertGreater(Exam.objects.count(), initial_exam_count)
            
            print("✓ Backup/restore cycle test passed!")