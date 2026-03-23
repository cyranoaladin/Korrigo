import hashlib
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from core.auth import UserRole
from exams.models import Copy, Exam
from grading.models import QuestionnaireResponse

User = get_user_model()
logger = logging.getLogger('grading')

QUESTIONNAIRE_BILAN_CACHE_KEY = 'questionnaire_bilan_cache_v1'
QUESTIONNAIRE_BILAN_LOCK_KEY = 'questionnaire_bilan_lock_v1'
QUESTIONNAIRE_BILAN_LOCK_TIMEOUT = 600
OLLAMA_URL = getattr(settings, 'OLLAMA_URL', 'http://ollama:11434')
OLLAMA_MODEL = getattr(settings, 'OLLAMA_MODEL', 'llama3.2:latest')
OLLAMA_TIMEOUT = getattr(settings, 'OLLAMA_TIMEOUT', 300)

BLOCK_OPTS = [
    'Chargement des pages PDF',
    'Placement précis des annotations',
    'Saisie des scores dans le barème',
    'Anonymat (difficile de se repérer)',
    'Navigation entre les copies',
    'Connexion réseau instable',
    'Rien — la correction était fluide',
]

KORRIGO_TECH_CONTEXT = """
Korrigo PMF est une plateforme de correction numérique de copies du bac et de bac blanc.

Contexte réel de production :
- Backend Django + DRF
- Frontend Vue 3
- PostgreSQL + Redis + Celery
- Reverse proxy Nginx
- Génération IA locale via Ollama
- Correction de copies anonymisées avec barème interactif, annotations, remarques, dashboards correcteurs et élèves
- Déploiement réel BB 2026 avec 209 copies et 8 correcteurs effectivement affectés aux copies

Fonctionnalités importantes à prendre en compte :
- visualisation page par page des copies rasterisées
- annotations visuelles et textuelles
- barème interactif
- autosave et reprise après incident
- anonymisation stricte pendant la correction
- export PDF corrigé et portail élève

Le bilan à produire doit rester factuel, professionnel, prudent, et croiser les réponses du questionnaire avec la réalité fonctionnelle de la plateforme.
""".strip()


def build_display_name(user):
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.username


def get_questionnaire_eligible_queryset():
    assigned_corrector_ids = list(
        Copy.objects.exclude(assigned_corrector__isnull=True)
        .values_list('assigned_corrector_id', flat=True)
        .distinct()
    )
    exam_corrector_ids = list(
        Exam.objects.exclude(correctors__isnull=True)
        .values_list('correctors__id', flat=True)
        .distinct()
    )
    eligible_ids = {user_id for user_id in assigned_corrector_ids + exam_corrector_ids if user_id}
    if eligible_ids:
        return User.objects.filter(id__in=eligible_ids, is_active=True).distinct()
    return User.objects.filter(groups__name=UserRole.TEACHER, is_active=True).exclude(
        groups__name=UserRole.ADMIN
    ).distinct()


def build_questionnaire_summary():
    eligible_queryset = get_questionnaire_eligible_queryset()
    total_eligible = eligible_queryset.count()
    responses_count = QuestionnaireResponse.objects.filter(
        user_id__in=eligible_queryset.values('id')
    ).distinct().count()
    completion_rate = round((responses_count / total_eligible) * 100, 1) if total_eligible else 0
    remaining_count = max(total_eligible - responses_count, 0)
    return {
        'responses_count': responses_count,
        'total_eligible': total_eligible,
        'remaining_count': remaining_count,
        'completion_rate': completion_rate,
        'is_available': total_eligible > 0 and responses_count >= total_eligible,
    }


def serialize_questionnaire_responses():
    eligible_ids = list(get_questionnaire_eligible_queryset().values_list('id', flat=True))
    responses = QuestionnaireResponse.objects.select_related('user').filter(
        user_id__in=eligible_ids
    ).order_by('-updated_at')
    serialized = []
    for item in responses:
        serialized.append({
            'user_id': item.user_id,
            'username': item.user.username,
            'display_name': build_display_name(item.user),
            'email': item.user.email,
            'submitted_at': item.updated_at.isoformat(),
            'answers': item.payload,
        })
    return serialized


def build_questionnaire_participants(serialized_responses=None):
    eligible_users = list(get_questionnaire_eligible_queryset().order_by('first_name', 'last_name', 'username'))
    responded_map = {
        item['user_id']: item
        for item in (serialized_responses or serialize_questionnaire_responses())
    }
    responded = []
    pending = []

    for user in eligible_users:
        payload = {
            'user_id': user.id,
            'username': user.username,
            'display_name': build_display_name(user),
            'email': user.email,
        }
        if user.id in responded_map:
            payload['submitted_at'] = responded_map[user.id]['submitted_at']
            responded.append(payload)
        else:
            pending.append(payload)

    responded.sort(key=lambda item: item.get('submitted_at') or '', reverse=True)

    return {
        'responded': responded,
        'pending': pending,
    }


