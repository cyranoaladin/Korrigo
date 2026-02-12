from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
import uuid
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .validators import (
    validate_pdf_size,
    validate_pdf_not_empty,
    validate_pdf_mime_type,
    validate_pdf_integrity,
)

class Exam(models.Model):
    class UploadMode(models.TextChoices):
        BATCH_A3 = 'BATCH_A3', _("Scan par lots (A3) - Découpage automatique")
        INDIVIDUAL_A4 = 'INDIVIDUAL_A4', _("Fichiers individuels (A4) - Déjà découpés")
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name=_("Nom de l'examen"))
    date = models.DateField(verbose_name=_("Date de l'examen"))
    
    # Upload mode selection
    upload_mode = models.CharField(
        max_length=20,
        choices=UploadMode.choices,
        default=UploadMode.BATCH_A3,
        verbose_name=_("Mode d'upload"),
        help_text=_("BATCH_A3: scan par lots à découper | INDIVIDUAL_A4: fichiers déjà découpés par élève")
    )
    
    # CSV file for student list
    students_csv = models.FileField(
        upload_to='exams/csv/',
        verbose_name=_("Liste des élèves (CSV)"),
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        help_text=_("Fichier CSV contenant la liste des élèves (optionnel)")
    )
    
    # Legacy single PDF field - used for BATCH_A3 mode
    pdf_source = models.FileField(
        upload_to='exams/source/',
        verbose_name=_("Fichier PDF source"),
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf']),
            validate_pdf_size,
            validate_pdf_not_empty,
            validate_pdf_mime_type,
            validate_pdf_integrity,
        ],
        help_text=_("Fichier PDF uniquement. Taille max: 50 MB, 500 pages max")
    )
    pages_per_booklet = models.PositiveIntegerField(
        default=4,
        verbose_name=_("Pages par fascicule"),
        help_text=_("Nombre de pages par copie/fascicule pour le découpage automatique.")
    )
    grading_structure = models.JSONField(default=list, blank=True, verbose_name=_("Barème (Structure JSON)"))
    is_processed = models.BooleanField(default=False, verbose_name=_("Traité ?"))
    
    # Mission 24: Assigned Correctors
    correctors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='assigned_exams',
        verbose_name=_("Correcteurs assignés"),
        blank=True
    )
    
    # Result release control
    results_released_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de publication des résultats"),
        help_text=_("Quand non-null, les élèves peuvent voir leurs résultats")
    )

    # P7 FIX: Timestamps for audit trail
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date de création"),
        null=True
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Date de modification"),
        null=True
    )

    class Meta:
        verbose_name = _("Examen")
        verbose_name_plural = _("Examens")

    def __init__(self, *args, **kwargs):
        # P14 FIX: Safely handle legacy aliases only when creating via kwargs (not from DB)
        if not args:
            if "title" in kwargs and "name" not in kwargs:
                kwargs["name"] = kwargs.pop("title")
            kwargs.pop("created_by", None)
            if "date" not in kwargs:
                kwargs["date"] = timezone.now().date()
        super().__init__(*args, **kwargs)

    def __str__(self):
        return self.name

