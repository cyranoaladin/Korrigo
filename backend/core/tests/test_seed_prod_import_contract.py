from pathlib import Path
import sys
import unittest

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from core.tests._repo_paths import repo_root_from

REPO_ROOT = repo_root_from(__file__)
SEED_COMMAND = REPO_ROOT / "backend" / "core" / "management" / "commands" / "seed_prod.py"
CORE_SEED_MODULE = REPO_ROOT / "backend" / "core" / "seed_prod.py"
LEGACY_SEED_SCRIPT = REPO_ROOT / "backend" / "seed_prod.py"


class SeedProdImportContractTests(unittest.TestCase):
    def test_management_command_imports_packaged_seed_module(self):
        command_text = SEED_COMMAND.read_text()

        self.assertIn("from core.seed_prod import seed_prod", command_text)
        self.assertNotIn("from seed_prod import seed_prod", command_text)

    def test_packaged_seed_module_exists(self):
        self.assertTrue(CORE_SEED_MODULE.is_file())

    def test_legacy_seed_script_remains_a_compatibility_shim(self):
        legacy_text = LEGACY_SEED_SCRIPT.read_text()

        self.assertIn("from core.seed_prod import seed_prod, setup_standalone_django", legacy_text)
        self.assertIn("if __name__ == \"__main__\":", legacy_text)


if __name__ == "__main__":
    unittest.main()
