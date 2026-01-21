from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist

class Command(BaseCommand):
    help = 'Initialize PMF Users and Groups'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting PMF Initialization...'))

        # 1. Create Groups
        teachers_group, created = Group.objects.get_or_create(name='Teachers')
        if created:
            self.stdout.write(self.style.SUCCESS('Created group "Teachers"'))
        else:
            self.stdout.write('Group "Teachers" already exists')

        # 2. Create Admin
        admin_email = 'alaeddine.benrhouma@ert.tn'
        admin_pass = 'adminpass'
        
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
        self.stdout.write(f'Added Admin {admin_email} to "Teachers" group')

        # 3. Create Teachers
        teachers_data = [
            'patrick.dupont@ert.tn',
            'selima.klibi@ert.tn',
            'philippe.carr@ert.tn'
        ]
        default_pass = 'profpass'

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
            self.stdout.write(f'Added {email} to "Teachers" group')

        self.stdout.write(self.style.SUCCESS('PMF Initialization Complete.'))
