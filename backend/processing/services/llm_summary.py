"""
Service de génération de bilan élève via LLM local (Ollama).
Utilise qwen2.5:32b pour produire un résumé personnalisé à partir de :
- Notes détaillées du barème (Score.scores_data)
- Remarques par question (QuestionRemark)
- Annotations visuelles (Annotation)
- Appréciation générale (Copy.global_appreciation)
- Note finale
"""
import json
import logging
import urllib.request
from django.conf import settings
from exams.models import Copy
from grading.models import Score, QuestionRemark, Annotation

logger = logging.getLogger(__name__)

# Configuration Ollama — accessible via Docker network alias
OLLAMA_URL = getattr(settings, 'OLLAMA_URL', 'http://ollama:11434')
OLLAMA_MODEL = getattr(settings, 'OLLAMA_MODEL', 'llama3.2:latest')
OLLAMA_TIMEOUT = getattr(settings, 'OLLAMA_TIMEOUT', 300)


class LLMSummaryService:
    """
    Génère un bilan personnalisé pour une copie finalisée.
    Lecture seule sur la DB sauf pour Copy.llm_summary.
    """

    @staticmethod
    def generate_summary(copy: Copy) -> str:
        """
        Génère et persiste le bilan LLM pour une copie GRADED.
        Retourne le texte du bilan.
        Raises ValueError si la copie n'est pas GRADED.
        """
        if copy.status != Copy.Status.GRADED:
            raise ValueError(f"Copie {copy.id} n'est pas finalisée (status={copy.status})")

        # --- Collecter les données ---
        context = LLMSummaryService._build_context(copy)
        prompt = LLMSummaryService._build_prompt(context)

        # --- Appel Ollama ---
        try:
            summary = LLMSummaryService._call_ollama(prompt)
        except Exception as e:
            logger.error(f"Erreur LLM pour copie {copy.id}: {e}")
            raise

        # --- Persister le bilan (seul champ modifié) ---
        copy.llm_summary = summary
        copy.save(update_fields=['llm_summary'])

        logger.info(f"Bilan LLM généré pour copie {copy.id} ({len(summary)} chars)")
        return summary

    @staticmethod
    def _build_context(copy: Copy) -> dict:
        """Collecte toutes les données de correction pour le prompt."""
        # 1. Scores du barème
        score_obj = Score.objects.filter(copy=copy).first()
        scores_data = {}
        total_score = 0.0
        if score_obj and score_obj.scores_data:
            scores_data = score_obj.scores_data
            for val in scores_data.values():
                try:
                    total_score += float(val) if val not in (None, '') else 0
                except (TypeError, ValueError):
                    pass

        # 2. Remarques par question
        remarks = {}
        for r in QuestionRemark.objects.filter(copy=copy):
            if r.remark and r.remark.strip():
                remarks[r.question_id] = r.remark.strip()

        # 3. TOUTES les annotations visuelles (commentaires, erreurs, etc.)
        annotations = []
        for a in copy.annotations.all().order_by('page_index'):
            annot_data = {
                'page': a.page_index + 1,
                'type': a.type,
                'content': (a.content or '').strip()[:150],
            }
            if a.score_delta is not None:
                annot_data['score_delta'] = a.score_delta
            annotations.append(annot_data)

        # 4. Appréciation générale
        appreciation = (copy.global_appreciation or '').strip()

        # 5. Structure du barème (exercices/questions)
        grading_structure = None
        if copy.exam and copy.exam.grading_structure:
            grading_structure = copy.exam.grading_structure

        return {
            'anonymous_id': copy.anonymous_id,
            'exam_name': copy.exam.name if copy.exam else '',
            'total_score': round(total_score, 2),
            'scores_detail': scores_data,
            'remarks': remarks,
            'annotations': annotations,
            'appreciation': appreciation,
            'grading_structure': grading_structure,
        }

    @staticmethod
    def _build_prompt(context: dict) -> str:
        """Construit le prompt pour le LLM avec prompt engineering avancé."""

        # --- Scores groupés par exercice ---
        scores_by_exercise = {}
        for q_id, score in sorted(context['scores_detail'].items()):
            ex_num = q_id.split('.')[0] if '.' in q_id else q_id
            if ex_num not in scores_by_exercise:
                scores_by_exercise[ex_num] = []
            scores_by_exercise[ex_num].append((q_id, score))

        scores_block = ""
        for ex_num in sorted(scores_by_exercise.keys(),
                             key=lambda x: (int(x) if x.isdigit() else 999, x)):
            questions = scores_by_exercise[ex_num]
            ex_total = sum(float(s) for _, s in questions
                          if s not in (None, ''))
            scores_block += f"  Exercice {ex_num} (sous-total : {ex_total:.2f}) :\n"
            for q_id, score in questions:
                score_val = score if score not in (None, '') else 0
                scores_block += f"    Q{q_id} : {score_val}\n"

        # --- Remarques du correcteur ---
        remarks_block = ""
        for q_id, remark in sorted(context['remarks'].items()):
            remarks_block += f"  Q{q_id} : {remark}\n"

        # --- Annotations du correcteur ---
        annotations_block = ""
        for a in context['annotations']:
            line = f"  Page {a['page']} [{a['type']}]"
            if a.get('score_delta') is not None:
                line += f" ({a['score_delta']:+d} pts)"
            if a['content']:
                line += f" : {a['content']}"
            annotations_block += line + "\n"

        # --- Structure du barème ---
        structure_block = ""
        if context.get('grading_structure'):
            for ex in context['grading_structure']:
                label = ex.get('label', f"Exercice {ex.get('id', '?')}")
                pts = ex.get('points', '?')
                structure_block += f"  {label} : {pts} points\n"

        prompt = (
            "Tu es un professeur de mathematiques experimente et bienveillant. "
            "Redige un bilan pedagogique personnalise pour un eleve de terminale "
            "a partir de sa copie d'examen corrigee.\n\n"
            "REGLES ABSOLUES :\n"
            "- TUTOIE l'eleve (utilise 'tu', 'ton', 'tes', JAMAIS 'vous' ou 'votre').\n"
            "- Redige en francais uniquement.\n"
            "- Base-toi UNIQUEMENT sur les donnees fournies ci-dessous.\n"
            "- N'invente rien. Ne mentionne pas le numero de copie.\n"
            "- NE SIGNE PAS le bilan (pas de 'Cordialement', pas de '[Votre Nom]', "
            "pas de signature).\n"
            "- Ton encourageant mais honnete. 200 a 350 mots.\n\n"
            "STRUCTURE :\n"
            "1) Appreciation generale (2-3 phrases situant le niveau).\n"
            "2) Points forts (exercices/questions bien reussis, sois precis).\n"
            "3) Points a ameliorer (lacunes, erreurs recurrentes citees par le correcteur).\n"
            "4) Conseils (2-3 conseils concrets et actionnables).\n"
            "5) Encouragement final (une phrase positive).\n\n"
            "=== DONNEES DE LA COPIE ===\n\n"
            f"Examen : {context.get('exam_name', 'Non precise')}\n"
            f"Note finale : {context['total_score']:.2f} / 20\n\n"
        )

        if structure_block:
            prompt += f"Bareme de l'examen :\n{structure_block}\n"

        prompt += (
            f"Notes detaillees par exercice et question :\n"
            f"{scores_block if scores_block else '  Aucune note detaillee'}\n\n"
            f"Remarques du correcteur par question :\n"
            f"{remarks_block if remarks_block else '  Aucune remarque'}\n\n"
            f"Annotations du correcteur sur la copie :\n"
            f"{annotations_block if annotations_block else '  Aucune annotation'}\n\n"
            f"Appreciation generale du correcteur :\n"
            f"  {context['appreciation'] if context['appreciation'] else 'Non renseignee'}\n\n"
            "=== BILAN PEDAGOGIQUE ===\n"
        )

        return prompt

    @staticmethod
    def _call_ollama(prompt: str) -> str:
        """Appelle l'API Ollama et retourne la réponse textuelle."""
        payload = json.dumps({
            'model': OLLAMA_MODEL,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': 0.7,
                'top_p': 0.9,
                'num_predict': 1024,
            }
        }).encode('utf-8')

        url = f"{OLLAMA_URL}/api/generate"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={'Content-Type': 'application/json'}
        )

        try:
            resp = urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT)
            data = json.loads(resp.read())
            response_text = data.get('response', '').strip()
            if not response_text:
                raise ValueError("Réponse LLM vide")
            return response_text
        except urllib.error.URLError as e:
            raise ConnectionError(f"Impossible de contacter Ollama ({OLLAMA_URL}): {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Réponse Ollama invalide: {e}")

    @staticmethod
    def generate_batch(exam_id: str, force: bool = False) -> dict:
        """
        Génère les bilans LLM pour toutes les copies GRADED d'un examen.
        Si force=False, ne régénère pas les bilans déjà existants.
        Retourne un dict avec les compteurs success/skip/error.
        """
        from exams.models import Exam
        exam = Exam.objects.get(id=exam_id)
        copies = Copy.objects.filter(exam=exam, status=Copy.Status.GRADED)

        stats = {'success': 0, 'skipped': 0, 'errors': 0, 'details': []}

        for copy in copies:
            if not force and copy.llm_summary:
                stats['skipped'] += 1
                continue

            try:
                summary = LLMSummaryService.generate_summary(copy)
                stats['success'] += 1
                stats['details'].append({
                    'copy_id': str(copy.id),
                    'anonymous_id': copy.anonymous_id,
                    'status': 'ok',
                    'length': len(summary),
                })
            except Exception as e:
                stats['errors'] += 1
                stats['details'].append({
                    'copy_id': str(copy.id),
                    'anonymous_id': copy.anonymous_id,
                    'status': 'error',
                    'error': str(e)[:200],
                })
                logger.error(f"Bilan LLM échoué pour {copy.id}: {e}")

        logger.info(
            f"Batch LLM terminé pour {exam.name}: "
            f"{stats['success']} OK, {stats['skipped']} skip, {stats['errors']} erreurs"
        )
        return stats
