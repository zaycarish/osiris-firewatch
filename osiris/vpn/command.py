"""Safe subprocess helper for read-only VPN checks."""

import subprocess
from typing import Sequence

from .providers.base import CommandResult


def run_command(command: Sequence[str], timeout: float = 15) -> CommandResult:
    if not command or not all(isinstance(part, str) and part for part in command):
        raise ValueError("command must be a nonempty sequence of strings")

    try:
        completed = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return CommandResult(
            completed.returncode,
            completed.stdout.strip(),
            completed.stderr.strip(),
        )
    except subprocess.TimeoutExpired:
        return CommandResult(124, "", f"command timed out after {timeout}s")
    except OSError as error:
        return CommandResult(127, "", str(error))
