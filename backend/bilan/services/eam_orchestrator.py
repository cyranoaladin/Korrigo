"""
EAM Bilan Orchestrator - Pipeline dédié pour l'Épreuve Anticipée de Mathématiques (Première Spécialité Maths)

Structure du rapport S0-S4 :
- S0 — Synthèse exécutive (stats globales + 5 actions prioritaires)
- S1 — Tableau de bord (stats globales + Automatismes vs Exercices)
- S2A — Automatismes (12 QCM, 6 pts) — analyse qualitative + plan d'entraînement
- S2B — Exercices (Exercice 1/2/3, 14 pts) — analyse par sous-partie + leviers méthodo
- S3 — Analyse question-par-question (tableau complet)
- S4 — Recommandations (3 blocs : Automatismes / Raisonnement / Pilotage)

Sources exclusives : DB data (copies FINALIZED/GRADED + Score.scores_data) + RAG rag_maths_premiere
Garde-fous : anti-DNB validation + retry automatique si termes interdits détectés
"""

import statistics
import logging
from typing import Dict, List, Optional, Any, Tuple
from django.conf import settings
from .rag_retriever import RAGRetriever
from .llm_writer import write
from .analytics_simple import DNBAnalyticsEngine as AnalyticsEngine
from exams.grading_utils import extract_leaf_questions

logger = logging.getLogger(__name__)

# Forbidden terms — anti-confusion EAM / DNB (exhaustif)
FORBIDDEN_TERMS = [
    'DNB', 'brevet', 'cycle 4', '3e', 'troisième', '3ème', '3eme',
    'brevet des collèges', 'collège', 'college',
    'brevet des colleges', 'diplôme national', 'diplome national',
]

# EAM-specific LLM models (overridable via Django settings)
EAM_LLM_SYNTHESIS = getattr(settings, 'EAM_LLM_SYNTHESIS', 'openai/gpt-5.5')
EAM_LLM_ANALYSIS = getattr(settings, 'EAM_LLM_ANALYSIS', 'openai/gpt-5.4')

# EAM grading structure constants
EAM_NODE_AUTOMATISMES = 'automatismes'
EAM_TOTAL_POINTS = 20.0
EAM_AUTOMATISMES_MAX_POINTS = 6.0
EAM_EXERCICES_MAX_POINTS = 14.0


def validate_no_dnb_references(text: str) -> Tuple[bool, List[str]]:
    """
    Validate that text contains no DNB/cycle 4 references.

    Returns:
        (is_valid, forbidden_terms_found)
    """
    text_lower = text.lower()
    found = []
    for term in FORBIDDEN_TERMS:
        if term.lower() in text_lower:
            found.append(term)
    return len(found) == 0, found


