import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from recovery_test import plan


class RecoveryPlanTests(unittest.TestCase):
    def test_scenarios_have_no_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'osiris').mkdir()
            state = root / 'osiris/.recovery.json'
            state.write_text(json.dumps({'app': 100}))
            jobs = [{'name': 'mount', 'check': ['mountpoint', '/media']},
                    {'name': 'app', 'requires': ['mount'], 'check': ['check-app'],
                     'action': ['restart-app'], 'cooldown': 900}]
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with patch('subprocess.Popen', side_effect=AssertionError('must not execute')):
                self.assertIn('WOULD RUN: restart-app', plan(root, jobs, ['app'], now=2000))
                self.assertIn('COOLDOWN', plan(root, jobs, ['app'], now=101))
                self.assertIn('app: BLOCKED by mount', plan(root, jobs, ['mount'], now=2000))
                self.assertIn('Simulated result: FAILED', plan(root, jobs, ['app'], True, now=2000))
                with self.assertRaises(ValueError):
                    plan(root, jobs, ['missing'])
            after = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before, after)
