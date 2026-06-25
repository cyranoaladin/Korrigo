"""
Bilan Orchestrator for DNB Report Generation

Coordinates the generation of the complete DNB pedagogical report.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from django.conf import settings
from django.contrib.auth import get_user_model

from .rag_retriever import RAGRetriever, RAG_COLLECTION
from .llm_writer import write, MODEL_DEFAULT, MODEL_PREMIUM
from .analytics_simple import DNBAnalyticsEngine as DNBAnalyticsEngine

User = get_user_model()
logger = logging.getLogger(__name__)


class BilanOrchestrator:
    """
    Orchestrates the generation of the complete DNB pedagogical report.
    """

    def __init__(self, exam_slug: str = 'DNB_2026', rag_collection: Optional[str] = None):
        self.exam_slug = exam_slug
        self.engine = DNBAnalyticsEngine(exam_slug)
        # Use rag_maths_premiere for EAM BLANCHE 2026, otherwise use default
        if 'EAM BLANCHE' in exam_slug:
            self.rag_retriever = RAGRetriever(collection='rag_maths_premiere')
        elif rag_collection:
            self.rag_retriever = RAGRetriever(collection=rag_collection)
        else:
            self.rag_retriever = RAGRetriever(collection=RAG_COLLECTION)

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
                "Vérifiez que des copies sont en statut FINALIZED et qu'un "
                "`grading.Score.scores_data` non vide est présent. "
                f"(copies_total={quality.get('n_copies_total')}, "
                f"finalized={quality.get('n_copies_finalized')}, "
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
        limitations: list[str] = []
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
        def _is_p1_p2(name: str) -> bool:
            low = str(name or "").lower().strip()
            return low.startswith("p1") or low.startswith("p2")

        def _is_exercise(name: str) -> bool:
            return "exercice" in str(name or "").lower()

        def _is_programme_domain(name: str) -> bool:
            low = str(name or "").lower()
            return not (
                _is_p1_p2(low)
                or "partie" in low
                or "exercice" in low
            )

        # Identify which breakdowns are actually available from DB-provided metadata.
        programme_candidates = [(d, p) for d, p in domain_stats.items() if _is_programme_domain(d)]
        exercise_candidates = [(d, p) for d, p in domain_stats.items() if _is_exercise(d)]
        has_competence_breakdown = bool(comp_stats)

        if not programme_candidates:
            limitations.append(
                "Aucun domaine du programme n'est renseigné dans `Exam.grading_structure` "
                "(métadonnées `domain` vides). L'analyse par « domaine du programme » est donc approximée "
                "via les blocs disponibles (exercices / P1-P2) sans simulation."
            )
        if not has_competence_breakdown:
            limitations.append(
                "Les 6 compétences DNB ne sont pas renseignées dans `Exam.grading_structure` "
                "(métadonnées `competence` vides). La section compétences n'affiche pas de pourcentages "
                "pour éviter toute valeur inventée."
            )

        # Choose which "domains" we can meaningfully analyze with LLM:
        # - Prefer programme domains when tagged
        # - Otherwise, fall back to exercises (exclude P1/P2 from this section)
        if programme_candidates:
            domain_breakdown_type = "programme_domains"
            analysis_candidates = programme_candidates
        elif exercise_candidates:
            domain_breakdown_type = "exercises"
            analysis_candidates = exercise_candidates
        else:
            domain_breakdown_type = "mixed"
            analysis_candidates = [
                (d, p)
                for d, p in domain_stats.items()
                if not _is_p1_p2(d) and "partie" not in str(d or "").lower()
            ] or list(domain_stats.items())

        sorted_domains = sorted(analysis_candidates, key=lambda x: x[1])
        weakest = sorted_domains[:2] if len(sorted_domains) >= 2 else sorted_domains[:1]

        # Blank-rate par bloc (domaine si taggé, sinon "Exercice N" via label)
        try:
            def _block_label(q: dict) -> str:
                qinfo = q.get("question") or {}
                dom = str(qinfo.get("domain") or "").strip()
                if dom:
                    return dom
                label = str(qinfo.get("label") or "").strip()
                if " — " in label:
                    return label.split(" — ", 1)[0].strip()
                return label

            block_blank: dict[str, list[float]] = {}
            for q in q_stats:
                block = _block_label(q)
                if not block:
                    continue
                block_blank.setdefault(block, []).append(float(q.get("blank_rate") or 0.0))
            for block, blanks in block_blank.items():
                if not blanks:
                    continue
                avg_blank = round(sum(blanks) / len(blanks), 1)
                if avg_blank >= 10.0:
                    strong_signals.append({
                        "key": f"blank_rate:{block}",
                        "severity": "high",
                        "message": f"Taux de blancs élevé en « {block} » (≈ {avg_blank}% de non-réponses).",
                    })
        except Exception:
            pass

        def _validate_no_percent(text: str) -> str | None:
            t = (text or "").strip()
            if "%" in t or "/20" in t:
                return "contient des pourcentages ou '/20' malgré la contrainte"
            return None

        def _llm_guarded(section: str, *, model: str, max_tokens: int, prompt: str, retries: int = 1) -> str:
            last_error: str | None = None
            for attempt in range(retries + 1):
                txt = _llm(section, model=model, max_tokens=max_tokens, prompt=prompt)
                err = _validate_no_percent(txt)
                if not err:
                    return txt
                last_error = err
                prompt = (
                    prompt
                    + "\n\nIMPORTANT: Ta réponse précédente est invalide (" + err + "). "
                    "Réécris entièrement en respectant STRICTEMENT les contraintes."
                )
            raise RuntimeError(f"Réponse LLM invalide après retries (section={section}): {last_error}")

        # ── 2. SECTION 2 — Domaines/Blocs (LLM = analyse qualitative) ────
        domain_analyses: dict[str, str] = {}
        programme_domains = sorted({d for d, _ in programme_candidates if d})
        seen_norms: set[str] = set()

        for domain, pct in weakest:
            if domain_breakdown_type == "programme_domains":
                rag_ctx = _rag(
                    self.rag_retriever.search_for_domain,
                    domain=domain,
                    issue=f"taux réussite {pct}%"
                )
                auto_ctx = _rag(self.rag_retriever.search_for_automatismes, domain)
                forbidden = [d for d in programme_domains if d != domain]
            else:
                # No tagged programme domain available; use a broader programme context.
                rag_ctx = _rag(
                    self.rag_retriever.search,
                    query=f"programme mathématiques cycle 4 attendus remédiation difficultés {domain}",
                )
                auto_ctx = _rag(
                    self.rag_retriever.search,
                    query="automatismes DNB octobre 2025 mathématiques partie 1 partie 2",
                    top_k=3,
                )
                forbidden = []

            prompt = f"""CONTEXTE PROGRAMME OFFICIEL :
{rag_ctx}

