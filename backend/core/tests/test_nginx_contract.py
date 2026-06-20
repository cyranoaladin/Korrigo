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

    def test_student_login_nginx_limit_is_high_anti_flood_guard(self):
        conf = NGINX_CONF.read_text()
        zone_idx = conf.index("zone=student_login")
        login_idx = conf.index("location /api/students/login/")
        login_block = conf[login_idx : conf.index("location /api/students/", login_idx + 1)]

        self.assertIn("Business lockout is per attempted identifier in Django", conf)
        self.assertIn("zone=student_login:10m rate=30r/s", conf[zone_idx : zone_idx + 120])
        self.assertIn("limit_req zone=student_login burst=60 nodelay;", login_block)
        self.assertIn("anti-flood guard for student login", conf.lower())


if __name__ == "__main__":
    unittest.main()
