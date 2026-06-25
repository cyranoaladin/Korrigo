from pathlib import Path
import stat
import unittest

from core.tests._repo_paths import repo_root_from


REPO_ROOT = repo_root_from(__file__)
LOCAL_RELEASE_CHECK = REPO_ROOT / "scripts" / "release" / "local_release_check.sh"
LOCAL_SMOKE_E2E = REPO_ROOT / "scripts" / "release" / "local_smoke_e2e.sh"
SEED_E2E = REPO_ROOT / "backend" / "core" / "management" / "commands" / "seed_e2e.py"
E2E_ENV = REPO_ROOT / "frontend" / "tests" / "e2e" / "e2eEnv.ts"
AUTH_HELPERS = REPO_ROOT / "frontend" / "tests" / "e2e" / "authHelpers.ts"


class LocalReleaseScriptsContractTests(unittest.TestCase):
    def test_release_scripts_exist_and_are_executable(self):
        for path in (LOCAL_RELEASE_CHECK, LOCAL_SMOKE_E2E):
            self.assertTrue(path.exists(), f"{path} must exist")
            mode = path.stat().st_mode
            self.assertTrue(mode & stat.S_IXUSR, f"{path} must be user-executable")

    def test_release_scripts_use_strict_shell_mode(self):
        for path in (LOCAL_RELEASE_CHECK, LOCAL_SMOKE_E2E):
            text = path.read_text()
            self.assertIn("set -euo pipefail", text)

    def test_pipeline_requires_real_playwright_when_configured(self):
        release_text = LOCAL_RELEASE_CHECK.read_text()
        smoke_text = LOCAL_SMOKE_E2E.read_text()

        self.assertIn("PASS_EXISTING_PLAYWRIGHT_OR_CYPRESS", release_text)
        self.assertIn("NO-GO_E2E_EXISTING_PLAYWRIGHT_FAILED", smoke_text)
        self.assertIn("npm run test:e2e", smoke_text)
        self.assertIn('grep "^E2E_STATUS="', release_text)
        self.assertNotIn('"PASS_LOCAL_HTTP_SMOKE" ]; then', release_text)
        self.assertNotIn("PASS_PUBLIC_SMOKE_ONLY", release_text + smoke_text)

    def test_release_scripts_do_not_use_forbidden_docker_or_prod_operations(self):
        forbidden = [
            "docker compose down",
            "down -v",
            "docker system prune",
            "docker volume prune",
            "docker network prune",
            "docker compose up",
            "korrigo.labomaths.tn",
            "workflow_dispatch",
            "git push",
        ]
        for path in (LOCAL_RELEASE_CHECK, LOCAL_SMOKE_E2E):
            text = path.read_text()
            for needle in forbidden:
                self.assertNotIn(needle, text, f"{needle!r} must not appear in {path}")

    def test_smoke_e2e_has_diagnostics_and_login_probe(self):
        text = LOCAL_SMOKE_E2E.read_text()

        self.assertIn("E2E_DIAGNOSTIC.md", text)
        self.assertIn("E2E_TEACHER_EXISTS", text)
        self.assertIn("E2E_TEACHER_GROUP_TEACHER", text)
        self.assertIn("E2E_DIRECTION_EXISTS", text)
        self.assertIn("E2E_DIRECTION_GROUP_DIRECTION", text)
        self.assertIn("/api/login/", text)
        self.assertIn("TEACHER_SESSION_COOKIE_COUNT", text)
        self.assertIn("do_POST", text)

    def test_e2e_seed_and_helpers_use_synthetic_direction_contract(self):
        seed_text = SEED_E2E.read_text()
        env_text = E2E_ENV.read_text()
        helper_text = AUTH_HELPERS.read_text()

        self.assertIn("E2E_DIRECTION_USERNAME", seed_text)
        self.assertIn("direction_all", seed_text)
        self.assertIn("@example.test", seed_text)
        self.assertIn("DIRECTION_USER", env_text)
        self.assertIn("DIRECTION_PASS", env_text)
        self.assertIn("DIRECTION_USER", helper_text)
        self.assertIn("DIRECTION_PASS", helper_text)
        self.assertNotRegex(
            helper_text,
            r"[A-Za-z0-9._%+-]+@(?!example\.test\b|example\.com\b|example\.org\b|localhost\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        )

    def test_release_check_writes_manifest(self):
        text = LOCAL_RELEASE_CHECK.read_text()

        self.assertIn("LOCAL_RELEASE_MANIFEST.md", text)
        self.assertIn("LOCAL_RELEASE_CHECK_STATUS=PASS", text)
        self.assertIn("FAILED_STEP=", text)


if __name__ == "__main__":
    unittest.main()
