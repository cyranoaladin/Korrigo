"""
Views pour la gestion documentaire des examens (sujet, corrigé, barème).
Upload sécurisé, versioning, extraction de texte asynchrone.
"""
import hashlib
import os
import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.auth import UserRole
from exams.models import (
    Exam,
    ExamDocumentSet,
    ExamDocument,
    DocumentTextExtraction,
)

logger = logging.getLogger(__name__)


def _is_admin(user):
    """Vérifie si l'utilisateur est admin."""
    return user.is_superuser or getattr(user, 'role', None) == UserRole.ADMIN


class DocumentSetUploadView(APIView):
    """
    POST /api/exams/<exam_id>/document-sets/
    
    Upload d'un lot documentaire (sujet + corrigé + barème).
    Crée un ExamDocumentSet versionné + lance l'extraction asynchrone.
    
    Fichiers attendus (multipart/form-data) :
        sujet   : fichier PDF du sujet
        corrige : fichier PDF du corrigé
        bareme  : fichier PDF du barème
        label   : libellé optionnel (ex: "BB 2026 J1 - Officiel")
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request, exam_id):
        if not _is_admin(request.user):
            return Response(
                {"detail": "Seuls les administrateurs peuvent uploader des documents."},
                status=status.HTTP_403_FORBIDDEN
            )

        exam = get_object_or_404(Exam, id=exam_id)

        # Vérifier qu'au moins un fichier est fourni
        doc_types = ['sujet', 'corrige', 'bareme']
        files = {}
        for dt in doc_types:
            f = request.FILES.get(dt)
            if f:
                if not f.name.lower().endswith('.pdf'):
                    return Response(
                        {"detail": f"Le fichier '{dt}' doit être un PDF."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                files[dt] = f

        if not files:
            return Response(
                {"detail": "Au moins un fichier PDF est requis (sujet, corrige, bareme)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculer la prochaine version
        max_version = ExamDocumentSet.objects.filter(exam=exam).order_by('-version').values_list('version', flat=True).first()
        next_version = (max_version or 0) + 1

        # Désactiver les anciennes versions
        ExamDocumentSet.objects.filter(exam=exam, is_active=True).update(is_active=False)

        # Créer le lot documentaire
        label = request.data.get('label', f"{exam.name} - v{next_version}")
        doc_set = ExamDocumentSet.objects.create(
            exam=exam,
            version=next_version,
            label=label,
            is_active=True,
            created_by=request.user
        )

        # Stocker chaque fichier
        storage_base = os.path.join('exams', 'documents', str(exam.id), f'v{next_version}')
        abs_base = os.path.join(settings.MEDIA_ROOT, storage_base)
        os.makedirs(abs_base, exist_ok=True)

        created_docs = []
        for doc_type, uploaded_file in files.items():
            filename = f"{doc_type}.pdf"
            storage_path = os.path.join(storage_base, filename)
            abs_path = os.path.join(abs_base, filename)

            # Écrire le fichier + calculer SHA-256
            sha256 = hashlib.sha256()
            file_size = 0
            with open(abs_path, 'wb') as dest:
                for chunk in uploaded_file.chunks():
                    dest.write(chunk)
                    sha256.update(chunk)
                    file_size += len(chunk)

            # Compter les pages avec PyMuPDF
            page_count = None
            try:
                import fitz
                doc = fitz.open(abs_path)
                page_count = doc.page_count
                doc.close()
            except Exception as e:
                logger.warning(f"Impossible de compter les pages de {filename}: {e}")

            exam_doc = ExamDocument.objects.create(
                document_set=doc_set,
                doc_type=doc_type,
                original_filename=uploaded_file.name,
                storage_path=storage_path,
                sha256=sha256.hexdigest(),
                file_size=file_size,
                page_count=page_count,
                uploaded_by=request.user
            )

            # Créer l'extraction en attente
            DocumentTextExtraction.objects.create(
                document=exam_doc,
                status=DocumentTextExtraction.Status.PENDING,
                engine='pymupdf'
            )

            created_docs.append({
                'id': str(exam_doc.id),
                'doc_type': doc_type,
                'original_filename': uploaded_file.name,
                'page_count': page_count,
                'file_size': file_size,
                'sha256': sha256.hexdigest(),
            })

        # Lancer l'extraction asynchrone via Celery
        try:
            from exams.tasks import process_document_set
            process_document_set.delay(str(doc_set.id))
        except Exception as e:
            logger.warning(f"Impossible de lancer l'extraction asynchrone: {e}")

        return Response({
            'id': str(doc_set.id),
            'exam_id': str(exam.id),
            'version': next_version,
            'label': label,
            'documents': created_docs,
        }, status=status.HTTP_201_CREATED)


class DocumentSetListView(APIView):
    """
    GET /api/exams/<exam_id>/document-sets/
    
    Liste les lots documentaires d'un examen avec état d'extraction.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        doc_sets = ExamDocumentSet.objects.filter(exam=exam).order_by('-version')

        result = []
        for ds in doc_sets:
            docs = []
            for doc in ds.documents.all():
                latest_extraction = doc.extractions.order_by('-created_at').first()
                docs.append({
                    'id': str(doc.id),
                    'doc_type': doc.doc_type,
                    'original_filename': doc.original_filename,
                    'page_count': doc.page_count,
                    'file_size': doc.file_size,
                    'extraction_status': latest_extraction.status if latest_extraction else None,
                    'extraction_error': latest_extraction.error_message if latest_extraction and latest_extraction.status == 'failed' else None,
                })
            result.append({
                'id': str(ds.id),
                'version': ds.version,
                'label': ds.label,
                'is_active': ds.is_active,
                'created_at': ds.created_at.isoformat(),
                'documents': docs,
            })

        return Response(result)


class DocumentSetActivateView(APIView):
    """
    POST /api/exams/<exam_id>/document-sets/<set_id>/activate/
    
    Active un lot documentaire (désactive les autres).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, exam_id, set_id):
        if not _is_admin(request.user):
            return Response(
                {"detail": "Seuls les administrateurs peuvent activer un lot documentaire."},
                status=status.HTTP_403_FORBIDDEN
            )

        doc_set = get_object_or_404(ExamDocumentSet, id=set_id, exam_id=exam_id)
        ExamDocumentSet.objects.filter(exam_id=exam_id, is_active=True).update(is_active=False)
        doc_set.is_active = True
        doc_set.save(update_fields=['is_active'])

        return Response({"detail": f"Version {doc_set.version} activée."})


class DocumentSetRetryExtractionView(APIView):
    """
    POST /api/exams/<exam_id>/document-sets/<set_id>/retry-extraction/
    
    Relance l'extraction de texte pour un lot documentaire.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, exam_id, set_id):
        if not _is_admin(request.user):
            return Response(
                {"detail": "Seuls les administrateurs peuvent relancer l'extraction."},
                status=status.HTTP_403_FORBIDDEN
            )

        doc_set = get_object_or_404(ExamDocumentSet, id=set_id, exam_id=exam_id)

        # Réinitialiser les extractions en échec
        for doc in doc_set.documents.all():
            for ext in doc.extractions.filter(status='failed'):
                ext.status = 'pending'
                ext.error_message = None
                ext.save(update_fields=['status', 'error_message'])

        try:
            from exams.tasks import process_document_set
            process_document_set.delay(str(doc_set.id))
        except Exception as e:
            logger.warning(f"Impossible de relancer l'extraction: {e}")

        return Response({"detail": "Extraction relancée."})
