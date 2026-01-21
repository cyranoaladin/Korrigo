from django.db import models
import uuid
from django.utils.translation import gettext_lazy as _

class Exam(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name=_("Nom de l'examen"))
    date = models.DateField(verbose_name=_("Date de l'examen"))
    pdf_source = models.FileField(upload_to='exams/source/', verbose_name=_("Fichier PDF source"))
    grading_structure = models.JSONField(default=list, blank=True, verbose_name=_("Barème (Structure JSON)"))
    is_processed = models.BooleanField(default=False, verbose_name=_("Traité ?"))

    class Meta:
        verbose_name = _("Examen")
        verbose_name_plural = _("Examens")

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
        on_delete=models.CASCADE, 
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
        GRADED = 'GRADED', _("Corrigé")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(
        Exam, 
        on_delete=models.CASCADE, 
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

    class Meta:
        verbose_name = _("Copie")
        verbose_name_plural = _("Copies")

    def __str__(self):
        return f"Copie {self.anonymous_id} ({self.get_status_display()})"
