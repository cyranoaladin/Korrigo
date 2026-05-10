"""
EAM Bilan Orchestrator - Pipeline dédié pour l'épreuve anticipée de mathématiques (Première Spé Maths)

Structure du rapport :
- S0 — Synthèse exécutive (1 page)
- S1 — Tableau de bord (stats globales + Partie A vs Partie B)
- S2A — Partie A (Automatismes/QCM)
- S2B — Partie B (Exercices)
- S3 — Questions (tableau complet question-par-question)
- S4 — Recommandations (3 blocs [A] Automatismes, [B] Raisonnement, [C] Pilotage)

Sources : DB data (copies FINALIZED/GRADED + Score.scores_data) + RAG rag_maths_premiere
"""

import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.contrib.auth import get_user_model
from .rag_retriever import RAGRetriever
from .llm_writer import write, MODEL_DEFAULT, MODEL_PREMIUM
from .analytics_simple import DNBAnalyticsEngine as AnalyticsEngine

User = get_user_model()
logger = logging.getLogger(__name__)

# Forbidden terms for EAM (anti-confusion with DNB)
FORBIDDEN_TERMS = [
    'DNB', 'brevet', 'cycle 4', '3e', 'troisième', '3ème', '3eme',
    'brevet des collèges', 'collège', 'college',
]

# EAM-specific LLM models
EAM_LLM_SYNTHESIS = getattr(settings, 'EAM_LLM_SYNTHESIS', 'openai/gpt-5.5')
EAM_LLM_ANALYSIS = getattr(settings, 'EAM_LLM_ANALYSIS', 'openai/gpt-5.4')


