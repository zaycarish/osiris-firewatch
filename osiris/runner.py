#!/usr/bin/env python3
"""Run trusted, host-owned Osiris check and recovery definitions."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from reporting import Reporter, show_status
from restart_limits import load_history, recent, limit

ROOT = Path(__file__).resolve().parent.parent


def validate(config):
    jobs = config['jobs']
    names = [j['name'] for j in jobs]
    if len(names) != len(set(names)):
        raise ValueError('job names must be unique')
    seen = set()
    for job in jobs:
        if not isinstance(job['name'], str) or not job['name']:
            raise ValueError('job name must be a nonempty string')
        for key in ('check', 'action'):
            command = job.get(key)
            if command is not None and (not isinstance(command, list) or not command or
                                        not all(isinstance(x, str) for x in command)):
                raise ValueError(f'{job["name"]}: {key} must be a nonempty list of strings')
        if not job.get('check') and not job.get('action'):
            raise ValueError(f'{job["name"]}: requires a check or action')
        for key, default in (('timeout', 60), ('wait', 0), ('interval', 5), ('cooldown', 0)):
            value = job.get(key, default)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0 or (key not in ('wait', 'cooldown') and value == 0):
                raise ValueError(f'{job["name"]}: invalid {key}')
        if isinstance(job.get('max_attempts', 3), bool) or not isinstance(job.get('max_attempts', 3), int) or job.get('max_attempts', 3) < 1:
            raise ValueError(f'{job["name"]}: max_attempts must be a positive integer')
        if not isinstance(job.get('attempt_window', 3600), (int, float)) or isinstance(job.get('attempt_window', 3600), bool) or job.get('attempt_window', 3600) <= 0:
            raise ValueError(f'{job["name"]}: attempt_window must be positive')
        if any(dep not in seen for dep in job.get('requires', [])):
            raise ValueError(f'{job["name"]}: dependencies must appear earlier in jobs')
        seen.add(job['name'])
    return jobs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', choices=['run', 'status', 'alerts', 'discord-setup', 'discord-test', 'simulate-failure', 'simulate-boot', 'recovery-test'], default='run')
    parser.add_argument('--fail', action='append', default=[], metavar='JOB', help='simulate failure in recovery-test; repeat for multiple jobs')
    parser.add_argument('--recovery-fails', action='store_true', help='assume recovery fails in recovery-test')
    parser.add_argument('--json', action='store_true', help='show status as JSON')
    parser.add_argument('--config', type=Path, default=ROOT / 'osiris/jobs.json')
    parser.add_argument('--dry-run', action='store_true', help='validate and show jobs without running commands')
    args = parser.parse_args()
    if args.command == 'simulate-boot':
        from notifications import enqueue, flush
        import socket
        import uuid
        with (ROOT / 'osiris/.run.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print('Osiris is running. Try again after this run finishes.', file=sys.stderr)
                return 1
            test_id = str(uuid.uuid4())
            try:
                enqueue(ROOT, dict(time=time.time(), host=socket.gethostname(), job='host', status='boot',
                    test_id=test_id, reason='SIMULATED power recovery / boot notification. No reboot performed; no health checks run by this test.'))
                flush(ROOT)
                pending = json.loads((ROOT / 'osiris/.discord-pending.json').read_text())
                if any(event.get('test_id') == test_id for event in pending):
                    print('Simulated boot notification queued for a later timer run.')
                else:
                    print('Simulated boot notification delivered to Discord.')
                return 0
            except (OSError, ValueError, KeyError):
                print('Delivery could not complete; any queued notification will retry on a later timer run.', file=sys.stderr)
                return 1
    if args.command == 'simulate-failure':
        with (ROOT / 'osiris/.run.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print('Osiris is running. Try again after this run finishes.', file=sys.stderr)
                return 1
            (ROOT / 'osiris/.simulate-failure').touch()
        print('Simulation armed: next scheduled run reports simulation failure; the following run recovers silently.')
        print('No real containers will be stopped by this simulation.')
        return 0
    if args.command in ('discord-setup', 'discord-test'):
        from notifications import configure, send
        try:
            if args.command == 'discord-setup':
                configure(ROOT)
            else:
                import socket
                send(ROOT, f'Osiris test from {socket.gethostname()}: Discord alerts are connected.')
                print('Discord test delivered.')
            return 0
        except (OSError, ValueError, KeyError):
            print('Discord setup or delivery failed. Check the saved webhook, channel permissions, and host connectivity.', file=sys.stderr)
            return 1
    if args.command == 'status':
        try:
            return show_status(ROOT, args.json)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            parser.error(f'Cannot read status: {exc}')
    if args.command == 'alerts':
        path = ROOT / 'osiris/alerts.jsonl'
        if path.exists():
            from collections import deque
            with path.open() as stream:
                print(''.join(deque(stream, maxlen=20)), end='')
        else:
            print('No recorded alerts.')
        return 0
    try:
        jobs = validate(json.loads(args.config.read_text()))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    if args.command == 'recovery-test':
        from recovery_test import plan
        try:
            print(plan(ROOT, jobs, args.fail, args.recovery_fails))
        except (OSError, ValueError, TypeError) as exc:
            parser.error(str(exc))
        return 0
    if args.dry_run:
        print(json.dumps(jobs, indent=2))
        return 0
    # Keep concurrent boot/manual/timer runs from issuing duplicate actions.
    with (ROOT / 'osiris/.run.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Osiris is already running', file=sys.stderr)
            return 1
        with (ROOT / 'osiris.log').open('a', buffering=1) as logfile:
            def log(message):
                line = f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] {message}'
                print(line, flush=True)
                logfile.write(line + '\n')

            def run(command, timeout):
                log(f'COMMAND: {command!r}')
                try:
                    # Separate process group lets timeout stop descendants too.
                    with subprocess.Popen(command, cwd=ROOT, stdout=logfile, stderr=subprocess.STDOUT,
                                          start_new_session=True) as process:
                        try:
                            return process.wait(timeout=timeout) == 0
                        except subprocess.TimeoutExpired:
                            import signal
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait()
                            log(f'TIMEOUT after {timeout}s')
                            return False
                except OSError as exc:
                    log(f'COMMAND ERROR: {exc}')
                    return False

            def check(job):
                deadline = time.monotonic() + job.get('wait', 0)
                while True:
                    if run(job['check'], job.get('timeout', 60)):
                        return True
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return False
                    time.sleep(min(job.get('interval', 5), remaining))

            state_path = ROOT / 'osiris/.recovery.json'
            try:
                attempts = json.loads(state_path.read_text())
                if not isinstance(attempts, dict):
                    raise ValueError('invalid recovery state')
            except FileNotFoundError:
                attempts = {}
            except (ValueError, OSError) as exc:
                log(f'Cannot read recovery state: {exc}')
                return 1
            try:
                history = load_history(ROOT, attempts)
            except (OSError, ValueError, TypeError) as exc:
                log(f'Cannot read recovery history: {exc}')
                return 1
            log('=== Osiris modular run starting ===')
            reporter = Reporter(ROOT, [j['name'] for j in jobs], attempts, history)
            results = {}
            for job in jobs:
                name = job['name']
                if any(not results[dep] for dep in job.get('requires', [])):
                    log(f'HELD BACK: {name} — dependency failed')
                    results[name] = False
                    reporter.record(job, 'blocked', 'Dependencies failed: ' + ', '.join(dep for dep in job.get('requires', []) if not results[dep]))
                    continue
                recovered = False
                healthy = check(job) if job.get('check') else False
                if not healthy and job.get('action'):
                    now = time.time()
                    if limit(job, history, now) is not None:
                        reason = f'Restart limit reached: {job.get("max_attempts", 3)} attempts within {job.get("attempt_window", 3600)}s; automatic recovery paused'
                        log(f'FAILED: {name} — {reason}')
                        results[name] = False
                        reporter.record(job, 'failed', reason)
                        continue
                    last = attempts.get(name, 0)
                    if time.time() - last < job.get('cooldown', 0):
                        log(f'FAILED: {name} — recovery cooldown active')
                        results[name] = False
                        reporter.record(job, 'failed', 'Check failed; recovery cooldown active')
                        continue
                    # Persist before executing, so interrupted/failed actions count too.
                    history[name] = recent(job, history, now) + [now]
                    from notifications import private_json
                    private_json(ROOT / 'osiris/.attempt-history.json', history)
                    attempts[name] = now
                    temporary = state_path.with_suffix('.tmp')
                    temporary.write_text(json.dumps(attempts))
                    temporary.replace(state_path)
                    log(f'ACTION: {name}')
                    healthy = run(job['action'], job.get('timeout', 60))
                    if healthy and job.get('check'):
                        healthy = check(job)
                    recovered = healthy
                reporter.record(job, 'ok' if healthy else 'failed',
                                'Recovery verified' if recovered else ('Check passed' if healthy else 'Check or recovery failed; see osiris.log'), recovered)
                results[name] = healthy
                log(f'{"OK" if healthy else "FAILED"}: {name}')
            failed = [name for name, ok in results.items() if not ok]
            reporter.finish(failed)
            log(f'=== Osiris finished: {len(failed)} failed/held back ===')
            return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
