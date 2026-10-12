import importlib.util
from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'ops' / 'repair_korrigo_egress.py'


class NetworkRepairTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), 'The scoped network repair helper is missing')
        spec = importlib.util.spec_from_file_location('korrigo_egress', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_network_uses_current_bridge_not_historical_identifier(self):
        result = self.module.network_details({
            'Name': 'docker_default', 'Id': 'a6c97bf6afce' + '0' * 52,
            'Driver': 'bridge', 'Internal': False, 'Options': {},
            'IPAM': {'Config': [{'Subnet': '172.19.0.0/16'}]},
        })
        self.assertEqual(result['bridge'], 'br-a6c97bf6afce')
        self.assertEqual(result['subnet'], '172.19.0.0/16')

    def test_refuses_unrelated_or_internal_network(self):
        for change in [{'Name': 'other_default'}, {'Internal': True}, {'Driver': 'overlay'}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.module.network_details({
                    'Name': 'docker_default', 'Id': 'a' * 64, 'Driver': 'bridge',
                    'Internal': False, 'Options': {},
                    'IPAM': {'Config': [{'Subnet': '172.19.0.0/16'}]}, **change,
                })

    def test_only_new_https_is_allowed_and_return_traffic_is_stateful(self):
        commands = self.module.rule_commands({'bridge': 'br-a6c97bf6afce', 'subnet': '172.19.0.0/16'})
        outgoing = next(c for c in commands if 'DOCKER-FORWARD' in c)
        returning = next(c for c in commands if 'DOCKER-CT' in c)
        self.assertIn('--dport', outgoing)
        self.assertEqual(outgoing[outgoing.index('--dport') + 1], '443')
        self.assertIn('172.19.0.0/16', outgoing)
        self.assertIn('RELATED,ESTABLISHED', returning)
        self.assertFalse(any('-F' in c or '-X' in c or '-P' in c for c in commands))

    def test_apply_is_idempotent_and_dry_run_does_not_change_firewall(self):
        rules = set()
        writes = []

        def run(cmd, **kwargs):
            op = '-C' if '-C' in cmd else '-A'
            canonical = tuple('-OP' if x == op else x for x in cmd)
            if op == '-C':
                return subprocess.CompletedProcess(cmd, 0 if canonical in rules else 1, '', '')
            rules.add(canonical)
            writes.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, '', '')

        info = {'bridge': 'br-a6c97bf6afce', 'subnet': '172.19.0.0/16'}
        self.module.ensure_rules(info, run=run, apply=False)
        self.assertEqual(writes, [])
        self.module.ensure_rules(info, run=run, apply=True)
        self.assertEqual(len(writes), 3)
        self.module.ensure_rules(info, run=run, apply=True)
        self.assertEqual(len(writes), 3)


if __name__ == '__main__':
    unittest.main()
