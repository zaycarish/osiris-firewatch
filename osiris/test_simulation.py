import json
from pathlib import Path
import subprocess
import tempfile
import unittest


class SimulationTests(unittest.TestCase):
    def test_failure_and_recovery_through_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'osiris'
            folder.mkdir()
            for filename in ['runner.py', 'reporting.py', 'notifications.py', 'simulation.py', 'restart_limits.py']:
                (folder / filename).write_text(Path(__file__).with_name(filename).read_text())
            (folder / 'jobs.json').write_text(json.dumps({'jobs': [{'name': 'simulation', 'check': ['python3', 'osiris/simulation.py']}]}))
            def run(*args):
                return subprocess.run(['python3', str(folder / 'runner.py'), *args], capture_output=True, text=True)
            self.assertEqual(run('simulate-failure').returncode, 0)
            self.assertEqual(run().returncode, 1)
            self.assertEqual(run().returncode, 0)
            self.assertEqual(run().returncode, 0)
            alerts = [json.loads(line) for line in (folder / 'alerts.jsonl').read_text().splitlines()]
            self.assertEqual([a['status'] for a in alerts], ['failed', 'recovered'])
            self.assertFalse((folder / '.simulate-failure').exists())
