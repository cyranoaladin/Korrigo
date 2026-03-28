import uuid
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def auto_dispatch_copies(sender, instance, action, pk_set, **kwargs):
    """
    Auto-dispatch unassigned READY copies when the exam's corrector list changes.

    Triggers on post_add / post_remove / post_clear.
    Only dispatches copies with assigned_corrector=NULL — never touches already-assigned copies.
    Uses bulk_update for efficiency (single SQL UPDATE regardless of copy count).
    """
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return

    from exams.models import Copy

    unassigned = list(
        Copy.objects.filter(
            exam=instance,
            status=Copy.Status.READY,
            assigned_corrector__isnull=True,
        ).order_by('anonymous_id')
    )

    if not unassigned:
        return

    correctors = list(instance.correctors.all())
    if not correctors:
        logger.warning(
            "auto_dispatch: exam %s has no correctors, %d copies remain unassigned.",
            instance.name, len(unassigned),
        )
        return

    run_id = uuid.uuid4()
    now = timezone.now()

    for i, copy in enumerate(unassigned):
        copy.assigned_corrector = correctors[i % len(correctors)]
        copy.dispatch_run_id = run_id
        copy.assigned_at = now

    Copy.objects.bulk_update(
        unassigned,
        ['assigned_corrector', 'dispatch_run_id', 'assigned_at'],
    )

    logger.info(
        "auto_dispatch: exam=%s action=%s → %d copies dispatched to %d correctors (run=%s).",
        instance.name, action, len(unassigned), len(correctors), run_id,
    )
