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
        COMMENTAIRE = 'COMMENTAIRE', _("Commentaire")
        SURLIGNAGE = 'SURLIGNAGE', _("Surlignage")
        ERREUR = 'ERREUR', _("Erreur")
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
        default=Type.COMMENTAIRE,
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


class QuestionRemark(models.Model):
    """
    Remarque facultative pour une question du barème.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    copy = models.ForeignKey(
        Copy,
        on_delete=models.CASCADE,
        related_name='question_remarks',
        verbose_name=_("Copie")
    )
    question_id = models.CharField(
        max_length=255,
        verbose_name=_("ID de la question"),
        help_text=_("Identifiant de la question dans le barème")
    )
    remark = models.TextField(
        verbose_name=_("Remarque"),
        blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='question_remarks_created',
        verbose_name=_("Créé par")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Date de modification"))

    class Meta:
        verbose_name = _("Remarque de question")
        verbose_name_plural = _("Remarques de questions")
        unique_together = ['copy', 'question_id']
        indexes = [
            models.Index(fields=['copy', 'question_id']),
        ]

    def __str__(self):
        return f"Remarque {self.question_id} - {self.copy.anonymous_id}"


class Score(models.Model):
    """
    Score détaillé d'une copie avec données JSON.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    copy = models.ForeignKey(
        Copy,
        on_delete=models.CASCADE,
        related_name='scores',
        verbose_name=_("Copie")
    )
    scores_data = models.JSONField(
        verbose_name=_("Détail des notes"),
        help_text=_("Structure JSON contenant les scores par question")
    )
    final_comment = models.TextField(
        blank=True,
        verbose_name=_("Appréciation Générale")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Date de modification"))

    class Meta:
        verbose_name = _("Score")
        verbose_name_plural = _("Scores")

    def __str__(self):
        return f"Score - {self.copy.anonymous_id}"


class AnnotationTemplate(models.Model):
    """
    Banque d'annotations officielles contextualisées par exercice/question.
    Générées automatiquement à partir du barème, corrigé et sujet,
    ou créées manuellement par un admin.
    """
    class CriterionType(models.TextChoices):
        METHOD = 'method', _("Méthode")
        RESULT = 'result', _("Résultat")
        JUSTIFICATION = 'justification', _("Justification")
        REDACTION = 'redaction', _("Rédaction")
        ERROR_TYPIQUE = 'error_typique', _("Erreur typique")
        BONUS = 'bonus', _("Bonus")
        PLAFOND = 'plafond', _("Plafond")

    class Severity(models.TextChoices):
        INFO = 'info', _("Information")
        MINEUR = 'mineur', _("Mineur")
        MAJEUR = 'majeur', _("Majeur")
        CRITIQUE = 'critique', _("Critique")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(
        'exams.Exam',
        on_delete=models.CASCADE,
        related_name='annotation_templates',
        verbose_name=_("Examen")
    )
    document_set = models.ForeignKey(
        'exams.ExamDocumentSet',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='annotation_templates',
        verbose_name=_("Lot documentaire source"),
        help_text=_("Version des documents ayant servi à générer ce template")
    )
    exercise_number = models.PositiveIntegerField(
        verbose_name=_("Numéro d'exercice")
    )
    question_number = models.CharField(
        max_length=20,
        verbose_name=_("Numéro de question"),
        help_text=_("Ex: '1', '3b', 'A.1'")
    )
    sub_question = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Sous-question"),
        help_text=_("Ex: 'a', 'ii', etc.")
    )
    criterion_type = models.CharField(
        max_length=30,
        choices=CriterionType.choices,
        verbose_name=_("Type de critère")
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.INFO,
        verbose_name=_("Sévérité")
    )
    text = models.TextField(
        verbose_name=_("Texte de l'annotation")
    )
    linked_bareme_reference = models.TextField(
        blank=True,
        verbose_name=_("Référence barème"),
        help_text=_("Extrait du barème lié à cette annotation")
    )
    linked_corrige_reference = models.TextField(
        blank=True,
        verbose_name=_("Référence corrigé"),
        help_text=_("Extrait du corrigé lié à cette annotation")
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Tags"),
        help_text=_("Tags pour filtrage et recherche")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Actif")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Date de modification"))

    class Meta:
        verbose_name = _("Template d'annotation")
        verbose_name_plural = _("Templates d'annotation")
        ordering = ['exercise_number', 'question_number', 'criterion_type']
        indexes = [
            models.Index(fields=['exam', 'exercise_number', 'question_number']),
            models.Index(fields=['exam', 'criterion_type']),
        ]

    def __str__(self):
        return f"Ex{self.exercise_number} Q{self.question_number} [{self.get_criterion_type_display()}] - {self.text[:50]}"


class UserAnnotation(models.Model):
    """
    Mémoire personnelle du correcteur.
    Annotations créées manuellement, persistantes, auto-alimentées,
    avec compteur d'usage et contexte exercice/question.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='personal_annotations',
        verbose_name=_("Correcteur")
    )
    text = models.TextField(
        verbose_name=_("Texte de l'annotation")
    )
    exercise_context = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Contexte exercice"),
        help_text=_("Numéro d'exercice associé (optionnel)")
    )
    question_context = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Contexte question"),
        help_text=_("Label de question associé (optionnel)")
    )
    usage_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Nombre d'utilisations")
    )
    last_used = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Dernière utilisation")
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Tags")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Actif")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Date de modification"))

    class Meta:
        verbose_name = _("Annotation personnelle")
        verbose_name_plural = _("Annotations personnelles")
        ordering = ['-usage_count', '-last_used']
        indexes = [
            models.Index(fields=['user', '-usage_count']),
            models.Index(fields=['user', 'exercise_context']),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.text[:50]} (×{self.usage_count})"
