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
OLLAMA_MODEL = getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:32b')
OLLAMA_TIMEOUT = getattr(settings, 'OLLAMA_TIMEOUT', 120)


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

        # 3. Annotations visuelles
        annotations = []
        for a in copy.annotations.filter(score_delta__isnull=False).order_by('page_index'):
            annotations.append({
                'page': a.page_index + 1,
                'score_delta': a.score_delta,
                'content': (a.content or '')[:100],
            })

        # 4. Appréciation générale
        appreciation = (copy.global_appreciation or '').strip()

        return {
            'anonymous_id': copy.anonymous_id,
            'total_score': round(total_score, 2),
            'scores_detail': scores_data,
            'remarks': remarks,
            'annotations': annotations,
            'appreciation': appreciation,
        }

    @staticmethod
    def _build_prompt(context: dict) -> str:
        """Construit le prompt pour le LLM."""
        scores_lines = []
        for q_id, score in sorted(context['scores_detail'].items()):
            scores_lines.append(f"  Q{q_id}: {score}")

        remarks_lines = []
        for q_id, remark in sorted(context['remarks'].items()):
            remarks_lines.append(f"  Q{q_id}: {remark}")

        annotations_lines = []
        for a in context['annotations']:
            line = f"  Page {a['page']}: {a['score_delta']:+d} pts"
            if a['content']:
                line += f" — {a['content']}"
            annotations_lines.append(line)

        prompt = f"""Tu es un professeur de mathématiques bienveillant et rigoureux. 
Rédige un bilan personnalisé en français pour un élève à partir de sa copie corrigée.

Le bilan doit :
1. Commencer par un résumé global de la performance (2-3 phrases)
2. Identifier les points forts (questions bien réussies)
3. Identifier les lacunes et erreurs récurrentes
4. Donner des conseils concrets d'amélioration
5. Terminer par un encouragement adapté au niveau

Sois concis (200-300 mots max), constructif et pédagogue.

=== DONNÉES DE LA COPIE ===

Note finale : {context['total_score']:.2f} / 20

Notes détaillées par question :
{chr(10).join(scores_lines) if scores_lines else '  Aucune note détaillée'}

Remarques du correcteur par question :
{chr(10).join(remarks_lines) if remarks_lines else '  Aucune remarque'}

Annotations sur la copie :
{chr(10).join(annotations_lines) if annotations_lines else '  Aucune annotation'}

Appréciation générale du correcteur :
{context['appreciation'] if context['appreciation'] else '  Non renseignée'}

=== BILAN ==="""

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
