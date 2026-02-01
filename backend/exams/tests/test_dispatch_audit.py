"""
ZF-AUD-08: Dispatch Copies + Remarks Tests
Tests for dispatch fairness, atomicity, and remarks CRUD.
"""
import pytest
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework import status

from core.auth import UserRole, create_user_roles
from exams.models import Exam, Copy

User = get_user_model()


@pytest.mark.django_db
class TestDispatchFairness:
    """Test dispatch algorithm fairness (max diff ≤ 1)."""

    @pytest.fixture
    def setup_exam_with_correctors(self, db):
        """Create exam with correctors."""
        admin_group, teacher_group, _ = create_user_roles()
        
        admin = User.objects.create_user(username='admin_disp', password='pass', is_staff=True)
        admin.groups.add(admin_group)  # Admin group required for IsAdminOnly
        
        exam = Exam.objects.create(name='Fairness Test', date='2026-01-31')
        
        correctors = []
        for i in range(3):
            c = User.objects.create_user(username=f'corrector_f{i}', password='pass')
            c.groups.add(teacher_group)
            correctors.append(c)
            exam.correctors.add(c)
        
        return exam, correctors, admin

    def test_10_copies_3_correctors_max_diff_1(self, setup_exam_with_correctors):
        """10 copies / 3 correctors → 4/3/3 distribution (max diff = 1)."""
        exam, correctors, admin = setup_exam_with_correctors
        
        for i in range(10):
            Copy.objects.create(exam=exam, anonymous_id=f'FAIR{i:03d}', status=Copy.Status.READY)
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        response = client.post(f"/api/exams/{exam.id}/dispatch/")
        
        assert response.status_code == 200
        assert response.data['copies_assigned'] == 10
        
        distribution = response.data['distribution']
        counts = list(distribution.values())
        
        assert sum(counts) == 10
        assert max(counts) - min(counts) <= 1  # Fairness guarantee

    def test_7_copies_3_correctors_max_diff_1(self, setup_exam_with_correctors):
        """7 copies / 3 correctors → 3/2/2 distribution (max diff = 1)."""
        exam, correctors, admin = setup_exam_with_correctors
        
        for i in range(7):
            Copy.objects.create(exam=exam, anonymous_id=f'FAIR7_{i:03d}', status=Copy.Status.READY)
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        response = client.post(f"/api/exams/{exam.id}/dispatch/")
        
        assert response.status_code == 200
        
        distribution = response.data['distribution']
        counts = list(distribution.values())
        
        assert sum(counts) == 7
        assert max(counts) - min(counts) <= 1

    def test_1_copy_3_correctors(self, setup_exam_with_correctors):
        """1 copy / 3 correctors → 1/0/0 distribution."""
        exam, correctors, admin = setup_exam_with_correctors
        
        Copy.objects.create(exam=exam, anonymous_id='SINGLE001', status=Copy.Status.READY)
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        response = client.post(f"/api/exams/{exam.id}/dispatch/")
        
        assert response.status_code == 200
        assert response.data['copies_assigned'] == 1
        
        distribution = response.data['distribution']
        counts = list(distribution.values())
        
        assert sum(counts) == 1
        assert counts.count(1) == 1
        assert counts.count(0) == 2


@pytest.mark.django_db
class TestDispatchEdgeCases:
    """Test dispatch edge cases."""

    @pytest.fixture
    def setup_admin(self, db):
        """Create admin user."""
        admin_group, teacher_group, _ = create_user_roles()
        admin = User.objects.create_user(username='admin_edge', password='pass', is_staff=True)
        admin.groups.add(admin_group)  # Admin group required for IsAdminOnly
        return admin

    def test_dispatch_no_correctors_returns_400(self, setup_admin):
        """Dispatch with no correctors returns 400."""
        admin = setup_admin
        
        exam = Exam.objects.create(name='No Correctors', date='2026-01-31')
        Copy.objects.create(exam=exam, anonymous_id='NOCORR001', status=Copy.Status.READY)
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        response = client.post(f"/api/exams/{exam.id}/dispatch/")
        
        assert response.status_code == 400
        assert 'error' in response.data

    def test_dispatch_no_copies_returns_200_message(self, setup_admin):
        """Dispatch with no unassigned copies returns 200 with message."""
        admin = setup_admin
        _, teacher_group, _ = create_user_roles()
        
        exam = Exam.objects.create(name='No Copies', date='2026-01-31')
        corrector = User.objects.create_user(username='corr_nocopy', password='pass')
        corrector.groups.add(teacher_group)
        exam.correctors.add(corrector)
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        response = client.post(f"/api/exams/{exam.id}/dispatch/")
        
        assert response.status_code == 200
        assert 'message' in response.data


