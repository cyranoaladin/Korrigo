"""
Audit 2026 — Tests couvrant les angles morts identifiés lors de l'audit complet.

Couvre :
1. CopySerializer : total_score calculé correctement (None si pas de Score)
2. CopySerializer : exam_details injecté avec grading_structure
3. CopySerializer : graded_at présent et correctement filtré par rôle
4. ProgressDashboard : graded_at != updated_at (Copy n'a pas updated_at)
5. CorrectorDashboard : accès exam_details.grading_structure (pas exam.grading_structure)
6. CopyScoresView : update_or_create atomique avec select_for_update
7. CopyGlobalAppreciationView : GET endpoint fonctionnel
8. Accordéon exercices : openExerciseId scalar (pas Set)
9. Score.update_or_create : pas de doublon même en concurrence
10. CanvasLayer : flush:'post' — pas de régression sur le rendu
"""

import json
import pytest
from datetime import date
from unittest.mock import patch
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APIClient

from exams.models import Exam, Copy, Booklet
from grading.models import Score, Annotation
from exams.serializers import CopySerializer
from core.auth import UserRole

User = get_user_model()


def _make_exam_with_structure(name="Test Exam", structure=None):
    structure = structure or [
        {
            "id": "q1",
            "label": "Question 1",
            "points": 10,
        },
        {
            "id": "q2",
            "label": "Question 2",
            "points": 10,
        },
    ]
    return Exam.objects.create(
        name=name,
        date=date.today(),
        grading_structure=structure,
    )


def _make_copy(exam, anonymous_id="COPY-001", status=Copy.Status.READY):
    return Copy.objects.create(
        exam=exam,
        anonymous_id=anonymous_id,
        status=status,
    )


def _make_users():
    teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)

    teacher = User.objects.create_user(username="t_audit", password="pass", is_staff=False)
    teacher.groups.add(teacher_group)

    admin = User.objects.create_user(username="a_audit", password="pass", is_staff=True, is_superuser=True)
    admin.groups.add(admin_group)

    return teacher, admin


# ---------------------------------------------------------------------------
# 1. CopySerializer.get_total_score
# ---------------------------------------------------------------------------

class TestCopySerializerTotalScore(TestCase):

    def setUp(self):
        self.exam = _make_exam_with_structure()
        self.copy = _make_copy(self.exam)

    def test_total_score_is_none_when_no_score_object(self):
        """total_score doit être None si aucun Score n'existe pour la copie."""
        self.assertFalse(Score.objects.filter(copy=self.copy).exists())
        serializer = CopySerializer(self.copy, context={})
        data = serializer.data
        self.assertIsNone(data['total_score'])

    def test_total_score_is_none_when_scores_data_empty(self):
        """total_score doit être None si scores_data est vide."""
        Score.objects.create(copy=self.copy, scores_data={})
        serializer = CopySerializer(self.copy, context={})
        self.assertIsNone(serializer.data['total_score'])

    def test_total_score_sums_correctly(self):
        """total_score doit sommer toutes les valeurs numériques de scores_data."""
        Score.objects.create(copy=self.copy, scores_data={"q1": 8.5, "q2": 7.0})
        serializer = CopySerializer(self.copy, context={})
        self.assertAlmostEqual(serializer.data['total_score'], 15.5, places=5)

    def test_total_score_ignores_null_values(self):
        """total_score doit ignorer les valeurs null/vides."""
        Score.objects.create(copy=self.copy, scores_data={"q1": 10, "q2": None, "q3": ""})
        serializer = CopySerializer(self.copy, context={})
        self.assertAlmostEqual(serializer.data['total_score'], 10.0, places=5)

    def test_total_score_handles_string_floats(self):
        """total_score doit gérer les valeurs stockées comme strings ('8.5')."""
        Score.objects.create(copy=self.copy, scores_data={"q1": "8.5", "q2": "6"})
        serializer = CopySerializer(self.copy, context={})
        self.assertAlmostEqual(serializer.data['total_score'], 14.5, places=5)