class Booklet(models.Model):
    """
    Représente un fascicule (groupe de pages) détecté automatiquement.
    C'est une entité de "Staging" avant validation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(
        Exam, 
        on_delete=models.PROTECT,  # P0-DI-005 FIX: Prevent accidental deletion of booklets
        related_name='booklets',
        verbose_name=_("Examen")
    )
    start_page = models.PositiveIntegerField(verbose_name=_("Page de début"))
    end_page = models.PositiveIntegerField(verbose_name=_("Page de fin"))
    header_image = models.ImageField(
        upload_to='booklets/headers/',
        verbose_name=_("Image de l'en-tête"),
        help_text=_("Image rognée de la zone nom pour validation manuelle."),
        blank=True,
        null=True
    )
    student_name_guess = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name=_("Estimation du nom (OCR)")
    )
    pages_images = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Liste des pages ordonnée"),
        help_text=_("Liste des chemins des images [P1, P2, P3, P4] après split.")
    )

    class Meta:
        verbose_name = _("Fascicule")
        verbose_name_plural = _("Fascicules")

    def __str__(self):
        return f"Fascicule {self.id} (Pages {self.start_page}-{self.end_page})"

class Copy(models.Model):
    """
    Entité finale validée. Une copie peut être composée de plusieurs fascicules fusionnés.
    """
    class Status(models.TextChoices):
        STAGING = 'STAGING', _("En attente")
        READY = 'READY', _("Prêt à corriger")
        LOCKED = 'LOCKED', _("Verrouillé")
        GRADING_IN_PROGRESS = 'GRADING_IN_PROGRESS', _("Correction en cours")
        GRADING_FAILED = 'GRADING_FAILED', _("Échec de correction")
        GRADED = 'GRADED', _("Corrigé")

    class SubjectVariant(models.TextChoices):
        A = 'A', _("Sujet A")
        B = 'B', _("Sujet B")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(
        Exam, 
        on_delete=models.PROTECT,  # P0-DI-005 FIX: Prevent catastrophic deletion of all student data
        related_name='copies',
        verbose_name=_("Examen")
    )
    # Booklets will be linked via ManyToMany or Foreign Key? 
    # Logic in SPEC implies Copy is created FROM booklets. 
    # Let's keep a connection if needed, or if booklets are consumed.
    # For now, following strict fields requested:
    
    anonymous_id = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Anonymat")
    )
    final_pdf = models.FileField(
        upload_to='copies/final/',
        verbose_name=_("PDF Final Anonymisé"),
        blank=True,
        null=True
    )
    pdf_source = models.FileField(
        upload_to='copies/source/',
        verbose_name=_("Fichier PDF source"),
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf']),
            validate_pdf_size,
            validate_pdf_not_empty,
            validate_pdf_mime_type,
            validate_pdf_integrity,
        ],
        help_text=_("Fichier PDF uniquement. Taille max: 50 MB, 500 pages max")
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.STAGING,
        verbose_name=_("Statut")
    )

    # Adding ManyToMany relationship to Booklet to track composition as implied
    booklets = models.ManyToManyField(
        Booklet,
        related_name='assigned_copy',
        verbose_name=_("Fascicules composants"),
        blank=True
    )

    # Link to Student (Mission 17)
    student = models.ForeignKey(
        'students.Student', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='copies',
        verbose_name=_("Élève identifié")
    )
    is_identified = models.BooleanField(
        default=False,
        verbose_name=_("Identifié ?"),
        help_text=_("Vrai si la copie a été associée à un élève.")
    )

    # Dispatch fields for copy assignment
    assigned_corrector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_copies',
        verbose_name=_("Correcteur assigné")
    )
    dispatch_run_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_("ID d'exécution du dispatch"),
        help_text=_("UUID généré lors du dispatch pour traçabilité")
    )
    assigned_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date d'assignation"),
        help_text=_("Timestamp de l'assignation au correcteur")
    )

    # Traçabilité (ADR-003)
    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de validation"),
        help_text=_("Timestamp STAGING → READY")
    )
    
    # P0-DI-004: Error tracking for failed grading operations
    grading_error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Message d'erreur de correction"),
        help_text=_("Détails de l'erreur si la correction échoue")
    )
    grading_retries = models.IntegerField(
        default=0,
        verbose_name=_("Nombre de tentatives"),
        help_text=_("Nombre de tentatives de correction automatique")
    )
    locked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de verrouillage"),
        help_text=_("Timestamp READY → LOCKED")
    )
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locked_copies',
        verbose_name=_("Verrouillé par")
    )
    graded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de notation"),
        help_text=_("Timestamp LOCKED → GRADED")
    )
    
    # Global appreciation for the copy
    global_appreciation = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Appréciation globale"),
        help_text=_("Commentaire global du correcteur pour cette copie")
    )

    # Subject variant (Sujet A / Sujet B) — set manually by corrector
    subject_variant = models.CharField(
        max_length=1,
        choices=SubjectVariant.choices,
        null=True,
        blank=True,
        verbose_name=_("Variante du sujet"),
        help_text=_("Sujet A ou B, identifié par le correcteur via la référence en bas de l'annexe")
    )

    class Meta:
        verbose_name = _("Copie")
        verbose_name_plural = _("Copies")

    def __str__(self):
        return f"Copie {self.anonymous_id} ({self.get_status_display()})"


class ExamPDF(models.Model):
    """
    Représente un fichier PDF individuel uploadé pour un examen.
    Utilisé dans le mode INDIVIDUAL_A4 où chaque PDF correspond à la copie d'un élève.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='individual_pdfs',
        verbose_name=_("Examen")
    )
    pdf_file = models.FileField(
        upload_to='exams/individual/',
        verbose_name=_("Fichier PDF individuel"),
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf']),
            validate_pdf_size,
            validate_pdf_not_empty,
            validate_pdf_mime_type,
            validate_pdf_integrity,
        ],
        help_text=_("Fichier PDF d'un élève (A4)")
    )
    student_identifier = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Identifiant élève"),
        help_text=_("Nom ou identifiant extrait du nom de fichier (optionnel)")
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date d'upload")
    )
    
    class Meta:
        verbose_name = _("PDF Individuel")
        verbose_name_plural = _("PDFs Individuels")
        ordering = ['uploaded_at']
    
    def __str__(self):
        return f"PDF {self.student_identifier or self.id} - {self.exam.name}"