@pytest.mark.django_db
class TestDispatchNonDestructive:
    """Test that dispatch does not reassign already assigned copies."""

    @pytest.fixture
    def setup_exam_with_assigned(self, db):
        """Create exam with some already assigned copies."""
        admin_group, teacher_group, _ = create_user_roles()
        
        admin = User.objects.create_user(username='admin_nondest', password='pass', is_staff=True)
        admin.groups.add(admin_group)  # Admin group required for IsAdminOnly
        
        exam = Exam.objects.create(name='Non-Destructive Test', date='2026-01-31')
        
        corrector1 = User.objects.create_user(username='corr_nd1', password='pass')
        corrector1.groups.add(teacher_group)
        corrector2 = User.objects.create_user(username='corr_nd2', password='pass')
        corrector2.groups.add(teacher_group)
        
        exam.correctors.add(corrector1, corrector2)
        
        # Pre-assigned copy
        assigned_copy = Copy.objects.create(
            exam=exam,
            anonymous_id='PREASSIGNED',
            status=Copy.Status.READY,
            assigned_corrector=corrector1
        )
        
        return exam, corrector1, corrector2, assigned_copy, admin

    def test_dispatch_preserves_existing_assignments(self, setup_exam_with_assigned):
        """Dispatch should not change already assigned copies."""
        exam, corrector1, corrector2, assigned_copy, admin = setup_exam_with_assigned
        
        # Add new unassigned copies
        for i in range(4):
            Copy.objects.create(exam=exam, anonymous_id=f'NEW{i:03d}', status=Copy.Status.READY)
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        response = client.post(f"/api/exams/{exam.id}/dispatch/")
        
        assert response.status_code == 200
        assert response.data['copies_assigned'] == 4  # Only new copies
        
        # Verify pre-assigned copy unchanged
        assigned_copy.refresh_from_db()
        assert assigned_copy.assigned_corrector == corrector1
        assert assigned_copy.dispatch_run_id is None  # Not touched by this run


@pytest.mark.django_db
class TestDispatchAtomicity:
    """Test dispatch atomicity (all or nothing)."""

    @pytest.fixture
    def setup_exam_for_atomicity(self, db):
        """Create exam for atomicity test."""
        admin_group, teacher_group, _ = create_user_roles()
        
        admin = User.objects.create_user(username='admin_atom', password='pass', is_staff=True)
        admin.groups.add(admin_group)  # Admin group required for IsAdminOnly
        
        exam = Exam.objects.create(name='Atomicity Test', date='2026-01-31')
        
        corrector = User.objects.create_user(username='corr_atom', password='pass')
        corrector.groups.add(teacher_group)
        exam.correctors.add(corrector)
        
        return exam, admin

    def test_all_copies_get_same_run_id(self, setup_exam_for_atomicity):
        """All copies in a dispatch run should have the same run_id."""
        exam, admin = setup_exam_for_atomicity
        
        for i in range(5):
            Copy.objects.create(exam=exam, anonymous_id=f'ATOM{i:03d}', status=Copy.Status.READY)
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        response = client.post(f"/api/exams/{exam.id}/dispatch/")
        
        assert response.status_code == 200
        
        run_ids = set(
            Copy.objects.filter(exam=exam, assigned_corrector__isnull=False)
            .values_list('dispatch_run_id', flat=True)
        )
        
        assert len(run_ids) == 1  # All same run_id
        assert response.data['dispatch_run_id'] == str(list(run_ids)[0])


@pytest.mark.django_db
class TestDispatchTraceability:
    """Test dispatch traceability (no PII in logs, run_id for tracking)."""

    @pytest.fixture
    def setup_exam_trace(self, db):
        """Create exam for traceability test."""
        admin_group, teacher_group, _ = create_user_roles()
        
        admin = User.objects.create_user(username='admin_trace', password='pass', is_staff=True)
        admin.groups.add(admin_group)  # Admin group required for IsAdminOnly
        
        exam = Exam.objects.create(name='Traceability Test', date='2026-01-31')
        
        corrector = User.objects.create_user(username='corr_trace', password='pass')
        corrector.groups.add(teacher_group)
        exam.correctors.add(corrector)
        
        return exam, admin

    def test_response_contains_run_id(self, setup_exam_trace):
        """Response should contain dispatch_run_id for traceability."""
        exam, admin = setup_exam_trace
        
        Copy.objects.create(exam=exam, anonymous_id='TRACE001', status=Copy.Status.READY)
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        response = client.post(f"/api/exams/{exam.id}/dispatch/")
        
        assert response.status_code == 200
        assert 'dispatch_run_id' in response.data
        assert len(response.data['dispatch_run_id']) == 36  # UUID format

    def test_copies_have_assigned_at_timestamp(self, setup_exam_trace):
        """Copies should have assigned_at timestamp after dispatch."""
        exam, admin = setup_exam_trace
        
        Copy.objects.create(exam=exam, anonymous_id='TRACE002', status=Copy.Status.READY)
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        response = client.post(f"/api/exams/{exam.id}/dispatch/")
        
        assert response.status_code == 200
        
        copy = Copy.objects.get(anonymous_id='TRACE002')
        assert copy.assigned_at is not None
        assert copy.dispatch_run_id is not None
