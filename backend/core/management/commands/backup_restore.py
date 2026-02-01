import os
import tempfile
import zipfile
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core import serializers
import json

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backup or restore database and media files'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['backup', 'restore'],
            help='Action to perform: backup or restore'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default=None,
            help='Directory to store backup files (for backup action)'
        )
        parser.add_argument(
            '--backup-path',
            type=str,
            default=None,
            help='Path to backup directory (for restore action)'
        )
        parser.add_argument(
            '--include-media',
            action='store_true',
            help='Include media files in backup'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'backup':
            self.backup(options)
        elif action == 'restore':
            self.restore(options)

    def backup(self, options):
        output_dir = options['output_dir']
        include_media = options['include_media']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write("DRY RUN MODE - No backup will be created")
            return
        
        if not output_dir:
            output_dir = tempfile.mkdtemp(prefix='korrigo_backup_')
            self.stdout.write(f"Created temporary backup directory: {output_dir}")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"korrigo_backup_{timestamp}"
        backup_dir = os.path.join(output_dir, backup_name)
        os.makedirs(backup_dir, exist_ok=True)
        
        try:
            # Backup database
            db_backup_path = os.path.join(backup_dir, f'db_backup_{timestamp}.json')
            self.stdout.write("Backing up database...")
            
            # Get all models to backup (excluding some Django internal ones)
            from django.apps import apps
            from django.contrib.contenttypes.models import ContentType
            
            # Define models to backup
            models_to_backup = []
            for app_config in apps.get_app_configs():
                for model in app_config.get_models():
                    # Skip some models that don't need to be backed up
                    if model._meta.label not in [
                        'contenttypes.ContentType',
                        'auth.Permission',
                        'sessions.Session'
                    ]:
                        models_to_backup.append(model)
            
            # Serialize data
            serialized_data = []
            for model in models_to_backup:
                try:
                    model_data = serializers.serialize('json', model.objects.all())
                    serialized_data.extend(json.loads(model_data))
                except Exception as e:
                    self.stderr.write(f"Error serializing {model._meta.label}: {e}")
            
            with open(db_backup_path, 'w') as f:
                json.dump(serialized_data, f, indent=2, default=str)
            
            # Backup media files if requested
            if include_media and os.path.exists(settings.MEDIA_ROOT):
                media_backup_path = os.path.join(backup_dir, f'media_backup_{timestamp}.zip')
                self.stdout.write("Backing up media files...")
                with zipfile.ZipFile(media_backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(settings.MEDIA_ROOT):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, settings.MEDIA_ROOT)
                            zipf.write(file_path, arcname)
            
            # Create manifest
            manifest = {
                'timestamp': timestamp,
                'includes_media': include_media,
                'database_backup': os.path.basename(db_backup_path) if os.path.exists(db_backup_path) else None,
                'media_backup': os.path.basename(media_backup_path) if include_media and os.path.exists(media_backup_path) else None,
                'backup_dir': backup_dir
            }
            
            manifest_path = os.path.join(backup_dir, 'manifest.json')
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created backup at: {backup_dir}')
            )
            self.stdout.write(f"Backup manifest: {manifest}")
            
        except Exception as e:
            self.stderr.write(f"Backup failed: {str(e)}")
            raise

    def restore(self, options):
        backup_path = options['backup_path']
        dry_run = options['dry_run']
        
        if not backup_path:
            self.stderr.write("Backup path is required for restore action")
            return
        
        if dry_run:
            self.stdout.write("DRY RUN MODE - No changes will be made")
        
        # Load manifest
        manifest_path = os.path.join(backup_path, 'manifest.json')
        if not os.path.exists(manifest_path):
            self.stderr.write("Manifest file not found in backup directory")
            return
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        self.stdout.write(f"Restoring from backup: {backup_path}")
        self.stdout.write(f"Backup timestamp: {manifest['timestamp']}")
        
        if dry_run:
            self.stdout.write("Would restore database...")
        else:
            # Restore database
            db_backup_file = manifest['database_backup']
            if db_backup_file:
                db_backup_path = os.path.join(backup_path, db_backup_file)
                if os.path.exists(db_backup_path):
                    self.stdout.write("Restoring database...")
                    
                    # Clear existing data first (be careful!)
                    from django.apps import apps
                    from django.db import connection
                    
                    # Get all models to restore
                    models_to_restore = []
                    for app_config in apps.get_app_configs():
                        for model in app_config.get_models():
                            if model._meta.label not in [
                                'contenttypes.ContentType',
                                'auth.Permission',
                                'sessions.Session'
                            ]:
                                models_to_restore.append(model)
                    
                    # Delete existing data (this is risky, but necessary for clean restore)
                    # Use a safer approach - truncate tables
                    with connection.cursor() as cursor:
                        for model in reversed(models_to_restore):
                            table_name = model._meta.db_table
                            try:
                                # table_name is from Django ORM model._meta.db_table (not user input)
                                cursor.execute(f"DELETE FROM {table_name};")  # nosec B608
                            except Exception as e:
                                # Table might not exist or have foreign key constraints
                                logger.warning(f"Could not delete from table {table_name}: {e}")  # nosec B608
                    
                    # Load data
                    with open(db_backup_path, 'r') as f:
                        data = json.load(f)
                    
                    # Deserialize and save
                    for item in data:
                        try:
                            obj_json = json.dumps([item])
                            obj = serializers.deserialize('json', obj_json)
                            for obj_instance in obj:
                                obj_instance.save()
                        except Exception as e:
                            self.stderr.write(f"Error restoring object: {e}")
                            continue
                    
                    self.stdout.write("Database restored successfully")
                else:
                    self.stderr.write(f"Database backup file not found: {db_backup_path}")
        
        if manifest['includes_media']:
            media_backup_file = manifest['media_backup']
            if media_backup_file:
                media_backup_path = os.path.join(backup_path, media_backup_file)
                if os.path.exists(media_backup_path):
                    if dry_run:
                        self.stdout.write("Would restore media files...")
                    else:
                        self.stdout.write("Restoring media files...")
                        
                        # Create media directory if it doesn't exist
                        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
                        
                        # Extract media files
                        with zipfile.ZipFile(media_backup_path, 'r') as zipf:
                            zipf.extractall(settings.MEDIA_ROOT)
                            
                        self.stdout.write(f"Restored media from: {media_backup_path}")
                else:
                    self.stderr.write(f"Media backup file not found: {media_backup_path}")
        
        self.stdout.write(
            self.style.SUCCESS('Restore completed successfully')
        )