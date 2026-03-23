from django.contrib.auth import get_user_model
from rest_framework import status, views
from rest_framework.response import Response

from core.auth import IsTeacher, UserRole
from exams.permissions import IsTeacherOrAdmin
from grading.models import QuestionnaireResponse
from grading.questionnaire_bilan import (
    build_display_name,
    build_questionnaire_participants,
    build_questionnaire_summary,
    get_questionnaire_bilan_state,
    serialize_questionnaire_responses,
    trigger_questionnaire_bilan_generation,
)

User = get_user_model()


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

    def finalize_response(self, request, response, *args, **kwargs):
        return super().finalize_response(request, response, *args, **kwargs)


class QuestionnaireBilanView(views.APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        summary = build_questionnaire_summary()
        serialized = serialize_questionnaire_responses()
        participants = build_questionnaire_participants(serialized)
        generated_bilan = get_questionnaire_bilan_state(serialized, summary)
        is_admin = bool(
            request.user.is_superuser
            or request.user.is_staff
            or request.user.groups.filter(name=UserRole.ADMIN).exists()
        )
        # If bilan is already generated, show it to everyone regardless of is_available
        # Only block if bilan is NOT ready AND user is not admin
        if not summary['is_available'] and generated_bilan['status'] != 'ready' and not is_admin:
            return Response({
                'responses': [],
                'participants': participants,
                'summary': summary,
                'generated_bilan': generated_bilan,
                'detail': '',
            })
        if generated_bilan['status'] == 'missing':
            trigger_questionnaire_bilan_generation()
            generated_bilan = get_questionnaire_bilan_state(serialized, summary)
        if generated_bilan['status'] == 'pending':
            detail = 'Toutes les réponses ont été reçues. Le bilan automatique est en cours de génération.'
        elif generated_bilan['status'] == 'failed':
            detail = 'Le bilan automatique n’a pas pu être généré pour le moment.'
        else:
            detail = ''

        return Response({
            'responses': serialized,
            'participants': participants,
            'summary': summary,
            'generated_bilan': generated_bilan,
            'detail': detail,
        })
