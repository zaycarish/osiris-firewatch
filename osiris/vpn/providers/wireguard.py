"""Read-only WireGuard provider adapter."""

import time
from typing import Mapping

from .base import CheckResult, ProviderAdapter
from ..system_checks import validate_interface


class WireGuardAdapter(ProviderAdapter):
    name = "wireguard"
    supported_checks = frozenset({"connection"})

    def check_connection(self, config: Mapping[str, object]) -> CheckResult:
        interface = validate_interface(config.get("interface"))
        wg_path = config.get("wg_path", "/usr/bin/wg")
        if not isinstance(wg_path, str) or not wg_path:
            raise ValueError("wireguard wg_path must be a nonempty string")

        result = self.run_command(
            [wg_path, "show", interface, "latest-handshakes"]
        )
        if result.returncode != 0:
            detail = result.stderr or result.stdout or "no diagnostic output"
            return CheckResult(
                "connection",
                False,
                f"WireGuard status command failed: {detail[:200]}",
            )

        handshakes = []
        for line in result.stdout.splitlines():
            fields = line.split()
            if len(fields) >= 2:
                try:
                    handshakes.append(int(fields[-1]))
                except ValueError:
                    continue

        handshakes = [timestamp for timestamp in handshakes if timestamp > 0]
        if not handshakes:
            return CheckResult(
                "connection",
                False,
                f"{interface} has no completed peer handshake",
            )

        max_age = config.get("max_handshake_age")
        if max_age is not None:
            if (
                isinstance(max_age, bool)
                or not isinstance(max_age, (int, float))
                or max_age <= 0
            ):
                raise ValueError("max_handshake_age must be a positive number")

            newest_age = max(0, int(time.time() - max(handshakes)))
            if newest_age > max_age:
                return CheckResult(
                    "connection",
                    False,
                    f"{interface} newest handshake is {newest_age}s old",
                )

        return CheckResult(
            "connection",
            True,
            f"{interface} has a completed peer handshake",
        )
