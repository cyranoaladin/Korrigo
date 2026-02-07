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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name=_("Nom de l'examen"))
    date = models.DateField(verbose_name=_("Date de l'examen"))
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
    student_csv = models.FileField(
        upload_to='exams/csv/',
        verbose_name=_("Fichier CSV des élèves"),
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        help_text=_("Fichier CSV pour l'identification des élèves (whitelist).")
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

    class Meta:
        verbose_name = _("Examen")
        verbose_name_plural = _("Examens")

    def __init__(self, *args, **kwargs):
        if "title" in kwargs and "name" not in kwargs:
            kwargs["name"] = kwargs.pop("title")
        kwargs.pop("created_by", None)
        # P0-DI-006 FIX: Only set default date if not loading from DB
        # When loading from DB, Django passes field values via *args
        # Adding date to kwargs would cause "positional and keyword" conflict
        if not args and "date" not in kwargs:
            kwargs["date"] = timezone.now().date()
        super().__init__(*args, **kwargs)

    def __str__(self):
        return self.name

class ExamSourcePDF(models.Model):
    """
    Stocke un fichier PDF source individuel uploadé pour un examen.
    Un examen peut avoir plusieurs PDFs (ex: lots de scans différents).
    Chaque PDF est détecté indépendamment comme A3 ou A4.
    """
    class Format(models.TextChoices):
        A3 = 'A3', 'A3'
        A4 = 'A4', 'A4'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='source_pdfs',
        verbose_name=_("Examen")
    )
    pdf_file = models.FileField(
        upload_to='exams/source/',
        verbose_name=_("Fichier PDF"),
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf']),
            validate_pdf_size,
            validate_pdf_not_empty,
            validate_pdf_mime_type,
            validate_pdf_integrity,
        ],
    )
    original_filename = models.CharField(
        max_length=255,
        verbose_name=_("Nom du fichier original")
    )
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Ordre d'affichage")
    )
    detected_format = models.CharField(
        max_length=10,
        choices=Format.choices,
        default=Format.A4,
        verbose_name=_("Format détecté")
    )
    page_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Nombre de pages")
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("PDF Source")
        verbose_name_plural = _("PDFs Source")
        ordering = ['display_order', 'uploaded_at']

    def __str__(self):
        return f"{self.original_filename} ({self.detected_format}, {self.page_count}p)"


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
    source_pdf = models.ForeignKey(
        'ExamSourcePDF',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='booklets',
        verbose_name=_("PDF source d'origine")
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

    # Valid status transitions (state machine)
    ALLOWED_TRANSITIONS = {
        Status.STAGING: {Status.READY},
        Status.READY: {Status.LOCKED, Status.STAGING},
        Status.LOCKED: {Status.GRADING_IN_PROGRESS, Status.READY},
        Status.GRADING_IN_PROGRESS: {Status.GRADED, Status.GRADING_FAILED},
        Status.GRADING_FAILED: {Status.GRADING_IN_PROGRESS, Status.LOCKED},
        Status.GRADED: set(),  # Terminal state
    }

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
        db_index=True,  # Performance optimization for filtering
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
        db_index=True,  # Performance optimization for filtering
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

    def transition_to(self, new_status):
        """
        Transition the copy to a new status with state machine validation.
        Raises ValueError if the transition is not allowed.
        """
        old_status = self.status
        allowed = Copy.ALLOWED_TRANSITIONS.get(old_status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid status transition: {old_status} → {new_status}. "
                f"Allowed: {', '.join(sorted(allowed)) or 'none (terminal state)'}"
            )
        self.status = new_status

    class Meta:
        verbose_name = _("Copie")
        verbose_name_plural = _("Copies")
        # ZF-AUD-13: Performance indexes for common queries
        indexes = [
            models.Index(fields=['exam', 'status'], name='copy_exam_status_idx'),
            models.Index(fields=['assigned_corrector', 'status'], name='copy_corrector_status_idx'),
            models.Index(fields=['student', 'status'], name='copy_student_status_idx'),
            models.Index(fields=['dispatch_run_id'], name='copy_dispatch_run_idx'),
            models.Index(fields=['exam', 'is_identified'], name='copy_exam_identified_idx'),
        ]

    def __str__(self):
        return f"Copie {self.anonymous_id} ({self.get_status_display()})"
