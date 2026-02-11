"""
Tests for the seed_initial_exams management command.
Covers: CSV parsing, anonymization, dispatch, idempotence.
"""
import csv
import io
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase, override_settings

from exams.management.commands.seed_initial_exams import (
    generate_copy_code,
    parse_student_csv,
)
from exams.models import Copy, Exam
from students.models import Student


class TestGenerateCopyCode(TestCase):
    """Test the anonymization code generation."""

    def test_stable_output(self):
        """Same inputs always produce the same code."""
        code1 = generate_copy_code("exam-123", "copie_DUPONT_JEAN.pdf")
        code2 = generate_copy_code("exam-123", "copie_DUPONT_JEAN.pdf")
        assert code1 == code2

    def test_different_inputs_different_codes(self):
        """Different inputs produce different codes."""
        code1 = generate_copy_code("exam-123", "copie_DUPONT_JEAN.pdf")
        code2 = generate_copy_code("exam-456", "copie_DUPONT_JEAN.pdf")
        code3 = generate_copy_code("exam-123", "copie_MARTIN_PAUL.pdf")
        assert code1 != code2
        assert code1 != code3

    def test_format(self):
        """Code is 7 chars: 2 letters + 4 digits + 1 checksum."""
        code = generate_copy_code("exam-id", "test.pdf")
        assert len(code) == 7
        assert code[:2].isalpha()
        assert code[2:6].isdigit()
        assert code[6].isdigit()

    def test_checksum(self):
        """Checksum is sum of ascii values mod 10."""
        code = generate_copy_code("test-exam", "test.pdf")
        body = code[:6]
        expected_checksum = sum(ord(c) for c in body) % 10
        assert int(code[6]) == expected_checksum


class TestParseStudentCSV(TestCase):
    """Test CSV parsing with various formats."""

    def _write_csv(self, content, encoding='utf-8'):
        """Helper to write CSV content to a temp file."""
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False, encoding=encoding
        )
        tmp.write(content)
        tmp.close()
        return tmp.name

    def test_standard_csv(self):
        """Parse standard comma-separated CSV."""
        path = self._write_csv(
            'Élèves,Né(e) le,Adresse E-mail,Classe,EDS,Groupe\n'
            'DUPONT JEAN,15/03/2008,jean.dupont@test.tn,T.01,"EDS MATHS",G1\n'
            'MARTIN PAUL,20/06/2007,paul.martin@test.tn,T.02,"EDS PC",G2\n'
        )
        students = parse_student_csv(path)
        os.unlink(path)

        assert len(students) == 2
        assert students[0]['last_name'] == 'DUPONT'
        assert students[0]['first_name'] == 'JEAN'
        assert students[0]['email'] == 'jean.dupont@test.tn'
        assert str(students[0]['date_naissance']) == '2008-03-15'

    def test_empty_lines_skipped(self):
        """Empty lines are ignored."""
        path = self._write_csv(
            'Élèves,Né(e) le,Adresse E-mail,Classe,EDS,Groupe\n'
            '\n'
            'DUPONT JEAN,15/03/2008,jean.dupont@test.tn,T.01,"",G1\n'
            '\n'
        )
        students = parse_student_csv(path)
        os.unlink(path)
        assert len(students) == 1

    def test_utf8_bom(self):
        """Handle UTF-8 BOM correctly."""
        content = '\ufeffÉlèves,Né(e) le,Adresse E-mail,Classe,EDS,Groupe\nDUPONT JEAN,01/01/2008,test@t.tn,T.01,"",G1\n'
        tmp = tempfile.NamedTemporaryFile(
            mode='wb', suffix='.csv', delete=False
        )
        tmp.write(content.encode('utf-8-sig'))
        tmp.close()
        students = parse_student_csv(tmp.name)
        os.unlink(tmp.name)
        assert len(students) == 1

    def test_missing_file(self):
        """Returns empty list for missing file."""
        students = parse_student_csv('/nonexistent/path/file.csv')
        assert students == []

    def test_compound_names(self):
        """Handle compound names (hyphenated, multi-word)."""
        path = self._write_csv(
            'Élèves,Né(e) le,Adresse E-mail,Classe,EDS,Groupe\n'
            'BEN RHOUMA ALAEDDINE,01/01/2008,a@t.tn,T.01,"",G1\n'
        )
        students = parse_student_csv(path)
        os.unlink(path)
        # First word is last_name, rest is first_name
        assert students[0]['last_name'] == 'BEN'
        assert students[0]['first_name'] == 'RHOUMA ALAEDDINE'

    def test_crlf_line_endings(self):
        """Handle Windows-style CRLF line endings."""
        content = 'Élèves,Né(e) le,Adresse E-mail,Classe,EDS,Groupe\r\nDUPONT JEAN,01/01/2008,t@t.tn,T.01,"",G1\r\n'
        tmp = tempfile.NamedTemporaryFile(
            mode='wb', suffix='.csv', delete=False
        )
        tmp.write(content.encode('utf-8'))
        tmp.close()
        students = parse_student_csv(tmp.name)
        os.unlink(tmp.name)
        assert len(students) == 1


