"""Registry of supported VPN provider adapters."""

from typing import Mapping, Type

from .base import CommandRunner, ProviderAdapter
from .generic import GenericAdapter
from .openvpn import OpenVPNAdapter
from .windscribe import WindscribeAdapter
from .wireguard import WireGuardAdapter


ADAPTERS: Mapping[str, Type[ProviderAdapter]] = {
    "generic": GenericAdapter,
    "openvpn": OpenVPNAdapter,
    "windscribe": WindscribeAdapter,
    "wireguard": WireGuardAdapter,
}


def create_adapter(
    provider: object,
    run_command: CommandRunner,
) -> ProviderAdapter:
    if not isinstance(provider, str):
        raise ValueError("provider must be a string")

    name = provider.strip().lower()
    adapter_class = ADAPTERS.get(name)
    if adapter_class is None:
        supported = ", ".join(sorted(ADAPTERS))
        raise ValueError(
            f"unsupported VPN provider {provider!r}; supported: {supported}"
        )

    return adapter_class(run_command)
