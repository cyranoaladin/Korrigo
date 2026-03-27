import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from unittest.mock import patch

from core.auth import UserRole
from exams.models import Exam
from grading.models import QuestionnaireResponse

User = get_user_model()


@pytest.fixture
def teacher_group(db):
    group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    return group


@pytest.fixture
def admin_group(db):
    group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
    return group


@pytest.fixture
def student_group(db):
    group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
    return group


@pytest.fixture
def questionnaire_teacher(db, teacher_group):
    user = User.objects.create_user(
        username='questionnaire_teacher',
        password='testpass123',
        first_name='Prof',
        last_name='Questionnaire',
        email='questionnaire_teacher@test.tn',
        is_staff=False,
        is_superuser=False,
    )
    user.groups.add(teacher_group)
    return user


@pytest.fixture
def questionnaire_teacher_2(db, teacher_group):
    user = User.objects.create_user(
        username='questionnaire_teacher_2',
        password='testpass123',
        first_name='Deuxieme',
        last_name='Correcteur',
        email='questionnaire_teacher_2@test.tn',
        is_staff=False,
        is_superuser=False,
    )
    user.groups.add(teacher_group)
    return user


@pytest.fixture
def questionnaire_teacher_3(db, teacher_group):
    user = User.objects.create_user(
        username='questionnaire_teacher_3',
        password='testpass123',
        first_name='Troisieme',
        last_name='Correcteur',
        email='questionnaire_teacher_3@test.tn',
        is_staff=False,
        is_superuser=False,
    )
    user.groups.add(teacher_group)
    return user


@pytest.fixture
def questionnaire_admin(db, admin_group):
    user = User.objects.create_user(
        username='questionnaire_admin',
        password='testpass123',
        first_name='Admin',
        last_name='Questionnaire',
        email='questionnaire_admin@test.tn',
        is_staff=True,
        is_superuser=True,
    )
    user.groups.add(admin_group)
    return user


@pytest.fixture
def questionnaire_student(db, student_group):
    user = User.objects.create_user(
        username='questionnaire_student',
        password='testpass123',
        email='questionnaire_student@test.tn',
        is_staff=False,
        is_superuser=False,
    )
    user.groups.add(student_group)
    return user


@pytest.fixture
def questionnaire_plain_user(db):
    return User.objects.create_user(
        username='questionnaire_plain',
        password='testpass123',
        email='questionnaire_plain@test.tn',
        is_staff=False,
        is_superuser=False,
    )


@pytest.fixture
def questionnaire_payload():
    return {
        '_uid': 'questionnaire_teacher',
        'q11': 4,
        'q12': 5,
        'q21': 'Utile',
        'q25': ['Navigation entre les copies'],
        'q53': 9,
        'q61': 'Satisfait(e) — bon outil, quelques ajustements à faire',
        'q62': 'Très bonne expérience.'
    }


@pytest.fixture
def questionnaire_exam(db, questionnaire_teacher, questionnaire_teacher_2):
    exam = Exam.objects.create(
        name='Questionnaire Exam',
        date='2026-03-01',
    )
    exam.correctors.add(questionnaire_teacher, questionnaire_teacher_2)
    return exam