class ExamDocumentSet(models.Model):
    """
    Lot documentaire versionné pour un examen.
    Contient les 3 PDFs officiels : sujet, corrigé, barème.
    Chaque nouvelle version crée un nouveau lot pour traçabilité.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='document_sets',
        verbose_name=_("Examen")
    )
    version = models.PositiveIntegerField(
        verbose_name=_("Version"),
        help_text=_("Numéro de version (v1, v2, ...)")
    )
    label = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Libellé"),
        help_text=_("Ex: 'BB 2026 J1 - Officiel'")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Version active"),
        help_text=_("Seule la version active est utilisée par les correcteurs")
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_document_sets',
        verbose_name=_("Créé par")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))

    class Meta:
        verbose_name = _("Lot documentaire")
        verbose_name_plural = _("Lots documentaires")
        unique_together = ['exam', 'version']
        ordering = ['-version']

    def __str__(self):
        return f"{self.exam.name} - v{self.version} {'(actif)' if self.is_active else ''}"


class ExamDocument(models.Model):
    """
    Un document PDF individuel (sujet, corrigé ou barème) au sein d'un lot.
    Stockage sécurisé avec hash SHA-256 pour traçabilité et déduplication.
    """
    class DocType(models.TextChoices):
        SUJET = 'sujet', _("Sujet")
        CORRIGE = 'corrige', _("Corrigé")
        BAREME = 'bareme', _("Barème")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_set = models.ForeignKey(
        ExamDocumentSet,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_("Lot documentaire")
    )
    doc_type = models.CharField(
        max_length=20,
        choices=DocType.choices,
        verbose_name=_("Type de document")
    )
    original_filename = models.CharField(
        max_length=512,
        verbose_name=_("Nom de fichier original")
    )
    storage_path = models.CharField(
        max_length=1024,
        verbose_name=_("Chemin de stockage"),
        help_text=_("Chemin relatif dans MEDIA_ROOT")
    )
    mime_type = models.CharField(
        max_length=100,
        default='application/pdf',
        verbose_name=_("Type MIME")
    )
    sha256 = models.CharField(
        max_length=64,
        verbose_name=_("Hash SHA-256"),
        help_text=_("Pour traçabilité et déduplication")
    )
    file_size = models.BigIntegerField(
        verbose_name=_("Taille du fichier (octets)")
    )
    page_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Nombre de pages")
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_documents',
        verbose_name=_("Uploadé par")
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date d'upload"))

    class Meta:
        verbose_name = _("Document d'examen")
        verbose_name_plural = _("Documents d'examen")
        unique_together = ['document_set', 'doc_type']
        ordering = ['doc_type']

    def __str__(self):
        return f"{self.get_doc_type_display()} - {self.original_filename}"


class DocumentTextExtraction(models.Model):
    """
    État du pipeline d'extraction de texte pour un document PDF.
    Permet le suivi asynchrone et la relance en cas d'échec.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _("En attente")
        PROCESSING = 'processing', _("En cours")
        DONE = 'done', _("Terminé")
        FAILED = 'failed', _("Échoué")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        ExamDocument,
        on_delete=models.CASCADE,
        related_name='extractions',
        verbose_name=_("Document")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Statut")
    )
    engine = models.CharField(
        max_length=30,
        default='pymupdf',
        verbose_name=_("Moteur d'extraction"),
        help_text=_("Ex: pymupdf, pdfminer")
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Message d'erreur")
    )
    extracted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date d'extraction")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))

    class Meta:
        verbose_name = _("Extraction de texte")
        verbose_name_plural = _("Extractions de texte")
        ordering = ['-created_at']

    def __str__(self):
        return f"Extraction {self.get_status_display()} - {self.document}"


