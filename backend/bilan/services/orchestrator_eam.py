"""
Bilan Orchestrator for EAM BLANCHE Report Generation

Coordinates the generation of the complete EAM BLANCHE pedagogical report.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
from django.conf import settings
from django.contrib.auth import get_user_model

from .rag_retriever_premiere import RAGRetrieverPremiere
from .llm_writer import write, MODEL_DEFAULT, MODEL_PREMIUM
from .analytics_simple import DNBAnalyticsEngine as AnalyticsEngine

User = get_user_model()
rag = RAGRetrieverPremiere()


class BilanOrchestratorEAM:
    """
    Orchestrates the generation of the complete EAM BLANCHE pedagogical report.
    """

    def __init__(self, exam_slug: str = 'EAM BLANCHE 2026'):
        self.exam_slug = exam_slug
        self.engine = AnalyticsEngine(exam_slug)
        self.rag_retriever = rag

    def generate(self, requested_by) -> Dict[str, Any]:
        """
        Génère le bilan institutionnel complet.
        Retourne un dict contenant les champs à persister sur `BilanReport`.
        """
        start_time = datetime.now()

        # ── ANALYTIQUES (DB) ────────────────────────────────────────
        global_stats = self.engine.global_stats()
        q_stats = self.engine.stats_by_question()
        domain_stats_dict = self.engine.stats_by_domain()

        # Convert domain stats to list format
        domain_stats = [{'domain': k, 'mean': v} for k, v in domain_stats_dict.items()]
        # Skip at_risk for now to avoid serialization issues
        at_risk = []

        # ── RAG CONTEXT ───────────────────────────────────────────────
        rag_context = {}
        rag_stats = {"hits": 0, "queries": 0}

        try:
            # Récupérer le contexte pour chaque domaine
            for d in domain_stats:
                ctx = self.rag_retriever.search_for_domain(
                    domain=d["domain"],
                    issue=f"moyenne {d.get('mean', 0):.1f}%"
                )
                rag_context[d["domain"]] = ctx
                rag_stats["queries"] += 1
                rag_stats["hits"] += len(ctx.split("---")) if ctx else 0
        except Exception as e:
            print(f"RAG error: {e}")

        # ── LLM SECTIONS ──────────────────────────────────────────────
        sections = {}

        # Section 1: Synthèse globale
        sections["synthese_globale"] = self._llm_guarded(
            self._synthese_globale,
            global_stats,
            rag_context.get("global", "")
        )

        # Section 2: Analyse par domaine
        domain_analysis = []
        for d in domain_stats:
            ctx = rag_context.get(d["domain"], "")
            analysis = self._llm_guarded(
                self._domain_analysis,
                d,
                ctx
            )
            domain_analysis.append({
                "domain": d["domain"],
                "analysis": analysis
            })
        sections["domain_analysis"] = domain_analysis

        # Section 3: Recommandations
        sections["recommandations"] = self._llm_guarded(
            self._recommandations,
            domain_stats,
            at_risk
        )

        # ── STRUCTURE DU BILAN ────────────────────────────────────────
        bilan_data = {
            "sections": sections,
            "metadata": {
                "exam_slug": self.exam_slug,
                "generated_at": datetime.now().isoformat(),
                "generated_by": requested_by.email if requested_by else "system"
            },
            "analytics": {
                "global": global_stats,
                "questions": q_stats,
                "domains": domain_stats_dict,
                "at_risk": at_risk
            },
            "rag_context": rag_context,
            "rag_stats": rag_stats
        }

        generation_time = timedelta(seconds=(datetime.now() - start_time).total_seconds())

        return {
            "json_data": bilan_data,
            "llm_model": f"{MODEL_DEFAULT} / {MODEL_PREMIUM}",
            "rag_collection": "rag_maths_premiere",
            "generation_time": generation_time,
        }

    # ── LLM HELPERS ───────────────────────────────────────────────────

    def _llm_guarded(self, func, *args, **kwargs):
        """Exécute une fonction LLM avec gestion d'erreur."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"LLM error in {func.__name__}: {e}")
            return f"[Erreur LLM: {str(e)}]"

    def _llm(self, model: str, max_tokens: int, prompt: str) -> str:
        return write(model=model, max_tokens=max_tokens, prompt=prompt)

    # ── LLM PROMPTS ─────────────────────────────────────────────────

    def _synthese_globale(self, global_stats, rag_context) -> str:
        prompt = f"""
Synthèse globale de l'évaluation EAM BLANCHE:
- Copies: {global_stats.get('n_copies', 0)}
- Moyenne: {global_stats.get('mean', 0):.1f}/20
- Médiane: {global_stats.get('median', 0):.1f}/20

Contexte pédagogique: {rag_context}

Rédige une synthèse en 2-3 phrases adaptée au niveau Première.
"""
        return self._llm(model=MODEL_DEFAULT, max_tokens=500, prompt=prompt)

    def _domain_analysis(self, domain_data, rag_context) -> str:
        prompt = f"""
Analyse du domaine {domain_data['domain']}:
- Moyenne: {domain_data.get('mean', 0):.1f}%

Contexte: {rag_context}

Analyse en 1-2 phrases adaptée au niveau Première.
"""
        return self._llm(model=MODEL_DEFAULT, max_tokens=300, prompt=prompt)

    def _recommandations(self, domain_stats, at_risk) -> str:
        weak_domains = [d['domain'] for d in domain_stats if d.get('mean', 0) < 50]
        prompt = f"""
Recommandations pédagogiques:
- Domaines en difficulté: {weak_domains}
- Élèves à risque: {len(at_risk)}

Propose 2-3 recommandations concrètes adaptées au niveau Première.
"""
        return self._llm(model=MODEL_DEFAULT, max_tokens=400, prompt=prompt)
