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
        self.assertIn('run_as_app_user "python manage.py migrate"', pre_drop)
        self.assertIn('run_as_app_user "python manage.py collectstatic --noinput"', pre_drop)
        self.assertIn(
            'run_as_app_user "python manage.py shell -c \\"from core.auth import create_user_roles; create_user_roles()\\""',
            pre_drop,
        )

        self.assertNotIn("python manage.py migrate", pre_drop.replace('run_as_app_user "python manage.py migrate"', ""))
        self.assertNotIn(
            "python manage.py collectstatic --noinput",
            pre_drop.replace('run_as_app_user "python manage.py collectstatic --noinput"', ""),
        )


if __name__ == "__main__":
    unittest.main()
