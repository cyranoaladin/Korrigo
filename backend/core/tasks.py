import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

BACKUP_DIR = os.environ.get('BACKUP_DIR', '/app/backups')
BACKUP_RETAIN_DAYS = int(os.environ.get('BACKUP_RETAIN_DAYS', '7'))


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def scheduled_backup(self):
    """
    Automated daily database backup via pg_dump.
    Stores compressed SQL dumps and rotates old backups.
    """
    try:
        backup_path = Path(BACKUP_DIR)
        backup_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'korrigo_db_{timestamp}.sql.gz'
        filepath = backup_path / filename

        db = settings.DATABASES['default']
        env = os.environ.copy()
        env['PGPASSWORD'] = db['PASSWORD']

        cmd = [
            'pg_dump',
            '-h', db['HOST'],
            '-p', str(db['PORT']),
            '-U', db['USER'],
            '-d', db['NAME'],
            '--no-owner',
            '--no-acl',
            '-Fc',  # custom format (compressed)
        ]

        with open(filepath, 'wb') as f:
            proc = subprocess.run(
                cmd, stdout=f, stderr=subprocess.PIPE,
                env=env, timeout=600,
            )

        if proc.returncode != 0:
            err = proc.stderr.decode(errors='replace')
            logger.error('pg_dump failed (rc=%d): %s', proc.returncode, err)
            raise RuntimeError(f'pg_dump failed: {err}')

        size_mb = filepath.stat().st_size / (1024 * 1024)
        logger.info('Backup created: %s (%.1f MB)', filename, size_mb)

        # Rotate old backups
        _cleanup_old_backups(backup_path)

        return {'file': str(filepath), 'size_mb': round(size_mb, 1)}

    except Exception as exc:
        logger.exception('Backup task failed')
        raise self.retry(exc=exc)


def _cleanup_old_backups(backup_path: Path):
    """Remove backups older than BACKUP_RETAIN_DAYS."""
    cutoff = datetime.now() - timedelta(days=BACKUP_RETAIN_DAYS)
    removed = 0
    for f in backup_path.glob('korrigo_db_*.sql.gz'):
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink()
            removed += 1
    if removed:
        logger.info('Rotated %d old backup(s) (retain=%d days)', removed, BACKUP_RETAIN_DAYS)
