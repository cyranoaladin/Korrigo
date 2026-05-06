import pytest
from datetime import date

from django.contrib.auth import get_user_model

from exams.models import Exam, Copy
from grading.models import Score
from students.models import Student

from bilan.services.analytics_simple import DNBAnalyticsEngine


@pytest.mark.django_db
def test_stats_by_question_handles_uuid_and_numeric_ids_without_sort_typeerror():
    """
    Regression test:
    stats_by_question used to sort question ids using a mixed int/str key,
    which crashed for DNB-style grading structures combining numeric ids (e.g. "1")
    with UUID ids.
    """
    uuid_q = "ee620dea-15cb-4827-8e48-b250a19d0d0b"

    exam = Exam.objects.create(
        name="DNB_SORT_TEST",
        date=date(2026, 1, 15),
        grading_structure=[
            {"id": "1", "label": "Partie 1", "points": 6},
            {"id": "p2", "label": "Partie 2", "children": [
                {"id": uuid_q, "label": "Exercice 3 — 1", "points": 0.5},
            ]},
        ],
    )

    # Optional relations: keep them to mirror production queries (select_related).
    student1 = Student.objects.create(
        first_name="ELEVE",
        last_name="TEST1",
        date_naissance=date(2011, 1, 1),
        email="s1@example.com",
        class_name="3A",
    )
    student2 = Student.objects.create(
        first_name="ELEVE",
        last_name="TEST2",
        date_naissance=date(2011, 1, 2),
        email="s2@example.com",
        class_name="3A",
    )
    User = get_user_model()
    corrector = User.objects.create_user(username="corr@test", password="pass")

    c1 = Copy.objects.create(
        exam=exam,
        anonymous_id="C1",
        status=Copy.Status.FINALIZED,
        student=student1,
        assigned_corrector=corrector,
    )
    Score.objects.create(copy=c1, scores_data={"1": 3.0, uuid_q: 0.5})

    c2 = Copy.objects.create(
        exam=exam,
        anonymous_id="C2",
        status=Copy.Status.FINALIZED,
        student=student2,
        assigned_corrector=corrector,
    )
    # Missing uuid_q score -> counts as blank for that question.
    Score.objects.create(copy=c2, scores_data={"1": 6.0})

    engine = DNBAnalyticsEngine("DNB_SORT_TEST")
    q_stats = engine.stats_by_question()

    assert len(q_stats) == 2
    assert q_stats[0]["question"]["id"] == "1"
    assert q_stats[1]["question"]["id"] == uuid_q
    assert q_stats[1]["blank_rate"] == 50.0

