"""Discord notification configuration and durable delivery queue."""
import getpass
import json
import os
import re
import socket
import time
import urllib.error
import urllib.request


def private_json(path, value):
    temporary = path.with_suffix('.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream)
    temporary.replace(path)


def webhook(root):
    path = root / 'osiris/discord.json'
    if not path.exists():
        return None
    url = json.loads(path.read_text())['webhook_url']
    if not isinstance(url, str) or not re.fullmatch(r'https://discord\.com/api(?:/v\d+)?/webhooks/\d+/[A-Za-z0-9_-]+', url):
        raise ValueError('Invalid Discord webhook URL; run discord-setup again')
    return url


def send(root, content):
    url = webhook(root)
    if not url:
        raise ValueError('Discord is not configured; run discord-setup first')
    request = urllib.request.Request(url + '?wait=true',
        data=json.dumps({'content': content[:2000], 'allowed_mentions': {'parse': []}}).encode(),
        headers={'Content-Type': 'application/json', 'User-Agent': 'Osiris/1.0'}, method='POST')
    # Do not follow redirects carrying the private webhook token.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                raise ValueError('Discord did not accept the message')
    except urllib.error.HTTPError as exc:
        raise ValueError(f'Discord returned HTTP {exc.code}; notification not delivered') from None
    except (OSError, urllib.error.URLError):
        raise ValueError('Discord connection failed; notification not delivered') from None


def configure(root):
    url = getpass.getpass('Paste Discord webhook URL (hidden): ').strip()
    if not re.fullmatch(r'https://discord\.com/api(?:/v\d+)?/webhooks/\d+/[A-Za-z0-9_-]+', url):
        raise ValueError('Expected a Discord webhook URL copied from Discord')
    private_json(root / 'osiris/discord.json', {'webhook_url': url})
    print('Discord webhook saved privately. Run discord-test to send a test message.')


def enqueue(root, event):
    path = root / 'osiris/.discord-pending.json'
    queue = json.loads(path.read_text()) if path.exists() else []
    queue.append(event)
    private_json(path, queue)


def flush(root):
    path = root / 'osiris/.discord-pending.json'
    if not path.exists():
        return
    queue = json.loads(path.read_text())
    failures = [event for event in queue if event.get('status') in ('failed', 'blocked', 'boot')]
    if len(failures) != len(queue):
        private_json(path, failures)
    queue = failures
    if not queue or not webhook(root):
        return
    # One bounded batch per run; remaining events stay queued for later runs.
    batch = queue[:8]
    lines = []
    for event in batch:
        stamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event['time']))
        lines.append(f"{stamp} [{event['host']}] {event['job']}: {event['status'].upper()} — {event['reason']}"[:240])
    send(root, '\n'.join(lines))
    private_json(path, queue[len(batch):])


def boot_id():
    from pathlib import Path
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def queue_boot(root, failed):
    """Queue once per Linux boot, after checks finish; retry through normal delivery."""
    current = boot_id()
    marker = root / 'osiris/.boot-notified.json'
    previous = json.loads(marker.read_text()) if marker.exists() else {}
    if previous.get('boot_id') == current:
        return
    path = root / 'osiris/.discord-pending.json'
    queue = json.loads(path.read_text()) if path.exists() else []
    if not any(event.get('boot_id') == current for event in queue):
        summary = ('Checks completed: all configured jobs passed.' if not failed else
                   f'Checks completed: {len(failed)} failed or blocked: ' + ', '.join(failed))
        event = dict(time=time.time(), host=socket.gethostname(), job='host', status='boot',
                     boot_id=current, reason='Host back online after boot. ' + summary)
        enqueue(root, event)
    # Mark only after the durable event exists; failed sends remain queued.
    private_json(marker, {'boot_id': current})
