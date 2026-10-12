"""Exercise production entrypoints without touching the shared Docker daemon."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / 'infra/docker/docker-compose.prod.yml'


class ProductionTemplateTests(unittest.TestCase):
    def test_examples_cover_every_required_canonical_compose_variable(self):
        required = set(re.findall(r'\$\{([A-Z_]+):\?', COMPOSE.read_text()))
        for filename in ('.env.example', '.env.prod.example'):
            with self.subTest(filename=filename):
                text = (ROOT / filename).read_text()
                assignments = dict(re.findall(r'^([A-Z_]+)=(.*)$', text, re.MULTILINE))
                self.assertEqual(required - assignments.keys(), set())
                self.assertEqual(assignments['RAG_URL'], 'http://korrigo-rag:8001')
                self.assertEqual(assignments['KORRIGO_BACKEND_IMAGE'], '')
                self.assertEqual(assignments['KORRIGO_NGINX_IMAGE'], '')
                self.assertNotIn('KORRIGO_SHA', assignments)
                self.assertNotIn('DB_PASSWORD', assignments)
                self.assertNotIn('DJANGO_ALLOWED_HOSTS', assignments)


class ProductionEntrypointTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.log = self.directory / 'docker-calls.jsonl'
        self.runtime = self.directory / 'private runtime.env'
        self.runtime.write_text('SECRET_KEY=synthetic-not-printed\n')
        self.runtime.chmod(0o600)
        docker = self.directory / 'docker'
        docker.write_text('''#!/usr/bin/env python3
import json, os, sys
with open(os.environ['DOCKER_CALL_LOG'], 'a') as log:
    log.write(json.dumps(sys.argv[1:]) + '\\n')
if '--quiet' in sys.argv and os.environ.get('FAIL_CONFIG'):
    sys.exit(23)
''')
        docker.chmod(0o755)
        legacy = self.directory / 'docker-compose'
        legacy.write_text(docker.read_text())
        legacy.chmod(0o755)
        self.env = {'PATH': str(self.directory) + os.pathsep + os.environ['PATH'],
                    'KORRIGO_ENV_FILE': str(self.runtime),
                    'DOCKER_CALL_LOG': str(self.log)}

    def run_script(self, *arguments, **extra_env):
        return subprocess.run(['bash', str(ROOT / 'scripts/prod_up.sh'), *arguments],
                              cwd=self.directory, env=self.env | extra_env,
                              text=True, capture_output=True)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def expected_prefix(self):
        return ['compose', '--env-file', str(self.runtime), '-f', str(COMPOSE)]

    def test_up_validates_privately_then_uses_verified_images_from_any_working_directory(self):
        result = self.run_script('backend')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [self.expected_prefix() + ['config', '--quiet'],
                                       self.expected_prefix() + ['up', '--no-build', '--wait', '-d', 'backend']])
        self.assertNotIn('synthetic-not-printed', result.stdout + result.stderr)

    def test_failed_validation_never_starts_services(self):
        result = self.run_script(FAIL_CONFIG='1')
        self.assertEqual(result.returncode, 23)
        self.assertEqual(self.calls(), [self.expected_prefix() + ['config', '--quiet']])

    def test_missing_environment_file_fails_before_invoking_docker(self):
        self.runtime.unlink()
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_make_targets_use_same_explicit_environment_and_compose_plugin(self):
        targets = {'logs': ['logs', '-f'],
                   'migrate': ['run', '--rm', '--no-deps', '-T', 'backend', 'python', 'manage.py', 'migrate', '--noinput'],
                   'down': ['down'], 'shell': ['exec', 'backend', 'python', 'manage.py', 'shell']}
        for target, expected in targets.items():
            with self.subTest(target=target):
                if self.log.exists():
                    self.log.unlink()
                result = subprocess.run(['make', '-s', target], cwd=ROOT, env=self.env,
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.calls(), [self.expected_prefix() + expected])

    def test_down_preserves_volumes_and_uses_canonical_environment_from_any_directory(self):
        result = subprocess.run(['bash', str(ROOT / 'scripts/prod_down.sh')],
                                cwd=self.directory, env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [self.expected_prefix() + ['down']])

    def test_make_preserves_literal_shell_syntax_in_environment_file_name(self):
        filename = 'private $(printf shell-evaluated) `printf backtick-evaluated` runtime.env'
        self.runtime = self.directory / filename
        self.runtime.write_text('SECRET_KEY=synthetic-not-printed\n')
        self.env['KORRIGO_ENV_FILE'] = str(self.runtime)
        result = subprocess.run(['make', '-s', 'logs'], cwd=ROOT, env=self.env,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [self.expected_prefix() + ['logs', '-f']])

    def test_documented_fresh_install_migrates_before_starting_applications(self):
        text = (ROOT / 'README_KORRIGO_PRODUCTION.md').read_text()
        match = re.search(r'```bash\n(bash scripts/prod_compose\.sh up[^`]*?bash scripts/prod_up\.sh)\n```', text)
        self.assertIsNotNone(match, 'Fresh-install dependency/migration/application sequence is missing')
        self.assertLess(match.start(1), text.index('bash scripts/prod_up.sh'),
                        'Fresh-install preparation must precede the first application-start command')
        result = subprocess.run(['bash', '-e', '-c', match.group(1)],
                                cwd=ROOT, env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        prefix = self.expected_prefix()
        self.assertEqual(self.calls(), [
            prefix + ['up', '--no-build', '--wait', '-d', 'db', 'redis'],
            prefix + ['run', '--rm', '--no-deps', '-T', 'backend', 'python', 'manage.py', 'migrate', '--noinput'],
            prefix + ['config', '--quiet'],
            prefix + ['up', '--no-build', '--wait', '-d'],
        ])


if __name__ == '__main__':
    unittest.main()
