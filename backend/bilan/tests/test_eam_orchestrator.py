"""
Tests unitaires pour EamBilanOrchestrator et validate_no_dnb_references.

Ces tests couvrent :
1. validate_no_dnb_references — cas nominaux, faux positifs, contexte ordinal
2. EamBilanOrchestrator._parse_eam_structure — séparation Automatismes / Exercices
3. EamBilanOrchestrator._build_metadata — clés correctes depuis global_stats
4. EamBilanOrchestrator._compute_part_stats — stats Automatismes vs Exercices
5. EamBilanOrchestrator._build_exercise_details — structure barème EAM
6. EamBilanOrchestrator._format_stats_text — pas de N/A avec données réelles
"""

import pytest
from datetime import date
from django.contrib.auth import get_user_model

from exams.models import Exam, Copy
from grading.models import Score
from students.models import Student

from bilan.services.eam_orchestrator import (
    EamBilanOrchestrator,
    validate_no_dnb_references,
    FORBIDDEN_TERMS,
)


# ─────────────────────────────────────────── validate_no_dnb_references ────────

class TestValidateNoDnbReferences:
    """Tests exhaustifs pour la fonction de validation anti-DNB."""

    def test_clean_text_passes(self):
        text = "Bilan de l'épreuve de Première Spécialité Mathématiques."
        ok, found = validate_no_dnb_references(text)
        assert ok is True
        assert found == []

    def test_dnb_detected(self):
        ok, found = validate_no_dnb_references("Le DNB est validé.")
        assert ok is False
        assert 'DNB' in found

    def test_brevet_detected(self):
        ok, found = validate_no_dnb_references("Le brevet des collèges approche.")
        assert ok is False
        assert 'brevet' in found

    def test_brevet_des_colleges_detected(self):
        ok, found = validate_no_dnb_references("Résultats du brevet des collèges.")
        assert ok is False
        assert 'brevet des collèges' in found

    def test_cycle_4_detected(self):
        ok, found = validate_no_dnb_references("Programme du cycle 4.")
        assert ok is False
        assert 'cycle 4' in found

    def test_3e_grade_detected(self):
        ok, found = validate_no_dnb_references("Les élèves de 3e ont réussi.")
        assert ok is False
        assert '3e' in found

    def test_3eme_detected(self):
        ok, found = validate_no_dnb_references("élèves de 3ème niveau.")
        assert ok is False
        assert '3ème' in found

    def test_college_detected(self):
        ok, found = validate_no_dnb_references("Au collège Saint-Exupéry.")
        assert ok is False
        assert 'collège' in found

    def test_diplome_national_detected(self):
        ok, found = validate_no_dnb_references("Le diplôme national valide.")
        assert ok is False
        assert 'diplôme national' in found

    def test_ordinal_troisieme_action_not_flagged(self):
        """'Troisième action' est un ordinal, pas une référence scolaire DNB."""
        text = "Troisième action : travailler la stratégie QCM elle-même."
        ok, found = validate_no_dnb_references(text)
        assert ok is True, f"False positive: found={found}"

    def test_ordinal_troisieme_point_not_flagged(self):
        """'Troisième point' = ordinal, pas DNB."""
        text = "Troisième point abordé dans l'analyse."
        ok, found = validate_no_dnb_references(text)
        assert ok is True, f"False positive: found={found}"

    def test_en_troisieme_grade_detected(self):
        """'en troisième' = contexte scolaire, doit être détecté."""
        text = "Les élèves en troisième préparent leurs révisions."
        ok, found = validate_no_dnb_references(text)
        assert ok is False
        assert 'en troisième' in found

    def test_classe_de_troisieme_detected(self):
        ok, found = validate_no_dnb_references("Programme de la classe de troisième.")
        assert ok is False
        assert 'classe de troisième' in found

    def test_multiple_forbidden_detected(self):
        text = "Le DNB et le brevet des collèges sont des épreuves de 3e."
        ok, found = validate_no_dnb_references(text)
        assert ok is False
        assert len(found) >= 3

    def test_case_insensitive(self):
        ok, found = validate_no_dnb_references("dnb brevet COLLÈGE")
        assert ok is False

    def test_empty_string_passes(self):
        ok, found = validate_no_dnb_references("")
        assert ok is True

    def test_premiere_specialite_keywords_safe(self):
        """Vocabulaire Première Spé — ne doit PAS déclencher de faux positifs."""
        texts = [
            "Suites arithmétiques et géométriques en Première.",
            "Probabilités et loi binomiale : cours de Première Spé.",
            "Fonctions dérivées, second degré, vecteurs.",
            "Trigonométrie et géométrie dans l'espace.",
            "Résultats satisfaisants pour 67% des élèves de Première.",
            "Troisième exercice : étude d'une fonction continue.",
        ]
        for text in texts:
            ok, found = validate_no_dnb_references(text)
            assert ok is True, f"False positive in: {text!r} -> found={found}"


