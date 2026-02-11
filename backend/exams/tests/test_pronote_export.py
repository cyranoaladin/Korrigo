"""
Unit Tests for PRONOTE CSV Export Service

Tests the PronoteExporter service class methods.
Reference: spec.md section 5.1
"""
from django.test import TestCase
from django.contrib.auth.models import User
from exams.models import Exam, Copy
from exams.services.pronote_export import PronoteExporter, ValidationError
from students.models import Student
from grading.models import Annotation
from decimal import Decimal


class PronoteExporterFormatTests(TestCase):
    """Test decimal formatting and comment sanitization"""
    
    def setUp(self):
        self.exam = Exam.objects.create(
            name='Test Exam',
            date='2026-01-31'
        )
        self.exporter = PronoteExporter(self.exam)
    
    def test_format_decimal_french_typical_values(self):
        """Test French decimal formatting with typical values"""
        self.assertEqual(self.exporter.format_decimal_french(15.5), '15,50')
        self.assertEqual(self.exporter.format_decimal_french(12.0), '12,00')
        self.assertEqual(self.exporter.format_decimal_french(18.25), '18,25')
    
    def test_format_decimal_french_rounding(self):
        """Test proper rounding (half-up)"""
        self.assertEqual(self.exporter.format_decimal_french(15.555), '15,56')
        self.assertEqual(self.exporter.format_decimal_french(15.554), '15,55')
        self.assertEqual(self.exporter.format_decimal_french(19.995), '20,00')
    
    def test_format_decimal_french_edge_cases(self):
        """Test edge values"""
        self.assertEqual(self.exporter.format_decimal_french(0.0), '0,00')
        self.assertEqual(self.exporter.format_decimal_french(20.0), '20,00')
        self.assertEqual(self.exporter.format_decimal_french(0.01), '0,01')
    
    def test_format_decimal_french_with_precision(self):
        """Test custom precision"""
        self.assertEqual(
            self.exporter.format_decimal_french(1.5, precision=1), 
            '1,5'
        )
        self.assertEqual(
            self.exporter.format_decimal_french(1.123, precision=3), 
            '1,123'
        )
    
    def test_sanitize_comment_normal(self):
        """Test sanitization of normal comments"""
        self.assertEqual(
            self.exporter.sanitize_comment("Bon travail"), 
            "Bon travail"
        )
        self.assertEqual(
            self.exporter.sanitize_comment("Très bien!"), 
            "Très bien!"
        )
    
    def test_sanitize_comment_with_newlines(self):
        """Test newline replacement"""
        self.assertEqual(
            self.exporter.sanitize_comment("Line 1\nLine 2"), 
            "Line 1 Line 2"
        )
        self.assertEqual(
            self.exporter.sanitize_comment("Line 1\r\nLine 2"), 
            "Line 1 Line 2"
        )
    
    def test_sanitize_comment_csv_injection(self):
        """Test CSV injection prevention"""
        # Leading equals sign should be removed
        self.assertEqual(
            self.exporter.sanitize_comment("=FORMULA()"), 
            "FORMULA()"
        )
        self.assertEqual(
            self.exporter.sanitize_comment("+VALUE"), 
            "VALUE"
        )
        self.assertEqual(
            self.exporter.sanitize_comment("-CMD"), 
            "CMD"
        )
        self.assertEqual(
            self.exporter.sanitize_comment("@IMPORT"), 
            "IMPORT"
        )
    
    def test_sanitize_comment_length_limit(self):
        """Test comment length limiting"""
        long_comment = "x" * 600
        sanitized = self.exporter.sanitize_comment(long_comment)
        self.assertEqual(len(sanitized), 500)
        self.assertTrue(sanitized.endswith("..."))
    
    def test_sanitize_comment_empty(self):
        """Test empty/None comments"""
        self.assertEqual(self.exporter.sanitize_comment(None), "")
        self.assertEqual(self.exporter.sanitize_comment(""), "")
        self.assertEqual(self.exporter.sanitize_comment("   "), "")


