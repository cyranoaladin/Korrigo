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
from .serializers import ExamSerializer, BookletSerializer, CopySerializer
from processing.services.vision import HeaderDetector
from grading.services import GradingService
from .permissions import IsTeacherOrAdmin

import fitz  # PyMuPDF

class ExamUploadView(APIView):
    permission_classes = [IsTeacherOrAdmin]  # Teacher/Admin only
    parser_classes = (MultiPartParser, FormParser)

    @method_decorator(maybe_ratelimit(key='user', rate='20/h', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        serializer = ExamSerializer(data=request.data)
        if serializer.is_valid():
            exam = serializer.save()

            # REAL-TIME PROCESSING using PDFSplitter
            try:
                from processing.services.pdf_splitter import PDFSplitter

                splitter = PDFSplitter(dpi=150)
                booklets = splitter.split_exam(exam)

                # Créer les copies en statut STAGING (ADR-003)
                import uuid
                import logging
                logger = logging.getLogger(__name__)

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
    permission_classes = [IsTeacherOrAdmin]
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
        return Booklet.objects.filter(exam_id=exam_id).order_by('start_page')

class ExamListView(generics.ListCreateAPIView):
    permission_classes = [IsTeacherOrAdmin]  # Teacher/Admin only
    queryset = Exam.objects.all().order_by('-date')
    serializer_class = ExamSerializer

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
    """
    permission_classes = [IsTeacherOrAdmin]  # Teacher/Admin only
    serializer_class = CopySerializer

    def get_queryset(self):
        exam_id = self.kwargs['exam_id']
        return Copy.objects.filter(exam_id=exam_id)\
            .select_related('exam', 'student', 'locked_by')\
            .prefetch_related('booklets', 'annotations__created_by')\
            .order_by('anonymous_id')


class MergeBookletsView(APIView):
    permission_classes = [IsTeacherOrAdmin]  # Teacher/Admin only

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
    permission_classes = [IsTeacherOrAdmin]  # Teacher/Admin only

    def post(self, request, id):
        exam = get_object_or_404(Exam, id=id)
        # Trigger processing (Sync for MVP)
        from processing.services.pdf_flattener import PDFFlattener
        flattener = PDFFlattener()

        copies = exam.copies.all()
        # Verify related name in Copy model: exam = ForeignKey(Exam) -> default copy_set

        count = 0
        for copy in copies:
             flattener.flatten_copy(copy)
             count += 1

        return Response({"message": f"{count} copies traitées."}, status=status.HTTP_200_OK)

class CSVExportView(APIView):
    permission_classes = [IsTeacherOrAdmin]  # Teacher/Admin only

    def get(self, request, id):
        import csv
        from django.http import HttpResponse
        
        exam = get_object_or_404(Exam, id=id)
        copies = exam.copies.all()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="exam_{id}_results.csv"'
        
        writer = csv.writer(response)
        
        # Dynamic Header based on Grading Structure?
        # For simplicity, we dump just Total and the raw JSON keys present in the first copy
        # Better: iterate all possible keys from exam.grading_structure if possible.
        # MVP: AnonymousID, Total, JSON_Scores
        
        # Mission 3.2: Explicit Mapping
        header = ['AnonymousID', 'Student Name', 'Status', 'Total']
        
        # Attempt to find all keys
        all_keys = set()
        for c in copies:
            if c.scores.exists():
                all_keys.update(c.scores.first().scores_data.keys())
        sorted_keys = sorted(list(all_keys))
        header.extend(sorted_keys)
        
        writer.writerow(header)
        
        for c in copies:
            score_obj = c.scores.first()
            data = score_obj.scores_data if score_obj else {}
            
            # Mission 3.2: Student Name
            student_name = "Inconnu"
            if c.is_identified and c.student:
                 # Check if Student model has name/first_name or just string representation
                 student_name = str(c.student) 
            
            # Calculate total
            total = sum(float(v) for v in data.values() if v)
            
            row = [c.anonymous_id, student_name, c.get_status_display(), total]
            for k in sorted_keys:
                row.append(data.get(k, ''))
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
        copies = Copy.objects.filter(exam_id=id, is_identified=False)
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
    permission_classes = [IsTeacherOrAdmin]
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
    List all copies available for correction (Global List).
    GET /api/copies/
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = CopySerializer

    def get_queryset(self):
        # MVP: Return all copies that are ready/locked/graded
        return Copy.objects.filter(
            status__in=[Copy.Status.READY, Copy.Status.LOCKED, Copy.Status.GRADED]
        ).select_related('exam').order_by('exam__date', 'anonymous_id')

class CorrectorCopyDetailView(generics.RetrieveAPIView):
    """
    Permet au correcteur de récupérer les détails d'une copie spécifique.
    """
    queryset = Copy.objects.select_related('exam', 'student', 'locked_by')\
        .prefetch_related('booklets', 'annotations__created_by')
    serializer_class = CopySerializer
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]
    lookup_field = 'id'


class ExamDispatchView(APIView):
    """
    Dispatches unassigned copies to correctors fairly and randomly.
    POST /api/exams/<exam_id>/dispatch/
    """
    permission_classes = [IsTeacherOrAdmin]

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

        unassigned_copies = list(
            Copy.objects.filter(
                exam=exam,
                assigned_corrector__isnull=True
            ).order_by('anonymous_id')
        )

        if not unassigned_copies:
            return Response(
                {"message": _("Aucune copie à dispatcher.")},
                status=status.HTTP_200_OK
            )

        run_id = uuid.uuid4()
        now = timezone.now()

        random.shuffle(unassigned_copies)

        distribution = {corrector.id: 0 for corrector in correctors}
        assignments = []

        for i, copy in enumerate(unassigned_copies):
            corrector = correctors[i % len(correctors)]
            copy.assigned_corrector = corrector
            copy.dispatch_run_id = run_id
            copy.assigned_at = now
            assignments.append(copy)
            distribution[corrector.id] += 1

        try:
            with transaction.atomic():
                Copy.objects.bulk_update(
                    assignments,
                    ['assigned_corrector', 'dispatch_run_id', 'assigned_at']
                )

                logger.info(
                    f"Dispatch completed for exam {exam_id}: "
                    f"{len(assignments)} copies assigned to {len(correctors)} correctors. "
                    f"Run ID: {run_id}"
                )

            distribution_stats = {
                corrector.username: distribution[corrector.id]
                for corrector in correctors
            }

            return Response({
                "message": _("Dispatch effectué avec succès."),
                "dispatch_run_id": str(run_id),
                "copies_assigned": len(assignments),
                "correctors_count": len(correctors),
                "distribution": distribution_stats,
                "min_assigned": min(distribution.values()),
                "max_assigned": max(distribution.values())
            }, status=status.HTTP_200_OK)

        except Exception as e:
            from core.utils.errors import safe_error_response
            logger.error(f"Dispatch failed for exam {exam_id}: {str(e)}", exc_info=True)
            return Response(
                safe_error_response(e, context="Copy dispatch", user_message="Failed to dispatch copies."),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

