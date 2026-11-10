import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from notifications import enqueue, flush, configure


class NotificationTests(unittest.TestCase):
    def test_retry_retains_failed_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'osiris').mkdir()
            event = dict(time=1, host='host', job='app', status='failed', reason='failed check')
            enqueue(root, event)
            with patch('notifications.webhook', return_value='configured'), patch('notifications.send', side_effect=ValueError('offline')):
                with self.assertRaises(ValueError):
                    flush(root)
            path = root / 'osiris/.discord-pending.json'
            self.assertEqual(len(json.loads(path.read_text())), 1)
            with patch('notifications.webhook', return_value='configured'), patch('notifications.send') as send:
                flush(root)
                send.assert_called_once()
            self.assertEqual(json.loads(path.read_text()), [])

    def test_private_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'osiris').mkdir()
            with patch('notifications.getpass.getpass', return_value='https://discord.com/api/webhooks/123/token'), patch('builtins.print'):
                configure(root)
            self.assertEqual((root / 'osiris/discord.json').stat().st_mode & 0o777, 0o600)

    def test_queued_recovery_is_discarded_without_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'osiris').mkdir()
            enqueue(root, dict(time=1, host='host', job='app', status='recovered', reason='healthy'))
            with patch('notifications.send') as send:
                flush(root)
                send.assert_not_called()
            self.assertEqual(json.loads((root / 'osiris/.discord-pending.json').read_text()), [])

    def test_boot_once_and_retry(self):
        from notifications import queue_boot
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'osiris').mkdir()
            with patch('notifications.boot_id', return_value='boot-one'):
                queue_boot(root, ['radarr'])
                queue_boot(root, [])
            path = root / 'osiris/.discord-pending.json'
            queue = json.loads(path.read_text())
            self.assertEqual(len(queue), 1)
            self.assertIn('radarr', queue[0]['reason'])
            with patch('notifications.webhook', return_value='configured'), patch('notifications.send', side_effect=ValueError('offline')):
                with self.assertRaises(ValueError):
                    flush(root)
            self.assertEqual(len(json.loads(path.read_text())), 1)
            with patch('notifications.webhook', return_value='configured'), patch('notifications.send') as send:
                flush(root)
                send.assert_called_once()
                self.assertIn('BOOT', send.call_args.args[1])
            with patch('notifications.boot_id', return_value='boot-one'):
                queue_boot(root, [])
            self.assertEqual(json.loads(path.read_text()), [])
            with patch('notifications.boot_id', return_value='boot-two'):
                queue_boot(root, [])
            self.assertEqual(len(json.loads(path.read_text())), 1)
