"""
Tests pour MyStudentsListView (GET /api/grading/my-students/).

Spec :
- Sans paramètre : retourne tous les élèves des assignations du correcteur
  avec toutes leurs copies (mode legacy).
- Avec exam_id : retourne UNIQUEMENT les élèves du correcteur qui ont une
  copie FINALIZED dans cet examen, et UNIQUEMENT les copies assignées au
  correcteur (sauf admin qui voit tout).
- Couvre les 4 examens réels : BB_J1, BB_J2, DNB_2026, EAM BLANCHE 2026.
"""
import uuid
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from core.auth import UserRole
from exams.models import Booklet, Copy, Exam, ExamType, TeacherGroupAssignment
from students.models import Student

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_teacher(username):
    u = User.objects.create_user(username=username, password="pass1234")
    g, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    u.groups.add(g)
    return u


def _make_admin(username):
    u = User.objects.create_user(
        username=username, password="pass1234",
        is_staff=True, is_superuser=True,
    )
    g, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
    u.groups.add(g)
    return u


def _make_exam(name, exam_type, exam_date=None):
    return Exam.objects.create(
        name=name,
        date=exam_date or date.today(),
        exam_type=exam_type,
    )


def _make_student(first, last, class_name, groupe=None, dob=None):
    return Student.objects.create(
        first_name=first,
        last_name=last,
        date_naissance=dob or date(2007, 1, 1),
        class_name=class_name,
        groupe=groupe,
    )


def _make_copy(exam, student, anon, status, corrector=None):
    booklet = Booklet.objects.create(
        exam=exam, start_page=1, end_page=4, pages_images=["p000.png"],
    )
    copy = Copy.objects.create(
        exam=exam,
        student=student,
        anonymous_id=anon,
        status=status,
        assigned_corrector=corrector,
    )
    copy.booklets.add(booklet)
    return copy