# ─────────────────────────────────────────── EamBilanOrchestrator (unit) ────────

@pytest.fixture
def eam_exam(db):
    """Crée un exam EAM BLANCHE minimal avec la structure barème réelle."""
    exam = Exam.objects.create(
        name="EAM TEST 2026",
        date=date(2026, 5, 1),
        grading_structure=[
            {
                "id": "auto-node",
                "label": "Automatismes",
                "children": [
                    {"id": f"q{i}", "label": f"Automatismes — Q{i}", "points": 0.5}
                    for i in range(1, 13)
                ],
            },
            {
                "id": "ex1-node",
                "label": "Exercice 1",
                "children": [
                    {"id": "a1", "label": "A.1", "points": 0.5},
                    {"id": "a2", "label": "A.2", "points": 0.5},
                    {"id": "b1", "label": "B.1", "points": 1.0},
                    {"id": "b2", "label": "B.2", "points": 1.0},
                ],
            },
            {
                "id": "ex2-node",
                "label": "Exercice 2",
                "children": [
                    {"id": "p1", "label": "1", "points": 1.0},
                    {"id": "p2", "label": "2", "points": 2.0},
                ],
            },
        ],
    )
    return exam


@pytest.mark.django_db
def test_eam_orchestrator_init(eam_exam):
    """L'orchestrateur s'initialise correctement et parse la structure."""
    orc = EamBilanOrchestrator("EAM TEST 2026")
    assert orc.engine.exam is not None
    assert orc.engine.exam.name == "EAM TEST 2026"
    # 12 automatismes
    assert len(orc._automatismes_leaves) == 12
    # 6 exercices questions
    assert len(orc._exercices_leaves) == 6
    assert orc.rag_retriever is not None


@pytest.mark.django_db
def test_eam_parse_structure_separates_parts(eam_exam):
    """Les feuilles Automatismes et Exercices sont bien séparées."""
    orc = EamBilanOrchestrator("EAM TEST 2026")
    auto_ids = {l['id'] for l in orc._automatismes_leaves}
    exo_ids = {l['id'] for l in orc._exercices_leaves}
    # no overlap
    assert auto_ids.isdisjoint(exo_ids)
    # automatismes = q1..q12
    for i in range(1, 13):
        assert f"q{i}" in auto_ids
    # exercices = a1, a2, b1, b2, p1, p2
    for qid in ("a1", "a2", "b1", "b2", "p1", "p2"):
        assert qid in exo_ids


@pytest.mark.django_db
def test_build_metadata_uses_correct_keys(eam_exam):
    """_build_metadata doit lire les clés de global_stats, pas les anciennes clés."""
    orc = EamBilanOrchestrator("EAM TEST 2026")
    gs = orc.engine.global_stats()
    meta = orc._build_metadata(gs)

    assert 'n_copies' in meta
    assert 'mean' in meta
    assert 'median' in meta
    assert 'std' in meta
    assert 'min' in meta
    assert 'max' in meta
    assert 'pct_above_10' in meta
    assert 'distribution' in meta
    assert 'data_quality' in meta

    # Anciennes clés (bug corrigé) ne doivent PAS être présentes
    assert 'total_copies' not in meta
    assert 'mean_score' not in meta
    assert 'std_dev' not in meta


@pytest.mark.django_db
def test_compute_part_stats_empty_when_no_copies(eam_exam):
    """Avec 0 copies, _compute_part_stats retourne {}."""
    orc = EamBilanOrchestrator("EAM TEST 2026")
    stats = orc._compute_part_stats(orc._automatismes_leaves, 'Automatismes')
    assert stats == {}


@pytest.mark.django_db
def test_compute_part_stats_with_copies(eam_exam):
    """Avec copies scorées, _compute_part_stats retourne stats correctes."""
    User = get_user_model()
    user = User.objects.create_user(username="corrtest", password="pass")

    # Créer 3 copies avec scores
    for i in range(3):
        copy = Copy.objects.create(
            exam=eam_exam,
            status=Copy.Status.FINALIZED,
            anonymous_id=f"ANON{i:03d}",
        )
        scores_data = {}
        for j in range(1, 13):
            scores_data[f"q{j}"] = 0.5  # full marks on automatismes
        scores_data["a1"] = 0.5
        scores_data["a2"] = 0.25
        scores_data["b1"] = 0.5
        scores_data["b2"] = 0.75
        scores_data["p1"] = 0.5
        scores_data["p2"] = 1.0
        Score.objects.create(copy=copy, scores_data=scores_data)

    orc = EamBilanOrchestrator("EAM TEST 2026")
    auto_stats = orc._compute_part_stats(orc._automatismes_leaves, 'Automatismes')
    exo_stats = orc._compute_part_stats(orc._exercices_leaves, 'Exercices')

    assert auto_stats['n_copies'] == 3
    assert auto_stats['max_points'] == 6.0
    assert auto_stats['mean'] == 6.0  # full marks
    assert auto_stats['mean_pct'] == 100.0

    assert exo_stats['n_copies'] == 3
    assert exo_stats['max_points'] == 6.0  # 0.5+0.5+1+1+1+2
    assert exo_stats['mean'] > 0


