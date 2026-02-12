"""
Management command to provision Django User accounts for existing students.

For each Student with an email but no linked User:
  - Creates a Django User (username=email, password=default)
  - Adds the user to the 'student' group
  - Links the User to the Student via student.user

Usage:
  python manage.py provision_student_users
  python manage.py provision_student_users --password=monmotdepasse
  python manage.py provision_student_users --dry-run
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from students.models import Student
from core.auth import UserRole


class Command(BaseCommand):
    help = "Provision Django User accounts for students who have an email but no linked User."

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            type=str,
            default='passe123',
            help='Default password for new student accounts (default: passe123)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        password = options['password']
        dry_run = options['dry_run']

        student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)

        students_without_user = Student.objects.filter(
            user__isnull=True,
        ).exclude(email__isnull=True).exclude(email='')

        total = students_without_user.count()
        self.stdout.write(f"Found {total} students without a Django User account.")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made."))

        created = 0
        skipped = 0
        errors = []

        for student in students_without_user:
            email = student.email.strip().lower()

            if not email:
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(f"  [DRY] Would create User for {student.last_name} {student.first_name} ({email})")
                created += 1
                continue

            try:
                # Check if a User with this email already exists
                existing_user = User.objects.filter(email=email).first()
                if existing_user:
                    # Link existing user to student
                    student.user = existing_user
                    student.save(update_fields=['user'])
                    existing_user.groups.add(student_group)
                    self.stdout.write(f"  [LINKED] {email} -> existing User #{existing_user.id}")
                    created += 1
                    continue

                # Also check by username
                existing_user = User.objects.filter(username=email).first()
                if existing_user:
                    student.user = existing_user
                    student.save(update_fields=['user'])
                    existing_user.groups.add(student_group)
                    self.stdout.write(f"  [LINKED] {email} -> existing User #{existing_user.id}")
                    created += 1
                    continue

                # Create new User
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=student.first_name[:30],
                    last_name=student.last_name[:30],
                    is_active=True,
                )
                user.groups.add(student_group)

                student.user = user
                student.save(update_fields=['user'])

                self.stdout.write(f"  [CREATED] {email} -> User #{user.id}")
                created += 1

            except Exception as e:
                errors.append(f"{student.last_name} {student.first_name} ({email}): {e}")
                self.stdout.write(self.style.ERROR(f"  [ERROR] {email}: {e}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Done: {created} created/linked, {skipped} skipped, {len(errors)} errors."))

        if errors:
            self.stdout.write(self.style.ERROR("Errors:"))
            for err in errors:
                self.stdout.write(f"  - {err}")
