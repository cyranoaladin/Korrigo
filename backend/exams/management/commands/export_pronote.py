from django.core.management.base import BaseCommand
from exams.models import Exam, Copy
from grading.services import GradingService
import csv
import sys

class Command(BaseCommand):
    help = 'Export exam grades to Pronote CSV format'

    def add_arguments(self, parser):
        parser.add_argument('exam_id', type=str, help='UUID of the exam')
        parser.add_argument('--scale', type=float, default=20.0, help='Target scale (default 20)')
        parser.add_argument('--max-score', type=float, default=20.0, help='Max score of the exam (to scale from)')

    def handle(self, *args, **options):
        exam_id = options['exam_id']
        target_scale = options['scale']
        exam_max_score = options['max_score']

        try:
            exam = Exam.objects.get(id=exam_id)
        except Exam.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Exam {exam_id} not found"))
            return

        copies = Copy.objects.filter(exam=exam, status=Copy.Status.GRADED)
        
        # Pronote Format: EMAIL;MATIERE;NOTE;COEFF;COMMENTAIRE
        
        writer = csv.writer(sys.stdout, delimiter=';')
        writer.writerow(['EMAIL', 'MATIERE', 'NOTE', 'COEFF', 'COMMENTAIRE'])

        count = 0
        for copy in copies:
            if not copy.student:
                self.stderr.write(self.style.WARNING(f"Skipping Copy {copy.anonymous_id}: No Student identified"))
                continue
            
            # ZF-AUD-10 FIX: Use GradingService.compute_score() instead of non-existent scores relation
            raw_total = GradingService.compute_score(copy)
            
            # Simple scaling logic
            # If exam was /40 and we want /20 -> raw * (20/40)
            if exam_max_score > 0:
                final_note = (raw_total / exam_max_score) * target_scale
            else:
                final_note = raw_total
                
            final_note_str = f"{final_note:.2f}".replace('.', ',')  # French format uses comma
            
            writer.writerow([
                copy.student.email,
                exam.name,
                final_note_str,
                "1",  # Default Coeff
                ""    # Default Comment
            ])
            count += 1

        self.stderr.write(self.style.SUCCESS(f"Exported {count} grades for Pronote."))
