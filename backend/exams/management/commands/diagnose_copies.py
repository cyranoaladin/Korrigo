"""
Management command to diagnose and fix copy-related issues.

This command provides a comprehensive analysis of the copy workflow:
1. Identifies orphan STAGING copies (should have been deleted during merge)
2. Identifies copies without booklets
3. Identifies booklets assigned to multiple copies
4. Identifies READY copies that should be available for dispatch
5. Optionally fixes issues

Usage:
    python manage.py diagnose_copies --exam-id <uuid>
    python manage.py diagnose_copies --fix
    python manage.py diagnose_copies --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from exams.models import Exam, Copy, Booklet


class Command(BaseCommand):
    help = 'Diagnose and fix copy-related issues in the workflow'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exam-id',
            type=str,
            help='Specific exam ID to diagnose (optional, defaults to all exams)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without actually fixing',
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Actually fix the issues found',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information',
        )

    def handle(self, *args, **options):
        exam_id = options.get('exam_id')
        dry_run = options.get('dry_run', False)
        fix = options.get('fix', False)
        verbose = options.get('verbose', False)

        if dry_run and fix:
            self.stdout.write(self.style.ERROR('Cannot use --dry-run and --fix together'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))

        if exam_id:
            exams = Exam.objects.filter(id=exam_id)
            if not exams.exists():
                self.stdout.write(self.style.ERROR(f'Exam {exam_id} not found'))
                return
        else:
            exams = Exam.objects.all()

        total_issues = 0
        total_fixed = 0

        for exam in exams:
            self.stdout.write(f'\n{"="*60}')
            self.stdout.write(f'EXAM: {exam.name}')
            self.stdout.write(f'ID: {exam.id}')
            self.stdout.write(f'{"="*60}')

            issues, fixed = self._diagnose_exam(exam, fix, dry_run, verbose)
            total_issues += issues
            total_fixed += fixed

        # Global summary
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write('GLOBAL SUMMARY')
        self.stdout.write(f'{"="*60}')
        self.stdout.write(f'Total exams analyzed: {exams.count()}')
        self.stdout.write(f'Total issues found: {total_issues}')
        
        if fix:
            self.stdout.write(self.style.SUCCESS(f'Total issues fixed: {total_fixed}'))
        elif dry_run:
            self.stdout.write(self.style.WARNING(f'Issues that would be fixed: {total_fixed}'))

    def _diagnose_exam(self, exam, fix, dry_run, verbose):
        """Diagnose a single exam and optionally fix issues."""
        issues = 0
        fixed = 0

        # Get all copies and booklets for this exam
        copies = Copy.objects.filter(exam=exam).prefetch_related('booklets')
        booklets = Booklet.objects.filter(exam=exam)

        # Basic stats
        self.stdout.write(f'\n--- Statistics ---')
        self.stdout.write(f'Total booklets: {booklets.count()}')
        self.stdout.write(f'Total copies: {copies.count()}')
        
        # Copy status breakdown
        status_counts = {}
        for status_choice in Copy.Status.choices:
            count = copies.filter(status=status_choice[0]).count()
            status_counts[status_choice[0]] = count
            self.stdout.write(f'  - {status_choice[1]}: {count}')

        # Identification stats
        identified = copies.filter(is_identified=True).count()
        unidentified = copies.filter(is_identified=False).count()
        self.stdout.write(f'Identified copies: {identified}')
        self.stdout.write(f'Unidentified copies: {unidentified}')

        # Dispatch stats
        dispatched = copies.filter(assigned_corrector__isnull=False).count()
        not_dispatched = copies.filter(assigned_corrector__isnull=True).count()
        self.stdout.write(f'Dispatched copies: {dispatched}')
        self.stdout.write(f'Not dispatched: {not_dispatched}')

        # Issue 1: STAGING copies that should have been deleted
        self.stdout.write(f'\n--- Issue 1: Orphan STAGING copies ---')
        staging_copies = copies.filter(status=Copy.Status.STAGING)
        orphan_staging = []
        
        for staging_copy in staging_copies:
            copy_booklets = staging_copy.booklets.all()
            
            if not copy_booklets.exists():
                orphan_staging.append(staging_copy)
                if verbose:
                    self.stdout.write(f'  [ORPHAN] Copy {staging_copy.id} has no booklets')
                continue
            
            # Check if booklets are also in a non-STAGING copy
            all_in_ready = True
            for booklet in copy_booklets:
                non_staging = booklet.assigned_copy.exclude(status=Copy.Status.STAGING)
                if not non_staging.exists():
                    all_in_ready = False
                    break
            
            if all_in_ready:
                orphan_staging.append(staging_copy)
                if verbose:
                    pages = ', '.join([f'{b.start_page}-{b.end_page}' for b in copy_booklets])
                    self.stdout.write(f'  [DUPLICATE] Copy {staging_copy.id} (pages: {pages})')

        if orphan_staging:
            issues += len(orphan_staging)
            self.stdout.write(self.style.WARNING(f'Found {len(orphan_staging)} orphan STAGING copies'))
            
            if fix or dry_run:
                if fix:
                    with transaction.atomic():
                        ids = [c.id for c in orphan_staging]
                        deleted = Copy.objects.filter(id__in=ids).delete()[0]
                        fixed += deleted
                        self.stdout.write(self.style.SUCCESS(f'  Deleted {deleted} orphan STAGING copies'))
                else:
                    fixed += len(orphan_staging)
                    self.stdout.write(self.style.WARNING(f'  Would delete {len(orphan_staging)} orphan STAGING copies'))
        else:
            self.stdout.write(self.style.SUCCESS('No orphan STAGING copies found'))

        # Issue 2: Copies without booklets (except STAGING which we just handled)
        self.stdout.write(f'\n--- Issue 2: Copies without booklets ---')
        copies_without_booklets = copies.exclude(status=Copy.Status.STAGING).annotate(
            booklet_count=Count('booklets')
        ).filter(booklet_count=0)
        
        if copies_without_booklets.exists():
            issues += copies_without_booklets.count()
            self.stdout.write(self.style.WARNING(f'Found {copies_without_booklets.count()} copies without booklets'))
            for c in copies_without_booklets:
                self.stdout.write(f'  Copy {c.id} (status: {c.status}, identified: {c.is_identified})')
        else:
            self.stdout.write(self.style.SUCCESS('All copies have booklets'))

        # Issue 3: Booklets assigned to multiple non-STAGING copies
        self.stdout.write(f'\n--- Issue 3: Booklets in multiple copies ---')
        multi_assigned = []
        for booklet in booklets:
            non_staging_copies = booklet.assigned_copy.exclude(status=Copy.Status.STAGING)
            if non_staging_copies.count() > 1:
                multi_assigned.append((booklet, list(non_staging_copies)))
        
        if multi_assigned:
            issues += len(multi_assigned)
            self.stdout.write(self.style.WARNING(f'Found {len(multi_assigned)} booklets in multiple copies'))
            for booklet, assigned_copies in multi_assigned:
                copy_ids = ', '.join([str(c.id)[:8] for c in assigned_copies])
                self.stdout.write(f'  Booklet {booklet.id} (pages {booklet.start_page}-{booklet.end_page}) -> Copies: {copy_ids}')
        else:
            self.stdout.write(self.style.SUCCESS('No booklets assigned to multiple copies'))

        # Issue 4: READY copies available for dispatch
        self.stdout.write(f'\n--- Issue 4: Dispatch readiness ---')
        ready_for_dispatch = copies.filter(
            status=Copy.Status.READY,
            assigned_corrector__isnull=True
        )
        self.stdout.write(f'Copies ready for dispatch: {ready_for_dispatch.count()}')
        
        if ready_for_dispatch.count() == 0 and status_counts.get(Copy.Status.READY, 0) > 0:
            self.stdout.write(self.style.WARNING('All READY copies are already dispatched'))
        
        # Check if there are STAGING copies that should be READY
        staging_with_booklets = staging_copies.annotate(
            booklet_count=Count('booklets')
        ).filter(booklet_count__gt=0)
        
        if staging_with_booklets.exists():
            self.stdout.write(self.style.WARNING(
                f'{staging_with_booklets.count()} STAGING copies have booklets but were not merged/promoted to READY'
            ))
            self.stdout.write('  These copies need to go through the stapling (agrafage) process')

        # Issue 5: Identified vs dispatch status
        self.stdout.write(f'\n--- Issue 5: Identification vs Dispatch ---')
        ready_identified_not_dispatched = copies.filter(
            status=Copy.Status.READY,
            is_identified=True,
            assigned_corrector__isnull=True
        )
        if ready_identified_not_dispatched.exists():
            self.stdout.write(f'READY + Identified + Not dispatched: {ready_identified_not_dispatched.count()}')
            self.stdout.write('  These copies are ready to be dispatched to correctors')
        
        ready_unidentified = copies.filter(
            status=Copy.Status.READY,
            is_identified=False
        )
        if ready_unidentified.exists():
            self.stdout.write(f'READY + Unidentified: {ready_unidentified.count()}')
            self.stdout.write('  These copies need identification in video-coding before dispatch')

        return issues, fixed
