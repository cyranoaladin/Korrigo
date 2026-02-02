"""
ZF-AUD-09: Student Portal Security Tests
Tests for student auth, copies access, and PDF download security.
"""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.base import ContentFile

from core.auth import UserRole, create_user_roles
from students.models import Student
from exams.models import Exam, Copy, Booklet

User = get_user_model()


@pytest.fixture
def setup_students(db):
    """Create students for testing."""
    student1 = Student.objects.create(
        email="alice@test.com",
        first_name="Alice",
        last_name="DUPONT",
        class_name="3A"
    )
    student2 = Student.objects.create(
        email="bob@test.com",
        first_name="Bob",
        last_name="MARTIN",
        class_name="3B"
    )
    return student1, student2


@pytest.fixture
def setup_copies_with_students(db, setup_students):
    """Create copies with different statuses and student assignments."""
    student1, student2 = setup_students
    
    exam = Exam.objects.create(name="Student Portal Test", date="2026-01-31")
    
    # Student1's GRADED copy
    copy1_graded = Copy.objects.create(
        exam=exam,
        anonymous_id="STU1-GRADED",
        status=Copy.Status.GRADED,
        student=student1
    )
    copy1_graded.final_pdf.save("test.pdf", ContentFile(b"%PDF-1.4\ntest content"))
    
    # Student1's READY copy (should not be visible)
    copy1_ready = Copy.objects.create(
        exam=exam,
        anonymous_id="STU1-READY",
        status=Copy.Status.READY,
        student=student1
    )
    
    # Student2's GRADED copy
    copy2_graded = Copy.objects.create(
        exam=exam,
        anonymous_id="STU2-GRADED",
        status=Copy.Status.GRADED,
        student=student2
    )
    copy2_graded.final_pdf.save("test2.pdf", ContentFile(b"%PDF-1.4\ntest content 2"))
    
    # Unassigned GRADED copy
    copy_unassigned = Copy.objects.create(
        exam=exam,
        anonymous_id="UNASSIGNED",
        status=Copy.Status.GRADED,
        student=None
    )
    
    return {
        'student1': student1,
        'student2': student2,
        'copy1_graded': copy1_graded,
        'copy1_ready': copy1_ready,
        'copy2_graded': copy2_graded,
        'copy_unassigned': copy_unassigned
    }


@pytest.mark.django_db
class TestStudentLogin:
    """Test student authentication (email + last_name)."""

    def test_login_success_with_valid_credentials(self, setup_students):
        """Valid email + last_name should login successfully."""
        student1, _ = setup_students
        
        client = Client()
        response = client.post('/api/students/login/', {
            'email': 'alice@test.com',
            'last_name': 'DUPONT'
        })
        
        assert response.status_code == 200
        assert 'message' in response.json()
        assert client.session.get('student_id') == student1.id

    def test_login_case_insensitive(self, setup_students):
        """Login should be case insensitive."""
        student1, _ = setup_students
        
        client = Client()
        response = client.post('/api/students/login/', {
            'email': 'ALICE@TEST.COM',  # uppercase
            'last_name': 'dupont'  # lowercase
        })
        
        assert response.status_code == 200

    def test_login_fails_with_wrong_email(self, setup_students):
        """Wrong email should return 401."""
        client = Client()
        response = client.post('/api/students/login/', {
            'email': 'wrong@test.com',
            'last_name': 'DUPONT'
        })
        
        assert response.status_code == 401

    def test_login_fails_with_wrong_name(self, setup_students):
        """Wrong last_name should return 401."""
        client = Client()
        response = client.post('/api/students/login/', {
            'email': 'alice@test.com',
            'last_name': 'WRONGNAME'
        })
        
        assert response.status_code == 401

    def test_login_fails_with_missing_fields(self):
        """Missing fields should return 400."""
        client = Client()
        
        # Missing last_name
        response = client.post('/api/students/login/', {'email': 'alice@test.com'})
        assert response.status_code == 400
        
        # Missing email
        response = client.post('/api/students/login/', {'last_name': 'DUPONT'})
        assert response.status_code == 400

    def test_error_message_does_not_reveal_existence(self, setup_students):
        """Error message should not reveal if email exists."""
        client = Client()
        
        # Wrong email
        response1 = client.post('/api/students/login/', {
            'email': 'nonexistent@test.com',
            'last_name': 'DUPONT'
        })
        
        # Wrong name for existing email
        response2 = client.post('/api/students/login/', {
            'email': 'alice@test.com',
            'last_name': 'WRONGNAME'
        })
        
        # Both should have same generic error
        assert response1.status_code == response2.status_code == 401
        # Error messages should be identical (no enumeration)
        assert response1.json().get('error') == response2.json().get('error')


