#!/usr/bin/env python3
"""Check one container, or recover it without touching its dependencies."""
import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request


def docker(*args):
    return subprocess.run(['docker', *args], capture_output=True, text=True, timeout=45)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['check', 'recover'])
    parser.add_argument('name')
    parser.add_argument('--url')
    args = parser.parse_args()
    # An unavailable daemon is an infrastructure failure, not a missing container.
    if docker('info', '--format', '{{.ServerVersion}}').returncode:
        print('Docker unavailable; no container action taken')
        return 1
    result = docker('inspect', args.name)
    if args.mode == 'recover':
        if result.returncode == 0:
            return docker('restart', '--timeout', '20', args.name).returncode
        return docker('compose', 'up', '-d', '--no-deps', args.name).returncode
    if result.returncode:
        print(f'{args.name}: missing or cannot inspect')
        return 1
    state = json.loads(result.stdout)[0]['State']
    if not state.get('Running') or state.get('Paused') or state.get('Restarting'):
        return 1
    health = state.get('Health', {}).get('Status')
    if health is not None and health != 'healthy':
        print(f'{args.name}: Docker health is {health}')
        return 1
    if args.url:
        try:
            with urllib.request.urlopen(args.url, timeout=5) as response:
                return 0 if response.status < 400 else 1
        except urllib.error.HTTPError as exc:
            # Authentication responses demonstrate a responsive protected app.
            return 0 if exc.code in (401, 403) else 1
        except (urllib.error.URLError, TimeoutError, OSError):
            return 1
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
