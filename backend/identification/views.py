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
    Interface "Video-Coding" pour l'identification manuelle des copies.
    
    IMPORTANT: Ne retourne que les copies en statut READY non identifiées.
    Les copies STAGING sont en attente d'agrafage et ne doivent pas apparaître ici.
    
    Flux normal:
    1. Upload → Crée copies STAGING (1 par booklet)
    2. Agrafage (MergeBookletsView) → Supprime STAGING, crée 1 copie READY
    3. Video-coding (ici) → Affiche copies READY non identifiées
    4. Identification → Associe élève, garde statut READY
    5. Dispatch → Assigne copies READY aux correcteurs
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def get(self, request):
        from exams.models import Copy, Booklet

        # CORRECTION: Ne récupérer que les copies READY non identifiées
        # Les copies STAGING ne doivent PAS apparaître dans le video-coding
        # car elles n'ont pas encore été agrafées/validées
        unidentified_copies = Copy.objects.filter(
            is_identified=False,
            status=Copy.Status.READY  # Seulement les copies prêtes
        ).select_related('exam').prefetch_related('booklets')

        data = []
        seen_booklet_sets = set()  # Pour détecter les doublons
        
        for copy in unidentified_copies:
            # Get the first booklet for the header image
            booklet = copy.booklets.first()
            header_url = None
            if booklet:
                header_url = f"/api/exams/booklets/{booklet.id}/header/"
            
            # Créer une clé unique basée sur les booklets pour détecter les doublons
            booklet_ids = tuple(sorted(str(b.id) for b in copy.booklets.all()))
            if booklet_ids in seen_booklet_sets:
                # Doublon détecté, ignorer cette copie
                continue
            seen_booklet_sets.add(booklet_ids)

            data.append({
                "id": str(copy.id),
                "anonymous_id": copy.anonymous_id,
                "header_image_url": header_url,
                "status": copy.status,
                "exam_id": str(copy.exam_id),
                "exam_name": copy.exam.name if copy.exam else None,
                "booklet_count": copy.booklets.count()
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
        # IMPORTANT: Seules les copies READY ou LOCKED peuvent être identifiées
        # Les copies STAGING doivent d'abord passer par l'agrafage (MergeBookletsView)
        allowed_statuses = [Copy.Status.READY, Copy.Status.LOCKED]
        if copy.status not in allowed_statuses:
            if copy.status == Copy.Status.STAGING:
                return Response({
                    'error': 'Cette copie est en statut STAGING. Elle doit d\'abord être agrafée avant identification.'
                }, status=status.HTTP_400_BAD_REQUEST)
            return Response({
                'error': f'Impossible d\'identifier une copie en statut {copy.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Associer la copie à l'élève
        copy.student = student
        copy.is_identified = True
        
        # Mettre à jour validated_at si pas déjà défini
        if not copy.validated_at:
            copy.validated_at = timezone.now()

        copy.save()

        # Créer un événement d'audit
        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.VALIDATE,  # Using existing action for identification
            actor=request.user if request.user.is_authenticated else None,
            metadata={
                'student_id': str(student.id),
                'student_name': student.full_name,
                'method': 'manual_identification'
            }
        )

        return Response({
            'message': 'Copie identifiée avec succès',
            'copy_id': copy.id,
            'student_name': student.full_name,
            'new_status': copy.status
        })


class OCRIdentifyView(APIView):
    """
    Endpoint pour identifier une copie via OCR + validation humaine.
    
    IMPORTANT: Seules les copies READY peuvent être identifiées.
    Les copies STAGING doivent d'abord passer par l'agrafage.
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)
        student_id = request.data.get('student_id')

        if not student_id:
            return Response({
                'error': 'student_id requis'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Vérifier le statut de la copie
        allowed_statuses = [Copy.Status.READY, Copy.Status.LOCKED]
        if copy.status not in allowed_statuses:
            if copy.status == Copy.Status.STAGING:
                return Response({
                    'error': 'Cette copie est en statut STAGING. Elle doit d\'abord être agrafée avant identification.'
                }, status=status.HTTP_400_BAD_REQUEST)
            return Response({
                'error': f'Impossible d\'identifier une copie en statut {copy.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({
                'error': 'Élève non trouvé'
            }, status=status.HTTP_404_NOT_FOUND)

        # Associer la copie à l'élève
        copy.student = student
        copy.is_identified = True
        if not copy.validated_at:
            copy.validated_at = timezone.now()
        copy.save()

        # Créer un événement d'audit OCR
        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.VALIDATE,
            actor=request.user if request.user.is_authenticated else None,
            metadata={
                'student_id': str(student.id),
                'student_name': student.full_name,
                'method': 'ocr_assisted_identification'
            }
        )

        return Response({
            'message': 'Copie identifiée avec succès',
            'copy_id': str(copy.id),
            'student_name': student.full_name
        })


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


class CMENOCRView(APIView):
    """
    OCR spécialisé pour les en-têtes CMEN v2.
    Extrait NOM, PRÉNOM et DATE DE NAISSANCE pour identification.
    
    POST /api/identification/cmen-ocr/<copy_id>/
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, copy_id):
        from processing.services.cmen_header_ocr import CMENHeaderOCR, load_students_from_csv
        from django.conf import settings
        import os
        import cv2
        
        copy = get_object_or_404(Copy, id=copy_id)
        booklet = copy.booklets.first()
        
        if not booklet:
            return Response({
                'error': 'Aucun fascicule associé à cette copie'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Obtenir l'image de l'en-tête
            if booklet.pages_images and len(booklet.pages_images) > 0:
                first_page_path = booklet.pages_images[0]
                full_path = os.path.join(settings.MEDIA_ROOT, first_page_path)
                
                if not os.path.exists(full_path):
                    return Response({
                        'error': f'Image non trouvée: {first_page_path}'
                    }, status=status.HTTP_404_NOT_FOUND)
                
                # Charger l'image
                image = cv2.imread(full_path)
                if image is None:
                    return Response({
                        'error': 'Impossible de charger l\'image'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # Extraire l'en-tête (25% supérieur)
                height = image.shape[0]
                header_height = int(height * 0.25)
                header_image = image[:header_height, :]
                
                # Effectuer l'OCR CMEN
                ocr = CMENHeaderOCR(debug=False)
                header_result = ocr.extract_header(header_image)
                
                # Charger les élèves depuis la base de données
                from processing.services.cmen_header_ocr import StudentCSVRecord
                students = []
                for db_student in Student.objects.all():
                    # Extraire nom et prénom depuis full_name
                    parts = db_student.full_name.split(maxsplit=1) if db_student.full_name else []
                    last_name = parts[0] if parts else ''
                    first_name = parts[1] if len(parts) > 1 else ''
                    
                    # Formater la date de naissance
                    dob = ''
                    if db_student.date_of_birth:
                        dob = db_student.date_of_birth.strftime('%d/%m/%Y')
                    
                    students.append(StudentCSVRecord(
                        student_id=str(db_student.id),
                        last_name=last_name,
                        first_name=first_name,
                        date_of_birth=dob,
                        email=db_student.email or '',
                        class_name=db_student.class_name or ''
                    ))
                
                # Chercher une correspondance
                match_result = None
                suggestions = []
                
                if students:
                    match_result = ocr.match_student(header_result, students, threshold=0.5)
                    
                    # Générer des suggestions triées par score
                    from difflib import SequenceMatcher
                    
                    scored_students = []
                    for student in students:
                        name_score = SequenceMatcher(None, header_result.last_name.upper(), student.last_name.upper()).ratio()
                        firstname_score = SequenceMatcher(None, header_result.first_name.upper(), student.first_name.upper()).ratio()
                        date_score = 1.0 if header_result.date_of_birth == student.date_of_birth else 0.0
                        
                        overall = (name_score * 0.35 + firstname_score * 0.35 + date_score * 0.30)
                        scored_students.append((student, overall, {
                            'last_name': name_score,
                            'first_name': firstname_score,
                            'date_of_birth': date_score
                        }))
                    
                    # Trier par score décroissant et prendre les 5 meilleurs
                    scored_students.sort(key=lambda x: x[1], reverse=True)
                    
                    for student, score, details in scored_students[:5]:
                        # Chercher l'élève dans la base de données par full_name
                        full_name = f"{student.last_name} {student.first_name}".strip()
                        db_student = Student.objects.filter(
                            full_name__iexact=full_name
                        ).first()
                        
                        # Si pas trouvé, essayer avec le student_id (qui est l'ID de la DB)
                        if not db_student and student.student_id:
                            try:
                                db_student = Student.objects.filter(id=int(student.student_id)).first()
                            except (ValueError, TypeError):
                                pass
                        
                        suggestions.append({
                            'csv_id': student.student_id,
                            'db_id': db_student.id if db_student else None,
                            'last_name': student.last_name,
                            'first_name': student.first_name,
                            'date_of_birth': student.date_of_birth,
                            'email': student.email,
                            'score': round(score, 3),
                            'match_details': {k: round(v, 3) for k, v in details.items()}
                        })
                
                return Response({
                    'success': True,
                    'copy_id': str(copy.id),
                    'ocr_result': {
                        'last_name': header_result.last_name,
                        'first_name': header_result.first_name,
                        'date_of_birth': header_result.date_of_birth,
                        'confidence': round(header_result.overall_confidence, 3),
                        'fields': [{
                            'name': f.field_name,
                            'value': f.value,
                            'confidence': round(f.confidence, 3)
                        } for f in header_result.fields]
                    },
                    'best_match': {
                        'student_id': match_result.student.student_id if match_result else None,
                        'last_name': match_result.student.last_name if match_result else None,
                        'first_name': match_result.student.first_name if match_result else None,
                        'date_of_birth': match_result.student.date_of_birth if match_result else None,
                        'confidence': round(match_result.confidence, 3) if match_result else 0,
                        'match_details': {k: round(v, 3) for k, v in match_result.match_details.items()} if match_result else {}
                    } if match_result else None,
                    'suggestions': suggestions
                })
            else:
                return Response({
                    'error': 'Aucune image de page disponible'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': f'Erreur OCR: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BatchAutoIdentifyView(APIView):
    """
    Auto-identification batch de toutes les copies non identifiées d'un examen.
    
    POST /api/identification/batch-auto-identify/<exam_id>/
    
    Workflow:
    1. Récupère toutes les copies non identifiées de l'examen
    2. Pour chaque copie, lance l'OCR CMEN
    3. Si confiance > seuil, identifie automatiquement
    4. Retourne un rapport avec les résultats
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, exam_id):
        from processing.services.cmen_header_ocr import CMENHeaderOCR, StudentCSVRecord
        from exams.models import Exam
        from django.conf import settings
        import os
        import cv2
        
        exam = get_object_or_404(Exam, id=exam_id)
        
        # Paramètres
        confidence_threshold = float(request.data.get('confidence_threshold', 0.6))
        dry_run = request.data.get('dry_run', False)
        
        # Charger les élèves depuis la base de données
        students = []
        for db_student in Student.objects.all():
            parts = db_student.full_name.split(maxsplit=1) if db_student.full_name else []
            last_name = parts[0] if parts else ''
            first_name = parts[1] if len(parts) > 1 else ''
            dob = db_student.date_of_birth.strftime('%d/%m/%Y') if db_student.date_of_birth else ''
            
            students.append(StudentCSVRecord(
                student_id=str(db_student.id),
                last_name=last_name,
                first_name=first_name,
                date_of_birth=dob,
                email=db_student.email or '',
                class_name=db_student.class_name or ''
            ))
        
        if not students:
            return Response({
                'error': 'Aucun élève dans la base de données'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Récupérer les copies non identifiées
        unidentified_copies = Copy.objects.filter(
            exam=exam,
            is_identified=False
        ).prefetch_related('booklets')
        
        results = {
            'total': unidentified_copies.count(),
            'auto_identified': 0,
            'needs_review': 0,
            'failed': 0,
            'details': []
        }
        
        ocr = CMENHeaderOCR(debug=False)
        
        for copy in unidentified_copies:
            booklet = copy.booklets.first()
            if not booklet or not booklet.pages_images:
                results['failed'] += 1
                results['details'].append({
                    'copy_id': str(copy.id),
                    'anonymous_id': copy.anonymous_id,
                    'status': 'failed',
                    'reason': 'Pas d\'image disponible'
                })
                continue
            
            try:
                # Charger l'image de l'en-tête
                first_page_path = booklet.pages_images[0]
                full_path = os.path.join(settings.MEDIA_ROOT, first_page_path)
                
                if not os.path.exists(full_path):
                    results['failed'] += 1
                    results['details'].append({
                        'copy_id': str(copy.id),
                        'anonymous_id': copy.anonymous_id,
                        'status': 'failed',
                        'reason': f'Image non trouvée: {first_page_path}'
                    })
                    continue
                
                image = cv2.imread(full_path)
                if image is None:
                    results['failed'] += 1
                    continue
                
                # Extraire l'en-tête (25% supérieur)
                height = image.shape[0]
                header_height = int(height * 0.25)
                header_image = image[:header_height, :]
                
                # OCR CMEN
                header_result = ocr.extract_header(header_image)
                match_result = ocr.match_student(header_result, students, threshold=confidence_threshold)
                
                if match_result and match_result.confidence >= confidence_threshold:
                    # Chercher l'élève dans la base de données
                    db_student = Student.objects.filter(
                        last_name__iexact=match_result.student.last_name,
                        first_name__iexact=match_result.student.first_name
                    ).first()
                    
                    if db_student and not dry_run:
                        # Identifier la copie
                        copy.student = db_student
                        copy.is_identified = True
                        copy.status = Copy.Status.READY
                        copy.save()
                        
                        results['auto_identified'] += 1
                        results['details'].append({
                            'copy_id': str(copy.id),
                            'anonymous_id': copy.anonymous_id,
                            'status': 'auto_identified',
                            'student': f'{db_student.last_name} {db_student.first_name}',
                            'confidence': round(match_result.confidence, 3)
                        })
                    elif db_student and dry_run:
                        results['auto_identified'] += 1
                        results['details'].append({
                            'copy_id': str(copy.id),
                            'anonymous_id': copy.anonymous_id,
                            'status': 'would_identify',
                            'student': f'{match_result.student.last_name} {match_result.student.first_name}',
                            'confidence': round(match_result.confidence, 3)
                        })
                    else:
                        results['needs_review'] += 1
                        results['details'].append({
                            'copy_id': str(copy.id),
                            'anonymous_id': copy.anonymous_id,
                            'status': 'needs_review',
                            'reason': 'Élève trouvé dans CSV mais pas dans la base de données',
                            'ocr_result': f'{match_result.student.last_name} {match_result.student.first_name}'
                        })
                else:
                    results['needs_review'] += 1
                    results['details'].append({
                        'copy_id': str(copy.id),
                        'anonymous_id': copy.anonymous_id,
                        'status': 'needs_review',
                        'reason': 'Confiance OCR insuffisante',
                        'ocr_result': {
                            'last_name': header_result.last_name,
                            'first_name': header_result.first_name,
                            'date_of_birth': header_result.date_of_birth,
                            'confidence': round(header_result.overall_confidence, 3)
                        }
                    })
                    
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'copy_id': str(copy.id),
                    'anonymous_id': copy.anonymous_id,
                    'status': 'failed',
                    'reason': str(e)
                })
        
        return Response({
            'success': True,
            'exam_id': str(exam.id),
            'exam_name': exam.name,
            'dry_run': dry_run,
            'confidence_threshold': confidence_threshold,
            'results': results
        })