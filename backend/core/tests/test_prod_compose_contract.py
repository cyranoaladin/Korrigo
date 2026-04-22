from pathlib import Path
import unittest

from core.tests._repo_paths import repo_root_from


REPO_ROOT = repo_root_from(__file__)
PROD_COMPOSE = REPO_ROOT / "infra" / "docker" / "docker-compose.prod.yml"


def _section(text: str, header: str, next_header: str | None = None) -> str:
    start = text.index(header)
    if next_header is None:
        return text[start:]
    end = text.index(next_header, start)
    return text[start:end]


class ProdComposeContractTests(unittest.TestCase):
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

    def test_celery_workers_do_not_receive_http_only_secrets(self):
        compose_text = PROD_COMPOSE.read_text()
        celery_block = _section(compose_text, "\n  celery:\n", "\n  celery-beat:\n")
        beat_block = _section(compose_text, "\n  celery-beat:\n", "\n  nginx:\n")

        for block in (celery_block, beat_block):
            self.assertNotIn('CORS_ALLOWED_ORIGINS:', block)
            self.assertNotIn('CSRF_TRUSTED_ORIGINS:', block)
            self.assertNotIn('METRICS_TOKEN:', block)
            self.assertNotIn('env_file:', block)


if __name__ == "__main__":
    unittest.main()
