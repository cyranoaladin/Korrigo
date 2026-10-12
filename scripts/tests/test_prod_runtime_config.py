import json
import os
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]


class RuntimeConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = {'PATH': os.environ['PATH']}
        env.update({key: 'synthetic-test-only' for key in (
            'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'REDIS_PASSWORD',
            'SECRET_KEY', 'ALLOWED_HOSTS', 'CORS_ALLOWED_ORIGINS',
            'CSRF_TRUSTED_ORIGINS', 'METRICS_TOKEN', 'BACKUP_GPG_PASSPHRASE',
        )})
        cls.backend_image = 'example.invalid/backend@sha256:' + 'a' * 64
        cls.nginx_image = 'example.invalid/nginx@sha256:' + 'b' * 64
        env.update(KORRIGO_BACKEND_IMAGE=cls.backend_image, KORRIGO_NGINX_IMAGE=cls.nginx_image,
                   KORRIGO_REDIS_VOLUME='existing-redis-volume',
                   KORRIGO_PROXY_CONFIG='/tmp/synthetic-proxy.conf',
                   OLLAMA_URL='http://korrigo-ollama:11434')
        result = subprocess.run([
            'docker', 'compose', '--env-file', '/dev/null', '-f',
            str(ROOT / 'infra/docker/docker-compose.prod.yml'), 'config', '--format', 'json',
        ], env=env, text=True, capture_output=True, check=True)
        cls.config = json.loads(result.stdout)

    def test_runtime_images_can_be_pinned_without_secret_overrides(self):
        for name in ['backend', 'celery', 'celery-beat']:
            self.assertEqual(self.config['services'][name]['image'], self.backend_image)
        self.assertEqual(self.config['services']['nginx']['image'], self.nginx_image)

    def test_beat_schedule_lives_on_existing_persistent_cache(self):
        command = self.config['services']['celery-beat']['command']
        self.assertIn('--schedule', command)
        self.assertEqual(command[command.index('--schedule') + 1],
                         '/app/.cache/nexus-celerybeat/celerybeat-schedule')

    def test_inference_url_and_private_network_are_explicit(self):
        for name in ['backend', 'celery', 'celery-beat']:
            service = self.config['services'][name]
            self.assertEqual(service['environment'].get('OLLAMA_URL'), 'http://korrigo-ollama:11434')
            self.assertIn('korrigo_ai', service['networks'])
            self.assertIn('default', service['networks'])
        self.assertTrue(self.config['networks']['korrigo_ai']['external'])
        self.assertNotIn('korrigo_ai', self.config['services']['db']['networks'])
        self.assertNotIn('korrigo_ai', self.config['services']['redis']['networks'])

    def test_redis_retains_existing_volume_and_does_not_evict_tasks(self):
        service = self.config['services']['redis']
        self.assertIn('noeviction', ' '.join(service['command']))
        self.assertIn('--appendonly yes', ' '.join(service['command']))
        self.assertIn('--appendfsync everysec', ' '.join(service['command']))
        self.assertEqual(service['volumes'][0]['target'], '/data')
        source = service['volumes'][0]['source']
        self.assertTrue(self.config['volumes'][source]['external'])
        self.assertEqual(self.config['volumes'][source]['name'], 'existing-redis-volume')

    def test_inference_gateway_exposes_no_host_port_or_ingestion_credential(self):
        service = self.config['services']['inference-proxy']
        self.assertNotIn('ports', service)
        self.assertNotIn('environment', service)
        self.assertTrue(service['read_only'])
        self.assertIn('korrigo_ai', service['networks'])
        self.assertIn('rag_upstream', service['networks'])
        self.assertNotIn('default', service['networks'])
        self.assertTrue(service['volumes'][0]['read_only'])
        self.assertEqual(self.config['networks']['rag_upstream']['name'], 'compose_rag_ui_net')


if __name__ == '__main__':
    unittest.main()
