# Osiris Firewatch — VPN Monitor

Optional, modular, read-only VPN health monitoring for Linux.

## Supported adapters

- Windscribe: connection and firewall status
- WireGuard: peer handshake status
- OpenVPN: systemd service status
- Generic: interface and routing checks only

## Available checks

- Connection: provider-specific status
- Interface: verifies the configured interface is UP
- Routes: verifies selected IP destinations route through the VPN
- Firewall: provider-specific protection status, where supported

## Configuration

Create a JSON configuration based on this example:

{
  "provider": "generic",
  "interface": "tun0",
  "route_targets": ["1.1.1.1"],
  "checks": {
    "connection": false,
    "interface": true,
    "routes": true,
    "firewall": false
  }
}

Provider-specific settings belong in "provider_options".

WireGuard supports "max_handshake_age".
OpenVPN requires "service_unit".
Windscribe supports "cli_path".

## Standalone usage

From the Firewatch project root:

python3 -m osiris.vpn --config osiris/vpn.json

Exit codes:

0 = healthy
1 = health check failed
2 = configuration error

## Firewatch integration

Add an optional check-only job to jobs.json:

{
  "name": "vpn",
  "check": [
    "python3",
    "-m",
    "osiris.vpn",
    "--config",
    "osiris/vpn.json"
  ],
  "timeout": 30
}

Remove this job to disable VPN monitoring.

Do not configure a recovery action unless you explicitly
intend to permit automated VPN recovery.

## Privacy

The VPN monitor does not capture network packets,
inspect browsing activity, or collect VPN traffic contents.

It reads local operational status and routing information.

Firewatch may store health results locally and send
failure notifications through configured services.

## Limitations

- Routing checks examine configured destinations only.
- Interface UP does not guarantee working connectivity.
- WireGuard handshakes do not guarantee current connectivity.
- OpenVPN service status does not guarantee tunnel health.
- DNS and IPv6 leak detection are not implemented.
- Automatic VPN recovery is disabled by default.
