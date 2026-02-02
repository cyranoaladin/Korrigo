import os
import sys
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from core.models import UserProfile

class Command(BaseCommand):
    help = 'Ensure admin user exists. In production, ADMIN_PASSWORD env var is required.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Ensuring admin user exists...'))

        # Detect production mode: DJANGO_ENV=production AND not running tests
        django_env = getattr(settings, 'DJANGO_ENV', os.environ.get('DJANGO_ENV', 'development'))
        is_testing = 'test' in os.environ.get('DJANGO_SETTINGS_MODULE', '') or 'pytest' in sys.modules
        is_prod = django_env == 'production' and not is_testing
        
        username = os.environ.get('ADMIN_USERNAME', 'admin')
        password = os.environ.get('ADMIN_PASSWORD', '')
        email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        
        # Security: Block weak passwords in production
        if is_prod:
            if not password or len(password) < 12:
                self.stderr.write(self.style.ERROR(
                    'CRITICAL: In production, ADMIN_PASSWORD must be set and >= 12 characters.'
                ))
                return
        else:
            # Development fallback
            if not password:
                password = 'admin'
                self.stdout.write(self.style.WARNING('Using default dev password (admin). NOT for production!'))

        try:
            admin_user = User.objects.get(username=username)
            self.stdout.write(f'Admin user "{username}" already exists.')
        except User.DoesNotExist:
            admin_user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f'Created admin user "{username}"'))

        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

        try:
            profile = admin_user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=admin_user)
            self.stdout.write('Created user profile for admin')

        if not profile.must_change_password:
            profile.must_change_password = True
            profile.save()
            self.stdout.write(self.style.WARNING('Set must_change_password=True for admin user'))
        else:
            self.stdout.write('Admin profile already requires password change')

        self.stdout.write(self.style.SUCCESS('Admin user setup complete.'))
        self.stdout.write(self.style.WARNING('User will be forced to change password on first login'))
