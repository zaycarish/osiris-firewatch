"""Provider-neutral, read-only VPN interface and route checks."""

import ipaddress
import re
from typing import Sequence

from .providers.base import CheckResult, CommandRunner


_INTERFACE_PATTERN = re.compile(r"^[A-Za-z0-9_.:@-]{1,64}$")


def validate_interface(interface: object) -> str:
    if not isinstance(interface, str) or not _INTERFACE_PATTERN.fullmatch(interface):
        raise ValueError("interface must be a valid nonempty Linux interface name")
    return interface


def check_interface(run_command: CommandRunner, interface: object) -> CheckResult:
    name = validate_interface(interface)
    result = run_command(["ip", "-o", "link", "show", "dev", name])

    if result.returncode != 0:
        detail = result.stderr or result.stdout or "interface not found"
        return CheckResult("interface", False, f"{name}: {detail[:200]}")

    flags_start = result.stdout.find("<")
    flags_end = result.stdout.find(">", flags_start + 1)
    flags = set()
    if flags_start >= 0 and flags_end > flags_start:
        flags = set(result.stdout[flags_start + 1:flags_end].split(","))

    is_up = "UP" in flags
    detail = f"{name} is UP" if is_up else f"{name} exists but is not UP"
    return CheckResult("interface", is_up, detail)


def check_routes(
    run_command: CommandRunner,
    interface: object,
    targets: Sequence[object],
) -> CheckResult:
    name = validate_interface(interface)
    if not isinstance(targets, list) or not targets:
        raise ValueError("route_targets must be a nonempty list")

    failures = []
    for value in targets:
        if not isinstance(value, str):
            raise ValueError("each route target must be an IP address string")

        try:
            address = ipaddress.ip_address(value)
        except ValueError as error:
            raise ValueError(f"invalid route target: {value}") from error

        family = "-4" if address.version == 4 else "-6"
        result = run_command(["ip", family, "route", "get", value])
        tokens = result.stdout.split()
        uses_interface = any(
            tokens[index] == "dev" and tokens[index + 1] == name
            for index in range(len(tokens) - 1)
        )

        if result.returncode != 0 or not uses_interface:
            failures.append(value)

    if failures:
        return CheckResult(
            "routes",
            False,
            f"routes not using {name}: {', '.join(failures)}",
        )

    return CheckResult(
        "routes",
        True,
        f"{len(targets)} route target(s) use {name}",
    )