@pytest.mark.django_db
class TestStudentCopiesAccess:
    """Test student can only see their own GRADED copies."""

    def test_student_sees_only_own_graded_copies(self, setup_copies_with_students):
        """Student should only see their own GRADED copies."""
        data = setup_copies_with_students
        
        client = Client()
        # Login as student1
        client.post('/api/students/login/', {
            'email': 'alice@test.com',
            'last_name': 'DUPONT'
        })
        
        response = client.get('/api/exams/student/copies/')
        
        assert response.status_code == 200
        copies = response.json()
        
        # Should only see student1's GRADED copy
        assert len(copies) == 1
        assert str(copies[0]['id']) == str(data['copy1_graded'].id)

    def test_student_does_not_see_ready_copies(self, setup_copies_with_students):
        """Student should not see READY/LOCKED copies."""
        data = setup_copies_with_students
        
        client = Client()
        client.post('/api/students/login/', {
            'email': 'alice@test.com',
            'last_name': 'DUPONT'
        })
        
        response = client.get('/api/exams/student/copies/')
        copies = response.json()
        
        # Should not include READY copy
        copy_ids = [str(c['id']) for c in copies]
        assert str(data['copy1_ready'].id) not in copy_ids

    def test_student_does_not_see_other_students_copies(self, setup_copies_with_students):
        """Student should not see other students' copies."""
        data = setup_copies_with_students
        
        client = Client()
        client.post('/api/students/login/', {
            'email': 'alice@test.com',
            'last_name': 'DUPONT'
        })
        
        response = client.get('/api/exams/student/copies/')
        copies = response.json()
        
        # Should not include student2's copy
        copy_ids = [str(c['id']) for c in copies]
        assert str(data['copy2_graded'].id) not in copy_ids

    def test_unauthenticated_cannot_access_copies(self, setup_copies_with_students):
        """Unauthenticated user should get 401/403."""
        client = Client()
        
        response = client.get('/api/exams/student/copies/')
        
        assert response.status_code in [401, 403]


