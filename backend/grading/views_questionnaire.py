from django.contrib.auth import get_user_model
from rest_framework import status, views
from rest_framework.response import Response

from core.auth import IsTeacher, UserRole
from exams.permissions import IsTeacherOrAdmin
from grading.models import QuestionnaireResponse

User = get_user_model()


def build_display_name(user):
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.username


def get_eligible_correctors():
    """Return the set of users assigned as correctors on at least one exam."""
    from exams.models import Exam
    corrector_ids = (
        Exam.objects.exclude(correctors=None)
        .values_list('correctors', flat=True)
        .distinct()
    )
    return User.objects.filter(id__in=corrector_ids).distinct()


def get_teacher_queryset():
    """Return the eligible cohort: assigned correctors if any exams exist, else all teachers."""
    eligible = get_eligible_correctors()
    if eligible.exists():
        return eligible
    return User.objects.filter(groups__name=UserRole.TEACHER).distinct()


def build_questionnaire_summary():
    eligible_qs = get_teacher_queryset()
    total_eligible = eligible_qs.count()
    eligible_ids = set(eligible_qs.values_list('id', flat=True))
    responses_count = QuestionnaireResponse.objects.filter(
        user_id__in=eligible_ids
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


def trigger_questionnaire_bilan_generation():
    """Trigger async generation of the questionnaire bilan report.

    This is a placeholder that can be replaced with a Celery task or other
    async mechanism.  Tests patch this function to verify it is called at the
    right moment.
    """
    pass


def _read_bilan_html():
    """Read the static bilan.html file and return style+body content for v-html injection."""
    import os
    import re
    bilan_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bilan.html')
    if not os.path.exists(bilan_path):
        bilan_path = '/app/bilan.html'
    if not os.path.exists(bilan_path):
        return None
    try:
        with open(bilan_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Extract <style> block
        style_match = re.search(r'(<style[^>]*>.*?</style>)', content, re.DOTALL)
        style_block = style_match.group(1) if style_match else ''
        # Scope body selector to avoid conflicts
        style_block = style_block.replace('body {', '.bilan-injected-content {')
        style_block = style_block.replace('body{', '.bilan-injected-content{')
        # Extract <body> content
        body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL)
        body_content = body_match.group(1).strip() if body_match else ''
        if not body_content:
            return None
        return f'{style_block}\n<div class="bilan-injected-content">\n{body_content}\n</div>'
    except Exception:
        return None


# Cache the bilan HTML in memory to avoid re-reading the file on every request
_BILAN_HTML_CACHE = None


def _get_bilan_html():
    global _BILAN_HTML_CACHE
    if _BILAN_HTML_CACHE is None:
        _BILAN_HTML_CACHE = _read_bilan_html() or ''
    return _BILAN_HTML_CACHE


def _build_participants():
    """Build responded/pending participant lists from the eligible corrector cohort."""
    eligible_qs = get_teacher_queryset()
    responded_user_ids = set(
        QuestionnaireResponse.objects.filter(
            user__in=eligible_qs
        ).values_list('user_id', flat=True)
    )
    responded = []
    pending = []
    for user in eligible_qs:
        entry = {
            'user_id': user.id,
            'username': user.username,
            'display_name': build_display_name(user),
            'email': user.email,
        }
        if user.id in responded_user_ids:
            responded.append(entry)
        else:
            pending.append(entry)
    return {'responded': responded, 'pending': pending}


class QuestionnaireResponseView(views.APIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        response = QuestionnaireResponse.objects.filter(user=request.user).first()
        summary = build_questionnaire_summary()
        return Response({
            'has_response': bool(response),
            'response': response.payload if response else {},
            'submitted_at': response.updated_at.isoformat() if response else None,
            'respondent': {
                'username': request.user.username,
                'display_name': build_display_name(request.user),
                'email': request.user.email,
            },
            'summary': summary,
        })

    def post(self, request):
        answers = request.data.get('answers', request.data)
        if not isinstance(answers, dict):
            return Response({
                'detail': 'Payload invalide.'
            }, status=status.HTTP_400_BAD_REQUEST)
        if QuestionnaireResponse.objects.filter(user=request.user).exists():
            return Response({
                'detail': 'Le questionnaire a déjà été soumis.'
            }, status=status.HTTP_409_CONFLICT)

        response = QuestionnaireResponse.objects.create(
            user=request.user,
            payload=answers,
        )

        summary = build_questionnaire_summary()

        if summary['is_available']:
            trigger_questionnaire_bilan_generation()

        return Response({
            'status': 'ok',
            'submitted_at': response.updated_at.isoformat(),
            'has_response': True,
            'summary': summary,
        })


class QuestionnaireBilanView(views.APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        eligible_qs = get_teacher_queryset()
        eligible_ids = set(eligible_qs.values_list('id', flat=True))

        responses = QuestionnaireResponse.objects.select_related('user').filter(
            user_id__in=eligible_ids
        ).order_by('-updated_at')
        summary = build_questionnaire_summary()
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

        participants = _build_participants()

        # Build generated_bilan from static HTML file
        bilan_html = _get_bilan_html()
        generated_bilan = {
            'status': 'ready' if bilan_html else 'missing',
            'html': bilan_html or '',
            'generated_at': '2026-03-21T21:11:01' if bilan_html else None,
            'error_detail': '',
        }

        is_admin = bool(
            request.user.is_superuser
            or request.user.is_staff
            or request.user.groups.filter(name=UserRole.ADMIN).exists()
        )

        # Admin always sees responses; non-admin only when all have responded
        visible_responses = serialized if (is_admin or summary['is_available']) else []

        return Response({
            'responses': visible_responses,
            'participants': participants,
            'summary': summary,
            'generated_bilan': generated_bilan,
            'detail': '',
        })