class PronoteExporterGradeCalculationTests(TestCase):
    """Test grade calculation logic"""
    
    def setUp(self):
        self.exam = Exam.objects.create(
            name='Math Exam',
            date='2026-01-31',
            grading_structure=[
                {"id": "ex1", "max_points": 10},
                {"id": "ex2", "max_points": 10}
            ]
        )
        self.exporter = PronoteExporter(self.exam)
        
        self.student = Student.objects.create(
            first_name='Jean',
            last_name='Dupont',
            class_name='TS1',
            date_naissance='2005-01-15'
        )
        
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='COPY001',
            student=self.student,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        
        self.user = User.objects.create_user(
            username='teacher',
            password='pass'
        )
    
    def test_calculate_grade_from_score_model(self):
        """Test grade calculation from annotations"""
        Annotation.objects.create(
            copy=self.copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=8,
            created_by=self.user
        )
        Annotation.objects.create(
            copy=self.copy,
            page_index=1,
            x=0.2, y=0.2, w=0.1, h=0.1,
            score_delta=7,
            created_by=self.user
        )
        
        grade = self.exporter.calculate_copy_grade(self.copy)
        
        # 8 + 7 = 15 out of 20 = 15.0
        self.assertAlmostEqual(grade, 15.0, places=2)
    
    def test_calculate_grade_from_annotations(self):
        """Test grade calculation from annotations when no Score"""
        Annotation.objects.create(
            copy=self.copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=8,
            created_by=self.user
        )
        Annotation.objects.create(
            copy=self.copy,
            page_index=1,
            x=0.2, y=0.2, w=0.1, h=0.1,
            score_delta=7,
            created_by=self.user
        )
        
        grade = self.exporter.calculate_copy_grade(self.copy)
        
        # 8 + 7 = 15 out of 20 = 15.0
        self.assertAlmostEqual(grade, 15.0, places=2)
    
    def test_calculate_grade_scaling(self):
        """Test scaling from different max score to /20"""
        # Exam with /40 scale
        exam_40 = Exam.objects.create(
            name='Exam 40',
            date='2026-01-31',
            grading_structure=[
                {"id": "ex1", "max_points": 20},
                {"id": "ex2", "max_points": 20}
            ]
        )
        copy_40 = Copy.objects.create(
            exam=exam_40,
            anonymous_id='COPY002',
            student=self.student,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        # Create annotations with score_delta: 16 + 14 = 30 out of 40
        Annotation.objects.create(
            copy=copy_40,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=16,
            created_by=self.user
        )
        Annotation.objects.create(
            copy=copy_40,
            page_index=1,
            x=0.2, y=0.2, w=0.1, h=0.1,
            score_delta=14,
            created_by=self.user
        )
        
        exporter_40 = PronoteExporter(exam_40)
        grade = exporter_40.calculate_copy_grade(copy_40)
        
        # 30/40 = 15/20
        self.assertAlmostEqual(grade, 15.0, places=2)
    
    def test_calculate_grade_clamping(self):
        """Test clamping to [0, 20]"""
        # Negative score (should clamp to 0)
        Annotation.objects.create(
            copy=self.copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=-50,
            created_by=self.user
        )
        
        grade = self.exporter.calculate_copy_grade(self.copy)
        self.assertEqual(grade, 0.0)
        
        # Score > 20 (should clamp to 20)
        copy2 = Copy.objects.create(
            exam=self.exam,
            anonymous_id='COPY003',
            student=self.student,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Annotation.objects.create(
            copy=copy2,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=15,
            created_by=self.user
        )
        Annotation.objects.create(
            copy=copy2,
            page_index=1,
            x=0.2, y=0.2, w=0.1, h=0.1,
            score_delta=15,
            created_by=self.user
        )
        
        grade2 = self.exporter.calculate_copy_grade(copy2)
        self.assertEqual(grade2, 20.0)
    
    def test_calculate_grade_no_data_raises_error(self):
        """Test that missing grade data raises ValueError"""
        copy_empty = Copy.objects.create(
            exam=self.exam,
            anonymous_id='COPY_EMPTY',
            student=self.student,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        
        with self.assertRaises(ValueError) as cm:
            self.exporter.calculate_copy_grade(copy_empty)
        
        self.assertIn("No grade data found", str(cm.exception))


class PronoteExporterValidationTests(TestCase):
    """Test export validation logic"""
    
    def setUp(self):
        self.exam = Exam.objects.create(
            name='Validation Test',
            date='2026-01-31',
            grading_structure=[{"id": "ex1", "max_points": 20}]
        )
        self.exporter = PronoteExporter(self.exam)
        
        self.student = Student.objects.create(
            first_name='Marie',
            last_name='Martin',
            class_name='TS2',
            date_naissance='2005-02-20'
        )
        
        self.user = User.objects.create_user(
            username='teacher',
            password='pass'
        )
    
    def test_validation_no_copies(self):
        """Test validation fails when no copies exist"""
        result = self.exporter.validate_export_eligibility()
        
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Aucune copie trouvée", result.errors[0])
    
    def test_validation_no_graded_copies(self):
        """Test validation fails when no graded copies"""
        Copy.objects.create(
            exam=self.exam,
            anonymous_id='STAGING001',
            status=Copy.Status.STAGING
        )
        
        result = self.exporter.validate_export_eligibility()
        
        self.assertFalse(result.is_valid)
        self.assertIn("Aucune copie notée trouvée", result.errors[0])
    
    def test_validation_unidentified_copies(self):
        """Test validation fails with unidentified graded copies"""
        Copy.objects.create(
            exam=self.exam,
            anonymous_id='GRADED001',
            status=Copy.Status.GRADED,
            is_identified=False
        )
        
        result = self.exporter.validate_export_eligibility()
        
        self.assertFalse(result.is_valid)
        self.assertIn("non identifiée", result.errors[0])
    
    def test_validation_missing_student(self):
        """Test validation fails when copy is identified but has no linked student."""
        Copy.objects.create(
            exam=self.exam,
            anonymous_id='COPY_NO_STUDENT',
            student=None,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        
        result = self.exporter.validate_export_eligibility()
        
        self.assertFalse(result.is_valid)
        self.assertIn("sans élève", result.errors[0])
    
    def test_validation_success(self):
        """Test validation passes with valid graded copies"""
        user = User.objects.create(username='teacher_validation_success')
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='VALID001',
            student=self.student,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=15,
            created_by=user
        )
        
        result = self.exporter.validate_export_eligibility()
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_validation_warning_delimiter_in_comment(self):
        """Test warning for comments with delimiter"""
        user = User.objects.create(username='teacher_warning_delimiter')
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='COMMENT001',
            student=self.student,
            is_identified=True,
            status=Copy.Status.GRADED,
            global_appreciation="Bien; mais peut mieux faire"
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=14,
            created_by=user
        )
        
        result = self.exporter.validate_export_eligibility()
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("point-virgule", result.warnings[0])


class PronoteExporterCSVGenerationTests(TestCase):
    """Test CSV generation"""
    
    def setUp(self):
        self.exam = Exam.objects.create(
            name='MATHEMATIQUES',
            date='2026-01-31',
            grading_structure=[{"id": "ex1", "max_points": 20}]
        )
        self.exporter = PronoteExporter(self.exam, coefficient=1.0)
        
        self.student1 = Student.objects.create(
            first_name='Alice',
            last_name='Durand',
            class_name='TS1',
            date_naissance='2005-04-01'
        )
        self.student2 = Student.objects.create(
            first_name='Bob',
            last_name='Lefebvre',
            class_name='TS1',
            date_naissance='2005-05-02'
        )
        
        self.user = User.objects.create_user(
            username='teacher',
            password='pass'
        )
    
    def test_generate_csv_format(self):
        """Test CSV format and structure"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='CSV001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED,
            global_appreciation="Excellent travail"
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=16,
            created_by=self.user
        )
        
        csv_content, warnings = self.exporter.generate_csv()
        
        # Check UTF-8 BOM
        self.assertTrue(csv_content.startswith('\ufeff'))
        
        # Check header
        lines = csv_content.split('\r\n')
        self.assertIn('INE;MATIERE;NOTE;COEFF;COMMENTAIRE', lines[0])
        
        # Check data row
        self.assertIn('Durand Alice;MATHEMATIQUES;16,00;1,0;Excellent travail', lines[1])
    
    def test_generate_csv_multiple_copies(self):
        """Test CSV with multiple copies"""
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
            score_delta=12,
            created_by=self.user
        )
        
        csv_content, warnings = self.exporter.generate_csv()
        
        lines = csv_content.strip().split('\r\n')
        # Header + 2 data rows
        self.assertEqual(len(lines), 3)
    
    def test_generate_csv_validation_error(self):
        """Test CSV generation fails validation"""
        # Create unidentified copy
        Copy.objects.create(
            exam=self.exam,
            anonymous_id='INVALID001',
            is_identified=False,
            status=Copy.Status.GRADED
        )
        
        with self.assertRaises(ValidationError):
            self.exporter.generate_csv()
    
    def test_generate_csv_coefficient_formatting(self):
        """Test coefficient formatting"""
        exporter_custom = PronoteExporter(self.exam, coefficient=2.5)
        
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
        
        csv_content, warnings = exporter_custom.generate_csv()
        
        # Coefficient should be "2,5" (French format, 1 decimal)
        self.assertIn(';2,5;', csv_content)


class PronoteExporterMaxScoreCalculationTests(TestCase):
    """Test _calculate_max_score with different grading structures"""
    
    def test_calculate_max_score_simple(self):
        """Test simple grading structure"""
        exam = Exam.objects.create(
            name='Simple',
            date='2026-01-31',
            grading_structure=[
                {"id": "ex1", "max_points": 10},
                {"id": "ex2", "max_points": 10}
            ]
        )
        exporter = PronoteExporter(exam)
        
        max_score = exporter._calculate_max_score(exam.grading_structure)
        self.assertEqual(max_score, 20.0)
    
    def test_calculate_max_score_nested(self):
        """Test nested grading structure with children"""
        exam = Exam.objects.create(
            name='Nested',
            date='2026-01-31',
            grading_structure=[
                {
                    "id": "ex1",
                    "max_points": 10,
                    "children": [
                        {"id": "q1", "max_points": 5},
                        {"id": "q2", "max_points": 5}
                    ]
                }
            ]
        )
        exporter = PronoteExporter(exam)
        
        max_score = exporter._calculate_max_score(exam.grading_structure)
        # Should sum parent + children: 10 + 5 + 5 = 20
        self.assertEqual(max_score, 20.0)
    
    def test_calculate_max_score_empty_defaults_to_20(self):
        """Test that empty structure defaults to 20"""
        exam = Exam.objects.create(
            name='Empty',
            date='2026-01-31',
            grading_structure=[]
        )
        exporter = PronoteExporter(exam)
        
        max_score = exporter._calculate_max_score(exam.grading_structure)
        self.assertEqual(max_score, 20.0)
    
    def test_calculate_max_score_with_points_field(self):
        """Test structure using 'points' instead of 'max_points'"""
        exam = Exam.objects.create(
            name='Points',
            date='2026-01-31',
            grading_structure=[
                {"id": "q1", "points": 8},
                {"id": "q2", "points": 12}
            ]
        )
        exporter = PronoteExporter(exam)
        
        max_score = exporter._calculate_max_score(exam.grading_structure)
        self.assertEqual(max_score, 20.0)