@pytest.mark.django_db
class TestPDFDownloadSecurity:
    """Test PDF download security (owner check, GRADED check)."""

    def test_student_can_download_own_graded_pdf(self, setup_copies_with_students):
        """Student can download their own GRADED copy PDF."""
        data = setup_copies_with_students
        
        client = Client()
        client.post('/api/students/login/', {
            'email': 'alice@test.com',
            'last_name': 'DUPONT'
        })
        
        response = client.get(f"/api/grading/copies/{data['copy1_graded'].id}/final-pdf/")
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'

    def test_student_cannot_download_other_students_pdf(self, setup_copies_with_students):
        """Student cannot download another student's PDF."""
        data = setup_copies_with_students
        
        client = Client()
        client.post('/api/students/login/', {
            'email': 'alice@test.com',
            'last_name': 'DUPONT'
        })
        
        # Try to download student2's copy
        response = client.get(f"/api/grading/copies/{data['copy2_graded'].id}/final-pdf/")
        
        assert response.status_code == 403

    def test_student_cannot_download_non_graded_pdf(self, setup_copies_with_students):
        """Student cannot download PDF for non-GRADED copy."""
        data = setup_copies_with_students
        
        client = Client()
        client.post('/api/students/login/', {
            'email': 'alice@test.com',
            'last_name': 'DUPONT'
        })
        
        # Try to download READY copy
        response = client.get(f"/api/grading/copies/{data['copy1_ready'].id}/final-pdf/")
        
        assert response.status_code == 403

    def test_unauthenticated_cannot_download_pdf(self, setup_copies_with_students):
        """Unauthenticated user cannot download PDF."""
        data = setup_copies_with_students
        
        client = Client()
        
        response = client.get(f"/api/grading/copies/{data['copy1_graded'].id}/final-pdf/")
        
        assert response.status_code == 401

    def test_pdf_response_has_security_headers(self, setup_copies_with_students):
        """PDF response should have security headers."""
        data = setup_copies_with_students
        
        client = Client()
        client.post('/api/students/login/', {
            'email': 'alice@test.com',
            'last_name': 'DUPONT'
        })
        
        response = client.get(f"/api/grading/copies/{data['copy1_graded'].id}/final-pdf/")
        
        assert response.status_code == 200
        assert response.get('Cache-Control') == 'no-store, private'
        assert response.get('X-Content-Type-Options') == 'nosniff'


@pytest.mark.django_db
class TestTeacherAccessToStudentCopies:
    """Test that teachers can access all copies."""

    def test_teacher_can_download_any_graded_pdf(self, setup_copies_with_students):
        """Teacher can download any GRADED copy PDF."""
        data = setup_copies_with_students
        
        admin_group, teacher_group, _ = create_user_roles()
        teacher = User.objects.create_user(username='teacher_pdf', password='pass')
        teacher.groups.add(teacher_group)
        
        client = APIClient()
        client.force_authenticate(user=teacher)
        
        # Download student1's copy
        response = client.get(f"/api/grading/copies/{data['copy1_graded'].id}/final-pdf/")
        assert response.status_code == 200
        
        # Download student2's copy
        response = client.get(f"/api/grading/copies/{data['copy2_graded'].id}/final-pdf/")
        assert response.status_code == 200

    def test_teacher_cannot_download_non_graded_pdf(self, setup_copies_with_students):
        """Even teachers cannot download non-GRADED PDF."""
        data = setup_copies_with_students
        
        admin_group, teacher_group, _ = create_user_roles()
        teacher = User.objects.create_user(username='teacher_nograded', password='pass')
        teacher.groups.add(teacher_group)
        
        client = APIClient()
        client.force_authenticate(user=teacher)
        
        response = client.get(f"/api/grading/copies/{data['copy1_ready'].id}/final-pdf/")
        
        assert response.status_code == 403


@pytest.mark.django_db
class TestStudentLogout:
    """Test student logout functionality."""

    def test_logout_clears_session(self, setup_students):
        """Logout should clear student session."""
        student1, _ = setup_students
        
        client = Client()
        client.post('/api/students/login/', {
            'email': 'alice@test.com',
            'last_name': 'DUPONT'
        })
        
        # Verify logged in
        assert client.session.get('student_id') == student1.id
        
        # Logout
        response = client.post('/api/students/logout/')
        assert response.status_code == 200
        
        # Verify session cleared
        assert client.session.get('student_id') is None

    def test_cannot_access_copies_after_logout(self, setup_copies_with_students):
        """Cannot access copies after logout."""
        data = setup_copies_with_students
        
        client = Client()
        client.post('/api/students/login/', {
            'email': 'alice@test.com',
            'last_name': 'DUPONT'
        })
        
        # Logout
        client.post('/api/students/logout/')
        
        # Try to access copies
        response = client.get('/api/exams/student/copies/')
        
        assert response.status_code in [401, 403]
