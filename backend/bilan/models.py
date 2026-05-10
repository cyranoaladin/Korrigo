"""
Models for DNB Bilan Generation
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
import json
from datetime import datetime

User = get_user_model()


class BilanReport(models.Model):
    """
    Rapport de bilan pédagogique DNB.
    """
    
    EXAM_TYPES = [
        ('DNB_2026', 'DNB 2026'),
        ('BILAN_BLANC', 'Bilan Blanc'),
        ('EAM BLANCHE 2026', 'EAM BLANCHE 2026'),
    ]
    
    SCOPES = [
        ('ETABLISSEMENT', 'Établissement'),
        ('CLASSE', 'Classe'),
        ('GROUPE', 'Groupe'),
    ]
    
    STATUSES = [
        ('PENDING', 'En attente'),
        ('GENERATING', 'En cours de génération'),
        ('DONE', 'Terminé'),
        ('ERROR', 'Erreur'),
    ]
    
    # Métadonnées
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPES)
    exam = models.ForeignKey('exams.Exam', on_delete=models.CASCADE, null=True, blank=True)
    scope = models.CharField(max_length=20, choices=SCOPES, default='ETABLISSEMENT')
    
    # Génération
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUSES, default='PENDING')
    
    # Données
    json_data = models.JSONField(null=True, blank=True)
    pdf_file = models.FileField(upload_to='bilans/%Y/%m/', null=True, blank=True)
    
    # Métadonnées techniques
    llm_model = models.CharField(max_length=100, blank=True)
    rag_collection = models.CharField(max_length=100, blank=True)
    generation_time = models.DurationField(null=True, blank=True)
    
    # Accès
    is_public = models.BooleanField(default=False)  # Visible par tous les enseignants
    
    class Meta:
        ordering = ['-generated_at']
        verbose_name = "Rapport de bilan"
        verbose_name_plural = "Rapports de bilan"
    
    def __str__(self):
        return f"Bilan {self.exam_type} - {self.generated_at.strftime('%d/%m/%Y')}"
    
    @property
    def metadata(self):
        """Métadonnées du bilan."""
        if self.json_data and 'metadata' in self.json_data:
            return self.json_data['metadata']
        return {}
    
    def get_section(self, section_key: str):
        """Récupérer une section spécifique du bilan."""
        if self.json_data and section_key in self.json_data:
            return self.json_data[section_key]
        return None
    
    def can_view(self, user):
        """Vérifier si l'utilisateur peut voir ce bilan."""
        if user.is_staff or user.is_superuser:
            return True

        # Les enseignants peuvent voir les bilans d'établissement
        if self.scope == 'ETABLISSEMENT' and user.groups.filter(
            name__in=['admin', 'teacher', 'corrector']
        ).exists():
            # Si le bilan est lié à un examen, vérifier que l'utilisateur est assigné à cet examen
            if self.exam:
                if self.exam.correctors.filter(id=user.id).exists():
                    return True
            # Sinon, permettre l'accès aux correcteurs/admins/teachers
            return True

        # TODO: Ajouter logique pour classe/groupe

        return False


class BilanSection(models.Model):
    """
    Section individuelle d'un bilan (pour versionnement).
    """
    
    SECTION_TYPES = [
        ('STATS', 'Statistiques globales'),
        ('DOMAINS', 'Analyse par domaine'),
        ('QUESTIONS', 'Analyse question par question'),
        ('COMPETENCES', 'Maîtrise des compétences'),
        ('CORRECTORS', 'Analyse inter-correcteurs'),
        ('PROFILES', 'Profils de la promotion'),
        ('RECOMMENDATIONS', 'Recommandations'),
    ]
    
    report = models.ForeignKey(BilanReport, on_delete=models.CASCADE, related_name='sections')
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES)
    title = models.CharField(max_length=200)
    content = models.JSONField()
    order = models.PositiveIntegerField(default=0)
    
    # Métadonnées de génération
    llm_model = models.CharField(max_length=100, blank=True)
    rag_context_used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['order', 'section_type']
        unique_together = ['report', 'section_type']
    
    def __str__(self):
        return f"{self.report} - {self.get_section_type_display()}"