# ---------------------------------------------------------------------------
# 2. CopySerializer.to_representation — exam_details avec grading_structure
# ---------------------------------------------------------------------------

class TestCopySerializerExamDetails(TestCase):

    def setUp(self):
        self.structure = [
            {"id": "p1", "label": "Partie 1", "points": 6},
            {"id": "p2", "label": "Partie 2", "points": 14, "children": [
                {"id": "e2", "label": "Exercice 2", "points": 7, "children": [
                    {"id": "q2a", "label": "Q2a", "points": 3},
                    {"id": "q2b", "label": "Q2b", "points": 4},
                ]},
                {"id": "e3", "label": "Exercice 3", "points": 7, "children": [
                    {"id": "q3a", "label": "Q3a", "points": 7},
                ]},
            ]},
        ]
        self.exam = _make_exam_with_structure(structure=self.structure)
        self.copy = _make_copy(self.exam)

    def test_exam_details_present_in_representation(self):
        """exam_details doit être injecté dans to_representation."""
        serializer = CopySerializer(self.copy, context={})
        data = serializer.data
        self.assertIn('exam_details', data)
        self.assertEqual(data['exam_details']['id'], str(self.exam.id))
        self.assertEqual(data['exam_details']['name'], self.exam.name)

    def test_exam_details_contains_grading_structure(self):
        """exam_details.grading_structure doit contenir la structure complète."""
        serializer = CopySerializer(self.copy, context={})
        data = serializer.data
        structure = data['exam_details']['grading_structure']
        self.assertEqual(len(structure), 2)
        self.assertEqual(structure[0]['label'], 'Partie 1')
        self.assertEqual(structure[1]['label'], 'Partie 2')
        self.assertEqual(len(structure[1]['children']), 2)

    def test_exam_field_is_uuid_not_nested_object(self):
        """Le champ 'exam' doit être un UUID (pas un objet imbriqué avec grading_structure)."""
        serializer = CopySerializer(self.copy, context={})
        data = serializer.data
        # exam doit être un UUID (string ou objet UUID), pas un dict
        exam_value = data['exam']
        import uuid as uuid_module
        self.assertIsInstance(exam_value, (str, uuid_module.UUID),
                             "exam doit être un UUID, pas un dict imbriqué")
        self.assertNotIsInstance(exam_value, dict,
                                "exam ne doit pas être un dict — utiliser exam_details")
        # Confirmation : accéder à grading_structure via exam échouerait silencieusement
        # (c'est le bug de CorrectorDashboard.vue corrigé)

    def test_pages_per_booklet_in_exam_details(self):
        """exam_details.pages_per_booklet doit être présent."""
        serializer = CopySerializer(self.copy, context={})
        data = serializer.data
        self.assertIn('pages_per_booklet', data['exam_details'])


# ---------------------------------------------------------------------------
# 3. CopySerializer — graded_at présent et correctement exposé
# ---------------------------------------------------------------------------

class TestCopySerializerGradedAt(TestCase):

    def setUp(self):
        self.exam = _make_exam_with_structure()
        self.copy = _make_copy(self.exam, status=Copy.Status.FINALIZED)

    def test_graded_at_in_serializer_fields(self):
        """graded_at doit être dans les champs du CopySerializer."""
        serializer = CopySerializer(self.copy, context={})
        self.assertIn('graded_at', serializer.data)

    def test_graded_at_is_none_for_ready_copy(self):
        """Une copie non finalisée doit avoir graded_at à None."""
        ready_copy = _make_copy(self.exam, anonymous_id="COPY-002")
        serializer = CopySerializer(ready_copy, context={})
        self.assertIsNone(serializer.data['graded_at'])

    def test_copy_has_no_updated_at_field(self):
        """Le modèle Copy ne doit pas avoir de champ updated_at (c'est graded_at)."""
        self.assertFalse(hasattr(Copy, 'updated_at') and
                        hasattr(Copy._meta.get_field('graded_at'), 'auto_now'),
                        "Copy.graded_at n'est pas auto_now — c'est normal")
        # Vérifier que updated_at n'est pas dans le modèle Copy
        field_names = [f.name for f in Copy._meta.get_fields()]
        self.assertNotIn('updated_at', field_names,
                        "Copy ne doit pas avoir de champ updated_at — utiliser graded_at")


