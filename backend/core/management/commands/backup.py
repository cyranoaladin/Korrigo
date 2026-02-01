import os
import tempfile
import zipfile
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core import serializers
import json


class Command(BaseCommand):
    help = 'Backup database and media files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default=None,
            help='Directory to store backup files (default: temporary directory)'
        )
        parser.add_argument(
            '--include-media',
            action='store_true',
            help='Include media files in backup'
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        include_media = options['include_media']
        
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
                data = serializers.serialize('json', model.objects.all(), indent=2)
                serialized_data.extend(json.loads(data))
            
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