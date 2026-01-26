from django.core.management.base import BaseCommand
from students.models import Student
from students.services.csv_import import import_students_from_csv, CsvReadError, CsvSchemaError
import os

class Command(BaseCommand):
    help = 'Imports students from a CSV file (Format: INE,NOM,PRENOM,CLASSE,EMAIL)'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {csv_file_path}'))
            return

        self.stdout.write(f'Importing students from {csv_file_path} (Delimiter: comma)...')

        try:
            # P0 Fix: Use robust service with comma delimiter
            result = import_students_from_csv(csv_file_path, Student, delimiter=",")
            
            self.stdout.write(self.style.SUCCESS(
                f"Import Complete. Created: {result['created']}, Updated: {result['updated']}, Errors: {len(result['errors'])}"
            ))
            
            if result['errors']:
                self.stdout.write(self.style.WARNING("Details of errors:"))
                for err in result['errors']:
                     self.stdout.write(self.style.WARNING(f" - {err}"))

        except (CsvReadError, CsvSchemaError) as e:
             self.stdout.write(self.style.ERROR(str(e)))
        except Exception as e:
             self.stdout.write(self.style.ERROR(f"Critical Error: {e}"))
