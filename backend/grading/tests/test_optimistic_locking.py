"""
Tests for optimistic locking on annotations
P0-DI-008: Concurrent edit protection tests
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from core.auth import UserRole
from exams.models import Exam, Copy
from grading.models import Annotation
from grading.services import AnnotationService, GradingService

User = get_user_model()


class OptimisticLockingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testcorrector',
            email='corrector@test.com',
            password='testpass123'
        )
        teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        self.user.groups.add(teacher_group)
        self.exam = Exam.objects.create(
            name='Lock Test Exam',
            date='2024-01-01'
        )
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='LOCK-001',
            status=Copy.Status.READY,
            assigned_corrector=self.user,
        )

    def test_annotation_has_version_field(self):
        """Annotation model has version field defaulting to 0"""
        annotation = Annotation.objects.create(
            copy=self.copy,
            created_by=self.user,
            type=Annotation.Type.COMMENT,
            content='Test comment',
            x=0.1,
            y=0.2,
            w=0.1,
            h=0.1,
            page_index=0
        )
        
        self.assertEqual(annotation.version, 0)

    def test_update_increments_version(self):
        """Updating annotation increments version atomically"""
        annotation = Annotation.objects.create(
            copy=self.copy,
            created_by=self.user,
            type=Annotation.Type.COMMENT,
            content='Original',
            x=0.1,
            y=0.2,
            w=0.1,
            h=0.1,
            page_index=0
        )
        initial_version = annotation.version
        
        updated = AnnotationService.update_annotation(
            annotation_id=annotation.id,
            user=self.user,
            payload={'content': 'Updated', 'version': initial_version},
        )
        
        self.assertEqual(updated.version, initial_version + 1)
        self.assertEqual(updated.content, 'Updated')

    def test_version_mismatch_raises_error(self):
        """Concurrent edit with stale version raises ValueError"""
        annotation = Annotation.objects.create(
            copy=self.copy,
            created_by=self.user,
            type=Annotation.Type.COMMENT,
            content='Original',
            x=0.1,
            y=0.2,
            w=0.1,
            h=0.1,
            page_index=0
        )
        
        # First update succeeds
        AnnotationService.update_annotation(
            annotation_id=annotation.id,
            user=self.user,
            payload={'content': 'First update', 'version': 0},
        )
        
        # Second update with stale version fails
        with self.assertRaises(ValueError) as cm:
            AnnotationService.update_annotation(
                annotation_id=annotation.id,
                user=self.user,
                payload={'content': 'Stale update', 'version': 0},
            )
        
        self.assertIn('Version mismatch', str(cm.exception))
        self.assertIn('concurrent edit', str(cm.exception).lower())

    def test_update_without_version_check_works(self):
        """Update without version in payload skips check (backward compatible)"""
        annotation = Annotation.objects.create(
            copy=self.copy,
            created_by=self.user,
            type=Annotation.Type.COMMENT,
            content='Original',
            x=0.1,
            y=0.2,
            w=0.1,
            h=0.1,
            page_index=0
        )
        
        # Update without version field works (backward compatible)
        updated = AnnotationService.update_annotation(
            annotation_id=annotation.id,
            user=self.user,
            payload={'content': 'Updated without version'},
        )
        
        self.assertEqual(updated.content, 'Updated without version')
        self.assertEqual(updated.version, 1)

    def test_concurrent_updates_prevented(self):
        """Simulates concurrent edit scenario"""
        annotation = Annotation.objects.create(
            copy=self.copy,
            created_by=self.user,
            type=Annotation.Type.COMMENT,
            content='Original',
            x=0.1,
            y=0.2,
            w=0.1,
            h=0.1,
            page_index=0
        )
        
        # User A fetches annotation (version=0)
        version_a = annotation.version
        
        # User B updates (version=0 -> 1)
        AnnotationService.update_annotation(
            annotation_id=annotation.id,
            user=self.user,
            payload={'content': 'User B update', 'version': 0},
        )
        
        # User A tries to update with stale version
        with self.assertRaises(ValueError):
            AnnotationService.update_annotation(
                annotation_id=annotation.id,
                user=self.user,
                payload={'content': 'User A update', 'version': version_a},
            )
        
        # Verify User B's update persisted
        annotation.refresh_from_db()
        self.assertEqual(annotation.content, 'User B update')
        self.assertEqual(annotation.version, 1)
