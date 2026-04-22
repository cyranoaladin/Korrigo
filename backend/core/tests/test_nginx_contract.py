from pathlib import Path
import unittest

from core.tests._repo_paths import repo_root_from


REPO_ROOT = repo_root_from(__file__)
NGINX_CONF = REPO_ROOT / "infra" / "nginx" / "nginx.conf"


class NginxContractTests(unittest.TestCase):
    def test_backend_upstream_is_resolved_dynamically(self):
        conf = NGINX_CONF.read_text()
        self.assertIn("resolver 127.0.0.11 valid=10s ipv6=off;", conf)
        self.assertIn("set $backend_upstream http://backend:8000;", conf)

    def test_metrics_endpoint_is_proxied_before_spa_fallback(self):
        conf = NGINX_CONF.read_text()

        metrics_idx = conf.index("location = /metrics")
        api_idx = conf.index("location /api/")
        spa_idx = conf.index("location / {")

        self.assertGreater(metrics_idx, api_idx)
        self.assertLess(metrics_idx, spa_idx)
        self.assertIn("proxy_pass $backend_upstream;", conf[metrics_idx:spa_idx])


if __name__ == "__main__":
    unittest.main()
