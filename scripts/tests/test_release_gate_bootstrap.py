"""Exercise release bootstrap with fake commands, never the shared Docker daemon."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'release_gate_oneshot.sh'
FAKE_COMMAND = '''
import json
import os
from pathlib import Path
import sys

tool = Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ['FAKE_EVENTS'], 'a') as stream:
    stream.write(json.dumps({'tool': tool, 'args': args}) + '\\n')
state_path = Path(os.environ['FAKE_STATE'])
state = json.loads(state_path.read_text()) if state_path.exists() else {}
if tool == 'bash':
    if '/api/health/live/' in ' '.join(args) and os.environ.get('FAKE_STOP_AT_HEALTH') == '1':
        sys.exit(70)
    sys.exit(0)
if tool != 'docker' or args[0] != 'compose' or args[1] == 'version':
    sys.exit(0)
command = args[1:]
while command and command[0] in ('--env-file', '-f'):
    command = command[2:]
if command[0] == 'up':
    if command[-2:] == ['db', 'redis']:
        if '--wait' not in command:
            sys.exit(40)
        failure = int(os.environ.get('FAKE_DEPENDENCIES_EXIT', '0'))
        if failure:
            sys.exit(failure)
        state['dependencies_healthy'] = True
    elif not state.get('migrated'):
        # The production entrypoint rejects a fresh schema without auto-migrate.
        sys.exit(41)
if command[0] == 'run' and command[-4:] == ['python', 'manage.py', 'migrate', '--noinput']:
    if not state.get('dependencies_healthy'):
        sys.exit(42)
    failure = int(os.environ.get('FAKE_MIGRATION_EXIT', '0'))
    if failure:
        sys.exit(failure)
    state['migrated'] = True
state_path.write_text(json.dumps(state))
if command[0] == 'exec' and 'pytest' in command:
    print('===== 1 passed in 0.01s =====')
'''


class ReleaseGateBootstrapTests(unittest.TestCase):
    def run_gate(self, *, stop_at_health=True, **overrides):
        with tempfile.TemporaryDirectory(prefix='korrigo-bootstrap-contract-') as temporary:
            root = Path(temporary)
            bindir = root / 'bin'
            bindir.mkdir()
            for name in ('docker', 'bash', 'jq'):
                command = bindir / name
                command.write_text('#!' + sys.executable + '\n' + FAKE_COMMAND)
                command.chmod(0o755)
            events = root / 'events.jsonl'
            env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ['PATH'],
                       ROOT=str(root), LOG_DIR=str(root / 'logs'),
                       COMPOSE_FILE='validation.yml', COMPOSE_ENV_FILE='validation.env',
                       NGINX_BASE_URL='http://validation.invalid',
                       TEST_PROF_PASSWORD='contract-password',
                       FAKE_EVENTS=str(events), FAKE_STATE=str(root / 'state.json'),
                       FAKE_STOP_AT_HEALTH='1' if stop_at_health else '0',
                       **overrides)
            result = subprocess.run(['/bin/bash', str(SCRIPT)], env=env, text=True,
                                    capture_output=True, timeout=20, check=False)
            history = [json.loads(line) for line in events.read_text().splitlines()]
            return result, history

    @staticmethod
    def compose_calls(history, operation):
        return [event['args'] for event in history
                if event['tool'] == 'docker' and event['args'][:1] == ['compose']
                and len(event['args']) > 5 and event['args'][5] == operation]

    def test_fresh_schema_migrates_after_healthy_dependencies_before_apps_and_http(self):
        result, history = self.run_gate(BACKEND_SVC='validation-backend')
        self.assertEqual(result.returncode, 70, result.stdout + result.stderr)
        dependencies, applications = self.compose_calls(history, 'up')
        self.assertEqual(dependencies[-2:], ['db', 'redis'])
        self.assertIn('--wait', dependencies)
        self.assertEqual(dependencies[dependencies.index('--wait-timeout') + 1], '120')
        migration, = self.compose_calls(history, 'run')
        for argument in ('--rm', '--no-deps', '-T', 'DJANGO_AUTO_MIGRATE=false'):
            self.assertIn(argument, migration)
        self.assertEqual(migration[-5:], ['validation-backend', 'python', 'manage.py', 'migrate', '--noinput'])
        self.assertLess(history.index({'tool': 'docker', 'args': dependencies}),
                        history.index({'tool': 'docker', 'args': migration}))
        self.assertLess(history.index({'tool': 'docker', 'args': migration}),
                        history.index({'tool': 'docker', 'args': applications}))
        first_health = next(i for i, event in enumerate(history)
                            if event['tool'] == 'bash' and '/api/health/live/' in ' '.join(event['args']))
        self.assertLess(history.index({'tool': 'docker', 'args': applications}), first_health)
        for event in history:
            if event['tool'] == 'docker' and event['args'][:1] == ['compose'] and event['args'][1] != 'version':
                self.assertEqual(event['args'][1:5], ['--env-file', 'validation.env', '-f', 'validation.yml'])

    def test_unhealthy_dependencies_stop_before_migrations_or_application_boot(self):
        result, history = self.run_gate(FAKE_DEPENDENCIES_EXIT='31')
        self.assertEqual(result.returncode, 31, result.stdout + result.stderr)
        up, = self.compose_calls(history, 'up')
        self.assertEqual(up[-2:], ['db', 'redis'])
        self.assertFalse(self.compose_calls(history, 'run'))
        self.assertFalse(any(event['tool'] == 'bash' for event in history))

    def test_failed_migration_stops_before_application_boot_or_http(self):
        result, history = self.run_gate(FAKE_MIGRATION_EXIT='32')
        self.assertEqual(result.returncode, 32, result.stdout + result.stderr)
        self.assertEqual(len(self.compose_calls(history, 'up')), 1)
        self.assertEqual(len(self.compose_calls(history, 'run')), 1)
        self.assertFalse(any(event['tool'] == 'bash' for event in history))

    def test_later_migration_gate_checks_schema_and_keeps_seed_and_test_phases(self):
        result, history = self.run_gate(stop_at_health=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        executions = self.compose_calls(history, 'exec')
        migration_checks = [command for command in executions if 'migrate' in command]
        self.assertEqual(len(migration_checks), 1)
        self.assertEqual(migration_checks[0][-5:], ['python', 'manage.py', 'migrate', '--check', '--noinput'])
        self.assertEqual(sum('seed_prod' in command for command in executions), 2)
        tests, = [command for command in executions if 'pytest' in command]
        self.assertIn('DJANGO_SETTINGS_MODULE=core.settings_test_postgres', tests)
        self.assertEqual(tests[-2:], ['-m', ''])
        self.assertTrue(any(event['tool'] == 'bash' and 'release_gate_e2e.sh' in event['args'][0]
                            for event in history))


if __name__ == '__main__':
    unittest.main()
