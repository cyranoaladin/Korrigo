"""
Centralized student matching service — single source of truth.
Replaces duplicated matching logic across 6 OCR services.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Any
from difflib import SequenceMatcher

try:
    from Levenshtein import distance as levenshtein_distance
    HAS_LEVENSHTEIN = True
except ImportError:
    HAS_LEVENSHTEIN = False


def _jaro_winkler(s1: str, s2: str) -> float:
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    try:
        from Levenshtein import jaro_winkler as _jw
        return _jw(s1, s2)
    except ImportError:
        return SequenceMatcher(None, s1, s2).ratio()


def _lev_distance(s1: str, s2: str) -> int:
    if HAS_LEVENSHTEIN:
        return levenshtein_distance(s1, s2)
    if len(s1) < len(s2):
        return _lev_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        cur_row = [i + 1]
        for j, c2 in enumerate(s2):
            cur_row.append(min(prev_row[j + 1] + 1, cur_row[j] + 1, prev_row[j] + (c1 != c2)))
        prev_row = cur_row
    return prev_row[-1]


W_DOB = 0.55
W_NAME = 0.25
W_FIRSTNAME = 0.20


@dataclass
class MatchCandidate:
    student_id: Any
    last_name: str
    first_name: str
    date_of_birth: str
    email: str = ''
    total_score: float = 0.0
    name_score: float = 0.0
    firstname_score: float = 0.0
    dob_score: float = 0.0


@dataclass
class MatchDecision:
    decision: str  # 'AUTO', 'SEMI_AUTO', 'MANUAL'
    candidates: List[MatchCandidate] = field(default_factory=list)
    best_score: float = 0.0
    margin: float = 0.0


def normalize_text(text: str) -> str:
    if not text:
        return ''
    text = text.upper()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^A-Z]', '', text)
    return text


def normalize_dob(dob: str) -> str:
    return re.sub(r'[^\d]', '', str(dob)) if dob else ''


def score_dob(ocr_dob: str, csv_dob: str) -> float:
    if not ocr_dob or not csv_dob:
        return 0.0
    if ocr_dob == csv_dob:
        return 1.0
    if len(ocr_dob) >= 6 and len(csv_dob) >= 6:
        min_len = min(len(ocr_dob), len(csv_dob))
        matching = sum(1 for a, b in zip(ocr_dob[:min_len], csv_dob[:min_len]) if a == b)
        return matching / max(len(ocr_dob), len(csv_dob))
    return 0.0


class StudentMatcherService:
    """Single source of truth for OCR -> CSV matching.

    Scoring: DOB (55%) + NOM (25%) + PRENOM (20%).
    Anti-false-AUTO: homonymes same DOB, DOB exact required, name_score >= 0.80.
    """

    def __init__(self, students: list):
        self.students = []
        for s in students:
            entry = dict(s)
            entry['norm_name'] = normalize_text(s.get('last_name', ''))
            entry['norm_first'] = normalize_text(s.get('first_name', ''))
            entry['norm_dob'] = normalize_dob(s.get('date_of_birth', ''))
            entry.setdefault('id', s.get('student_id'))
            self.students.append(entry)

    def match(self, last_name: str, first_name: str,
              date_of_birth: str) -> MatchDecision:
        ocr_name = normalize_text(last_name)
        ocr_first = normalize_text(first_name)
        ocr_dob = normalize_dob(date_of_birth)

        has_name = len(ocr_name) >= 2
        has_first = len(ocr_first) >= 2
        has_dob = len(ocr_dob) >= 6

        candidates = []
        for s in self.students:
            name_sc = _jaro_winkler(ocr_name, s['norm_name']) if has_name else 0.0
            first_sc = _jaro_winkler(ocr_first, s['norm_first']) if has_first else 0.0
            dob_sc = score_dob(ocr_dob, s['norm_dob']) if has_dob else 0.0

            if has_name and has_first and has_dob:
                total = W_DOB * dob_sc + W_NAME * name_sc + W_FIRSTNAME * first_sc
            elif has_name and has_first:
                total = (W_NAME * name_sc + W_FIRSTNAME * first_sc) / (W_NAME + W_FIRSTNAME)
            elif has_name and has_dob:
                total = (W_DOB * dob_sc + W_NAME * name_sc) / (W_DOB + W_NAME)
            elif has_name:
                total = name_sc * 0.6
            elif has_dob and has_first:
                total = (W_DOB * dob_sc + W_FIRSTNAME * first_sc) / (W_DOB + W_FIRSTNAME)
            elif has_dob:
                total = dob_sc * 0.5
            else:
                total = 0.0

            candidates.append(MatchCandidate(
                student_id=s.get('id'),
                last_name=s.get('last_name', ''),
                first_name=s.get('first_name', ''),
                date_of_birth=s.get('date_of_birth', ''),
                email=s.get('email', ''),
                total_score=total,
                name_score=name_sc,
                firstname_score=first_sc,
                dob_score=dob_sc,
            ))

        candidates.sort(key=lambda c: c.total_score, reverse=True)

        best = candidates[0].total_score if candidates else 0.0
        second = candidates[1].total_score if len(candidates) > 1 else 0.0
        margin = best - second
        field_mask = (has_name, has_first, has_dob)

        decision = self._decide(field_mask, best, margin, candidates)

        return MatchDecision(decision=decision, candidates=candidates,
                             best_score=best, margin=margin)

    def _decide(self, field_mask, best, margin, candidates) -> str:
        has_name, has_first, has_dob = field_mask

        if not has_name and not has_first and not has_dob:
            return 'MANUAL'

        # DOB only (no name, no firstname) => insufficient for identification
        if not has_name and not has_first:
            return 'MANUAL'

        # Gate 1: homonymes with same last_name AND same DOB
        if len(candidates) >= 2 and self._is_homonym_risk(candidates[0], candidates[1]):
            return 'SEMI_AUTO' if best >= 0.50 else 'MANUAL'

        # Gate 2: missing DOB => NEVER AUTO
        if not has_dob:
            return 'SEMI_AUTO' if best >= 0.60 and margin >= 0.25 else 'MANUAL'

        # Gate 3: DOB must be exact for AUTO
        if candidates and candidates[0].dob_score < 1.0:
            return 'SEMI_AUTO' if best >= 0.50 else 'MANUAL'

        # Gate 4: name_score must be >= 0.80 for AUTO
        if candidates and has_name and candidates[0].name_score < 0.80:
            return 'SEMI_AUTO' if best >= 0.50 else 'MANUAL'

        # Missing first name: stricter
        if not has_first:
            if best >= 0.85 and margin >= 0.20:
                return 'AUTO'
            return 'SEMI_AUTO' if best >= 0.50 else 'MANUAL'

        # All fields present
        if best >= 0.80 and margin >= 0.15:
            return 'AUTO'
        return 'SEMI_AUTO' if best >= 0.50 else 'MANUAL'

    def _is_homonym_risk(self, c1: MatchCandidate, c2: MatchCandidate) -> bool:
        n1 = normalize_text(c1.last_name)
        n2 = normalize_text(c2.last_name)
        d1 = normalize_dob(c1.date_of_birth)
        d2 = normalize_dob(c2.date_of_birth)
        return n1 == n2 and d1 == d2 and n1 != ''
