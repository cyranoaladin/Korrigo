from rest_framework import viewsets, status, generics, serializers # Added serializers import
from rest_framework.views import APIView

# ... (omitted)


from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.utils.decorators import method_decorator
from django.db import transaction
from core.utils.ratelimit import maybe_ratelimit
from .models import Exam, Booklet, Copy, ExamPDF
from .serializers import ExamSerializer, BookletSerializer, CopySerializer, ExamPDFSerializer
from processing.services.vision import HeaderDetector
from grading.services import GradingService
from .permissions import IsTeacherOrAdmin

import fitz  # PyMuPDF
import logging
import os
import uuid


def generate_anonymous_id(exam, index: int) -> str:
    """
    Generate a collision-free sequential anonymous ID for a copy within an exam.
    Format: XXXX-NNN where XXXX = first 4 chars of exam UUID, NNN = sequential number.
    Falls back to longer UUID segment if collision detected.
    """
    prefix = str(exam.id).replace('-', '')[:4].upper()
    existing_count = Copy.objects.filter(exam=exam).count()
    seq = existing_count + index + 1
    candidate = f"{prefix}-{seq:03d}"
    # Safety: check uniqueness, extend if collision
    if Copy.objects.filter(anonymous_id=candidate).exists():
        candidate = f"{prefix}-{str(uuid.uuid4()).replace('-', '')[:6].upper()}"
    return candidate

