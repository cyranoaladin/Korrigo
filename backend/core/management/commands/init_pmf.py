import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from core.auth import UserRole

class Command(BaseCommand):
    help = 'Initialize PMF Users and Groups. In production, requires strong passwords via env vars.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting PMF Initialization...'))
        
        is_prod = getattr(settings, 'DJANGO_ENV', os.environ.get('DJANGO_ENV', 'development')) == 'production'

        # 1. Create Groups
        teachers_group, created = Group.objects.get_or_create(name=UserRole.TEACHER)
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created group "{UserRole.TEACHER}"'))
        else:
            self.stdout.write(f'Group "{UserRole.TEACHER}" already exists')

        # 2. Create Admin
        admin_email = os.environ.get('PMF_ADMIN_EMAIL', 'alaeddine.benrhouma@ert.tn')
        # Security: Use environment variable for admin password
        admin_pass = os.environ.get('ADMIN_DEFAULT_PASSWORD', '')

        if is_prod:
            if not admin_pass or len(admin_pass) < 12:
                self.stderr.write(self.style.ERROR(
                    'CRITICAL: In production, ADMIN_DEFAULT_PASSWORD must be set and >= 12 characters.'
                ))
                return
        else:
            if not admin_pass:
                admin_pass = 'CHANGE_ME_ADMIN'
                self.stdout.write(self.style.WARNING(
                    'WARNING: Using default admin password. NOT for production!'
                ))

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
        default_pass = os.environ.get('TEACHER_DEFAULT_PASSWORD', '')

        if is_prod:
            if not default_pass or len(default_pass) < 12:
                self.stderr.write(self.style.ERROR(
                    'CRITICAL: In production, TEACHER_DEFAULT_PASSWORD must be set and >= 12 characters.'
                ))
                return
        else:
            if not default_pass:
                default_pass = 'CHANGE_ME_TEACHER'
                self.stdout.write(self.style.WARNING(
                    'WARNING: Using default teacher password. NOT for production!'
                ))

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
