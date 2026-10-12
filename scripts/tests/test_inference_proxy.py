import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/ops/render_inference_proxy.py'
TEMPLATE = ROOT / 'infra/nginx/inference-proxy.conf.template'


class InferenceProxyTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), 'The safe inference proxy renderer is missing')
        spec = importlib.util.spec_from_file_location('proxy_renderer', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_search_credential_is_scoped_and_ingestion_is_not_exposed(self):
        rendered = self.module.render_proxy(TEMPLATE.read_text(), 'client-test-token-1234567890',
                                            'upstream-test-token-1234567890')
        self.assertIn('location = /search', rendered)
        self.assertIn('Bearer client-test-token-1234567890', rendered)
        self.assertIn('proxy_set_header Authorization "Bearer upstream-test-token-1234567890"', rendered)
        self.assertIn('limit_except POST { deny all; }', rendered)
        self.assertNotIn('location /ingest', rendered)
        self.assertNotIn('location /delete', rendered)
        self.assertEqual(rendered.count('location / { return 404; }'), 2)
        self.assertNotIn('__KORRIGO_', rendered)

    def test_token_cannot_inject_nginx_directives_or_variables(self):
        for token in ['bad"; return 200; #', '$http_authorization', 'short', 'line\nbreak']:
            with self.subTest(token=token), self.assertRaises(ValueError):
                self.module.render_proxy('template', token, 'upstream-test-token-1234567890')


if __name__ == '__main__':
    unittest.main()
