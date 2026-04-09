from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
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
