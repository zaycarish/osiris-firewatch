"""Generic adapter for VPNs without provider-specific integration."""

from typing import Mapping

from .base import CheckResult, ProviderAdapter


class GenericAdapter(ProviderAdapter):
    name = "generic"
    supported_checks = frozenset()

    def check_connection(self, config: Mapping[str, object]) -> CheckResult:
        raise ValueError(
            "generic VPN monitoring does not support connection checks"
        )
