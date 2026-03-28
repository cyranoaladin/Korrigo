from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils import timezone


def auto_dispatch_copies(sender, instance, action, pk_set, **kwargs):
    """When correctors are added/changed on an exam, auto-dispatch unassigned copies."""
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    from exams.models import Copy
    copies = Copy.objects.filter(
        exam=instance,
        status=Copy.Status.READY,
        assigned_corrector__isnull=True
    )
    correctors = list(instance.correctors.all())
    if not correctors:
        return
    for i, copy in enumerate(copies):
        copy.assigned_corrector = correctors[i % len(correctors)]
        copy.assigned_at = timezone.now()
        copy.save(update_fields=['assigned_corrector', 'assigned_at'])
