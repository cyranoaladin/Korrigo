from django.db import models
from django.conf import settings
from exams.models import Copy
from django.utils.translation import gettext_lazy as _
import uuid


class Annotation(models.Model):
    """
    Annotation vectorielle sur une copie.
    Coordonnées normalisées [0,1] selon ADR-002.
    """
    class Type(models.TextChoices):
        COMMENT = 'COMMENT', _("Commentaire")
        HIGHLIGHT = 'HIGHLIGHT', _("Surligné")
        ERROR = 'ERROR', _("Erreur")
        BONUS = 'BONUS', _("Bonus")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    copy = models.ForeignKey(
        Copy,
        on_delete=models.CASCADE,
        related_name='annotations',
        verbose_name=_("Copie")
    )
    page_index = models.PositiveIntegerField(
        verbose_name=_("Index de page (0-based)"),
        help_text=_("Index de la page (0 = première page)")
    )

    # ADR-002 : Coordonnées normalisées [0, 1]
    x = models.FloatField(
        verbose_name=_("Position X normalisée"),
        help_text=_("Position X dans l'intervalle [0,1]")
    )
    y = models.FloatField(
        verbose_name=_("Position Y normalisée"),
        help_text=_("Position Y dans l'intervalle [0,1]")
    )
    w = models.FloatField(
        verbose_name=_("Largeur normalisée"),
        help_text=_("Largeur dans l'intervalle [0,1]")
    )
    h = models.FloatField(
        verbose_name=_("Hauteur normalisée"),
        help_text=_("Hauteur dans l'intervalle [0,1]")
    )

    content = models.TextField(
        blank=True,
        verbose_name=_("Contenu"),
        help_text=_("Texte ou données JSON de l'annotation")
    )
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.COMMENT,
        verbose_name=_("Type d'annotation")
    )
    score_delta = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Variation de score"),
        help_text=_("Points ajoutés/retirés (peut être négatif)")
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='annotations_created',
        verbose_name=_("Créé par")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Date de modification"))
    
    # P0-DI-008: Optimistic locking to prevent lost updates
    version = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Version"),
        help_text=_("Numéro de version pour le verrouillage optimiste")
    )

    class Meta:
        verbose_name = _("Annotation")
        verbose_name_plural = _("Annotations")
        ordering = ['page_index', 'created_at']
        indexes = [
            models.Index(fields=['copy', 'page_index']),
        ]

    def __init__(self, *args, **kwargs):
        if args:
            super().__init__(*args, **kwargs)
            return
        if "annotation_type" in kwargs and "type" not in kwargs:
            kwargs["type"] = kwargs.pop("annotation_type")
        if "page_number" in kwargs and "page_index" not in kwargs:
            kwargs["page_index"] = kwargs.pop("page_number")
        if "w" not in kwargs:
            kwargs["w"] = 0.1
        if "h" not in kwargs:
            kwargs["h"] = 0.1
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"Annotation {self.type} - Page {self.page_index} (Copy {self.copy.anonymous_id})"


class GradingEvent(models.Model):
    """
    Journal d'audit des événements de correction.
    Traçabilité complète du workflow (ADR-003).
    Includes Audit Trail for all major actions (IMPORT, ANNOTATE, etc.)
    """
    class Action(models.TextChoices):
        IMPORT = 'IMPORT', _("Import Copie")
        VALIDATE = 'VALIDATE', _("Validation (STAGING→READY)")
        LOCK = 'LOCK', _("Verrouillage (READY→LOCKED)")
        UNLOCK = 'UNLOCK', _("Déverrouillage (LOCKED→READY)")
        CREATE_ANN = 'CREATE_ANN', _("Création Annotation")
        UPDATE_ANN = 'UPDATE_ANN', _("Modification Annotation")
        DELETE_ANN = 'DELETE_ANN', _("Suppression Annotation")
        FINALIZE = 'FINALIZE', _("Finalisation (LOCKED→GRADED)")
        EXPORT = 'EXPORT', _("Export PDF")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    copy = models.ForeignKey(
        Copy,
        on_delete=models.CASCADE,
        related_name='grading_events',
        verbose_name=_("Copie")
    )
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        verbose_name=_("Action")
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='grading_actions',
        verbose_name=_("Acteur")
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Horodatage")
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Métadonnées"),
        help_text=_("Données contextuelles (score, raison, etc.)")
    )

    class Meta:
        verbose_name = _("Événement de correction")
        verbose_name_plural = _("Événements de correction")
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['copy', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.copy.anonymous_id} par {self.actor.username}"


class CopyLock(models.Model):
    """
    Soft Lock pour l'édition concurrente des copies (Voie C3).
    Garantit qu'un seul utilisateur peut éditer une copie à la fois.
    """
    copy = models.OneToOneField(
        Copy,
        on_delete=models.CASCADE,
        related_name='lock',
        verbose_name=_("Copie")
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='copy_locks',
        verbose_name=_("Propriétaire")
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Token de session")
    )
    locked_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Verrouillé le")
    )
    expires_at = models.DateTimeField(
        verbose_name=_("Expire le"),
        db_index=True
    )
    
    class Meta:
        verbose_name = _("Verrou de copie")
        verbose_name_plural = _("Verrous de copies")
        constraints = [
            models.UniqueConstraint(fields=["copy"], name="uniq_copylock_copy"),
        ]
        indexes = [
            models.Index(fields=["expires_at"], name="idx_copylock_expires_at"),
            models.Index(fields=["owner"], name="idx_copylock_owner"),
            models.Index(fields=["copy"], name="idx_copylock_copy"),
        ]
        
    def __str__(self):
        return f"Lock {self.copy.anonymous_id} by {self.owner} (expires {self.expires_at})"


class DraftState(models.Model):
    """
    Etat brouillon (autosave) d'une copie en cours de correction.
    Permet de ne pas perdre de données en cas de crash/refresh.
    Un seul draft par user/copie (le dernier).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    copy = models.ForeignKey(
        Copy,
        on_delete=models.CASCADE,
        related_name='drafts',
        verbose_name=_("Copie")
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='grading_drafts',
        verbose_name=_("Propriétaire")
    )
    payload = models.JSONField(
        default=dict,
        verbose_name=_("Contenu Draft"),
        help_text=_("Etat complet de l'éditeur (annotations, texte en cours)")
    )
    lock_token = models.UUIDField(
        null=True, 
        blank=True,
        verbose_name=_("Token de verrou associé")
    )
    client_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_("ID Client (Anti-écrasement)")
    )
    version = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Version")
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Brouillon de correction")
        verbose_name_plural = _("Brouillons de correction")
        unique_together = ['copy', 'owner'] # One draft per copy per user
    
    def __str__(self):
        return f"Draft {self.copy.anonymous_id} by {self.owner} (v{self.version})"
