"""
Views pour la banque d'annotations (officielles + personnelles).
Fonctionnalité 1 : Suggestions contextuelles par exercice/question
Fonctionnalité 2 : Mémoire personnelle du correcteur (CRUD + autocomplétion)
"""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, F
from django.utils import timezone
from exams.permissions import IsTeacherOrAdmin
from grading.models import AnnotationTemplate, UserAnnotation
from grading.serializers import AnnotationTemplateSerializer, UserAnnotationSerializer
import logging

logger = logging.getLogger(__name__)


class ContextualSuggestionsView(APIView):
    """
    GET /api/grading/exams/<exam_id>/suggestions/
    
    Retourne les annotations suggérées (officielles + personnelles)
    filtrées par exercice, question et recherche textuelle.
    
    Query params:
        exercise (int) : numéro d'exercice
        question (str) : numéro de question (ex: '3b')
        q (str) : recherche textuelle libre (fuzzy)
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def get(self, request, exam_id):
        exercise = request.query_params.get('exercise')
        question = request.query_params.get('question')
        search_query = request.query_params.get('q', '').strip()

        # --- 1. Annotations officielles ---
        official_qs = AnnotationTemplate.objects.filter(
            exam_id=exam_id,
            is_active=True
        )
        if exercise:
            official_qs = official_qs.filter(exercise_number=exercise)
        if question:
            official_qs = official_qs.filter(question_number=question)
        if search_query:
            official_qs = official_qs.filter(text__icontains=search_query)
        official_qs = official_qs[:30]

        # --- 2. Annotations personnelles ---
        personal_qs = UserAnnotation.objects.filter(
            user=request.user,
            is_active=True
        )
        if exercise:
            personal_qs = personal_qs.filter(
                Q(exercise_context=exercise) | Q(exercise_context__isnull=True)
            )
        if question:
            personal_qs = personal_qs.filter(
                Q(question_context=question) | Q(question_context='')
            )
        if search_query:
            personal_qs = personal_qs.filter(text__icontains=search_query)
        personal_qs = personal_qs.order_by('-usage_count', '-last_used')[:20]

        return Response({
            'official': AnnotationTemplateSerializer(official_qs, many=True).data,
            'personal': UserAnnotationSerializer(personal_qs, many=True).data,
        })


class UserAnnotationListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/grading/my-annotations/       → liste des annotations personnelles
    POST /api/grading/my-annotations/       → créer une annotation personnelle
    
    Query params (GET):
        q (str) : recherche textuelle
        exercise (int) : filtrer par exercice
    """
    serializer_class = UserAnnotationSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def get_queryset(self):
        qs = UserAnnotation.objects.filter(user=self.request.user, is_active=True)
        search_query = self.request.query_params.get('q', '').strip()
        exercise = self.request.query_params.get('exercise')
        if search_query:
            qs = qs.filter(text__icontains=search_query)
        if exercise:
            qs = qs.filter(exercise_context=exercise)
        return qs.order_by('-usage_count', '-last_used')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, usage_count=0)


class UserAnnotationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH/DELETE /api/grading/my-annotations/<pk>/
    """
    serializer_class = UserAnnotationSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def get_queryset(self):
        return UserAnnotation.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])


class UserAnnotationUseView(APIView):
    """
    POST /api/grading/my-annotations/<pk>/use/
    
    Incrémente le compteur d'usage et met à jour last_used.
    Appelé automatiquement quand le correcteur insère une annotation personnelle.
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, pk):
        try:
            ann = UserAnnotation.objects.get(pk=pk, user=request.user)
        except UserAnnotation.DoesNotExist:
            return Response(
                {"detail": "Annotation personnelle introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )
        ann.usage_count = F('usage_count') + 1
        ann.last_used = timezone.now()
        ann.save(update_fields=['usage_count', 'last_used', 'updated_at'])
        ann.refresh_from_db()
        return Response(UserAnnotationSerializer(ann).data)


class AutoSaveAnnotationView(APIView):
    """
    POST /api/grading/my-annotations/auto-save/
    
    Auto-enregistre une annotation manuelle dans la banque personnelle.
    Si le texte exact existe déjà, incrémente le compteur d'usage.
    Sinon, crée une nouvelle entrée.
    
    Body:
        text (str) : texte de l'annotation
        exercise_context (int, optional) : numéro d'exercice
        question_context (str, optional) : label de question
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request):
        text = request.data.get('text', '').strip()
        if not text:
            return Response(
                {"detail": "Le texte de l'annotation est requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        exercise_context = request.data.get('exercise_context')
        question_context = request.data.get('question_context', '')

        existing = UserAnnotation.objects.filter(
            user=request.user,
            text=text,
            is_active=True
        ).first()

        if existing:
            existing.usage_count = F('usage_count') + 1
            existing.last_used = timezone.now()
            existing.save(update_fields=['usage_count', 'last_used', 'updated_at'])
            existing.refresh_from_db()
            return Response(UserAnnotationSerializer(existing).data)

        ann = UserAnnotation.objects.create(
            user=request.user,
            text=text,
            exercise_context=exercise_context,
            question_context=question_context,
            usage_count=1,
            last_used=timezone.now()
        )
        return Response(
            UserAnnotationSerializer(ann).data,
            status=status.HTTP_201_CREATED
        )


class AnnotationTemplateListView(generics.ListAPIView):
    """
    GET /api/grading/exams/<exam_id>/annotation-templates/
    
    Liste tous les templates d'annotation pour un examen (admin).
    """
    serializer_class = AnnotationTemplateSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def get_queryset(self):
        return AnnotationTemplate.objects.filter(
            exam_id=self.kwargs['exam_id'],
            is_active=True
        )
