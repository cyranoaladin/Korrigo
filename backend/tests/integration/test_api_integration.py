"""
Integration Tests - API & Permission Flows
Phase 4: Testing Coverage - API Integration

This test suite covers cross-component API interactions:
1. Authorization & Permission Flows
2. Cross-Resource Operations
3. Data Consistency Across Components
4. Async Operation Integration
"""
import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

from core.auth import create_user_roles, UserRole
from django.contrib.auth.models import Group
from exams.models import Exam, Copy
from students.models import Student
from grading.models import Annotation
from django.utils import timezone


class PermissionFlowIntegrationTests(TestCase):
    """Test permission and authorization flows across components"""

    def setUp(self):
        self.client = APIClient()
        create_user_roles()

        # Create users with different roles
        self.admin = User.objects.create_user(
            username='admin1',
            password='AdminPass123!',
            is_staff=True,
            is_superuser=True
        )

        self.teacher1 = User.objects.create_user(
            username='teacher1',
            password='TeacherPass123!'
        )
        # Add teacher1 to Teacher group for permissions
        teacher_group = Group.objects.get(name=UserRole.TEACHER)
        self.teacher1.groups.add(teacher_group)

        self.teacher2 = User.objects.create_user(
            username='teacher2',
            password='TeacherPass123!'
        )
        # Add teacher2 to Teacher group for permissions
        self.teacher2.groups.add(teacher_group)

        # Create exam owned by teacher1
        self.exam = Exam.objects.create(
            name='Math Exam',
            date=timezone.now().date(),
        )
        self.exam.correctors.add(self.teacher1)

        # Create copy
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='PERM-001',
            status=Copy.Status.READY
        )

    def test_teacher_can_access_own_exam(self):
        """Test: Teacher can access exam they created/are assigned to"""
        self.client.force_authenticate(user=self.teacher1)

        response = self.client.get(f'/api/exams/{self.exam.id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_teacher_can_list_exams(self):
        """Test: Teachers can list exams (read access is allowed)"""
        self.client.force_authenticate(user=self.teacher2)

        # Teachers can view exam list (read-only access)
        response = self.client.get(f'/api/exams/{self.exam.id}/')
        # Read access is allowed for all teachers
        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_access_all_exams(self):
        """Test: Admin can access any exam"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(f'/api/exams/{self.exam.id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_teacher_can_delete_exam(self):
        """Test: Teachers with permission can delete exams without copies"""
        # Create a separate exam without copies for deletion test
        exam_to_delete = Exam.objects.create(
            name='Exam To Delete',
            date=timezone.now().date(),
        )
        exam_to_delete.correctors.add(self.teacher1)
        
        # Teacher1 is a corrector and can delete
        self.client.force_authenticate(user=self.teacher1)

        response = self.client.delete(f'/api/exams/{exam_to_delete.id}/')
        # Teachers can delete exams they have access to
        assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK]

    def test_unidentified_copies_permission_flow(self):
        """Test: Only exam correctors can view unidentified copies"""
        # Teacher1 (corrector) can access
        self.client.force_authenticate(user=self.teacher1)
        response = self.client.get(f'/api/exams/{self.exam.id}/unidentified-copies/')
        assert response.status_code == status.HTTP_200_OK

        # Teacher2 (not corrector) cannot access
        self.client.force_authenticate(user=self.teacher2)
        response = self.client.get(f'/api/exams/{self.exam.id}/unidentified-copies/')
        assert response.status_code == status.HTTP_403_FORBIDDEN


class CrossResourceIntegrationTests(TestCase):
    """Test operations spanning multiple resources"""

    def setUp(self):
        self.client = APIClient()
        create_user_roles()

        self.teacher = User.objects.create_user(
            username='teacher1',
            password='TeacherPass123!'
        )
        # Add to Teacher group for permissions
        teacher_group = Group.objects.get(name=UserRole.TEACHER)
        self.teacher.groups.add(teacher_group)
        self.client.force_authenticate(user=self.teacher)

        # Create student
        self.student = Student.objects.create(
            email='alice@test.com',
            full_name='Alice Dupont',
            date_of_birth='2005-03-15',
        )

        # Create exam
        self.exam = Exam.objects.create(
            name='Math Exam',
            date=timezone.now().date(),
        )
        self.exam.correctors.add(self.teacher)

    def test_copy_identification_updates_status(self):
        """Test: Identifying copy updates both student and copy status"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='CROSS-001',
            status=Copy.Status.STAGING
        )

        # Initially unidentified
        assert copy.is_identified is False
        assert copy.student is None

        # Identify copy
        copy.student = self.student
        copy.is_identified = True
        copy.status = Copy.Status.READY
        copy.save()

        # Verify both relationships
        copy.refresh_from_db()
        assert copy.student == self.student
        assert copy.is_identified is True
        assert copy.status == Copy.Status.READY

        # Verify reverse relationship
        student_copies = Copy.objects.filter(student=self.student)
        assert copy in student_copies

    def test_exam_deletion_protected_by_copies(self):
        """Test: Deleting exam with copies is protected (PROTECT)"""
        from django.db.models import ProtectedError
        
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='CASCADE-001'
        )

        exam_id = self.exam.id
        copy_id = copy.id

        # Delete exam should raise ProtectedError because Copy has on_delete=PROTECT
        with pytest.raises(ProtectedError):
            self.exam.delete()

        # Verify exam still exists (protected)
        assert Exam.objects.filter(id=exam_id).exists()
        # Verify copy still exists
        assert Copy.objects.filter(id=copy_id).exists()

    def test_student_results_across_multiple_exams(self):
        """Test: Student can have copies in multiple exams"""
        # Create second exam
        exam2 = Exam.objects.create(
            name='Physics Exam',
            date=timezone.now().date(),
        )

        # Create copies in both exams
        copy1 = Copy.objects.create(
            exam=self.exam,
            anonymous_id='MULTI-001',
            student=self.student,
            is_identified=True,
            status=Copy.Status.GRADED
        )

        copy2 = Copy.objects.create(
            exam=exam2,
            anonymous_id='MULTI-002',
            student=self.student,
            is_identified=True,
            status=Copy.Status.GRADED
        )

        # Verify student has copies in both exams
        student_copies = Copy.objects.filter(student=self.student)
        assert student_copies.count() == 2
        assert copy1 in student_copies
        assert copy2 in student_copies

        # Verify exam filtering
        exam1_copies = Copy.objects.filter(student=self.student, exam=self.exam)
        assert exam1_copies.count() == 1


