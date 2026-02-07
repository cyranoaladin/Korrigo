import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from core.models import UserProfile

class Command(BaseCommand):
    help = 'Ensure admin user exists with default credentials (username: admin, password: admin)'

    def handle(self, *args, **options):
        allow = os.environ.get('ALLOW_ENSURE_ADMIN', 'false').lower() == 'true'
        django_env = os.environ.get('DJANGO_ENV', 'development')
        if not allow or django_env == 'production':
            raise CommandError(
                "ensure_admin is disabled by default. Set ALLOW_ENSURE_ADMIN=true "
                "and ensure DJANGO_ENV is not 'production' to run this command."
            )

        self.stdout.write(self.style.SUCCESS('Ensuring admin user exists...'))

        username = os.environ.get('ADMIN_DEFAULT_USERNAME', 'admin')
        password = os.environ.get('ADMIN_DEFAULT_PASSWORD')
        email = os.environ.get('ADMIN_DEFAULT_EMAIL', 'admin@example.com')

        if not password:
            raise CommandError(
                "ADMIN_DEFAULT_PASSWORD must be set when running ensure_admin."
            )

        try:
            admin_user = User.objects.get(username=username)
            self.stdout.write(f'Admin user "{username}" already exists.')
        except User.DoesNotExist:
            admin_user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f'Created admin user "{username}" with default password'))

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
        self.stdout.write(self.style.WARNING(f'Default credentials: username={username}'))
        self.stdout.write(self.style.WARNING('User will be forced to change password on first login'))
