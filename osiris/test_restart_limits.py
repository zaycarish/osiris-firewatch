import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from restart_limits import limit


class RestartLimitTests(unittest.TestCase):
    def test_window_expiry_and_future_timestamps(self):
        job = {'name': 'app', 'max_attempts': 3, 'attempt_window': 3600}
        history = {'app': [100, 200, 300]}
        self.assertEqual(limit(job, history, 300), 3700)
        self.assertIsNone(limit(job, history, 3700))
        self.assertIsNotNone(limit(job, history, 50))

    def test_only_three_actions_and_healthy_checks_continue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'osiris'
            folder.mkdir()
            for name in ['runner.py', 'reporting.py', 'notifications.py', 'restart_limits.py']:
                (folder / name).write_text(Path(__file__).with_name(name).read_text())
            marker = root / 'healthy'
            actions = root / 'actions'
            config = {'jobs': [{'name': 'app', 'check': ['test', '-f', str(marker)],
                                'action': ['sh', '-c', 'echo attempt >> "$1"; exit 1', 'sh', str(actions)],
                                'max_attempts': 3, 'attempt_window': 3600}]}
            (folder / 'jobs.json').write_text(json.dumps(config))
            def run():
                return subprocess.run(['python3', '-B', str(folder / 'runner.py')], capture_output=True, text=True)
            for _ in range(4):
                result = run()
                self.assertEqual(result.returncode, 1)
            self.assertEqual(len(actions.read_text().splitlines()), 3)
            self.assertIn('Restart limit reached', result.stdout)
            alerts = [json.loads(line) for line in (folder / 'alerts.jsonl').read_text().splitlines()]
            self.assertEqual(sum('Restart limit reached' in e['reason'] for e in alerts), 1)
            run()
            self.assertEqual(len(actions.read_text().splitlines()), 3)
            marker.touch()
            self.assertEqual(run().returncode, 0)
            self.assertEqual(len(actions.read_text().splitlines()), 3)
            marker.unlink()
            (folder / '.attempt-history.json').write_text(json.dumps({'app': [time.time() - 4000] * 3}))
            run()
            self.assertEqual(len(actions.read_text().splitlines()), 4)
