from django.core.management.base import BaseCommand
from students.models import Student
import csv
import os

class Command(BaseCommand):
    help = 'Imports students from a CSV file (Format: INE;NOM;PRENOM;CLASSE;EMAIL)'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {csv_file_path}'))
            return

        self.stdout.write(f'Importing students from {csv_file_path}...')

        success_count = 0
        error_count = 0

        try:
            with open(csv_file_path, 'r', encoding='utf-8') as f:
                # Detect delimiter if needed, or assume ';' based on spec
                reader = csv.DictReader(f, delimiter=';')
                
                # Check for BOM just in case
                if reader.fieldnames and reader.fieldnames[0].startswith('\ufeff'):
                     reader.fieldnames[0] = reader.fieldnames[0].replace('\ufeff', '')
                
                # Expected Columns: INE, NOM, PRENOM, CLASSE, EMAIL
                # Allow case-insensitive matching or standard names
                
                for row_idx, row in enumerate(reader, start=1):
                    # Normalized keys
                    row_clean = {k.strip().upper(): v.strip() for k, v in row.items() if k}
                    
                    ine = row_clean.get('INE')
                    last_name = row_clean.get('NOM')
                    first_name = row_clean.get('PRENOM')
                    class_name = row_clean.get('CLASSE')
                    email = row_clean.get('EMAIL', '')

                    if not ine or not last_name or not first_name:
                        self.stdout.write(self.style.WARNING(f'Skipping Row {row_idx}: Missing required fields (INE/NOM/PRENOM) - Data: {row}'))
                        error_count += 1
                        continue

                    try:
                        student, created = Student.objects.update_or_create(
                            ine=ine,
                            defaults={
                                'first_name': first_name,
                                'last_name': last_name,
                                'class_name': class_name,
                                'email': email
                            }
                        )
                        action = "Created" if created else "Updated"
                        # self.stdout.write(f'{action}: {student}') # Verbose
                        success_count += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error Row {row_idx}: {e}'))
                        error_count += 1

            self.stdout.write(self.style.SUCCESS(f'Import Complete. Success: {success_count}, Errors: {error_count}'))

        except Exception as e:
             self.stdout.write(self.style.ERROR(f'Failed to read CSV: {e}'))
