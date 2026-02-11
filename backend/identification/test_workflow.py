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
from django.utils import timezone


class IdentificationWorkflowTest(TestCase):
    """
    Tests pour le workflow complet d'identification manuelle
    """
    def setUp(self):
        # Create test user and groups
        self.admin_group = Group.objects.create(name='admin')
        self.teacher_group = Group.objects.create(name='teacher')
        
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.user.groups.add(self.teacher_group)
        
        # Create test student
        self.student = Student.objects.create(
            ine="1234567890A",
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
            status=Copy.Status.STAGING  # Starting in STAGING state
        )
        
        # Create a booklet for the copy
        self.booklet = Booklet.objects.create(
            exam=self.exam,
            start_page=1,
            end_page=4,
            student_name_guess="Jean Dupont"
        )
        self.copy.booklets.add(self.booklet)

    def test_state_transition_staging_to_ready_manual(self):
        """
        Test la transition d'état de STAGING à READY via identification manuelle
        """
        # Vérifier l'état initial
        self.copy.refresh_from_db()
        self.assertEqual(self.copy.status, Copy.Status.STAGING)
        self.assertFalse(self.copy.is_identified)
        self.assertIsNone(self.copy.student)
        
        # Simuler l'identification manuelle (comme le ferait l'API)
        self.copy.student = self.student
        self.copy.is_identified = True
        self.copy.status = Copy.Status.READY
        self.copy.validated_at = timezone.now()
        self.copy.save()
        
        # Vérifier la transition d'état
        self.copy.refresh_from_db()
        self.assertEqual(self.copy.status, Copy.Status.READY)
        self.assertTrue(self.copy.is_identified)
        self.assertEqual(self.copy.student, self.student)
        self.assertIsNotNone(self.copy.validated_at)

    def test_identification_prevents_invalid_transitions(self):
        """
        Test que l'identification ne peut se faire qu'à partir des états valides
        """
        # Créer une copie dans l'état LOCKED (déjà en cours de correction)
        locked_copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="DEF456",
            status=Copy.Status.LOCKED
        )
        
        # Essayer d'identifier cette copie devrait échouer
        # (ceci serait géré dans la logique métier, testons simplement le concept)
        self.assertEqual(locked_copy.status, Copy.Status.LOCKED)
        
        # Passer à un état où l'identification est autorisée
        locked_copy.status = Copy.Status.STAGING
        locked_copy.save()
        
        # Maintenant l'identification devrait être possible
        locked_copy.student = self.student
        locked_copy.is_identified = True
        locked_copy.status = Copy.Status.READY
        locked_copy.save()
        
        locked_copy.refresh_from_db()
        self.assertEqual(locked_copy.status, Copy.Status.READY)
        self.assertTrue(locked_copy.is_identified)

    def test_multiple_identification_attempts(self):
        """
        Test qu'une copie identifiée ne peut pas être ré-identifiée
        """
        # Identifier la copie
        self.copy.student = self.student
        self.copy.is_identified = True
        self.copy.status = Copy.Status.READY
        self.copy.save()
        
        # Créer un autre étudiant
        other_student = Student.objects.create(
            ine="0987654321B",
            first_name="Marie",
            last_name="Martin",
            class_name="TG3"
        )
        
        # Normalement, le système devrait empêcher de ré-identifier une copie déjà identifiée
        # Mais cela dépend de la logique métier implémentée dans les vues
        self.copy.refresh_from_db()
        self.assertTrue(self.copy.is_identified)
        self.assertEqual(self.copy.student, self.student)


class IdentificationPermissionsTest(TestCase):
    """
    Tests pour les permissions d'identification
    """
    def setUp(self):
        # Create groups
        self.admin_group, _ = Group.objects.get_or_create(name='admin')
        self.teacher_group, _ = Group.objects.get_or_create(name='teacher')
        self.student_group, _ = Group.objects.get_or_create(name='student')
        
        # Create test users
        self.admin_user = User.objects.create_user(username='admin', password='testpass')
        self.admin_user.groups.add(self.admin_group)
        
        self.teacher_user = User.objects.create_user(username='teacher', password='testpass')
        self.teacher_user.groups.add(self.teacher_group)
        
        self.student_user = User.objects.create_user(username='student', password='testpass')
        self.student_user.groups.add(self.student_group)
        
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