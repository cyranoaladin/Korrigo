"""
Management command to clean up duplicate copies created by the MergeBookletsView bug.

The bug: When merging booklets, STAGING copies (created during upload) were not deleted,
resulting in duplicate copies for the same booklets.

This command identifies and removes orphan STAGING copies that have no booklets
or whose booklets are already assigned to READY/LOCKED/GRADED copies.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from exams.models import Exam, Copy, Booklet


class Command(BaseCommand):
    help = 'Clean up duplicate STAGING copies that were not properly deleted during merge'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exam-id',
            type=str,
            help='Specific exam ID to clean up (optional, defaults to all exams)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        exam_id = options.get('exam_id')
        dry_run = options.get('dry_run', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))

        if exam_id:
            exams = Exam.objects.filter(id=exam_id)
            if not exams.exists():
                self.stdout.write(self.style.ERROR(f'Exam {exam_id} not found'))
                return
        else:
            exams = Exam.objects.all()

        total_deleted = 0
        total_orphan_staging = 0

        for exam in exams:
            self.stdout.write(f'\n--- Exam: {exam.name} (ID: {exam.id}) ---')
            
            copies = Copy.objects.filter(exam=exam)
            staging_copies = copies.filter(status=Copy.Status.STAGING)
            ready_copies = copies.exclude(status=Copy.Status.STAGING)
            
            self.stdout.write(f'  Total copies: {copies.count()}')
            self.stdout.write(f'  STAGING copies: {staging_copies.count()}')
            self.stdout.write(f'  Non-STAGING copies: {ready_copies.count()}')
            
            # Find STAGING copies whose booklets are already in non-STAGING copies
            orphan_staging_ids = []
            
            for staging_copy in staging_copies:
                booklets = staging_copy.booklets.all()
                
                if not booklets.exists():
                    # STAGING copy with no booklets - orphan
                    orphan_staging_ids.append(staging_copy.id)
                    self.stdout.write(f'    Orphan (no booklets): Copy {staging_copy.id}')
                    continue
                
                # Check if all booklets are also in a non-STAGING copy
                all_booklets_in_ready = True
                for booklet in booklets:
                    non_staging_copies = booklet.assigned_copy.exclude(status=Copy.Status.STAGING)
                    if not non_staging_copies.exists():
                        all_booklets_in_ready = False
                        break
                
                if all_booklets_in_ready:
                    orphan_staging_ids.append(staging_copy.id)
                    booklet_pages = ', '.join([f'{b.start_page}-{b.end_page}' for b in booklets])
                    self.stdout.write(f'    Duplicate STAGING: Copy {staging_copy.id} (booklets: {booklet_pages})')
            
            if orphan_staging_ids:
                total_orphan_staging += len(orphan_staging_ids)
                
                if not dry_run:
                    with transaction.atomic():
                        deleted_count = Copy.objects.filter(id__in=orphan_staging_ids).delete()[0]
                        total_deleted += deleted_count
                        self.stdout.write(self.style.SUCCESS(f'  Deleted {deleted_count} orphan STAGING copies'))
                else:
                    self.stdout.write(self.style.WARNING(f'  Would delete {len(orphan_staging_ids)} orphan STAGING copies'))
            else:
                self.stdout.write(self.style.SUCCESS('  No orphan STAGING copies found'))

        self.stdout.write('\n' + '=' * 50)
        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN: Would delete {total_orphan_staging} copies total'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Cleanup complete: Deleted {total_deleted} orphan STAGING copies'))