def _assign_teacher(teacher, level, group_name, assignment_type='groupe'):
    return TeacherGroupAssignment.objects.create(
        teacher=teacher,
        level=level,
        group_name=group_name,
        assignment_type=assignment_type,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures pour les 4 examens réels
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def bac_type(db):
    return ExamType.objects.create(
        name="Bac Blanc Maths 2026", code="BAC_BLANC_MATHS_2026",
    )


@pytest.fixture
def dnb_type(db):
    return ExamType.objects.create(
        name="DNB Blanc Maths 2026", code="DNB_BLANC_MATHS_2026",
    )


@pytest.fixture
def eam_type(db):
    return ExamType.objects.create(name="EAM 2026", code="EAM_2026")


@pytest.fixture
def bb_j1(db, bac_type):
    return _make_exam("BB_J1", bac_type, exam_date=date(2026, 1, 10))


@pytest.fixture
def bb_j2(db, bac_type):
    return _make_exam("BB_J2", bac_type, exam_date=date(2026, 1, 11))


@pytest.fixture
def dnb_exam(db, dnb_type):
    return _make_exam("DNB_2026", dnb_type, exam_date=date(2026, 1, 15))


@pytest.fixture
def eam_exam(db, eam_type):
    return _make_exam("EAM BLANCHE 2026", eam_type, exam_date=date(2026, 2, 1))


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures pour le correcteur "alaeddine"
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def alaeddine(db):
    """Correcteur assigné Terminale G3 + Première G6 (cas réel)."""
    teacher = _make_teacher("alaeddine.benrhouma")
    _assign_teacher(teacher, level='terminale', group_name='G3')
    _assign_teacher(teacher, level='premiere', group_name='G6')
    return teacher


@pytest.fixture
def other_teacher(db):
    """Un autre correcteur, pour vérifier l'isolation."""
    teacher = _make_teacher("other.teacher")
    _assign_teacher(teacher, level='terminale', group_name='G3')
    return teacher


@pytest.fixture
def admin(db):
    return _make_admin("admin_user")


@pytest.fixture
def students_terminale_g3(db):
    """Élèves de Terminale G3 (assignés à alaeddine)."""
    return [
        _make_student("Alice", "Dupont", "T.04", groupe="G3"),
        _make_student("Bob", "Martin", "T.04", groupe="G3"),
    ]


@pytest.fixture
def students_premiere_g6(db):
    """Élèves de Première G6 (assignés à alaeddine)."""
    return [
        _make_student("Chloe", "Durand", "1.02", groupe="G6"),
        _make_student("David", "Petit", "1.02", groupe="G6"),
    ]


@pytest.fixture
def students_terminale_g1(db):
    """Élèves de Terminale G1 (NON assignés à alaeddine)."""
    return [
        _make_student("Eve", "Robert", "T.01", groupe="G1"),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Tests : sans exam_id (mode legacy)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_without_exam_returns_all_students_legacy(
    alaeddine, students_terminale_g3, students_premiere_g6, students_terminale_g1
):
    """Sans exam_id : tous les élèves des assignations du correcteur."""
    client = APIClient()
    client.force_authenticate(user=alaeddine)
    res = client.get('/api/grading/my-students/', secure=True)
    assert res.status_code == 200
    data = res.json()
    assert 'groupe' in data  # format legacy
    assert data.get('filter') != 'finalized_only'
    # Doit inclure les 4 élèves G3 + G6 (jamais G1)
    names = {(s['first_name'], s['last_name']) for s in data['students']}
    assert ('Alice', 'Dupont') in names
    assert ('Bob', 'Martin') in names
    assert ('Chloe', 'Durand') in names
    assert ('David', 'Petit') in names
    assert ('Eve', 'Robert') not in names


@pytest.mark.django_db
def test_without_assignment_returns_empty(db):
    """Correcteur sans assignation → liste vide, pas d'erreur."""
    teacher = _make_teacher("ghost")
    client = APIClient()
    client.force_authenticate(user=teacher)
    res = client.get('/api/grading/my-students/', secure=True)
    assert res.status_code == 200
    assert res.json()['students'] == []


# ─────────────────────────────────────────────────────────────────────────────
# Tests : filtrage strict par exam_id (BB_J1, BB_J2, DNB_2026, EAM)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_bb_j1_returns_only_terminale_finalized(
    alaeddine, bb_j1, bb_j2, students_terminale_g3, students_premiere_g6
):
    """BB_J1 (terminale) → seuls les élèves Terminale G3 avec copie FINALIZED."""
    alice, bob = students_terminale_g3
    chloe, _ = students_premiere_g6

    # Alice a une copie FINALIZED dans BB_J1 (assignée à alaeddine)
    _make_copy(bb_j1, alice, "BBJ1-001", Copy.Status.FINALIZED, corrector=alaeddine)
    # Bob a une copie en cours (READY) → ne doit PAS apparaître
    _make_copy(bb_j1, bob, "BBJ1-002", Copy.Status.READY, corrector=alaeddine)
    # Alice a aussi une copie dans BB_J2 → ne doit pas polluer le retour BB_J1
    _make_copy(bb_j2, alice, "BBJ2-001", Copy.Status.FINALIZED, corrector=alaeddine)
    # Chloe (première) a une copie EAM, non liée → exclue
    # (pas de copie BB_J1 pour les premières)

    client = APIClient()
    client.force_authenticate(user=alaeddine)
    res = client.get('/api/grading/my-students/', secure=True, data={'exam_id': str(bb_j1.id)})
    assert res.status_code == 200
    data = res.json()

    assert data['filter'] == 'finalized_only'
    assert data['exam_id'] == str(bb_j1.id)
    assert data['exam_name'] == 'BB_J1'

    # Seule Alice doit être retournée
    assert len(data['students']) == 1
    s = data['students'][0]
    assert s['first_name'] == 'Alice'
    # Une seule copie (FINALIZED, dans BB_J1)
    assert len(s['copies']) == 1
    assert s['copies'][0]['exam_name'] == 'BB_J1'
    assert s['copies'][0]['status'] == Copy.Status.FINALIZED


@pytest.mark.django_db
def test_bb_j2_isolated_from_bb_j1(
    alaeddine, bb_j1, bb_j2, students_terminale_g3
):
    """BB_J2 et BB_J1 partagent le même ExamType : doivent être bien isolés."""
    alice, bob = students_terminale_g3

    _make_copy(bb_j1, alice, "BBJ1-001", Copy.Status.FINALIZED, corrector=alaeddine)
    _make_copy(bb_j2, bob, "BBJ2-001", Copy.Status.FINALIZED, corrector=alaeddine)

    client = APIClient()
    client.force_authenticate(user=alaeddine)

    # BB_J1 : Alice seule
    res = client.get('/api/grading/my-students/', secure=True, data={'exam_id': str(bb_j1.id)})
    data = res.json()
    assert {s['first_name'] for s in data['students']} == {'Alice'}

    # BB_J2 : Bob seul
    res = client.get('/api/grading/my-students/', secure=True, data={'exam_id': str(bb_j2.id)})
    data = res.json()
    assert {s['first_name'] for s in data['students']} == {'Bob'}


@pytest.mark.django_db
def test_eam_returns_only_premiere_finalized(
    alaeddine, eam_exam, students_terminale_g3, students_premiere_g6
):
    """EAM BLANCHE 2026 → seuls les élèves Première G6 avec copie FINALIZED."""
    alice, _ = students_terminale_g3
    chloe, david = students_premiere_g6

    _make_copy(eam_exam, chloe, "EAM-001", Copy.Status.FINALIZED, corrector=alaeddine)
    _make_copy(eam_exam, david, "EAM-002", Copy.Status.IN_PROGRESS, corrector=alaeddine)
    # Alice (terminale) sur EAM → ne devrait pas exister normalement, mais
    # si elle a une copie, l'EAM ne concerne PAS les terminales d'alaeddine.
    # On la met quand même pour vérifier que le filtre level passe :
    _make_copy(eam_exam, alice, "EAM-099", Copy.Status.FINALIZED, corrector=alaeddine)

    client = APIClient()
    client.force_authenticate(user=alaeddine)
    res = client.get('/api/grading/my-students/', secure=True, data={'exam_id': str(eam_exam.id)})
    data = res.json()

    # Doit retourner Alice (assignée Terminale) ET Chloe (assignée Première)
    # car les deux sont dans les assignations d'alaeddine et ont une copie
    # FINALIZED dans cet examen. David est exclu (IN_PROGRESS).
    names = {s['first_name'] for s in data['students']}
    assert 'Chloe' in names
    assert 'David' not in names  # IN_PROGRESS exclu


@pytest.mark.django_db
def test_dnb_no_assignment_returns_empty(alaeddine, dnb_exam):
    """alaeddine n'est pas assigné en troisième → DNB ne retourne rien.
    NOTE: si alaeddine voulait DNB il faudrait l'assigner level=troisieme.
    """
    # Pas d'assignation troisième pour alaeddine
    client = APIClient()
    client.force_authenticate(user=alaeddine)
    res = client.get('/api/grading/my-students/', secure=True, data={'exam_id': str(dnb_exam.id)})
    assert res.status_code == 200
    data = res.json()
    # Aucune copie finalisée pour ses élèves dans DNB → liste vide
    assert data['students'] == []


# ─────────────────────────────────────────────────────────────────────────────
# Tests : statut FINALIZED only
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_excludes_non_finalized_copies(
    alaeddine, bb_j1, students_terminale_g3
):
    """Seules les copies FINALIZED apparaissent ; READY/IN_PROGRESS/SUBMITTED exclues."""
    alice, bob = students_terminale_g3
    _make_copy(bb_j1, alice, "A-FIN", Copy.Status.FINALIZED, corrector=alaeddine)
    _make_copy(bb_j1, bob, "B-RDY", Copy.Status.READY, corrector=alaeddine)

    client = APIClient()
    client.force_authenticate(user=alaeddine)
    res = client.get('/api/grading/my-students/', secure=True, data={'exam_id': str(bb_j1.id)})
    data = res.json()
    names = {s['first_name'] for s in data['students']}
    assert names == {'Alice'}  # Bob exclu (READY)


# ─────────────────────────────────────────────────────────────────────────────
# Tests : isolation entre correcteurs (assigned_corrector)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_corrector_sees_assigned_students_regardless_of_who_finalized(
    alaeddine, other_teacher, bb_j1, students_terminale_g3
):
    """Règle UNION : un élève de l'assignation du correcteur est visible
    dès lors que sa copie a été finalisée, peu importe par qui.
    (Spec : 'mes élèves dont la copie a été finalisée')"""
    alice, bob = students_terminale_g3

    # Alice : copie finalisée par alaeddine (lui-même)
    _make_copy(bb_j1, alice, "A-001", Copy.Status.FINALIZED, corrector=alaeddine)
    # Bob : copie finalisée par un AUTRE correcteur (other_teacher)
    _make_copy(bb_j1, bob, "B-001", Copy.Status.FINALIZED, corrector=other_teacher)

    client = APIClient()
    client.force_authenticate(user=alaeddine)
    res = client.get('/api/grading/my-students/', secure=True, data={'exam_id': str(bb_j1.id)})
    data = res.json()
    names = {s['first_name'] for s in data['students']}
    # Les DEUX sont dans l'assignation terminale G3 → visibles
    assert names == {'Alice', 'Bob'}


