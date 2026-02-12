"""
Tests pour la banque d'annotations (officielles + personnelles).
Couvre : modèles, API suggestions, CRUD annotations personnelles, auto-save.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from grading.models import AnnotationTemplate, UserAnnotation
from exams.models import Exam

User = get_user_model()


@pytest.fixture
def admin_user(db):
    u = User.objects.create_superuser('admin_bank', 'admin@bank.com', 'pass')
    group, _ = Group.objects.get_or_create(name='admin')
    u.groups.add(group)
    return u


@pytest.fixture
def teacher_user(db):
    u = User.objects.create_user('teacher_bank', 'teacher@bank.com', 'pass')
    u.is_staff = True
    u.save()
    group, _ = Group.objects.get_or_create(name='teacher')
    u.groups.add(group)
    return u


@pytest.fixture
def exam(db):
    return Exam.objects.create(name="Bac Blanc J1", date="2026-06-01")


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def teacher_client(teacher_user):
    c = APIClient()
    c.force_authenticate(user=teacher_user)
    return c


@pytest.fixture
def templates(exam):
    """Crée des templates d'annotation pour les tests."""
    t1 = AnnotationTemplate.objects.create(
        exam=exam,
        exercise_number=1,
        question_number='1',
        criterion_type='method',
        severity='info',
        text="Méthode correctement mise en place.",
        tags=['méthode', 'positif'],
    )
    t2 = AnnotationTemplate.objects.create(
        exam=exam,
        exercise_number=1,
        question_number='1',
        criterion_type='error_typique',
        severity='majeur',
        text="Confusion convexité / concavité.",
        tags=['erreur', 'convexité'],
    )
    t3 = AnnotationTemplate.objects.create(
        exam=exam,
        exercise_number=2,
        question_number='3b',
        criterion_type='justification',
        severity='mineur',
        text="Résultat exact mais justification absente.",
        tags=['justification'],
    )
    return [t1, t2, t3]


# ============================================================================
# A) Modèles
# ============================================================================

@pytest.mark.unit
class TestAnnotationTemplateModel:
    def test_create_template(self, exam):
        t = AnnotationTemplate.objects.create(
            exam=exam,
            exercise_number=1,
            question_number='3b',
            criterion_type='method',
            severity='info',
            text="Test annotation template",
        )
        assert t.id is not None
        assert t.is_active is True
        assert str(t).startswith("Ex1 Q3b")

    def test_criterion_type_choices(self):
        choices = dict(AnnotationTemplate.CriterionType.choices)
        assert 'method' in choices
        assert 'error_typique' in choices
        assert 'plafond' in choices

    def test_severity_choices(self):
        choices = dict(AnnotationTemplate.Severity.choices)
        assert 'info' in choices
        assert 'critique' in choices


@pytest.mark.unit
class TestUserAnnotationModel:
    def test_create_user_annotation(self, teacher_user):
        ua = UserAnnotation.objects.create(
            user=teacher_user,
            text="Rédaction imprécise, conclusion non formulée.",
            usage_count=0,
        )
        assert ua.id is not None
        assert ua.is_active is True
        assert ua.usage_count == 0

    def test_ordering_by_usage(self, teacher_user):
        ua1 = UserAnnotation.objects.create(user=teacher_user, text="A", usage_count=5)
        ua2 = UserAnnotation.objects.create(user=teacher_user, text="B", usage_count=10)
        ua3 = UserAnnotation.objects.create(user=teacher_user, text="C", usage_count=1)
        qs = UserAnnotation.objects.filter(user=teacher_user)
        assert list(qs.values_list('text', flat=True)) == ['B', 'A', 'C']


# ============================================================================
# B) API Suggestions contextuelles
# ============================================================================

@pytest.mark.unit
class TestContextualSuggestionsAPI:
    def test_get_suggestions_all(self, teacher_client, exam, templates):
        url = f"/api/grading/exams/{exam.id}/suggestions/"
        resp = teacher_client.get(url)
        assert resp.status_code == 200
        assert 'official' in resp.data
        assert 'personal' in resp.data
        assert len(resp.data['official']) == 3

    def test_filter_by_exercise(self, teacher_client, exam, templates):
        url = f"/api/grading/exams/{exam.id}/suggestions/?exercise=1"
        resp = teacher_client.get(url)
        assert resp.status_code == 200
        assert len(resp.data['official']) == 2

    def test_filter_by_question(self, teacher_client, exam, templates):
        url = f"/api/grading/exams/{exam.id}/suggestions/?exercise=2&question=3b"
        resp = teacher_client.get(url)
        assert resp.status_code == 200
        assert len(resp.data['official']) == 1
        assert resp.data['official'][0]['text'] == "Résultat exact mais justification absente."

    def test_search_query(self, teacher_client, exam, templates):
        url = f"/api/grading/exams/{exam.id}/suggestions/?q=convexité"
        resp = teacher_client.get(url)
        assert resp.status_code == 200
        assert len(resp.data['official']) == 1

    def test_personal_annotations_in_suggestions(self, teacher_client, teacher_user, exam, templates):
        UserAnnotation.objects.create(
            user=teacher_user,
            text="Ma remarque personnelle",
            usage_count=5,
        )
        url = f"/api/grading/exams/{exam.id}/suggestions/"
        resp = teacher_client.get(url)
        assert resp.status_code == 200
        assert len(resp.data['personal']) == 1


