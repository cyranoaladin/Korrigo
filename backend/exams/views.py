from rest_framework import status, generics, serializers # Added serializers import
from rest_framework.views import APIView

# ... (omitted)


from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.utils.decorators import method_decorator
from django.db import transaction
from django.db.models import Count
from core.utils.ratelimit import maybe_ratelimit
from .models import Exam, Booklet, Copy, ExamPDF, ExamType, JuryReport
from .serializers import (
    ExamSerializer, BookletSerializer, CopySerializer, CorrectorCopySerializer,
    ExamTypeSerializer, JuryReportSerializer
)
from grading.services import GradingService
from grading.models import GradingEvent
from .permissions import IsTeacherOrAdmin

import fitz  # PyMuPDF
import logging
from core.auth import UserRole, IsKorrigoAdmin
from exams.score_constraints import Q_MAX_BY_EXAM
import os
import uuid

logger = logging.getLogger(__name__)


def generate_anonymous_id(exam, index: int) -> str:
    """
    Generate a collision-free sequential anonymous ID for a copy within an exam.
    Format: XXXX-NNN where XXXX = first 4 chars of exam UUID, NNN = sequential number.
    Falls back to longer UUID segment if collision detected.
    """
    exam_id_clean: str = str(exam.id).replace('-', '')
    prefix = exam_id_clean[:4].upper()  # type: ignore[misc]
    existing_count = Copy.objects.filter(exam=exam).count()
    seq = existing_count + index + 1
    candidate = f"{prefix}-{seq:03d}"
    # Safety: check uniqueness, extend if collision
    if Copy.objects.filter(anonymous_id=candidate).exists():
        uid_clean: str = str(uuid.uuid4()).replace('-', '')
        candidate = f"{prefix}-{uid_clean[:6].upper()}"  # type: ignore[misc]
    return candidate


def _rotate_copy_last_page(copy: Copy) -> dict[str, object]:
    """
    Rotate the last page image of a copy by 180°.

    The rotated file is written next to the original and only the last page
    entry in the booklet JSON is updated.
    """
    from exams.services.page_rotation import rotate_image_file_180

    booklets = list(copy.booklets.all().order_by('start_page', 'id'))
    for booklet in reversed(booklets):
        if not booklet.pages_images:
            continue
        last_index = len(booklet.pages_images) - 1
        original_path = booklet.pages_images[last_index]
        new_path = rotate_image_file_180(original_path)
        booklet.pages_images[last_index] = new_path
        booklet.save(update_fields=['pages_images'])
        return {
            'copy_id': str(copy.id),
            'anonymous_id': copy.anonymous_id,
            'booklet_id': str(booklet.id),
            'page_index': last_index,
            'original_path': original_path,
            'new_path': new_path,
        }
    raise ValueError("Aucune page trouvée pour cette copie.")


class GlobalStatsView(APIView):
    """GET /api/exams/global-stats/ agrégé global admin."""
    permission_classes = [IsKorrigoAdmin]

    def get(self, request):
        from django.contrib.auth import get_user_model
        from students.models import Student

        User = get_user_model()
        copies_by_status = {
            row['status']: row['count']
            for row in Copy.objects.values('status').annotate(count=Count('id'))
        }

        ready_count = copies_by_status.get(Copy.Status.READY, 0)
        in_progress_count = copies_by_status.get(Copy.Status.IN_PROGRESS, 0)
        finalized_count = copies_by_status.get(Copy.Status.FINALIZED, 0)
        exams_with_results = Exam.objects.filter(results_released_at__isnull=False).count()

        return Response({
            'total_exams': Exam.objects.count(),
            'total_copies': Copy.objects.count(),
            'copies_by_status': {
                'READY': ready_count,
                'IN_PROGRESS': in_progress_count,
                'FINALIZED': finalized_count,
            },
            'ready_count': ready_count,
            'in_progress_count': in_progress_count,
            'finalized_count': finalized_count,
            'students_count': Student.objects.count(),
            'exams_with_results': exams_with_results,
            'exams_with_results_released': exams_with_results,
            'correctors_count': User.objects.filter(groups__name__iexact=UserRole.TEACHER).distinct().count(),
        })

