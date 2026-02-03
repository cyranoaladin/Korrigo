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
                safe_error_response(e, context="OCR", user_message="OCR processing failed. Please try again."),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# PRD-19: Multi-layer OCR API Endpoints

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacherOrAdmin])
def get_ocr_candidates(request, copy_id):
    """
    Get top-k OCR candidates for semi-automatic selection.

    Returns list of top-5 student candidates with confidence scores,
    OCR engine sources, and vote counts.
    """
    copy = get_object_or_404(Copy, id=copy_id)

    # Validate copy status - only allow editable states
    if copy.status not in [Copy.Status.STAGING, Copy.Status.READY]:
        return Response({
            'error': f'Copy is in {copy.status} state and cannot be modified'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check if OCR result exists
    if not hasattr(copy, 'ocr_result'):
        return Response({
            'error': 'No OCR result available for this copy'
        }, status=status.HTTP_404_NOT_FOUND)

    ocr_result = copy.ocr_result

    # Build candidate list from top_candidates JSON field
    candidates = []
    for idx, candidate_data in enumerate(ocr_result.top_candidates[:5], 1):
        try:
            student = Student.objects.get(id=candidate_data['student_id'])
            candidates.append({
                'rank': idx,
                'student': {
                    'id': student.id,
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'email': student.email,
                    'date_of_birth': student.date_of_birth.strftime('%d/%m/%Y') if student.date_of_birth else None
                },
                'confidence': candidate_data['confidence'],
                'vote_count': candidate_data.get('vote_count', 0),
                'vote_agreement': candidate_data.get('vote_agreement', 0.0),
                'ocr_sources': candidate_data.get('sources', [])
            })
        except Student.DoesNotExist:
            # Student not found, skip this candidate
            continue

    return Response({
        'copy_id': str(copy_id),
        'anonymous_id': copy.anonymous_id,
        'ocr_mode': ocr_result.ocr_mode,
        'candidates': candidates,
        'total_engines': len(ocr_result.top_candidates[0].get('sources', [])) if ocr_result.top_candidates else 0
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacherOrAdmin])
def select_ocr_candidate(request, copy_id):
    """
    Teacher selects a student from the top-k OCR candidates.

    Expected POST data:
    {
        "rank": 1  // 1-5, rank of the selected candidate
    }
    """
    copy = get_object_or_404(Copy, id=copy_id)

    # Validate copy status - only allow editable states
    if copy.status not in [Copy.Status.STAGING, Copy.Status.READY]:
        return Response({
            'error': f'Copy is in {copy.status} state and cannot be modified'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Get selected rank from request
    selected_rank = request.data.get('rank')
    if not selected_rank or not isinstance(selected_rank, int) or selected_rank < 1 or selected_rank > 5:
        return Response({
            'error': 'Invalid rank. Must be integer between 1 and 5.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check if OCR result exists
    if not hasattr(copy, 'ocr_result'):
        return Response({
            'error': 'No OCR result available for this copy'
        }, status=status.HTTP_404_NOT_FOUND)

    ocr_result = copy.ocr_result

    # Check if selected rank is within available candidates
    if selected_rank > len(ocr_result.top_candidates):
        return Response({
            'error': f'Rank {selected_rank} exceeds available candidates ({len(ocr_result.top_candidates)})'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Get selected candidate
    candidate = ocr_result.top_candidates[selected_rank - 1]

    try:
        student = Student.objects.get(id=candidate['student_id'])
    except Student.DoesNotExist:
        return Response({
            'error': 'Selected student not found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Assign student to copy
    copy.student = student
    copy.is_identified = True

    # Transition copy to READY status if currently STAGING
    if copy.status == Copy.Status.STAGING:
        copy.status = Copy.Status.READY

    copy.save()

    # Update OCR result audit trail
    ocr_result.selected_candidate_rank = selected_rank
    ocr_result.save()

    # Log grading event for audit trail
    GradingEvent.objects.create(
        copy=copy,
        action='IDENTIFIED_FROM_OCR_CANDIDATES',
        details={
            'selected_rank': selected_rank,
            'student_id': student.id,
            'confidence': candidate['confidence'],
            'ocr_mode': ocr_result.ocr_mode
        },
        user=request.user if request.user.is_authenticated else None,
        timestamp=timezone.now()
    )

    return Response({
        'success': True,
        'copy_id': str(copy.id),
        'student': {
            'id': student.id,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'email': student.email
        },
        'status': copy.status
    })