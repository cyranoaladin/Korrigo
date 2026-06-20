"""
Tests P1-004 : Isolation totale BAC BLANC / DNB BLANC

Vérifie que :
1. Un correcteur BAC ne voit que ses copies BAC
2. Un correcteur DNB ne voit que ses copies DNB
3. L'admin voit tout
4. Le dispatch d'un examen ne touche pas les copies de l'autre
5. Les statistiques par examen sont isolées
"""
import pytest
from datetime import date
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework import status as http_status

from core.auth import UserRole
from exams.models import Copy, Exam, ExamType, Booklet

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_teacher(username):
    u = User.objects.create_user(username=username, password="pass1234", is_staff=False)
    g, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    u.groups.add(g)
    return u


def _make_admin(username):
    u = User.objects.create_user(
        username=username, password="pass1234", is_staff=True, is_superuser=True
    )
    g, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
    u.groups.add(g)
    return u


def _make_exam(name, exam_type=None):
    return Exam.objects.create(name=name, date=date.today(), exam_type=exam_type)


def _make_copy(exam, anon_id, corrector=None, status=Copy.Status.READY):
    booklet = Booklet.objects.create(
        exam=exam, start_page=1, end_page=4, pages_images=["p000.png"]
    )
    copy = Copy.objects.create(
        exam=exam,
        anonymous_id=anon_id,
        status=status,
        assigned_corrector=corrector,
    )
    copy.booklets.add(booklet)
    return copy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bac_type(db):
    return ExamType.objects.create(name="BAC BLANC MATHS 2026", code="BB2026")


@pytest.fixture
def dnb_type(db):
    return ExamType.objects.create(name="DNB BLANC MATHS 2026", code="DNBM2026")


@pytest.fixture
def bac_exam(db, bac_type):
    return _make_exam("Bac Blanc Maths 2026 J1", exam_type=bac_type)


@pytest.fixture
def dnb_exam(db, dnb_type):
    return _make_exam("DNB Blanc Maths 2026", exam_type=dnb_type)


@pytest.fixture
def corrector_bac(db):
    return _make_teacher("prof_bac")


@pytest.fixture
def corrector_dnb(db):
    return _make_teacher("prof_dnb")


@pytest.fixture
def admin_user(db):
    return _make_admin("admin_test")


@pytest.fixture
def bac_copy(db, bac_exam, corrector_bac):
    return _make_copy(bac_exam, "BAC-001", corrector=corrector_bac)


@pytest.fixture
def dnb_copy(db, dnb_exam, corrector_dnb):
    return _make_copy(dnb_exam, "DNB-001", corrector=corrector_dnb)


# ---------------------------------------------------------------------------
# Test 1 : correcteur BAC voit uniquement ses copies BAC
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_corrector_bac_sees_only_bac_copies(bac_exam, dnb_exam, corrector_bac, corrector_dnb, bac_copy, dnb_copy):
    """Un correcteur BAC ne doit voir que ses copies BAC, jamais les copies DNB."""
    client = APIClient()
    client.force_authenticate(user=corrector_bac)

    # Via /api/exams/{bac_id}/copies/
    resp = client.get(f"/api/exams/{bac_exam.id}/copies/")
    assert resp.status_code == http_status.HTTP_200_OK
    results = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
    ids = [c["anonymous_id"] for c in results]
    assert "BAC-001" in ids
    assert "DNB-001" not in ids


# ---------------------------------------------------------------------------
# Test 2 : correcteur DNB voit uniquement ses copies DNB
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_corrector_dnb_sees_only_dnb_copies(bac_exam, dnb_exam, corrector_bac, corrector_dnb, bac_copy, dnb_copy):
    """Un correcteur DNB ne doit voir que ses copies DNB, jamais les copies BAC."""
    client = APIClient()
    client.force_authenticate(user=corrector_dnb)

    resp = client.get(f"/api/exams/{dnb_exam.id}/copies/")
    assert resp.status_code == http_status.HTTP_200_OK
    results = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
    ids = [c["anonymous_id"] for c in results]
    assert "DNB-001" in ids
    assert "BAC-001" not in ids


# ---------------------------------------------------------------------------
# Test 3 : l'admin voit tout
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_admin_sees_all_copies(bac_exam, dnb_exam, admin_user, bac_copy, dnb_copy):
    """L'admin peut voir les copies des deux examens."""
    client = APIClient()
    client.force_authenticate(user=admin_user)

    resp_bac = client.get(f"/api/exams/{bac_exam.id}/copies/")
    assert resp_bac.status_code == http_status.HTTP_200_OK
    bac_results = resp_bac.data.get("results", resp_bac.data) if isinstance(resp_bac.data, dict) else resp_bac.data
    bac_ids = [c["anonymous_id"] for c in bac_results]
    assert "BAC-001" in bac_ids

    resp_dnb = client.get(f"/api/exams/{dnb_exam.id}/copies/")
    assert resp_dnb.status_code == http_status.HTTP_200_OK
    dnb_results = resp_dnb.data.get("results", resp_dnb.data) if isinstance(resp_dnb.data, dict) else resp_dnb.data
    dnb_ids = [c["anonymous_id"] for c in dnb_results]
    assert "DNB-001" in dnb_ids


# ---------------------------------------------------------------------------
# Test 4 : le correcteur BAC ne peut pas annoter une copie DNB
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_corrector_bac_cannot_annotate_dnb_copy(dnb_copy, corrector_bac):
    """Un correcteur BAC ne doit pas pouvoir annoter une copie DNB."""
    client = APIClient()
    client.force_authenticate(user=corrector_bac)

    payload = {
        "page_index": 0,
        "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2,
        "type": "COMMENT",
        "content": "Test",
    }
    resp = client.post(f"/api/grading/copies/{dnb_copy.id}/annotations/", payload, format="json")
    assert resp.status_code in (http_status.HTTP_403_FORBIDDEN, http_status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Test 5 : dispatch sur BAC ne touche pas les copies DNB
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_dispatch_bac_does_not_touch_dnb_copies(bac_exam, dnb_exam, corrector_bac, corrector_dnb):
    """L'assignation de correcteurs sur BAC ne doit pas modifier les copies DNB."""
    # Créer des copies NON assignées dans chaque examen
    bac_copy_unassigned = _make_copy(bac_exam, "BAC-UNASSIGNED")
    dnb_copy_unassigned = _make_copy(dnb_exam, "DNB-UNASSIGNED")

    # Assigner un correcteur au BAC (déclenche le signal auto_dispatch)
    bac_exam.correctors.add(corrector_bac)

    # Recharger depuis la DB
    bac_copy_unassigned.refresh_from_db()
    dnb_copy_unassigned.refresh_from_db()

    # La copie BAC doit être assignée
    assert bac_copy_unassigned.assigned_corrector == corrector_bac

    # La copie DNB ne doit PAS être modifiée
    assert dnb_copy_unassigned.assigned_corrector is None


# ---------------------------------------------------------------------------
# Test 6 : les statuts de copies sont corrects (3 états uniquement)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_copy_statuses_are_exactly_three_values(bac_exam):
    """Les statuts valides sont READY, IN_PROGRESS, FINALIZED."""
    valid_statuses = {c[0] for c in Copy.Status.choices}
    assert valid_statuses == {"READY", "IN_PROGRESS", "FINALIZED"}
    # Aucun ancien statut ne doit exister
    assert "STAGING" not in valid_statuses
    assert "LOCKED" not in valid_statuses
    assert "GRADED" not in valid_statuses
    assert "GRADING_IN_PROGRESS" not in valid_statuses
    assert "GRADING_FAILED" not in valid_statuses