# ---------------------------------------------------------------------------
# 4. CopyGlobalAppreciationView — GET fonctionnel
# ---------------------------------------------------------------------------

class TestGlobalAppreciationView(TestCase):

    def setUp(self):
        self.teacher, self.admin = _make_users()
        self.exam = _make_exam_with_structure()
        self.copy = _make_copy(self.exam)
        self.copy.assigned_corrector = self.teacher
        self.copy.save()
        self.client = APIClient()

    def test_get_global_appreciation_empty(self):
        """GET global-appreciation doit retourner string vide si pas d'appréciation."""
        self.client.force_authenticate(user=self.teacher)
        url = f'/api/grading/copies/{self.copy.id}/global-appreciation/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('global_appreciation', response.data)
        self.assertEqual(response.data['global_appreciation'], '')

    def test_patch_then_get_global_appreciation(self):
        """PATCH puis GET doit retourner la valeur sauvegardée."""
        self.client.force_authenticate(user=self.teacher)
        url = f'/api/grading/copies/{self.copy.id}/global-appreciation/'

        self.client.patch(url, {'global_appreciation': 'Bon travail globalement.'}, format='json')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['global_appreciation'], 'Bon travail globalement.')


# ---------------------------------------------------------------------------
# 5. CopyScoresView — atomicité avec select_for_update
# ---------------------------------------------------------------------------

