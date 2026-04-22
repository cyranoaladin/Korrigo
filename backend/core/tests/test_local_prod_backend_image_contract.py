from pathlib import Path
import sys
import unittest

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from core.tests._repo_paths import repo_root_from

REPO_ROOT = repo_root_from(__file__)
DOCKERFILE = REPO_ROOT / "backend" / "Dockerfile"
BACKEND_DOCKERIGNORE = REPO_ROOT / "backend" / ".dockerignore"
LOCAL_PROD_COMPOSE = REPO_ROOT / "infra" / "docker" / "docker-compose.local-prod.yml"
RELEASE_GATE = REPO_ROOT / "scripts" / "release_gate_oneshot.sh"


def _section(text: str, header: str, next_header: str | None = None) -> str:
    start = text.index(header)
    if next_header is None:
        return text[start:]
    end = text.index(next_header, start)
    return text[start:end]


class LocalProdBackendImageContractTests(unittest.TestCase):
    def test_dockerfile_supports_optional_dev_requirements_install(self):
        dockerfile_text = DOCKERFILE.read_text()

        self.assertIn("COPY requirements.txt requirements-dev.txt ./", dockerfile_text)
        self.assertIn("ARG INSTALL_DEV_REQUIREMENTS=false", dockerfile_text)
        self.assertIn("pip install --no-cache-dir -r requirements.txt", dockerfile_text)
        self.assertIn("pip install --no-cache-dir -r requirements-dev.txt", dockerfile_text)

    def test_local_prod_backend_build_enables_dev_requirements(self):
        compose_text = LOCAL_PROD_COMPOSE.read_text()
        backend_block = _section(compose_text, "\n  backend:\n", "\n  celery:\n")

        self.assertIn("build:", backend_block)
        self.assertIn("args:", backend_block)
        self.assertIn('INSTALL_DEV_REQUIREMENTS: "true"', backend_block)
        self.assertIn("- ../../:/repo:ro", backend_block)

    def test_release_gate_runs_pytest_via_python_module(self):
        release_gate_text = RELEASE_GATE.read_text()

        self.assertIn("python -m pytest -v --tb=short -m \"\"", release_gate_text)
        self.assertNotIn(' "$BACKEND_SVC" pytest -v --tb=short -m ""', release_gate_text)

    def test_backend_dockerignore_keeps_release_gate_dependencies_in_context(self):
        dockerignore_text = BACKEND_DOCKERIGNORE.read_text()

        blocked_entries = [
            "requirements-dev.txt",
            "pytest.ini",
            "conftest.py",
            "tests/",
            "test_*.py",
        ]

        for entry in blocked_entries:
            self.assertNotIn(entry, dockerignore_text)


if __name__ == "__main__":
    unittest.main()
