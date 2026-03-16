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


def get_teacher_queryset():
    return User.objects.filter(groups__name=UserRole.TEACHER).distinct()


def build_questionnaire_summary():
    total_eligible = get_teacher_queryset().count()
    responses_count = QuestionnaireResponse.objects.filter(
        user__groups__name=UserRole.TEACHER
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

        return Response({
            'status': 'ok',
            'submitted_at': response.updated_at.isoformat(),
            'has_response': True,
            'summary': build_questionnaire_summary(),
        })


class QuestionnaireBilanView(views.APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        responses = QuestionnaireResponse.objects.select_related('user').order_by('-updated_at')
        summary = build_questionnaire_summary()
        serialized = []

        for item in responses:
            if not item.user.groups.filter(name=UserRole.TEACHER).exists():
                continue
            serialized.append({
                'user_id': item.user_id,
                'username': item.user.username,
                'display_name': build_display_name(item.user),
                'email': item.user.email,
                'submitted_at': item.updated_at.isoformat(),
                'answers': item.payload,
            })
        if not summary['is_available']:
            return Response({
                'responses': [],
                'summary': summary,
                'detail': 'Le bilan sera disponible une fois que tous les correcteurs auront répondu au questionnaire.',
            })

        return Response({
            'responses': serialized,
            'summary': summary,
        })
