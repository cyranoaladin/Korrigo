"""
Tests for StudentMatcherService — anti-false-AUTO, partial fields, homonymes.
CI-BLOCKING: any false AUTO = test failure.
"""
import pytest
from processing.services.student_matcher import (
    StudentMatcherService, normalize_text, normalize_dob, score_dob,
)


@pytest.fixture
def students_basic():
    return [
        {'id': 1, 'last_name': 'DUPONT', 'first_name': 'MARIE',
         'date_of_birth': '15/03/2008', 'email': 'marie@e.fr'},
        {'id': 2, 'last_name': 'MARTIN', 'first_name': 'PIERRE',
         'date_of_birth': '22/11/2007', 'email': 'pierre@e.fr'},
        {'id': 3, 'last_name': 'BERNARD', 'first_name': 'LUC',
         'date_of_birth': '01/06/2008', 'email': 'luc@e.fr'},
    ]


@pytest.fixture
def students_homonymes():
    return [
        {'id': 10, 'last_name': 'MARTIN', 'first_name': 'PIERRE',
         'date_of_birth': '15/03/2008', 'email': 'p.martin@e.fr'},
        {'id': 11, 'last_name': 'MARTIN', 'first_name': 'PAUL',
         'date_of_birth': '15/03/2008', 'email': 'pa.martin@e.fr'},
    ]


@pytest.fixture
def students_same_name_diff_dob():
    return [
        {'id': 20, 'last_name': 'DURAND', 'first_name': 'ALICE',
         'date_of_birth': '10/01/2008', 'email': 'a@e.fr'},
        {'id': 21, 'last_name': 'DURAND', 'first_name': 'BOB',
         'date_of_birth': '25/12/2007', 'email': 'b@e.fr'},
    ]


class TestNormalization:
    def test_normalize_text_accents(self):
        assert normalize_text('Eloise') == 'ELOISE'

    def test_normalize_text_empty(self):
        assert normalize_text('') == ''

    def test_normalize_dob(self):
        assert normalize_dob('15/03/2008') == '15032008'

    def test_normalize_dob_dashes(self):
        assert normalize_dob('15-03-2008') == '15032008'

    def test_score_dob_exact(self):
        assert score_dob('15032008', '15032008') == 1.0

    def test_score_dob_one_off(self):
        s = score_dob('15032008', '15032009')
        assert 0.5 < s < 1.0

    def test_score_dob_empty(self):
        assert score_dob('', '15032008') == 0.0


class TestAutoDecision:
    def test_perfect_match_is_auto(self, students_basic):
        matcher = StudentMatcherService(students_basic)
        result = matcher.match('DUPONT', 'MARIE', '15/03/2008')
        assert result.decision == 'AUTO'
        assert result.best_score > 0.8
        assert result.candidates[0].student_id == 1

    def test_good_match_different_case(self, students_basic):
        matcher = StudentMatcherService(students_basic)
        result = matcher.match('dupont', 'marie', '15/03/2008')
        assert result.decision == 'AUTO'

    def test_slight_ocr_error_still_matches(self, students_basic):
        matcher = StudentMatcherService(students_basic)
        result = matcher.match('DUPOMT', 'MARIE', '15/03/2008')
        assert result.decision in ('AUTO', 'SEMI_AUTO')
        assert result.candidates[0].student_id == 1


class TestAntiFalseAuto:
    """CRITICAL: prevent false AUTO identification."""

    def test_homonymes_same_dob_never_auto(self, students_homonymes):
        matcher = StudentMatcherService(students_homonymes)
        result = matcher.match('MARTIN', 'P', '15/03/2008')
        assert result.decision != 'AUTO', \
            "CRITICAL: homonymes with same DOB must NEVER be AUTO"

    def test_homonymes_same_dob_full_name_never_auto(self, students_homonymes):
        matcher = StudentMatcherService(students_homonymes)
        result = matcher.match('MARTIN', 'PIERRE', '15/03/2008')
        assert result.decision != 'AUTO', \
            "CRITICAL: homonymes with same DOB must NEVER be AUTO"

    def test_dob_one_digit_off_never_auto(self, students_basic):
        matcher = StudentMatcherService(students_basic)
        result = matcher.match('DUPONT', 'MARIE', '15/03/2009')
        assert result.decision != 'AUTO', "DOB not exact => must not be AUTO"

    def test_dob_missing_never_auto(self, students_basic):
        matcher = StudentMatcherService(students_basic)
        result = matcher.match('DUPONT', 'MARIE', '')
        assert result.decision != 'AUTO'

    def test_name_very_different_never_auto(self, students_basic):
        matcher = StudentMatcherService(students_basic)
        result = matcher.match('XXXXXX', 'YYYY', '15/03/2008')
        assert result.decision != 'AUTO'

    def test_same_name_diff_dob_resolves(self, students_same_name_diff_dob):
        matcher = StudentMatcherService(students_same_name_diff_dob)
        result = matcher.match('DURAND', 'ALICE', '10/01/2008')
        assert result.candidates[0].student_id == 20


class TestPartialFields:
    def test_name_only_not_auto(self, students_basic):
        matcher = StudentMatcherService(students_basic)
        result = matcher.match('DUPONT', '', '')
        assert result.decision in ('SEMI_AUTO', 'MANUAL')

    def test_dob_only_is_manual(self, students_basic):
        matcher = StudentMatcherService(students_basic)
        result = matcher.match('', '', '15/03/2008')
        assert result.decision == 'MANUAL'

    def test_no_fields_is_manual(self, students_basic):
        matcher = StudentMatcherService(students_basic)
        result = matcher.match('', '', '')
        assert result.decision == 'MANUAL'

    def test_name_and_dob_no_first(self, students_basic):
        matcher = StudentMatcherService(students_basic)
        result = matcher.match('DUPONT', '', '15/03/2008')
        assert result.decision in ('AUTO', 'SEMI_AUTO')
        assert result.candidates[0].student_id == 1


class TestMatchStructure:
    def test_returns_all_candidates(self, students_basic):
        matcher = StudentMatcherService(students_basic)
        result = matcher.match('DUPONT', 'MARIE', '15/03/2008')
        assert len(result.candidates) == 3

    def test_margin_positive(self, students_basic):
        matcher = StudentMatcherService(students_basic)
        result = matcher.match('DUPONT', 'MARIE', '15/03/2008')
        assert result.margin > 0

    def test_best_score_matches_first(self, students_basic):
        matcher = StudentMatcherService(students_basic)
        result = matcher.match('DUPONT', 'MARIE', '15/03/2008')
        assert result.best_score == result.candidates[0].total_score
