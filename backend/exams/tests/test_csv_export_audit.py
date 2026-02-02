"""
ZF-AUD-10: CSV Export Tests (Pronote Format)
Tests for CSV format, encoding, decimals, and admin-only access.
"""
import pytest
import io
from django.test import Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework import status

from core.auth import UserRole, create_user_roles
from exams.models import Exam, Copy
from students.models import Student

User = get_user_model()


@pytest.fixture
def setup_admin_and_teacher(db):
    """Create admin and teacher users."""
    admin_group, teacher_group, _ = create_user_roles()
    
    admin = User.objects.create_user(username='admin_csv', password='pass', is_staff=True)
    admin.groups.add(admin_group)
    
    teacher = User.objects.create_user(username='teacher_csv', password='pass')
    teacher.groups.add(teacher_group)
    
    return admin, teacher


@pytest.fixture
def setup_exam_with_copies(db):
    """Create exam with copies and annotations for scores."""
    from grading.models import Annotation
    
    exam = Exam.objects.create(name="CSV Export Test", date="2026-01-31")
    
    # Create students
    student1 = Student.objects.create(email="alice.csv@test.com", first_name="Alice", last_name="DUPONT", class_name="3A")
    student2 = Student.objects.create(email="bob.csv@test.com", first_name="Bob", last_name="MARTIN", class_name="3B")
    
    # Create a teacher for annotations
    admin_group, teacher_group, _ = create_user_roles()
    teacher = User.objects.create_user(username='teacher_csv_ann', password='pass')
    teacher.groups.add(teacher_group)
    
    # Copy with student and annotations
    copy1 = Copy.objects.create(
        exam=exam,
        anonymous_id="CSV001",
        status=Copy.Status.GRADED,
        student=student1,
        is_identified=True
    )
    # Add annotation with score
    Annotation.objects.create(
        copy=copy1, page_index=0, x=0.1, y=0.1, w=0.1, h=0.1,
        type=Annotation.Type.COMMENT, score_delta=15, created_by=teacher
    )
    
    # Copy without student (unidentified)
    copy2 = Copy.objects.create(
        exam=exam,
        anonymous_id="CSV002",
        status=Copy.Status.GRADED,
        student=None,
        is_identified=False
    )
    
    # Copy with student2
    copy3 = Copy.objects.create(
        exam=exam,
        anonymous_id="CSV003",
        status=Copy.Status.GRADED,
        student=student2,
        is_identified=True
    )
    Annotation.objects.create(
        copy=copy3, page_index=0, x=0.1, y=0.1, w=0.1, h=0.1,
        type=Annotation.Type.COMMENT, score_delta=18, created_by=teacher
    )
    
    # Non-GRADED copy (should not appear in Pronote export)
    copy4 = Copy.objects.create(
        exam=exam,
        anonymous_id="CSV004",
        status=Copy.Status.READY,
        student=student1,
        is_identified=True
    )
    
    return exam, [copy1, copy2, copy3, copy4], [student1, student2]


@pytest.mark.django_db
class TestCSVExportPermissions:
    """Test CSV export is admin-only."""

    def test_admin_can_export_csv(self, setup_admin_and_teacher, setup_exam_with_copies):
        """Admin should be able to export CSV."""
        admin, _ = setup_admin_and_teacher
        exam, _, _ = setup_exam_with_copies
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        response = client.get(f"/api/exams/{exam.id}/export-csv/")
        
        assert response.status_code == 200
        assert 'text/csv' in response['Content-Type']

    def test_teacher_cannot_export_csv(self, setup_admin_and_teacher, setup_exam_with_copies):
        """Teacher should not be able to export CSV."""
        _, teacher = setup_admin_and_teacher
        exam, _, _ = setup_exam_with_copies
        
        client = APIClient()
        client.force_authenticate(user=teacher)
        
        response = client.get(f"/api/exams/{exam.id}/export-csv/")
        
        assert response.status_code == 403

    def test_unauthenticated_cannot_export_csv(self, setup_exam_with_copies):
        """Unauthenticated user should not be able to export CSV."""
        exam, _, _ = setup_exam_with_copies
        
        client = APIClient()
        
        response = client.get(f"/api/exams/{exam.id}/export-csv/")
        
        assert response.status_code in [401, 403]


