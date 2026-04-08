import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('viatique__PMF')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat periodic tasks schedule
app.conf.beat_schedule = {
    'update-copy-status-metrics': {
        'task': 'grading.tasks.update_copy_status_metrics',
        'schedule': 60.0,  # Run every 60 seconds
    },
    # LOT 9: Clean up expired edit locks every 5 minutes
    'cleanup-expired-locks': {
        'task': 'grading.tasks.cleanup_expired_locks',
        'schedule': 300.0,  # Every 5 minutes
    },
    # LOT 9 RGPD: Purge audit logs older than 1 year, daily at 03:00
    'purge-old-audit-logs': {
        'task': 'grading.tasks.purge_old_audit_logs',
        'schedule': crontab(hour=3, minute=0),
    },
    # LOT 3: Automated daily database backup at 02:00
    'daily-database-backup': {
        'task': 'core.tasks.scheduled_backup',
        'schedule': crontab(hour=2, minute=0),
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
