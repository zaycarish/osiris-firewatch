import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('container_health', Path(__file__).with_name('container.py'))
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)


def result(code=0, output=''):
    return subprocess.CompletedProcess([], code, output, '')


class HealthTests(unittest.TestCase):
    def call(self, args, replies):
        with patch('sys.argv', ['container.py', *args]), patch.object(health, 'docker', side_effect=replies) as docker:
            status = health.main()
            return status, docker.call_args_list

    def test_daemon_failure_never_recovers(self):
        status, calls = self.call(['recover', 'app'], [result(1)])
        self.assertEqual(status, 1)
        self.assertEqual(len(calls), 1)

    def test_unhealthy(self):
        state = json.dumps([{'State': {'Running': True, 'Health': {'Status': 'unhealthy'}}}])
        status, _ = self.call(['check', 'app'], [result(), result(output=state)])
        self.assertEqual(status, 1)

    def test_restart_only_affected_container(self):
        status, calls = self.call(['recover', 'app'], [result(), result(output='[]'), result()])
        self.assertEqual(status, 0)
        self.assertEqual(calls[-1].args, ('restart', '--timeout', '20', 'app'))

    def test_create_missing_without_dependencies(self):
        status, calls = self.call(['recover', 'app'], [result(), result(1), result()])
        self.assertEqual(status, 0)
        self.assertEqual(calls[-1].args, ('compose', 'up', '-d', '--no-deps', 'app'))

    def test_cooldown_persists_across_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'osiris').mkdir()
            runner = root / 'osiris/runner.py'
            (root / 'osiris/reporting.py').write_text(Path(__file__).with_name('reporting.py').read_text())
            (root / 'osiris/notifications.py').write_text(Path(__file__).with_name('notifications.py').read_text())
            (root / 'osiris/restart_limits.py').write_text(Path(__file__).with_name('restart_limits.py').read_text())
            runner.write_text(Path(__file__).with_name('runner.py').read_text())
            action = root / 'actions'
            config = {'jobs': [{'name': 'broken', 'check': ['false'],
                                'action': ['sh', '-c', 'echo action >> "$1"', 'sh', str(action)],
                                'cooldown': 900}]}
            (root / 'osiris/jobs.json').write_text(json.dumps(config))
            for _ in range(2):
                run = subprocess.run(['python3', str(runner)], capture_output=True, text=True)
                self.assertEqual(run.returncode, 1)
            self.assertEqual(action.read_text(), 'action\n')
            self.assertIn('cooldown active', run.stdout)


if __name__ == '__main__':
    unittest.main()