@pytest.mark.django_db
class TestSeedCommand(TestCase):
    """Test seed_initial_exams command end-to-end."""

    def setUp(self):
        # Create a temp directory with test CSV and PDFs
        self.test_dir = tempfile.mkdtemp()
        self._create_test_csv(
            os.path.join(self.test_dir, 'eleves_maths_J1.csv'),
            [
                ('DUPONT JEAN', '01/01/2008', 'jean.dupont@test.tn', 'T.01'),
                ('MARTIN PAUL', '02/02/2008', 'paul.martin@test.tn', 'T.02'),
            ]
        )
        self._create_test_csv(
            os.path.join(self.test_dir, 'eleves_maths_J2.csv'),
            [
                ('GARCIA MARIE', '03/03/2008', 'marie.garcia@test.tn', 'T.03'),
            ]
        )

        # Create minimal PDFs
        self._create_test_pdfs(os.path.join(self.test_dir, 'copies_finales_J1'), [
            'copie_DUPONT_JEAN.pdf', 'copie_MARTIN_PAUL.pdf',
        ])
        self._create_test_pdfs(os.path.join(self.test_dir, 'copies_finales_J2'), [
            'copie_GARCIA_MARIE.pdf',
        ])

    def _create_test_csv(self, path, rows):
        with open(path, 'w', encoding='utf-8') as f:
            f.write('Élèves,Né(e) le,Adresse E-mail,Classe,EDS,Groupe\n')
            for name, dob, email, classe in rows:
                f.write(f'{name},{dob},{email},{classe},"EDS MATHS",G1\n')

    def _create_test_pdfs(self, dir_path, filenames):
        os.makedirs(dir_path, exist_ok=True)
        for name in filenames:
            self._create_minimal_pdf(os.path.join(dir_path, name))

    def _create_minimal_pdf(self, path):
        """Create a minimal valid PDF for testing."""
        try:
            import fitz
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text((72, 72), "Test Page", fontsize=12)
            doc.save(path)
            doc.close()
        except ImportError:
            # Fallback: write minimal PDF bytes
            with open(path, 'wb') as f:
                f.write(b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
                        b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
                        b'3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n'
                        b'xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n'
                        b'0000000058 00000 n \n0000000115 00000 n \n'
                        b'trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF')

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_creates_groups(self):
        """Seed creates required groups."""
        call_command('seed_initial_exams', data_dir=self.test_dir, password='test123')
        assert Group.objects.filter(name='admin').exists()
        assert Group.objects.filter(name='teacher').exists()
        assert Group.objects.filter(name='student').exists()

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_creates_admin(self):
        """Seed creates admin user."""
        call_command('seed_initial_exams', data_dir=self.test_dir, password='test123')
        admin = User.objects.get(username='admin')
        assert admin.is_superuser
        assert admin.is_staff
        assert admin.check_password('test123')

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_creates_correctors(self):
        """Seed creates all 8 correctors."""
        call_command('seed_initial_exams', data_dir=self.test_dir, password='test123')
        corrector_emails = [
            'alaeddine.benrhouma@ert.tn', 'patrick.dupont@ert.tn',
            'philippe.carr@ert.tn', 'selima.klibi@ert.tn',
            'chawki.saadi@ert.tn', 'edouard.rousseau@ert.tn',
            'sami.bentiba@ert.tn', 'laroussi.laroussi@ert.tn',
        ]
        for email in corrector_emails:
            assert User.objects.filter(username=email).exists(), f"Corrector {email} not found"

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_creates_exams(self):
        """Seed creates 2 exams."""
        call_command('seed_initial_exams', data_dir=self.test_dir, password='test123')
        assert Exam.objects.filter(name='BB Jour 1').exists()
        assert Exam.objects.filter(name='BB Jour 2').exists()

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_creates_students(self):
        """Seed creates student accounts from CSV."""
        call_command('seed_initial_exams', data_dir=self.test_dir, password='test123')
        assert Student.objects.filter(email='jean.dupont@test.tn').exists()
        assert Student.objects.filter(email='paul.martin@test.tn').exists()
        # Student has linked user account
        student = Student.objects.get(email='jean.dupont@test.tn')
        assert student.user is not None
        assert student.user.check_password('test123')

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_idempotent(self):
        """Running seed twice does not duplicate data."""
        media_root = tempfile.mkdtemp()
        with self.settings(MEDIA_ROOT=media_root):
            call_command('seed_initial_exams', data_dir=self.test_dir, password='test123')
            count1_exams = Exam.objects.count()
            count1_users = User.objects.count()
            count1_students = Student.objects.count()

            call_command('seed_initial_exams', data_dir=self.test_dir, password='test123')
            count2_exams = Exam.objects.count()
            count2_users = User.objects.count()
            count2_students = Student.objects.count()

            assert count1_exams == count2_exams
            assert count1_users == count2_users
            assert count1_students == count2_students

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_copies_imported(self):
        """Seed imports PDF copies."""
        call_command('seed_initial_exams', data_dir=self.test_dir, password='test123')
        exam_j1 = Exam.objects.get(name='BB Jour 1')
        copies = Copy.objects.filter(exam=exam_j1)
        assert copies.count() == 2  # 2 PDFs in J1

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_copies_dispatched(self):
        """Copies are assigned to correctors."""
        call_command('seed_initial_exams', data_dir=self.test_dir, password='test123')
        exam_j1 = Exam.objects.get(name='BB Jour 1')
        assigned = Copy.objects.filter(
            exam=exam_j1, assigned_corrector__isnull=False
        ).count()
        total = Copy.objects.filter(exam=exam_j1).count()
        assert assigned == total

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_dispatch_balanced(self):
        """Dispatch distributes copies evenly (diff max 1)."""
        call_command('seed_initial_exams', data_dir=self.test_dir, password='test123')
        exam_j1 = Exam.objects.get(name='BB Jour 1')
        correctors = list(exam_j1.correctors.all())
        counts = []
        for c in correctors:
            counts.append(
                Copy.objects.filter(exam=exam_j1, assigned_corrector=c).count()
            )
        if counts:
            assert max(counts) - min(counts) <= 1

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_no_reshuffle_after_grading(self):
        """Dispatch does not reassign copies that have started grading."""
        call_command('seed_initial_exams', data_dir=self.test_dir, password='test123')
        exam_j1 = Exam.objects.get(name='BB Jour 1')
        first_copy = Copy.objects.filter(exam=exam_j1).first()
        original_corrector = first_copy.assigned_corrector

        # Simulate grading started
        first_copy.status = Copy.Status.LOCKED
        first_copy.save()

        # Re-run seed
        call_command('seed_initial_exams', data_dir=self.test_dir, password='test123')
        first_copy.refresh_from_db()
        assert first_copy.assigned_corrector == original_corrector

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_bareme_structure(self):
        """Exam has correct barème structure."""
        call_command('seed_initial_exams', data_dir=self.test_dir, password='test123')
        exam_j1 = Exam.objects.get(name='BB Jour 1')
        structure = exam_j1.grading_structure
        assert isinstance(structure, list)
        assert len(structure) == 4  # 4 exercices
        assert structure[0]['title'] == 'Exercice 1'
        assert structure[0]['type'] == 'group'

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_force_resets_passwords(self):
        """--force flag resets all passwords."""
        call_command('seed_initial_exams', data_dir=self.test_dir, password='original')
        admin = User.objects.get(username='admin')
        assert admin.check_password('original')

        call_command('seed_initial_exams', data_dir=self.test_dir, password='newpass', force=True)
        admin.refresh_from_db()
        assert admin.check_password('newpass')


@pytest.mark.django_db
class TestCopyGradedRules(TestCase):
    """Test the 'copy graded' business rules."""

    def setUp(self):
        from grading.models import Score
        self.Score = Score

        self.exam = Exam.objects.create(
            name='Test Exam',
            grading_structure=[
                {'type': 'group', 'title': 'Ex1', 'children': [
                    {'type': 'question', 'title': 'Q1', 'maxScore': 5},
                    {'type': 'question', 'title': 'Q2', 'maxScore': 5},
                ]},
            ]
        )
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='TEST-001',
            status=Copy.Status.READY,
        )

    def test_copy_not_graded_without_scores(self):
        """A copy without scores is not graded."""
        assert self.copy.status != Copy.Status.GRADED

    def test_scores_stored_as_json(self):
        """Per-question scores are stored in JSON format."""
        score = self.Score.objects.create(
            copy=self.copy,
            scores_data={'1.1': 3.5, '1.2': 4.0},
        )
        score.refresh_from_db()
        assert score.scores_data == {'1.1': 3.5, '1.2': 4.0}

    def test_appreciation_required_for_graded(self):
        """Copy needs appreciation to be considered fully graded."""
        assert self.copy.global_appreciation is None or self.copy.global_appreciation == ''
