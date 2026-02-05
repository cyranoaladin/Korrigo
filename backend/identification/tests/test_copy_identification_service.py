"""
Tests pour CopyIdentificationService - Protection anti-doublons.

PRD-19: Vérifie que:
- Un seul Copy identifié par (exam, student)
- Fusion automatique si doublon détecté
- Race-condition safe
"""
import pytest
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid

from exams.models import Exam, Booklet, Copy
from students.models import Student
from grading.models import GradingEvent
from identification.services import CopyIdentificationService

User = get_user_model()


class CopyIdentificationServiceTest(TestCase):
    """Tests unitaires pour CopyIdentificationService."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123'
        )
        self.exam = Exam.objects.create(
            name='Test Exam',
            date='2026-02-04'
        )
        self.student = Student.objects.create(
            full_name='DUPONT Jean',
            date_of_birth='2005-01-15'
        )

    def _create_copy_with_booklet(self, status=Copy.Status.READY):
        """Helper pour créer une copie avec un booklet."""
        booklet = Booklet.objects.create(
            exam=self.exam,
            start_page=1,
            end_page=4,
            pages_images=['page1.png', 'page2.png', 'page3.png', 'page4.png']
        )
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id=f'ANON-{uuid.uuid4().hex[:8].upper()}',
            status=status
        )
        copy.booklets.add(booklet)
        return copy, booklet

    def test_identify_copy_simple(self):
        """Test identification simple sans doublon."""
        copy, _ = self._create_copy_with_booklet()
        
        result = CopyIdentificationService.identify_copy(
            copy_id=str(copy.id),
            student_id=str(self.student.id),
            user=self.user,
            method='manual'
        )
        
        self.assertFalse(result['merged'])
        self.assertEqual(result['student_name'], 'DUPONT Jean')
        
        copy.refresh_from_db()
        self.assertTrue(copy.is_identified)
        self.assertEqual(copy.student, self.student)

    def test_identify_copy_merge_on_duplicate(self):
        """Test fusion automatique si doublon détecté."""
        # Créer une première copie identifiée
        copy1, booklet1 = self._create_copy_with_booklet()
        copy1.student = self.student
        copy1.is_identified = True
        copy1.save()
        
        # Créer une seconde copie non identifiée
        copy2, booklet2 = self._create_copy_with_booklet()
        
        # Identifier la seconde copie avec le même élève
        result = CopyIdentificationService.identify_copy(
            copy_id=str(copy2.id),
            student_id=str(self.student.id),
            user=self.user,
            method='manual'
        )
        
        # Vérifier la fusion
        self.assertTrue(result['merged'])
        self.assertEqual(result['copy_id'], str(copy1.id))
        
        # Vérifier que copy2 a été supprimée
        self.assertFalse(Copy.objects.filter(id=copy2.id).exists())
        
        # Vérifier que copy1 a les deux booklets
        copy1.refresh_from_db()
        self.assertEqual(copy1.booklets.count(), 2)
        self.assertIn(booklet1, copy1.booklets.all())
        self.assertIn(booklet2, copy1.booklets.all())

    def test_identify_copy_rejects_staging(self):
        """Test que les copies STAGING sont rejetées."""
        copy, _ = self._create_copy_with_booklet(status=Copy.Status.STAGING)
        
        with self.assertRaises(ValueError) as ctx:
            CopyIdentificationService.identify_copy(
                copy_id=str(copy.id),
                student_id=str(self.student.id),
                user=self.user
            )
        
        self.assertIn('STAGING', str(ctx.exception))

    def test_identify_copy_rejects_graded(self):
        """Test que les copies GRADED sont rejetées."""
        copy, _ = self._create_copy_with_booklet(status=Copy.Status.GRADED)
        
        with self.assertRaises(ValueError) as ctx:
            CopyIdentificationService.identify_copy(
                copy_id=str(copy.id),
                student_id=str(self.student.id),
                user=self.user
            )
        
        self.assertIn('GRADED', str(ctx.exception))

    def test_identify_copy_invalid_student(self):
        """Test avec un élève inexistant."""
        copy, _ = self._create_copy_with_booklet()
        
        with self.assertRaises(ValueError) as ctx:
            CopyIdentificationService.identify_copy(
                copy_id=str(copy.id),
                student_id='999999',  # ID entier inexistant
                user=self.user
            )
        
        self.assertIn('non trouvé', str(ctx.exception))

    def test_check_for_duplicates(self):
        """Test détection des doublons."""
        # Créer deux copies identifiées pour le même élève
        copy1, _ = self._create_copy_with_booklet()
        copy1.student = self.student
        copy1.is_identified = True
        copy1.save()
        
        copy2, _ = self._create_copy_with_booklet()
        copy2.student = self.student
        copy2.is_identified = True
        copy2.save()
        
        duplicates = CopyIdentificationService.check_for_duplicates(str(self.exam.id))
        
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]['student_name'], 'DUPONT Jean')
        self.assertEqual(duplicates[0]['copy_count'], 2)

    def test_fix_duplicates(self):
        """Test correction automatique des doublons."""
        # Créer deux copies identifiées pour le même élève
        copy1, booklet1 = self._create_copy_with_booklet()
        copy1.student = self.student
        copy1.is_identified = True
        copy1.save()
        
        copy2, booklet2 = self._create_copy_with_booklet()
        copy2.student = self.student
        copy2.is_identified = True
        copy2.save()
        
        result = CopyIdentificationService.fix_duplicates(str(self.exam.id), self.user)
        
        self.assertEqual(result['duplicates_found'], 1)
        self.assertEqual(result['merges_done'], 1)
        
        # Vérifier qu'il ne reste qu'une copie
        remaining_copies = Copy.objects.filter(
            exam=self.exam,
            student=self.student,
            is_identified=True
        )
        self.assertEqual(remaining_copies.count(), 1)
        
        # Vérifier que la copie restante a les deux booklets
        remaining = remaining_copies.first()
        self.assertEqual(remaining.booklets.count(), 2)

    def test_audit_trail_on_identification(self):
        """Test que l'audit trail est créé."""
        copy, _ = self._create_copy_with_booklet()
        
        CopyIdentificationService.identify_copy(
            copy_id=str(copy.id),
            student_id=str(self.student.id),
            user=self.user,
            method='manual'
        )
        
        events = GradingEvent.objects.filter(copy=copy)
        self.assertEqual(events.count(), 1)
        
        event = events.first()
        self.assertEqual(event.action, GradingEvent.Action.VALIDATE)
        self.assertEqual(event.metadata['method'], 'manual')
        self.assertFalse(event.metadata['merged'])

    def test_audit_trail_on_merge(self):
        """Test que l'audit trail capture la fusion."""
        # Créer une première copie identifiée
        copy1, _ = self._create_copy_with_booklet()
        copy1.student = self.student
        copy1.is_identified = True
        copy1.save()
        
        # Créer une seconde copie
        copy2, _ = self._create_copy_with_booklet()
        copy2_anon = copy2.anonymous_id
        
        CopyIdentificationService.identify_copy(
            copy_id=str(copy2.id),
            student_id=str(self.student.id),
            user=self.user,
            method='manual'
        )
        
        # Vérifier l'événement de fusion sur copy1
        events = GradingEvent.objects.filter(copy=copy1)
        merge_event = events.filter(metadata__merged=True).first()
        
        self.assertIsNotNone(merge_event)
        self.assertEqual(merge_event.metadata['merged_from_anonymous_id'], copy2_anon)