def validate_no_dnb_references(text: str) -> tuple[bool, List[str]]:
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
    
    Pipeline isolé pour éviter toute confusion avec le DNB.
    """
    
    def __init__(self, exam_slug: str = 'EAM BLANCHE 2026'):
        self.exam_slug = exam_slug
        self.engine = AnalyticsEngine(exam_slug)
        self.rag_retriever = RAGRetriever(collection='rag_maths_premiere')
        
    def generate(self, scope: str = 'ETABLISSEMENT', class_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Génère le bilan EAM complet avec la structure S0-S4.
        """
        logger.info(f"EamBilanOrchestrator: Generating bilan for {self.exam_slug}, scope={scope}")
        
        # Fetch analytics data using individual methods
        analytics = {
            'global_stats': self.engine.global_stats(),
            'stats_by_question': self.engine.stats_by_question(),
            'stats_by_domain': self.engine.stats_by_domain(),
            'inter_corrector_analysis': self.engine.inter_corrector_analysis(),
            'stats_by_class': self.engine.stats_by_class(),
            'at_risk_students': self.engine.at_risk_students(),
        }
        
        # Build report sections
        report = {
            'exam_slug': self.exam_slug,
            'scope': scope,
            'class_id': class_id,
            'metadata': self._build_metadata(analytics),
            'sections': {
                'S0': self._generate_s0_synthesis(analytics),
                'S1': self._generate_s1_dashboard(analytics),
                'S2A': self._generate_s2a_partie_automatismes(analytics),
                'S2B': self._generate_s2b_partie_exercices(analytics),
                'S3': self._generate_s3_questions(analytics),
                'S4': self._generate_s4_recommendations(analytics),
            },
            'llm_model': f"{EAM_LLM_SYNTHESIS} / {EAM_LLM_ANALYSIS}",
            'rag_collection': self.rag_retriever.collection,
        }
        
        logger.info(f"EamBilanOrchestrator: Bilan generated successfully")
        return report
    
    def _build_metadata(self, analytics: Dict) -> Dict[str, Any]:
        """Build metadata section."""
        return {
            'total_copies': analytics.get('total_copies', 0),
            'graded_copies': analytics.get('graded_copies', 0),
            'mean_score': analytics.get('mean_score', 0),
            'median_score': analytics.get('median_score', 0),
            'std_dev': analytics.get('std_dev', 0),
            'min_score': analytics.get('min_score', 0),
            'max_score': analytics.get('max_score', 0),
        }
    
    def _generate_s0_synthesis(self, analytics: Dict) -> Dict[str, str]:
        """
        S0 — Synthèse exécutive (1 page).
        6-10 lignes + 5 puces d'actions prioritaires (focus A/B).
        """
        logger.info("EamBilanOrchestrator: Generating S0 synthesis")
        
        # Prepare context
        stats = self._format_stats(analytics)
        rag_ctx = self.rag_retriever.search(
            query="épreuve anticipée mathématiques première synthèse bilan pédagogique",
            top_k=3
        )
        
        # Build prompt
        prompt = f"""Rédige une synthèse exécutive du bilan de l'épreuve anticipée de mathématiques (Première Spé Maths).

CONTEXTE STATISTIQUE :
{stats}

CONTEXTE PÉDAGOGIQUE (RAG) :
{rag_ctx}

CONSIGNE :
- Rédige 6 à 10 lignes de synthèse générale
- Ensuite, liste 5 actions prioritaires (puces) avec focus sur les parties A (Automatismes) et B (Exercices)
- Format : "• [Action prioritaire] (Partie A ou B)"
- IMPORTANT : Ne mentionne JAMAIS DNB, brevet, cycle 4, 3e, troisième
- Adopte un ton professionnel et opérationnel pour direction et professeurs"""
        
        # Generate with validation
        text = self._generate_with_validation(prompt, EAM_LLM_SYNTHESIS, max_tokens=800)
        
        return {
            'type': 'synthesis',
            'title': 'Synthèse Exécutive',
            'content': text,
        }
    
    def _generate_s1_dashboard(self, analytics: Dict) -> Dict[str, Any]:
        """
        S1 — Tableau de bord.
        Stats globales + comparaison Partie A vs Partie B.
        """
        logger.info("EamBilanOrchestrator: Generating S1 dashboard")
        
        # Extract Part A and Part B stats if available
        part_a_stats = analytics.get('part_a_stats', {})
        part_b_stats = analytics.get('part_b_stats', {})
        
        # Build dashboard data
        dashboard = {
            'type': 'dashboard',
            'title': 'Tableau de Bord',
            'global_stats': self._build_metadata(analytics),
            'part_a_stats': part_a_stats,
            'part_b_stats': part_b_stats,
            'comparison': self._compare_part_a_b(part_a_stats, part_b_stats),
        }
        
        return dashboard
    
    def _generate_s2a_partie_automatismes(self, analytics: Dict) -> Dict[str, str]:
        """
        S2A — Partie A (Automatismes/QCM).
        Top réussites/échecs + analyse qualitative + plan d'entraînement.
        """
        logger.info("EamBilanOrchestrator: Generating S2A Partie A")
        
        part_a_data = analytics.get('part_a_details', {})
        top_success = part_a_data.get('top_success', [])
        top_failures = part_a_data.get('top_failures', [])
        
        # RAG context for automatismes
        rag_ctx = self.rag_retriever.search(
            query="automatismes mathématiques première QCM entraînement plan",
            top_k=3
        )
        
        # Build prompt
        prompt = f"""Analyse la Partie A (Automatismes/QCM) de l'épreuve anticipée de mathématiques.

RÉUSSITES (top) :
{self._format_list(top_success)}

ÉCHECS (top) :
{self._format_list(top_failures)}

CONTEXTE PÉDAGOGIQUE (RAG) :
{rag_ctx}

CONSIGNE :
- Analyse qualitative des réussites et échecs
- Propose un plan d'entraînement pour améliorer les automatismes
- Format : 3 paragraphes (analyse réussites, analyse échecs, plan d'entraînement)
- IMPORTANT : Ne mentionne JAMAIS DNB, brevet, cycle 4, 3e, troisième
- Utilise un vocabulaire spécifique à la Première (suites, fonctions, probabilités, géométrie, etc.)"""
        
        text = self._generate_with_validation(prompt, EAM_LLM_ANALYSIS, max_tokens=1000)
        
        return {
            'type': 'partie_automatismes',
            'title': 'Partie A — Automatismes (QCM)',
            'content': text,
            'data': part_a_data,
        }
    
    def _generate_s2b_partie_exercices(self, analytics: Dict) -> Dict[str, Any]:
        """
        S2B — Partie B (Exercices).
        Analyse par exercice puis par sous-parties (A., B., ...) + leviers méthodo.
        """
        logger.info("EamBilanOrchestrator: Generating S2B Partie B")
        
        part_b_data = analytics.get('part_b_details', {})
        exercises = part_b_data.get('exercises', [])
        
        # RAG context for exercises
        rag_ctx = self.rag_retriever.search(
            query="exercices raisonnement mathématiques première méthodologie leviers",
            top_k=3
        )
        
        # Build exercise analysis
        exercise_analysis = []
        for ex in exercises:
            ex_name = ex.get('name', f'Exercice {ex.get("id", "")}')
            subparts = ex.get('subparts', [])
            ex_prompt = f"""Analyse l'exercice "{ex_name}" de la Partie B.

SOUS-PARTIES :
{self._format_subparts(subparts)}

CONTEXTE PÉDAGOGIQUE (RAG) :
{rag_ctx}

CONSIGNE :
- Analyse par sous-partie (A., B., C., ...)
- Identifie les leviers méthodologiques
- Format : 2-3 paragraphes
- IMPORTANT : Ne mentionne JAMAIS DNB, brevet, cycle 4, 3e, troisième"""
            
            ex_text = self._generate_with_validation(ex_prompt, EAM_LLM_ANALYSIS, max_tokens=600)
            exercise_analysis.append({
                'name': ex_name,
                'analysis': ex_text,
                'data': ex,
            })
        
        return {
            'type': 'partie_exercices',
            'title': 'Partie B — Exercices de Raisonnement',
            'exercises': exercise_analysis,
            'data': part_b_data,
        }
    
    def _generate_s3_questions(self, analytics: Dict) -> Dict[str, Any]:
        """
        S3 — Questions.
        Tableau complet question-par-question (existe déjà).
        """
        logger.info("EamBilanOrchestrator: Generating S3 questions")
        
        questions_data = analytics.get('questions_details', {})
        
        return {
            'type': 'questions',
            'title': 'Analyse Question par Question',
            'data': questions_data,
        }
    
    def _generate_s4_recommendations(self, analytics: Dict) -> Dict[str, Any]:
        """
        S4 — Recommandations.
        3 blocs [A] Automatismes, [B] Raisonnement, [C] Pilotage évaluation.
        Sans référence DNB.
        """
        logger.info("EamBilanOrchestrator: Generating S4 recommendations")
        
        # RAG context for recommendations
        rag_auto = self.rag_retriever.search(
            query="recommandations automatismes mathématiques première entraînement",
            top_k=2
        )
        rag_raisonnement = self.rag_retriever.search(
            query="recommandations raisonnement mathématiques première méthodologie",
            top_k=2
        )
        rag_pilotage = self.rag_retriever.search(
            query="pilotage évaluation mathématiques première",
            top_k=2
        )
        
        # Build prompt for each block
        prompt_a = f"""Propose des recommandations pour améliorer les automatismes (Partie A).

CONTEXTE :
{self._format_stats(analytics)}

RAG :
{rag_auto}

CONSIGNE :
- Format : bloc [A] avec 3-4 recommandations concrètes
- IMPORTANT : Ne mentionne JAMAIS DNB, brevet, cycle 4, 3e, troisième"""
        
        prompt_b = f"""Propose des recommandations pour améliorer le raisonnement (Partie B).

CONTEXTE :
{self._format_stats(analytics)}

RAG :
{rag_raisonnement}

CONSIGNE :
- Format : bloc [B] avec 3-4 recommandations concrètes
- IMPORTANT : Ne mentionne JAMAIS DNB, brevet, cycle 4, 3e, troisième"""
        
        prompt_c = f"""Propose des recommandations pour le pilotage de l'évaluation.

CONTEXTE :
{self._format_stats(analytics)}

RAG :
{rag_pilotage}

CONSIGNE :
- Format : bloc [C] avec 3-4 recommandations concrètes pour l'équipe pédagogique
- IMPORTANT : Ne mentionne JAMAIS DNB, brevet, cycle 4, 3e, troisième"""
        
        block_a = self._generate_with_validation(prompt_a, EAM_LLM_SYNTHESIS, max_tokens=400)
        block_b = self._generate_with_validation(prompt_b, EAM_LLM_SYNTHESIS, max_tokens=400)
        block_c = self._generate_with_validation(prompt_c, EAM_LLM_SYNTHESIS, max_tokens=400)
        
        return {
            'type': 'recommendations',
            'title': 'Recommandations',
            'blocks': {
                'A': block_a,
                'B': block_b,
                'C': block_c,
            },
        }
    
    def _generate_with_validation(self, prompt: str, model: str, max_tokens: int = 1000, max_retries: int = 3) -> str:
        """
        Generate text with anti-DNB validation and retry logic.
        """
        for attempt in range(max_retries):
            try:
                text = write(prompt, max_tokens=max_tokens, model=model)
                is_valid, forbidden = validate_no_dnb_references(text)
                
                if is_valid:
                    return text
                else:
                    logger.warning(
                        f"EamBilanOrchestrator: Forbidden terms found (attempt {attempt + 1}/{max_retries}): {forbidden}. Retrying..."
                    )
                    if attempt < max_retries - 1:
                        # Add warning to prompt for next attempt
                        prompt = prompt + "\n\nATTENTION : Votre réponse précédente contenait des termes interdits. Évitez absolument : " + ", ".join(forbidden)
                    else:
                        logger.error(f"EamBilanOrchestrator: Max retries exceeded. Forbidden terms: {forbidden}")
                        return text  # Return last attempt despite validation failure
            except Exception as e:
                logger.error(f"EamBilanOrchestrator: Error in generation (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
        
        return ""
    
    def _format_stats(self, analytics: Dict) -> str:
        """Format analytics stats for prompt."""
        stats = self._build_metadata(analytics)
        lines = [
            f"Total copies : {stats['total_copies']}",
            f"Copies corrigées : {stats['graded_copies']}",
            f"Moyenne : {stats['mean_score']:.2f}/20",
            f"Médiane : {stats['median_score']:.2f}/20",
            f"Écart-type : {stats['std_dev']:.2f}",
            f"Min : {stats['min_score']}/20",
            f"Max : {stats['max_score']}/20",
        ]
        return "\n".join(lines)
    
    def _format_list(self, items: List[Any]) -> str:
        """Format a list for prompt."""
        if not items:
            return "Aucune donnée disponible"
        return "\n".join(f"- {item}" for item in items[:10])
    
    def _format_subparts(self, subparts: List[Dict]) -> str:
        """Format subparts for prompt."""
        if not subparts:
            return "Aucune sous-partie disponible"
        lines = []
        for sp in subparts:
            name = sp.get('name', sp.get('id', ''))
            score = sp.get('mean_score', 0)
            lines.append(f"- {name} : {score:.2f}/20")
        return "\n".join(lines)
    
    def _compare_part_a_b(self, part_a: Dict, part_b: Dict) -> Dict[str, Any]:
        """Compare Part A and Part B stats."""
        return {
            'mean_diff': part_b.get('mean_score', 0) - part_a.get('mean_score', 0),
            'success_rate_diff': part_b.get('success_rate', 0) - part_a.get('success_rate', 0),
            'stronger_part': 'A' if part_a.get('mean_score', 0) > part_b.get('mean_score', 0) else 'B',
        }