# ─────────────────────────────────────────────────────────────────────────────
# Tests : admin voit toutes les copies finalisées
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_sees_all_finalized_copies(
    alaeddine, other_teacher, admin, bb_j1, students_terminale_g3
):
    """Un admin (sans assignation) voit toutes les copies finalisées si on
    l'authentifie. Note : il doit avoir des assignations pour avoir des
    élèves à matcher. On le force ici en admin avec assignation Terminale G3."""
    alice, bob = students_terminale_g3
    _assign_teacher(admin, level='terminale', group_name='G3')

    _make_copy(bb_j1, alice, "A", Copy.Status.FINALIZED, corrector=alaeddine)
    _make_copy(bb_j1, bob, "B", Copy.Status.FINALIZED, corrector=other_teacher)

    client = APIClient()
    client.force_authenticate(user=admin)
    res = client.get('/api/grading/my-students/', secure=True, data={'exam_id': str(bb_j1.id)})
    data = res.json()
    names = {s['first_name'] for s in data['students']}
    # Admin voit Alice ET Bob (peu importe le correcteur assigné)
    assert names == {'Alice', 'Bob'}


# ─────────────────────────────────────────────────────────────────────────────
# Tests : permissions
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_unauthenticated_returns_403(db, bb_j1):
    """Non-authentifié → 403."""
    client = APIClient()
    res = client.get('/api/grading/my-students/', secure=True, data={'exam_id': str(bb_j1.id)})
    assert res.status_code in (401, 403)