class ExamUploadView(APIView):
    permission_classes = [IsTeacherOrAdmin]  # Teacher/Admin only
    parser_classes = (MultiPartParser, FormParser)

    @method_decorator(maybe_ratelimit(key='user', rate='20/h', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        logger = logging.getLogger(__name__)
        serializer = ExamSerializer(data=request.data)
        
        # Validate serializer and handle errors
        if not serializer.is_valid():
            errors = serializer.errors
            
            # Check for file_too_large error → return HTTP 413 instead of 400
            if 'pdf_source' in errors:
                pdf_errors = errors['pdf_source']
                for error in pdf_errors:
                    if hasattr(error, 'code') and error.code == 'file_too_large':
                        logger.warning(f"Upload rejected: file too large (user: {request.user.username})")
                        return Response(
                            {"error": str(error)},
                            status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                        )
            
            # Log other validation errors
            logger.warning(f"Upload validation failed (user: {request.user.username}): {errors}")
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Log upload initiation
        upload_mode = serializer.validated_data.get('upload_mode', Exam.UploadMode.BATCH_A3)
        logger.info(f"Exam upload initiated by user {request.user.username}, mode: {upload_mode}")
        
        # Wrap entire operation in atomic transaction
        try:
            with transaction.atomic():
                # Create exam record
                exam = serializer.save()
                logger.info(f"Exam {exam.id} created: {exam.name}, mode: {exam.upload_mode}")
                
                # Handle based on upload mode
                if exam.upload_mode == Exam.UploadMode.BATCH_A3:
                    # BATCH_A3 MODE: Split PDF into booklets and create copies
                    from processing.services.pdf_splitter import PDFSplitter
                    from django.utils import timezone

                    splitter = PDFSplitter(dpi=150)
                    booklets = splitter.split_exam(exam)
                    logger.info(f"PDF split into {len(booklets)} booklets for exam {exam.id}")

                    # Create copies and auto-validate (STAGING→READY) since pages exist after split
                    for i, booklet in enumerate(booklets):
                        has_pages = booklet.pages_images and len(booklet.pages_images) > 0
                        copy = Copy.objects.create(
                            exam=exam,
                            anonymous_id=generate_anonymous_id(exam, i),
                            status=Copy.Status.READY if has_pages else Copy.Status.STAGING,
                            is_identified=False,
                            validated_at=timezone.now() if has_pages else None
                        )
                        copy.booklets.add(booklet)
                        logger.info(f"Copy {copy.id} ({copy.anonymous_id}) created as {copy.status} for booklet {booklet.id}")

                    # Log successful completion
                    logger.info(f"Exam upload completed successfully: {exam.id} with {len(booklets)} booklets")
                    
                    return Response({
                        **serializer.data,
                        "booklets_created": len(booklets),
                        "message": f"{len(booklets)} copies créées et prêtes à corriger"
                    }, status=status.HTTP_201_CREATED)
                
                elif exam.upload_mode == Exam.UploadMode.INDIVIDUAL_A4:
                    # INDIVIDUAL_A4 MODE: Exam created, individual PDFs will be uploaded separately
                    logger.info(f"Exam {exam.id} created in INDIVIDUAL_A4 mode. Waiting for individual PDF uploads.")
                    
                    return Response({
                        **serializer.data,
                        "message": _("Examen créé. Vous pouvez maintenant uploader les fichiers PDF individuels."),
                        "upload_endpoint": f"/api/exams/{exam.id}/upload-individual-pdfs/"
                    }, status=status.HTTP_201_CREATED)

        except Exception as e:
            from core.utils.errors import safe_error_response
            
            # Log error with full context
            logger.error(
                f"Exam upload failed for user {request.user.username}, "
                f"file: {request.FILES.get('pdf_source', 'unknown')}, "
                f"error: {str(e)}", 
                exc_info=True
            )
            
            # Cleanup uploaded file if exam was partially created
            # Note: transaction.atomic() already rolled back DB changes
            # But we need to clean up the uploaded file from filesystem
            if 'exam' in locals():
                # Clean up PDF source
                if exam.pdf_source and hasattr(exam.pdf_source, 'path'):
                    try:
                        if os.path.exists(exam.pdf_source.path):
                            os.remove(exam.pdf_source.path)
                            logger.info(f"Cleaned up orphaned file: {exam.pdf_source.path}")
                    except Exception as cleanup_error:
                        logger.error(f"Failed to cleanup PDF file: {cleanup_error}")
                
                # P11 FIX: Clean up extracted PNG images
                import shutil
                from django.conf import settings as django_settings
                booklet_dir = os.path.join(django_settings.MEDIA_ROOT, 'booklets', str(exam.id))
                if os.path.exists(booklet_dir):
                    try:
                        shutil.rmtree(booklet_dir)
                        logger.info(f"Cleaned up orphaned booklet images: {booklet_dir}")
                    except Exception as cleanup_error:
                        logger.error(f"Failed to cleanup booklet images: {cleanup_error}")
            
            # Return user-friendly error with safe_error_response
            return Response(
                safe_error_response(
                    e, 
                    context="Traitement PDF", 
                    user_message="Échec du traitement du PDF. Veuillez vérifier que le fichier est valide et réessayer."
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class IndividualPDFUploadView(APIView):
    """
    Upload multiple individual PDF files for an exam in INDIVIDUAL_A4 mode.
    POST /api/exams/<exam_id>/upload-individual-pdfs/
    Supports uploading multiple files simultaneously.
    
    Limits: Max 100 files per request to prevent DoS
    """
    permission_classes = [IsTeacherOrAdmin]
    parser_classes = (MultiPartParser, FormParser)
    
    MAX_FILES_PER_REQUEST = 100

    @method_decorator(maybe_ratelimit(key='user', rate='50/h', method='POST', block=True))
    def post(self, request, exam_id):
        logger = logging.getLogger(__name__)
        exam = get_object_or_404(Exam, id=exam_id)
        
        # Verify exam is in INDIVIDUAL_A4 mode
        if exam.upload_mode != Exam.UploadMode.INDIVIDUAL_A4:
            return Response(
                {"error": _("Cet examen n'est pas en mode INDIVIDUAL_A4. Utilisez l'endpoint d'upload standard.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all uploaded PDF files (can be multiple)
        uploaded_files = request.FILES.getlist('pdf_files')
        
        if not uploaded_files:
            return Response(
                {"error": _("Aucun fichier PDF uploadé. Utilisez le champ 'pdf_files'.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Limit number of files per request
        if len(uploaded_files) > self.MAX_FILES_PER_REQUEST:
            return Response(
                {"error": _(f"Trop de fichiers. Maximum {self.MAX_FILES_PER_REQUEST} fichiers par requête.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"Individual PDF upload for exam {exam_id}: {len(uploaded_files)} files by user {request.user.username}")
        
        created_copies = []
        
        try:
            with transaction.atomic():
                for i, pdf_file in enumerate(uploaded_files):
                    # Extract student identifier from filename (optional)
                    filename = pdf_file.name
                    student_identifier = os.path.splitext(filename)[0] if filename else None
                    
                    # Create ExamPDF record for tracking
                    exam_pdf = ExamPDF.objects.create(
                        exam=exam,
                        pdf_file=pdf_file,
                        student_identifier=student_identifier
                    )
                    
                    # Create Copy in STAGING status (using exam_pdf.pdf_file as reference)
                    copy = Copy.objects.create(
                        exam=exam,
                        anonymous_id=generate_anonymous_id(exam, i),
                        status=Copy.Status.STAGING,
                        is_identified=False,
                        pdf_source=exam_pdf.pdf_file
                    )
                    
                    created_copies.append({
                        'exam_pdf_id': str(exam_pdf.id),
                        'copy_id': str(copy.id),
                        'filename': filename,
                        'student_identifier': student_identifier
                    })
                    
                    logger.info(f"Created ExamPDF {exam_pdf.id} and Copy {copy.id} for {filename}")
                
                logger.info(f"Successfully uploaded {len(created_copies)} individual PDFs for exam {exam_id}")
                
                return Response({
                    "message": f"{len(created_copies)} fichiers PDF uploadés avec succès",
                    "uploaded_files": created_copies,
                    "total_copies": exam.copies.count()
                }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            from core.utils.errors import safe_error_response
            logger.error(f"Individual PDF upload failed for exam {exam_id}: {str(e)}", exc_info=True)
            
            return Response(
                safe_error_response(
                    e,
                    context="Upload de PDFs individuels",
                    user_message="Échec de l'upload des fichiers PDF. Veuillez vérifier que tous les fichiers sont valides."
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
    
    # P10 FIX: Add pagination (returns all if no page param, paginated otherwise)
    from rest_framework.pagination import PageNumberPagination
    
    class ExamPagination(PageNumberPagination):
        page_size = 50
        page_size_query_param = 'page_size'
        max_page_size = 200
    
    pagination_class = ExamPagination

class BookletHeaderView(APIView):
    """
    Serve the header image for a booklet.
    If header_image exists, serve it directly.
    Otherwise, crop the top ~25% of the first page image as header.
    """
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, id):
        from django.http import FileResponse, HttpResponse
        from PIL import Image as PILImage
        from io import BytesIO
        from django.conf import settings

        booklet = get_object_or_404(Booklet, id=id)

        # Case 1: header_image exists
        if booklet.header_image:
            try:
                return FileResponse(
                    booklet.header_image.open('rb'),
                    content_type='image/jpeg'
                )
            except Exception:
                pass

        # Case 2: Crop top of first page
        if booklet.pages_images:
            first_page = booklet.pages_images[0]
            # Try media root
            full_path = os.path.join(settings.MEDIA_ROOT, first_page)
            if not os.path.exists(full_path):
                full_path = first_page  # absolute path fallback

            if os.path.exists(full_path):
                try:
                    with PILImage.open(full_path) as img:
                        w, h = img.size
                        # Crop top 25% of the page (where student name typically is)
                        crop_box = (0, 0, w, int(h * 0.25))
                        header_crop = img.crop(crop_box)

                        buffer = BytesIO()
                        header_crop.save(buffer, format='JPEG', quality=85)
                        buffer.seek(0)

                        return HttpResponse(
                            buffer.read(),
                            content_type='image/jpeg'
                        )
                except Exception as e:
                    logger.error(f"BookletHeaderView crop failed: {e}")

        return HttpResponse(status=404)


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
             return Response(
                 {"error": _("Le PDF source n'est pas disponible pour cet examen")},
                 status=status.HTTP_404_NOT_FOUND
             )
        
        # Determine source page index
        page_index = booklet.start_page - 1
        
        import tempfile
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
        
        # Generate collision-free anonymous ID
        exam = get_object_or_404(Exam, id=exam_id)
        anon_id = generate_anonymous_id(exam, 0)
        
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
        base_filter = {
            'status': Copy.Status.GRADED,
            'exam__results_released_at__isnull': False,
        }
        if student_id:
            return Copy.objects.filter(student=student_id, **base_filter)
        else:
            try:
                from students.models import Student
                student = Student.objects.get(user=self.request.user)
                return Copy.objects.filter(student=student, **base_filter)
            except Student.DoesNotExist:
                return Copy.objects.none()

    def list(self, request, *args, **kwargs):
        from grading.models import Score, QuestionRemark
        from grading.services import GradingService
        from core.utils.audit import log_data_access

        queryset = self.get_queryset()

        # Audit trail
        student_id = request.session.get('student_id')
        if student_id:
            log_data_access(request, 'Copy', f'student_{student_id}_list', action_detail='list')

        data = []
        for copy in queryset:
            total_score = GradingService.compute_score(copy)

            # Get detailed scores from Score model
            scores_data = {}
            score_obj = Score.objects.filter(copy=copy).first()
            if score_obj and score_obj.scores_data:
                scores_data = score_obj.scores_data

            # Get question remarks
            remarks = {}
            for remark in QuestionRemark.objects.filter(copy=copy):
                remarks[remark.question_id] = remark.remark

            data.append({
                "id": copy.id,
                "exam_name": copy.exam.name,
                "date": copy.exam.date,
                "total_score": total_score,
                "status": copy.status,
                "final_pdf_url": f"/api/grading/copies/{copy.id}/final-pdf/" if copy.final_pdf else None,
                "scores_details": scores_data,
                "remarks": remarks,
                "global_appreciation": copy.global_appreciation or '',
            })
        return Response(data)
class ExamSourceUploadView(APIView):
    permission_classes = [IsTeacherOrAdmin]
    parser_classes = (MultiPartParser, FormParser)

    @method_decorator(maybe_ratelimit(key='user', rate='20/h', method='POST', block=True))
    def post(self, request, pk):
        logger = logging.getLogger(__name__)
        exam = get_object_or_404(Exam, pk=pk)
        
        if 'pdf_source' not in request.FILES:
            return Response({"error": "pdf_source field required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # P3 FIX: Block re-upload if non-STAGING copies exist (already being corrected)
        non_staging_copies = exam.copies.exclude(status=Copy.Status.STAGING).count()
        if non_staging_copies > 0:
            return Response(
                {"error": _(f"Impossible de re-uploader: {non_staging_copies} copie(s) sont déjà en cours de traitement ou corrigées.")},
                status=status.HTTP_409_CONFLICT
            )
        
        try:
            with transaction.atomic():
                # P3 FIX: Clean up existing STAGING copies and booklets before re-processing
                existing_staging = exam.copies.filter(status=Copy.Status.STAGING)
                if existing_staging.exists():
                    logger.info(f"Cleaning up {existing_staging.count()} existing STAGING copies for exam {exam.id}")
                    existing_staging.delete()
                
                # Clean up existing booklets (PDFSplitter idempotence uses force=True)
                exam.booklets.all().delete()
                
                exam.pdf_source = request.FILES['pdf_source']
                exam.is_processed = False
                exam.save()
                
                from processing.services.pdf_splitter import PDFSplitter
                from django.utils import timezone
                
                splitter = PDFSplitter(dpi=150)
                booklets = splitter.split_exam(exam, force=True)
                
                # Create copies with auto-validation
                created_count = 0
                for i, booklet in enumerate(booklets):
                    has_pages = booklet.pages_images and len(booklet.pages_images) > 0
                    copy = Copy.objects.create(
                        exam=exam,
                        anonymous_id=generate_anonymous_id(exam, i),
                        status=Copy.Status.READY if has_pages else Copy.Status.STAGING,
                        is_identified=False,
                        validated_at=timezone.now() if has_pages else None
                    )
                    copy.booklets.add(booklet)
                    created_count += 1
                
                logger.info(f"Re-upload completed for exam {exam.id}: {created_count} copies created")
                
                return Response({
                    "message": f"PDF uploadé et traité. {created_count} copies créées.",
                    "booklets_created": created_count
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            from core.utils.errors import safe_error_response
            logger.error(f"PDF re-upload failed for exam {exam.id}: {str(e)}", exc_info=True)
            return Response(
                safe_error_response(e, context="PDF upload", user_message="Échec du traitement du PDF."),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
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

class BulkCopyValidationView(APIView):
    """
    Validate all STAGING copies for an exam (STAGING → READY).
    POST /api/exams/<exam_id>/validate-all/
    """
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, exam_id):
        logger = logging.getLogger(__name__)
        exam = get_object_or_404(Exam, id=exam_id)
        
        staging_copies = Copy.objects.filter(exam=exam, status=Copy.Status.STAGING)
        
        if not staging_copies.exists():
            return Response(
                {"message": _("Aucune copie en attente de validation.")},
                status=status.HTTP_200_OK
            )
        
        validated_count = 0
        errors = []
        
        for copy in staging_copies:
            try:
                GradingService.validate_copy(copy, request.user)
                validated_count += 1
            except ValueError as e:
                errors.append({"copy_id": str(copy.id), "error": str(e)})
        
        logger.info(f"Bulk validation for exam {exam_id}: {validated_count} validated, {len(errors)} errors")
        
        return Response({
            "validated": validated_count,
            "errors": errors,
            "message": f"{validated_count} copie(s) validée(s) avec succès."
        }, status=status.HTTP_200_OK)


class CorrectorCopiesView(generics.ListAPIView):
    """
    List copies assigned to the current corrector.
    GET /api/copies/
    Admin sees all copies; teachers see only their assigned ones.
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = CopySerializer
    pagination_class = None  # Frontend expects flat array

    def get_queryset(self):
        user = self.request.user
        base_qs = Copy.objects.filter(
            status__in=[Copy.Status.READY, Copy.Status.LOCKED, Copy.Status.GRADED,
                        Copy.Status.GRADING_IN_PROGRESS]
        ).select_related('exam').order_by('exam__date', 'anonymous_id')

        # Admin sees all; teacher sees only assigned
        if user.is_superuser:
            return base_qs
        return base_qs.filter(assigned_corrector=user)

class CorrectorCopyDetailView(generics.RetrieveUpdateAPIView):
    """
    Permet au correcteur de récupérer et mettre à jour les détails d'une copie.
    GET  /api/copies/<id>/  → détails complets
    PATCH /api/copies/<id>/ → mise à jour partielle (ex: subject_variant)
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

        # P12 FIX: Only dispatch READY copies (not STAGING or already processed)
        unassigned_copies = list(
            Copy.objects.filter(
                exam=exam,
                assigned_corrector__isnull=True,
                status__in=[Copy.Status.READY, Copy.Status.STAGING]
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


class PronoteExportView(APIView):
    """
    Export exam grades in PRONOTE CSV format (admin only).
    
    POST /api/exams/<id>/export-pronote/
    
    Request body (optional):
        {
            "coefficient": 1.0  // Override default coefficient
        }
    
    Response:
        - 200 OK: CSV file download
        - 400 Bad Request: Validation errors (ungraded copies, unidentified students, etc.)
        - 403 Forbidden: Non-admin user
        - 404 Not Found: Exam not found
        - 429 Too Many Requests: Rate limit exceeded (10/hour)
    
    Audit:
        Logs all export attempts (success/failure) with user, exam, timestamp
    """
    permission_classes = [IsAuthenticated]

    @method_decorator(maybe_ratelimit(key='user', rate='10/h', method='POST', block=True))
    def post(self, request, id):
        from core.auth import IsAdminOnly
        from django.http import HttpResponse
        from core.utils.audit import log_audit
        from exams.services import PronoteExporter
        from exams.services.pronote_export import ValidationError
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Admin-only permission check
        if not IsAdminOnly().has_permission(request, self):
            log_audit(
                request,
                'export.pronote.forbidden',
                'Exam',
                id,
                {'reason': 'Non-admin user attempted PRONOTE export'}
            )
            return Response(
                {"error": _("Accès refusé. Seuls les administrateurs peuvent exporter vers PRONOTE.")},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get exam
        exam = get_object_or_404(Exam, id=id)
        
        # Get optional coefficient from request
        coefficient = request.data.get('coefficient', 1.0)
        try:
            coefficient = float(coefficient)
        except (ValueError, TypeError):
            return Response(
                {"error": _("Coefficient invalide. Doit être un nombre décimal.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create exporter
        exporter = PronoteExporter(exam, coefficient=coefficient)
        
        # Validate export eligibility
        validation = exporter.validate_export_eligibility()
        if not validation.is_valid:
            # Log failed attempt
            log_audit(
                request,
                'export.pronote.failed',
                'Exam',
                exam.id,
                {
                    'exam_name': exam.name,
                    'errors': validation.errors,
                    'coefficient': coefficient
                }
            )
            
            return Response(
                {
                    "error": _("Export impossible"),
                    "details": validation.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate CSV
        try:
            csv_content, warnings = exporter.generate_csv()
        except ValidationError as e:
            # Log failed attempt
            log_audit(
                request,
                'export.pronote.failed',
                'Exam',
                exam.id,
                {
                    'exam_name': exam.name,
                    'error': str(e),
                    'coefficient': coefficient
                }
            )
            
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Log unexpected error
            logger.error(f"Unexpected error during PRONOTE export for exam {exam.id}: {e}", exc_info=True)
            log_audit(
                request,
                'export.pronote.error',
                'Exam',
                exam.id,
                {
                    'exam_name': exam.name,
                    'error': str(e),
                    'coefficient': coefficient
                }
            )
            
            from core.utils.errors import safe_error_response
            return Response(
                safe_error_response(
                    e,
                    context="PRONOTE export",
                    user_message="Erreur lors de l'export. Veuillez réessayer ou contacter le support."
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Count exported grades
        export_count = csv_content.count('\n') - 1  # Minus header
        
        # Log successful export
        log_audit(
            request,
            'export.pronote.success',
            'Exam',
            exam.id,
            {
                'exam_name': exam.name,
                'export_count': export_count,
                'coefficient': coefficient,
                'warnings': warnings
            }
        )
        
        logger.info(
            f"PRONOTE export for exam {exam.id} ({exam.name}) by user {request.user.username}: "
            f"{export_count} grades exported. Warnings: {len(warnings)}"
        )
        
        # Create HTTP response with proper headers
        # Note: csv_content already has UTF-8 BOM from exporter
        response = HttpResponse(
            csv_content.encode('utf-8'),  # Don't re-add BOM
            content_type='text/csv; charset=utf-8'
        )
        
        # Generate safe filename
        safe_filename = exam.name.replace(' ', '_').replace('/', '_')[:50]  # Limit length
        response['Content-Disposition'] = (
            f'attachment; filename="export_pronote_{safe_filename}_{exam.date}.csv"'
        )
        
        # Add warnings to response headers if any (for debugging)
        if warnings:
            response['X-Export-Warnings'] = f"{len(warnings)} warning(s)"
        
        return response


class BulkSubjectVariantView(APIView):
    """
    Assign subject_variant (A/B) to multiple copies of an exam at once.
    POST /api/exams/<exam_id>/bulk-subject-variant/
    Body: { "assignments": { "<copy_id>": "A", "<copy_id>": "B", ... } }
    Or:   { "variant": "A", "copy_ids": ["id1", "id2", ...] }
    """
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, exam_id):
        """Return all copies for this exam with their current subject_variant."""
        exam = get_object_or_404(Exam, id=exam_id)
        copies = Copy.objects.filter(exam=exam).select_related('student').order_by('anonymous_id')
        data = []
        for c in copies:
            data.append({
                'id': str(c.id),
                'anonymous_id': c.anonymous_id,
                'student_name': f"{c.student.last_name} {c.student.first_name}" if c.student else None,
                'subject_variant': c.subject_variant,
                'status': c.status,
            })
        return Response(data)

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        
        assignments = request.data.get('assignments', {})
        variant = request.data.get('variant')
        copy_ids = request.data.get('copy_ids', [])
        
        # Mode 1: bulk assign same variant to list of copy_ids
        if variant and copy_ids:
            if variant not in ('A', 'B'):
                return Response({'error': 'variant must be A or B'}, status=status.HTTP_400_BAD_REQUEST)
            updated = Copy.objects.filter(exam=exam, id__in=copy_ids).update(subject_variant=variant)
            return Response({'updated': updated, 'variant': variant})
        
        # Mode 2: individual assignments dict
        if assignments:
            updated = 0
            errors = []
            for copy_id, var in assignments.items():
                if var not in ('A', 'B', None, ''):
                    errors.append(f"Invalid variant '{var}' for copy {copy_id}")
                    continue
                val = var if var in ('A', 'B') else None
                count = Copy.objects.filter(exam=exam, id=copy_id).update(subject_variant=val)
                updated += count
            result = {'updated': updated}
            if errors:
                result['errors'] = errors
            return Response(result)
        
        return Response({'error': 'Provide assignments or (variant + copy_ids)'}, status=status.HTTP_400_BAD_REQUEST)


class AutoDetectSubjectVariantView(APIView):
    """
    OCR auto-detect subject variant from the reference at the bottom of the last page (annexe).
    POST /api/exams/<exam_id>/auto-detect-subject/
    Convention: BBMATHS... = Sujet A, BBMATH... (no S) = Sujet B
    """
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, exam_id):
        import fitz
        import io
        import os
        import re
        from PIL import Image
        import pytesseract
        import logging
        from django.conf import settings

        logger = logging.getLogger(__name__)
        exam = get_object_or_404(Exam, id=exam_id)

        # Media root: try standard path first, then Docker volume
        media_paths = [
            settings.MEDIA_ROOT,
            '/var/lib/docker/volumes/docker_media_volume/_data',
        ]

        copies = Copy.objects.filter(exam=exam).order_by('anonymous_id')
        results = {'detected': 0, 'failed': 0, 'errors': [], 'copies': []}

        for copy in copies:
            if not copy.pdf_source:
                results['errors'].append({'id': str(copy.id), 'error': 'No PDF source'})
                results['failed'] += 1
                continue

            # Find the actual file
            pdf_path = None
            for base in media_paths:
                candidate = os.path.join(base, copy.pdf_source.name)
                if os.path.exists(candidate):
                    pdf_path = candidate
                    break

            if not pdf_path:
                results['errors'].append({'id': str(copy.id), 'error': 'PDF file not found'})
                results['failed'] += 1
                continue

            try:
                doc = fitz.open(pdf_path)
                last_page = doc[-1]
                # Render bottom 15% at 150 DPI for OCR
                pix = last_page.get_pixmap(dpi=150)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                w, h = img.size
                bottom = img.crop((0, int(h * 0.85), w, h))
                text = pytesseract.image_to_string(bottom, lang="eng")
                doc.close()

                # Detect reference pattern
                text_clean = re.sub(r'[^A-Z0-9]', '', text.upper())
                variant = None
                if re.search(r'BBMATHS', text_clean):
                    variant = 'A'
                elif re.search(r'BBMATH', text_clean):
                    variant = 'B'

                if variant:
                    copy.subject_variant = variant
                    copy.save(update_fields=['subject_variant'])
                    results['detected'] += 1
                else:
                    results['errors'].append({
                        'id': str(copy.id),
                        'anonymous_id': copy.anonymous_id,
                        'error': f'No reference found in OCR text: {text.strip()[:100]}'
                    })
                    results['failed'] += 1

                results['copies'].append({
                    'id': str(copy.id),
                    'anonymous_id': copy.anonymous_id,
                    'subject_variant': variant,
                    'ocr_text': text.strip()[:100],
                })

            except Exception as e:
                logger.error(f"OCR failed for copy {copy.id}: {e}")
                results['errors'].append({'id': str(copy.id), 'error': str(e)[:200]})
                results['failed'] += 1

        return Response(results)

