"""Common interface for read-only VPN provider adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


CommandRunner = Callable[[Sequence[str]], CommandResult]


class ProviderAdapter(ABC):
    """Provider-specific, read-only VPN status checks."""

    name = ""
    supported_checks = frozenset({"connection"})

    def __init__(self, run_command: CommandRunner):
        self.run_command = run_command

    def supports(self, check_name: str) -> bool:
        return check_name in self.supported_checks

    @abstractmethod
    def check_connection(self, config: Mapping[str, object]) -> CheckResult:
        """Return the provider's connection state."""

    def check_firewall(self, config: Mapping[str, object]) -> CheckResult:
        raise ValueError(f"{self.name} does not support firewall checks")
