"""Read-only OpenVPN provider adapter."""

import re
from typing import Mapping

from .base import CheckResult, ProviderAdapter


_UNIT_PATTERN = re.compile(r"^[A-Za-z0-9_.@:-]{1,128}$")


class OpenVPNAdapter(ProviderAdapter):
    name = "openvpn"
    supported_checks = frozenset({"connection"})

    def check_connection(self, config: Mapping[str, object]) -> CheckResult:
        unit = config.get("service_unit")
        if not isinstance(unit, str) or not _UNIT_PATTERN.fullmatch(unit):
            raise ValueError(
                "openvpn service_unit must be a valid systemd unit name"
            )

        systemctl_path = config.get("systemctl_path", "/usr/bin/systemctl")
        if not isinstance(systemctl_path, str) or not systemctl_path:
            raise ValueError("openvpn systemctl_path must be a nonempty string")

        result = self.run_command(
            [systemctl_path, "is-active", "--", unit]
        )
        active = result.returncode == 0 and result.stdout.strip() == "active"

        if active:
            return CheckResult(
                "connection",
                True,
                f"OpenVPN unit {unit} is active",
            )

        state = result.stdout or result.stderr or "unknown"
        return CheckResult(
            "connection",
            False,
            f"OpenVPN unit {unit} is not active: {state[:200]}",
        )
