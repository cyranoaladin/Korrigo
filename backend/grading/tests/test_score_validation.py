"""
Tests for score validation in QuestionScoreListCreateView.

Validates:
- score >= 0
- question_id exists in grading_structure
- score <= max points from barème
"""
import fitz
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status as http_status
from django.contrib.auth.models import User
from exams.models import Exam, Copy
from grading.models import QuestionScore


def make_pdf(pages=4):
    doc = fitz.open()
    for i in range(pages):
        doc.new_page(width=595, height=842)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@override_settings(RATELIMIT_ENABLE=False)
class TestScoreValidation(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser('admin', 'admin@t.fr', 'admin')
        self.client.force_login(self.admin)

        self.exam = Exam.objects.create(
            name='Score Test',
            date='2026-01-01',
            grading_structure=[
                {'id': 'ex1', 'label': 'Exercice 1', 'points': 5, 'children': [
                    {'id': 'ex1a', 'label': '1a', 'points': 2},
                    {'id': 'ex1b', 'label': '1b', 'points': 3},
                ]},
                {'id': 'ex2', 'label': 'Exercice 2', 'points': 10},
            ]
        )
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='TEST0001',
            status=Copy.Status.LOCKED,
        )
        self.url = reverse('question-score-list-create', kwargs={'copy_id': self.copy.id})

    def test_valid_score_accepted(self):
        """A valid score within barème limits is accepted."""
        response = self.client.post(self.url, {
            'question_id': 'ex1a',
            'score': 1.5,
        })
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        self.assertEqual(QuestionScore.objects.count(), 1)

    def test_score_at_max_accepted(self):
        """Score exactly at max is accepted."""
        response = self.client.post(self.url, {
            'question_id': 'ex2',
            'score': 10,
        })
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)

    def test_score_exceeds_max_rejected(self):
        """Score above barème max is rejected."""
        response = self.client.post(self.url, {
            'question_id': 'ex1a',
            'score': 5,  # max is 2
        })
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('exceeds', str(response.data['detail']))
        self.assertEqual(QuestionScore.objects.count(), 0)

    def test_negative_score_rejected(self):
        """Negative scores are rejected."""
        response = self.client.post(self.url, {
            'question_id': 'ex1a',
            'score': -1,
        })
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertEqual(QuestionScore.objects.count(), 0)

    def test_phantom_question_rejected(self):
        """Score for non-existent question_id is rejected."""
        response = self.client.post(self.url, {
            'question_id': 'PHANTOM_Q',
            'score': 5,
        })
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('not found', str(response.data['detail']))

    def test_missing_question_id_rejected(self):
        response = self.client.post(self.url, {'score': 5})
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_missing_score_rejected(self):
        response = self.client.post(self.url, {'question_id': 'ex1a'})
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_non_numeric_score_rejected(self):
        response = self.client.post(self.url, {
            'question_id': 'ex1a',
            'score': 'abc',
        })
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_update_existing_score(self):
        """Updating an existing score works via update_or_create."""
        self.client.post(self.url, {'question_id': 'ex1a', 'score': 1})
        response = self.client.post(self.url, {'question_id': 'ex1a', 'score': 2})
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(QuestionScore.objects.count(), 1)
        self.assertEqual(float(QuestionScore.objects.first().score), 2.0)

    def test_no_bareme_accepts_any_valid_score(self):
        """If exam has no grading_structure, any positive score is accepted."""
        exam2 = Exam.objects.create(name='No Bareme', date='2026-01-01')
        copy2 = Copy.objects.create(exam=exam2, anonymous_id='TEST0002', status=Copy.Status.LOCKED)
        url2 = reverse('question-score-list-create', kwargs={'copy_id': copy2.id})

        response = self.client.post(url2, {
            'question_id': 'any_q',
            'score': 999,
        })
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)


@override_settings(RATELIMIT_ENABLE=False)
class TestAppreciationImmutability(TestCase):
    """Test that global appreciation cannot be modified on GRADED copies."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser('admin', 'admin@t.fr', 'admin')
        self.client.force_login(self.admin)

        self.exam = Exam.objects.create(name='Immutable Test', date='2026-01-01')
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='TEST0003',
            status=Copy.Status.GRADED,
        )
        self.url = reverse('copy-global-appreciation', kwargs={'copy_id': self.copy.id})

    def test_graded_copy_appreciation_rejected(self):
        response = self.client.put(self.url, {
            'global_appreciation': 'Modified after grading'
        }, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_locked_copy_appreciation_accepted(self):
        self.copy.status = Copy.Status.LOCKED
        self.copy.save()
        response = self.client.put(self.url, {
            'global_appreciation': 'Good work!'
        }, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