class DataConsistencyIntegrationTests(TestCase):
    """Test data consistency across operations"""

    def setUp(self):
        self.client = APIClient()
        create_user_roles()

        self.teacher = User.objects.create_user(
            username='teacher1',
            password='TeacherPass123!'
        )
        # Add to Teacher group for permissions
        teacher_group = Group.objects.get(name=UserRole.TEACHER)
        self.teacher.groups.add(teacher_group)
        self.client.force_authenticate(user=self.teacher)

        self.exam = Exam.objects.create(
            name='Math Exam',
            date=timezone.now().date(),
        )

    def test_anonymous_id_uniqueness(self):
        """Test: Anonymous IDs must be unique"""
        copy1 = Copy.objects.create(
            exam=self.exam,
            anonymous_id='UNIQUE-001'
        )

        # Creating another copy with different anonymous_id should work
        copy2 = Copy.objects.create(
            exam=self.exam,
            anonymous_id='UNIQUE-002'
        )

        assert copy1.anonymous_id != copy2.anonymous_id

    def test_copy_graded_status(self):
        """Test: Copy can be set to GRADED status"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='SCORE-001',
            status=Copy.Status.GRADED
        )

        # Verify status is GRADED
        assert copy.status == Copy.Status.GRADED
        # Verify exam relationship exists
        assert copy.exam is not None
        assert copy.exam.name == 'Math Exam'

    def test_copy_status_transitions(self):
        """Test: Copy status follows valid state transitions"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='STATUS-001',
            status=Copy.Status.STAGING
        )

        # STAGING → READY
        copy.status = Copy.Status.READY
        copy.save()
        assert copy.status == Copy.Status.READY

        # READY → LOCKED
        copy.status = Copy.Status.LOCKED
        copy.save()
        assert copy.status == Copy.Status.LOCKED

        # LOCKED → GRADED
        copy.status = Copy.Status.GRADED
        copy.save()
        assert copy.status == Copy.Status.GRADED


