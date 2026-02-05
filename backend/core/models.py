from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache

class GlobalSettings(models.Model):
    """
    Paramètres globaux de l'application (Singleton par convention ou id=1).
    """
    institution_name = models.CharField(max_length=255, default="Lycée Pierre Mendès France", verbose_name=_("Nom Etablissement"))
    theme = models.CharField(max_length=20, default="light", verbose_name=_("Thème par défaut"))
    default_exam_duration = models.PositiveIntegerField(default=60, verbose_name=_("Durée par défaut (min)"))
    notifications_enabled = models.BooleanField(default=True, verbose_name=_("Notifications Email"))
    
    # Singleton pattern helper with caching
    CACHE_KEY = 'global_settings'
    CACHE_TIMEOUT = 300  # 5 minutes

    @classmethod
    def load(cls):
        """
        Load global settings with Redis caching.
        Phase 4: Performance optimization - cache for 5 minutes.
        """
        # Try to get from cache first
        cached = cache.get(cls.CACHE_KEY)
        if cached:
            return cached

        # Not in cache, fetch from database
        obj, created = cls.objects.get_or_create(pk=1)

        # Store in cache
        cache.set(cls.CACHE_KEY, obj, cls.CACHE_TIMEOUT)

        return obj

    def save(self, *args, **kwargs):
        """Save and invalidate cache."""
        self.pk = 1
        super(GlobalSettings, self).save(*args, **kwargs)

        # Phase 4: Invalidate cache on save
        cache.delete(self.CACHE_KEY)

    @classmethod
    def clear_cache(cls):
        """
        Manually clear the settings cache.
        Useful for debugging or after bulk updates.
        """
        cache.delete(cls.CACHE_KEY)

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

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_("Utilisateur")
    )
    must_change_password = models.BooleanField(
        default=False,
        verbose_name=_("Doit changer le mot de passe"),
        help_text=_("Force l'utilisateur à changer son mot de passe à la prochaine connexion")
    )

    class Meta:
        verbose_name = _("Profil Utilisateur")
        verbose_name_plural = _("Profils Utilisateurs")

    def __str__(self):
        return f"Profile: {self.user.username}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