# ============================================================================
# C) API Annotations personnelles CRUD
# ============================================================================

@pytest.mark.unit
class TestUserAnnotationCRUD:
    def test_create_annotation(self, teacher_client):
        resp = teacher_client.post("/api/grading/my-annotations/", {
            "text": "Bonne intuition mais manque de justification.",
            "tags": ["justification"],
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['text'] == "Bonne intuition mais manque de justification."
        assert resp.data['usage_count'] == 0

    def test_list_annotations(self, teacher_client, teacher_user):
        UserAnnotation.objects.create(user=teacher_user, text="Ann 1", usage_count=3)
        UserAnnotation.objects.create(user=teacher_user, text="Ann 2", usage_count=7)
        resp = teacher_client.get("/api/grading/my-annotations/")
        assert resp.status_code == 200
        results = resp.data.get('results', resp.data) if isinstance(resp.data, dict) and 'results' in resp.data else resp.data
        assert len(results) == 2
        assert results[0]['text'] == "Ann 2"  # Ordered by usage_count desc

    def test_search_annotations(self, teacher_client, teacher_user):
        UserAnnotation.objects.create(user=teacher_user, text="Confusion convexité")
        UserAnnotation.objects.create(user=teacher_user, text="Bonne méthode")
        resp = teacher_client.get("/api/grading/my-annotations/?q=convexité")
        assert resp.status_code == 200
        results = resp.data.get('results', resp.data) if isinstance(resp.data, dict) and 'results' in resp.data else resp.data
        assert len(results) == 1

    def test_update_annotation(self, teacher_client, teacher_user):
        ua = UserAnnotation.objects.create(user=teacher_user, text="Original")
        resp = teacher_client.patch(
            f"/api/grading/my-annotations/{ua.id}/",
            {"text": "Modifié"},
            format='json'
        )
        assert resp.status_code == 200
        assert resp.data['text'] == "Modifié"

    def test_soft_delete_annotation(self, teacher_client, teacher_user):
        ua = UserAnnotation.objects.create(user=teacher_user, text="À supprimer")
        resp = teacher_client.delete(f"/api/grading/my-annotations/{ua.id}/")
        assert resp.status_code == 204
        ua.refresh_from_db()
        assert ua.is_active is False

    def test_isolation_between_users(self, teacher_client, admin_user, teacher_user):
        UserAnnotation.objects.create(user=teacher_user, text="Teacher's")
        UserAnnotation.objects.create(user=admin_user, text="Admin's")
        resp = teacher_client.get("/api/grading/my-annotations/")
        results = resp.data.get('results', resp.data) if isinstance(resp.data, dict) and 'results' in resp.data else resp.data
        assert len(results) == 1
        assert results[0]['text'] == "Teacher's"


# ============================================================================
# D) API Use + Auto-save
# ============================================================================

@pytest.mark.unit
class TestUserAnnotationUseAndAutoSave:
    def test_use_increments_counter(self, teacher_client, teacher_user):
        ua = UserAnnotation.objects.create(user=teacher_user, text="Test", usage_count=3)
        resp = teacher_client.post(f"/api/grading/my-annotations/{ua.id}/use/")
        assert resp.status_code == 200
        assert resp.data['usage_count'] == 4
        assert resp.data['last_used'] is not None

    def test_auto_save_new(self, teacher_client):
        resp = teacher_client.post("/api/grading/my-annotations/auto-save/", {
            "text": "Nouvelle annotation auto",
            "exercise_context": 2,
            "question_context": "3b",
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['usage_count'] == 1

    def test_auto_save_existing_increments(self, teacher_client, teacher_user):
        UserAnnotation.objects.create(
            user=teacher_user,
            text="Déjà existante",
            usage_count=5,
        )
        resp = teacher_client.post("/api/grading/my-annotations/auto-save/", {
            "text": "Déjà existante",
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['usage_count'] == 6

    def test_auto_save_empty_text_rejected(self, teacher_client):
        resp = teacher_client.post("/api/grading/my-annotations/auto-save/", {
            "text": "",
        }, format='json')
        assert resp.status_code == 400


# ============================================================================
# E) API Templates list
# ============================================================================

@pytest.mark.unit
class TestAnnotationTemplateListAPI:
    def test_list_templates(self, teacher_client, exam, templates):
        url = f"/api/grading/exams/{exam.id}/annotation-templates/"
        resp = teacher_client.get(url)
        assert resp.status_code == 200
        results = resp.data.get('results', resp.data) if isinstance(resp.data, dict) and 'results' in resp.data else resp.data
        assert len(results) == 3

    def test_inactive_templates_excluded(self, teacher_client, exam, templates):
        templates[0].is_active = False
        templates[0].save()
        url = f"/api/grading/exams/{exam.id}/annotation-templates/"
        resp = teacher_client.get(url)
        results = resp.data.get('results', resp.data) if isinstance(resp.data, dict) and 'results' in resp.data else resp.data
        assert len(results) == 2
