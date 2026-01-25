from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class GlobalSettings(models.Model):
    """
    Paramètres globaux de l'application (Singleton par convention ou id=1).
    """
    institution_name = models.CharField(max_length=255, default="Lycée Pierre Mendès France", verbose_name=_("Nom Etablissement"))
    theme = models.CharField(max_length=20, default="light", verbose_name=_("Thème par défaut"))
    default_exam_duration = models.PositiveIntegerField(default=60, verbose_name=_("Durée par défaut (min)"))
    notifications_enabled = models.BooleanField(default=True, verbose_name=_("Notifications Email"))
    
    # Singleton pattern helper
    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super(GlobalSettings, self).save(*args, **kwargs)

    class Meta:
        verbose_name = _("Configuration Système")
        verbose_name_plural = _("Configuration Système")

class AuditLog(models.Model):
    """
    Table d'audit centralisée pour actions critiques.
    Conformité RGPD/CNIL - Traçabilité obligatoire.
    
    Référence: .antigravity/rules/01_security_rules.md § 7.3
    """
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_("Horodatage"))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name=_("Utilisateur")
    )
    student_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("ID Élève"),
        help_text=_("Si session élève (pas de User Django)")
    )
    action = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_("Action"),
        help_text=_("Ex: login.success, copy.download, copy.unlock")
    )
    resource_type = models.CharField(
        max_length=50,
        verbose_name=_("Type de ressource"),
        help_text=_("Ex: Copy, Exam, Student")
    )
    resource_id = models.CharField(
        max_length=255,
        verbose_name=_("ID Ressource")
    )
    ip_address = models.GenericIPAddressField(
        verbose_name=_("Adresse IP")
    )
    user_agent = models.TextField(
        verbose_name=_("User Agent"),
        help_text=_("Navigateur et système")
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Métadonnées"),
        help_text=_("Données contextuelles additionnelles")
    )

    class Meta:
        verbose_name = _("Log d'audit")
        verbose_name_plural = _("Logs d'audit")
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['student_id', '-timestamp']),
        ]

    def __str__(self):
        actor = self.user.username if self.user else f"Student#{self.student_id}" if self.student_id else "Anonymous"
        return f"{self.action} by {actor} at {self.timestamp}"
