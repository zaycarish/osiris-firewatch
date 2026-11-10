"""Read-only recovery planning with explicitly simulated check outcomes."""
import json
import math
import shlex
import time
from restart_limits import load_history, limit


def plan(root, jobs, failures, recovery_fails=False, now=None):
    names = {job['name'] for job in jobs}
    unknown = set(failures) - names
    if unknown:
        raise ValueError('Unknown job(s): ' + ', '.join(sorted(unknown)))
    if not failures:
        raise ValueError('Specify at least one failing job using --fail NAME')
    path = root / 'osiris/.recovery.json'
    attempts = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(attempts, dict):
        raise ValueError('Invalid recovery state')
    now = time.time() if now is None else now
    history = load_history(root, attempts)
    results = {}
    lines = ['RECOVERY DRY RUN — no commands, state changes, or notifications.',
             'Assumptions: unselected checks pass; recovery ' + ('fails.' if recovery_fails else 'succeeds.'),
             'This is a scenario preview, not a live health check.']
    for job in jobs:
        name = job['name']
        blocked = [dep for dep in job.get('requires', []) if not results[dep]]
        if blocked:
            results[name] = False
            lines.append(f'{name}: BLOCKED by ' + ', '.join(blocked))
            continue
        if name not in failures and job.get('check'):
            results[name] = True
            lines.append(f'{name}: PASS (assumed)')
            continue
        if job.get('check'):
            lines.append(f'{name}: FAIL (simulated); check: ' + shlex.join(job['check']))
            lines.append(f'  Retry window: {job.get("wait", 0)}s; command timeout: {job.get("timeout", 60)}s')
        if not job.get('action'):
            results[name] = False
            lines.append('  No recovery action configured; would report failure.')
            continue
        unlock = limit(job, history, now)
        if unlock is not None:
            results[name] = False
            lines.append(f'  RESTART LIMIT: action blocked for another {math.ceil(unlock - now)}s')
            continue
        last = attempts.get(name, 0)
        if not isinstance(last, (float, int)) or not math.isfinite(last):
            raise ValueError(f'Invalid recovery timestamp for {name}')
        remaining = max(0, last + job.get('cooldown', 0) - now)
        if remaining:
            results[name] = False
            lines.append(f'  COOLDOWN: action blocked for another {math.ceil(remaining)}s')
            continue
        lines.append('  WOULD RUN: ' + shlex.join(job['action']))
        if job.get('check'):
            lines.append('  WOULD VERIFY: ' + shlex.join(job['check']))
        results[name] = not recovery_fails
        lines.append('  Simulated result: ' + ('FAILED; would report failure.' if recovery_fails else 'RECOVERED; Discord recovery alert suppressed.'))
    failed = [name for name, passed in results.items() if not passed]
    lines.append(f'Scenario result: {len(failed)} failed/blocked' + (': ' + ', '.join(failed) if failed else ''))
    lines.append('No Discord messages sent. Normal failure alerts would follow transition deduplication.')
    return '\n'.join(lines)
