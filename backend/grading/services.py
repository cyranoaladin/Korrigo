"""
Services métier pour annotation et grading.
Respect strict de la machine d'états ADR-003.
"""
from django.db import transaction
from django.utils import timezone
from grading.models import Annotation, GradingEvent
from exams.models import Copy
import logging

logger = logging.getLogger(__name__)


class AnnotationService:
    """
    Service pour la gestion des annotations.
    Machine d'état (ADR-003) :
    - STAGING : aucune annotation autorisée
    - READY : création/modification/suppression autorisées
    - LOCKED : lecture seule (aucune modification)
    - GRADED : lecture seule (aucune modification)
    """

    @staticmethod
    def validate_coordinates(x, y, w, h):
        """
        Valide que les coordonnées sont dans [0, 1] (ADR-002).
        """
        if not (0 <= x <= 1 and 0 <= y <= 1 and 0 <= w <= 1 and 0 <= h <= 1):
            raise ValueError("Coordinates must be in [0, 1]")

    @staticmethod
    def validate_page_index(page_index):
        """
        Valide que page_index est >= 0.
        """
        if page_index < 0:
            raise ValueError("page_index must be >= 0")

    @staticmethod
    @transaction.atomic
    def add_annotation(copy: Copy, payload: dict, user):
        """
        Ajoute une annotation à une copie.
        RÈGLE STRICTE : uniquement si copy.status == READY.
        """
        # Vérification machine d'état
        if copy.status != Copy.Status.READY:
            raise ValueError(
                f"Cannot add annotation to copy in status {copy.status}. "
                f"Only READY copies can be annotated."
            )

        # Validation coordonnées ADR-002
        AnnotationService.validate_coordinates(
            payload['x'], payload['y'], payload['w'], payload['h']
        )

        # Validation page_index
        AnnotationService.validate_page_index(payload['page_index'])

        # Création annotation
        annotation = Annotation.objects.create(
            copy=copy,
            page_index=payload['page_index'],
            x=payload['x'],
            y=payload['y'],
            w=payload['w'],
            h=payload['h'],
            content=payload.get('content', ''),
            type=payload.get('type', Annotation.Type.COMMENT),
            score_delta=payload.get('score_delta'),
            created_by=user
        )

        logger.info(
            f"Annotation {annotation.id} added to copy {copy.id} "
            f"(page {payload['page_index']}) by {user.username}"
        )
        return annotation

    @staticmethod
    @transaction.atomic
    def update_annotation(annotation: Annotation, payload: dict, user):
        """
        Modifie une annotation existante.
        RÈGLE STRICTE : uniquement si copy.status == READY.
        LOCKED et GRADED sont en lecture seule.
        """
        # Vérification machine d'état
        if annotation.copy.status != Copy.Status.READY:
            raise ValueError(
                f"Cannot update annotation of copy in status {annotation.copy.status}. "
                f"Only READY copies can have their annotations modified."
            )

        # Mise à jour champs autorisés
        for field in ['content', 'score_delta', 'type']:
            if field in payload:
                setattr(annotation, field, payload[field])

        annotation.save()
        logger.info(
            f"Annotation {annotation.id} updated by {user.username}"
        )
        return annotation

    @staticmethod
    @transaction.atomic
    def delete_annotation(annotation: Annotation, user):
        """
        Supprime une annotation.
        RÈGLE STRICTE : uniquement si copy.status == READY.
        LOCKED et GRADED sont en lecture seule.
        """
        # Vérification machine d'état
        if annotation.copy.status != Copy.Status.READY:
            raise ValueError(
                f"Cannot delete annotation of copy in status {annotation.copy.status}. "
                f"Only READY copies can have their annotations deleted."
            )

        annotation_id = annotation.id
        copy_id = annotation.copy.id
        annotation.delete()
        logger.info(
            f"Annotation {annotation_id} deleted from copy {copy_id} by {user.username}"
        )

    @staticmethod
    def list_annotations(copy: Copy):
        """
        Liste toutes les annotations d'une copie.
        Lecture autorisée quel que soit le statut.
        """
        return copy.annotations.select_related('created_by').order_by('page_index', 'created_at')


