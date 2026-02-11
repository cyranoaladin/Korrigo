"""
Management command to export exam grades to PRONOTE CSV format.

Usage:
    python manage.py export_pronote <exam_id> [options]
    
Examples:
    # Basic export to stdout
    python manage.py export_pronote abc123def456 > export.csv
    
    # Export to file with custom coefficient
    python manage.py export_pronote abc123def456 --output /tmp/export.csv --coefficient 1.5
    
    # Validation only (no export)
    python manage.py export_pronote abc123def456 --validate-only
"""

import uuid as uuid_lib

from django.core.management.base import BaseCommand, CommandError
from exams.models import Exam
from exams.services import PronoteExporter
from exams.services.pronote_export import ValidationError


class Command(BaseCommand):
    help = 'Export exam grades to PRONOTE CSV format'

    def add_arguments(self, parser):
        parser.add_argument(
            'exam_id',
            type=str,
            help='UUID of the exam to export'
        )
        parser.add_argument(
            '--coefficient',
            type=float,
            default=1.0,
            help='Grade coefficient (default: 1.0)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (default: stdout)'
        )
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Only validate export eligibility without generating CSV'
        )

    def handle(self, *args, **options):
        exam_id = options['exam_id']
        coefficient = options['coefficient']
        output_path = options.get('output')
        validate_only = options['validate_only']

        # Validate UUID format
        try:
            uuid_lib.UUID(exam_id)
        except (ValueError, AttributeError):
            raise CommandError(f"Exam with ID '{exam_id}' not found (invalid UUID format)")

        # Get exam
        try:
            exam = Exam.objects.get(id=exam_id)
        except Exam.DoesNotExist:
            raise CommandError(f"Exam with ID '{exam_id}' not found")
        
        self.stdout.write(f"Examen: {exam.name} ({exam.date})")
        
        # Create exporter
        exporter = PronoteExporter(exam, coefficient=coefficient)
        
        # Validate
        self.stdout.write("Validation en cours...")
        validation = exporter.validate_export_eligibility()
        
        # Display validation results
        if validation.errors:
            self.stderr.write(self.style.ERROR("\n❌ Erreurs de validation:"))
            for error in validation.errors:
                self.stderr.write(self.style.ERROR(f"  - {error}"))
            
            raise CommandError("Export impossible: corrigez les erreurs ci-dessus")
        
        if validation.warnings:
            self.stdout.write(self.style.WARNING("\n⚠️  Avertissements:"))
            for warning in validation.warnings:
                self.stdout.write(self.style.WARNING(f"  - {warning}"))
        
        if not validation.errors and not validation.warnings:
            self.stdout.write(self.style.SUCCESS("✅ Validation réussie"))
        
        # If validate-only, stop here
        if validate_only:
            self.stdout.write(self.style.SUCCESS("\nMode validation uniquement: pas d'export généré"))
            return
        
        # Generate CSV
        try:
            csv_content, warnings = exporter.generate_csv()
        except ValidationError as e:
            raise CommandError(f"Erreur de validation: {e}")
        except Exception as e:
            raise CommandError(f"Erreur inattendue: {e}")
        
        # Count exported grades
        export_count = csv_content.count('\n') - 1  # Minus header
        
        # Write to file or stdout
        if output_path:
            # Write to file in binary mode to preserve CRLF line endings
            try:
                with open(output_path, 'wb') as f:
                    f.write(csv_content.encode('utf-8'))
                self.stdout.write(
                    self.style.SUCCESS(f"\n✅ Export réussi: {export_count} notes exportées vers {output_path}")
                )
            except IOError as e:
                raise CommandError(f"Erreur d'écriture du fichier: {e}")
        else:
            # Write CSV to self.stdout so Django test framework can capture it
            self.stdout.write(csv_content)
            # Success message goes to stderr to not interfere with CSV output
            self.stderr.write(
                self.style.SUCCESS(f"Exported {export_count} grades")
            )