@pytest.mark.django_db
class TestQuestionnaireResponseEndpoint:
    def test_teacher_get_without_existing_response_returns_empty_payload(self, api_client, questionnaire_teacher):
        api_client.force_authenticate(questionnaire_teacher)

        response = api_client.get('/api/grading/questionnaire/')

        assert response.status_code == 200
        assert response.data['has_response'] is False
        assert response.data['response'] == {}
        assert response.data['submitted_at'] is None
        assert response.data['respondent']['username'] == 'questionnaire_teacher'
        assert response.data['respondent']['display_name'] == 'Prof Questionnaire'
        assert response.data['summary']['responses_count'] == 0
        assert response.data['summary']['total_eligible'] >= 1
        assert response.data['summary']['is_available'] is False

    def test_teacher_can_create_questionnaire_response(self, api_client, questionnaire_teacher, questionnaire_payload):
        api_client.force_authenticate(questionnaire_teacher)

        response = api_client.post('/api/grading/questionnaire/', questionnaire_payload, format='json')

        assert response.status_code == 200
        assert response.data['status'] == 'ok'
        stored = QuestionnaireResponse.objects.get(user=questionnaire_teacher)
        assert stored.payload == questionnaire_payload

    def test_auto_generation_is_triggered_when_last_eligible_corrector_submits(
        self,
        api_client,
        questionnaire_teacher,
        questionnaire_teacher_2,
        questionnaire_exam,
        questionnaire_payload,
    ):
        QuestionnaireResponse.objects.create(user=questionnaire_teacher_2, payload={'q53': 7})
        api_client.force_authenticate(questionnaire_teacher)

        with patch('grading.views_questionnaire.trigger_questionnaire_bilan_generation') as trigger_mock:
            response = api_client.post('/api/grading/questionnaire/', questionnaire_payload, format='json')

        assert response.status_code == 200
        assert response.data['summary']['is_available'] is True
        trigger_mock.assert_called_once_with()

    def test_teacher_cannot_submit_questionnaire_twice(self, api_client, questionnaire_teacher, questionnaire_payload):
        QuestionnaireResponse.objects.create(user=questionnaire_teacher, payload={'q11': 1, 'q53': 2})
        api_client.force_authenticate(questionnaire_teacher)

        response = api_client.post('/api/grading/questionnaire/', {'answers': questionnaire_payload}, format='json')

        assert response.status_code == 409
        assert response.data['detail'] == 'Le questionnaire a déjà été soumis.'
        stored = QuestionnaireResponse.objects.get(user=questionnaire_teacher)
        assert QuestionnaireResponse.objects.filter(user=questionnaire_teacher).count() == 1
        assert stored.payload == {'q11': 1, 'q53': 2}

    def test_teacher_get_returns_existing_response(self, api_client, questionnaire_teacher, questionnaire_payload):
        QuestionnaireResponse.objects.create(user=questionnaire_teacher, payload=questionnaire_payload)
        api_client.force_authenticate(questionnaire_teacher)

        response = api_client.get('/api/grading/questionnaire/')

        assert response.status_code == 200
        assert response.data['has_response'] is True
        assert response.data['response'] == questionnaire_payload
        assert response.data['submitted_at'] is not None
        assert response.data['respondent']['username'] == questionnaire_teacher.username
        assert response.data['respondent']['display_name'] == 'Prof Questionnaire'

    def test_teacher_get_returns_existing_response_after_submission(self, api_client, questionnaire_teacher, questionnaire_payload):
        QuestionnaireResponse.objects.create(user=questionnaire_teacher, payload=questionnaire_payload)
        api_client.force_authenticate(questionnaire_teacher)

        response = api_client.get('/api/grading/questionnaire/')

        assert response.status_code == 200
        assert response.data['has_response'] is True
        assert response.data['response'] == questionnaire_payload
        assert response.data['submitted_at'] is not None
        assert response.data['respondent']['username'] == questionnaire_teacher.username
        assert response.data['respondent']['display_name'] == 'Prof Questionnaire'

    def test_invalid_payload_is_rejected(self, api_client, questionnaire_teacher):
        api_client.force_authenticate(questionnaire_teacher)

        response = api_client.post('/api/grading/questionnaire/', {'answers': ['bad']}, format='json')

        assert response.status_code == 400
        assert response.data['detail'] == 'Payload invalide.'
        assert QuestionnaireResponse.objects.count() == 0

    def test_unauthenticated_user_is_rejected(self, api_client):
        response = api_client.get('/api/grading/questionnaire/')

        assert response.status_code in [401, 403]

    def test_student_user_is_rejected(self, api_client, questionnaire_student):
        api_client.force_authenticate(questionnaire_student)

        response = api_client.get('/api/grading/questionnaire/')

        assert response.status_code == 403

    def test_plain_user_is_rejected(self, api_client, questionnaire_plain_user):
        api_client.force_authenticate(questionnaire_plain_user)

        response = api_client.get('/api/grading/questionnaire/')

        assert response.status_code == 403

    def test_admin_can_access_questionnaire(self, api_client, questionnaire_admin):
        # IsTeacher explicitly allows is_superuser/is_staff for monitoring (see core/auth.py)
        api_client.force_authenticate(questionnaire_admin)

        response = api_client.get('/api/grading/questionnaire/')

        assert response.status_code == 200


