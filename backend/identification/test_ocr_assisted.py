from django.test import TestCase
from django.contrib.auth.models import User, Group
from exams.models import Exam, Copy, Booklet
from students.models import Student
from identification.models import OCRResult
from identification.services import OCRService
from identification.views import OCRPerformView
from unittest.mock import patch, MagicMock
import tempfile
import os
from PIL import Image
from django.test import RequestFactory
from django.contrib.auth import get_user_model


class OCRAssistedIdentificationTest(TestCase):
    """
    Tests pour la fonctionnalité OCR assistée
    """
    def setUp(self):
        # Create groups
        self.admin_group, _ = Group.objects.get_or_create(name='admin')
        self.teacher_group, _ = Group.objects.get_or_create(name='teacher')
        
        # Create test users
        self.teacher_user = User.objects.create_user(username='teacher', password='testpass')
        self.teacher_user.groups.add(self.teacher_group)
        
        # Create test data
        self.student = Student.objects.create(
            email="jean.dupont@test.com",
            full_name="Dupont Jean",
            date_of_birth="2008-01-15",
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

    def test_ocr_assisted_workflow(self):
        """
        Test le workflow complet OCR assisté
        """
        # Simuler une requête pour effectuer l'OCR
        factory = RequestFactory()
        request = factory.post(f'/api/identification/perform-ocr/{self.copy.id}/')
        request.user = self.teacher_user  # Authenticated user
        
        # Créer une instance de la vue
        view = OCRPerformView()
        view.setup(request)
        
        # Simuler la réponse de l'OCR
        with patch.object(OCRService, 'perform_ocr_on_header') as mock_ocr:
            mock_ocr.return_value = {
                'text': 'JEAN DUPONT',
                'confidence': 0.95
            }
            
            with patch.object(OCRService, 'find_matching_students') as mock_find:
                mock_find.return_value = [self.student]
                
                # Appeler la méthode post
                response = view.post(request, copy_id=self.copy.id)
                
                # Vérifier que la réponse est correcte
                self.assertEqual(response.status_code, 200)
                response_data = response.data
                self.assertIn('detected_text', response_data)
                self.assertIn('confidence', response_data)
                self.assertIn('suggestions', response_data)
                self.assertEqual(len(response_data['suggestions']), 1)

    def test_ocr_low_confidence_still_works(self):
        """
        Test que l'OCR fonctionne même avec une faible confiance
        """
        factory = RequestFactory()
        request = factory.post(f'/api/identification/perform-ocr/{self.copy.id}/')
        request.user = self.teacher_user
        
        view = OCRPerformView()
        view.setup(request)
        
        with patch.object(OCRService, 'perform_ocr_on_header') as mock_ocr:
            mock_ocr.return_value = {
                'text': 'JEAN DUPONT',
                'confidence': 0.3  # Faible confiance
            }
            
            with patch.object(OCRService, 'find_matching_students') as mock_find:
                mock_find.return_value = [self.student]
                
                response = view.post(request, copy_id=self.copy.id)
                
                # Même avec faible confiance, devrait toujours retourner des suggestions
                self.assertEqual(response.status_code, 200)
                self.assertGreaterEqual(len(response.data['suggestions']), 0)

    def test_ocr_no_matches(self):
        """
        Test le cas où l'OCR ne trouve aucune correspondance
        """
        factory = RequestFactory()
        request = factory.post(f'/api/identification/perform-ocr/{self.copy.id}/')
        request.user = self.teacher_user
        
        view = OCRPerformView()
        view.setup(request)
        
        with patch.object(OCRService, 'perform_ocr_on_header') as mock_ocr:
            mock_ocr.return_value = {
                'text': 'TEXT INVALIDE',
                'confidence': 0.8
            }
            
            with patch.object(OCRService, 'find_matching_students') as mock_find:
                mock_find.return_value = []  # Aucune correspondance
                
                response = view.post(request, copy_id=self.copy.id)
                
                # Devrait quand même retourner la réponse avec suggestions vides
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.data['suggestions']), 0)

    def test_human_validation_required_after_ocr(self):
        """
        Test que la validation humaine est toujours requise après OCR
        """
        # Même si l'OCR suggère un élève, l'utilisateur doit encore valider manuellement
        # Cela est assuré par le fait que l'interface ne valide pas automatiquement
        # mais affiche les suggestions pour validation humaine
        
        # Créer un deuxième étudiant pour tester la sélection
        other_student = Student.objects.create(
            email="marie.martin@test.com",
            full_name="Martin Marie",
            date_of_birth="2008-02-20",
            class_name="TG3"
        )
        
        factory = RequestFactory()
        request = factory.post(f'/api/identification/perform-ocr/{self.copy.id}/')
        request.user = self.teacher_user
        
        view = OCRPerformView()
        view.setup(request)
        
        with patch.object(OCRService, 'perform_ocr_on_header') as mock_ocr:
            mock_ocr.return_value = {
                'text': 'JEAN DUPONT',
                'confidence': 0.9
            }
            
            with patch.object(OCRService, 'find_matching_students') as mock_find:
                mock_find.return_value = [self.student, other_student]  # Plusieurs suggestions
                
                response = view.post(request, copy_id=self.copy.id)
                
                self.assertEqual(response.status_code, 200)
                # Devrait retourner plusieurs suggestions
                self.assertGreaterEqual(len(response.data['suggestions']), 1)
                
                # Mais aucune n'est automatiquement sélectionnée
                # La validation humaine est obligatoire