"""
Management command to reset all student passwords to their date of birth (DDMMYYYY).

This ensures a consistent default password for all students.
The login view flags must_change_password=True for DOB passwords,
forcing students to change on first login.

Usage:
  python manage.py reset_student_passwords
  python manage.py reset_student_passwords --dry-run
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from students.models import Student


class Command(BaseCommand):
    help = "Reset all student passwords to their date of birth (DDMMYYYY format)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        students_with_user = Student.objects.filter(
            user__isnull=False,
            date_naissance__isnull=False,
        ).select_related('user')

        total = students_with_user.count()
        self.stdout.write(f"Found {total} students with user accounts and DOB.")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made."))

        reset_count = 0
        already_dob = 0
        no_dob = 0
        errors = []

        for student in students_with_user:
            if not student.date_naissance:
                no_dob += 1
                continue

            dob_pwd = student.date_naissance.strftime('%d%m%Y')
            user = student.user

            # Skip if already set to DOB
            if user.check_password(dob_pwd):
                already_dob += 1
                continue

            if dry_run:
                self.stdout.write(
                    f"  [DRY] Would reset {student.last_name} {student.first_name} "
                    f"({user.username}) -> {dob_pwd}"
                )
                reset_count += 1
                continue

            try:
                user.set_password(dob_pwd)
                user.save(update_fields=['password'])
                reset_count += 1
                self.stdout.write(
                    f"  [RESET] {student.last_name} {student.first_name} "
                    f"({user.username})"
                )
            except Exception as e:
                errors.append(f"{student.last_name} {student.first_name}: {e}")
                self.stdout.write(self.style.ERROR(
                    f"  [ERROR] {user.username}: {e}"
                ))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done: {reset_count} reset, {already_dob} already DOB, "
            f"{no_dob} no DOB, {len(errors)} errors."
        ))

        if errors:
            self.stdout.write(self.style.ERROR("Errors:"))
            for err in errors:
                self.stdout.write(f"  - {err}")
