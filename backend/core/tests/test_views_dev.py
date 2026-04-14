from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory

from core.views_dev import seed_e2e_endpoint


class TestSeedE2eEndpoint(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @override_settings(E2E_SEED_TOKEN=None)
    def test_seed_endpoint_disabled_without_token(self):
        request = self.factory.post("/api/dev/seed/")
        response = seed_e2e_endpoint(request)

        self.assertEqual(response.status_code, 503)

    @override_settings(E2E_SEED_TOKEN="expected-token")
    def test_seed_endpoint_rejects_invalid_token(self):
        request = self.factory.post("/api/dev/seed/", HTTP_X_E2E_SEED_TOKEN="wrong-token")
        response = seed_e2e_endpoint(request)

        self.assertEqual(response.status_code, 403)

    @override_settings(E2E_SEED_TOKEN="expected-token")
    @patch("core.views_dev.subprocess.run")
    def test_seed_endpoint_runs_canonical_script_with_e2e_env(self, mock_run):
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="ok", stderr="")

        request = self.factory.post("/api/dev/seed/", HTTP_X_E2E_SEED_TOKEN="expected-token")
        response = seed_e2e_endpoint(request)

        self.assertEqual(response.status_code, 200)
        _, kwargs = mock_run.call_args
        called_args = mock_run.call_args.args[0]

        self.assertEqual(Path(called_args[1]).name, "seed_e2e.py")
        self.assertIn("scripts", Path(called_args[1]).parts)
        self.assertEqual(kwargs["env"]["E2E_TEST_MODE"], "true")