class DocumentPage(models.Model):
    """
    Texte extrait page par page d'un document PDF.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    extraction = models.ForeignKey(
        DocumentTextExtraction,
        on_delete=models.CASCADE,
        related_name='pages',
        verbose_name=_("Extraction")
    )
    page_number = models.PositiveIntegerField(
        verbose_name=_("Numéro de page")
    )
    page_text = models.TextField(
        verbose_name=_("Texte de la page")
    )

    class Meta:
        verbose_name = _("Page de document")
        verbose_name_plural = _("Pages de document")
        unique_together = ['extraction', 'page_number']
        ordering = ['page_number']

    def __str__(self):
        return f"Page {self.page_number} - {self.extraction.document}"


class DocumentChunk(models.Model):
    """
    Segment de texte indexé pour recherche full-text et suggestions contextuelles.
    Découpé par exercice/question pour permettre des suggestions ciblées.
    """
    class DocType(models.TextChoices):
        SUJET = 'sujet', _("Sujet")
        CORRIGE = 'corrige', _("Corrigé")
        BAREME = 'bareme', _("Barème")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    extraction = models.ForeignKey(
        DocumentTextExtraction,
        on_delete=models.CASCADE,
        related_name='chunks',
        verbose_name=_("Extraction")
    )
    doc_type = models.CharField(
        max_length=20,
        choices=DocType.choices,
        verbose_name=_("Type de document source")
    )
    chunk_index = models.PositiveIntegerField(
        verbose_name=_("Index du segment")
    )
    page_start = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Page de début")
    )
    page_end = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Page de fin")
    )
    exercise_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Numéro d'exercice"),
        help_text=_("Détecté automatiquement lors du chunking")
    )
    question_label = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Label de question"),
        help_text=_("Ex: '3b', 'A.1', etc.")
    )
    chunk_text = models.TextField(
        verbose_name=_("Texte du segment")
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Tags"),
        help_text=_("Tags pour filtrage et recherche")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))

    class Meta:
        verbose_name = _("Segment de document")
        verbose_name_plural = _("Segments de document")
        unique_together = ['extraction', 'chunk_index']
        ordering = ['chunk_index']

    def __str__(self):
        ex = f"Ex{self.exercise_number}" if self.exercise_number else ""
        q = f" Q{self.question_label}" if self.question_label else ""
        return f"Chunk {self.chunk_index} {ex}{q} - {self.extraction.document}"