class GradingService:
    """
    Service pour la gestion du workflow de correction.
    Machine d'état stricte (ADR-003) :
    STAGING → READY → LOCKED → GRADED
    """

    @staticmethod
    def compute_score(copy: Copy) -> int:
        """
        Calcule le score total d'une copie (somme des score_delta).
        Les annotations sans score_delta (None) sont ignorées.
        """
        total = 0
        for annotation in copy.annotations.all():
            if annotation.score_delta is not None:
                total += annotation.score_delta
        return total

    @staticmethod
    @transaction.atomic
    def validate_copy(copy: Copy, user):
        """
        Transition STAGING → READY.
        Marque une copie comme prête à être corrigée.
        """
        if copy.status != Copy.Status.STAGING:
            raise ValueError(
                f"Cannot validate copy in status {copy.status}. "
                f"Only STAGING copies can be validated."
            )

        copy.status = Copy.Status.READY
        copy.validated_at = timezone.now()
        copy.save()

        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.VALIDATE,
            actor=user,
            metadata={'previous_status': Copy.Status.STAGING}
        )

        logger.info(f"Copy {copy.id} validated (STAGING → READY) by {user.username}")
        return copy

    @staticmethod
    @transaction.atomic
    def lock_copy(copy: Copy, user):
        """
        Transition READY → LOCKED.
        Verrouille une copie pour correction.
        """
        if copy.status != Copy.Status.READY:
            raise ValueError(
                f"Cannot lock copy in status {copy.status}. "
                f"Only READY copies can be locked."
            )

        copy.status = Copy.Status.LOCKED
        copy.locked_at = timezone.now()
        copy.locked_by = user
        copy.save()

        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.LOCK,
            actor=user,
            metadata={'locked_by': user.username}
        )

        logger.info(f"Copy {copy.id} locked (READY → LOCKED) by {user.username}")
        return copy

    @staticmethod
    @transaction.atomic
    def unlock_copy(copy: Copy, user):
        """
        Transition LOCKED → READY.
        Déverrouille une copie (en cas d'erreur ou abandon de correction).
        """
        if copy.status != Copy.Status.LOCKED:
            raise ValueError(
                f"Cannot unlock copy in status {copy.status}. "
                f"Only LOCKED copies can be unlocked."
            )

        previous_locker = copy.locked_by.username if copy.locked_by else "unknown"

        copy.status = Copy.Status.READY
        copy.locked_at = None
        copy.locked_by = None
        copy.save()

        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.UNLOCK,
            actor=user,
            metadata={
                'unlocked_by': user.username,
                'previous_locker': previous_locker,
                'reason': 'Manual unlock'
            }
        )

        logger.info(f"Copy {copy.id} unlocked (LOCKED → READY) by {user.username}")
        return copy

    @staticmethod
    @transaction.atomic
    def finalize_copy(copy: Copy, user):
        """
        Transition LOCKED → GRADED.
        Finalise la correction d'une copie :
        - Génère le PDF final avec annotations (via PDFFlattener)
        - Calcule et enregistre le score final
        - Marque la copie comme GRADED (immutable)
        """
        if copy.status != Copy.Status.LOCKED:
            raise ValueError(
                f"Cannot finalize copy in status {copy.status}. "
                f"Only LOCKED copies can be finalized."
            )

        # Calcul score final avant génération PDF
        final_score = GradingService.compute_score(copy)

        # Génération PDF avec annotations
        from processing.services.pdf_flattener import PDFFlattener
        flattener = PDFFlattener()
        try:
            flattener.flatten_copy(copy)
        except Exception as e:
            logger.error(f"PDFFlattener error for copy {copy.id}: {e}", exc_info=True)
            raise ValueError(f"Failed to generate final PDF: {str(e)}")

        # Mise à jour statut
        copy.status = Copy.Status.GRADED
        copy.graded_at = timezone.now()
        copy.save()

        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.FINALIZE,
            actor=user,
            metadata={
                'final_score': final_score,
                'annotation_count': copy.annotations.count(),
                'graded_by': user.username
            }
        )

        logger.info(
            f"Copy {copy.id} finalized (LOCKED → GRADED) by {user.username}, "
            f"final score: {final_score}"
        )
        return copy