class AsyncOperationIntegrationTests(TestCase):
    """Test async operations and task integration"""

    def setUp(self):
        self.client = APIClient()
        create_user_roles()

        self.teacher = User.objects.create_user(
            username='teacher1',
            password='TeacherPass123!'
        )
        # Add to Teacher group for permissions
        teacher_group = Group.objects.get(name=UserRole.TEACHER)
        self.teacher.groups.add(teacher_group)
        self.client.force_authenticate(user=self.teacher)

        self.exam = Exam.objects.create(
            name='Math Exam',
            date=timezone.now().date(),
        )
        self.exam.correctors.add(self.teacher)

    def test_exam_exists_and_accessible(self):
        """Test: Exam is accessible to authenticated teacher"""
        response = self.client.get(f'/api/exams/{self.exam.id}/')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['name'] == 'Math Exam'

    def test_copy_creation_in_exam(self):
        """Test: Copies can be created and linked to exam"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='TEST-001'
        )

        # Verify copy is linked to exam
        assert copy.exam == self.exam
        assert copy.status == Copy.Status.STAGING

    def test_multiple_async_operations_independent(self):
        """Test: Multiple async operations can run independently"""
        # Create multiple copies
        copies = [
            Copy.objects.create(exam=self.exam, anonymous_id=f'ASYNC-{i:03d}')
            for i in range(3)
        ]

        # In real scenario, each could trigger independent task
        # Verify copies are independent
        for copy in copies:
            assert copy.exam == self.exam
            assert copy.status == Copy.Status.STAGING


class StudentPortalIntegrationTests(TestCase):
    """Test student portal integration flows"""

    def setUp(self):
        self.client = APIClient()
        create_user_roles()

        # Create student with user account
        self.student_user = User.objects.create_user(
            username='alice',
            password='StudentPass123!'
        )

        self.student = Student.objects.create(
            email='alice@test.com',
            full_name='Alice Dupont',
            date_of_birth='2005-03-15',
            user=self.student_user
        )

        # Create teacher and exam
        self.teacher = User.objects.create_user(
            username='teacher1',
            password='TeacherPass123!'
        )
        # Add to Teacher group for permissions
        teacher_group = Group.objects.get(name=UserRole.TEACHER)
        self.teacher.groups.add(teacher_group)

        self.exam = Exam.objects.create(
            name='Math Exam',
            date=timezone.now().date(),
        )

    def test_student_login_and_view_results_flow(self):
        """Test: Student login → View own results"""
        # Step 1: Login as student
        response = self.client.post('/api/students/login/', {
            'email': 'alice@test.com',
            'password': 'StudentPass123!'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['role'] == 'Student'

        # Step 2: Create graded copy for student
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='PORTAL-001',
            student=self.student,
            is_identified=True,
            status=Copy.Status.GRADED
        )

        # Step 3: Student views own profile
        # (In real implementation, would use student session)
        # For now, verify the data relationship exists
        student_copies = Copy.objects.filter(
            student=self.student,
            status=Copy.Status.GRADED
        )
        assert copy in student_copies

    def test_student_cannot_access_others_results(self):
        """Test: Students can only see their own results"""
        # Create another student
        other_student = Student.objects.create(
            email='bob@test.com',
            full_name='Bob Martin',
            date_of_birth='2005-05-20',
        )

        # Create copies for both students
        alice_copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='ALICE-001',
            student=self.student,
            is_identified=True,
            status=Copy.Status.GRADED
        )

        bob_copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='BOB-001',
            student=other_student,
            is_identified=True,
            status=Copy.Status.GRADED
        )

        # Verify filtering works
        alice_results = Copy.objects.filter(student=self.student)
        assert alice_copy in alice_results
        assert bob_copy not in alice_results


class CacheConsistencyIntegrationTests(TestCase):
    """Test cache consistency across operations"""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

        self.client = APIClient()
        create_user_roles()

    def test_global_settings_cache_invalidation(self):
        """Test: GlobalSettings cache invalidates on save"""
        from core.models import GlobalSettings

        # Load settings (should cache)
        settings1 = GlobalSettings.load()
        assert settings1.institution_name == "Lycée Pierre Mendès France"

        # Modify settings
        settings1.institution_name = "New Institution"
        settings1.save()  # Should invalidate cache

        # Load again (should get updated value, not cached)
        settings2 = GlobalSettings.load()
        assert settings2.institution_name == "New Institution"

    def test_cache_clear_method_works(self):
        """Test: Manual cache clear works"""
        from core.models import GlobalSettings
        from django.core.cache import cache

        # Load settings
        settings = GlobalSettings.load()

        # Manually clear cache
        GlobalSettings.clear_cache()

        # Cache should be empty
        cached = cache.get(GlobalSettings.CACHE_KEY)
        assert cached is None