@pytest.mark.django_db
class TestQuestionnaireBilanEndpoint:
    def test_admin_can_access_bilan_with_summary_and_responses(
        self,
        api_client,
        questionnaire_admin,
        questionnaire_teacher,
        questionnaire_teacher_2,
    ):
        QuestionnaireResponse.objects.create(
            user=questionnaire_teacher,
            payload={'q53': 9, 'q61': 'Satisfait(e) — bon outil, quelques ajustements à faire'}
        )
        QuestionnaireResponse.objects.create(
            user=questionnaire_teacher_2,
            payload={'q53': 6, 'q61': 'Mitigé(e) — autant d\'avantages que d\'inconvénients'}
        )
        api_client.force_authenticate(questionnaire_admin)

        response = api_client.get('/api/grading/questionnaire/bilan/')

        assert response.status_code == 200
        assert response.data['summary']['responses_count'] == 2
        assert response.data['summary']['total_eligible'] == 2
        assert response.data['summary']['completion_rate'] == 100.0
        assert len(response.data['responses']) == 2
        first = response.data['responses'][0]
        assert 'display_name' in first
        assert 'answers' in first
        assert 'submitted_at' in first

    def test_teacher_can_access_bilan_when_all_responses_are_complete(
        self,
        api_client,
        questionnaire_teacher,
        questionnaire_teacher_2,
    ):
        QuestionnaireResponse.objects.create(user=questionnaire_teacher, payload={'q53': 9})
        QuestionnaireResponse.objects.create(user=questionnaire_teacher_2, payload={'q53': 8})
        api_client.force_authenticate(questionnaire_teacher)

        response = api_client.get('/api/grading/questionnaire/bilan/')

        assert response.status_code == 200
        assert response.data['summary']['is_available'] is True
        assert len(response.data['responses']) == 2

    def test_bilan_is_locked_until_all_teachers_have_responded(
        self,
        api_client,
        questionnaire_admin,
        questionnaire_teacher,
        questionnaire_teacher_2,
    ):
        QuestionnaireResponse.objects.create(user=questionnaire_teacher, payload={'q53': 8})
        api_client.force_authenticate(questionnaire_admin)

        response = api_client.get('/api/grading/questionnaire/bilan/')

        assert response.status_code == 200
        assert response.data['summary']['responses_count'] == 1
        assert response.data['summary']['total_eligible'] == 2
        assert response.data['summary']['completion_rate'] == 50.0
        assert response.data['summary']['remaining_count'] == 1
        assert response.data['summary']['is_available'] is False
        assert len(response.data['responses']) == 1
        assert response.data['responses'][0]['username'] == questionnaire_teacher.username
        assert len(response.data['participants']['responded']) == 1
        assert len(response.data['participants']['pending']) == 1
        assert response.data['participants']['pending'][0]['username'] == questionnaire_teacher_2.username
        # detail is empty — bilan is accessible even before all teachers respond
        assert response.data['detail'] == ''

    def test_admin_can_access_partial_detailed_responses_before_completion(
        self,
        api_client,
        questionnaire_admin,
        questionnaire_teacher,
        questionnaire_teacher_2,
        questionnaire_exam,
        questionnaire_payload,
    ):
        QuestionnaireResponse.objects.create(user=questionnaire_teacher, payload=questionnaire_payload)
        api_client.force_authenticate(questionnaire_admin)

        response = api_client.get('/api/grading/questionnaire/bilan/')

        assert response.status_code == 200
        assert response.data['summary']['is_available'] is False
        assert len(response.data['responses']) == 1
        assert response.data['responses'][0]['answers'] == questionnaire_payload
        assert len(response.data['participants']['responded']) == 1
        assert len(response.data['participants']['pending']) == 1

    def test_teacher_cannot_see_detailed_responses_before_completion(
        self,
        api_client,
        questionnaire_teacher,
        questionnaire_teacher_2,
        questionnaire_exam,
    ):
        QuestionnaireResponse.objects.create(user=questionnaire_teacher, payload={'q53': 8})
        api_client.force_authenticate(questionnaire_teacher)

        response = api_client.get('/api/grading/questionnaire/bilan/')

        assert response.status_code == 200
        assert response.data['summary']['is_available'] is False
        assert response.data['responses'] == []
        assert len(response.data['participants']['responded']) == 1
        assert len(response.data['participants']['pending']) == 1

    def test_summary_uses_assigned_corrector_cohort_instead_of_all_teacher_group_users(
        self,
        api_client,
        questionnaire_admin,
        questionnaire_teacher,
        questionnaire_teacher_2,
        questionnaire_teacher_3,
        questionnaire_exam,
    ):
        QuestionnaireResponse.objects.create(user=questionnaire_teacher, payload={'q53': 8})
        api_client.force_authenticate(questionnaire_admin)

        response = api_client.get('/api/grading/questionnaire/bilan/')

        assert response.status_code == 200
        assert response.data['summary']['total_eligible'] == 2
        assert response.data['summary']['responses_count'] == 1
        assert response.data['summary']['remaining_count'] == 1
        assert response.data['summary']['completion_rate'] == 50.0

    def test_student_cannot_access_admin_bilan(self, api_client, questionnaire_student):
        api_client.force_authenticate(questionnaire_student)

        response = api_client.get('/api/grading/questionnaire/bilan/')

        assert response.status_code == 403

    def test_unauthenticated_user_cannot_access_admin_bilan(self, api_client):
        response = api_client.get('/api/grading/questionnaire/bilan/')

        assert response.status_code in [401, 403]
