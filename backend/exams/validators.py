"""
Validators pour les fichiers PDF
Conformité: docs/security/MANUEL_SECURITE.md — Validation PDF
"""
import magic
import fitz  # PyMuPDF
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_pdf_size(value):
    """
    Valide que la taille du fichier PDF ne dépasse pas 50 MB.
    
    Args:
        value: UploadedFile instance
        
    Raises:
        ValidationError: Si le fichier dépasse 50 MB
    """
    limit = 50 * 1024 * 1024  # 50 MB
    if value.size > limit:
        size_mb = value.size / (1024 * 1024)
        raise ValidationError(
            _(f'Fichier trop volumineux. Taille maximale: 50 MB. Taille actuelle: {size_mb:.1f} MB'),
            code='file_too_large'
        )


def validate_pdf_not_empty(value):
    """
    Valide que le fichier PDF n'est pas vide.
    
    Args:
        value: UploadedFile instance
        
    Raises:
        ValidationError: Si le fichier est vide (0 bytes)
    """
    if value.size == 0:
        raise ValidationError(
            _('Le fichier PDF est vide (0 bytes)'),
            code='empty_file'
        )


def validate_pdf_mime_type(value):
    """
    Valide que le fichier est vraiment un PDF en vérifiant le MIME type.
    Protection contre les fichiers renommés avec extension .pdf.
    
    Args:
        value: UploadedFile instance
        
    Raises:
        ValidationError: Si le MIME type n'est pas application/pdf
    """
    try:
        # Lire les premiers 2048 bytes pour détection MIME
        value.seek(0)
        file_head = value.read(2048)
        value.seek(0)
        
        # Détecter le MIME type
        mime = magic.from_buffer(file_head, mime=True)
        
        # Accepter application/pdf et application/x-pdf
        valid_mimes = ['application/pdf', 'application/x-pdf']
        
        if mime not in valid_mimes:
            raise ValidationError(
                _(f'Type MIME invalide: {mime}. Attendu: application/pdf'),
                code='invalid_mime_type'
            )
    except ValidationError:
        # Re-raise ValidationError (already formatted with proper code)
        raise
    except Exception as e:
        # Si python-magic échoue (library issue), on laisse passer (graceful degradation)
        # Mais on log l'erreur - only for true library/system errors, not validation failures
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"MIME type library error: {e}")


def validate_pdf_integrity(value):
    """
    Valide l'intégrité du PDF avec PyMuPDF.
    Vérifie que le PDF n'est pas corrompu et a un nombre raisonnable de pages.
    
    Args:
        value: UploadedFile instance
        
    Raises:
        ValidationError: Si le PDF est corrompu ou invalide
    """
    try:
        # Lire le contenu du fichier
        value.seek(0)
        pdf_bytes = value.read()
        value.seek(0)
        
        # Ouvrir avec PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = doc.page_count
        doc.close()
        
        # Validation nombre de pages
        if page_count == 0:
            raise ValidationError(
                _('PDF vide (0 pages)'),
                code='empty_pdf'
            )
        
        if page_count > 500:
            raise ValidationError(
                _(f'PDF trop volumineux: {page_count} pages. Maximum: 500 pages'),
                code='too_many_pages'
            )
            
    except ValidationError:
        # Re-raise ValidationError (déjà formatée)
        raise
    except Exception as e:
        # Toute autre erreur = PDF corrompu
        raise ValidationError(
            _(f'PDF corrompu ou invalide: {str(e)}'),
            code='corrupted_pdf'
        )