class ExamUploadView(APIView):
    permission_classes = [IsTeacherOrAdmin]  # Teacher/Admin only
    parser_classes = (MultiPartParser, FormParser)

    @method_decorator(maybe_ratelimit(key='user', rate='20/h', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        logger = logging.getLogger(__name__)

        # Early guard: BATCH_A3 upload requires a pdf_source file.
        # (ExamListView handles metadata-only creation without a PDF.)
        upload_mode_raw = request.data.get('upload_mode', Exam.UploadMode.BATCH_A3)
        if upload_mode_raw == Exam.UploadMode.BATCH_A3 and 'pdf_source' not in request.FILES:
            return Response(
                {'pdf_source': [_('Le fichier PDF source est obligatoire en mode BATCH_A3')]},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
                            status=Copy.Status.READY,
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
                    
                    copy = Copy.objects.create(
                        exam=exam,
                        anonymous_id=generate_anonymous_id(exam, i),
                        status=Copy.Status.READY,
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
             return Response({'error': 'Fichier PDF invalide.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
             from core.utils.errors import safe_error_response
             return Response(
                 safe_error_response(e, context="PDF import", user_message="Échec de l'import PDF. Veuillez réessayer."),
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
    serializer_class = ExamSerializer

    def get_queryset(self):
        from django.db.models import Count, Q
        return Exam.objects.all().order_by('-date').annotate(
            _copies_count=Count('copies'),
            _ready_count=Count('copies', filter=Q(copies__status='READY')),
            _in_progress_count=Count('copies', filter=Q(copies__status='IN_PROGRESS')),
            _finalized_count=Count('copies', filter=Q(copies__status='FINALIZED')),
        )
    
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
        from django.http import HttpResponse
        from PIL import Image as PILImage
        from io import BytesIO
        from django.conf import settings

        booklet = get_object_or_404(Booklet, id=id)

        # Case 1: header_image exists — LOT 2: X-Accel-Redirect
        if booklet.header_image:
            try:
                response = HttpResponse(content_type='image/jpeg')
                response['X-Accel-Redirect'] = f'/internal-media/{booklet.header_image.name}'
                response['Cache-Control'] = 'private, max-age=3600'
                return response
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
        if instance.assigned_copy.filter(status__in=[Copy.Status.IN_PROGRESS, Copy.Status.FINALIZED]).exists():
             raise 	serializers.ValidationError(
                 {"error": _("Impossible de supprimer un fascicule associé à une copie validée ou corrigée.")}
             )
        instance.delete()

class BookletSplitView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, id):
        booklet = get_object_or_404(Booklet, id=id)
        
        # Mission 1.3: Protocol Enforce
        if booklet.assigned_copy.filter(status__in=[Copy.Status.IN_PROGRESS, Copy.Status.FINALIZED]).exists():
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
                return Response({"error": "Page hors limites."}, status=status.HTTP_404_NOT_FOUND)
                
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
                safe_error_response(e, context="Page analysis", user_message="Échec de l'analyse de la page."),
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

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied

        if not IsKorrigoAdmin().has_permission(self.request, self):
            raise PermissionDenied("Seul un administrateur peut supprimer un examen.")
        super().perform_destroy(instance)


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


class RotateCopyLastPagesView(APIView):
    """
    POST /api/exams/<exam_id>/copies/rotate-last-pages/

    Batch admin action: rotate the last page only of the selected copies.
    """
    permission_classes = [IsKorrigoAdmin]

    def post(self, request, exam_id):
        anonymous_ids = request.data.get('anonymous_ids', [])
        if not isinstance(anonymous_ids, list) or not anonymous_ids:
            return Response(
                {"detail": _("La liste des anonymats est requise.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        normalized_ids = []
        seen = set()
        for raw in anonymous_ids:
            if raw is None:
                continue
            code = str(raw).strip()
            if not code or code in seen:
                continue
            seen.add(code)
            normalized_ids.append(code)

        if not normalized_ids:
            return Response(
                {"detail": _("La liste des anonymats est vide.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        copies = (
            Copy.objects.filter(exam_id=exam_id, anonymous_id__in=normalized_ids)
            .select_related('exam')
            .prefetch_related('booklets')
            .order_by('anonymous_id')
        )
        copy_map = {copy.anonymous_id: copy for copy in copies}

        results = []
        errors = []

        with transaction.atomic():
            for code in normalized_ids:
                copy = copy_map.get(code)
                if not copy:
                    errors.append({
                        'anonymous_id': code,
                        'error': _('Copie introuvable pour cet examen.'),
                    })
                    continue
                try:
                    rotation = _rotate_copy_last_page(copy)
                    results.append(rotation)
                    GradingEvent.objects.create(
                        copy=copy,
                        actor=request.user,
                        action=GradingEvent.Action.ROTATE_LAST_PAGE,
                        metadata={
                            'anonymous_id': copy.anonymous_id,
                            'booklet_id': rotation['booklet_id'],
                            'page_index': rotation['page_index'],
                            'original_path': rotation['original_path'],
                            'new_path': rotation['new_path'],
                        },
                    )
                except Exception as e:
                    logger.exception("Failed to rotate last page for copy %s", code)
                    errors.append({
                        'anonymous_id': code,
                        'error': str(e),
                    })

        status_code = status.HTTP_200_OK if results else status.HTTP_400_BAD_REQUEST
        return Response({
            'exam_id': str(exam_id),
            'requested_anonymous_ids': normalized_ids,
            'rotated_count': len(results),
            'error_count': len(errors),
            'rotated': results,
            'errors': errors,
        }, status=status_code)


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
            return Response({"error": "Identifiant élève requis."}, status=status.HTTP_400_BAD_REQUEST)

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
                header_url = f"/api/exams/booklets/{booklet.id}/header/"
            
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
        from django.db.models import Q
        # Une copie est visible dès qu'elle est FINALIZED et que l'élève est identifié.
        # results_released_at sert uniquement de blocage global admin (embargo) :
        # s'il est renseigné sur l'examen, il doit être dans le passé.
        # S'il est NULL, aucun embargo n'est en place → la copie est directement visible.
        base_filter = Q(status=Copy.Status.FINALIZED) & (
            Q(exam__results_released_at__isnull=True)
            | Q(exam__results_released_at__lte=__import__('django.utils.timezone', fromlist=['now']).now())
        )
        if student_id:
            return Copy.objects.filter(base_filter, student=student_id).select_related('exam')
        else:
            try:
                from students.models import Student
                student = Student.objects.get(user=self.request.user)
                return Copy.objects.filter(base_filter, student=student).select_related('exam')
            except Student.DoesNotExist:
                return Copy.objects.none()

    @staticmethod
    def _build_exercise_config(exam):
        """Build exercise_config from exam.grading_structure (DB source of truth)."""
        from exams.grading_utils import build_exercise_config
        return build_exercise_config(exam.grading_structure)

    @staticmethod
    def _get_file_version_ms(relative_path):
        """Get file modification time in milliseconds for cache-busting."""
        if not relative_path:
            return None
        from django.conf import settings
        import os
        full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        try:
            return int(os.path.getmtime(full_path) * 1000)
        except OSError:
            return None

    def _build_versioned_media_url(self, request, relative_path):
        """Build protected media URL with version parameter."""
        if not relative_path:
            return None
        version = self._get_file_version_ms(relative_path)
        url = f'/api/media/{relative_path}'
        if version is not None:
            url = f'{url}?v={version}'
        return request.build_absolute_uri(url)

    def _build_q_max(self, exam):
        """Dérive q_max depuis grading_structure, fallback sur score_constraints."""
        from exams.grading_utils import build_q_max as build_q_max_from_structure
        q_max = build_q_max_from_structure(exam.grading_structure)

        # Fallback sur le dict hardcodé si grading_structure ne fournit pas de q_max
        if not q_max:
            q_max = Q_MAX_BY_EXAM.get(exam.name, {})
            if q_max:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"DEPRECATED: Using hardcoded Q_MAX_BY_EXAM fallback for {exam.name}. Update grading_structure!")
        return q_max

    def list(self, request, *args, **kwargs):
        from grading.models import Score, QuestionRemark
        from grading.services import GradingService
        from core.utils.audit import log_data_access

        queryset = self.get_queryset()

        # Audit trail
        student_id = request.session.get('student_id')
        if student_id:
            log_data_access(request, 'Copy', f'student_{student_id}_list', action_detail='list')

        # LOT 7: Prefetch scores and remarks in bulk to avoid N+1 queries
        copy_list = list(queryset)
        copy_ids = [c.id for c in copy_list]

        scores_by_copy = {}
        for s in Score.objects.filter(copy_id__in=copy_ids):
            scores_by_copy[s.copy_id] = s

        from collections import defaultdict
        remarks_by_copy = defaultdict(dict)
        for r in QuestionRemark.objects.filter(copy_id__in=copy_ids):
            if r.remark and r.remark.strip():
                remarks_by_copy[r.copy_id][r.question_id] = r.remark

        data = []
        for copy in copy_list:
            # Use prefetched score
            score_obj = scores_by_copy.get(copy.id)
            scores_data = score_obj.scores_data if score_obj and score_obj.scores_data else {}
            total_score: float = GradingService.compute_score(copy)

            remarks = remarks_by_copy.get(copy.id, {})

            # Build exercise_config from DB grading_structure (source of truth)
            exercise_config = self._build_exercise_config(copy.exam)
            q_max = self._build_q_max(copy.exam)

            # Build question_map for UUID-based question IDs
            question_map = {}
            if copy.exam and copy.exam.grading_structure:
                from exams.grading_utils import extract_leaf_questions
                for leaf in extract_leaf_questions(copy.exam.grading_structure):
                    question_map[leaf['id']] = {
                        'exercise_idx': leaf['exercise_idx'],
                        'label': leaf.get('short_label') or leaf['label'],
                        'points': leaf['points'],
                    }

            final_comment = score_obj.final_comment if score_obj else ''

            data.append({
                "id": copy.id,
                "anonymous_id": copy.anonymous_id,
                "exam_name": copy.exam.name,
                "date": copy.exam.date,
                "total_score": total_score,
                "status": copy.status,
                "final_pdf_url": self._build_versioned_media_url(request, copy.final_pdf.name) if copy.final_pdf else None,
                "scores_details": scores_data,
                "remarks": remarks,
                "global_appreciation": copy.global_appreciation or '',
                "final_comment": final_comment or '',
                "llm_summary": copy.llm_summary or '',
                "exercise_config": exercise_config,
                "q_max": q_max,
                "question_map": question_map,
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
        
        in_progress_or_graded = exam.copies.filter(status__in=[Copy.Status.IN_PROGRESS, Copy.Status.FINALIZED]).count()
        if in_progress_or_graded > 0:
            return Response(
                {"error": _(f"Impossible de re-uploader: {in_progress_or_graded} copie(s) sont déjà en cours de correction ou corrigées.")},

                status=status.HTTP_409_CONFLICT
            )
        
        try:
            with transaction.atomic():
                existing_ready = exam.copies.filter(status=Copy.Status.READY)
                if existing_ready.exists():
                    logger.info(f"Cleaning up {existing_ready.count()} existing READY copies for exam {exam.id}")
                    existing_ready.delete()
                
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
                        status=Copy.Status.READY,
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
             return Response({"error": "État de copie invalide."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
             from core.utils.errors import safe_error_response
             return Response(
                 safe_error_response(e, context="Copy validation", user_message="Échec de la validation de la copie."),
                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
             )

class BulkCopyValidationView(APIView):
    """
    POST /api/exams/<exam_id>/validate-all/
    Kept for backward compatibility. Copies are now created directly as READY.
    """
    permission_classes = [IsTeacherOrAdmin]

    def post(self, request, exam_id):
        logger = logging.getLogger(__name__)
        exam = get_object_or_404(Exam, id=exam_id)
        
        ready_copies = Copy.objects.filter(exam=exam, status=Copy.Status.READY)
        
        if not ready_copies.exists():
            return Response(
                {"message": _("Aucune copie à valider.")},
                status=status.HTTP_200_OK
            )
        
        validated_count = 0
        errors = []
        
        for copy in ready_copies:
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
    Admin sees all copies (CopySerializer); teachers see only their assigned ones (CorrectorCopySerializer).
    """
    permission_classes = [IsTeacherOrAdmin]
    pagination_class = None  # Frontend expects flat array

    def get_serializer_class(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name__iexact=UserRole.ADMIN).exists():
            return CopySerializer
        return CorrectorCopySerializer

    def get_queryset(self):
        user = self.request.user

        base_qs = Copy.objects.filter(
            status__in=[Copy.Status.READY, Copy.Status.FINALIZED,
                        Copy.Status.IN_PROGRESS]
        ).select_related('exam').order_by('exam__date', 'anonymous_id')

        # Filtrage optionnel par Type d'Examen
        exam_type_id = self.request.query_params.get('exam_type_id')
        if exam_type_id:
            base_qs = base_qs.filter(exam__exam_type_id=exam_type_id)

        # Everyone sees only copies they are assigned to correct.
        # Admins who don't personally correct see 0 copies here (they use
        # the admin dashboard /api/exams/.../student-list/ for overview).
        return base_qs.filter(assigned_corrector=user)

class CorrectorCopyDetailView(generics.RetrieveUpdateAPIView):
    """
    Permet au correcteur de récupérer et mettre à jour les détails d'une copie.
    GET  /api/copies/<id>/  → détails complets
    PATCH /api/copies/<id>/ → mise à jour partielle (ex: subject_variant)
    """
    queryset = Copy.objects.select_related('exam', 'locked_by')\
        .prefetch_related('booklets', 'annotations__created_by')
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]
    lookup_field = 'id'

    def get_serializer_class(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name__iexact=UserRole.ADMIN).exists():
            return CopySerializer
        return CorrectorCopySerializer

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if not user.is_superuser and not user.groups.filter(name__iexact=UserRole.ADMIN).exists():
            if obj.assigned_corrector_id != user.id:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Vous n'êtes pas assigné à cette copie.")
        return obj


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
                status=Copy.Status.READY
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
                safe_error_response(e, context="Copy dispatch", user_message="Échec de la distribution des copies."),
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
    permission_classes = [IsKorrigoAdmin]

    @method_decorator(maybe_ratelimit(key='user', rate='10/h', method='POST', block=True))
    def post(self, request, id):
        from django.http import HttpResponse
        from core.utils.audit import log_audit
        from exams.services import PronoteExporter
        from exams.services.pronote_export import ValidationError
        import logging

        logger = logging.getLogger(__name__)

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
            result: dict[str, object] = {'updated': updated}
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
        results: dict[str, object] = {'detected': 0, 'failed': 0, 'errors': [], 'copies': []}

        for copy in copies:
            _errors: list = results['errors']  # type: ignore[assignment]
            _copies_list: list = results['copies']  # type: ignore[assignment]

            if not copy.pdf_source:
                _errors.append({'id': str(copy.id), 'error': 'No PDF source'})
                results['failed'] = int(results['failed']) + 1  # type: ignore[arg-type]
                continue

            # Find the actual file
            pdf_path = None
            for base in media_paths:
                candidate = os.path.join(base, copy.pdf_source.name)
                if os.path.exists(candidate):
                    pdf_path = candidate
                    break

            if not pdf_path:
                _errors.append({'id': str(copy.id), 'error': 'PDF file not found'})
                results['failed'] = int(results['failed']) + 1  # type: ignore[arg-type]
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
                    results['detected'] = int(results['detected']) + 1  # type: ignore[arg-type]
                else:
                    _errors.append({
                        'id': str(copy.id),
                        'anonymous_id': copy.anonymous_id,
                        'error': f'No reference found in OCR text: {text.strip()[:100]}'
                    })
                    results['failed'] = int(results['failed']) + 1  # type: ignore[arg-type]

                _copies_list.append({
                    'id': str(copy.id),
                    'anonymous_id': copy.anonymous_id,
                    'subject_variant': variant,
                    'ocr_text': text.strip()[:100],
                })

            except Exception as e:
                logger.error(f"OCR failed for copy {copy.id}: {e}")
                _errors.append({'id': str(copy.id), 'error': str(e)[:200]})
                results['failed'] = int(results['failed']) + 1  # type: ignore[arg-type]

        return Response(results)


class ExamStudentListView(APIView):
    """
    GET /api/exams/<exam_id>/student-list/
    Returns the exam roster merged with copies so every student is visible,
    even when no copy has been imported or assigned yet.
    Admin only.
    """
    permission_classes = [IsTeacherOrAdmin]

    @staticmethod
    def _normalize_name(value):
        return ' '.join((value or '').split()).strip().upper()

    @staticmethod
    def _parse_date(value):
        from datetime import datetime

        raw = (value or '').strip()
        if not raw:
            return None
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        return None

    @classmethod
    def _student_display_name(cls, student):
        if not student:
            return None
        parts = [getattr(student, 'last_name', None), getattr(student, 'first_name', None)]
        name = ' '.join(p for p in parts if p).strip()
        if name:
            return name
        user = getattr(student, 'user', None)
        if user:
            user_name = f"{user.last_name} {user.first_name}".strip()
            return user_name or user.username
        return str(student)

    @classmethod
    def _corrector_display_name(cls, user):
        if not user:
            return None
        name = f"{getattr(user, 'last_name', '')} {getattr(user, 'first_name', '')}".strip()
        return name or getattr(user, 'username', None) or str(user)

    def _load_roster_rows(self, exam):
        from students.models import Student
        import csv
        from io import StringIO

        if not exam.students_csv:
            return []

        try:
            exam.students_csv.open('rb')
            raw = exam.students_csv.read().decode('utf-8-sig')
        except Exception:
            return []
        finally:
            try:
                exam.students_csv.close()
            except Exception:
                pass

        if not raw.strip():
            return []

        sample = raw[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ';'

        reader = csv.DictReader(StringIO(raw), delimiter=delimiter)
        parsed_rows = []
        class_names = set()

        for row in reader:
            normalized = {
                (k or '').strip().lower(): (v or '').strip()
                for k, v in row.items()
            }

            last_name = normalized.get('nom') or normalized.get('last_name') or ''
            first_name = normalized.get('prenom') or normalized.get('prénom') or normalized.get('first_name') or ''
            date_raw = (
                normalized.get('date_naissance')
                or normalized.get('date naissance')
                or normalized.get('ddn')
                or normalized.get('date_de_naissance')
                or ''
            )
            class_name = normalized.get('classe') or normalized.get('class_name') or normalized.get('class') or ''
            email = normalized.get('mail') or normalized.get('email') or ''

            parsed_date = self._parse_date(date_raw)
            if not last_name or not first_name or not parsed_date:
                continue

            class_names.add(class_name)
            parsed_rows.append({
                'identity_key': (
                    self._normalize_name(last_name),
                    self._normalize_name(first_name),
                    parsed_date.isoformat(),
                ),
                'last_name': self._normalize_name(last_name),
                'first_name': self._normalize_name(first_name),
                'date_naissance': parsed_date,
                'email': email or None,
                'class_name': class_name or None,
                'groupe': normalized.get('groupe') or None,
            })

        if not parsed_rows:
            return []

        students_qs = Student.objects.all()
        if class_names:
            students_qs = students_qs.filter(class_name__in=[c for c in class_names if c])

        students_by_identity = {}
        for student in students_qs.select_related('user'):
            key = (
                self._normalize_name(student.last_name),
                self._normalize_name(student.first_name),
                student.date_naissance.isoformat(),
            )
            students_by_identity[key] = student

        for row in parsed_rows:
            student = students_by_identity.get(row['identity_key'])
            row['student'] = student
            row['student_id'] = str(student.id) if student else None
            row['student_name'] = self._student_display_name(student) or f"{row['last_name']} {row['first_name']}".strip()
            row['student_class'] = getattr(student, 'class_name', None) if student else row['class_name']
            row['student_groupe'] = getattr(student, 'groupe', None) if student else row['groupe']

        return parsed_rows

    def get(self, request, exam_id):
        from grading.services import GradingService
        from grading.models import Score

        exam = get_object_or_404(Exam, id=exam_id)
        copies = list(Copy.objects.filter(exam=exam).select_related(
            'student', 'student__user', 'assigned_corrector'
        ).prefetch_related('annotations').order_by('anonymous_id'))
        copies_by_identity = {}
        for copy in copies:
            if copy.student:
                key = (
                    self._normalize_name(copy.student.last_name),
                    self._normalize_name(copy.student.first_name),
                    copy.student.date_naissance.isoformat(),
                )
                copies_by_identity.setdefault(key, copy)

        score_lookup = {}
        for score in Score.objects.filter(copy__in=copies).select_related('copy'):
            score_data = score.scores_data or {}
            total = 0
            if isinstance(score_data, dict):
                for value in score_data.values():
                    if value is not None and value != '':
                        total += float(value)
            score_lookup[str(score.copy_id)] = round(total, 2)

        from core.auth import UserRole
        is_admin = (
            request.user.is_superuser
            or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()
        )

        roster_rows = self._load_roster_rows(exam)
        
        # Filtrage pour les enseignants : uniquement leurs élèves
        if not is_admin:
            from grading.views_my_students import _get_teacher_assignments, _student_matches_assignments
            # On a besoin d'une version de _student_matches_assignments qui travaille sur les dicts du roster
            assignments = _get_teacher_assignments(request.user)
            filtered_roster = []
            for row in roster_rows:
                # Création d'un objet Student fictif pour la validation par _student_matches_assignments
                # ou adaptation de la logique. Utilisons les champs du dict.
                match = False
                for a in assignments:
                    # Check level prefix (simplifié pour le roster)
                    if a['assignment_type'] == 'classe' and row.get('class_name') == a['group_name']:
                        match = True; break
                    if a['assignment_type'] == 'groupe' and row.get('groupe') == a['group_name']:
                        match = True; break
                if match:
                    filtered_roster.append(row)
            roster_rows = filtered_roster

        data = []
        used_copy_ids = set()

        def build_row(copy, roster_row=None):
            student = copy.student if copy else (roster_row or {}).get('student')
            student_id = str(student.id) if student else None
            student_name = None
            student_class = None
            student_groupe = None
            if student:
                student_name = self._student_display_name(student)
                student_class = getattr(student, 'class_name', None)
                student_groupe = getattr(student, 'groupe', None)
            elif roster_row:
                student_name = roster_row.get('student_name')
                student_class = roster_row.get('student_class')
                student_groupe = roster_row.get('student_groupe')

            # Pour les enseignants, on masque tout ce qui n'est pas FINALIZED
            if not is_admin and copy and copy.status != Copy.Status.FINALIZED:
                copy = None

            if copy:
                used_copy_ids.add(str(copy.id))

            total_score = score_lookup.get(str(copy.id)) if copy else None
            if copy and str(copy.id) not in score_lookup:
                total_score = GradingService.compute_score(copy)

            corrector_name = self._corrector_display_name(copy.assigned_corrector) if copy and copy.assigned_corrector else None

            return {
                "id": str(copy.id) if copy else None,
                "copy_id": str(copy.id) if copy else None,
                "anonymous_id": copy.anonymous_id if copy else None,
                "student_id": student_id,
                "student_name": student_name,
                "student_class": student_class,
                "student_groupe": student_groupe,
                "total_score": total_score,
                "status": copy.status if copy else ("NO_COPY" if roster_row else "UNKNOWN"),
                "has_copy": bool(copy),
                "corrector": corrector_name,
                "has_appreciation": bool(copy and copy.global_appreciation and copy.global_appreciation.strip()),
            }

        for row in roster_rows:
            copy = copies_by_identity.get(row['identity_key'])
            data.append(build_row(copy, row))

        for copy in copies:
            if str(copy.id) in used_copy_ids:
                continue
            data.append(build_row(copy))

        # Summary stats
        scored = [d for d in data if d['total_score'] is not None]
        summary = {
            "exam_name": exam.name,
            "exam_date": str(exam.date) if exam.date else None,
            "total_students": len(roster_rows) if roster_rows else len(data),
            "total_copies": len(copies),
            "linked_copies": sum(1 for d in data if d['has_copy']),
            "missing_copies": sum(1 for d in data if not d['has_copy']),
            "graded": sum(1 for d in data if d['status'] == 'FINALIZED'),
            "ready": sum(1 for d in data if d['status'] == 'READY'),
            "en_cours": sum(1 for d in data if d['status'] == 'IN_PROGRESS'),
            "staging": sum(1 for d in data if d['status'] == 'STAGING'),
            "with_scores": len(scored),
            "average": float(round(  # type: ignore[call-overload]
                sum(d['total_score'] for d in scored) / len(scored), 2  # type: ignore[arg-type]
            )) if scored else None,
            "min_score": min(d['total_score'] for d in scored) if scored else None,
            "max_score": max(d['total_score'] for d in scored) if scored else None,
            "has_groups": any(d.get('student_groupe') for d in data),
        }

        return Response({"summary": summary, "copies": data})


class ExamTypeListView(generics.ListCreateAPIView):
    """
    GET /api/exams/types/
    POST /api/exams/types/
    Admin voit tous les types actifs.
    Correcteur voit uniquement les types où il a des copies assignées.
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = ExamTypeSerializer
    pagination_class = None  # Frontend expects a flat array; exam types are always a small list

    def get_queryset(self):
        from .models import ExamType
        from django.db.models import Q
        user = self.request.user
        qs = ExamType.objects.filter(is_active=True).order_by('sort_order', 'name')

        # Admin et superuser voient tous les types
        if user.is_superuser or user.groups.filter(name__iexact=UserRole.ADMIN).exists():
            return qs

        # Correcteur : types liés aux examens auxquels il est assigné OU types de ses copies
        return qs.filter(
            Q(exams__correctors=user) | 
            Q(exams__copies__assigned_corrector=user, exams__copies__status__in=['READY', 'FINALIZED', 'IN_PROGRESS'])
        ).distinct()


class ExamTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET, PUT, PATCH, DELETE /api/exams/types/<id>/
    """
    
    permission_classes = [IsTeacherOrAdmin]
    
    queryset = ExamType.objects.all()
    
    serializer_class = ExamTypeSerializer
    lookup_field = 'id'


class JuryReportListView(generics.ListCreateAPIView):
    """
    GET /api/exams/reports/
    POST /api/exams/reports/
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = JuryReportSerializer

    def get_queryset(self):
        from grading.models import Copy
        queryset = JuryReport.objects.select_related('exam_type', 'created_by').all()
        user = self.request.user

        is_admin = (
            user.is_superuser
            or user.groups.filter(name__iexact=UserRole.ADMIN).exists()
        )
        if not is_admin:
            # Non-admin correctors: only published reports for exam types
            # where they actually have at least one copy assigned.
            assigned_type_ids = (
                Copy.objects.filter(assigned_corrector=user)
                .values_list('exam__exam_type_id', flat=True)
                .distinct()
            )
            queryset = queryset.filter(
                exam_type_id__in=assigned_type_ids,
                is_published=True,
            )

        # Optional scope filters
        exam_type_code = self.request.query_params.get('exam_type_code')
        if exam_type_code:
            queryset = queryset.filter(exam_type__code=exam_type_code)

        exam_type_id = self.request.query_params.get('exam_type_id')
        if exam_type_id:
            queryset = queryset.filter(exam_type_id=exam_type_id)

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class JuryReportDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET, PUT, PATCH, DELETE /api/exams/reports/<id>/
    """
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = JuryReportSerializer
    lookup_field = 'id'

    def get_queryset(self):
        queryset = JuryReport.objects.all()
        user = self.request.user
        is_admin = user.is_superuser or user.groups.filter(name__iexact=UserRole.ADMIN).exists()
        if not is_admin:
            queryset = queryset.filter(exam__correctors=user)
        return queryset
