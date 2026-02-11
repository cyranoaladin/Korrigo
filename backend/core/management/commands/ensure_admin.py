import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile

class Command(BaseCommand):
    help = 'Ensure admin user exists with default credentials (username: admin, password: admin)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Ensuring admin user exists...'))

        username = 'admin'
        password = 'admin'
        email = 'admin@example.com'

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
        self.stdout.write(self.style.WARNING('Default credentials: username=admin, password=admin'))
        self.stdout.write(self.style.WARNING('User will be forced to change password on first login'))
