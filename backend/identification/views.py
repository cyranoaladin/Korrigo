from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .services import OCRService
from exams.models import Copy, Booklet
from grading.services import GradingService
from grading.models import GradingEvent
from students.models import Student
from exams.permissions import IsTeacherOrAdmin, IsAdmin
from django.utils import timezone


class IdentificationDeskView(APIView):
    """
    Interface "Video-Coding" pour l'identification manuelle des copies
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def get(self, request):
        # Récupérer les copies non identifiées avec en-tête
        from exams.models import Copy, Booklet

        # Get ALL unidentified copies (not limited to a specific exam)
        unidentified_copies = Copy.objects.filter(is_identified=False).select_related('exam')

        data = []
        for copy in unidentified_copies:
            # Get the first booklet for the header image
            booklet = copy.booklets.first()
            header_url = None
            if booklet:
                # Use the same format as the original endpoint
                header_url = f"/api/booklets/{booklet.id}/header/"

            data.append({
                "id": copy.id,
                "anonymous_id": copy.anonymous_id,
                "header_image_url": header_url,
                "status": copy.status
            })

        return Response(data)


from exams.models import Copy, Booklet
from grading.services import GradingService
from grading.models import GradingEvent


class ManualIdentifyView(APIView):
    """
    Endpoint pour identifier une copie manuellement (sans OCR)
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)
        student_id = request.data.get('student_id')

        if not student_id:
            return Response({
                'error': 'student_id requis'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({
                'error': 'Élève non trouvé'
            }, status=status.HTTP_404_NOT_FOUND)

        # Vérifier que la copie est dans l'état approprié pour identification
        if copy.status not in [Copy.Status.STAGING, Copy.Status.READY]:
            return Response({
                'error': f'Impossible d\'identifier une copie en statut {copy.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Associer la copie à l'élève
        copy.student = student
        copy.is_identified = True

        # Transition d'état : STAGING → READY (prêt à corriger)
        if copy.status == Copy.Status.STAGING:
            copy.status = Copy.Status.READY
            copy.validated_at = timezone.now()

        copy.save()

        # Créer un événement d'audit
        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.VALIDATE,  # Using existing action for identification
            actor=request.user if request.user.is_authenticated else None,
            metadata={
                'student_id': str(student.id),
                'student_name': f"{student.first_name} {student.last_name}",
                'method': 'manual_identification'
            }
        )

        return Response({
            'message': 'Copie identifiée avec succès',
            'copy_id': copy.id,
            'student_name': f"{student.first_name} {student.last_name}",
            'new_status': copy.status
        })


class OCRIdentifyView(APIView):
    """
    Endpoint pour identifier une copie via OCR + validation humaine
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)
        student_id = request.data.get('student_id')

        if student_id:
            try:
                student = Student.objects.get(id=student_id)
            except Student.DoesNotExist:
                return Response({
                    'error': 'Élève non trouvé'
                }, status=status.HTTP_404_NOT_FOUND)

            # Associer la copie à l'élève
            copy.student = student
            copy.is_identified = True
            copy.status = Copy.Status.READY  # Passer à READY après identification
            copy.save()

            # Créer un événement d'audit OCR
            GradingEvent.objects.create(
                copy=copy,
                action=GradingEvent.Action.VALIDATE,
                actor=request.user if request.user.is_authenticated else None,
                metadata={
                    'student_id': str(student.id),
                    'student_name': f"{student.first_name} {student.last_name}",
                    'method': 'ocr_assisted_identification'
                }
            )

            return Response({
                'message': 'Copie identifiée avec succès',
                'copy_id': copy.id,
                'student_name': f"{student.first_name} {student.last_name}"
            })

        return Response({
            'error': 'student_id requis'
        }, status=status.HTTP_400_BAD_REQUEST)


class OCRPerformView(APIView):
    """
    Endpoint pour effectuer l'OCR sur une copie spécifique
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)
        booklet = copy.booklets.first()
        
        if not booklet:
            return Response({
                'error': 'Aucun fascicule associé à cette copie'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Extraire l'image d'en-tête
            header_image = OCRService.extract_header_from_booklet(booklet)
            
            # Effectuer l'OCR
            ocr_result = OCRService.perform_ocr_on_header(header_image)
            
            if 'error' in ocr_result:
                return Response({
                    'error': ocr_result['error']
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Trouver les élèves correspondants
            suggestions = OCRService.find_matching_students(ocr_result['text'])
            
            suggestion_data = [{
                'id': student.id,
                'full_name': f"{student.first_name} {student.last_name}",
                'class_name': student.class_name
            } for student in suggestions]
            
            return Response({
                'detected_text': ocr_result['text'],
                'confidence': ocr_result['confidence'],
                'suggestions': suggestion_data
            })
            
        except Exception as e:
            from core.utils.errors import safe_error_response
            return Response(
                safe_error_response(e, context="OCR", user_message="Erreur lors de l'OCR. Veuillez réessayer ou identifier manuellement."),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )