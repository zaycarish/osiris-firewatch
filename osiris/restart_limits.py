"""Persistent rolling-window recovery limits shared by runner and dry run."""
import json
import math


def load_history(root, attempts):
    path = root / 'osiris/.attempt-history.json'
    history = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(history, dict):
        raise ValueError('Invalid recovery history')
    # Preserve the last attempt recorded before rolling-window protection existed.
    for name, last in attempts.items():
        if name not in history:
            history[name] = [last]
    for values in history.values():
        if not isinstance(values, list) or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
            raise ValueError('Invalid recovery history timestamps')
    return history


def recent(job, history, now):
    return sorted(t for t in history.get(job['name'], []) if t > now - job.get('attempt_window', 3600))


def limit(job, history, now):
    values = recent(job, history, now)
    maximum = job.get('max_attempts', 3)
    if len(values) < maximum:
        return None
    return values[-maximum] + job.get('attempt_window', 3600)