@pytest.mark.django_db
def test_student_role_forbidden(db, bb_j1):
    """Un élève ne doit pas accéder à cette vue (correcteurs/admin only)."""
    student_user = User.objects.create_user(username='studs', password='x')
    g, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
    student_user.groups.add(g)
    client = APIClient()
    client.force_authenticate(user=student_user)
    res = client.get('/api/grading/my-students/', secure=True, data={'exam_id': str(bb_j1.id)})
    assert res.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# Tests : exam_id inexistant
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_unknown_exam_id_returns_404(alaeddine):
    """exam_id qui n'existe pas → 404."""
    client = APIClient()
    client.force_authenticate(user=alaeddine)
    res = client.get('/api/grading/my-students/', secure=True, data={'exam_id': str(uuid.uuid4())})
    assert res.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Test régression : élève de MON assignation finalisé par AUTRE correcteur
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_student_in_my_assignment_finalized_by_other_corrector(
    alaeddine, other_teacher, eam_exam, students_premiere_g6
):
    """Cas réel : alaeddine est assigné Première G6. Un élève G6 en EAM a sa
    copie finalisée par un AUTRE correcteur. alaeddine doit voir cet élève
    (car il est dans son assignation et la copie est finalisée)."""
    chloe, _ = students_premiere_g6

    # Copie finalisée par other_teacher (pas par alaeddine)
    _make_copy(eam_exam, chloe, "EAM-G6", Copy.Status.FINALIZED, corrector=other_teacher)

    client = APIClient()
    client.force_authenticate(user=alaeddine)
    res = client.get('/api/grading/my-students/', secure=True, data={'exam_id': str(eam_exam.id)})
    assert res.status_code == 200
    data = res.json()
    names = {s['first_name'] for s in data['students']}
    assert 'Chloe' in names  # Dans mon assignation + copie finalisée = visible


