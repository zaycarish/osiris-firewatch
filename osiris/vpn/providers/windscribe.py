"""Read-only Windscribe provider adapter."""

from typing import Mapping, Optional

from .base import CheckResult, CommandResult, ProviderAdapter


class WindscribeAdapter(ProviderAdapter):
    name = "windscribe"
    supported_checks = frozenset({"connection", "firewall"})

    def __init__(self, run_command):
        super().__init__(run_command)
        self._cached_status: Optional[CommandResult] = None

    def _status(self, config: Mapping[str, object]) -> CommandResult:
        cli_path = config.get("cli_path", "/usr/bin/windscribe-cli")
        if not isinstance(cli_path, str) or not cli_path:
            raise ValueError("windscribe cli_path must be a nonempty string")

        if self._cached_status is None:
            self._cached_status = self.run_command([cli_path, "status"])
        return self._cached_status

    @staticmethod
    def _failure(result: CommandResult) -> str:
        detail = result.stderr or result.stdout or "no diagnostic output"
        return f"Windscribe status command failed: {detail[:200]}"

    def check_connection(self, config: Mapping[str, object]) -> CheckResult:
        result = self._status(config)
        if result.returncode != 0:
            return CheckResult("connection", False, self._failure(result))

        connected = "Connect state: Connected:" in result.stdout
        detail = "Windscribe connected" if connected else "Windscribe disconnected"
        return CheckResult("connection", connected, detail)

    def check_firewall(self, config: Mapping[str, object]) -> CheckResult:
        result = self._status(config)
        if result.returncode != 0:
            return CheckResult("firewall", False, self._failure(result))

        enabled = "Firewall state: On" in result.stdout
        detail = "Windscribe firewall on" if enabled else "Windscribe firewall disabled"
        return CheckResult("firewall", enabled, detail)
