from django.core.management.base import BaseCommand
from students.models import Student
import csv
import os
from datetime import datetime, date
from django.db import transaction


class Command(BaseCommand):
    help = 'Import student birth dates from CSV file (Format: INE,DATE_NAISSANCE)'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without committing to database',
        )
        parser.add_argument(
            '--delimiter',
            type=str,
            default=',',
            help='CSV delimiter (default: comma)',
        )

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        dry_run = options['dry_run']
        delimiter = options['delimiter']

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {csv_file_path}'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY-RUN MODE: No changes will be committed'))

        self.stdout.write(f'Processing {csv_file_path}...')

        stats = {
            'total': 0,
            'updated': 0,
            'skipped': 0,
            'errors': [],
        }

        try:
            with open(csv_file_path, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                
                if not reader.fieldnames:
                    self.stdout.write(self.style.ERROR('No headers found in CSV'))
                    return
                
                fieldnames = [fn.replace('\ufeff', '') if fn else fn for fn in reader.fieldnames]
                normalized_headers = {fn.strip().upper(): fn for fn in fieldnames}
                
                if 'INE' not in normalized_headers:
                    self.stdout.write(self.style.ERROR('Required column "INE" not found in CSV'))
                    return
                
                if 'DATE_NAISSANCE' not in normalized_headers:
                    self.stdout.write(self.style.ERROR('Required column "DATE_NAISSANCE" not found in CSV'))
                    return
                
                ine_col = normalized_headers['INE']
                birth_date_col = normalized_headers['DATE_NAISSANCE']
                
                for row_num, row in enumerate(reader, start=2):
                    stats['total'] += 1
                    
                    ine = (row.get(ine_col) or '').strip()
                    birth_date_str = (row.get(birth_date_col) or '').strip()
                    
                    if not ine:
                        stats['skipped'] += 1
                        stats['errors'].append(f'Row {row_num}: Missing INE')
                        continue
                    
                    if not birth_date_str:
                        stats['skipped'] += 1
                        stats['errors'].append(f'Row {row_num}: Missing DATE_NAISSANCE for INE {ine}')
                        continue
                    
                    try:
                        birth_date_obj = self._parse_birth_date(birth_date_str)
                    except ValueError as e:
                        stats['skipped'] += 1
                        stats['errors'].append(f'Row {row_num}: Invalid date format for INE {ine}: {e}')
                        continue
                    
                    min_birth_date = date(1990, 1, 1)
                    max_birth_date = date(date.today().year - 10, date.today().month, date.today().day)
                    
                    if birth_date_obj < min_birth_date or birth_date_obj > max_birth_date:
                        stats['skipped'] += 1
                        stats['errors'].append(
                            f'Row {row_num}: Birth date {birth_date_str} out of valid range '
                            f'(1990-01-01 to {max_birth_date}) for INE {ine}'
                        )
                        continue
                    
                    try:
                        student = Student.objects.filter(ine__iexact=ine).first()
                        
                        if not student:
                            stats['skipped'] += 1
                            stats['errors'].append(f'Row {row_num}: Student not found for INE {ine}')
                            continue
                        
                        if dry_run:
                            if student.birth_date:
                                self.stdout.write(
                                    f'  [DRY-RUN] Would update: {ine} ({student.first_name} {student.last_name}) '
                                    f'- Current: {student.birth_date}, New: {birth_date_obj}'
                                )
                            else:
                                self.stdout.write(
                                    f'  [DRY-RUN] Would set: {ine} ({student.first_name} {student.last_name}) '
                                    f'- Birth date: {birth_date_obj}'
                                )
                            stats['updated'] += 1
                        else:
                            with transaction.atomic():
                                student.birth_date = birth_date_obj
                                student.save(update_fields=['birth_date'])
                            stats['updated'] += 1
                            
                    except Exception as e:
                        stats['skipped'] += 1
                        stats['errors'].append(f'Row {row_num}: Database error for INE {ine}: {str(e)}')
                        continue
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Critical error reading CSV: {str(e)}'))
            return
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'Processing Complete'))
        self.stdout.write(f'Total rows processed: {stats["total"]}')
        self.stdout.write(self.style.SUCCESS(f'Successfully updated: {stats["updated"]}'))
        
        if stats['skipped'] > 0:
            self.stdout.write(self.style.WARNING(f'Skipped/Errors: {stats["skipped"]}'))
        
        if stats['errors']:
            self.stdout.write(self.style.WARNING('\nError Details:'))
            for error in stats['errors'][:20]:
                self.stdout.write(self.style.WARNING(f'  - {error}'))
            
            if len(stats['errors']) > 20:
                self.stdout.write(self.style.WARNING(f'  ... and {len(stats["errors"]) - 20} more errors'))
        
        if dry_run:
            self.stdout.write('\n' + self.style.WARNING('DRY-RUN MODE: No changes were committed to the database'))
        else:
            students_without_birth_date = Student.objects.filter(birth_date__isnull=True).count()
            if students_without_birth_date > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'\nWARNING: {students_without_birth_date} students still have no birth_date'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('\n✓ All students now have birth_date populated')
                )

    def _parse_birth_date(self, date_str):
        date_formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%d-%m-%Y',
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        raise ValueError(f'Date "{date_str}" does not match any expected format (YYYY-MM-DD, DD/MM/YYYY, etc.)')
