import pytest
import os
import shutil
import tempfile
from django.test import TransactionTestCase
from django.core.management import call_command
from django.contrib.auth.models import User
from exams.models import Exam, Copy, Booklet
from grading.models import Annotation, GradingEvent
from students.models import Student
from django.conf import settings

class BackupRestoreDestroyRecoverTest(TransactionTestCase):
    """
    Test complet: Création -> Backup -> Destruction -> Restore -> Vérification.
    """
    
    def setUp(self):
        # Temp dir for backups
        self.backup_root = tempfile.mkdtemp()
        
        # Temp media root
        self.temp_media = tempfile.mkdtemp()
        self._original_media_root = settings.MEDIA_ROOT
        settings.MEDIA_ROOT = self.temp_media
        
    def tearDown(self):
        shutil.rmtree(self.backup_root, ignore_errors=True)
        shutil.rmtree(self.temp_media, ignore_errors=True)
        settings.MEDIA_ROOT = self._original_media_root

    def test_backup_restore_destroy_recover_full_cycle(self):
        # 1. SETUP DATA
        print("Creating Data...")
        student = Student.objects.create(
            date_naissance="2005-03-15",
            last_name="Sauvegardable",
            first_name="Jean",
            class_name="TG1"
        )
        exam = Exam.objects.create(name="Backup Exam", date="2026-06-01")
        copy = Copy.objects.create(exam=exam, anonymous_id="RESTORE_ME", student=student)
        booklet = Booklet.objects.create(exam=exam, start_page=1, end_page=2)
        copy.booklets.add(booklet)
        
        # Annotation (Deep dependency)
        # Note: Annotation requires created_by user usually
        admin = User.objects.create_superuser('admin_br', 'admin@br.com', 'pass')
        ann = Annotation.objects.create(
            copy=copy, page_index=0, type=Annotation.Type.COMMENT, 
            content="Persistent Data", x=0.1, y=0.1, w=0.1, h=0.1,
            created_by=admin
        )
        
        # Verify counts
        self.assertEqual(Exam.objects.count(), 1)
        self.assertEqual(Copy.objects.count(), 1)
        self.assertEqual(Annotation.objects.count(), 1)
        
        # 2. BACKUP
        print("Running Backup...")
        out =  tempfile.mkdtemp(dir=self.backup_root)
        call_command('backup', output_dir=out, include_media=True, verbosity=0)
        
        # Find generated backup folder
        backup_name = os.listdir(out)[0]
        backup_path = os.path.join(out, backup_name)
        
        # 3. DESTROY
        print("DESTROYING DATA...")
        Annotation.objects.all().delete()
        Copy.objects.all().delete()
        Booklet.objects.all().delete()
        Exam.objects.all().delete() # Cascade should handle most, but being explicit
        Student.objects.all().delete()
        User.objects.filter(username='admin_br').delete() # Be careful not to delete ALL users if other tests run in parallel DB, but this is TransactionTestCase
        
        self.assertEqual(Exam.objects.count(), 0)
        self.assertEqual(Annotation.objects.count(), 0)
        
        # 4. RESTORE
        print(f"Restoring from {backup_path}...")
        call_command('restore', backup_path)
        
        # 5. VERIFY
        print("Verifying Integrity...")
        self.assertEqual(Exam.objects.count(), 1)
        self.assertEqual(Copy.objects.count(), 1)
        self.assertEqual(Annotation.objects.count(), 1)
        
        restored_ann = Annotation.objects.first()
        self.assertEqual(restored_ann.content, "Persistent Data")
        self.assertEqual(restored_ann.copy.anonymous_id, "RESTORE_ME")
        self.assertEqual(restored_ann.copy.student.ine, "BRTEST001")
        
        print("✓ DESTROY/RECOVER CYCLE PASSED")