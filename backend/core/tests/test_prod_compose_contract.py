from pathlib import Path
import unittest

from core.tests._repo_paths import repo_root_from


REPO_ROOT = repo_root_from(__file__)
PROD_COMPOSE = REPO_ROOT / "infra" / "docker" / "docker-compose.prod.yml"
BACKUP_SCRIPT = REPO_ROOT / "scripts" / "korrigo_backup.sh"


def _section(text: str, header: str, next_header: str | None = None) -> str:
    start = text.index(header)
    if next_header is None:
        return text[start:]
    end = text.index(next_header, start)
    return text[start:end]


class ProdComposeContractTests(unittest.TestCase):
    def test_release_images_are_explicit_direct_runtime_tags(self):
        compose_text = PROD_COMPOSE.read_text()
        backend_block = _section(compose_text, "\n  backend:\n", "\n  celery:\n")
        celery_block = _section(compose_text, "\n  celery:\n", "\n  celery-beat:\n")
        beat_block = _section(compose_text, "\n  celery-beat:\n", "\n  nginx:\n")
        nginx_block = _section(compose_text, "\n  nginx:\n", "\nvolumes:\n")

        for block in (backend_block, celery_block, beat_block):
            self.assertIn(
                "image: korrigo-backend:korrigo-direct-c38a586",
                block,
            )
            self.assertNotIn("${KORRIGO_SHA", block)
            self.assertNotIn(":latest", block)

        self.assertIn(
            "image: korrigo-nginx:korrigo-direct-81b85c5",
            nginx_block,
        )
        self.assertNotIn("${KORRIGO_SHA", nginx_block)
        self.assertNotIn(":latest", nginx_block)

    def test_prod_compose_has_no_overlay_or_frontend_bind_mounts(self):
        compose_text = PROD_COMPOSE.read_text()
        self.assertNotIn("OVERLAY_DIR", compose_text)
        self.assertNotIn("/overlay", compose_text)
        self.assertNotIn("../../overlay", compose_text)
        self.assertNotIn("FRONTEND_DIR", compose_text)
        self.assertNotIn("/usr/share/nginx/html:ro", compose_text)

    def test_redis_auth_is_mandatory(self):
        compose_text = PROD_COMPOSE.read_text()
        redis_block = _section(compose_text, "\n  redis:\n", "\n  backend:\n")

        self.assertIn('REDIS_PASSWORD: "${REDIS_PASSWORD:?err}"', redis_block)
        self.assertIn("--requirepass $$REDIS_PASSWORD", redis_block)
        self.assertIn("redis-cli -a $$REDIS_PASSWORD ping", redis_block)

    def test_prod_runtime_disables_implicit_mutations_and_api_docs(self):
        compose_text = PROD_COMPOSE.read_text()
        backend_block = _section(compose_text, "\n  backend:\n", "\n  celery:\n")
        celery_block = _section(compose_text, "\n  celery:\n", "\n  celery-beat:\n")
        beat_block = _section(compose_text, "\n  celery-beat:\n", "\n  nginx:\n")

        for block in (backend_block, celery_block, beat_block):
            self.assertIn('DJANGO_AUTO_MIGRATE: "false"', block)
            self.assertIn('SEED_ON_START: "false"', block)
            self.assertIn('ENABLE_API_DOCS: "false"', block)
            self.assertNotIn("E2E_SEED_TOKEN", block)

        self.assertIn('GUNICORN_WORKERS: "${GUNICORN_WORKERS:-4}"', backend_block)

    def test_backup_gpg_passphrase_is_required_for_runtime_backup_tasks(self):
        compose_text = PROD_COMPOSE.read_text()
        backend_block = _section(compose_text, "\n  backend:\n", "\n  celery:\n")
        celery_block = _section(compose_text, "\n  celery:\n", "\n  celery-beat:\n")
        beat_block = _section(compose_text, "\n  celery-beat:\n", "\n  nginx:\n")

        for block in (backend_block, celery_block, beat_block):
            self.assertIn('BACKUP_GPG_PASSPHRASE: "${BACKUP_GPG_PASSPHRASE:?err}"', block)
            self.assertIn('REQUIRE_BACKUP_GPG: "true"', block)

    def test_db_service_no_longer_inherits_full_env_file(self):
        compose_text = PROD_COMPOSE.read_text()
        db_block = _section(compose_text, "\n  db:\n", "\n  redis:\n")
        self.assertNotIn("env_file:", db_block)

    def test_backend_does_not_receive_seed_only_admin_passwords(self):
        compose_text = PROD_COMPOSE.read_text()
        backend_block = _section(compose_text, "\n  backend:\n", "\n  celery:\n")
        self.assertNotIn("env_file:", backend_block)
        self.assertNotIn("ADMIN_PASSWORD:", backend_block)
        self.assertNotIn("TEACHER_PASSWORD:", backend_block)
        self.assertNotIn("DEFAULT_PASSWORD:", backend_block)

    def test_default_student_password_is_not_runtime_environment(self):
        compose_text = PROD_COMPOSE.read_text()
        backend_block = _section(compose_text, "\n  backend:\n", "\n  celery:\n")
        celery_block = _section(compose_text, "\n  celery:\n", "\n  celery-beat:\n")
        beat_block = _section(compose_text, "\n  celery-beat:\n", "\n  nginx:\n")

        for block in (backend_block, celery_block, beat_block):
            self.assertNotIn("DEFAULT_PASSWORD:", block)
            self.assertNotIn("STUDENT_INITIAL_PASSWORD:", block)

    def test_celery_workers_do_not_receive_http_only_secrets(self):
        compose_text = PROD_COMPOSE.read_text()
        celery_block = _section(compose_text, "\n  celery:\n", "\n  celery-beat:\n")
        beat_block = _section(compose_text, "\n  celery-beat:\n", "\n  nginx:\n")

        for block in (celery_block, beat_block):
            self.assertNotIn('CORS_ALLOWED_ORIGINS:', block)
            self.assertNotIn('CSRF_TRUSTED_ORIGINS:', block)
            self.assertNotIn('METRICS_TOKEN:', block)
            self.assertNotIn('env_file:', block)

class BackupScriptContractTests(unittest.TestCase):
    def test_host_backup_requires_gpg_and_encrypts_json_exports(self):
        script = BACKUP_SCRIPT.read_text()

        self.assertIn("REQUIRE_BACKUP_GPG", script)
        self.assertIn("BACKUP_GPG_PASSPHRASE must be set", script)
        self.assertIn("encrypt_json_exports_if_configured", script)
        self.assertIn("*.json", script)

    def test_host_backup_redacts_email_like_values_from_logs(self):
        script = BACKUP_SCRIPT.read_text()

        self.assertIn("redact_log_message", script)
        self.assertIn("<redacted-email>", script)


if __name__ == "__main__":
    unittest.main()
