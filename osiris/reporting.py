"""Persistent run status and transition alerts; no commands run when viewing status."""
import json
from pathlib import Path
import socket
import time
from notifications import enqueue, flush, queue_boot
from restart_limits import recent, limit


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def read_status(root):
    try:
        return json.loads((root / 'osiris/status.json').read_text())
    except FileNotFoundError:
        return {}


def show_status(root, raw=False):
    state = read_status(root)
    if raw:
        print(json.dumps(state, indent=2))
        return 0
    if not state:
        print('No recorded checks yet. Results appear after the next Osiris run.')
        return 0
    def stamp(value):
        return time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime(value)) if value else 'never'
    print(f"Osiris: {state['phase']} | started {stamp(state['started'])}")
    print(f"Last completed run: {stamp(state.get('completed'))}")
    if state.get('notification_error'):
        print(state['notification_error'])
    print(f"Snapshot age: {int(max(0, time.time() - state['updated']))} seconds")
    print(f"{'JOB':20} {'STATUS':12} {'CHECKED':24} DETAILS")
    for name, job in state.get('jobs', {}).items():
        print(f"{name:20} {job['status']:12} {stamp(job.get('checked')):24} {job['reason']}")
        if job.get('attempt_count'):
            print(f"  Recovery attempts in window: {job['attempt_count']}/{job['max_attempts']}")
        if job.get('restart_locked_until'):
            print(f"  Restart limit releases: {stamp(job['restart_locked_until'])}")
        if job.get('last_action'):
            print(f"  Last recovery attempt: {stamp(job['last_action'])}; eligible again: {stamp(job['next_action'])}")
    return 0


class Reporter:
    def __init__(self, root, names, attempts, history=None):
        self.root = root
        self.previous = read_status(root).get('jobs', {})
        now = time.time()
        self.state = dict(phase='running', started=now, updated=now, completed=None,
                          jobs={name: dict(status='pending', reason='Waiting for this run', checked=None)
                                for name in names})
        self.attempts = attempts
        self.history = history if history is not None else {}
        self.save()

    def save(self):
        self.state['updated'] = time.time()
        write_json(self.root / 'osiris/status.json', self.state)

    def record(self, job, status, reason, recovered=False):
        name = job['name']
        last = self.attempts.get(name)
        row = dict(status=status, reason=reason, checked=time.time(), last_action=last,
                   next_action=last + job.get('cooldown', 0) if last else None)
        unlock = limit(job, self.history, time.time())
        row['attempt_count'] = len(recent(job, self.history, time.time()))
        row['max_attempts'] = job.get('max_attempts', 3)
        row['restart_locked_until'] = unlock
        if unlock:
            row['next_action'] = max(row.get('next_action') or 0, unlock)
        old = self.previous.get(name, {})
        self.state['jobs'][name] = row
        self.save()
        # Persist transitions as each job finishes, even if a later job hangs.
        if status != 'ok' and (old.get('status') != status or old.get('reason') != reason):
            self.alert(name, status, reason)
        elif status == 'ok' and (recovered or old.get('status') in ('failed', 'blocked')):
            self.alert(name, 'recovered', reason)

    def alert(self, name, status, reason):
        event = dict(time=time.time(), host=socket.gethostname(), job=name, status=status, reason=reason)
        with (self.root / 'osiris/alerts.jsonl').open('a') as stream:
            stream.write(json.dumps(event) + '\n')
        if status in ('failed', 'blocked'):
            enqueue(self.root, event)

    def finish(self, failed):
        self.state['phase'] = 'failed' if failed else 'healthy'
        self.state['completed'] = time.time()
        try:
            queue_boot(self.root, failed)
            flush(self.root)
            self.state['notification_error'] = None
        except (OSError, ValueError, KeyError) as exc:
            # Never print exception text: it may contain a secret URL.
            self.state['notification_error'] = 'Discord delivery failed; alerts remain queued. Run discord-test to diagnose.'
            print(self.state['notification_error'], flush=True)
        self.save()
