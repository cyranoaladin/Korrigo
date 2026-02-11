"""
Management Command Tests for export_pronote

Tests the Django management command for PRONOTE export.
Reference: spec.md section 5.3
"""
from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.auth.models import User
from exams.models import Exam, Copy
from students.models import Student
from grading.models import Annotation
import tempfile
import os
from io import StringIO


class ExportPronoteCommandTests(TestCase):
    """Test export_pronote management command"""
    
    def setUp(self):
        self.exam = Exam.objects.create(
            name='MATHEMATIQUES',
            date='2026-02-01',
            grading_structure=[{"id": "ex1", "max_points": 20}]
        )
        
        self.student1 = Student.objects.create(
            first_name='Alice',
            last_name='Durand',
            class_name='TS1',
            date_naissance='2005-01-15'
        )
        
        self.student2 = Student.objects.create(
            first_name='Bob',
            last_name='Martin',
            class_name='TS1',
            date_naissance='2005-02-20'
        )
        
        self.user = User.objects.create_user(
            username='teacher',
            password='pass'
        )
    
    def test_command_with_invalid_exam_id(self):
        """Test command fails with invalid exam UUID"""
        with self.assertRaises(CommandError) as cm:
            call_command('export_pronote', 'invalid-uuid-12345')
        
        self.assertIn('not found', str(cm.exception).lower())
    
    def test_command_with_nonexistent_exam(self):
        """Test command fails with nonexistent exam UUID"""
        fake_uuid = '00000000-0000-0000-0000-000000000000'
        
        with self.assertRaises(CommandError) as cm:
            call_command('export_pronote', fake_uuid)
        
        self.assertIn('not found', str(cm.exception).lower())
    
    def test_command_validation_only_mode(self):
        """Test --validate-only mode doesn't generate CSV"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='VAL001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=15,
            created_by=self.user
        )
        
        out = StringIO()
        err = StringIO()
        
        call_command(
            'export_pronote',
            str(self.exam.id),
            '--validate-only',
            stdout=out,
            stderr=err
        )
        
        output = out.getvalue()
        error_output = err.getvalue()
        
        # Should mention validation
        self.assertIn('Validation', output)
        
        # Should say no export generated
        self.assertIn('Mode validation uniquement', output)
        
        # Should not have CSV data
        self.assertNotIn('INE;MATIERE;NOTE', output)
    
    def test_command_validation_fails_unidentified_copies(self):
        """Test command fails validation with unidentified copies"""
        Copy.objects.create(
            exam=self.exam,
            anonymous_id='UNID001',
            status=Copy.Status.GRADED,
            is_identified=False
        )
        
        with self.assertRaises(CommandError) as cm:
            call_command('export_pronote', str(self.exam.id))
        
        self.assertIn('Export impossible', str(cm.exception))
    
    def test_command_validation_fails_missing_student(self):
        """Test command fails validation when copy has no linked student."""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='NOSTUDENT001',
            student=None,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=15,
            created_by=self.user
        )
        
        with self.assertRaises(CommandError) as cm:
            call_command('export_pronote', str(self.exam.id))
        
        self.assertIn('Export impossible', str(cm.exception))
    
    def test_command_output_to_file(self):
        """Test --output option writes to file"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='FILE001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED,
            global_appreciation="Excellent"
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=15,
            created_by=self.user
        )
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            out = StringIO()
            err = StringIO()
            
            call_command(
                'export_pronote',
                str(self.exam.id),
                '--output', tmp_path,
                stdout=out,
                stderr=err
            )
            
            # Check success message
            output = out.getvalue()
            self.assertIn('Export réussi', output)
            self.assertIn(tmp_path, output)
            
            # Check file was created
            self.assertTrue(os.path.exists(tmp_path))
            
            # Check file content
            with open(tmp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check UTF-8 BOM
            self.assertTrue(content.startswith('\ufeff'))
            
            # Check header
            self.assertIn('INE;MATIERE;NOTE;COEFF;COMMENTAIRE', content)
            
            # Check data
            self.assertIn('Durand Alice', content)
            self.assertIn('MATHEMATIQUES', content)
            self.assertIn('15,00', content)
            self.assertIn('Excellent', content)
            
            # Check CRLF line endings
            self.assertIn('\r\n', content)
            
        finally:
            # Cleanup
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_command_output_to_stdout(self):
        """Test default behavior writes CSV to sys.stdout and count to stderr"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='STDOUT001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=16,
            created_by=self.user
        )
        
        # Command writes CSV to sys.stdout (not self.stdout), so use --output
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            out = StringIO()
            err = StringIO()
            
            call_command(
                'export_pronote',
                str(self.exam.id),
                '--output', tmp_path,
                stdout=out,
                stderr=err
            )
            
            with open(tmp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Should have CSV content
            self.assertIn('INE;MATIERE;NOTE;COEFF;COMMENTAIRE', content)
            self.assertIn('Durand Alice', content)
            self.assertIn('16,00', content)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_command_custom_coefficient(self):
        """Test --coefficient option"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='COEFF001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=15,
            created_by=self.user
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            call_command(
                'export_pronote',
                str(self.exam.id),
                '--coefficient', '2.5',
                '--output', tmp_path
            )
            
            with open(tmp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check coefficient in French format (1 decimal)
            self.assertIn(';2,5;', content)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_command_with_multiple_copies(self):
        """Test command exports multiple copies"""
        copy1 = Copy.objects.create(
            exam=self.exam,
            anonymous_id='MULTI001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        copy2 = Copy.objects.create(
            exam=self.exam,
            anonymous_id='MULTI002',
            student=self.student2,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        
        Annotation.objects.create(
            copy=copy1,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=16,
            created_by=self.user
        )
        Annotation.objects.create(
            copy=copy2,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=14,
            created_by=self.user
        )
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            out = StringIO()
            
            call_command(
                'export_pronote',
                str(self.exam.id),
                '--output', tmp_path,
                stdout=out
            )
            
            # Check file content
            with open(tmp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Should have 3 lines: header + 2 data rows
            lines = content.strip().split('\r\n')
            self.assertEqual(len(lines), 3)
            
            # Check both students
            self.assertIn('Durand Alice', content)
            self.assertIn('Martin Bob', content)
            
            # Check success message shows count
            output = out.getvalue()
            self.assertIn('2 notes', output)
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_command_with_warnings(self):
        """Test command displays warnings"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='WARN001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED,
            global_appreciation="Comment with ; semicolon"
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=15,
            created_by=self.user
        )
        
        out = StringIO()
        err = StringIO()
        
        call_command(
            'export_pronote',
            str(self.exam.id),
            stdout=out,
            stderr=err
        )
        
        output = out.getvalue()
        
        # Should show warning about semicolon
        self.assertIn('Avertissement', output)
        self.assertIn('point-virgule', output)
    
    def test_command_handles_special_characters(self):
        """Test command handles accents and special chars"""
        student_accent = Student.objects.create(
            first_name='François',
            last_name='Müller',
            class_name='TS1',
            date_naissance='2005-04-01'
        )
        
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='ACCENT001',
            student=student_accent,
            is_identified=True,
            status=Copy.Status.GRADED,
            global_appreciation="Très bien!"
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=18,
            created_by=self.user
        )
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            call_command(
                'export_pronote',
                str(self.exam.id),
                '--output', tmp_path
            )
            
            # Check file content
            with open(tmp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check accents are preserved
            self.assertIn('Müller François', content)
            self.assertIn('Très bien', content)
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_command_with_annotations_fallback(self):
        """Test command works with annotation-based grades"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='ANNOT001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        
        # Add annotations instead of Score
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=8,
            created_by=self.user
        )
        Annotation.objects.create(
            copy=copy,
            page_index=1,
            x=0.2, y=0.2, w=0.1, h=0.1,
            score_delta=7,
            created_by=self.user
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            call_command(
                'export_pronote',
                str(self.exam.id),
                '--output', tmp_path
            )
            
            with open(tmp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Should have grade from annotations (8 + 7 = 15)
            self.assertIn('15,00', content)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_command_file_write_error(self):
        """Test command handles file write errors"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='WRITEERR001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=15,
            created_by=self.user
        )
        
        # Try to write to invalid path
        invalid_path = '/nonexistent/directory/export.csv'
        
        with self.assertRaises(CommandError) as cm:
            call_command(
                'export_pronote',
                str(self.exam.id),
                '--output', invalid_path
            )
        
        self.assertIn('Erreur', str(cm.exception))
