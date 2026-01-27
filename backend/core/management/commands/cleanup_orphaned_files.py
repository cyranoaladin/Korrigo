"""
P0-DI-006 FIX: Management command to cleanup orphaned PDF files.

Orphaned files occur when:
1. PDF generation succeeds but database save fails
2. Transaction rollback after file write
3. Duplicate generation due to race conditions
4. Process crashes during file operations

Usage:
    python manage.py cleanup_orphaned_files --dry-run  # Preview only
    python manage.py cleanup_orphaned_files            # Actually delete
    python manage.py cleanup_orphaned_files --older-than-days 7  # Only old files
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from exams.models import Copy
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cleanup orphaned PDF files that are not referenced in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview orphaned files without deleting them',
        )
        parser.add_argument(
            '--older-than-days',
            type=int,
            default=1,
            help='Only delete files older than N days (default: 1)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        older_than_days = options['older_than_days']
        
        self.stdout.write(self.style.WARNING(
            f"Starting orphaned file cleanup (dry_run={dry_run}, older_than_days={older_than_days})"
        ))
        
        # Directories to check
        directories_to_check = [
            ('Final PDFs', os.path.join(settings.MEDIA_ROOT, 'copies/final/')),
            ('Source PDFs', os.path.join(settings.MEDIA_ROOT, 'copies/')),
        ]
        
        total_orphaned = 0
        total_size = 0
        total_deleted = 0
        
        for dir_name, dir_path in directories_to_check:
            if not os.path.exists(dir_path):
                self.stdout.write(self.style.WARNING(f"  Directory {dir_path} does not exist, skipping"))
                continue
            
            self.stdout.write(self.style.NOTICE(f"\nChecking {dir_name}: {dir_path}"))
            
            # Get all files in directory
            try:
                all_files = set()
                for root, dirs, files in os.walk(dir_path):
                    for filename in files:
                        if filename.endswith('.pdf'):
                            all_files.add(os.path.join(root, filename))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error listing files: {e}"))
                continue
            
            # Get all referenced PDFs from database
            if 'final' in dir_path:
                referenced_paths = set(
                    Copy.objects.exclude(final_pdf='')
                    .values_list('final_pdf', flat=True)
                )
            else:
                referenced_paths = set(
                    Copy.objects.exclude(pdf_source='')
                    .values_list('pdf_source', flat=True)
                )
            
            # Convert relative paths to absolute
            referenced_absolute = set()
            for rel_path in referenced_paths:
                abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
                referenced_absolute.add(abs_path)
            
            # Find orphaned files
            orphaned = all_files - referenced_absolute
            
            # Filter by age
            cutoff_time = datetime.now() - timedelta(days=older_than_days)
            orphaned_old = []
            for filepath in orphaned:
                try:
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_mtime < cutoff_time:
                        orphaned_old.append(filepath)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Error checking file {filepath}: {e}"))
            
            # Process orphaned files
            for filepath in orphaned_old:
                try:
                    size = os.path.getsize(filepath)
                    total_orphaned += 1
                    total_size += size
                    
                    if dry_run:
                        self.stdout.write(f"  [DRY-RUN] Would delete: {filepath} ({size / 1024 / 1024:.2f} MB)")
                    else:
                        os.unlink(filepath)
                        total_deleted += 1
                        self.stdout.write(f"  Deleted: {filepath} ({size / 1024 / 1024:.2f} MB)")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Error processing {filepath}: {e}"))
        
        # Summary
        self.stdout.write(self.style.SUCCESS(
            f"\n{'[DRY-RUN] ' if dry_run else ''}Cleanup complete:"
        ))
        self.stdout.write(f"  - Orphaned files found: {total_orphaned}")
        self.stdout.write(f"  - Total size: {total_size / 1024 / 1024:.2f} MB")
        if not dry_run:
            self.stdout.write(f"  - Files deleted: {total_deleted}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\nThis was a dry-run. Run without --dry-run to actually delete files."
            ))
