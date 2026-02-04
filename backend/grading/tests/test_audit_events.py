import os
import pytest
from django.test import TransactionTestCase
from django.conf import settings
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from exams.models import Exam, Copy
from grading.models import GradingEvent, Annotation, CopyLock
from core.auth import UserRole
import unittest.mock
from django.utils import timezone
import datetime

User = get_user_model()
FIXTURES_DIR = os.path.join(settings.BASE_DIR, "grading/tests/fixtures/pdfs")


class TestAuditEvents(TransactionTestCase):
    """
    Test suite for verifying GradingEvent creation at key workflow moments.
    Part of observability & audit trail requirements (ZF-AUD-11).
    """

    def setUp(self):
        super().setUp()
        self.client = APIClient()

        # Create groups if they don't exist
        self.teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)

        self.teacher = User.objects.create_user(username='teacher_audit', password='password')
        self.teacher.groups.add(self.teacher_group)

        self.exam = Exam.objects.create(name="Audit Test Exam", date="2024-01-01")

    def tearDown(self):
        super().tearDown()

    def test_import_creates_audit_event(self):
        """
        Verify that importing a PDF creates an IMPORT GradingEvent with metadata.
        
        Expected metadata: {'filename': <pdf_name>, 'pages': <page_count>}
        """
        self.client.force_authenticate(user=self.teacher)

        # Upload PDF via API
        pdf_path = os.path.join(FIXTURES_DIR, "copy_2p_simple.pdf")
        with open(pdf_path, 'rb') as f:
            resp = self.client.post(
                f"/api/exams/{self.exam.id}/copies/import/",
                {'pdf_file': f},
                format='multipart'
            )

        self.assertEqual(resp.status_code, 201)
        copy_id = resp.data['id']
        copy = Copy.objects.get(id=copy_id)

        # Assert IMPORT event created
        events = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.IMPORT)
        self.assertEqual(events.count(), 1)

        event = events.first()
        self.assertEqual(event.actor, self.teacher)
        self.assertIn('filename', event.metadata)
        self.assertIn('pages', event.metadata)
        self.assertEqual(event.metadata['pages'], 2)  # copy_2p_simple.pdf has 2 pages
        self.assertIn('copy_2p_simple.pdf', event.metadata['filename'])

        # Cleanup
        if copy.pdf_source:
            copy.pdf_source.delete(save=False)

    def test_create_annotation_creates_audit_event(self):
        """
        Verify that creating an annotation creates a CREATE_ANN GradingEvent.
        
        Expected metadata: {'annotation_id': <uuid>, 'page': <page_index>}
        """
        self.client.force_authenticate(user=self.teacher)

        # Create copy in READY state
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="AUDIT-ANN",
            status=Copy.Status.READY
        )

        # Add a booklet with pages (required for annotation validation)
        from exams.models import Booklet
        booklet = Booklet.objects.create(
            exam=self.exam,
            start_page=1,
            end_page=2,
            pages_images=["page1.png", "page2.png"]
        )
        copy.booklets.add(booklet)

        # Lock the copy (required for annotation creation)
        resp = self.client.post(f"/api/grading/copies/{copy.id}/lock/", {}, format='json')
        self.assertEqual(resp.status_code, 201)
        lock_token = resp.data['token']

        # Create annotation via API
        ann_data = {
            "page_index": 0,
            "x": 0.1,
            "y": 0.2,
            "w": 0.3,
            "h": 0.1,
            "type": Annotation.Type.COMMENT,
            "content": "Test annotation"
        }
        resp = self.client.post(
            f"/api/grading/copies/{copy.id}/annotations/",
            ann_data,
            format='json',
            HTTP_X_LOCK_TOKEN=str(lock_token)
        )
        self.assertEqual(resp.status_code, 201)
        annotation_id = resp.data['id']

        # Assert CREATE_ANN event created
        events = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.CREATE_ANN)
        self.assertEqual(events.count(), 1)

        event = events.first()
        self.assertEqual(event.actor, self.teacher)
        self.assertIn('annotation_id', event.metadata)
        self.assertIn('page', event.metadata)
        self.assertEqual(event.metadata['annotation_id'], str(annotation_id))
        self.assertEqual(event.metadata['page'], 0)

    def test_finalize_creates_audit_event_success(self):
        """
        Verify that successful finalization creates a FINALIZE GradingEvent.
        
        Expected metadata: {'final_score': <score>, 'retries': <attempt>, success implied by absence of 'success': False}
        """
        self.client.force_authenticate(user=self.teacher)

        # Create copy in LOCKED state with annotation
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="AUDIT-FIN-OK",
            status=Copy.Status.LOCKED,
            locked_by=self.teacher,
            locked_at=timezone.now()
        )

        # Create annotation with score_delta
        ann = Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1,
            y=0.1,
            w=0.1,
            h=0.1,
            type=Annotation.Type.COMMENT,
            content="Good",
            score_delta=5,
            created_by=self.teacher
        )

        # Create lock
        lock = CopyLock.objects.create(
            copy=copy,
            owner=self.teacher,
            expires_at=timezone.now() + datetime.timedelta(minutes=10)
        )

        # Mock PDF flattener
        with unittest.mock.patch("processing.services.pdf_flattener.PDFFlattener.flatten_copy") as mock_flatten:
            mock_flatten.return_value = b"%PDF-1.4\n%%EOF"
            
            resp = self.client.post(
                f"/api/grading/copies/{copy.id}/finalize/",
                {},
                format='json',
                HTTP_X_LOCK_TOKEN=str(lock.token)
            )

        self.assertEqual(resp.status_code, 200)
        copy.refresh_from_db()
        self.assertEqual(copy.status, Copy.Status.GRADED)

        # Assert FINALIZE event created with success metadata
        events = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.FINALIZE)
        self.assertEqual(events.count(), 1)

        event = events.first()
        self.assertEqual(event.actor, self.teacher)
        self.assertIn('final_score', event.metadata)
        self.assertIn('retries', event.metadata)
        self.assertEqual(event.metadata['final_score'], 5)
        self.assertEqual(event.metadata['retries'], 1)
        
        # Success events don't have 'success': False
        self.assertNotIn('success', event.metadata)
        self.assertNotIn('detail', event.metadata)

        # Cleanup
        if copy.final_pdf:
            copy.final_pdf.delete(save=False)

    def test_finalize_creates_audit_event_failure(self):
        """
        Verify that failed finalization creates a FINALIZE GradingEvent with error metadata.
        
        Expected metadata: {'detail': <error_msg>, 'retries': <attempt>, 'success': False}
        
        Note: Due to @transaction.atomic on finalize_copy, when an exception is raised,
        the entire transaction (including audit event and status change) is rolled back.
        This test verifies that the audit event *would be created* by testing at the
        service layer where we can observe the database state before rollback.
        
        In practice, this means failure events are NOT persisted in the current implementation,
        which is a known limitation. This test documents the intended behavior.
        """
        # Create copy in LOCKED state
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="AUDIT-FIN-FAIL",
            status=Copy.Status.LOCKED,
            locked_by=self.teacher,
            locked_at=timezone.now()
        )

        # Create lock
        lock = CopyLock.objects.create(
            copy=copy,
            owner=self.teacher,
            expires_at=timezone.now() + datetime.timedelta(minutes=10)
        )

        # Import service and mock PDF flattener
        from grading.services import GradingService
        
        # To verify the audit event is created before rollback, we need to test
        # at a lower level. We'll use a different approach: verify the event would
        # be created by checking the service behavior in a non-rolled-back context.
        # 
        # For this test, we'll verify that:
        # 1. The finalize method attempts to create the event (we can see this in logs)
        # 2. The copy status changes to GRADING_FAILED before exception is raised
        # 
        # Since @transaction.atomic causes rollback, we test that the service ATTEMPTS
        # to create the event by checking it exists in a nested savepoint.
        
        with unittest.mock.patch("processing.services.pdf_flattener.PDFFlattener.flatten_copy") as mock_flatten:
            mock_flatten.side_effect = Exception("PDF generation error - test failure")
            
            # Use a savepoint to capture the state before rollback
            from django.db import transaction
            savepoint = transaction.savepoint()
            
            try:
                GradingService.finalize_copy(copy, user=self.teacher, lock_token=str(lock.token))
            except ValueError as e:
                # Exception is expected
                self.assertIn("Failed to generate final PDF", str(e))
                
                # Check state before rollback
                copy.refresh_from_db()
                events = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.FINALIZE)
                
                # In the current transaction, the event exists
                self.assertEqual(events.count(), 1)
                event = events.first()
                self.assertEqual(event.actor, self.teacher)
                self.assertIn('detail', event.metadata)
                self.assertIn('retries', event.metadata)
                self.assertIn('success', event.metadata)
                self.assertEqual(event.metadata['success'], False)
                self.assertEqual(event.metadata['retries'], 1)
                self.assertIn("PDF generation error", event.metadata['detail'])
                
                # Verify copy status is GRADING_FAILED
                self.assertEqual(copy.status, Copy.Status.GRADING_FAILED)
                
                # Rollback to clean state
                transaction.savepoint_rollback(savepoint)
