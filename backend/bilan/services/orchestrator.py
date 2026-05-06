"""
Bilan Orchestrator for DNB Report Generation

Coordinates the generation of the complete DNB pedagogical report.
"""

from datetime import datetime
from typing import Dict, Any, List
from django.conf import settings
from django.contrib.auth import get_user_model

from .rag_retriever import RAGRetriever
from .llm_writer import write, MODEL_DEFAULT, MODEL_PREMIUM
from .analytics_simple import DNBAnalyticsEngine as DNBAnalyticsEngine

User = get_user_model()
rag = RAGRetriever()


class BilanOrchestrator:
    """
    Orchestrates the generation of the complete DNB pedagogical report.
    """

    def __init__(self, exam_slug: str = 'DNB_2026'):
        self.exam_slug = exam_slug
        self.engine = DNBAnalyticsEngine(exam_slug)
        self.rag_retriever = rag

    def generate(self, requested_by) -> Dict[str, Any]:
        """
        Génère le bilan institutionnel complet.
        Retourne un dict contenant les champs à persister sur `BilanReport`.
        """
        start_time = datetime.now()

        # ── 1. DONNÉES STATISTIQUES (DB) ───────────────────────────
        global_stats = self.engine.global_stats()
        q_stats = self.engine.stats_by_question()
        comp_stats = self.engine.stats_by_competence()
        domain_stats = self.engine.stats_by_domain()
        corrector_stats = self.engine.inter_corrector_analysis()
        class_stats = self.engine.stats_by_class()
        at_risk = self.engine.at_risk_students()

        # Fail-closed: never generate a Bilan with missing/empty real data.
        n_scored = int(global_stats.get("n_copies") or 0)
        if n_scored <= 0:
            quality = global_stats.get("data_quality") or {}
            raise RuntimeError(
                "Aucune copie notée trouvée pour générer le bilan. "
                "Vérifiez que des copies sont en statut FINALIZED/GRADED et qu'un "
                "`grading.Score.scores_data` non vide est présent. "
                f"(copies_total={quality.get('n_copies_total')}, "
                f"finalized={quality.get('n_copies_finalized')}, "
                f"graded={quality.get('n_copies_graded')}, "
                f"with_scores={quality.get('n_copies_with_scores')})"
            )
        if not q_stats:
            raise RuntimeError(
                "Aucune statistique question-par-question disponible. "
                "Vérifiez `Exam.grading_structure` et l'alignement des clés dans "
                "`Score.scores_data` (ids/positional_id, variantes 'q1' vs '1', etc.)."
            )

        rag_stats = {"calls": 0, "ok": 0, "empty": 0, "unavailable": 0}
        llm_stats = {"calls": 0, "models": [], "sections": []}

        def _rag(fn, *args, **kwargs) -> str:
            rag_stats["calls"] += 1
            txt = fn(*args, **kwargs)
            if not isinstance(txt, str) or not txt.strip():
                rag_stats["empty"] += 1
                if getattr(settings, "BILAN_REQUIRE_RAG", False):
                    raise RuntimeError(
                        "RAG vide (BILAN_REQUIRE_RAG=true). "
                        "Le bilan ne peut pas être généré sans contexte programme."
                    )
                return ""
            low = txt.lower().strip()
            if low.startswith("[rag indisponible"):
                rag_stats["unavailable"] += 1
                if getattr(settings, "BILAN_REQUIRE_RAG", False):
                    raise RuntimeError(
                        "RAG indisponible (BILAN_REQUIRE_RAG=true). "
                        "Configurez RAG_URL (et RAG_TOKEN si nécessaire) et relancez la génération."
                    )
            elif low.startswith("[aucun contexte"):
                rag_stats["empty"] += 1
                if getattr(settings, "BILAN_REQUIRE_RAG", False):
                    raise RuntimeError(
                        "Aucun contexte RAG trouvé (0 hits) alors que BILAN_REQUIRE_RAG=true. "
                        "Vérifiez la collection RAG, l'indexation et la requête."
                    )
            else:
                rag_stats["ok"] += 1
            return txt

        def _llm(section: str, *, model: str, max_tokens: int, prompt: str) -> str:
            llm_stats["calls"] += 1
            llm_stats["models"].append(model)
            llm_stats["sections"].append(section)
            return write(model=model, max_tokens=max_tokens, prompt=prompt)

        def _fmt(v: object, suffix: str = "") -> str:
            if isinstance(v, (int, float)):
                return f"{v:.2f}{suffix}" if suffix else f"{v:.2f}"
            return f"N/A{suffix}"

        # ── Signaux forts (déterministes, basés sur DB) ────────────
        def _pct(part: int, total: int) -> float:
            return round((part / total) * 100, 1) if total else 0.0

        strong_signals: list[dict[str, object]] = []
        n = int(global_stats.get("n_copies") or 0)
        dist = global_stats.get("distribution") or {}

        insuff = int(dist.get("insuffisant") or 0)
        if n and insuff:
            strong_signals.append({
                "key": "insuffisant",
                "severity": "high" if _pct(insuff, n) >= 20 else "medium",
                "message": f"{insuff} élèves insuffisants (<10/20) sur {n} ({_pct(insuff, n)}%).",
            })

        if n and at_risk:
            ar = len(at_risk)
            strong_signals.append({
                "key": "at_risk",
                "severity": "high" if _pct(ar, n) >= 15 else ("medium" if _pct(ar, n) >= 10 else "low"),
                "message": f"{ar} élèves à risque identifiés sur {n} ({_pct(ar, n)}%).",
            })

        # Qualité données: copies sans élève/correcteur
        quality = global_stats.get("data_quality") or {}
        try:
            no_student = int(quality.get("n_scored_without_student") or 0)
            if no_student > 0 and n:
                strong_signals.append({
                    "key": "missing_student_links",
                    "severity": "high" if _pct(no_student, n) >= 20 else "medium",
                    "message": f"{no_student} copies notées sans élève associé (noms indisponibles) sur {n} ({_pct(no_student, n)}%).",
                })
            no_corrector = int(quality.get("n_scored_without_corrector") or 0)
            if no_corrector > 0 and n:
                strong_signals.append({
                    "key": "missing_corrector_links",
                    "severity": "medium",
                    "message": f"{no_corrector} copies notées sans correcteur associé sur {n} ({_pct(no_corrector, n)}%).",
                })
        except Exception:
            pass

        # P1 vs P2 (si présent)
        p1 = domain_stats.get("P1 — Automatismes")
        p2 = domain_stats.get("P2 — Raisonnement")
        if isinstance(p1, (int, float)) and isinstance(p2, (int, float)):
            strong_signals.append({
                "key": "p1_p2",
                "severity": "medium",
                "message": f"Structure épreuve: P1 (6 pts) = {p1}% ; P2 (14 pts) = {p2}%.",
            })

        # Correcteurs (écart notable)
        try:
            worst = next((c for c in (corrector_stats or []) if abs(float(c.get("delta_from_mean") or 0.0)) >= 1.5), None)
            if worst:
                strong_signals.append({
                    "key": "corrector_delta",
                    "severity": "medium",
                    "message": f"Écart inter-correcteur notable (|Δ| ≥ 1,5) pour {worst.get('corrector__name', '—')} (Δ={worst.get('delta_from_mean')}).",
                })
        except Exception:
            pass

        # Enrichissement pour le LLM
        def _is_programme_domain(name: str) -> bool:
            low = str(name or "").lower()
            return not (
                low.startswith("p1")
                or low.startswith("p2")
                or "partie" in low
                or "exercice" in low
            )

        domain_candidates = [(d, p) for d, p in domain_stats.items() if _is_programme_domain(d)]
        if not domain_candidates:
            domain_candidates = list(domain_stats.items())

        sorted_domains = sorted(domain_candidates, key=lambda x: x[1])
        weakest = sorted_domains[:2] if len(sorted_domains) >= 2 else sorted_domains[:1]
        strongest = sorted_domains[-1] if sorted_domains else None

        # Blank-rate par domaine (si métadonnées domaine disponibles)
        try:
            dom_blank: dict[str, list[float]] = {}
            for q in q_stats:
                dom = q.get("question", {}).get("domain") or ""
                if not dom:
                    continue
                dom_blank.setdefault(dom, []).append(float(q.get("blank_rate") or 0.0))
            for dom, blanks in dom_blank.items():
                if not blanks:
                    continue
                avg_blank = round(sum(blanks) / len(blanks), 1)
                if avg_blank >= 10.0:
                    strong_signals.append({
                        "key": f"blank_rate:{dom}",
                        "severity": "high",
                        "message": f"Taux de blancs élevé en « {dom} » (≈ {avg_blank}% de non-réponses).",
                    })
        except Exception:
            pass

        # ── 2. SECTION 2 — Domaines (LLM = analyse qualitative) ────
        domain_analyses = {}
        programme_domains = sorted({d for d, _ in domain_candidates if d})
        for domain, pct in weakest:
            rag_ctx = _rag(
                rag.search_for_domain,
                domain=domain,
                issue=f"taux réussite {pct}%"
            )
            auto_ctx = _rag(rag.search_for_automatismes, domain)
            forbidden = [d for d in programme_domains if d != domain]

            domain_analyses[domain] = _llm(
                f"s2_domains:{domain}",
                model=MODEL_DEFAULT,
                max_tokens=500,
                prompt=f"""CONTEXTE PROGRAMME OFFICIEL :
{rag_ctx}

AUTOMATISMES DNB CONCERNÉS :
{auto_ctx}

DONNÉES :
Domaine : {domain}
Taux de réussite moyen : {pct}%
Moyenne promo : {global_stats['mean']}/20
Questions du domaine : {self._q_summary(q_stats, domain)}

Rédige une analyse pédagogique de ce domaine (8–10 lignes) :
1. Diagnostic précis des lacunes observées
2. Référence explicite aux attendus Éduscol et automatismes DNB non maîtrisés
3. Proposition d'action concrète pour l'équipe (remédiation, axe prioritaire)
CONTRAINTE STRICTE :
- Ne donne AUCUN chiffre (pas de %, pas de /20). Les chiffres sont affichés ailleurs dans le bilan.
- Analyse exclusivement le domaine « {domain} » (ne cite pas d'autres domaines du programme).
- Domaines interdits à citer : {", ".join(forbidden) if forbidden else "aucun"}.
- Cite au moins une référence du contexte sous la forme [Réf. X] si le contexte en contient.
Destinataire : enseignants correcteurs. Style rapport d'inspection."""
            )

        # Garde-fous post-LLM: détecter duplications et fuites de domaines
        try:
            def _norm_txt(t: str) -> str:
                return " ".join((t or "").strip().lower().split())

            norms = [_norm_txt(t) for t in domain_analyses.values() if isinstance(t, str)]
            if len(norms) >= 2 and len(set(norms)) < len(norms):
                strong_signals.append({
                    "key": "llm_domains_duplicated",
                    "severity": "medium",
                    "message": "Alerte qualité: au moins deux analyses LLM de domaines semblent dupliquées (vérifier le contenu).",
                })

            for dom, txt in domain_analyses.items():
                low = (txt or "").lower()
                leaked = [d for d in programme_domains if d and d != dom and d.lower() in low]
                if leaked:
                    strong_signals.append({
                        "key": f"llm_domain_leak:{dom}",
                        "severity": "low",
                        "message": f"Alerte qualité: l'analyse LLM de « {dom} » cite aussi {', '.join(leaked[:3])}{'…' if len(leaked) > 3 else ''}.",
                    })
        except Exception:
            pass

        # ── 3. SECTION 4 — Compétences (LLM = analyse qualitative) ─
        weak_comps = {k: v for k, v in comp_stats.items() if v < 50}
        competence_analysis = ""
        if weak_comps:
            rag_ctx = "\n\n".join(
                _rag(rag.search_for_competence, c) for c in list(weak_comps.keys())[:3]
            )
            competence_analysis = _llm(
                "s4_competences",
                model=MODEL_DEFAULT,
                max_tokens=600,
                prompt=f"""CONTEXTE PROGRAMME :
{rag_ctx}

DONNÉES COMPÉTENCES DNB :
{chr(10).join(f'• {k}: {v}% de maîtrise' for k, v in comp_stats.items())}
Compétences < 50% : {list(weak_comps.keys())}
Score moyen rédaction (2 pts) : {comp_stats.get('communiquer', 'N/A')}%

Analyse la maîtrise des 6 compétences DNB (10–12 lignes) :
- Identifie les compétences structurellement déficitaires
- Explique l'impact sur la note finale (quelles parties de l'épreuve ?)
- Cite les automatismes DNB Oct. 2025 non maîtrisés correspondants
- Recommande 2 axes de travail transversal pour l'équipe
CONTRAINTE STRICTE :
- Ne donne AUCUN chiffre (pas de %, pas de points). Les chiffres sont affichés ailleurs dans le bilan.
- Ne crée pas de nouvelles compétences : ne parle que des compétences listées dans "DONNÉES COMPÉTENCES DNB".
- Cite au moins une référence du contexte sous la forme [Réf. X] si le contexte en contient.
Destinataire : enseignants. Style analytique et opérationnel."""
            )

        # ── 4. SECTION 5 — Correcteurs (LLM = analyse qualitative) ─
        corrector_analysis = ""
        if corrector_stats:
            corrector_analysis = _llm(
                "s5_correctors",
                model=MODEL_DEFAULT,
                max_tokens=500,
                prompt=f"""DONNÉES INTER-CORRECTEURS :
{self._corrector_summary(corrector_stats)}
Moyenne générale : {_fmt(global_stats.get('mean'))}/20
Écart-type général : {_fmt(global_stats.get('std'))}

Rédige une analyse de la cohérence de correction (8 lignes) :
- Identifie les correcteurs avec un écart statistiquement notable (|Δ| > 1,5)
- Évalue la variance inter-correcteurs globale
- Recommande des actions de calibrage si nécessaire
- Ton factuel et professionnel. Pas de jugement de valeur.
CONTRAINTE STRICTE :
- Ne recopie aucun chiffre (les chiffres sont déjà dans le tableau).
Destinataire : responsable de l'évaluation / administration."""
            )

        # ── 5. SECTION 7 — Recommandations ────────────────────────
        # Contexte RAG large pour les recommandations finales
        domains_list = [d[0] for d in weakest]
        reco_ctx = _rag(rag.search_for_remediation, domains_list)

        recommendations = _llm(
            "s7_recommendations",
            model=MODEL_PREMIUM,   # GPT-4o pour la synthèse finale
            max_tokens=900,
            prompt=f"""CONTEXTE PÉDAGOGIQUE OFFICIEL :
{reco_ctx}

SYNTHÈSE DES RÉSULTATS DNB 2026 — {global_stats['n_copies']} copies :
Moyenne : {_fmt(global_stats.get('mean'))}/20 | Médiane : {_fmt(global_stats.get('median'))}/20
Taux réussite ≥10 : {global_stats['pct_above_10']}%
Domaines les plus faibles : {', '.join([f'{d[0]} ({d[1]}%)' for d in weakest])}
Compétences déficitaires : {list(weak_comps.keys())}
Élèves à risque identifiés : {len(at_risk)}

Rédige les recommandations pédagogiques en 3 sous-sections, avec des délimiteurs STRICTS :

[A]
Pour le conseil de classe (avant le DNB officiel si applicable) : 3 actions prioritaires et réalisables (délai, responsable, ressource)
[/A]

[B]
Pour les collègues de Seconde : lacunes du cycle 4 observées + automatismes DNB non acquis à cibler
[/B]

[C]
Pour l'équipe pédagogique : réflexivité sur l'évaluation (difficulté, barème, cohérence)
[/C]

Règles :
- Ne change pas les tags [A]/[/A]/[B]/[/B]/[C]/[/C]
- Chaque bloc : 6–8 lignes maximum
- Cite au moins une référence [Réf. X] si le contexte en contient"""
        )

        # Validation format (anti-regex brittle): exige les délimiteurs [A]/[/A]/[B]/[/B]/[C]/[/C]
        try:
            missing = []
            for sec in ("A", "B", "C"):
                if f"[{sec}]" not in recommendations or f"[/{sec}]" not in recommendations:
                    missing.append(sec)
            if missing:
                raise RuntimeError(
                    "Format recommandations invalide (délimiteurs manquants). "
                    f"Sections manquantes: {', '.join(missing)}. "
                    "Le LLM doit conserver exactement [A]/[/A]/[B]/[/B]/[C]/[/C]."
                )
        except Exception:
            raise

        # ── 6. ASSEMBLAGE JSON ─────────────────────────────────────
        generation_time = datetime.now() - start_time
        
        bilan_data = {
            'metadata': {
                'exam': self.exam_slug,
                'generated_at': datetime.now().isoformat(),
                'n_copies': global_stats['n_copies'],
                'generation_time_seconds': generation_time.total_seconds(),
                'llm_model': f"{MODEL_DEFAULT} / {MODEL_PREMIUM}",
                'rag_collection': 'rag_maths_3e_dnb',
                'data_quality': global_stats.get('data_quality', {}),
                'rag_stats': rag_stats,
                'llm_stats': llm_stats,
                'strong_signals': strong_signals,
            },
            's1_stats': global_stats,
            's2_domains': {
                'data': domain_stats,
                'analyses': domain_analyses,
            },
            's3_questions': q_stats,
            's4_competences': {
                'data': comp_stats,
                'analysis': competence_analysis,
            },
            's5_correctors': {
                'data': corrector_stats,
                'analysis': corrector_analysis,
            },
            's6_profiles': {
                'by_class': class_stats,
                'at_risk': [
                    {
                        'copy_id': s.get('copy_id', ''),
                        'anonymous_id': s.get('anonymous_id', ''),
                        'name': (
                            f"{st.last_name} {st.first_name}".strip()
                            if (st := s.get('student')) else (s.get('anonymous_id', '') or '')
                        ),
                        'class': st.class_name if (st := s.get('student')) else '',
                        'p1': s.get('p1_score', 0),
                        'p2': s.get('p2_score', 0),
                        'total_score': s.get('total_score', 0),
                    }
                    for s in at_risk
                ],
            },
            's7_recommendations': recommendations,
        }

        return {
            "json_data": bilan_data,
            "llm_model": f"{MODEL_DEFAULT} / {MODEL_PREMIUM}",
            "rag_collection": "rag_maths_3e_dnb",
            "generation_time": generation_time,
        }

    # ── HELPERS ───────────────────────────────────────────────────

    def _q_summary(self, q_stats: List[Dict], domain: str) -> str:
        """Résumé des questions pour un domaine donné."""
        qs = [q for q in q_stats if q.get('question', {}).get('domain') == domain]
        return " | ".join(
            f"Q{q['question']['number']}: {q['success_rate']:.0f}%"
            for q in qs
        )

    def _corrector_summary(self, corrector_stats: List[Dict]) -> str:
        """Résumé des données correcteurs."""
        lines = []
        for c in corrector_stats:
            lines.append(
                f"• {c['corrector__name']}: moy={c['mean']}/20, "
                f"n={c['n']}, σ={c['std']}, Δ={c['delta_from_mean']:+.2f}, "
                f"profil={c['severity']}"
            )
        return "\n".join(lines)
