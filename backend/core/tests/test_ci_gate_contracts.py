from pathlib import Path
import sys
import unittest

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from core.tests._repo_paths import repo_root_from

REPO_ROOT = repo_root_from(__file__)
RELEASE_GATE = REPO_ROOT / "scripts" / "release_gate_oneshot.sh"
RELEASE_GATE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release-gate.yml"
KORRIGO_CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "korrigo-ci.yml"
PIP_AUDIT_GATE = REPO_ROOT / "backend" / "scripts" / "run_pip_audit_gate.sh"
REQUIREMENTS = REPO_ROOT / "backend" / "requirements.txt"


class CIGateContractTests(unittest.TestCase):
    def test_release_gate_metrics_check_matches_protected_contract(self):
        text = RELEASE_GATE.read_text()

        self.assertIn('metrics_url=\'${NGINX_BASE_URL}/metrics\'', text)
        self.assertIn('X-Metrics-Token: ${METRICS_TOKEN}', text)
        self.assertIn('403 without token, 200 with token', text)

    def test_release_gate_workflow_uses_consistent_metrics_token(self):
        text = RELEASE_GATE_WORKFLOW.read_text()

        self.assertIn("RELEASE_GATE_METRICS_TOKEN: ci-release-gate-metrics-token", text)
        self.assertIn("METRICS_TOKEN=ci-release-gate-metrics-token", text)
        self.assertIn("METRICS_TOKEN: ${{ env.RELEASE_GATE_METRICS_TOKEN }}", text)
        self.assertNotIn("METRICS_TOKEN=ci-metrics-token", text)

    def test_security_gate_uses_pip_audit_wrapper(self):
        workflow_text = KORRIGO_CI_WORKFLOW.read_text()
        script_text = PIP_AUDIT_GATE.read_text()
        requirements_text = REQUIREMENTS.read_text()

        self.assertIn("./scripts/run_pip_audit_gate.sh", workflow_text)
        self.assertIn('if [ "$DJANGO_VERSION" = "4.2.30" ]', script_text)
        self.assertIn("CVE-2026-33034", script_text)
        self.assertIn("CVE-2026-4539", script_text)
        self.assertIn("django==4.2.30", requirements_text)


if __name__ == "__main__":
    unittest.main()
