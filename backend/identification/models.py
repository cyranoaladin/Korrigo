from django.db import models
from students.models import Student
from exams.models import Copy
import uuid


class OCRResult(models.Model):
    """
    Résultat de l'OCR sur un en-tête de copie (multi-layer OCR avec top-k candidates)
    """
    # OCR Modes
    AUTO = 'AUTO'
    SEMI_AUTO = 'SEMI_AUTO'
    MANUAL = 'MANUAL'
    OCR_MODE_CHOICES = [
        (AUTO, 'Automatique'),
        (SEMI_AUTO, 'Semi-automatique'),
        (MANUAL, 'Manuel'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    copy = models.OneToOneField(
        Copy,
        on_delete=models.CASCADE,
        related_name='ocr_result',
        verbose_name="Copie"
    )
    detected_text = models.TextField(
        verbose_name="Texte détecté par OCR"
    )
    confidence = models.FloatField(
        verbose_name="Confiance OCR",
        help_text="Valeur entre 0 et 1"
    )
    suggested_students = models.ManyToManyField(
        Student,
        related_name='ocr_suggestions',
        verbose_name="Élèves suggérés",
        blank=True
    )

    # Multi-layer OCR fields (PRD-19)
    top_candidates = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Top-K candidats",
        help_text="Liste des top-5 candidats avec scores de consensus"
    )
    ocr_mode = models.CharField(
        max_length=20,
        choices=OCR_MODE_CHOICES,
        default=MANUAL,
        verbose_name="Mode OCR",
        help_text="Détermine si l'identification est automatique, semi-automatique ou manuelle"
    )
    selected_candidate_rank = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Rang du candidat sélectionné",
        help_text="Si l'enseignant sélectionne un candidat de la liste top-k (1-5)"
    )
    manual_override = models.BooleanField(
        default=False,
        verbose_name="Remplacement manuel",
        help_text="True si l'enseignant a remplacé l'identification OCR manuellement"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Résultat OCR"
        verbose_name_plural = "Résultats OCR"