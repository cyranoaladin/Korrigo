"""
Tests for optimistic locking on annotations
P0-DI-008: Concurrent edit protection tests
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from exams.models import Exam, Copy
from grading.models import Annotation
from grading.services import AnnotationService

User = get_user_model()


class OptimisticLockingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testcorrector',
            email='corrector@test.com',
            password='testpass123',
            role=User.Role.TEACHER
        )
        self.exam = Exam.objects.create(
            title='Lock Test Exam',
            created_by=self.user
        )
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='LOCK-001',
            status=Copy.Status.LOCKED,
            locked_by=self.user
        )

    def test_annotation_has_version_field(self):
        """Annotation model has version field defaulting to 0"""
        annotation = Annotation.objects.create(
            copy=self.copy,
            created_by=self.user,
            annotation_type=Annotation.Type.COMMENT,
            content='Test comment',
            x=100.0,
            y=200.0,
            page_number=1
        )
        
        self.assertEqual(annotation.version, 0)

    def test_update_increments_version(self):
        """Updating annotation increments version atomically"""
        annotation = Annotation.objects.create(
            copy=self.copy,
            created_by=self.user,
            annotation_type=Annotation.Type.COMMENT,
            content='Original',
            x=100.0,
            y=200.0,
            page_number=1
        )
        initial_version = annotation.version
        
        updated = AnnotationService.update_annotation(
            annotation_id=annotation.id,
            user=self.user,
            payload={'content': 'Updated', 'version': initial_version},
            lock_token=None
        )
        
        self.assertEqual(updated.version, initial_version + 1)
        self.assertEqual(updated.content, 'Updated')

    def test_version_mismatch_raises_error(self):
        """Concurrent edit with stale version raises ValueError"""
        annotation = Annotation.objects.create(
            copy=self.copy,
            created_by=self.user,
            annotation_type=Annotation.Type.COMMENT,
            content='Original',
            x=100.0,
            y=200.0,
            page_number=1
        )
        
        # First update succeeds
        AnnotationService.update_annotation(
            annotation_id=annotation.id,
            user=self.user,
            payload={'content': 'First update', 'version': 0},
            lock_token=None
        )
        
        # Second update with stale version fails
        with self.assertRaises(ValueError) as cm:
            AnnotationService.update_annotation(
                annotation_id=annotation.id,
                user=self.user,
                payload={'content': 'Stale update', 'version': 0},  # Stale version
                lock_token=None
            )
        
        self.assertIn('Version mismatch', str(cm.exception))
        self.assertIn('concurrent edit', str(cm.exception).lower())

    def test_update_without_version_check_works(self):
        """Update without version in payload skips check (backward compatible)"""
        annotation = Annotation.objects.create(
            copy=self.copy,
            created_by=self.user,
            annotation_type=Annotation.Type.COMMENT,
            content='Original',
            x=100.0,
            y=200.0,
            page_number=1
        )
        
        # Update without version field works (backward compatible)
        updated = AnnotationService.update_annotation(
            annotation_id=annotation.id,
            user=self.user,
            payload={'content': 'Updated without version'},
            lock_token=None
        )
        
        self.assertEqual(updated.content, 'Updated without version')
        self.assertEqual(updated.version, 1)  # Still incremented

    def test_concurrent_updates_prevented(self):
        """Simulates concurrent edit scenario"""
        annotation = Annotation.objects.create(
            copy=self.copy,
            created_by=self.user,
            annotation_type=Annotation.Type.COMMENT,
            content='Original',
            x=100.0,
            y=200.0,
            page_number=1
        )
        
        # User A fetches annotation (version=0)
        version_a = annotation.version
        
        # User B updates (version=0 -> 1)
        AnnotationService.update_annotation(
            annotation_id=annotation.id,
            user=self.user,
            payload={'content': 'User B update', 'version': 0},
            lock_token=None
        )
        
        # User A tries to update with stale version
        with self.assertRaises(ValueError):
            AnnotationService.update_annotation(
                annotation_id=annotation.id,
                user=self.user,
                payload={'content': 'User A update', 'version': version_a},
                lock_token=None
            )
        
        # Verify User B's update persisted
        annotation.refresh_from_db()
        self.assertEqual(annotation.content, 'User B update')
        self.assertEqual(annotation.version, 1)
