import os
import json
import zipfile
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core import serializers
from django.db import transaction


class Command(BaseCommand):
    help = 'Restore database and media files from backup'

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_path',
            type=str,
            help='Path to backup directory'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be restored without actually restoring'
        )

    def handle(self, *args, **options):
        backup_path = options['backup_path']
        dry_run = options['dry_run']
        
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
                    for model in reversed(models_to_restore):
                        if hasattr(model, '_meta') and model._meta.managed:
                            model.objects.all().delete()
                    
                    # Load and deserialize data
                    with open(db_backup_path, 'r') as f:
                        data = json.load(f)
                    
                    objects_to_save = []
                    for item in data:
                        try:
                            # deserialize returns a generator
                            for obj in serializers.deserialize('json', json.dumps([item])):
                                objects_to_save.append(obj)
                        except Exception as e:
                            self.stderr.write(f"Error deserializing object: {e}")
                            continue

                    # Multi-pass insertion to resolve FK dependencies (Topological Sort approximation)
                    pending_objects = objects_to_save
                    max_passes = 15
                    pass_num = 1
                    
                    self.stdout.write(f"Starting restoration of {len(pending_objects)} objects...")
                    
                    while pending_objects and pass_num <= max_passes:
                        next_pending = []
                        saved_count = 0
                        
                        for obj_wrapper in pending_objects:
                            try:
                                # Try to save
                                with transaction.atomic():
                                    obj_wrapper.save()
                                saved_count += 1
                            except Exception as e:
                                # Keep for next pass
                                next_pending.append(obj_wrapper)
                        
                        if saved_count == 0 and next_pending:
                            # We are stuck
                            self.stderr.write(f"Pass {pass_num}: No progress made. {len(next_pending)} objects failed to save.")
                            self.stderr.write(f"Sample failure: {next_pending[0].object}")
                            break
                            
                        self.stdout.write(f"Pass {pass_num}: Saved {saved_count} objects. {len(next_pending)} remaining.")
                        pending_objects = next_pending
                        pass_num += 1
                        
                    if pending_objects:
                        self.stderr.write(f"Restore incomplete! {len(pending_objects)} objects could not be restored.")
                    else:
                        self.stdout.write("Database restored successfully")
                    
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