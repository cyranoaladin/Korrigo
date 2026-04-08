"""
RGPD: Anonymize a student's personal data.
Replaces PII with anonymized values while preserving referential integrity.
Usage: python manage.py anonymize_student --email student@school.tn --confirm
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Anonymize a student's personal data (RGPD right to erasure)."

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True, help='Student email to anonymize')
        parser.add_argument('--confirm', action='store_true', help='Required to execute')

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['confirm']:
            raise CommandError('Pass --confirm to execute. This is irreversible.')

        from students.models import Student
        email = options['email'].strip().lower()

        student = Student.objects.filter(email=email).first()
        if not student:
            raise CommandError(f'No student found with email: {email}')

        sid = student.id
        self.stdout.write(f'Anonymizing student #{sid} ({student.first_name} {student.last_name})...')

        # Anonymize PII
        student.first_name = f'ANON-{sid}'
        student.last_name = f'ANON-{sid}'
        student.email = f'anon-{sid}@removed.local'
        import datetime
        student.date_naissance = datetime.date(1900, 1, 1)  # sentinel — field is NOT NULL
        student.save(update_fields=['first_name', 'last_name', 'email', 'date_naissance'])

        # Deactivate linked Django user
        if student.user:
            user = student.user
            user.is_active = False
            user.set_unusable_password()
            user.first_name = f'ANON-{sid}'
            user.last_name = f'ANON-{sid}'
            user.email = f'anon-{sid}@removed.local'
            user.username = f'anon-{sid}'
            user.save()
            self.stdout.write(f'  Deactivated user #{user.id}')

        self.stdout.write(self.style.SUCCESS(f'Student #{sid} anonymized successfully.'))
