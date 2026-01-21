from django.db import models
from exams.models import Copy
from django.utils.translation import gettext_lazy as _
import uuid

class Annotation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    copy = models.ForeignKey(Copy, on_delete=models.CASCADE, related_name='annotations')
    page_number = models.PositiveIntegerField(verbose_name=_("Numéro de page"))
    
    # Vector Data Storage
    vector_data = models.JSONField(verbose_name=_("Données Vectorielles"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Score(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    copy = models.ForeignKey(Copy, on_delete=models.CASCADE, related_name='scores')
    
    # Stores the full grading state: { "ex1q1": 0.5, "ex1q2": 1, ... }
    scores_data = models.JSONField(verbose_name=_("Détail des notes"))
    
    final_comment = models.TextField(blank=True, verbose_name=_("Appréciation Générale"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
