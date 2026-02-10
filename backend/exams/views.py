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
from core.auth import IsAdminOnly

import fitz  # PyMuPDF
import logging
import os

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
                    import uuid

                    splitter = PDFSplitter(dpi=150)
                    booklets = splitter.split_exam(exam)
                    logger.info(f"PDF split into {len(booklets)} booklets for exam {exam.id}")

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

                    # Log successful completion
                    logger.info(f"Exam upload completed successfully: {exam.id} with {len(booklets)} booklets")
                    
                    return Response({
                        **serializer.data,
                        "booklets_created": len(booklets),
                        "message": f"{len(booklets)} booklets created successfully"
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
            if 'exam' in locals() and exam.pdf_source and hasattr(exam.pdf_source, 'path'):
                try:
                    if os.path.exists(exam.pdf_source.path):
                        os.remove(exam.pdf_source.path)
                        logger.info(f"Cleaned up orphaned file: {exam.pdf_source.path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup file: {cleanup_error}")
            
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
                import uuid
                
                for pdf_file in uploaded_files:
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
                    # Note: We don't duplicate the file; Copy.pdf_source will reference the same file
                    copy = Copy.objects.create(
                        exam=exam,
                        anonymous_id=str(uuid.uuid4())[:8].upper(),
                        status=Copy.Status.STAGING,
                        is_identified=False,
                        pdf_source=exam_pdf.pdf_file  # Reference the same file
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



class ExamMultiUploadView(APIView):
    """
    Upload d'examen avec support multi-fichiers PDF.
    POST /api/exams/multi-upload/

    Chaque fichier PDF est validé et traité indépendamment (A3/A4 auto-détecté).
    Tous les booklets/copies créés appartiennent au même examen.

    Multipart form data:
    - name (required): Nom de l'examen
    - date (required): Date de l'examen (YYYY-MM-DD)
    - pdf_files (required): Un ou plusieurs fichiers PDF
    - students_csv (optional): Fichier CSV des élèves
    - pages_per_booklet (optional): Entier, défaut 4
    """
    permission_classes = [IsAdminOnly]
    parser_classes = (MultiPartParser, FormParser)

    @method_decorator(maybe_ratelimit(key='user', rate='20/h', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        import logging
        import uuid
        from django.core.exceptions import ValidationError
        from core.utils.errors import safe_error_response
        from .validators import (
            validate_pdf_size, validate_pdf_not_empty,
            validate_pdf_mime_type, validate_pdf_integrity,
        )

        logger = logging.getLogger(__name__)

        # 1. Valider les champs obligatoires
        name = request.data.get('name', '').strip()
        date_str = request.data.get('date', '').strip()

        if not name:
            return Response(
                {"error": _("Le nom de l'examen est obligatoire.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not date_str:
            return Response(
                {"error": _("La date de l'examen est obligatoire.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Collecter les fichiers PDF
        pdf_files = request.FILES.getlist('pdf_files')
        if not pdf_files:
            # Fallback: clé unique 'pdf_source' pour backward compat
            single_pdf = request.FILES.get('pdf_source')
            if single_pdf:
                pdf_files = [single_pdf]

        if not pdf_files:
            return Response(
                {"error": _("Au moins un fichier PDF est requis.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Pré-validation de TOUS les fichiers AVANT toute écriture DB
        file_errors = {}
        for pdf_file in pdf_files:
            errors = []
            for validator in [validate_pdf_size, validate_pdf_not_empty,
                              validate_pdf_mime_type, validate_pdf_integrity]:
                try:
                    validator(pdf_file)
                except ValidationError as e:
                    errors.extend(e.messages if hasattr(e, 'messages') else [str(e.message)])
            if errors:
                file_errors[pdf_file.name] = errors

        if file_errors:
            return Response(
                {"error": _("Validation échouée pour certains fichiers."),
                 "file_errors": file_errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Traitement atomique
        try:
            with transaction.atomic():
                # Valider et parser pages_per_booklet
                try:
                    pages_per_booklet = int(request.data.get('pages_per_booklet', 4))
                    if pages_per_booklet < 1:
                        pages_per_booklet = 4
                except (ValueError, TypeError):
                    pages_per_booklet = 4

                # Créer l'examen
                exam = Exam.objects.create(
                    name=name,
                    date=date_str,
                    pages_per_booklet=pages_per_booklet
                )

                # Sauvegarder le CSV si fourni
                students_csv_file = request.FILES.get('students_csv')
                if students_csv_file:
                    exam.student_csv = students_csv_file
                    exam.save()
                    logger.info(f"Student CSV saved for exam {exam.id}")

                # Instancier le processeur batch (réutilisé pour tous les A3)
                from processing.services.batch_processor import BatchA3Processor
                from processing.services.pdf_splitter import PDFSplitter

                csv_path = exam.student_csv.path if exam.student_csv else None
                batch_processor = BatchA3Processor(dpi=200, csv_path=csv_path)
                splitter = PDFSplitter(dpi=150)

                per_file_results = []
                total_copies = 0
                total_ready = 0
                total_staging = 0
                total_booklets = 0

                for i, pdf_file in enumerate(pdf_files):
                    # Créer le record ExamSourcePDF
                    source_pdf = ExamSourcePDF.objects.create(
                        exam=exam,
                        pdf_file=pdf_file,
                        original_filename=pdf_file.name,
                        display_order=i
                    )

                    result = self._process_single_pdf(
                        exam, source_pdf, batch_processor, splitter, logger
                    )
                    per_file_results.append(result)

                    total_copies += result.get('copies_created', 0)
                    total_ready += result.get('ready_count', 0)
                    total_staging += result.get('staging_count', 0)
                    total_booklets += result.get('booklets_created', 0)

                # Sauvegarder le fichier d'annexes si fourni
                annexe_file = request.FILES.get('annexe_pdf')
                has_annexe = False
                if annexe_file:
                    annexe_source = ExamSourcePDF.objects.create(
                        exam=exam,
                        pdf_file=annexe_file,
                        original_filename=annexe_file.name,
                        display_order=len(pdf_files),
                        pdf_type=ExamSourcePDF.PDFType.ANNEXE,
                        detected_format=ExamSourcePDF.Format.A4,
                    )
                    ann_doc = fitz.open(annexe_source.pdf_file.path)
                    annexe_source.page_count = ann_doc.page_count
                    ann_doc.close()
                    annexe_source.save()
                    has_annexe = True
                    logger.info(f"Annexe PDF saved: {annexe_file.name} "
                                f"({annexe_source.page_count} pages)")

                exam.is_processed = True
                exam.save()

                return Response({
                    "id": str(exam.id),
                    "name": exam.name,
                    "date": str(exam.date),
                    "files_processed": len(pdf_files),
                    "total_copies_created": total_copies,
                    "total_ready": total_ready,
                    "total_staging": total_staging,
                    "total_booklets_created": total_booklets,
                    "has_annexe": has_annexe,
                    "per_file_results": per_file_results,
                    "message": (
                        f"{len(pdf_files)} fichier(s) traité(s): "
                        f"{total_copies} copies créées "
                        f"({total_ready} identifiées, {total_staging} à vérifier)"
                    )
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                safe_error_response(
                    e, context="Multi-file exam upload",
                    user_message="Échec du traitement de l'upload multi-fichiers."
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _process_single_pdf(self, exam, source_pdf, batch_processor, splitter, logger):
        """
        Traite un seul fichier PDF (A3 ou A4 auto-détecté).

        Returns:
            dict: Statistiques de traitement pour ce fichier
        """
        import uuid as uuid_mod

        pdf_path = source_pdf.pdf_file.path

        # Compter les pages
        doc = fitz.open(pdf_path)
        source_pdf.page_count = doc.page_count
        doc.close()

        # Détecter le format
        is_a3 = batch_processor.is_a3_format(pdf_path)
        source_pdf.detected_format = ExamSourcePDF.Format.A3 if is_a3 else ExamSourcePDF.Format.A4
        source_pdf.save()

        if is_a3:
            logger.info(
                f"[{source_pdf.original_filename}] Détecté A3 "
                f"({source_pdf.page_count} pages). BatchA3Processor."
            )

            student_copies = batch_processor.process_batch_pdf(
                pdf_path, str(exam.id)
            )
            copies = batch_processor.create_copies_from_batch(exam, student_copies)

            # Rattacher les booklets à leur source_pdf
            for copy in copies:
                copy.booklets.all().update(source_pdf=source_pdf)

            ready_count = sum(1 for c in copies if c.status == Copy.Status.READY)
            staging_count = sum(1 for c in copies if c.status == Copy.Status.STAGING)

            return {
                'filename': source_pdf.original_filename,
                'format': 'A3',
                'page_count': source_pdf.page_count,
                'copies_created': len(copies),
                'ready_count': ready_count,
                'staging_count': staging_count,
            }
        else:
            logger.info(
                f"[{source_pdf.original_filename}] Détecté A4 "
                f"({source_pdf.page_count} pages). PDFSplitter."
            )

            booklets = splitter.split_pdf_file(exam, pdf_path, source_pdf=source_pdf)

            created_count = 0
            for booklet in booklets:
                copy = Copy.objects.create(
                    exam=exam,
                    anonymous_id=str(uuid_mod.uuid4())[:8].upper(),
                    status=Copy.Status.STAGING,
                    is_identified=False
                )
                copy.booklets.add(booklet)
                created_count += 1

            return {
                'filename': source_pdf.original_filename,
                'format': 'A4',
                'page_count': source_pdf.page_count,
                'booklets_created': created_count,
                'copies_created': created_count,
                'ready_count': 0,
                'staging_count': created_count,
            }


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
        
        # Fallback: extraire depuis le PDF source (priorité: source_pdf du booklet, sinon exam.pdf_source)
        source_file = booklet.source_pdf.pdf_file if booklet.source_pdf else booklet.exam.pdf_source
        if source_file:
            page_index = booklet.start_page - 1 if booklet.start_page else 0

            try:
                doc = fitz.open(source_file.path)
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

        # Priorité: source_pdf du booklet, sinon exam.pdf_source
        source_file = booklet.source_pdf.pdf_file if booklet.source_pdf else booklet.exam.pdf_source
        if not source_file:
             return Response({"error": "No PDF source found"}, status=status.HTTP_404_NOT_FOUND)

        # Determine source page index
        page_index = booklet.start_page - 1

        import tempfile
        import os
        from processing.services.splitter import A3Splitter

        try:
            if not booklet.exam.pdf_source:
                return Response(
                    {"error": _("Le PDF source n'est pas disponible pour cet examen")},
                    status=status.HTTP_404_NOT_FOUND
                )
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
    Les admins voient toutes les copies (CopySerializer avec student info),
    les enseignants ne voient que leurs copies assignées (CorrectorCopySerializer sans student info).
    """
    permission_classes = [IsTeacherOrAdmin]

    def _is_admin(self):
        user = self.request.user
        return user.is_superuser or user.is_staff or user.groups.filter(name='admin').exists()

    def get_serializer_class(self):
        if self._is_admin():
            return CopySerializer
        return CorrectorCopySerializer

    def get_queryset(self):
        exam_id = self.kwargs['exam_id']

        queryset = Copy.objects.filter(exam_id=exam_id)\
            .select_related('exam', 'student', 'locked_by', 'assigned_corrector')\
            .prefetch_related('booklets', 'annotations__created_by')

        # Enseignants: seulement leurs copies assignées
        if not self._is_admin():
            queryset = queryset.filter(assigned_corrector=self.request.user)

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

class GenerateStudentPDFsView(APIView):
    """
    Génère un PDF A4 par élève à partir des scans A3 de l'examen.
    Optionnellement, ajoute les pages annexes (identifiées par OCR).

    POST /api/exams/<exam_id>/generate-student-pdfs/
    """
    permission_classes = [IsAdminOnly]

    @method_decorator(maybe_ratelimit(key='user', rate='5/h', method='POST', block=True))
    def post(self, request, exam_id):
        import logging
        import os
        from django.conf import settings
        from django.core.files.base import ContentFile
        from processing.services.student_pdf_generator import StudentPDFGenerator

        logger = logging.getLogger(__name__)
        exam = get_object_or_404(Exam, id=exam_id)

        # Collecter les PDFs source (type COPY uniquement)
        copy_sources = exam.source_pdfs.filter(
            pdf_type=ExamSourcePDF.PDFType.COPY
        ).order_by('display_order')

        if not copy_sources.exists():
            return Response(
                {"error": _("Aucun PDF source trouvé pour cet examen.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        # CSV requis
        if not exam.student_csv:
            return Response(
                {"error": _("Fichier CSV des élèves requis pour la génération.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Annexe optionnelle
        annexe_source = exam.source_pdfs.filter(
            pdf_type=ExamSourcePDF.PDFType.ANNEXE
        ).first()

        pdf_paths = [s.pdf_file.path for s in copy_sources]
        annexe_path = annexe_source.pdf_file.path if annexe_source else None
        api_key = getattr(settings, 'OPENAI_API_KEY', None) or os.environ.get('OPENAI_API_KEY')

        if not api_key:
            return Response(
                {"error": _("Clé API OpenAI non configurée (OPENAI_API_KEY).")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            generator = StudentPDFGenerator(
                csv_path=exam.student_csv.path,
                api_key=api_key,
            )

            # Générer les PDFs dans un répertoire temporaire
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                result = generator.generate(
                    pdf_paths,
                    annexe_path=annexe_path,
                    output_dir=tmpdir,
                )

                # Stocker chaque PDF généré comme Copy.final_pdf
                import uuid as uuid_mod
                from students.models import Student

                # Use filename_to_student mapping for accurate name lookup
                filename_map = result.get('filename_to_student', {})

                stored_count = 0
                for filename in os.listdir(tmpdir):
                    if not filename.endswith('.pdf'):
                        continue

                    filepath = os.path.join(tmpdir, filename)
                    # Prefer the original name from the mapping (preserves accents)
                    student_name = filename_map.get(
                        filename,
                        filename.replace('.pdf', '').replace('_', ' ').strip()
                    )

                    with open(filepath, 'rb') as f:
                        pdf_content = f.read()

                    # Trouver ou créer la Copy pour cet élève
                    copy = self._find_or_create_copy(exam, student_name)
                    copy.final_pdf.save(filename, ContentFile(pdf_content), save=True)
                    stored_count += 1
                    logger.info(f"Stored PDF for {student_name}: {filename}")

            return Response({
                "message": (
                    f"Génération terminée: {result['generated_count']} PDFs "
                    f"({result['annexes_matched']} annexes matchées)"
                ),
                "generated": result['generated_count'],
                "failed": result['failed_count'],
                "annexes_matched": result['annexes_matched'],
                "annexes_unmatched": result['annexes_unmatched'],
                "missing_students": result['missing_students'],
                "stored": stored_count,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            traceback.print_exc()
            from core.utils.errors import safe_error_response
            return Response(
                safe_error_response(
                    e, context="Student PDF generation",
                    user_message="Échec de la génération des PDFs par élève."
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    def _find_or_create_copy(exam, student_name):
        """
        Trouve une Copy existante pour cet élève, ou en crée une nouvelle.
        Uses exact match first, then fuzzy matching as fallback.
        """
        import re
        import unicodedata
        import uuid as uuid_mod
        from difflib import SequenceMatcher
        from students.models import Student

        def _normalize(text):
            """Normalize for fuzzy comparison (strip accents, uppercase)."""
            if not text:
                return ''
            text = text.upper().strip()
            text = unicodedata.normalize('NFD', text)
            text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
            return re.sub(r'[^A-Z\s]', '', text).strip()

        # 1. Exact match (case-insensitive)
        student = Student.objects.filter(full_name__iexact=student_name).first()

        # 2. Fuzzy fallback if exact match fails
        if not student:
            best_match = None
            best_ratio = 0.0
            norm_name = _normalize(student_name)
            for s in Student.objects.all():
                ratio = SequenceMatcher(
                    None, norm_name, _normalize(s.full_name)
                ).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = s
            if best_match and best_ratio >= 0.80:
                student = best_match

        if student:
            # Chercher une Copy existante liée à cet élève
            copy = Copy.objects.filter(exam=exam, student=student).first()
            if copy:
                return copy

        # Créer une nouvelle Copy
        copy = Copy.objects.create(
            exam=exam,
            anonymous_id=str(uuid_mod.uuid4())[:8].upper(),
            status=Copy.Status.READY,
            is_identified=bool(student),
            student=student,
        )
        return copy


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
                # Si même statut, garder celle notée le plus récemment
                elif copy.status == existing.status:
                    if copy.graded_at and not existing.graded_at:
                        seen_students[student_id] = copy
                    elif copy.graded_at and existing.graded_at and copy.graded_at > existing.graded_at:
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
        from grading.models import GradingEvent

        copy = get_object_or_404(Copy, id=id)
        student_id = request.data.get('student_id')

        if not student_id:
            return Response({"error": "Student ID required"}, status=status.HTTP_400_BAD_REQUEST)

        student = get_object_or_404(Student, id=student_id)

        # Check for duplicate: is this student already assigned to another copy in same exam?
        existing = Copy.objects.filter(
            exam=copy.exam, student=student
        ).exclude(id=copy.id).first()
        if existing:
            return Response(
                {"error": f"Student already assigned to copy {existing.anonymous_id}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_student = copy.student
        copy.student = student
        copy.is_identified = True
        copy.save(update_fields=['student', 'is_identified'])

        # Audit trail
        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.VALIDATE,
            actor=request.user,
            metadata={
                'action_type': 'identification',
                'student_id': str(student.id),
                'student_name': student.full_name,
                'previous_student': str(old_student.id) if old_student else None,
            }
        )

        return Response({"message": "Identification successful"}, status=status.HTTP_200_OK)

class UnidentifiedCopiesView(APIView):
    permission_classes = [IsTeacherOrAdmin]  # Teacher/Admin only

    def get(self, request, exam_id):
        # Mission 18: List unidentified copies for Video-Coding
        # Mission 21 Update: Use dynamic header URL
        # ZF-AUD-13: Prefetch to avoid N+1
        # PHASE 2 SECURITY FIX: Verify user has access to this exam
        exam = get_object_or_404(Exam, id=exam_id)

        # Check if user is admin or corrector for this exam
        if not request.user.is_staff and not exam.correctors.filter(id=request.user.id).exists():
            return Response(
                {"error": "You don't have access to this exam"},
                status=status.HTTP_403_FORBIDDEN
            )

        copies = Copy.objects.filter(exam_id=exam_id, is_identified=False)\
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
    pagination_class = None  # Frontend expects flat array

    def get_queryset(self):
        # Base filter: GRADED + results released by admin
        base_filter = dict(
            status=Copy.Status.GRADED,
            exam__results_released_at__isnull=False,
        )

        # Prefer user association over session for security
        try:
            from students.models import Student
            student = Student.objects.get(user=self.request.user)
            return Copy.objects.filter(
                student=student, **base_filter
            ).select_related('exam').prefetch_related('question_scores')
        except (Student.DoesNotExist, AttributeError):
            pass

        # Fallback: session-based (legacy)
        student_id = self.request.session.get('student_id')
        if student_id:
            return Copy.objects.filter(
                student=student_id, **base_filter
            ).select_related('exam').prefetch_related('question_scores')

        return Copy.objects.none()

    @staticmethod
    def _build_label_map(structure, prefix=''):
        """Build a flat dict mapping question IDs to their labels from grading_structure."""
        labels = {}
        for node in (structure or []):
            node_id = node.get('id')
            label = node.get('label', node_id or '')
            if node_id:
                labels[node_id] = f"{prefix}{label}" if prefix else label
            for child in node.get('children', []):
                child_id = child.get('id')
                child_label = child.get('label', child_id or '')
                if child_id:
                    labels[child_id] = child_label
                # Recurse deeper
                labels.update(StudentCopiesView._build_label_map(
                    child.get('children', [])
                ))
        return labels

    def list(self, request, *args, **kwargs):
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

            # Build detailed scores with labels from barème
            scores_data = {}
            question_labels = self._build_label_map(copy.exam.grading_structure or [])
            for qs in copy.question_scores.all():
                label = question_labels.get(qs.question_id, qs.question_id)
                scores_data[label] = float(qs.score) if qs.score is not None else None

            data.append({
                "id": copy.id,
                "exam_name": copy.exam.name,
                "date": copy.exam.date,
                "total_score": total_score,
                "graded_at": copy.graded_at.isoformat() if copy.graded_at else None,
                "status": copy.status,
                "global_appreciation": copy.global_appreciation or "",
                "final_pdf_url": f"/api/grading/copies/{copy.id}/final-pdf/" if copy.final_pdf else None,
                "scores_details": scores_data,
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


class ReleaseResultsView(APIView):
    """POST /api/exams/<id>/release-results/ — Publie les résultats aux élèves."""
    permission_classes = [IsAdminOnly]

    def post(self, request, exam_id):
        from django.utils import timezone
        exam = get_object_or_404(Exam, id=exam_id)
        if exam.results_released_at:
            return Response(
                {"message": "Résultats déjà publiés.", "released_at": exam.results_released_at},
                status=status.HTTP_200_OK
            )
        exam.results_released_at = timezone.now()
        exam.save(update_fields=['results_released_at'])
        return Response({
            "message": "Résultats publiés avec succès.",
            "released_at": exam.results_released_at,
        }, status=status.HTTP_200_OK)


class UnreleaseResultsView(APIView):
    """POST /api/exams/<id>/unrelease-results/ — Dépublie les résultats."""
    permission_classes = [IsAdminOnly]

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        exam.results_released_at = None
        exam.save(update_fields=['results_released_at'])
        return Response({"message": "Résultats dépubliés."}, status=status.HTTP_200_OK)


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
    pagination_class = None  # Frontend expects flat array, not paginated wrapper

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
    Object-level permission: teachers can only access their assigned copies.
    """
    queryset = Copy.objects.select_related('exam', 'locked_by')\
        .prefetch_related('booklets', 'annotations__created_by')
    serializer_class = CorrectorCopySerializer
    permission_classes = [IsTeacherOrAdmin]
    lookup_field = 'id'

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        is_admin = user.is_superuser or user.is_staff or user.groups.filter(name='admin').exists()
        if not is_admin and obj.assigned_corrector != user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous n'avez pas accès à cette copie.")
        return obj

class ExamDispatchView(APIView):
    """
    Déclenche le dispatch automatique et équitable des copies aux correcteurs assignés.
    POST /api/exams/<id>/dispatch/
    """
    permission_classes = [IsAdminOnly]

    def post(self, request, id):
        exam = get_object_or_404(Exam, id=id)
        
        try:
            from .services.dispatch import DispatchService
            assignments = DispatchService.dispatch_copies(exam)
            return Response({
                "message": "Dispatch successful", 
                "assignments": assignments
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            from core.utils.errors import safe_error_response
            return Response(
                safe_error_response(e, context="Exam Dispatch", user_message="Failed to dispatch copies."),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
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
                # Inside atomic block for read consistency; unassigned copies
                # are already locked above via select_for_update(skip_locked)
                from django.db.models import Count
                current_load = dict(
                    Copy.objects.filter(
                        exam=exam, assigned_corrector__isnull=False
                    )
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

