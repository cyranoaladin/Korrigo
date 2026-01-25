from django.db import models
from students.models import Student
from exams.models import Copy
import uuid


class OCRResult(models.Model):
    """
    Résultat de l'OCR sur un en-tête de copie
    """
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
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Résultat OCR"
        verbose_name_plural = "Résultats OCR"