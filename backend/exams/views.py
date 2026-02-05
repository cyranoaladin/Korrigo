from rest_framework import viewsets, status, generics, serializers # Added serializers import
from rest_framework.views import APIView

# ... (omitted)


from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.utils.decorators import method_decorator
from core.utils.ratelimit import maybe_ratelimit
from .models import Exam, Booklet, Copy
from .serializers import ExamSerializer, BookletSerializer, CopySerializer, CorrectorCopySerializer
from processing.services.vision import HeaderDetector
from grading.services import GradingService
from .permissions import IsTeacherOrAdmin
from core.auth import IsAdminOnly

import fitz  # PyMuPDF
from django.db import transaction

class ExamUploadView(APIView):
    """
    Upload d'examen avec détection automatique du format:
    - A3 batch avec CSV: utilise BatchA3Processor pour segmentation par élève
    - A3 simple: utilise A3PDFProcessor
    - A4 standard: utilise PDFSplitter
    
    Paramètres optionnels:
    - students_csv: fichier CSV des élèves (whitelist pour OCR)
    - batch_mode: true pour activer le mode batch avec segmentation
    """
    permission_classes = [IsAdminOnly]
    parser_classes = (MultiPartParser, FormParser)

    @method_decorator(maybe_ratelimit(key='user', rate='20/h', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        serializer = ExamSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    exam = serializer.save()
                    
                    import uuid
                    import logging
                    import tempfile
                    import os
                    logger = logging.getLogger(__name__)
                    
                    # Vérifier si mode batch avec CSV
                    students_csv = request.FILES.get('students_csv')
                    batch_mode = request.data.get('batch_mode', 'false').lower() == 'true'
                    
                    if batch_mode and students_csv:
                        # Mode batch: utiliser BatchA3Processor
                        logger.info(f"Batch mode enabled for exam {exam.id}")
                        
                        # Sauvegarder le CSV temporairement
                        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
                            for chunk in students_csv.chunks():
                                f.write(chunk)
                            csv_path = f.name
                        
                        try:
                            from processing.services.batch_processor import BatchA3Processor
                            
                            processor = BatchA3Processor(dpi=200, csv_path=csv_path)
                            
                            # Traiter le batch
                            student_copies = processor.process_batch_pdf(
                                exam.pdf_source.path, 
                                str(exam.id)
                            )
                            
                            # Créer les copies en DB
                            copies = processor.create_copies_from_batch(exam, student_copies)
                            
                            # Stats
                            ready_count = sum(1 for c in copies if c.status == Copy.Status.READY)
                            staging_count = sum(1 for c in copies if c.status == Copy.Status.STAGING)
                            
                            return Response({
                                **serializer.data,
                                "copies_created": len(copies),
                                "ready_count": ready_count,
                                "needs_review_count": staging_count,
                                "message": f"{len(copies)} copies created ({ready_count} ready, {staging_count} need review)"
                            }, status=status.HTTP_201_CREATED)
                            
                        finally:
                            if os.path.exists(csv_path):
                                os.unlink(csv_path)
                    
                    else:
                        # Mode standard: A3PDFProcessor (auto-détecte A3 vs A4)
                        from processing.services.a3_pdf_processor import A3PDFProcessor
                        
                        processor = A3PDFProcessor(dpi=150)
                        booklets = processor.process_exam(exam)
                        
                        # Créer les copies en statut STAGING (ADR-003)
                        for booklet in booklets:
                            copy = Copy.objects.create(
                                exam=exam,
                                anonymous_id=str(uuid.uuid4())[:8].upper(),
                                status=Copy.Status.STAGING,
                                is_identified=False
                            )
                            copy.booklets.add(booklet)
                            logger.info(f"Copy {copy.id} created in STAGING for booklet {booklet.id}")
                        
                        return Response({
                            **serializer.data,
                            "booklets_created": len(booklets),
                            "message": f"{len(booklets)} booklets created successfully"
                        }, status=status.HTTP_201_CREATED)

            except Exception as e:
                from core.utils.errors import safe_error_response
                return Response(
                    safe_error_response(e, context="PDF processing", user_message="PDF upload failed. Please verify the file is valid."),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CopyImportView(APIView):
    """
    Importe un PDF de copie pour un examen donné.
    POST /api/exams/<exam_id>/copies/import/
    Payload: multipart (pdf_file)
    """
    permission_classes = [IsAdminOnly]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        pdf_file = request.FILES.get('pdf_file')
        
        if not pdf_file:
             return Response({'error': 'pdf_file is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
             # Utilise le service de grading qui gère l'import + rasterization sync (P0)
             copy = GradingService.import_pdf(exam, pdf_file, request.user)
             serializer = CopySerializer(copy)
             return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
             return Response({'error': 'Invalid PDF file'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
             from core.utils.errors import safe_error_response
             return Response(
                 safe_error_response(e, context="PDF import", user_message="Failed to import PDF. Please try again."),
                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
             )



class BookletListView(generics.ListAPIView):
    permission_classes = [IsTeacherOrAdmin]  # Teacher/Admin only
    serializer_class = BookletSerializer

    def get_queryset(self):
        exam_id = self.kwargs['exam_id']
        # Exclude booklets already assigned to a Copy with status READY or higher
        # Only show unassigned booklets (for stapling workflow)
        return Booklet.objects.filter(
            exam_id=exam_id
        ).exclude(
            assigned_copy__status__in=[
                Copy.Status.READY,
                Copy.Status.LOCKED,
                Copy.Status.GRADING_IN_PROGRESS,
                Copy.Status.GRADED
            ]
        ).order_by('start_page')

class ExamListView(generics.ListCreateAPIView):
    permission_classes = [IsTeacherOrAdmin]  # Teacher/Admin only
    queryset = Exam.objects.all().order_by('-date')
    serializer_class = ExamSerializer

    # Phase 2: Add pagination
    from rest_framework.pagination import PageNumberPagination

    class ExamPagination(PageNumberPagination):
        page_size = 50
        page_size_query_param = 'page_size'
        max_page_size = 200

    pagination_class = ExamPagination

class BookletDetailView(generics.RetrieveDestroyAPIView):
    queryset = Booklet.objects.all()
    serializer_class = BookletSerializer
    permission_classes = [IsTeacherOrAdmin]
    lookup_field = 'id'

    def perform_destroy(self, instance):
        # Mission 1.3: Prevent modification if attached to a locked/graded copy
        if instance.assigned_copy.exclude(status=Copy.Status.STAGING).exists():
             raise 	serializers.ValidationError(
                 {"error": _("Impossible de supprimer un fascicule associé à une copie validée ou corrigée.")}
             )
        instance.delete()


class BookletHeaderView(APIView):
    """
    Retourne l'image de l'en-tête d'un booklet pour l'identification.
    GET /api/exams/booklets/<id>/header/
    """
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, id):
        from django.http import FileResponse
        from django.conf import settings
        import os

        booklet = get_object_or_404(Booklet, id=id)
        
        # Chercher l'image d'en-tête dans les pages_images
        if booklet.pages_images and len(booklet.pages_images) > 0:
            first_page_path = booklet.pages_images[0]
            full_path = os.path.join(settings.MEDIA_ROOT, first_page_path)
            
            if os.path.exists(full_path):
                # Extraire la région d'en-tête (top 20%)
                import cv2
                img = cv2.imread(full_path)
                if img is not None:
                    height = img.shape[0]
                    header_height = int(height * 0.25)
                    header = img[:header_height, :]

                    # Encode to PNG in memory
                    from io import BytesIO
                    _, buffer = cv2.imencode('.png', header)
                    image_bytes = BytesIO(buffer.tobytes())

                    response = FileResponse(
                        image_bytes,
                        content_type='image/png'
                    )
                    response['Content-Disposition'] = f'inline; filename="header_{id}.png"'

                    return response
        
        # Fallback: extraire depuis le PDF source
        if booklet.exam.pdf_source:
            page_index = booklet.start_page - 1 if booklet.start_page else 0
            
            try:
                doc = fitz.open(booklet.exam.pdf_source.path)
                if 0 <= page_index < doc.page_count:
                    page = doc.load_page(page_index)
                    pix = page.get_pixmap(dpi=150)
                    
                    # Crop top 25% for header
                    import io
                    from PIL import Image
                    
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    header_height = int(img.height * 0.25)
                    header = img.crop((0, 0, img.width, header_height))
                    
                    buffer = io.BytesIO()
                    header.save(buffer, format='PNG')
                    buffer.seek(0)
                    
                    doc.close()
                    
                    return FileResponse(
                        buffer,
                        content_type='image/png',
                        filename=f'header_{id}.png'
                    )
                doc.close()
            except Exception as e:
                from core.utils.errors import safe_error_response
                return Response(
                    safe_error_response(e, context="Header extraction"),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response({"error": "No header image available"}, status=status.HTTP_404_NOT_FOUND)


class BookletSplitView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, id):
        booklet = get_object_or_404(Booklet, id=id)
        
        # Mission 1.3: Protocol Enforce
        if booklet.assigned_copy.exclude(status=Copy.Status.STAGING).exists():
             return Response(
                 {"error": _("Impossible de scinder un fascicule associé à une copie validée.")},
                 status=status.HTTP_403_FORBIDDEN
             )

        if not booklet.exam.pdf_source:
             return Response({"error": "No PDF source found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Determine source page index
        page_index = booklet.start_page - 1
        
        import tempfile
        import os
        from processing.services.splitter import A3Splitter

        try:
            doc = fitz.open(booklet.exam.pdf_source.path)
            if page_index < 0 or page_index >= doc.page_count:
                return Response({"error": "Page out of range"}, status=status.HTTP_404_NOT_FOUND)
                
            page = doc.load_page(page_index)
            pix = page.get_pixmap(dpi=150)
            
            fd, temp_path = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            pix.save(temp_path)
            
            # Use Splitter Service
            splitter = A3Splitter()
            result = splitter.process_scan(temp_path)
            
            return Response({
                "message": "Split analysis complete",
                "type": result.get('type'),
                "has_header": result.get('has_header', False)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            from core.utils.errors import safe_error_response
            return Response(
                safe_error_response(e, context="Page analysis", user_message="Failed to analyze page."),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)

class ExamDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsTeacherOrAdmin]  # Teacher/Admin only
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    lookup_field = 'id'


class CopyListView(generics.ListAPIView):
    """
    Liste les copies d'un examen.
    Les admins voient toutes les copies, les enseignants ne voient que leurs copies assignées.
    """
    permission_classes = [IsTeacherOrAdmin]  # Teacher/Admin only
    serializer_class = CopySerializer

    # Phase 2: Add pagination for large exams
    from rest_framework.pagination import PageNumberPagination

    class CopyPagination(PageNumberPagination):
        page_size = 100
        page_size_query_param = 'page_size'
        max_page_size = 500

    pagination_class = CopyPagination

    def get_queryset(self):
        exam_id = self.kwargs['exam_id']
        user = self.request.user
        
        queryset = Copy.objects.filter(exam_id=exam_id)\
            .select_related('exam', 'student', 'locked_by', 'assigned_corrector')\
            .prefetch_related('booklets', 'annotations__created_by')
        
        # Les admins voient toutes les copies, les enseignants seulement les leurs
        if not (user.is_superuser or user.is_staff or user.groups.filter(name='admin').exists()):
            queryset = queryset.filter(assigned_corrector=user)
        
        return queryset.order_by('anonymous_id')


class MergeBookletsView(APIView):
    permission_classes = [IsAdminOnly]  # Admin only

    def post(self, request, exam_id):
        booklet_ids = request.data.get('booklet_ids', [])
        if not booklet_ids:
            return Response(
                {"error": _("Aucun fascicule sélectionné.")}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        booklets = Booklet.objects.filter(id__in=booklet_ids, exam_id=exam_id)
        if len(booklets) != len(booklet_ids):
             return Response(
                {"error": _("Certains fascicules sont introuvables ou ne correspondent pas à cet examen.")}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # PROTECTION ANTI-DOUBLONS: Vérifier si les booklets sont déjà assignés à une copie
        already_assigned = []
        for booklet in booklets:
            existing_copies = booklet.assigned_copy.exclude(status=Copy.Status.STAGING)
            if existing_copies.exists():
                already_assigned.append({
                    'booklet_id': str(booklet.id),
                    'pages': f'{booklet.start_page}-{booklet.end_page}',
                    'existing_copies': [str(c.id) for c in existing_copies]
                })
        
        if already_assigned:
            return Response({
                "error": _("Certains fascicules sont déjà assignés à des copies existantes."),
                "already_assigned": already_assigned
            }, status=status.HTTP_400_BAD_REQUEST)

        # NETTOYAGE: Supprimer les copies STAGING associées aux booklets sélectionnés
        # Ces copies ont été créées automatiquement lors de l'upload (1 copie par booklet)
        # et doivent être remplacées par la copie fusionnée
        staging_copies_to_delete = set()
        for booklet in booklets:
            staging_copies = booklet.assigned_copy.filter(status=Copy.Status.STAGING)
            for staging_copy in staging_copies:
                staging_copies_to_delete.add(staging_copy.id)
        
        if staging_copies_to_delete:
            deleted_count = Copy.objects.filter(id__in=staging_copies_to_delete).delete()[0]
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"MergeBookletsView: Deleted {deleted_count} STAGING copies before merge")

        # Logic: Create Copy -> Assign Booklets
        # Since Copy <-> Booklet relationship is via Booklet.assigned_copy (ManyToMany defined in Copy),
        # we create the Copy and add booklets.
        
        # Generate generic anonymous ID
        import uuid
        anon_id = str(uuid.uuid4())[:8].upper()
        
        copy = Copy.objects.create(
            exam_id=exam_id,
            anonymous_id=anon_id,
            status=Copy.Status.READY
        )
        
        copy.booklets.set(booklets)
        copy.save()
        
        return Response(
            {"message": _("Copie créée avec succès."), "copy_id": copy.id, "anonymous_id": copy.anonymous_id},
            status=status.HTTP_201_CREATED
        )

class ExportAllView(APIView):
    permission_classes = [IsAdminOnly]  # Admin only

    def post(self, request, id):
        exam = get_object_or_404(Exam, id=id)

        # Phase 3: Use async task instead of synchronous loop
        from grading.tasks import async_export_all_copies

        # Queue async task for background processing
        result = async_export_all_copies.delay(str(id), request.user.id)

        copies_count = exam.copies.count()

        return Response({
            "task_id": result.id,
            "message": f"Export of {copies_count} copies queued. Use task_id to check status.",
            "status_url": f"/api/tasks/{result.id}/status/",
            "copies_count": copies_count
        }, status=status.HTTP_202_ACCEPTED)

class CSVExportView(APIView):
    """
    Export CSV des résultats d'un examen.
    
    PRD-19 Guarantees:
    - Une ligne par élève (pas de doublons)
    - Encoding UTF-8 avec BOM pour Excel
    - Format stable et documenté
    - Inclut uniquement les copies GRADED ou avec note
    """
    permission_classes = [IsAdminOnly]

    def get(self, request, id):
        import csv
        from django.http import HttpResponse
        from grading.services import GradingService
        from django.db.models import Max
        
        exam = get_object_or_404(Exam, id=id)
        
        # PRD-19: Filtrer pour n'avoir qu'une copie par élève
        # Si plusieurs copies existent pour le même élève, prendre celle avec le statut le plus avancé
        # Priorité: GRADED > LOCKED > READY > autres
        status_priority = {
            Copy.Status.GRADED: 1,
            Copy.Status.LOCKED: 2,
            Copy.Status.GRADING_IN_PROGRESS: 3,
            Copy.Status.READY: 4,
            Copy.Status.GRADING_FAILED: 5,
            Copy.Status.STAGING: 6,
        }
        
        # Récupérer toutes les copies identifiées
        identified_copies = exam.copies.filter(
            is_identified=True,
            student__isnull=False
        ).select_related('student').order_by('student_id', 'graded_at')
        
        # Dédupliquer par élève (garder la copie avec le meilleur statut)
        seen_students = {}
        for copy in identified_copies:
            student_id = copy.student_id
            if student_id not in seen_students:
                seen_students[student_id] = copy
            else:
                existing = seen_students[student_id]
                # Garder la copie avec le meilleur statut
                if status_priority.get(copy.status, 99) < status_priority.get(existing.status, 99):
                    seen_students[student_id] = copy
                # Si même statut, garder celle qui est notée (graded_at non null)
                elif copy.status == existing.status and copy.graded_at and not existing.graded_at:
                    seen_students[student_id] = copy
        
        # Récupérer aussi les copies non identifiées (pour traçabilité)
        unidentified_copies = exam.copies.filter(
            is_identified=False
        ).exclude(status=Copy.Status.STAGING)
        
        # Préparer la réponse CSV avec BOM UTF-8 pour Excel
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="exam_{id}_results.csv"'
        response['X-Content-Type-Options'] = 'nosniff'
        
        writer = csv.writer(response, delimiter=';')  # Point-virgule pour Excel FR
        
        # Header enrichi
        header = [
            'Anonymat',
            'Nom Élève',
            'Date Naissance',
            'Statut',
            'Note Totale',
            'Identifié',
            'Corrigé le'
        ]
        writer.writerow(header)
        
        # Écrire les copies identifiées (une par élève)
        for student_id, copy in sorted(seen_students.items(), key=lambda x: x[1].student.full_name if x[1].student else ''):
            student = copy.student
            total = GradingService.compute_score(copy)
            
            row = [
                copy.anonymous_id,
                student.full_name if student else 'Inconnu',
                student.date_of_birth.strftime('%d/%m/%Y') if student and student.date_of_birth else '',
                copy.get_status_display(),
                total,
                'Oui',
                copy.graded_at.strftime('%d/%m/%Y %H:%M') if copy.graded_at else ''
            ]
            writer.writerow(row)
        
        # Écrire les copies non identifiées
        for copy in unidentified_copies:
            total = GradingService.compute_score(copy)
            row = [
                copy.anonymous_id,
                'NON IDENTIFIÉ',
                '',
                copy.get_status_display(),
                total,
                'Non',
                copy.graded_at.strftime('%d/%m/%Y %H:%M') if copy.graded_at else ''
            ]
            writer.writerow(row)
        
        return response

class CopyIdentificationView(APIView):
    permission_classes = [IsTeacherOrAdmin]  # Teacher/Admin only

    def post(self, request, id):
        # Mission 17: Identify Copy
        from students.models import Student

        copy = get_object_or_404(Copy, id=id)
        student_id = request.data.get('student_id')

        if not student_id:
            return Response({"error": "Student ID required"}, status=status.HTTP_400_BAD_REQUEST)

        student = get_object_or_404(Student, id=student_id)

        copy.student = student
        copy.is_identified = True
        copy.save()

        return Response({"message": "Identification successful"}, status=status.HTTP_200_OK)

class UnidentifiedCopiesView(APIView):
    permission_classes = [IsTeacherOrAdmin]  # Teacher/Admin only

    def get(self, request, id):
        # Mission 18: List unidentified copies for Video-Coding
        # Mission 21 Update: Use dynamic header URL
        # ZF-AUD-13: Prefetch to avoid N+1
        # PHASE 2 SECURITY FIX: Verify user has access to this exam
        exam = get_object_or_404(Exam, id=id)

        # Check if user is admin or corrector for this exam
        if not request.user.is_staff and not exam.correctors.filter(id=request.user.id).exists():
            return Response(
                {"error": "You don't have access to this exam"},
                status=status.HTTP_403_FORBIDDEN
            )

        copies = Copy.objects.filter(exam_id=id, is_identified=False)\
            .prefetch_related('booklets')
        data = []
        for c in copies:
            booklet = c.booklets.order_by('start_page').first()
            header_url = None
            if booklet:
                # Dynamic URL
                header_url = f"/api/booklets/{booklet.id}/header/"
            
            data.append({
                "id": c.id,
                "anonymous_id": c.anonymous_id,
                "header_image_url": header_url,
                "status": c.status
            })
        return Response(data)

class StudentCopiesView(generics.ListAPIView):
    from .permissions import IsStudent
    permission_classes = [IsStudent]

    def get_queryset(self):
        # Try to get student_id from session (legacy) or from user association (new)
        student_id = self.request.session.get('student_id')
        if student_id:
            # Legacy method: using session
            return Copy.objects.filter(student=student_id, status=Copy.Status.GRADED)
        else:
            # New method: get student via user association
            try:
                from students.models import Student
                student = Student.objects.get(user=self.request.user)
                return Copy.objects.filter(student=student, status=Copy.Status.GRADED)
            except Student.DoesNotExist:
                return Copy.objects.none()

    def list(self, request, *args, **kwargs):
        from grading.services import GradingService
        from core.utils.audit import log_data_access
        
        queryset = self.get_queryset()
        
        # Audit trail: Accès liste copies élève
        student_id = request.session.get('student_id')
        if student_id:
            log_data_access(request, 'Copy', f'student_{student_id}_list', action_detail='list')
        
        data = []
        for copy in queryset:
            total_score = GradingService.compute_score(copy)
            # Detailed scores not yet implemented in Annotation model linking to Question ID
            # For MVP, we just show total.
            scores_data = {} 
            
            data.append({
                "id": copy.id,
                "exam_name": copy.exam.name,
                "date": copy.exam.date,
                "total_score": total_score,
                "status": copy.status,
                "final_pdf_url": f"/api/grading/copies/{copy.id}/final-pdf/" if copy.final_pdf else None,
                "scores_details": scores_data
            })
        return Response(data)
class ExamSourceUploadView(APIView):
    permission_classes = [IsAdminOnly]
    parser_classes = (MultiPartParser, FormParser)

    @method_decorator(maybe_ratelimit(key='user', rate='20/h', method='POST', block=True))
    def post(self, request, pk):
        exam = get_object_or_404(Exam, pk=pk)
        
        # Update PDF
        if 'pdf_source' in request.FILES:
            exam.pdf_source = request.FILES['pdf_source']
            exam.save()
            
            # Trigger Processing
            try:
                from processing.services.pdf_splitter import PDFSplitter
                splitter = PDFSplitter(dpi=150)
                booklets = splitter.split_exam(exam)
                
                # Create Copies (Staging)
                import uuid
                import logging
                logger = logging.getLogger(__name__)
                
                created_count = 0
                for booklet in booklets:
                    # Avoid duplicates if reprocessing?
                    # For MVP, just create new copies.
                    copy = Copy.objects.create(
                        exam=exam,
                        anonymous_id=str(uuid.uuid4())[:8].upper(),
                        status=Copy.Status.STAGING,
                        is_identified=False
                    )
                    copy.booklets.add(booklet)
                    created_count += 1
                
                return Response({
                    "message": f"PDF uploaded and processed. {created_count} booklets created.",
                    "booklets_created": created_count
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                from core.utils.errors import safe_error_response
                return Response(
                    safe_error_response(e, context="PDF upload", user_message="Failed to process PDF upload."),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response({"error": "pdf_source field required"}, status=status.HTTP_400_BAD_REQUEST)
class CopyValidationView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, id):
        copy = get_object_or_404(Copy, id=id)
        
        try:
             # Use service to validate
             from grading.services import GradingService
             GradingService.validate_copy(copy, request.user)
             return Response({"message": "Copy validated and ready for grading.", "status": copy.status})
        except ValueError as e:
             return Response({"error": "Invalid copy state"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
             from core.utils.errors import safe_error_response
             return Response(
                 safe_error_response(e, context="Copy validation", user_message="Failed to validate copy."),
                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
             )

class CorrectorCopiesView(generics.ListAPIView):
    """
    List copies assigned to the current corrector.
    GET /api/copies/
    Admins see all copies, teachers see only their assigned copies.
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = CorrectorCopySerializer

    # Phase 2: Add pagination
    from rest_framework.pagination import PageNumberPagination

    class CorrectorCopyPagination(PageNumberPagination):
        page_size = 50
        page_size_query_param = 'page_size'
        max_page_size = 200

    pagination_class = CorrectorCopyPagination

    def get_queryset(self):
        user = self.request.user

        queryset = Copy.objects.filter(
            status__in=[Copy.Status.READY, Copy.Status.LOCKED, Copy.Status.GRADED]
        ).select_related('exam', 'assigned_corrector')\
         .prefetch_related('booklets', 'annotations')  # PHASE 2 FIX: Added booklets prefetch
        
        # Les admins voient toutes les copies, les enseignants seulement les leurs
        if not (user.is_superuser or user.is_staff or user.groups.filter(name='admin').exists()):
            queryset = queryset.filter(assigned_corrector=user)
        
        return queryset.order_by('exam__date', 'anonymous_id')

class CorrectorCopyDetailView(generics.RetrieveAPIView):
    """
    Permet au correcteur de récupérer les détails d'une copie spécifique.
    """
    queryset = Copy.objects.select_related('exam', 'locked_by')\
        .prefetch_related('booklets', 'annotations__created_by')
    serializer_class = CorrectorCopySerializer
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]
    lookup_field = 'id'


class ExamDispatchView(APIView):
    """
    Dispatches unassigned copies to correctors fairly and randomly.
    POST /api/exams/<exam_id>/dispatch/
    
    PRD-19 Guarantees:
    - Idempotent: re-running dispatch only assigns new unassigned copies
    - Race-condition safe: uses select_for_update to prevent double assignment
    - No duplicate assignments: filters assigned_corrector__isnull=True
    - Audit trail: logs run_id for each dispatch operation
    """
    permission_classes = [IsAdminOnly]

    def post(self, request, exam_id):
        from django.db import transaction
        from django.utils import timezone
        import uuid
        import random
        import logging

        logger = logging.getLogger(__name__)

        exam = get_object_or_404(Exam, id=exam_id)

        correctors = list(exam.correctors.all())
        if not correctors:
            return Response(
                {"error": _("Aucun correcteur assigné à cet examen.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        run_id = uuid.uuid4()
        now = timezone.now()

        try:
            with transaction.atomic():
                # PRD-19: Lock copies to prevent race conditions
                # select_for_update ensures no other dispatch can modify these copies
                unassigned_copies = list(
                    Copy.objects.select_for_update(skip_locked=True).filter(
                        exam=exam,
                        assigned_corrector__isnull=True,
                        status=Copy.Status.READY
                    ).order_by('anonymous_id')
                )

                if not unassigned_copies:
                    return Response(
                        {"message": _("Aucune copie à dispatcher.")},
                        status=status.HTTP_200_OK
                    )

                # Shuffle for fair random distribution
                random.shuffle(unassigned_copies)

                # PRD-19: Balance distribution based on current load
                # Count existing assignments per corrector for this exam
                from django.db.models import Count
                current_load = dict(
                    Copy.objects.filter(exam=exam, assigned_corrector__isnull=False)
                    .values('assigned_corrector')
                    .annotate(count=Count('id'))
                    .values_list('assigned_corrector', 'count')
                )

                distribution = {corrector.id: current_load.get(corrector.id, 0) for corrector in correctors}
                assignments = []

                for copy in unassigned_copies:
                    # Assign to corrector with lowest current load
                    corrector = min(correctors, key=lambda c: distribution[c.id])
                    copy.assigned_corrector = corrector
                    copy.dispatch_run_id = run_id
                    copy.assigned_at = now
                    assignments.append(copy)
                    distribution[corrector.id] += 1

                # Bulk update with explicit fields
                Copy.objects.bulk_update(
                    assignments,
                    ['assigned_corrector', 'dispatch_run_id', 'assigned_at']
                )

                logger.info(
                    f"Dispatch completed for exam {exam_id}: "
                    f"{len(assignments)} copies assigned to {len(correctors)} correctors. "
                    f"Run ID: {run_id}"
                )

            # Calculate final distribution stats
            final_distribution = {
                corrector.username: distribution[corrector.id]
                for corrector in correctors
            }

            return Response({
                "message": _("Dispatch effectué avec succès."),
                "dispatch_run_id": str(run_id),
                "copies_assigned": len(assignments),
                "correctors_count": len(correctors),
                "distribution": final_distribution,
                "min_assigned": min(distribution.values()) if distribution else 0,
                "max_assigned": max(distribution.values()) if distribution else 0
            }, status=status.HTTP_200_OK)

        except Exception as e:
            from core.utils.errors import safe_error_response
            logger.error(f"Dispatch failed for exam {exam_id}: {str(e)}")
            return Response(
                safe_error_response(e, context="Copy dispatch", user_message="Failed to dispatch copies."),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

