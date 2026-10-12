#!/usr/bin/env python3
"""Restore only Korrigo HTTPS egress after a Docker bridge ID changes."""
import argparse
import ipaddress
import json
import re
import subprocess


def network_details(data):
    if data['Name'] != 'docker_default' or data['Driver'] != 'bridge' or data['Internal']:
        raise ValueError('Expected the external bridge network docker_default')
    bridge = data.get('Options', {}).get('com.docker.network.bridge.name') or 'br-' + data['Id'][:12]
    if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,15}', bridge):
        raise ValueError('Invalid bridge interface')
    subnets = [ipaddress.ip_network(x['Subnet']) for x in data['IPAM']['Config'] if 'Subnet' in x]
    ipv4 = [s for s in subnets if s.version == 4]
    if len(ipv4) != 1 or not ipv4[0].is_private:
        raise ValueError('Expected exactly one private IPv4 subnet')
    return {'bridge': bridge, 'subnet': str(ipv4[0])}


def rule_commands(info):
    bridge, subnet = info['bridge'], info['subnet']
    base = ['iptables', '--wait', '5']
    return [
        base + ['-t', 'filter', '-A', 'DOCKER-CT', '-o', bridge, '-d', subnet,
                '-m', 'conntrack', '--ctstate', 'RELATED,ESTABLISHED',
                '-m', 'comment', '--comment', 'korrigo-https-return', '-j', 'ACCEPT'],
        base + ['-t', 'filter', '-A', 'DOCKER-FORWARD', '-i', bridge, '-s', subnet,
                '-p', 'tcp', '--dport', '443', '-m', 'conntrack',
                '--ctstate', 'NEW,ESTABLISHED', '-m', 'comment',
                '--comment', 'korrigo-https-egress', '-j', 'ACCEPT'],
        base + ['-t', 'nat', '-A', 'POSTROUTING', '-s', subnet, '!', '-o', bridge,
                '-m', 'comment', '--comment', 'korrigo-egress-nat', '-j', 'MASQUERADE'],
    ]


def ensure_rules(info, *, run=subprocess.run, apply=False):
    changed = 0
    for command in rule_commands(info):
        check = ['-C' if x == '-A' else x for x in command]
        result = run(check, text=True, capture_output=True)
        if result.returncode == 0:
            continue
        if result.returncode != 1:
            raise RuntimeError('Cannot check firewall rule: ' + result.stderr.strip())
        changed += 1
        if apply:
            result = run(command, text=True, capture_output=True)
            if result.returncode:
                raise RuntimeError('Cannot install firewall rule: ' + result.stderr.strip())
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Install missing scoped rules')
    args = parser.parse_args()
    raw = subprocess.check_output(['docker', 'network', 'inspect', 'docker_default'])
    info = network_details(json.loads(raw)[0])
    changed = ensure_rules(info, apply=args.apply)
    print(json.dumps({**info, 'mode': 'apply' if args.apply else 'dry-run', 'missing_rules': changed}))


if __name__ == '__main__':
    main()