def _compute_stats(rows, total_eligible):
    if not rows:
        return {}

    def avg(key):
        values = [int(row[key]) for row in rows if row.get(key) not in (None, '', 'null')]
        return round(sum(values) / len(values), 2) if values else None

    def dist(key, options):
        return {option: sum(1 for row in rows if row.get(key) == option) for option in options}

    def multi(key, options):
        return {option: sum(1 for row in rows if option in (row.get(key) or [])) for option in options}

    nps = [int(row['q53']) for row in rows if row.get('q53') not in (None, '', 'null')]
    promoters = sum(1 for value in nps if value >= 9)
    passives = sum(1 for value in nps if 7 <= value <= 8)
    detractors = sum(1 for value in nps if value <= 6)

    ergonomics = {
        'Clarte_interface': avg('q11'),
        'Navigation_PDF': avg('q12'),
        'Bareme_interactif': avg('q13'),
        'Zoom_deplacement': avg('q14'),
    }
    ergonomics_values = [value for value in ergonomics.values() if value is not None]
    ergonomics_global = round(sum(ergonomics_values) / len(ergonomics_values), 2) if ergonomics_values else None

    return {
        'nb_reponses': len(rows),
        'taux_participation': f"{len(rows)}/{total_eligible}",
        'correcteurs_ayant_repondu': [row.get('_display_name') or row.get('_uid') for row in rows],
        'ergonomie_par_dimension': ergonomics,
        'ergonomie_score_global': ergonomics_global,
        'prise_en_main_rapidite': dist('q15', [
            'Moins de 15 minutes', '15 à 30 minutes', '30 minutes à 1 heure',
            "Plus d'1 heure", "Je ne me suis jamais vraiment senti(e) à l'aise"
        ]),
        'utilite_outils': {
            'Annotation_commentaires': dist('q21', ['Inutile', 'Utile', 'Indispensable']),
            'Surlignage': dist('q22', ['Inutile', 'Utile', 'Indispensable']),
            'Raccourcis_clavier': dist('q23', ['Inutile', 'Utile', 'Indispensable']),
            'Banque_commentaires': dist('q24', ['Inutile', 'Utile', 'Indispensable']),
        },
        'blocages_signales': multi('q25', BLOCK_OPTS),
        'securite_ressentie_pendant_correction': avg('q31'),
        'confiance_apres_incident': dist('q32', [
            'Renforcée — la récupération complète prouve la résilience',
            'Inchangée — erreur humaine, pas un défaut structurel',
            'Légèrement ébranlée — le risque zéro n\'existe pas',
            'Sérieusement affectée — difficile de corriger sereinement',
        ]),
        'confiance_mesures_correctives': avg('q33'),
        'appreciation_postmortem': avg('q34'),
        'gain_temps_vs_papier_moy': avg('q41'),
        'qualite_retours_eleves_moy': avg('q42'),
        'effet_anonymat': dist('q43', [
            'Oui, je me sens plus objectif(ve) sans voir le nom',
            "Peu d'effet — j'aurais corrigé pareil",
            "L'anonymat m'a parfois perturbé(e) (difficile de se repérer)",
            'Difficile à évaluer sur un seul exercice',
        ]),
        'rigueur_correction': dist('q44', [
            'Plus rigoureux(se) — les outils m\'ont aidé à être plus précis(e)',
            'Identique à la correction papier',
            'Moins rigoureux(se) — l\'interface distrait ou fatigue',
        ]),
        'recommandation_prochain_bac': dist('q51', [
            "Absolument — c'est l'avenir de la correction",
            'Oui, avec quelques améliorations techniques',
            'Plutôt non — j\'attends une version plus stable',
            'Non — je reste sur la correction papier',
        ]),
        'types_evals_adaptes': multi('q52', [
            'Bac Blanc (examens importants)', 'Devoirs communs inter-classes',
            'Contrôles continus', 'NSI / Projets numériques', 'Épreuves de fin de semestre',
        ]),
        'nps_score_moyen': round(sum(nps) / len(nps), 1) if nps else None,
        'nps_index': round(((promoters - detractors) / len(nps)) * 100) if nps else None,
        'nps_promoteurs': promoters,
        'nps_passifs': passives,
        'nps_detracteurs': detractors,
        'sentiment_global': dist('q61', [
            'Enthousiaste — je suis convaincu(e) par l\'outil',
            'Satisfait(e) — bon outil, quelques ajustements à faire',
            'Mitigé(e) — autant d\'avantages que d\'inconvénients',
            'Déçu(e) — les promesses ne sont pas au rendez-vous',
            'Neutre — je n\'ai pas d\'opinion tranchée',
        ]),
        'verbatims_fonctionnalites_manquantes': [row['q54'] for row in rows if str(row.get('q54', '')).strip()],
        'verbatims_bugs': [row['q55'] for row in rows if str(row.get('q55', '')).strip()],
        'commentaires_libres': [
            {'auteur': row.get('_display_name') or row.get('_uid'), 'texte': row['q62']}
            for row in rows if str(row.get('q62', '')).strip()
        ],
    }


