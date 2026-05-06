"""
DNB Analytics Engine (DB-backed)

All statistics are computed from real database data:
- copies in status FINALIZED / GRADED
- `grading.Score.scores_data` (per-question points)

No simulation, no random data, no hardcoded corrector/student lists.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

import unicodedata
import re
from django.db import models

from exams.grading_utils import extract_leaf_questions
from exams.models import Copy, Exam
from grading.models import Score


class DNBAnalyticsEngine:
    """
    Engine for computing DNB statistics and analytics from REAL database data.

    Notes:
    - Global statistics use copies that are graded (FINALIZED or GRADED) and have
      a non-empty `Score.scores_data`.
    - Some advanced pedagogical breakdowns (programme domains, 6 DNB competences)
      require explicit question metadata that may not exist in `grading_structure`.
      Those methods return empty data rather than simulate values.
    """

    def __init__(self, exam_slug: str = "DNB_2026"):
        self.exam = Exam.objects.filter(name=exam_slug).first()
        if not self.exam:
            raise ValueError(f"Exam {exam_slug} not found")

        self.grading_structure = self.exam.grading_structure or []
        self._leaf_questions = extract_leaf_questions(self.grading_structure)
        self._q_max = {q["id"]: float(q.get("points") or 0.0) for q in self._leaf_questions}
        self._q_labels = {q["id"]: (q.get("label") or q["id"]) for q in self._leaf_questions}
        self._q_pos = {q["id"]: q.get("positional_id") for q in self._leaf_questions}
        self._q_domain = {q["id"]: str(q.get("domain") or "").strip() for q in self._leaf_questions}
        self._q_competence = {q["id"]: str(q.get("competence") or "").strip() for q in self._leaf_questions}

        self._cache_pairs: Optional[List[Tuple[Copy, float, Dict[str, Any]]]] = None
        self._cache_quality: Optional[Dict[str, Any]] = None

    # --------------------------------------------------------------------- utils
    @staticmethod
    def _coerce_float(val: object) -> Optional[float]:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            if not val.strip():
                return None
            try:
                return float(val)
            except ValueError:
                return None
        return None

    @classmethod
    def _sum_scores_data(cls, scores_data: object) -> Optional[float]:
        if not isinstance(scores_data, dict) or not scores_data:
            return None
        total = 0.0
        has = False
        for v in scores_data.values():
            fv = cls._coerce_float(v)
            if fv is None:
                continue
            total += fv
            has = True
        return total if has else None

    @staticmethod
    def _norm_text(val: object) -> str:
        """
        Normalise a label (domain/competence) for matching.
        Removes accents, lowercases, trims.
        """
        if not isinstance(val, str):
            return ""
        s = val.strip()
        if not s:
            return ""
        s = unicodedata.normalize("NFD", s)
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        return s.lower().strip()

    def _scored_pairs(self) -> Tuple[List[Tuple[Copy, float, Dict[str, Any]]], Dict[str, Any]]:
        """
        Returns:
          - pairs: [(copy, total_score, scores_data), ...] for graded copies (FINALIZED/GRADED) with scores
          - quality: data availability indicators (counts)
        """
        if self._cache_pairs is not None and self._cache_quality is not None:
            return self._cache_pairs, self._cache_quality

        all_copies = Copy.objects.filter(exam=self.exam)
        graded_qs = (
            all_copies.filter(status__in=[Copy.Status.FINALIZED, Copy.Status.GRADED])
            .select_related("student", "assigned_corrector")
            .prefetch_related("scores")
        )

        pairs: List[Tuple[Copy, float, Dict[str, Any]]] = []
        missing_scores = 0
        empty_scores = 0

        n_with_student = 0
        n_without_student = 0
        n_with_corrector = 0
        n_without_corrector = 0

        for c in graded_qs:
            score_obj = c.scores.first()
            sd = getattr(score_obj, "scores_data", None) if score_obj else None
            total = self._sum_scores_data(sd)
            if score_obj is None:
                missing_scores += 1
                continue
            if total is None:
                empty_scores += 1
                continue
            if c.student_id:
                n_with_student += 1
            else:
                n_without_student += 1
            if c.assigned_corrector_id:
                n_with_corrector += 1
            else:
                n_without_corrector += 1
            pairs.append((c, float(total), sd or {}))

        quality = {
            "n_copies_total": all_copies.count(),
            "n_copies_finalized": all_copies.filter(status=Copy.Status.FINALIZED).count(),
            "n_copies_graded": all_copies.filter(status=Copy.Status.GRADED).count(),
            "n_copies_included_in_bilan": graded_qs.count(),
            "n_copies_with_scores": len(pairs),
            "n_copies_missing_score_row": missing_scores,
            "n_copies_empty_or_invalid_scores": empty_scores,
            "n_scored_with_student": n_with_student,
            "n_scored_without_student": n_without_student,
            "n_scored_with_corrector": n_with_corrector,
            "n_scored_without_corrector": n_without_corrector,
        }
        try:
            from django.conf import settings

            db = (settings.DATABASES or {}).get("default", {})
            quality["db_engine"] = db.get("ENGINE")
            # Safe: helps detect "SQLite vs Postgres" mismatches without exposing credentials
            quality["db_name"] = str(db.get("NAME") or "")
        except Exception:
            pass

        self._cache_pairs = pairs
        self._cache_quality = quality
        return pairs, quality

    def _leaves_under(self, node: Optional[dict]) -> List[dict]:
        if not isinstance(node, dict):
            return []
        leaves = extract_leaf_questions([node])
        return leaves if isinstance(leaves, list) else []

    @classmethod
    def _get_sd_value(cls, scores_data: Dict[str, Any], key: str) -> Optional[float]:
        """
        Best-effort value lookup in `scores_data`.
        Handles minor key format variations (case, leading 'q'/'Q').
        """
        if not key:
            return None

        candidates = [key]
        low = key.lower()
        up = key.upper()
        if low != key:
            candidates.append(low)
        if up != key:
            candidates.append(up)

        # Try alternate "q" prefix toggles (q1 <-> 1) if applicable.
        if low.startswith("q") and len(low) > 1:
            candidates.append(key[1:])
        else:
            candidates.append(f"q{key}")
            candidates.append(f"Q{key}")

        for k in candidates:
            if k in scores_data:
                return cls._coerce_float(scores_data.get(k))
        return None

    @classmethod
    def _score_for_leaf(cls, scores_data: Dict[str, Any], leaf: dict) -> Optional[float]:
        qid = str(leaf.get("id") or "")
        pid = str(leaf.get("positional_id") or "")
        fv = cls._get_sd_value(scores_data, qid)
        if fv is None and pid and pid != qid:
            fv = cls._get_sd_value(scores_data, pid)
        return fv

    @classmethod
    def _sum_for_leaves(cls, scores_data: Dict[str, Any], leaves: Iterable[dict]) -> float:
        total = 0.0
        for leaf in leaves:
            fv = cls._score_for_leaf(scores_data, leaf)
            if fv is None:
                continue
            total += fv
        return total

    @staticmethod
    def _max_for_leaves(leaves: Iterable[dict]) -> float:
        total = 0.0
        for leaf in leaves:
            try:
                total += float(leaf.get("points") or 0.0)
            except (TypeError, ValueError):
                continue
        return total

    def _p1_p2_leaves(self) -> Tuple[List[dict], List[dict]]:
        """
        Best-effort extraction of P1 vs P2 leaves from `grading_structure`.

        For DNB_2026, top-level nodes are typically:
          - Partie 1 (6 pts) — leaf or children
          - Partie 2 (14 pts) — children (exercises/questions)
        """
        gs = self.grading_structure if isinstance(self.grading_structure, list) else []
        if not gs:
            return [], []

        def _label(it: dict) -> str:
            return str(it.get("label") or it.get("title") or it.get("name") or "")

        def _find_node(pred) -> Optional[dict]:
            for it in gs:
                try:
                    if pred(it):
                        return it
                except Exception:
                    continue
            return None

        p1_node = _find_node(lambda it: "partie 1" in _label(it).lower() or str(it.get("id") or "") == "1")
        p2_node = _find_node(
            lambda it: "partie 2" in _label(it).lower()
            or str(it.get("id") or "").lower() in {"partie-2", "partie2", "2"}
        )

        if p1_node is None and len(gs) >= 1:
            p1_node = gs[0]
        if p2_node is None and len(gs) >= 2:
            p2_node = gs[1]

        p1_leaves = self._leaves_under(p1_node)
        p2_leaves = self._leaves_under(p2_node)

        if not p2_leaves and p1_leaves:
            # Fallback: treat all leaf questions minus P1 as P2
            p1_ids = {str(q.get("id") or "") for q in p1_leaves}
            p2_leaves = [q for q in self._leaf_questions if str(q.get("id") or "") not in p1_ids]

        return p1_leaves, p2_leaves

    # ----------------------------------------------------------------- statistics
    def global_stats(self) -> Dict[str, Any]:
        """Statistiques globales (copies FINALIZED/GRADED avec Score)."""
        pairs, quality = self._scored_pairs()
        totals = [t for _, t, _ in pairs]

        if not totals:
            return {
                "n_copies": 0,
                "mean": None,
                "median": None,
                "std": None,
                "min": None,
                "max": None,
                "range": None,
                "pct_above_10": 0,
                "distribution": {"tb": 0, "b": 0, "ab": 0, "p": 0, "insuffisant": 0},
                "data_quality": quality,
            }

        n = len(totals)
        mean = statistics.mean(totals)
        median = statistics.median(totals)
        std = statistics.stdev(totals) if n > 1 else 0.0

        distribution = {
            "tb": sum(1 for s in totals if s >= 16),
            "b": sum(1 for s in totals if 14 <= s < 16),
            "ab": sum(1 for s in totals if 12 <= s < 14),
            "p": sum(1 for s in totals if 10 <= s < 12),
            "insuffisant": sum(1 for s in totals if s < 10),
        }

        return {
            "n_copies": n,
            "mean": round(mean, 2),
            "median": round(median, 2),
            "std": round(std, 2),
            "min": round(min(totals), 2),
            "max": round(max(totals), 2),
            "range": round(max(totals) - min(totals), 2),
            "pct_above_10": round(sum(1 for s in totals if s >= 10) / n * 100, 1) if n else 0,
            "distribution": distribution,
            "data_quality": quality,
        }

    def stats_by_question(self) -> List[Dict[str, Any]]:
        """Statistiques par question (issues du barème + `Score.scores_data`)."""
        pairs, _ = self._scored_pairs()
        if not pairs:
            return []

        all_sd = [sd for _, _, sd in pairs]
        n = len(all_sd)
        if n == 0:
            return []

        results: List[Dict[str, Any]] = []
        # IMPORTANT: preserve the order from `grading_structure` traversal.
        # Sorting question ids is brittle (mix of numeric ids and UUID strings)
        # and can raise TypeError in Python 3.
        for leaf in self._leaf_questions:
            qid = str(leaf.get("id") or "").strip()
            if not qid:
                continue

            mx = float(leaf.get("points") or self._q_max.get(qid, 0.0) or 0.0)
            vals: List[float] = []
            blanks = 0
            pos_id = str(leaf.get("positional_id") or self._q_pos.get(qid) or "")
            for sd in all_sd:
                fv = self._get_sd_value(sd, qid)
                if fv is None and pos_id and pos_id != qid:
                    fv = self._get_sd_value(sd, str(pos_id))
                if fv is None:
                    blanks += 1
                    continue
                vals.append(fv)

            if not vals and blanks == n:
                continue

            mean_q = round(statistics.mean(vals), 2) if vals else 0.0
            zeros_pct = round(sum(1 for v in vals if abs(v) < 1e-9) / len(vals) * 100, 1) if vals else 0.0
            full_pct = (
                round(sum(1 for v in vals if mx > 0 and abs(v - mx) < 0.01) / len(vals) * 100, 1)
                if vals and mx > 0
                else 0.0
            )
            success_pct = (
                round(sum(1 for v in vals if mx > 0 and v >= 0.8 * mx) / len(vals) * 100, 1)
                if vals and mx > 0
                else 0.0
            )
            blank_pct = round(blanks / n * 100, 1) if n else 0.0

            label = leaf.get("label") or self._q_labels.get(qid, qid)
            domain = str(leaf.get("domain") or self._q_domain.get(qid, "") or "").strip()
            competence = str(leaf.get("competence") or self._q_competence.get(qid, "") or "").strip()
            number: str = qid
            if isinstance(label, str):
                stripped = label.strip()
                if stripped.lower().startswith("q") and len(stripped) > 1:
                    number = stripped[1:].strip()
                elif stripped.lower().startswith("partie"):
                    number = stripped
                elif " — " in stripped:
                    # Common pattern: "Exercice 2 — 1" -> number="2.1" for UI readability
                    prefix, suffix = [p.strip() for p in stripped.split(" — ", 1)]
                    # Only apply when suffix is a compact identifier (avoid "Question 1", long text, etc.)
                    if suffix and (" " not in suffix) and re.search(r"\d", suffix):
                        m = re.search(r"exercice\s*(\d+)", prefix, flags=re.IGNORECASE)
                        number = f"{m.group(1)}.{suffix}" if m else suffix

            results.append({
                "question": {
                    "id": qid,
                    "number": number,
                    "label": label,
                    # Domain/competence are optional: filled only if present in grading_structure metadata.
                    "domain": domain,
                    "competence": competence,
                    "max_points": mx,
                },
                "n_attempts": len(vals),
                "mean_score": mean_q,
                "success_rate": success_pct,
                "zero_rate": zeros_pct,
                "blank_rate": blank_pct,
                "full_rate": full_pct,
            })

        return results

    def stats_by_domain(self) -> Dict[str, float]:
        """
        Statistiques de réussite par blocs explicitement présents dans le barème.

        Cela sert de "signaux forts" (ex: P1 vs P2, exercices) sans inventer un
        mapping vers les domaines du programme.
        """
        pairs, _ = self._scored_pairs()
        if not pairs:
            return {}

        gs = self.grading_structure if isinstance(self.grading_structure, list) else []
        if not gs:
            return {}

        domain_stats: Dict[str, float] = {}

        # P1/P2
        p1_leaves, p2_leaves = self._p1_p2_leaves()
        p1_max = self._max_for_leaves(p1_leaves)
        p2_max = self._max_for_leaves(p2_leaves)

        if p1_leaves and p1_max > 0:
            obtained = [self._sum_for_leaves(sd, p1_leaves) for _, _, sd in pairs]
            domain_stats["P1 — Automatismes"] = round(statistics.mean(obtained) / p1_max * 100, 1)
        if p2_leaves and p2_max > 0:
            obtained = [self._sum_for_leaves(sd, p2_leaves) for _, _, sd in pairs]
            domain_stats["P2 — Raisonnement"] = round(statistics.mean(obtained) / p2_max * 100, 1)

        # Programme domains (only if explicit metadata exists)
        dom_to_leaves: Dict[str, List[dict]] = defaultdict(list)
        for leaf in self._leaf_questions:
            dom = str(leaf.get("domain") or "").strip()
            if dom:
                dom_to_leaves[dom].append(leaf)

        for dom, leaves in dom_to_leaves.items():
            mx = self._max_for_leaves(leaves)
            if mx <= 0:
                continue
            obtained = [self._sum_for_leaves(sd, leaves) for _, _, sd in pairs]
            domain_stats[dom] = round(statistics.mean(obtained) / mx * 100, 1)

        # Per-exercise (children under any top-level node)
        def _label(it: dict) -> str:
            return str(it.get("label") or it.get("title") or it.get("name") or "").strip()

        for top in gs:
            children = top.get("children")
            if not isinstance(children, list) or not children:
                continue
            for child in children:
                child_label = _label(child) or str(child.get("id") or "Exercice")
                leaves = self._leaves_under(child)
                mx = self._max_for_leaves(leaves)
                if not leaves or mx <= 0:
                    continue
                obtained = [self._sum_for_leaves(sd, leaves) for _, _, sd in pairs]
                domain_stats[child_label] = round(statistics.mean(obtained) / mx * 100, 1)

        return domain_stats

    def stats_by_competence(self) -> Dict[str, float]:
        """
        Statistiques par compétence DNB.

        Nécessite un mapping question→compétence (chercher/modéliser/…),
        non garanti dans le barème JSON. Si absent, retourne un dict vide.
        """
        pairs, _ = self._scored_pairs()
        if not pairs:
            return {}

        # Extract leaves tagged with competence metadata
        comp_to_leaves: Dict[str, List[dict]] = defaultdict(list)
        for leaf in self._leaf_questions:
            comp_raw = str(leaf.get("competence") or "").strip()
            if not comp_raw:
                continue

            norm = self._norm_text(comp_raw)
            # Map to the 6 DNB competences (tolerant matching)
            mapping = {
                "chercher": "chercher",
                "modeliser": "modéliser",
                "modeliser/": "modéliser",
                "modeliser ": "modéliser",
                "representer": "représenter",
                "raisonner": "raisonner",
                "calculer": "calculer",
                "communiquer": "communiquer",
            }

            chosen = None
            if norm in mapping:
                chosen = mapping[norm]
            else:
                for needle, key in mapping.items():
                    if needle in norm:
                        chosen = key
                        break

            if not chosen:
                # Keep original label if it doesn't match the canonical ones
                chosen = comp_raw

            comp_to_leaves[chosen].append(leaf)

        if not comp_to_leaves:
            return {}

        comp_stats: Dict[str, float] = {}
        for comp, leaves in comp_to_leaves.items():
            mx = self._max_for_leaves(leaves)
            if mx <= 0:
                continue
            obtained = [self._sum_for_leaves(sd, leaves) for _, _, sd in pairs]
            comp_stats[comp] = round(statistics.mean(obtained) / mx * 100, 1)

        # Provide stable ordering for the 6 competences when available
        ordered = {}
        for k in ("chercher", "modéliser", "représenter", "raisonner", "calculer", "communiquer"):
            if k in comp_stats:
                ordered[k] = comp_stats[k]
        # Append any other competence labels
        for k in sorted(comp_stats.keys()):
            if k not in ordered:
                ordered[k] = comp_stats[k]
        return ordered

    def inter_corrector_analysis(self) -> List[Dict[str, Any]]:
        """Analyse inter-correcteurs (copies FINALIZED + scores réels)."""
        pairs, _ = self._scored_pairs()
        if not pairs:
            return []

        all_scores = [t for _, t, _ in pairs]
        global_mean = statistics.mean(all_scores) if all_scores else 0.0

        totals = (
            Copy.objects.filter(exam=self.exam)
            .values(
                "assigned_corrector_id",
                "assigned_corrector__username",
                "assigned_corrector__first_name",
                "assigned_corrector__last_name",
            )
            .annotate(n_total=models.Count("id"))
        )
        total_by_id = {t["assigned_corrector_id"]: t for t in totals if t.get("assigned_corrector_id")}

        corr_scores: Dict[int, List[float]] = defaultdict(list)
        corr_names: Dict[int, str] = {}
        for c, total, _ in pairs:
            if not c.assigned_corrector_id:
                continue
            corr_scores[c.assigned_corrector_id].append(float(total))
            u = c.assigned_corrector
            if u and c.assigned_corrector_id not in corr_names:
                fn = (u.first_name or "").strip()
                ln = (u.last_name or "").strip()
                corr_names[c.assigned_corrector_id] = (f"{fn} {ln}".strip() or u.username)

        analysis: List[Dict[str, Any]] = []
        for corr_id, scores in corr_scores.items():
            if not scores:
                continue
            mean = statistics.mean(scores)
            std = statistics.stdev(scores) if len(scores) > 1 else 0.0
            delta = mean - global_mean
            if abs(delta) <= 0.5:
                severity = "calibré"
            elif delta > 0.5:
                severity = "indulgent"
            else:
                severity = "sévère"

            total_info = total_by_id.get(corr_id) or {}
            analysis.append({
                "corrector": corr_id,
                "corrector__name": corr_names.get(
                    corr_id, total_info.get("assigned_corrector__username", "Inconnu")
                ),
                "n": len(scores),
                "n_total": int(total_info.get("n_total") or len(scores)),
                "mean": round(mean, 2),
                "std": round(std, 2),
                "min": round(min(scores), 2),
                "max": round(max(scores), 2),
                "delta_from_mean": round(delta, 2),
                "severity": severity,
            })

        analysis.sort(key=lambda x: abs(float(x.get("delta_from_mean") or 0.0)), reverse=True)
        return analysis

    def stats_by_class(self) -> List[Dict[str, Any]]:
        """Statistiques par classe (copies FINALIZED avec Score)."""
        pairs, _ = self._scored_pairs()
        if not pairs:
            return []

        class_data: Dict[str, List[float]] = defaultdict(list)
        for copy, total, _ in pairs:
            if not copy.student or not getattr(copy.student, "class_name", None):
                continue
            class_data[str(copy.student.class_name)].append(float(total))

        stats: List[Dict[str, Any]] = []
        for class_name, scores in class_data.items():
            if len(scores) < 2:
                continue
            stats.append({
                "class_name": class_name,
                "n_students": len(scores),
                "mean": round(statistics.mean(scores), 2),
                "std": round(statistics.stdev(scores), 2) if len(scores) > 1 else 0.0,
                "min": round(min(scores), 2),
                "max": round(max(scores), 2),
            })

        return sorted(stats, key=lambda x: x.get("mean") or 0.0, reverse=True)

    def at_risk_students(self) -> List[Dict[str, Any]]:
        """
        Identification élèves à risque (P1 < 2/6 ET P2 < 5/14), sur copies FINALIZED.

        Returns list of dicts including the Student object (if available) and p1/p2/total.
        """
        pairs, _ = self._scored_pairs()
        if not pairs:
            return []

        p1_leaves, p2_leaves = self._p1_p2_leaves()

        at_risk: List[Dict[str, Any]] = []
        for copy, total, sd in pairs:
            p1 = self._sum_for_leaves(sd, p1_leaves) if p1_leaves else 0.0
            p2 = (
                self._sum_for_leaves(sd, p2_leaves)
                if p2_leaves
                else max(0.0, float(total) - float(p1))
            )

            if p1 < 2.0 and p2 < 5.0:
                at_risk.append({
                    "copy_id": str(copy.id),
                    "anonymous_id": copy.anonymous_id,
                    "student": copy.student,
                    "p1_score": round(p1, 1),
                    "p2_score": round(p2, 1),
                    "total_score": round(float(total), 2),
                })

        return sorted(at_risk, key=lambda x: x.get("total_score") or 0.0)
