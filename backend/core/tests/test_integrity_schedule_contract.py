from pathlib import Path
import sys
import unittest

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from core.tests._repo_paths import repo_root_from

REPO_ROOT = repo_root_from(__file__)
CELERY_FILE = REPO_ROOT / "backend" / "core" / "celery.py"
TASKS_FILE = REPO_ROOT / "backend" / "grading" / "tasks.py"


class IntegrityScheduleContractTests(unittest.TestCase):
    def test_celery_beat_registers_integrity_audit(self):
        text = CELERY_FILE.read_text()
        self.assertIn("'run-copy-integrity-audit'", text)
        self.assertIn("'task': 'grading.tasks.run_copy_integrity_audit'", text)
        self.assertIn("'schedule': 900.0", text)

    def test_grading_tasks_exposes_integrity_audit_task(self):
        text = TASKS_FILE.read_text()
        self.assertIn("def run_copy_integrity_audit()", text)
        self.assertIn('call_command("check_copy_integrity", fail_on_issues=True)', text)


if __name__ == "__main__":
    unittest.main()
