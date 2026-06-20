from pathlib import Path
import sys
import unittest

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from core.tests._repo_paths import repo_root_from

REPO_ROOT = repo_root_from(__file__)
ENTRYPOINT = REPO_ROOT / "backend" / "entrypoint.sh"


def _pre_drop_section(text: str) -> str:
    marker = "# Drop privileges if running as root"
    return text[: text.index(marker)]


class EntrypointContractTests(unittest.TestCase):
    def test_management_commands_do_not_run_as_root_before_privilege_drop(self):
        entrypoint_text = ENTRYPOINT.read_text()
        pre_drop = _pre_drop_section(entrypoint_text)

        self.assertIn("run_as_app_user()", entrypoint_text)
        self.assertIn('run_as_app_user "python manage.py migrate --noinput"', pre_drop)
        self.assertIn('run_as_app_user "python manage.py collectstatic --noinput"', pre_drop)
        self.assertIn('run_as_app_user "python manage.py migrate --check --noinput"', pre_drop)
        self.assertIn("ensure_schema_ready()", pre_drop)

        self.assertNotIn("python manage.py migrate", pre_drop.replace('run_as_app_user "python manage.py migrate --noinput"', "").replace('run_as_app_user "python manage.py migrate --check --noinput"', ""))
        self.assertNotIn(
            "python manage.py collectstatic --noinput",
            pre_drop.replace('run_as_app_user "python manage.py collectstatic --noinput"', ""),
        )

    def test_entrypoint_is_fail_fast_and_allows_explicit_migration_oneshot(self):
        entrypoint_text = ENTRYPOINT.read_text()

        self.assertNotIn("|| true", entrypoint_text)
        self.assertIn("is_explicit_migration_command()", entrypoint_text)
        self.assertIn("Skipping schema invariant checks for explicit migration command", entrypoint_text)
        self.assertIn("Database schema is not up to date", entrypoint_text)
        self.assertIn("DJANGO_AUTO_MIGRATE=false", entrypoint_text)
        self.assertLess(
            entrypoint_text.index("ensure_schema_ready"),
            entrypoint_text.index("ensure_roles"),
        )


if __name__ == "__main__":
    unittest.main()
