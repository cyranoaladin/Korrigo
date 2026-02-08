from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404
from .services import OCRService
from .models import OCRResult
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
    Endpoint pour identifier une copie manuellement (sans OCR).
    
    PRD-19: Utilise CopyIdentificationService pour garantir:
    - Un seul Copy identifié par (exam, student)
    - Fusion automatique si doublon détecté
    - Race-condition safe via select_for_update
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, copy_id):
        from identification.services import CopyIdentificationService
        
        student_id = request.data.get('student_id')

        if not student_id:
            return Response({
                'error': 'student_id requis'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = CopyIdentificationService.identify_copy(
                copy_id=copy_id,
                student_id=student_id,
                user=request.user,
                method='manual_identification'
            )
            
            return Response({
                'message': result['message'],
                'copy_id': result['copy_id'],
                'student_name': result['student_name'],
                'merged': result['merged'],
                'merged_from': result.get('merged_from')
            })
            
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class OCRIdentifyView(APIView):
    """
    Endpoint pour identifier une copie via OCR + validation humaine.
    
    PRD-19: Utilise CopyIdentificationService pour garantir:
    - Un seul Copy identifié par (exam, student)
    - Fusion automatique si doublon détecté
    - Race-condition safe via select_for_update
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, copy_id):
        from identification.services import CopyIdentificationService
        
        student_id = request.data.get('student_id')

        if not student_id:
            return Response({
                'error': 'student_id requis'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = CopyIdentificationService.identify_copy(
                copy_id=copy_id,
                student_id=student_id,
                user=request.user,
                method='ocr_assisted_identification'
            )
            
            return Response({
                'message': result['message'],
                'copy_id': result['copy_id'],
                'student_name': result['student_name'],
                'merged': result['merged'],
                'merged_from': result.get('merged_from')
            })
            
        except ValueError as e:
            return Response({
                'error': str(e)
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
                'full_name': student.full_name,
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
                    'full_name': student.full_name,
                    'last_name': student.last_name,  # Property: first word of full_name
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
            'full_name': student.full_name,
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
        # Phase 3: Use async task instead of synchronous OCR
        from identification.tasks import async_cmen_ocr

        copy = get_object_or_404(Copy, id=copy_id)

        # Verify copy has booklets
        if not copy.booklets.exists():
            return Response({
                'error': 'Aucun fascicule associé à cette copie'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Queue async OCR task for background processing
        result = async_cmen_ocr.delay(str(copy_id))

        return Response({
            "task_id": result.id,
            "message": "OCR processing started. Use task_id to check status and results.",
            "status_url": f"/api/tasks/{result.id}/status/",
            "copy_id": str(copy_id)
        }, status=status.HTTP_202_ACCEPTED)


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
                    # Chercher l'élève dans la base de données par full_name
                    full_name = f"{match_result.student.last_name} {match_result.student.first_name}".strip()
                    db_student = Student.objects.filter(
                        full_name__iexact=full_name
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
                            'student': db_student.full_name,
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


class GPT4VisionIndexView(APIView):
    """
    Pipeline d'Indexation Automatisée avec GPT-4 Vision.
    
    POST /api/identification/gpt4v-index/<exam_id>/
    
    Traite un PDF scanné avec OCR GPT-4 Vision et réconcilie
    avec le CSV des élèves pour identification automatique.
    
    Body:
    {
        "pdf_path": "/path/to/scan.pdf",  # ou pdf_url
        "csv_path": "/path/to/students.csv",  # ou csv_url
        "dry_run": false,
        "max_copies": null  # optionnel, pour tests
    }
    """
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, exam_id):
        from exams.models import Exam
        from processing.services.exam_indexing_service import ExamIndexingService
        from identification.services import CopyIdentificationService
        import tempfile
        import os
        
        exam = get_object_or_404(Exam, id=exam_id)
        
        pdf_path = request.data.get('pdf_path')
        csv_path = request.data.get('csv_path')
        dry_run = request.data.get('dry_run', False)
        max_copies = request.data.get('max_copies')
        
        if not pdf_path or not csv_path:
            return Response({
                'error': 'pdf_path et csv_path sont requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not os.path.exists(pdf_path):
            return Response({
                'error': f'PDF non trouvé: {pdf_path}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not os.path.exists(csv_path):
            return Response({
                'error': f'CSV non trouvé: {csv_path}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Initialiser le service d'indexation
            service = ExamIndexingService(
                csv_path=csv_path,
                pdf_path=pdf_path,
                debug=request.data.get('debug', False)
            )
            
            # 1. Charger le CSV (SSOT)
            students = service.load_csv()
            
            # 2-4. Traiter le PDF avec OCR GPT-4V et matching
            output_dir = tempfile.mkdtemp(prefix='gpt4v_index_')
            results = service.process_pdf(output_dir=output_dir, max_copies=max_copies)
            
            # 5. Générer le manifest
            manifest_path = service.generate_manifest(output_dir)
            
            # Statistiques
            summary = {
                'total_copies': len(results),
                'validated': sum(1 for r in results if r.validation_status == 'VALIDATED'),
                'ambiguous': sum(1 for r in results if r.validation_status == 'AMBIGUOUS'),
                'manual_review': sum(1 for r in results if r.validation_status == 'MANUAL_REVIEW'),
                'no_match': sum(1 for r in results if r.validation_status == 'NO_MATCH'),
            }
            
            # Si pas dry_run, créer les copies et identifier
            copies_created = []
            if not dry_run:
                for result in results:
                    if result.validation_status == 'VALIDATED' and result.student:
                        # Chercher l'élève dans la base de données
                        db_student = Student.objects.filter(
                            full_name__icontains=result.student.last_name
                        ).first()
                        
                        if db_student:
                            # Créer ou récupérer la copie
                            copy, created = Copy.objects.get_or_create(
                                exam=exam,
                                anonymous_id=f"GPT4V-{result.page_start:03d}",
                                defaults={
                                    'status': Copy.Status.READY,
                                    'student': db_student,
                                    'is_identified': True,
                                    'validated_at': timezone.now()
                                }
                            )
                            
                            if created:
                                # Log l'événement
                                GradingEvent.objects.create(
                                    copy=copy,
                                    action=GradingEvent.Action.VALIDATE,
                                    actor=request.user,
                                    metadata={
                                        'method': 'gpt4v_auto_identification',
                                        'ocr_confidence': result.ocr_extraction.confidence,
                                        'match_score': result.match_score,
                                        'page_start': result.page_start,
                                        'page_end': result.page_end
                                    }
                                )
                                
                                copies_created.append({
                                    'copy_id': str(copy.id),
                                    'student': db_student.full_name,
                                    'pages': f"{result.page_start}-{result.page_end}"
                                })
            
            return Response({
                'success': True,
                'exam_id': str(exam.id),
                'exam_name': exam.name,
                'dry_run': dry_run,
                'students_loaded': len(students),
                'summary': summary,
                'manifest_path': manifest_path,
                'copies_created': copies_created if not dry_run else [],
                'details': [
                    {
                        'page_start': r.page_start,
                        'page_end': r.page_end,
                        'status': r.validation_status,
                        'student': r.student.raw_name if r.student else None,
                        'score': round(r.match_score, 3),
                        'ocr': {
                            'last_name': r.ocr_extraction.last_name,
                            'first_name': r.ocr_extraction.first_name,
                            'date_of_birth': r.ocr_extraction.date_of_birth
                        }
                    }
                    for r in results
                ]
            })
            
        except Exception as e:
            import traceback
            return Response({
                'error': str(e),
                'traceback': traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class QuarantineResolutionView(APIView):
    """Unified view: QUARANTINE copies + QUARANTINE annexes + student list."""
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, exam_id):
        from exams.models import Exam, Copy, AnnexePage
        from students.models import Student
        exam = get_object_or_404(Exam, id=exam_id)

        quarantine_copies = list(
            Copy.objects.filter(exam=exam, status='QUARANTINE')
            .values('id', 'anonymous_id', 'status')
        )

        # Enrich with OCR data if available
        for c in quarantine_copies:
            try:
                ocr = OCRResult.objects.get(copy_id=c['id'])
                c['ocr_confidence'] = ocr.confidence
                c['ocr_tier'] = ocr.ocr_tier
                c['extracted_last_name'] = ocr.extracted_last_name
                c['extracted_first_name'] = ocr.extracted_first_name
                c['top_candidates'] = ocr.top_candidates
            except OCRResult.DoesNotExist:
                c['ocr_confidence'] = 0.0
                c['ocr_tier'] = ''
                c['extracted_last_name'] = ''
                c['extracted_first_name'] = ''
                c['top_candidates'] = []

        quarantine_annexes = list(
            AnnexePage.objects.filter(exam=exam, status='QUARANTINE')
            .values('id', 'page_index', 'ocr_extracted_name', 'ocr_confidence', 'ocr_tier')
        )

        students = list(
            Student.objects.all().values('id', 'full_name', 'date_of_birth', 'class_name')
        )

        return Response({
            'copies': quarantine_copies,
            'annexes': quarantine_annexes,
            'students': students,
        })


class ManualAssignCopyView(APIView):
    """Assign student to a QUARANTINE copy manually."""
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, copy_id):
        from exams.models import Copy
        from students.models import Student
        from grading.models import GradingEvent

        with transaction.atomic():
            copy = get_object_or_404(
                Copy.objects.select_for_update(), id=copy_id
            )
            if copy.status != 'QUARANTINE':
                return Response(
                    {'error': f'Copy status is {copy.status}, expected QUARANTINE'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            student_id = request.data.get('student_id')
            if not student_id:
                return Response(
                    {'error': 'student_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            student = get_object_or_404(Student, id=student_id)

            # Anti-duplicate check
            existing = Copy.objects.filter(
                exam=copy.exam, student=student
            ).exclude(id=copy.id).first()
            if existing:
                return Response(
                    {'error': f'Student already assigned to copy {existing.anonymous_id}',
                     'existing_copy_id': str(existing.id)},
                    status=status.HTTP_409_CONFLICT
                )

            copy.student = student
            copy.is_identified = True
            copy.status = 'READY'
            copy.save(update_fields=['student', 'is_identified', 'status'])

            # Update OCR result
            ocr_result, _ = OCRResult.objects.get_or_create(
                copy=copy,
                defaults={'detected_text': '', 'confidence': 0.0}
            )
            ocr_result.ocr_mode = 'MANUAL'
            ocr_result.manual_override = True
            ocr_result.save(update_fields=['ocr_mode', 'manual_override'])

            GradingEvent.objects.create(
                copy=copy, action='IMPORT', actor=request.user,
                metadata={
                    'type': 'manual_quarantine_resolution',
                    'student_id': str(student_id),
                    'student_name': student.full_name,
                }
            )

        return Response({'status': 'assigned', 'copy_status': 'READY'})


class ManualAssignAnnexeView(APIView):
    """Assign student to a QUARANTINE annexe manually."""
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, annexe_id):
        from exams.models import Copy, AnnexePage
        from students.models import Student
        from django.utils import timezone

        with transaction.atomic():
            annexe = get_object_or_404(
                AnnexePage.objects.select_for_update(), id=annexe_id
            )
            student_id = request.data.get('student_id')
            if not student_id:
                return Response(
                    {'error': 'student_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            student = get_object_or_404(Student, id=student_id)

            copy = Copy.objects.filter(exam=annexe.exam, student=student).first()

            annexe.student = student
            annexe.copy = copy
            annexe.status = 'MANUAL_ASSIGNED'
            annexe.matched_by = request.user
            annexe.matched_at = timezone.now()
            annexe.save()

        return Response({'status': 'assigned'})