def _build_prompt(stats, total_eligible):
    return f"""Tu rédiges le bilan officiel du questionnaire correcteurs de Korrigo PMF.

Contrainte absolue : tu dois t'appuyer uniquement sur les données fournies et sur le contexte technique ci-dessous.
Le questionnaire existe déjà en production, les réponses sont réelles, et le bilan doit rester fidèle au ressenti des correcteurs.

{KORRIGO_TECH_CONTEXT}

Données agrégées du questionnaire ({stats.get('nb_reponses', 0)}/{total_eligible} réponses) :
{json.dumps(stats, ensure_ascii=False, indent=2)}

Rédige uniquement du HTML simple avec ces balises autorisées : h2, h3, p, ul, li, strong, em, blockquote, table, thead, tbody, tr, th, td.
N'ajoute ni html, ni body, ni script, ni style.

Structure attendue :
- Synthèse exécutive
- Ergonomie et prise en main
- Outils de correction
- Fiabilité et incident
- Impact pédagogique
- Score NPS et recommandation
- Attentes exprimées par les correcteurs
- Recommandations priorisées
- Conclusion

Le ton doit être professionnel, sobre, factuel, et prudent.
"""


def _call_ollama(prompt):
    payload = json.dumps({
        'model': OLLAMA_MODEL,
        'prompt': prompt,
        'stream': False,
        'options': {
            'temperature': 0.4,
            'top_p': 0.9,
            'num_predict': 3000,
        },
    }).encode('utf-8')
    request = urllib.request.Request(
        f'{OLLAMA_URL}/api/generate',
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    response = urllib.request.urlopen(request, timeout=OLLAMA_TIMEOUT)
    data = json.loads(response.read())
    text = (data.get('response') or '').strip()
    if not text:
        raise ValueError('Réponse Ollama vide')
    return text


def _compute_fingerprint(serialized_responses, summary):
    payload = {
        'eligible_total': summary['total_eligible'],
        'responses': [
            {
                'user_id': item['user_id'],
                'submitted_at': item['submitted_at'],
                'answers': item['answers'],
            }
            for item in serialized_responses
        ],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def get_questionnaire_bilan_state(serialized_responses, summary):
    fingerprint = _compute_fingerprint(serialized_responses, summary)
    cached = cache.get(QUESTIONNAIRE_BILAN_CACHE_KEY)
    if cached and cached.get('fingerprint') == fingerprint:
        return cached
    lock_value = cache.get(QUESTIONNAIRE_BILAN_LOCK_KEY)
    if lock_value == fingerprint:
        return {
            'status': 'pending',
            'html': '',
            'generated_at': None,
            'error': '',
            'auto': True,
            'fingerprint': fingerprint,
        }
    return {
        'status': 'missing',
        'html': '',
        'generated_at': None,
        'error': '',
        'auto': True,
        'fingerprint': fingerprint,
    }


def trigger_questionnaire_bilan_generation(force=False):
    from grading.tasks import generate_questionnaire_bilan_task

    try:
        generate_questionnaire_bilan_task.delay(force=force)
    except Exception:
        logger.exception('Questionnaire bilan async trigger failed, falling back to sync generation')
        generate_questionnaire_bilan(force=force)


def generate_questionnaire_bilan(force=False):
    serialized_responses = serialize_questionnaire_responses()
    summary = build_questionnaire_summary()
    state = get_questionnaire_bilan_state(serialized_responses, summary)
    fingerprint = state['fingerprint']
    if not summary['is_available']:
        return {
            'status': 'skipped',
            'fingerprint': fingerprint,
        }
    if state['status'] == 'ready' and not force:
        return state
    if not cache.add(QUESTIONNAIRE_BILAN_LOCK_KEY, fingerprint, QUESTIONNAIRE_BILAN_LOCK_TIMEOUT):
        return {
            'status': 'pending',
            'fingerprint': fingerprint,
        }
    try:
        rows = []
        for item in serialized_responses:
            row = dict(item['answers'])
            row['_uid'] = item['username']
            row['_display_name'] = item['display_name']
            rows.append(row)
        stats = _compute_stats(rows, summary['total_eligible'])
        prompt = _build_prompt(stats, summary['total_eligible'])
        html = _call_ollama(prompt)
        result = {
            'status': 'ready',
            'html': html,
            'generated_at': timezone.now().isoformat(),
            'error': '',
            'auto': True,
            'fingerprint': fingerprint,
            'responses_count': summary['responses_count'],
            'total_eligible': summary['total_eligible'],
            'model': OLLAMA_MODEL,
        }
        cache.set(QUESTIONNAIRE_BILAN_CACHE_KEY, result, timeout=None)
        return result
    except Exception as exc:
        logger.exception('Questionnaire bilan generation failed')
        error_result = {
            'status': 'error',
            'html': '',
            'generated_at': timezone.now().isoformat(),
            'error': str(exc)[:500],
            'auto': True,
            'fingerprint': fingerprint,
        }
        cache.set(QUESTIONNAIRE_BILAN_CACHE_KEY, error_result, timeout=3600)
        return error_result
    finally:
        current_lock = cache.get(QUESTIONNAIRE_BILAN_LOCK_KEY)
        if current_lock == fingerprint:
            cache.delete(QUESTIONNAIRE_BILAN_LOCK_KEY)
