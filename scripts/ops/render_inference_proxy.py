#!/usr/bin/env python3
"""Render the private inference proxy; credentials are read only from environment."""
import argparse
import os
from pathlib import Path
import re


def render_proxy(template, client_token, upstream_token):
    for token in (client_token, upstream_token):
        if not re.fullmatch(r'[A-Za-z0-9_.~+/-]{20,512}', token):
            raise ValueError('Invalid inference credential format')
    # Nginx string equality ignores case; its non-~* regex match is case-sensitive.
    pattern = re.escape(client_token).replace(r'\-', '-')
    return template.replace('__KORRIGO_SEARCH_TOKEN__', pattern).replace(
        '__KORRIGO_UPSTREAM_TOKEN__', upstream_token)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('template', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = render_proxy(args.template.read_text(), os.environ['KORRIGO_SEARCH_TOKEN'],
                          os.environ['KORRIGO_UPSTREAM_TOKEN'])
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as output:
        output.write(result)


if __name__ == '__main__':
    main()
