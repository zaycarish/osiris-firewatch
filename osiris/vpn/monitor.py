"""Provider-neutral orchestration for read-only VPN health checks."""

from typing import List, Mapping

from .command import run_command
from .providers import create_adapter
from .providers.base import CheckResult, CommandRunner
from .system_checks import check_interface, check_routes


CHECK_ORDER = ("connection", "interface", "routes", "firewall")
DEFAULT_CHECKS = {
    "connection": True,
    "interface": True,
    "routes": True,
    "firewall": False,
}


def run_checks(
    config: Mapping[str, object],
    command_runner: CommandRunner = run_command,
) -> List[CheckResult]:
    if not isinstance(config, Mapping):
        raise ValueError("VPN configuration must be an object")

    adapter = create_adapter(config.get("provider"), command_runner)

    checks = config.get("checks", DEFAULT_CHECKS)
    if not isinstance(checks, Mapping):
        raise ValueError("checks must be an object")

    unknown = set(checks) - set(CHECK_ORDER)
    if unknown:
        raise ValueError(f"unknown checks: {', '.join(sorted(unknown))}")

    enabled = {}
    for name in CHECK_ORDER:
        value = checks.get(name, DEFAULT_CHECKS[name])
        if not isinstance(value, bool):
            raise ValueError(f"checks.{name} must be true or false")
        enabled[name] = value

    if not any(enabled.values()):
        raise ValueError("at least one VPN check must be enabled")

    for name in ("connection", "firewall"):
        if enabled[name] and not adapter.supports(name):
            raise ValueError(
                f"{adapter.name} does not support the {name} check"
            )

    options = config.get("provider_options", {})
    if not isinstance(options, Mapping):
        raise ValueError("provider_options must be an object")

    adapter_config = dict(options)
    adapter_config["interface"] = config.get("interface")

    results = []
    for name in CHECK_ORDER:
        if not enabled[name]:
            continue

        if name == "connection":
            result = adapter.check_connection(adapter_config)
        elif name == "interface":
            result = check_interface(
                command_runner,
                config.get("interface"),
            )
        elif name == "routes":
            result = check_routes(
                command_runner,
                config.get("interface"),
                config.get("route_targets"),
            )
        else:
            result = adapter.check_firewall(adapter_config)

        results.append(result)

    return results
