import logging
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

BACKUP_DIR = os.environ.get('BACKUP_DIR', '/app/backups')
BACKUP_RETAIN_DAYS = int(os.environ.get('BACKUP_RETAIN_DAYS', '7'))
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def redact_backup_log_message(message: str) -> str:
    return EMAIL_RE.sub("<redacted-email>", message)


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def get_required_backup_gpg_passphrase() -> str | None:
    passphrase = os.environ.get("BACKUP_GPG_PASSPHRASE")
    if _env_truthy("REQUIRE_BACKUP_GPG") and not passphrase:
        raise RuntimeError(
            "BACKUP_GPG_PASSPHRASE must be set when REQUIRE_BACKUP_GPG=true"
        )
    return passphrase


def encrypt_backup_artifact(path: Path, *, passphrase: str, label: str) -> Path:
    encrypted_path = path.with_suffix(path.suffix + ".gpg")
    cmd = [
        "gpg",
        "--batch",
        "--yes",
        "--pinentry-mode",
        "loopback",
        "--passphrase-fd",
        "0",
        "--symmetric",
        "--cipher-algo",
        "AES256",
        "-o",
        str(encrypted_path),
        str(path),
    ]
    try:
        subprocess.run(
            cmd,
            input=passphrase.encode(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = redact_backup_log_message(exc.stderr.decode(errors="replace"))
        encrypted_path.unlink(missing_ok=True)
        raise RuntimeError(f"GPG encryption failed for {label}: {stderr}") from exc

    path.unlink()
    return encrypted_path


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def scheduled_backup(self):
    """
    Automated daily database backup via pg_dump custom format.
    Encrypts dumps when BACKUP_GPG_PASSPHRASE is set and rotates old backups.
    """
    try:
        backup_path = Path(BACKUP_DIR)
        backup_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        passphrase = get_required_backup_gpg_passphrase()
        filename = f'korrigo_db_{timestamp}.dump'
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
            err = redact_backup_log_message(proc.stderr.decode(errors='replace'))
            logger.error('pg_dump failed (rc=%d): %s', proc.returncode, err)
            raise RuntimeError(f'pg_dump failed: {err}')

        if passphrase:
            filepath = encrypt_backup_artifact(
                filepath,
                passphrase=passphrase,
                label="database dump",
            )

        size_mb = filepath.stat().st_size / (1024 * 1024)
        logger.info('Backup created: %s (%.1f MB)', filepath.name, size_mb)

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
    for f in (
        list(backup_path.glob('korrigo_db_*.dump'))
        + list(backup_path.glob('korrigo_db_*.dump.gpg'))
    ):
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink()
            removed += 1
    if removed:
        logger.info(
            'Rotated %d old backup(s) (retain=%d days)',
            removed,
            BACKUP_RETAIN_DAYS,
        )