AUTOMATISMES / ÉVALUATION DNB :
{auto_ctx}

DONNÉES (issues de la DB Korrigo) :
Bloc analysé : {domain}
Taux de réussite moyen : {pct}%
Moyenne promo : {global_stats['mean']}/20
Questions liées : {self._q_summary_for_block(q_stats, domain)}

Rédige une analyse pédagogique de ce bloc (8–10 lignes) :
1. Diagnostic précis des difficultés observées
2. Référence explicite aux attendus Éduscol et automatismes DNB non maîtrisés (si disponibles dans le contexte)
3. Proposition d'action concrète pour l'équipe (remédiation, axe prioritaire)

CONTRAINTE STRICTE :
- Ne donne AUCUN chiffre (pas de %, pas de /20). Les chiffres sont affichés ailleurs dans le bilan.
- Analyse exclusivement « {domain} ». Ne parle pas d'autres blocs.
- {"Domaines interdits à citer : " + ", ".join(forbidden) + "." if forbidden else "Si tu ne peux pas être spécifique faute de métadonnées, indique-le explicitement (sans inventer)."}
- Cite au moins une référence du contexte sous la forme [Réf. X] si le contexte en contient.
Destinataire : enseignants correcteurs. Style rapport d'inspection."""

            # Retry if duplicated content (common LLM failure mode)
            for attempt in range(2):
                txt = _llm_guarded(
                    f"s2_domains:{domain}",
                    model=MODEL_DEFAULT,
                    max_tokens=550,
                    prompt=prompt,
                    retries=1,
                )
                norm = " ".join((txt or "").strip().lower().split())
                if norm and norm not in seen_norms:
                    domain_analyses[domain] = txt
                    seen_norms.add(norm)
                    break
                prompt = prompt + "\n\nIMPORTANT: Ne réutilise pas mot pour mot une analyse précédente. Réécris différemment."
            else:
                domain_analyses[domain] = txt

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
                _rag(self.rag_retriever.search_for_competence, c) for c in list(weak_comps.keys())[:3]
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
        reco_ctx = _rag(self.rag_retriever.search_for_remediation, domains_list)

        def _validate_recommendations(text: str) -> tuple[list[str], list[str]]:
            """
            Validate that the LLM output contains the strict [A]/[/A]/[B]/[/B]/[C]/[/C] delimiters
            AND that each section is non-empty.
            """
            missing: list[str] = []
            empty: list[str] = []

            if not isinstance(text, str) or not text.strip():
                return ["A", "B", "C"], ["A", "B", "C"]

            for sec in ("A", "B", "C"):
                if f"[{sec}]" not in text or f"[/{sec}]" not in text:
                    missing.append(sec)

            import re

            for sec in ("A", "B", "C"):
                m = re.search(rf"\\[{sec}\\](.*?)\\[/{sec}\\]", text, flags=re.DOTALL)
                if not m or not (m.group(1) or "").strip():
                    empty.append(sec)

            return missing, empty

        base_reco_prompt = f"""CONTEXTE PÉDAGOGIQUE OFFICIEL :
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
- Cite au moins une référence [Réf. X] si le contexte en contient.
"""

        # Generate recommendations with retries (some models tend to output empty tags on first try).
        recommendations = ""
        last_missing: list[str] = []
        last_empty: list[str] = []
        retry_suffix = ""
        for attempt in range(3):
            recommendations = _llm(
                "s7_recommendations",
                model=MODEL_PREMIUM,   # GPT-4o pour la synthèse finale (ou fallback provider)
                max_tokens=950,
                prompt=(base_reco_prompt + retry_suffix).strip(),
            )
            last_missing, last_empty = _validate_recommendations(recommendations)
            if not last_missing and not last_empty:
                break

            retry_suffix = (
                "\n\nIMPORTANT: Ta réponse précédente est invalide.\n"
                f"- Délimiteurs manquants: {', '.join(last_missing) if last_missing else 'aucun'}\n"
                f"- Sections vides: {', '.join(last_empty) if last_empty else 'aucune'}\n"
                "Réécris ENTIÈREMENT en respectant STRICTEMENT:\n"
                "- conserver exactement [A]/[/A]/[B]/[/B]/[C]/[/C]\n"
                "- chaque bloc doit contenir au moins 3 puces (lignes commençant par '-')\n"
                "Template à remplir (ne pas laisser de blancs) :\n"
                "[A]\n"
                "- Action 1 (délai / responsable / ressource)\n"
                "- Action 2 (délai / responsable / ressource)\n"
                "- Action 3 (délai / responsable / ressource)\n"
                "[/A]\n"
                "[B]\n"
                "- Cible 1 (automatismes / lacune cycle 4)\n"
                "- Cible 2\n"
                "- Cible 3\n"
                "[/B]\n"
                "[C]\n"
                "- Point 1 (barème / cohérence)\n"
                "- Point 2\n"
                "- Point 3\n"
                "[/C]\n"
            )

        if last_missing:
            raise RuntimeError(
                "Format recommandations invalide (délimiteurs manquants). "
                f"Sections manquantes: {', '.join(last_missing)}. "
                "Le LLM doit conserver exactement [A]/[/A]/[B]/[/B]/[C]/[/C]."
            )
        if last_empty:
            # Allow empty sections when using Ollama fallback (BILAN_ALLOW_OLLAMA_FALLBACK)
            if getattr(settings, "BILAN_ALLOW_OLLAMA_FALLBACK", False):
                logger.warning(
                    "Recommandations with empty sections (Ollama fallback enabled). "
                    f"Sections vides: {', '.join(last_empty)}. "
                    "Proceeding with partial content."
                )
            else:
                raise RuntimeError(
                    "Recommandations invalides (sections vides). "
                    f"Sections vides: {', '.join(last_empty)}. "
                    "Chaque bloc [A]/[B]/[C] doit contenir du texte."
                )

        # ── 6. ASSEMBLAGE JSON ─────────────────────────────────────
        generation_time = datetime.now() - start_time
        
        bilan_data = {
            'metadata': {
                'exam': self.exam_slug,
                'generated_at': datetime.now().isoformat(),
                'n_copies': global_stats['n_copies'],
                'generation_time_seconds': generation_time.total_seconds(),
                'llm_model': f"{MODEL_DEFAULT} / {MODEL_PREMIUM}",
                'rag_collection': self.rag_retriever.collection,
                'data_quality': global_stats.get('data_quality', {}),
                'rag_stats': rag_stats,
                'llm_stats': llm_stats,
                'strong_signals': strong_signals,
                'limitations': limitations,
                'breakdowns': {
                    'domain_breakdown_type': domain_breakdown_type,
                    'programme_domains_available': bool(programme_candidates),
                    'competences_available': bool(has_competence_breakdown),
                },
            },
            's1_stats': global_stats,
            's2_domains': {
                'data': domain_stats,
                'analyses': domain_analyses,
                'breakdown_type': domain_breakdown_type,
            },
            's3_questions': q_stats,
            's4_competences': {
                'data': comp_stats,
                'analysis': competence_analysis,
                'available': bool(has_competence_breakdown),
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
            "rag_collection": self.rag_retriever.collection,
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

    def _q_summary_for_block(self, q_stats: List[Dict], block_label: str) -> str:
        """
        Résumé des questions liées à un "bloc" de réussite.

        - Si la question a un `question.domain` taggé, on matche dessus.
        - Sinon, on matche par préfixe de `question.label` (ex: "Exercice 2 — 1").
        """
        block = str(block_label or "").strip()
        if not block:
            return ""

        qs: list[dict] = []
        for q in q_stats:
            qinfo = q.get("question") or {}
            dom = str(qinfo.get("domain") or "").strip()
            if dom and dom == block:
                qs.append(q)
                continue
            label = str(qinfo.get("label") or "").strip()
            if label.startswith(f"{block} —"):
                qs.append(q)

        return " | ".join(
            f"Q{(q.get('question') or {}).get('number', '?')}: {float(q.get('success_rate') or 0.0):.0f}%"
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