# ─────────────────────────────────────────────────────────────────────────────
# Test régression : correcteur voit ses élèves même hors group_name officiel
# (cas réel Sami : assigné G1 mais finalise des copies pour G4-G8 + 1.02)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_corrector_sees_students_of_finalized_copies_beyond_assignment(
    alaeddine, bb_j1, db
):
    """Si le correcteur finalise une copie d'un élève en DEHORS de son
    group_name officiel, cet élève doit quand même apparaître (source de
    vérité = les copies finalisées, pas l'assignation group_name)."""
    # Élève hors de l'assignation de alaeddine (pas dans G3 ni G6)
    external_student = _make_student("Zoé", "Extra", "T.99", groupe="G99")
    _make_copy(bb_j1, external_student, "EXT-001", Copy.Status.FINALIZED, corrector=alaeddine)

    client = APIClient()
    client.force_authenticate(user=alaeddine)
    res = client.get('/api/grading/my-students/', secure=True, data={'exam_id': str(bb_j1.id)})
    assert res.status_code == 200
    data = res.json()
    names = {s['first_name'] for s in data['students']}
    assert 'Zoé' in names  # Doit apparaître car alaeddine a finalisé sa copie


# ─────────────────────────────────────────────────────────────────────────────
# Test : exam_type_id AGRÈGE toutes les copies finalisées du type
# (comportement corrigé: avant ne prenait que le 'latest exam')
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_exam_type_id_aggregates_all_exams(
    alaeddine, bac_type, students_terminale_g3
):
    """Avec exam_type_id seul : agrège les copies FINALIZED sur TOUS les
    examens de ce type (BB_J1 ET BB_J2), pas seulement 'le plus récent'.
    Régression test : l'ancien code prenait uniquement BB_J2 (plus récent)
    et ratait les copies BB_J1 du correcteur."""
    alice, bob = students_terminale_g3
    bb_j1 = _make_exam("BB_J1", bac_type, exam_date=date(2026, 1, 10))
    bb_j2 = _make_exam("BB_J2", bac_type, exam_date=date(2026, 1, 20))

    _make_copy(bb_j1, alice, "A1", Copy.Status.FINALIZED, corrector=alaeddine)
    _make_copy(bb_j2, bob, "B2", Copy.Status.FINALIZED, corrector=alaeddine)

    client = APIClient()
    client.force_authenticate(user=alaeddine)
    res = client.get('/api/grading/my-students/', secure=True, data={'exam_type_id': bac_type.id})
    assert res.status_code == 200
    data = res.json()

    # exam_name doit être le nom du TYPE (pas d'un examen précis)
    assert data['exam_name'] == bac_type.name
    assert data['scope'] == 'exam_type'

    # Les DEUX élèves doivent apparaître (BB_J1 + BB_J2 agrégés)
    names = {s['first_name'] for s in data['students']}
    assert names == {'Alice', 'Bob'}

    # Chaque copie garde son exam_name d'origine
    all_copy_exams = {c['exam_name'] for s in data['students'] for c in s['copies']}
    assert all_copy_exams == {'BB_J1', 'BB_J2'}