@pytest.mark.django_db
def test_build_exercise_details_correct_structure(eam_exam):
    """_build_exercise_details retourne les exercices sans Automatismes."""
    orc = EamBilanOrchestrator("EAM TEST 2026")
    exercises = orc._build_exercise_details()

    assert len(exercises) == 2  # Exercice 1 + Exercice 2 (pas Automatismes)
    names = [e['name'] for e in exercises]
    assert 'Exercice 1' in names
    assert 'Exercice 2' in names
    assert 'Automatismes' not in names

    ex1 = next(e for e in exercises if e['name'] == 'Exercice 1')
    assert ex1['max_points'] == 3.0  # 0.5+0.5+1+1
    assert len(ex1['subparts']) == 4

    ex2 = next(e for e in exercises if e['name'] == 'Exercice 2')
    assert ex2['max_points'] == 3.0  # 1+2
    assert len(ex2['subparts']) == 2


@pytest.mark.django_db
def test_compute_question_stats_for_leaves_filters_correctly(eam_exam):
    """Les questions Automatismes et Exercices sont correctement filtrées."""
    User = get_user_model()
    # Créer 1 copie scorée
    copy = Copy.objects.create(
        exam=eam_exam,
        status=Copy.Status.FINALIZED,
        anonymous_id="ANON001",
    )
    scores_data = {f"q{i}": 0.5 for i in range(1, 13)}
    scores_data.update({"a1": 0.5, "a2": 0.25, "b1": 0.5, "b2": 0.75, "p1": 1.0, "p2": 2.0})
    Score.objects.create(copy=copy, scores_data=scores_data)

    orc = EamBilanOrchestrator("EAM TEST 2026")
    auto_qs = orc._compute_question_stats_for_leaves(orc._automatismes_leaves)
    exo_qs = orc._compute_question_stats_for_leaves(orc._exercices_leaves)

    assert len(auto_qs) == 12
    assert len(exo_qs) == 6
    # No overlap
    auto_q_ids = {q['question']['id'] for q in auto_qs}
    exo_q_ids = {q['question']['id'] for q in exo_qs}
    assert auto_q_ids.isdisjoint(exo_q_ids)


@pytest.mark.django_db
def test_format_stats_text_no_na_with_data(eam_exam):
    """_format_stats_text ne doit pas contenir 'N/A' si les données sont disponibles."""
    User = get_user_model()
    copy = Copy.objects.create(
        exam=eam_exam,
        status=Copy.Status.FINALIZED,
        anonymous_id="ANON001",
    )
    scores_data = {f"q{i}": 0.5 for i in range(1, 13)}
    scores_data.update({"a1": 0.5, "a2": 0.25, "b1": 0.5, "b2": 0.75, "p1": 1.0, "p2": 2.0})
    Score.objects.create(copy=copy, scores_data=scores_data)

    orc = EamBilanOrchestrator("EAM TEST 2026")
    gs = orc.engine.global_stats()
    auto_s = orc._compute_part_stats(orc._automatismes_leaves, 'Automatismes')
    exo_s = orc._compute_part_stats(orc._exercices_leaves, 'Exercices')
    analytics = {'global_stats': gs, 'auto_stats': auto_s, 'exo_stats': exo_s}
    text = orc._format_stats_text(analytics)

    assert 'N/A' not in text
    assert '1' in text  # n_copies >= 1


@pytest.mark.django_db
def test_forbidden_terms_list_complete():
    """Vérifie que la liste FORBIDDEN_TERMS couvre les cas critiques."""
    term_strs = [t for t, _ in FORBIDDEN_TERMS]
    assert 'DNB' in term_strs
    assert 'brevet' in term_strs
    assert 'cycle 4' in term_strs
    assert '3e' in term_strs
    assert 'collège' in term_strs
    assert 'diplôme national' in term_strs
    assert 'classe de troisième' in term_strs
    assert 'en troisième' in term_strs
