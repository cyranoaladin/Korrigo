from django.test import TransactionTestCase
from rest_framework import status
from django.core.files.base import ContentFile
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from exams.models import Exam, Copy
from grading.models import GradingEvent
from rest_framework.test import APIClient
from core.auth import UserRole
import io
import os

User = get_user_model()

# TransactionTestCase required because tests involve I/O, streaming, and multiple
# transactions that fail with regular TestCase in a Docker environment.
class TestPhase39Hardening(TransactionTestCase):

    def setUp(self):
        super().setUp()
        self.client = APIClient()

        # Create groups if they don't exist
        self.teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        self.admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)

        self.teacher_user = User.objects.create_user(username='teacher', password='password123')
        self.teacher_user.groups.add(self.teacher_group)  # Add to teacher group instead of is_staff

        self.student_user = User.objects.create_user(username='student_user', password='password123')
        # Student user has no special group permissions - should be denied access
        self.exam = Exam.objects.create(name="Test Exam", date="2024-06-01", is_processed=False)
        
    def tearDown(self):
        super().tearDown()

    def test_import_permissions_forbidden_for_non_staff(self):
        self.client.force_login(self.student_user)
        url = f"/api/exams/{self.exam.id}/copies/import/"

        pdf_file = io.BytesIO(b"%PDF-1.4 empty pdf")
        pdf_file.name = "test.pdf"

        response = self.client.post(url, {'pdf_file': pdf_file}, format='multipart')
        pdf_file.close()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_import_success_for_teacher_creates_copy_booklet_and_audit(self):
        self.client.force_login(self.teacher_user)
        url = f"/api/exams/{self.exam.id}/copies/import/"

        # Mocking simpler via monkeypatching not easy in TestCase methods without pytest fixture injection
        # So we use unittest.mock
        from unittest.mock import patch

        def fake_rasterize(copy):
            return [f"copies/pages/{copy.id}/p000.png", f"copies/pages/{copy.id}/p001.png"]

        with patch('grading.services.GradingService._rasterize_pdf', side_effect=fake_rasterize):
            pdf_file = io.BytesIO(b"%PDF-1.4 Fake Content")
            pdf_file.name = "real.pdf"

            response = self.client.post(url, {'pdf_file': pdf_file}, format='multipart')
            pdf_file.close()

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['status'], 'STAGING')

            copy = Copy.objects.get(id=response.data['id'])
            self.assertEqual(copy.exam, self.exam)
            self.assertEqual(copy.booklets.count(), 1)

            # Check Audit
            event = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.IMPORT).first()
            self.assertIsNotNone(event)
            # Note: Using self.teacher_user instead of self.teacher_user as actor might not match due to force_login
            # The event.actor should be the logged in user
            self.assertEqual(str(event.actor.id), str(self.teacher_user.id))

            # Cleanup
            copy.delete()

    def test_audit_endpoint_requires_staff(self):
        copy = Copy.objects.create(exam=self.exam, anonymous_id="AUDIT-TEST", status=Copy.Status.READY)
        url = f"/api/grading/copies/{copy.id}/audit/"

        # Student -> 403
        self.client.force_login(self.student_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Teacher -> 200
        self.client.force_login(self.teacher_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_final_pdf_security_gate(self):
        copy = Copy.objects.create(exam=self.exam, anonymous_id="SECURE-PDF", status=Copy.Status.READY)
        content = ContentFile(b"PDF CONTENT")
        copy.final_pdf.save("final.pdf", content)
        copy.save()
        
        try:
            url = f"/api/grading/copies/{copy.id}/final-pdf/"
            self.client.force_authenticate(user=self.teacher_user)
            
            # READY with PDF -> 403 (status gate blocks even for staff)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            
            # GRADED -> 200
            copy.status = Copy.Status.GRADED
            copy.save()
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response['Content-Type'], 'application/pdf')
            self.assertTrue(getattr(response, "streaming", False))
            if hasattr(response, 'close'): response.close()
        finally:
            if copy.final_pdf:
                copy.final_pdf.delete(save=False)
            copy.delete()