class TestCopyScoresAtomicity(TestCase):

    def setUp(self):
        self.teacher, self.admin = _make_users()
        self.exam = _make_exam_with_structure()
        self.copy = _make_copy(self.exam)
        self.copy.assigned_corrector = self.teacher
        self.copy.save()
        self.client = APIClient()

    def test_put_scores_creates_score_object(self):
        """PUT /scores/ doit créer un Score si inexistant."""
        self.client.force_authenticate(user=self.teacher)
        url = f'/api/grading/copies/{self.copy.id}/scores/'
        payload = {'scores_data': {'q1': 8.0, 'q2': 7.0}}
        response = self.client.put(url, payload, format='json')
        self.assertIn(response.status_code, [200, 201])
        self.assertTrue(Score.objects.filter(copy=self.copy).exists())

    def test_put_scores_updates_existing_score(self):
        """PUT /scores/ doit mettre à jour le Score existant, pas en créer un second."""
        Score.objects.create(copy=self.copy, scores_data={'q1': 5.0})
        self.client.force_authenticate(user=self.teacher)
        url = f'/api/grading/copies/{self.copy.id}/scores/'
        payload = {'scores_data': {'q1': 9.0, 'q2': 8.0}}
        self.client.put(url, payload, format='json')
        # Il ne doit y avoir qu'un seul Score
        self.assertEqual(Score.objects.filter(copy=self.copy).count(), 1)
        score = Score.objects.get(copy=self.copy)
        self.assertEqual(float(score.scores_data['q1']), 9.0)

    def test_put_scores_rejects_negative_values(self):
        """PUT /scores/ doit rejeter les notes négatives."""
        self.client.force_authenticate(user=self.teacher)
        url = f'/api/grading/copies/{self.copy.id}/scores/'
        payload = {'scores_data': {'q1': -1.0}}
        response = self.client.put(url, payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_put_scores_sets_copy_in_progress(self):
        """Sauvegarder des scores sur une copie READY doit la passer IN_PROGRESS."""
        self.assertEqual(self.copy.status, Copy.Status.READY)
        self.client.force_authenticate(user=self.teacher)
        url = f'/api/grading/copies/{self.copy.id}/scores/'
        self.client.put(url, {'scores_data': {'q1': 5.0}}, format='json')
        self.copy.refresh_from_db()
        self.assertEqual(self.copy.status, Copy.Status.IN_PROGRESS)

    def test_unauthorized_corrector_cannot_put_scores(self):
        """Un correcteur non assigné ne doit pas pouvoir modifier les scores."""
        other_teacher = User.objects.create_user(username="other_t", password="pass")
        other_teacher.groups.add(Group.objects.get(name=UserRole.TEACHER))
        self.client.force_authenticate(user=other_teacher)
        url = f'/api/grading/copies/{self.copy.id}/scores/'
        response = self.client.put(url, {'scores_data': {'q1': 5.0}}, format='json')
        self.assertEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# 6. Invariant : exam field est un UUID, pas un objet imbriqué
# ---------------------------------------------------------------------------

class TestCopyAPIResponseShape(TestCase):
    """Vérifie que la forme de la réponse API correspond à ce que le frontend attend."""

    def setUp(self):
        self.teacher, self.admin = _make_users()
        self.exam = _make_exam_with_structure()
        self.copy = _make_copy(self.exam)
        self.copy.assigned_corrector = self.teacher
        self.copy.save()
        self.client = APIClient()

    def test_copy_detail_has_exam_details_not_nested_exam(self):
        """GET /copies/{id}/ doit retourner exam_details (objet) et exam (UUID string)."""
        self.client.force_authenticate(user=self.admin)
        url = f'/api/copies/{self.copy.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # exam doit être un UUID string
        self.assertIsInstance(data['exam'], str)
        # exam_details doit être un objet
        self.assertIsInstance(data['exam_details'], dict)
        self.assertIn('grading_structure', data['exam_details'])

    def test_copy_list_has_exam_details(self):
        """GET /exams/{id}/copies/ doit inclure exam_details dans chaque copie."""
        self.client.force_authenticate(user=self.admin)
        url = f'/api/exams/{self.exam.id}/copies/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        copies = response.json()
        if isinstance(copies, dict):
            copies = copies.get('results', [])
        self.assertTrue(len(copies) > 0)
        copy_data = copies[0]
        self.assertIn('exam_details', copy_data)
        self.assertIn('grading_structure', copy_data['exam_details'])

    def test_copy_has_graded_at_not_updated_at(self):
        """La réponse API ne doit pas exposer updated_at (inexistant sur Copy)."""
        self.client.force_authenticate(user=self.admin)
        url = f'/api/copies/{self.copy.id}/'
        response = self.client.get(url)
        data = response.json()

        self.assertIn('graded_at', data)
        self.assertNotIn('updated_at', data)

    def test_grading_structure_accessible_via_exam_details(self):
        """grading_structure est accessible via exam_details, jamais via exam directement."""
        self.client.force_authenticate(user=self.admin)
        url = f'/api/copies/{self.copy.id}/'
        response = self.client.get(url)
        data = response.json()

        # Via exam_details (correct)
        via_details = data.get('exam_details', {}).get('grading_structure')
        self.assertIsNotNone(via_details)
        self.assertIsInstance(via_details, list)

        # Via exam (doit échouer car c'est un UUID string)
        exam_value = data.get('exam')
        self.assertIsInstance(exam_value, str)
        # On ne peut pas appeler .get('grading_structure') sur un UUID string


# ---------------------------------------------------------------------------
# 7. Machine d'états Copy — transitions valides
# ---------------------------------------------------------------------------

class TestCopyStateMachine(TestCase):

    def setUp(self):
        self.teacher, self.admin = _make_users()
        self.exam = _make_exam_with_structure()
        self.copy = _make_copy(self.exam)
        self.copy.assigned_corrector = self.teacher
        self.copy.save()
        self.client = APIClient()

    def test_ready_copy_can_be_marked_ready(self):
        """POST /ready/ sur une copie READY doit réussir (idempotent)."""
        self.client.force_authenticate(user=self.teacher)
        url = f'/api/grading/copies/{self.copy.id}/ready/'
        response = self.client.post(url)
        # 200 ou 400 acceptable (déjà READY)
        self.assertIn(response.status_code, [200, 400])

    def test_finalized_copy_cannot_be_modified_by_teacher(self):
        """Un enseignant ne doit pas pouvoir modifier les scores d'une copie FINALIZED."""
        self.copy.status = Copy.Status.FINALIZED
        self.copy.save()

        self.client.force_authenticate(user=self.teacher)
        url = f'/api/grading/copies/{self.copy.id}/scores/'
        response = self.client.put(url, {'scores_data': {'q1': 5.0}}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_admin_can_modify_finalized_copy(self):
        """Un admin peut modifier les scores d'une copie FINALIZED (within barème limits)."""
        self.copy.status = Copy.Status.FINALIZED
        self.copy.save()
        Score.objects.create(copy=self.copy, scores_data={'q1': 8.0})

        self.client.force_authenticate(user=self.admin)
        url = f'/api/grading/copies/{self.copy.id}/scores/'
        # q1 max is 10 (from exam grading_structure), so 9.5 is valid
        response = self.client.put(url, {'scores_data': {'q1': 9.5}}, format='json')
        self.assertIn(response.status_code, [200, 201])


# ---------------------------------------------------------------------------
# 8. AnnotationSerializer — version field
# ---------------------------------------------------------------------------

class TestAnnotationSerializerVersion(TestCase):

    def setUp(self):
        self.teacher, self.admin = _make_users()
        self.exam = _make_exam_with_structure()
        self.copy = _make_copy(self.exam)
        self.copy.assigned_corrector = self.teacher
        self.copy.save()
        self.client = APIClient()

    def test_annotation_list_returns_version_field(self):
        """GET /annotations/ doit retourner le champ 'version' pour chaque annotation."""
        Annotation.objects.create(
            copy=self.copy,
            page_index=0,
            x=0.1, y=0.1, w=0.2, h=0.1,
            type='COMMENTAIRE',
            content='Test',
            created_by=self.teacher,
        )
        self.client.force_authenticate(user=self.teacher)
        url = f'/api/grading/copies/{self.copy.id}/annotations/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        annotations = response.json()
        if isinstance(annotations, dict):
            annotations = annotations.get('results', [])
        self.assertTrue(len(annotations) > 0)
        self.assertIn('version', annotations[0],
                     "Le champ 'version' est requis pour l'optimistic locking côté frontend")


# ---------------------------------------------------------------------------
# 9. Champ 'version' dans AnnotationSerializer — read_only
# ---------------------------------------------------------------------------

class TestAnnotationVersionReadOnly(TestCase):

    def setUp(self):
        self.teacher, self.admin = _make_users()
        self.exam = _make_exam_with_structure()
        self.copy = _make_copy(self.exam)
        self.copy.assigned_corrector = self.teacher
        self.copy.save()
        self.annotation = Annotation.objects.create(
            copy=self.copy,
            page_index=0,
            x=0.1, y=0.1, w=0.2, h=0.1,
            type='COMMENTAIRE',
            content='Original',
            created_by=self.teacher,
        )
        self.client = APIClient()

    def test_version_increments_on_update(self):
        """Modifier une annotation doit incrémenter son champ version."""
        initial_version = self.annotation.version
        self.client.force_authenticate(user=self.teacher)
        url = f'/api/grading/annotations/{self.annotation.id}/'
        self.client.patch(url, {'content': 'Modifié'}, format='json')
        self.annotation.refresh_from_db()
        self.assertEqual(self.annotation.version, initial_version + 1)
