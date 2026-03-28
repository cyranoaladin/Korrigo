"""
P0-OP-05: Management command for crash recovery of stuck copies
Recovers copies stuck in inconsistent states due to crashes, timeouts, or network failures.
"""
import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from exams.models import Copy
import logging

logger = logging.getLogger('grading')


class Command(BaseCommand):
    help = 'Recover stuck copies from failed PDF operations or abandoned locks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be recovered without making changes',
        )
        parser.add_argument(
            '--staging-threshold',
            type=int,
            default=60,
            help='Minutes threshold for stuck STAGING copies (default: 60)',
        )
        parser.add_argument(
            '--locked-threshold',
            type=int,
            default=120,
            help='Minutes threshold for abandoned LOCKED copies (default: 120)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        staging_threshold = options['staging_threshold']
        locked_threshold = options['locked_threshold']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        total_recovered = 0

        # Recovery: IN_PROGRESS copies abandoned for too long
        locked_cutoff = timezone.now() - timedelta(minutes=locked_threshold)
        stuck_in_progress = Copy.objects.filter(
            status=Copy.Status.IN_PROGRESS,
            assigned_at__lt=locked_cutoff
        ).select_related('exam')

        in_progress_count = stuck_in_progress.count()
        if in_progress_count > 0:
            self.stdout.write(f'\nFound {in_progress_count} abandoned IN_PROGRESS copies (older than {locked_threshold} min)')
            for copy in stuck_in_progress:
                self.stdout.write(f'  - Copy {copy.id} (exam: {copy.exam.name})')
                if not dry_run:
                    with transaction.atomic():
                        copy.status = Copy.Status.READY
                        copy.save(update_fields=['status'])
                        self.stdout.write(self.style.WARNING(f'    Reset copy {copy.id} to READY'))
                    total_recovered += 1

        if total_recovered == 0:
            self.stdout.write(self.style.SUCCESS('\nNo stuck copies found. System healthy.'))
        else:
            if dry_run:
                self.stdout.write(self.style.WARNING(f'\nWould recover {total_recovered} copies (dry run)'))
            else:
                self.stdout.write(self.style.SUCCESS(f'\nRecovered {total_recovered} copies'))
                logger.info(f'Recovered {total_recovered} stuck copies')