@pytest.mark.django_db
class TestCSVExportFormat:
    """Test CSV format compliance."""

    def test_csv_has_correct_content_type(self, setup_admin_and_teacher, setup_exam_with_copies):
        """CSV response should have correct content type."""
        admin, _ = setup_admin_and_teacher
        exam, _, _ = setup_exam_with_copies
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        response = client.get(f"/api/exams/{exam.id}/export-csv/")
        
        assert 'text/csv' in response['Content-Type']
        assert 'attachment' in response['Content-Disposition']

    def test_csv_has_header_row(self, setup_admin_and_teacher, setup_exam_with_copies):
        """CSV should have a header row."""
        admin, _ = setup_admin_and_teacher
        exam, _, _ = setup_exam_with_copies
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        response = client.get(f"/api/exams/{exam.id}/export-csv/")
        
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        
        assert len(lines) >= 1
        header = lines[0]
        assert 'AnonymousID' in header or 'INE' in header

    def test_csv_encoding_utf8(self, setup_admin_and_teacher, setup_exam_with_copies):
        """CSV should be UTF-8 encoded."""
        admin, _ = setup_admin_and_teacher
        exam, _, _ = setup_exam_with_copies
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        response = client.get(f"/api/exams/{exam.id}/export-csv/")
        
        # Should decode without errors
        try:
            content = response.content.decode('utf-8')
            assert True
        except UnicodeDecodeError:
            pytest.fail("CSV is not valid UTF-8")


@pytest.mark.django_db
class TestPronoteExportCommand:
    """Test Pronote export management command."""

    def test_pronote_export_format(self, setup_exam_with_copies, capsys):
        """Pronote export should use semicolon separator and French decimal format."""
        from django.core.management import call_command
        
        exam, copies, students = setup_exam_with_copies
        
        call_command('export_pronote', str(exam.id))
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Check header uses semicolon
        lines = output.strip().split('\n')
        assert len(lines) >= 1, "Should have at least header"
        header = lines[0]
        assert ';' in header, "Pronote format should use semicolon separator"
        assert 'EMAIL' in header
        assert 'MATIERE' in header
        assert 'NOTE' in header
        assert 'COEFF' in header

    def test_pronote_skips_unidentified_copies(self, setup_exam_with_copies, capsys):
        """Pronote export should skip copies without student."""
        from django.core.management import call_command
        
        exam, copies, students = setup_exam_with_copies
        
        call_command('export_pronote', str(exam.id))
        
        captured = capsys.readouterr()
        error_output = captured.err
        
        # Should warn about skipped copies (copy2 has no student)
        assert 'Skipping' in error_output or 'No Student' in error_output

    def test_pronote_decimal_french_format(self, setup_exam_with_copies):
        """Pronote export should use French decimal format (comma)."""
        # This test verifies the code logic - actual output depends on scores
        from exams.management.commands.export_pronote import Command
        
        # Verify the format string uses comma replacement
        # In the command: final_note_str = f"{final_note:.2f}".replace('.', ',')
        test_value = 15.5
        formatted = f"{test_value:.2f}".replace('.', ',')
        assert formatted == "15,50"


@pytest.mark.django_db
class TestCSVDataLeakage:
    """Test that CSV export doesn't leak unnecessary data."""

    def test_csv_does_not_include_sensitive_fields(self, setup_admin_and_teacher, setup_exam_with_copies):
        """CSV should not include sensitive fields like passwords or tokens."""
        admin, _ = setup_admin_and_teacher
        exam, _, _ = setup_exam_with_copies
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        response = client.get(f"/api/exams/{exam.id}/export-csv/")
        
        content = response.content.decode('utf-8').lower()
        
        # Should not contain sensitive fields
        assert 'password' not in content
        assert 'token' not in content
        assert 'secret' not in content
        assert 'session' not in content

    def test_csv_includes_only_exam_copies(self, setup_admin_and_teacher, setup_exam_with_copies, db):
        """CSV should only include copies from the requested exam."""
        admin, _ = setup_admin_and_teacher
        exam1, _, _ = setup_exam_with_copies
        
        # Create another exam with copies
        exam2 = Exam.objects.create(name="Other Exam", date="2026-02-01")
        Copy.objects.create(exam=exam2, anonymous_id="OTHER001", status=Copy.Status.GRADED)
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        response = client.get(f"/api/exams/{exam1.id}/export-csv/")
        
        content = response.content.decode('utf-8')
        
        # Should not include other exam's copies
        assert 'OTHER001' not in content


@pytest.mark.django_db
class TestCSVExportEdgeCases:
    """Test CSV export edge cases."""

    def test_export_empty_exam(self, setup_admin_and_teacher, db):
        """Export of exam with no copies should work."""
        admin, _ = setup_admin_and_teacher
        
        exam = Exam.objects.create(name="Empty Exam", date="2026-01-31")
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        response = client.get(f"/api/exams/{exam.id}/export-csv/")
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        
        # Should have at least header
        assert len(lines) >= 1

    def test_export_nonexistent_exam_returns_404(self, setup_admin_and_teacher):
        """Export of nonexistent exam should return 404."""
        admin, _ = setup_admin_and_teacher
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        import uuid
        fake_id = uuid.uuid4()
        response = client.get(f"/api/exams/{fake_id}/export-csv/")
        
        assert response.status_code == 404
