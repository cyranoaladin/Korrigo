from django.test import TestCase
from django.contrib.auth.models import User, Group
from exams.models import Exam, Copy, Booklet
from students.models import Student
from identification.models import OCRResult
from identification.services import OCRService
from unittest.mock import patch, MagicMock
import tempfile
import os
from PIL import Image


class OCRServiceTest(TestCase):
    def setUp(self):
        # Create test user and groups
        self.admin_group = Group.objects.create(name='admin')
        self.teacher_group = Group.objects.create(name='teacher')
        
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.user.groups.add(self.teacher_group)
        
        # Create test student
        self.student = Student.objects.create(
            date_naissance="2005-03-15",
            first_name="Jean",
            last_name="Dupont",
            class_name="TG2"
        )
        
        # Create test exam and copy
        self.exam = Exam.objects.create(
            name="Bac Blanc Maths",
            date="2026-01-25"
        )
        
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="ABC123",
            status=Copy.Status.STAGING
        )

    def test_perform_ocr_on_header_with_mock(self):
        # Create a mock image for testing
        image = Image.new('RGB', (100, 50), color='white')
        temp_image = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        image.save(temp_image.name)
        
        # Mock the pytesseract functionality
        with patch('identification.services.pytesseract.image_to_string') as mock_ocr:
            mock_ocr.return_value = "JEAN DUPONT"
            
            with patch('identification.services.pytesseract.image_to_data') as mock_data:
                mock_data.return_value = {'conf': [90, 85, 95]}
                
                with open(temp_image.name, 'rb') as img_file:
                    result = OCRService.perform_ocr_on_header(img_file)
                    
                    self.assertEqual(result['text'], "JEAN DUPONT")
                    self.assertGreaterEqual(result['confidence'], 0.0)
        
        # Clean up
        os.unlink(temp_image.name)

    def test_find_matching_students(self):
        # Test the student matching functionality
        ocr_text = "JEAN DUPONT"
        suggestions = OCRService.find_matching_students(ocr_text)
        
        # Should find our test student
        self.assertIn(self.student, suggestions)

    def test_perform_ocr_on_header_error_handling(self):
        # Test error handling in OCR service
        with patch('identification.services.Image.open') as mock_open:
            mock_open.side_effect = Exception("Invalid image")
            
            # Create a dummy file-like object
            dummy_file = tempfile.NamedTemporaryFile()
            
            result = OCRService.perform_ocr_on_header(dummy_file)
            
            # Should return error information
            self.assertIn('error', result)
            self.assertEqual(result['text'], '')
            self.assertEqual(result['confidence'], 0.0)


class OCRViewsTest(TestCase):
    def setUp(self):
        # Create test data
        self.student = Student.objects.create(
            ine="1234567890A",
            first_name="Jean",
            last_name="Dupont",
            class_name="TG2"
        )

        self.exam = Exam.objects.create(
            name="Bac Blanc Maths",
            date="2026-01-25"
        )

        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="ABC123",
            status=Copy.Status.STAGING
        )

        # Create a booklet for the copy
        self.booklet = Booklet.objects.create(
            exam=self.exam,
            start_page=1,
            end_page=4,
            student_name_guess="Jean Dupont"
        )
        self.copy.booklets.add(self.booklet)

    def test_identification_desk_view(self):
        # Test the identification desk view
        response = self.client.get('/api/identification/desk/')
        
        # Should return 403 because authentication is required
        self.assertEqual(response.status_code, 403)

    def test_manual_identify_view(self):
        # Test the manual identify view
        url = f'/api/identification/identify/{self.copy.id}/'
        response = self.client.post(url, {'student_id': self.student.id}, content_type='application/json')

        # Should return 403 because authentication is required
        self.assertEqual(response.status_code, 403)

    def test_ocr_identify_view(self):
        # Test the OCR identify view
        url = f'/api/identification/ocr-identify/{self.copy.id}/'
        response = self.client.post(url, {'student_id': self.student.id}, content_type='application/json')

        # Should return 403 because authentication is required
        self.assertEqual(response.status_code, 403)

    def test_ocr_perform_view(self):
        # Test the OCR perform view
        url = f'/api/identification/perform-ocr/{self.copy.id}/'
        response = self.client.post(url, content_type='application/json')

        # Should return 403 because authentication is required
        self.assertEqual(response.status_code, 403)


class OCRModelTest(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            ine="1234567890A",
            first_name="Jean",
            last_name="Dupont",
            class_name="TG2"
        )
        
        self.exam = Exam.objects.create(
            name="Bac Blanc Maths",
            date="2026-01-25"
        )
        
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="ABC123",
            status=Copy.Status.STAGING
        )

    def test_ocr_result_creation(self):
        # Test creating an OCR result
        ocr_result = OCRResult.objects.create(
            copy=self.copy,
            detected_text="JEAN DUPONT",
            confidence=0.95
        )
        
        ocr_result.suggested_students.add(self.student)
        
        self.assertEqual(ocr_result.detected_text, "JEAN DUPONT")
        self.assertEqual(ocr_result.confidence, 0.95)
        self.assertEqual(ocr_result.suggested_students.count(), 1)
        self.assertEqual(ocr_result.suggested_students.first(), self.student)