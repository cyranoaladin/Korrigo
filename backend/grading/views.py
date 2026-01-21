"""
Views pour l'app grading.
Tous les endpoints sont protégés par IsTeacherOrAdmin (staff only).
"""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from exams.permissions import IsTeacherOrAdmin
from grading.models import Annotation
from grading.serializers import AnnotationSerializer
from grading.services import AnnotationService, GradingService
from exams.models import Copy


class AnnotationListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/copies/<copy_id>/annotations/ - Liste les annotations d'une copie
    POST /api/copies/<copy_id>/annotations/ - Crée une annotation (si READY)

    Permission : IsTeacherOrAdmin (staff only)
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = AnnotationSerializer

    def get_queryset(self):
        copy_id = self.kwargs['copy_id']
        copy = get_object_or_404(Copy, id=copy_id)
        return AnnotationService.list_annotations(copy)

    def create(self, request, *args, **kwargs):
        copy_id = self.kwargs['copy_id']
        copy = get_object_or_404(Copy, id=copy_id)

        try:
            annotation = AnnotationService.add_annotation(
                copy=copy,
                payload=request.data,
                user=request.user
            )
            serializer = self.get_serializer(annotation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except KeyError as e:
            return Response(
                {'error': f'Missing required field: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class AnnotationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/annotations/<id>/ - Récupère une annotation
    PATCH  /api/annotations/<id>/ - Modifie une annotation (si READY)
    DELETE /api/annotations/<id>/ - Supprime une annotation (si READY)

    Permission : IsTeacherOrAdmin (staff only)
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = AnnotationSerializer
    queryset = Annotation.objects.all()

    def update(self, request, *args, **kwargs):
        annotation = self.get_object()
        partial = kwargs.pop('partial', True)  # PATCH par défaut

        try:
            updated = AnnotationService.update_annotation(
                annotation=annotation,
                payload=request.data,
                user=request.user
            )
            serializer = self.get_serializer(updated)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        annotation = self.get_object()
        try:
            AnnotationService.delete_annotation(annotation, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CopyLockView(APIView):
    """
    POST /api/copies/<id>/lock/

    Verrouille une copie pour correction (READY → LOCKED).
    Permission : IsTeacherOrAdmin (staff only)
    """
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, id):
        copy = get_object_or_404(Copy, id=id)
        try:
            GradingService.lock_copy(copy, request.user)
            return Response(
                {
                    'message': 'Copy locked successfully',
                    'copy_id': str(copy.id),
                    'status': copy.status,
                    'locked_by': request.user.username
                },
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CopyUnlockView(APIView):
    """
    POST /api/copies/<id>/unlock/

    Déverrouille une copie (LOCKED → READY).
    Permission : IsTeacherOrAdmin (staff only)
    """
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, id):
        copy = get_object_or_404(Copy, id=id)
        try:
            GradingService.unlock_copy(copy, request.user)
            return Response(
                {
                    'message': 'Copy unlocked successfully',
                    'copy_id': str(copy.id),
                    'status': copy.status
                },
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CopyFinalizeView(APIView):
    """
    POST /api/copies/<id>/finalize/

    Finalise la correction d'une copie (LOCKED → GRADED).
    Génère le PDF final avec annotations.
    Permission : IsTeacherOrAdmin (staff only)
    """
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, id):
        copy = get_object_or_404(Copy, id=id)
        try:
            GradingService.finalize_copy(copy, request.user)

            # Calcul score final pour la réponse
            final_score = GradingService.compute_score(copy)

            return Response(
                {
                    'message': 'Copy finalized successfully',
                    'copy_id': str(copy.id),
                    'status': copy.status,
                    'final_score': final_score,
                    'final_pdf': copy.final_pdf.url if copy.final_pdf else None
                },
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