class CopyIdentificationConcurrencyTest(TransactionTestCase):
    """Tests de concurrence pour CopyIdentificationService."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123'
        )
        self.exam = Exam.objects.create(
            name='Test Exam',
            date='2026-02-04'
        )
        self.student = Student.objects.create(
            full_name='DUPONT Jean',
            date_of_birth='2005-01-15'
        )

    def _create_copy_with_booklet(self):
        """Helper pour créer une copie avec un booklet."""
        booklet = Booklet.objects.create(
            exam=self.exam,
            start_page=1,
            end_page=4,
            pages_images=['page1.png', 'page2.png', 'page3.png', 'page4.png']
        )
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id=f'ANON-{uuid.uuid4().hex[:8].upper()}',
            status=Copy.Status.READY
        )
        copy.booklets.add(booklet)
        return copy

    def test_concurrent_identification_same_student(self):
        """
        Test que deux identifications concurrentes pour le même élève
        ne créent pas de doublon.
        
        Note: Ce test vérifie la logique de fusion, pas la vraie concurrence
        car SQLite ne supporte pas bien select_for_update en mode test.
        """
        copy1 = self._create_copy_with_booklet()
        copy2 = self._create_copy_with_booklet()
        
        # Identifier séquentiellement pour tester la fusion
        result1 = CopyIdentificationService.identify_copy(
            copy_id=str(copy1.id),
            student_id=str(self.student.id),
            user=self.user,
            method='concurrent_test'
        )
        
        result2 = CopyIdentificationService.identify_copy(
            copy_id=str(copy2.id),
            student_id=str(self.student.id),
            user=self.user,
            method='concurrent_test'
        )
        
        # La seconde identification devrait déclencher une fusion
        self.assertTrue(result2['merged'])
        
        # Vérifier qu'il n'y a qu'une seule copie identifiée
        identified_copies = Copy.objects.filter(
            exam=self.exam,
            student=self.student,
            is_identified=True
        )
        
        self.assertEqual(identified_copies.count(), 1)
        
        # Vérifier que la copie a les deux booklets
        final_copy = identified_copies.first()
        self.assertEqual(final_copy.booklets.count(), 2)
