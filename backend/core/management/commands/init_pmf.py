import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist
from core.auth import UserRole

class Command(BaseCommand):
    help = 'Initialize PMF Users and Groups'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting PMF Initialization...'))

        # 1. Create Groups
        teachers_group, created = Group.objects.get_or_create(name=UserRole.TEACHER)
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created group "{UserRole.TEACHER}"'))
        else:
            self.stdout.write(f'Group "{UserRole.TEACHER}" already exists')

        # 2. Create Admin
        admin_email = 'alaeddine.benrhouma@ert.tn'
        # Security: Use environment variable for admin password
        admin_pass = os.environ.get('ADMIN_DEFAULT_PASSWORD', 'CHANGE_ME_ADMIN')
        django_env = os.environ.get('DJANGO_ENV', 'development')
        allow_defaults = os.environ.get('ALLOW_DEFAULT_PASSWORDS', 'false').lower() == 'true'

        if admin_pass == 'CHANGE_ME_ADMIN' and (django_env == 'production' or not allow_defaults):
            raise CommandError(
                "ADMIN_DEFAULT_PASSWORD must be set (non-default). "
                "Set ALLOW_DEFAULT_PASSWORDS=true only for non-production dev/test."
            )

        try:
            admin_user = User.objects.get(username=admin_email)
            self.stdout.write(f'Admin user {admin_email} already exists. Updating Permissions.')
        except ObjectDoesNotExist:
            admin_user = User.objects.create_superuser(
                username=admin_email,
                email=admin_email,
                password=admin_pass
            )
            self.stdout.write(self.style.SUCCESS(f'Created Admin user {admin_email}'))
        
        # Ensure Password is correct (Force Reset)
        admin_user.set_password(admin_pass)

        # Ensure Admin is Staff and Superuser
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        
        # Add Admin to Teachers group (as requested for testing)
        teachers_group.user_set.add(admin_user)
        self.stdout.write(f'Added Admin {admin_email} to "{UserRole.TEACHER}" group')

        # 3. Create Teachers
        teachers_data = [
            'patrick.dupont@ert.tn',
            'selima.klibi@ert.tn',
            'philippe.carr@ert.tn'
        ]
        # Security: Use environment variable for teacher default password
        default_pass = os.environ.get('TEACHER_DEFAULT_PASSWORD', 'CHANGE_ME_TEACHER')

        if default_pass == 'CHANGE_ME_TEACHER' and (django_env == 'production' or not allow_defaults):
            raise CommandError(
                "TEACHER_DEFAULT_PASSWORD must be set (non-default). "
                "Set ALLOW_DEFAULT_PASSWORDS=true only for non-production dev/test."
            )

        for email in teachers_data:
            try:
                user = User.objects.get(username=email)
                self.stdout.write(f'Teacher {email} already exists.')
            except ObjectDoesNotExist:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=default_pass
                )
                self.stdout.write(self.style.SUCCESS(f'Created Teacher {email}'))
            
            # Ensure Password is correct (Force Reset)
            user.set_password(default_pass)
            
            # Ensure not staff (unless explicitly set otherwise, but here we enforce standard user)
            if not user.is_superuser:
                user.is_staff = False
                user.save()
            
            # Add to Group
            teachers_group.user_set.add(user)
            self.stdout.write(f'Added {email} to "{UserRole.TEACHER}" group')

        self.stdout.write(self.style.SUCCESS('PMF Initialization Complete.'))
