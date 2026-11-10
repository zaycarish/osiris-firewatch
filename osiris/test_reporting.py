import json
from pathlib import Path
import tempfile
import unittest
from reporting import Reporter


class ReportingTests(unittest.TestCase):
    def test_transitions_and_duplicate_suppression(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'osiris').mkdir()
            job = {'name': 'app', 'cooldown': 900}
            for status in ['failed', 'failed', 'ok', 'ok']:
                reporter = Reporter(root, ['app'], {'app': 100})
                reporter.record(job, status, 'Check passed' if status == 'ok' else 'Check failed')
                reporter.finish(['app'] if status != 'ok' else [])
            alerts = [json.loads(line) for line in (root / 'osiris/alerts.jsonl').read_text().splitlines()]
            self.assertEqual([a['status'] for a in alerts], ['failed', 'recovered'])
            state = json.loads((root / 'osiris/status.json').read_text())
            self.assertEqual(state['phase'], 'healthy')
            queued = json.loads((root / 'osiris/.discord-pending.json').read_text())
            self.assertEqual([a['status'] for a in queued if a['status'] != 'boot'], ['failed'])
            self.assertEqual(state['jobs']['app']['next_action'], 1000)

    def test_successful_repair_alert(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'osiris').mkdir()
            reporter = Reporter(root, ['app'], {})
            reporter.record({'name': 'app'}, 'ok', 'Recovery verified', recovered=True)
            event = json.loads((root / 'osiris/alerts.jsonl').read_text())
            self.assertEqual(event['status'], 'recovered')
            self.assertFalse((root / 'osiris/.discord-pending.json').exists())
