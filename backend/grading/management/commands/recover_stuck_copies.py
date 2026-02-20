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

        # Recovery 1: Orphaned STAGING copies (failed PDF import)
        staging_cutoff = timezone.now() - timedelta(minutes=staging_threshold)
        stuck_staging = Copy.objects.filter(
            status=Copy.Status.STAGING,
            created_at__lt=staging_cutoff
        ).select_related('exam')

        staging_count = stuck_staging.count()
        if staging_count > 0:
            self.stdout.write(f'\nFound {staging_count} stuck STAGING copies (older than {staging_threshold} min)')
            
            for copy in stuck_staging:
                self.stdout.write(f'  - Copy {copy.id} (exam: {copy.exam.title}, created: {copy.created_at})')
                
                if not dry_run:
                    with transaction.atomic():
                        # Check if copy has any pages/booklets
                        has_data = copy.booklets.exists()
                        
                        if not has_data:
                            # No data - likely failed import, safe to delete
                            if copy.pdf_source:
                                try:
                                    copy.pdf_source.delete(save=False)
                                except Exception as e:
                                    logger.warning(f'Failed to delete pdf_source for copy {copy.id}: {e}')
                            
                            copy.delete()
                            self.stdout.write(self.style.SUCCESS(f'    Deleted orphaned copy {copy.id}'))
                        else:
                            # Has some data - move to READY for manual review
                            copy.status = Copy.Status.READY
                            copy.save()
                            self.stdout.write(self.style.WARNING(f'    Moved copy {copy.id} to READY (has data)'))
                        
                        total_recovered += 1

        if total_recovered == 0:
            self.stdout.write(self.style.SUCCESS('\nNo stuck copies found. System healthy.'))
        else:
            if dry_run:
                self.stdout.write(self.style.WARNING(f'\nWould recover {total_recovered} copies (dry run)'))
            else:
                self.stdout.write(self.style.SUCCESS(f'\nRecovered {total_recovered} copies'))
                logger.info(f'Recovered {total_recovered} stuck copies')
