from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
LOCAL_PROD_COMPOSE = REPO_ROOT / "infra" / "docker" / "docker-compose.local-prod.yml"
RELEASE_GATE = REPO_ROOT / "scripts" / "release_gate_oneshot.sh"


def _section(text: str, header: str, next_header: str | None = None) -> str:
    start = text.index(header)
    if next_header is None:
        return text[start:]
    end = text.index(next_header, start)
    return text[start:end]


class ReleaseGateLocalProdContractTests(unittest.TestCase):
    def test_local_prod_celery_mirrors_required_production_env(self):
        compose_text = LOCAL_PROD_COMPOSE.read_text()
        celery_block = _section(compose_text, "\n  celery:\n", "\n  nginx:\n")

        self.assertIn("env_file:", celery_block)
        self.assertIn("../../.env", celery_block)

        required_env_lines = [
            'DEFAULT_PASSWORD: "${DEFAULT_PASSWORD?err}"',
            'REDIS_HOST: "redis"',
            'REDIS_PORT: "6379"',
            'REDIS_DB: "1"',
            'CORS_ALLOWED_ORIGINS: "${CORS_ALLOWED_ORIGINS?err}"',
            'CSRF_TRUSTED_ORIGINS: "${CSRF_TRUSTED_ORIGINS?err}"',
            'METRICS_TOKEN: "${METRICS_TOKEN?err}"',
            'RATELIMIT_ENABLE: "false"',
            'E2E_TEST_MODE: "true"',
            'E2E_SEED_TOKEN: "${E2E_SEED_TOKEN:-}"',
        ]

        for line in required_env_lines:
            self.assertIn(line, celery_block)

    def test_local_prod_nginx_healthcheck_avoids_localhost_ipv6_probe(self):
        compose_text = LOCAL_PROD_COMPOSE.read_text()
        nginx_block = _section(compose_text, "\n  nginx:\n")

        self.assertIn("http://127.0.0.1/", nginx_block)
        self.assertNotIn("http://localhost/", nginx_block)

    def test_release_gate_dumps_runtime_logs_on_stability_failure(self):
        release_gate_text = RELEASE_GATE.read_text()
        stability_block = _section(
            release_gate_text,
            'run_logged "06_stability_180s" bash -c "',
            '\n\n# ---- C) Migrations',
        )

        self.assertIn(
            "docker compose --env-file '$COMPOSE_ENV_FILE' -f '$COMPOSE_FILE' ps || true",
            stability_block,
        )
        self.assertIn("Restarting|Exited|unhealthy", stability_block)
        self.assertIn(
            "logs --no-color --tail=100 backend celery nginx || true",
            stability_block,
        )


if __name__ == "__main__":
    unittest.main()