class EamBilanOrchestrator:
    """
    Orchestrator dédié pour le bilan EAM BLANCHE (Première Spé Maths).
    Pipeline 100% isolé — aucune dépendance au pipeline DNB.
    """

    def __init__(self, exam_slug: str = 'EAM BLANCHE 2026'):
        self.exam_slug = exam_slug
        self.engine = AnalyticsEngine(exam_slug)
        self.rag_retriever = RAGRetriever(collection='rag_maths_premiere')
        # Parse EAM grading structure once
        self._automatismes_leaves, self._exercices_leaves = self._parse_eam_structure()

    # ─────────────────────────────────────────── structure EAM ─────────────────

    def _parse_eam_structure(self) -> Tuple[List[dict], List[dict]]:
        """
        Parse la structure barème EAM pour séparer :
        - Automatismes (nœud dont le label contient 'automatisme')
        - Exercices (tous les autres nœuds top-level)

        Returns:
            (automatismes_leaves, exercices_leaves)
        """
        gs = self.engine.grading_structure
        if not gs:
            return [], []

        auto_leaves: List[dict] = []
        exo_leaves: List[dict] = []

        for node in gs:
            label = str(
                node.get('label') or node.get('title') or node.get('name') or ''
            ).lower()
            leaves = extract_leaf_questions([node])
            if EAM_NODE_AUTOMATISMES in label:
                auto_leaves.extend(leaves)
            else:
                exo_leaves.extend(leaves)

        return auto_leaves, exo_leaves

    def _sum_for_leaves(self, scores_data: Dict, leaves: List[dict]) -> float:
        """Somme les points pour un ensemble de feuilles depuis scores_data."""
        return self.engine._sum_for_leaves(scores_data, leaves)

    def _max_for_leaves(self, leaves: List[dict]) -> float:
        """Calcule le barème max pour un ensemble de feuilles."""
        return self.engine._max_for_leaves(leaves)

    # ─────────────────────────────────────────── analytique EAM ────────────────

    def _compute_part_stats(
        self, leaves: List[dict], label: str
    ) -> Dict[str, Any]:
        """
        Calcule les stats (moyenne/médiane/std/taux) pour un sous-ensemble de feuilles.
        Utilisé pour les Automatismes et les Exercices.
        """
        pairs, _ = self.engine._scored_pairs()
        if not pairs or not leaves:
            return {}

        max_pts = self._max_for_leaves(leaves)
        scores = [self._sum_for_leaves(sd, leaves) for _, _, sd in pairs]

        if not scores:
            return {}

        n = len(scores)
        mean_v = statistics.mean(scores)
        median_v = statistics.median(scores)
        std_v = statistics.stdev(scores) if n > 1 else 0.0
        pct_above_half = (
            round(sum(1 for s in scores if s >= max_pts * 0.5) / n * 100, 1)
            if max_pts > 0 else 0.0
        )

        return {
            'label': label,
            'n_copies': n,
            'max_points': round(max_pts, 2),
            'mean': round(mean_v, 2),
            'mean_pct': round(mean_v / max_pts * 100, 1) if max_pts > 0 else 0.0,
            'median': round(median_v, 2),
            'std': round(std_v, 2),
            'min': round(min(scores), 2),
            'max': round(max(scores), 2),
            'pct_above_half': pct_above_half,
        }

    def _compute_question_stats_for_leaves(
        self, leaves: List[dict]
    ) -> List[Dict[str, Any]]:
        """Retourne les stats question-par-question pour un sous-ensemble de feuilles."""
        all_q = self.engine.stats_by_question()
        leaf_ids = {str(l.get('id') or '') for l in leaves}
        return [q for q in all_q if q.get('question', {}).get('id') in leaf_ids]

    def _build_exercise_details(self) -> List[Dict[str, Any]]:
        """
        Construit les détails par exercice (Exercice 1, 2, 3) avec stats
        par sous-partie basées sur la structure du barème EAM.
        """
        gs = self.engine.grading_structure or []
        pairs, _ = self.engine._scored_pairs()
        exercises = []

        for node in gs:
            label = str(
                node.get('label') or node.get('title') or node.get('name') or ''
            )
            label_lower = label.lower()
            if EAM_NODE_AUTOMATISMES in label_lower:
                continue  # skip Automatismes node

            node_leaves = extract_leaf_questions([node])
            if not node_leaves:
                continue

            max_pts = self._max_for_leaves(node_leaves)
            scores = [self._sum_for_leaves(sd, node_leaves) for _, _, sd in pairs]
            n = len(scores)
            mean_v = statistics.mean(scores) if scores else 0.0
            mean_pct = round(mean_v / max_pts * 100, 1) if max_pts > 0 else 0.0

            # Sub-parts = children of the node
            subparts = []
            for child in node.get('children') or []:
                child_label = str(
                    child.get('label') or child.get('title') or child.get('name') or child.get('id') or ''
                )
                child_leaves = extract_leaf_questions([child])
                child_max = self._max_for_leaves(child_leaves)
                child_scores = [
                    self._sum_for_leaves(sd, child_leaves) for _, _, sd in pairs
                ]
                child_mean = statistics.mean(child_scores) if child_scores else 0.0
                child_success = (
                    round(
                        sum(1 for s in child_scores if child_max > 0 and s >= 0.8 * child_max)
                        / len(child_scores) * 100,
                        1,
                    )
                    if child_scores and child_max > 0
                    else 0.0
                )
                subparts.append({
                    'id': child.get('id') or child_label,
                    'label': child_label,
                    'max_points': round(child_max, 2),
                    'mean_score': round(child_mean, 2),
                    'success_rate': child_success,
                    'n_attempts': len(child_scores),
                })

            exercises.append({
                'id': node.get('id') or label,
                'name': label,
                'max_points': round(max_pts, 2),
                'mean_score': round(mean_v, 2),
                'mean_pct': mean_pct,
                'n_copies': n,
                'subparts': subparts,
            })

        return exercises

    # ─────────────────────────────────────────── generate ──────────────────────

    def generate(self, scope: str = 'ETABLISSEMENT', class_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Génère le bilan EAM complet avec la structure S0-S4.
        Toutes les données sont issues de la DB réelle (copies FINALIZED/GRADED).
        """
        logger.info(f"EamBilanOrchestrator: Generating bilan for {self.exam_slug}, scope={scope}")

        # Fetch analytics data
        global_stats = self.engine.global_stats()
        stats_by_question = self.engine.stats_by_question()
        stats_by_domain = self.engine.stats_by_domain()
        inter_corrector = self.engine.inter_corrector_analysis()
        stats_by_class = self.engine.stats_by_class()
        at_risk = self.engine.at_risk_students()

        # EAM-specific analytics
        auto_stats = self._compute_part_stats(self._automatismes_leaves, 'Automatismes')
        exo_stats = self._compute_part_stats(self._exercices_leaves, 'Exercices')
        auto_questions = self._compute_question_stats_for_leaves(self._automatismes_leaves)
        exo_questions = self._compute_question_stats_for_leaves(self._exercices_leaves)
        exercise_details = self._build_exercise_details()

        analytics = {
            'global_stats': global_stats,
            'stats_by_question': stats_by_question,
            'stats_by_domain': stats_by_domain,
            'inter_corrector': inter_corrector,
            'stats_by_class': stats_by_class,
            'at_risk': at_risk,
            'auto_stats': auto_stats,
            'exo_stats': exo_stats,
            'auto_questions': auto_questions,
            'exo_questions': exo_questions,
            'exercise_details': exercise_details,
        }

        report = {
            'exam_slug': self.exam_slug,
            'scope': scope,
            'class_id': class_id,
            'metadata': self._build_metadata(global_stats),
            'sections': {
                'S0': self._generate_s0_synthesis(analytics),
                'S1': self._generate_s1_dashboard(analytics),
                'S2A': self._generate_s2a_automatismes(analytics),
                'S2B': self._generate_s2b_exercices(analytics),
                'S3': self._generate_s3_questions(analytics),
                'S4': self._generate_s4_recommendations(analytics),
            },
            'llm_model': f"{EAM_LLM_SYNTHESIS} / {EAM_LLM_ANALYSIS}",
            'rag_collection': self.rag_retriever.collection,
        }

        logger.info("EamBilanOrchestrator: Bilan generated successfully")
        return report

    # ─────────────────────────────────────────── metadata ──────────────────────

    def _build_metadata(self, global_stats: Dict) -> Dict[str, Any]:
        """Build metadata from real global_stats keys."""
        return {
            'n_copies': global_stats.get('n_copies', 0),
            'mean': global_stats.get('mean'),
            'median': global_stats.get('median'),
            'std': global_stats.get('std'),
            'min': global_stats.get('min'),
            'max': global_stats.get('max'),
            'pct_above_10': global_stats.get('pct_above_10', 0),
            'distribution': global_stats.get('distribution', {}),
            'data_quality': global_stats.get('data_quality', {}),
        }

    # ─────────────────────────────────────────── sections ──────────────────────

    def _generate_s0_synthesis(self, analytics: Dict) -> Dict[str, Any]:
        """S0 — Synthèse exécutive (6-10 lignes + 5 actions prioritaires)."""
        logger.info("EamBilanOrchestrator: Generating S0 synthesis")

        stats_text = self._format_stats_text(analytics)
        rag_ctx = self.rag_retriever.search(
            query="épreuve anticipée mathématiques première synthèse bilan pédagogique résultats",
            top_k=3,
        )

        prompt = f"""Tu es un expert en analyse pédagogique pour l'épreuve anticipée de mathématiques (Première Spécialité Maths, lycée).

DONNÉES STATISTIQUES RÉELLES :
{stats_text}

CONTEXTE PÉDAGOGIQUE :
{rag_ctx}

MISSION :
Rédige une synthèse exécutive (6 à 10 lignes) destinée à la direction et aux professeurs de mathématiques.
Termine par 5 actions prioritaires en puces, en précisant si elles portent sur les Automatismes (Partie A) ou les Exercices de raisonnement (Partie B).

RÈGLES ABSOLUES :
- Ne mentionne JAMAIS : DNB, brevet, cycle 4, 3e, troisième, 3ème, collège
- Parle uniquement de l'épreuve de Première Spécialité Mathématiques
- Utilise les thèmes du programme de Première : suites, fonctions, probabilités, géométrie dans l'espace, trigonométrie, second degré"""

        text = self._generate_with_validation(prompt, EAM_LLM_SYNTHESIS, max_tokens=900)

        return {
            'type': 'synthesis',
            'title': 'Synthèse Exécutive',
            'content': text,
            'stats_snapshot': {
                'n_copies': analytics['global_stats'].get('n_copies', 0),
                'mean': analytics['global_stats'].get('mean'),
                'pct_above_10': analytics['global_stats'].get('pct_above_10'),
            },
        }

    def _generate_s1_dashboard(self, analytics: Dict) -> Dict[str, Any]:
        """S1 — Tableau de bord : stats globales + comparaison Automatismes vs Exercices."""
        logger.info("EamBilanOrchestrator: Generating S1 dashboard")

        auto = analytics.get('auto_stats', {})
        exo = analytics.get('exo_stats', {})

        comparison: Dict[str, Any] = {}
        if auto and exo:
            auto_pct = auto.get('mean_pct', 0)
            exo_pct = exo.get('mean_pct', 0)
            comparison = {
                'auto_mean_pct': auto_pct,
                'exo_mean_pct': exo_pct,
                'diff_pct': round(auto_pct - exo_pct, 1),
                'stronger_part': 'Automatismes' if auto_pct >= exo_pct else 'Exercices',
                'weaker_part': 'Exercices' if auto_pct >= exo_pct else 'Automatismes',
            }

        return {
            'type': 'dashboard',
            'title': 'Tableau de Bord',
            'global_stats': analytics['global_stats'],
            'automatismes_stats': auto,
            'exercices_stats': exo,
            'comparison': comparison,
            'stats_by_class': analytics.get('stats_by_class', []),
            'inter_corrector': analytics.get('inter_corrector', []),
            'at_risk_count': len(analytics.get('at_risk', [])),
        }

    def _generate_s2a_automatismes(self, analytics: Dict) -> Dict[str, Any]:
        """S2A — Automatismes (12 QCM, 6 pts) : analyse qualitative + plan entraînement."""
        logger.info("EamBilanOrchestrator: Generating S2A Automatismes")

        auto_qs = analytics.get('auto_questions', [])
        auto_stats = analytics.get('auto_stats', {})

        # Sort by success_rate to find top/bottom
        sorted_qs = sorted(auto_qs, key=lambda q: q.get('success_rate', 0), reverse=True)
        top_success = sorted_qs[:3]
        top_failures = sorted_qs[-3:][::-1]

        rag_ctx = self.rag_retriever.search(
            query="automatismes QCM mathématiques Première calcul algébrique probabilités fonctions",
            top_k=3,
        )

        top_success_text = self._format_question_list(top_success)
        top_failures_text = self._format_question_list(top_failures)

        prompt = f"""Tu analyses la Partie Automatismes (12 QCM, 6 points) de l'épreuve anticipée de mathématiques de Première Spécialité.

STATISTIQUES AUTOMATISMES :
- Moyenne : {auto_stats.get('mean', 'N/A')}/6 ({auto_stats.get('mean_pct', 'N/A')}%)
- Médiane : {auto_stats.get('median', 'N/A')}/6
- Écart-type : {auto_stats.get('std', 'N/A')}
- % au-dessus de 3/6 : {auto_stats.get('pct_above_half', 'N/A')}%

MEILLEURES RÉUSSITES (QCM) :
{top_success_text}

PRINCIPALES DIFFICULTÉS (QCM) :
{top_failures_text}

RESSOURCES PÉDAGOGIQUES :
{rag_ctx}

MISSION :
1. Analyse qualitative des réussites (paragraphe 1)
2. Analyse qualitative des difficultés (paragraphe 2)
3. Plan d'entraînement ciblé sur les QCM de Première Spécialité (paragraphe 3)

RÈGLES ABSOLUES : Ne mentionne JAMAIS DNB, brevet, cycle 4, 3e, troisième, collège
Cite des thèmes de Première : suites arithmétiques/géométriques, probabilités, loi binomiale, second degré, vecteurs, fonctions dérivées."""

        text = self._generate_with_validation(prompt, EAM_LLM_ANALYSIS, max_tokens=1000)

        return {
            'type': 'automatismes',
            'title': 'Automatismes (Partie A — QCM)',
            'content': text,
            'stats': auto_stats,
            'questions': auto_qs,
            'top_success': top_success,
            'top_failures': top_failures,
        }

    def _generate_s2b_exercices(self, analytics: Dict) -> Dict[str, Any]:
        """S2B — Exercices de raisonnement (3 exercices, 14 pts) : analyse + leviers méthodo."""
        logger.info("EamBilanOrchestrator: Generating S2B Exercices")

        exercise_details = analytics.get('exercise_details', [])
        exo_stats = analytics.get('exo_stats', {})

        rag_ctx = self.rag_retriever.search(
            query="exercices raisonnement mathématiques Première démonstration résolution problème",
            top_k=3,
        )

        exercise_analyses = []
        for ex in exercise_details:
            ex_name = ex.get('name', 'Exercice')
            subparts = ex.get('subparts', [])
            subparts_text = self._format_subparts_text(subparts)

            prompt = f"""Tu analyses l'exercice "{ex_name}" (Partie B — Raisonnement) de l'épreuve anticipée de mathématiques de Première Spécialité.

STATISTIQUES EXERCICE :
- Maximum : {ex.get('max_points', 'N/A')} pts
- Moyenne : {ex.get('mean_score', 'N/A')} pts ({ex.get('mean_pct', 'N/A')}%)
- Nombre de copies : {ex.get('n_copies', 'N/A')}

DÉTAIL PAR SOUS-PARTIE :
{subparts_text}

RESSOURCES PÉDAGOGIQUES :
{rag_ctx}

MISSION :
1. Analyse des résultats par sous-partie (identification des obstacles)
2. Leviers méthodologiques pour améliorer le raisonnement et la rédaction
Format : 2-3 paragraphes concis.

RÈGLES ABSOLUES : Ne mentionne JAMAIS DNB, brevet, cycle 4, 3e, troisième, collège
Parle de Première Spécialité Mathématiques."""

            text = self._generate_with_validation(prompt, EAM_LLM_ANALYSIS, max_tokens=700)
            exercise_analyses.append({
                'id': ex.get('id'),
                'name': ex_name,
                'analysis': text,
                'stats': {
                    'max_points': ex.get('max_points'),
                    'mean_score': ex.get('mean_score'),
                    'mean_pct': ex.get('mean_pct'),
                    'n_copies': ex.get('n_copies'),
                },
                'subparts': subparts,
            })

        return {
            'type': 'exercices',
            'title': 'Exercices de Raisonnement (Partie B)',
            'exercices_stats': exo_stats,
            'exercises': exercise_analyses,
        }

    def _generate_s3_questions(self, analytics: Dict) -> Dict[str, Any]:
        """S3 — Tableau complet question-par-question (Automatismes + Exercices)."""
        logger.info("EamBilanOrchestrator: Generating S3 questions table")

        all_questions = analytics.get('stats_by_question', [])

        return {
            'type': 'questions_table',
            'title': 'Analyse Question par Question',
            'questions': all_questions,
            'n_questions': len(all_questions),
            'auto_questions': analytics.get('auto_questions', []),
            'exo_questions': analytics.get('exo_questions', []),
        }

    def _generate_s4_recommendations(self, analytics: Dict) -> Dict[str, Any]:
        """S4 — Recommandations : 3 blocs [A] Automatismes / [B] Raisonnement / [C] Pilotage."""
        logger.info("EamBilanOrchestrator: Generating S4 recommendations")

        stats_text = self._format_stats_text(analytics)
        auto = analytics.get('auto_stats', {})
        exo = analytics.get('exo_stats', {})

        rag_auto = self.rag_retriever.search(
            query="amélioration automatismes Première Spé entraînement quotidien QCM calcul mental",
            top_k=2,
        )
        rag_raison = self.rag_retriever.search(
            query="raisonnement mathématique Première démonstration rédaction méthodologie exercice",
            top_k=2,
        )
        rag_pilotage = self.rag_retriever.search(
            query="pilotage pédagogique évaluation progression mathématiques lycée",
            top_k=2,
        )

        auto_summary = (
            f"Automatismes : moyenne {auto.get('mean', 'N/A')}/6 "
            f"({auto.get('mean_pct', 'N/A')}%), {auto.get('pct_above_half', 'N/A')}% au-dessus de 3/6"
        )
        exo_summary = (
            f"Exercices : moyenne {exo.get('mean', 'N/A')}/14 "
            f"({exo.get('mean_pct', 'N/A')}%)"
        )

        prompt_a = f"""Tu es expert en pédagogie des mathématiques au lycée (Première Spécialité).

CONTEXTE :
{stats_text}
{auto_summary}

RESSOURCES :
{rag_auto}

Rédige le Bloc [A] — Recommandations pour les Automatismes (3 à 4 recommandations concrètes et actionnables).
Exemples : rituel de 5 min en début de cours, fiches de révision thématiques, etc.
RÈGLES ABSOLUES : Ne mentionne JAMAIS DNB, brevet, cycle 4, 3e, troisième, collège."""

        prompt_b = f"""Tu es expert en pédagogie des mathématiques au lycée (Première Spécialité).

CONTEXTE :
{stats_text}
{exo_summary}

RESSOURCES :
{rag_raison}

Rédige le Bloc [B] — Recommandations pour le Raisonnement et la Rédaction (3 à 4 recommandations concrètes).
Exemples : entraînement à la démonstration, gestion du temps sur exercice, méthode de rédaction, etc.
RÈGLES ABSOLUES : Ne mentionne JAMAIS DNB, brevet, cycle 4, 3e, troisième, collège."""

        prompt_c = f"""Tu es expert en pilotage pédagogique au lycée (Première Spécialité Maths).

CONTEXTE :
{stats_text}

RESSOURCES :
{rag_pilotage}

Rédige le Bloc [C] — Recommandations de Pilotage pour l'équipe pédagogique (3 à 4 recommandations).
Exemples : analyse de la progression par classe, suivi des élèves à risque, harmonisation correction, etc.
RÈGLES ABSOLUES : Ne mentionne JAMAIS DNB, brevet, cycle 4, 3e, troisième, collège."""

        block_a = self._generate_with_validation(prompt_a, EAM_LLM_SYNTHESIS, max_tokens=450)
        block_b = self._generate_with_validation(prompt_b, EAM_LLM_SYNTHESIS, max_tokens=450)
        block_c = self._generate_with_validation(prompt_c, EAM_LLM_SYNTHESIS, max_tokens=450)

        return {
            'type': 'recommendations',
            'title': 'Recommandations Pédagogiques',
            'blocks': {
                'A': {'title': 'Automatismes', 'content': block_a},
                'B': {'title': 'Raisonnement et Rédaction', 'content': block_b},
                'C': {'title': 'Pilotage Pédagogique', 'content': block_c},
            },
        }

    # ─────────────────────────────────────────── LLM + validation ──────────────

    def _generate_with_validation(
        self, prompt: str, model: str, max_tokens: int = 1000, max_retries: int = 3
    ) -> str:
        """Generate text with anti-DNB validation and retry logic."""
        for attempt in range(max_retries):
            try:
                text = write(prompt, max_tokens=max_tokens, model=model)
                is_valid, forbidden = validate_no_dnb_references(text)

                if is_valid:
                    return text

                logger.warning(
                    f"EamBilanOrchestrator: Forbidden terms (attempt {attempt + 1}/{max_retries}): {forbidden}"
                )
                if attempt < max_retries - 1:
                    prompt = (
                        prompt
                        + "\n\nATTENTION : Ta réponse précédente contenait des termes interdits. "
                        + "Reformule sans employer : "
                        + ", ".join(forbidden)
                    )
                else:
                    logger.error(
                        f"EamBilanOrchestrator: Max retries exceeded. Forbidden: {forbidden}"
                    )
                    return text

            except Exception as e:
                logger.error(
                    f"EamBilanOrchestrator: Error attempt {attempt + 1}/{max_retries}: {e}"
                )
                if attempt == max_retries - 1:
                    raise

        return ""

    # ─────────────────────────────────────────── formatters ────────────────────

    def _format_stats_text(self, analytics: Dict) -> str:
        """Format les stats globales + EAM pour les prompts LLM."""
        gs = analytics.get('global_stats', {})
        auto = analytics.get('auto_stats', {})
        exo = analytics.get('exo_stats', {})

        lines = [
            f"Copies analysées : {gs.get('n_copies', 0)}",
            f"Moyenne générale : {gs.get('mean', 'N/A')}/20 ({gs.get('pct_above_10', 'N/A')}% ≥ 10)",
            f"Médiane : {gs.get('median', 'N/A')}/20 | Écart-type : {gs.get('std', 'N/A')}",
            f"Min : {gs.get('min', 'N/A')} | Max : {gs.get('max', 'N/A')}",
        ]
        if auto:
            lines.append(
                f"Automatismes (6 pts) : moy={auto.get('mean', 'N/A')} "
                f"({auto.get('mean_pct', 'N/A')}% du barème)"
            )
        if exo:
            lines.append(
                f"Exercices (14 pts) : moy={exo.get('mean', 'N/A')} "
                f"({exo.get('mean_pct', 'N/A')}% du barème)"
            )
        return "\n".join(lines)

    def _format_question_list(self, questions: List[Dict]) -> str:
        """Format une liste de questions pour les prompts."""
        if not questions:
            return "Aucune donnée"
        lines = []
        for q in questions:
            info = q.get('question', {})
            label = info.get('label') or info.get('number') or info.get('id', '?')
            lines.append(
                f"- {label} : taux réussite {q.get('success_rate', 0)}%, "
                f"moyenne {q.get('mean_score', 0)}/{info.get('max_points', '?')}"
            )
        return "\n".join(lines)

    def _format_subparts_text(self, subparts: List[Dict]) -> str:
        """Format les sous-parties d'un exercice pour les prompts."""
        if not subparts:
            return "Aucune sous-partie disponible"
        lines = []
        for sp in subparts:
            lines.append(
                f"- {sp.get('label', sp.get('id', '?'))} : "
                f"moy={sp.get('mean_score', 0)}/{sp.get('max_points', '?')} pts | "
                f"réussite={sp.get('success_rate', 0)}%"
            )
        return "\n".join(lines)
