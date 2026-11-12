# Osiris Firewatch

**A lightweight, self-hosted Linux watchdog with automated recovery.**

Osiris Firewatch monitors services, detects failures, and performs controlled recovery actions using configurable health checks.

**Version:** v0.2.0-alpha
**OS** Ubuntu, Debian (have yet to test)
**Status:** Experimental

## Features

- Configurable command-based health checks
- Automated recovery actions
- Post-recovery health verification
- Restart limits and cooldown protection
- Dependency-aware monitoring
- Persistent recovery history
- Command timeouts
- Concurrent-run protection
- Discord failure and boot notifications
- Local status and alert history
- Failure simulation and recovery testing
- Optional read-only VPN monitoring

## Specifications

- Roughly 56KB :O

## Requirements

- Linux
- Python 3
- Bash

Docker is optional and only needed for Docker-specific monitoring.

## Installation

Clone this repository and enter the project directory.

Create your configuration:

Copy the example configuration:

    cp osiris/jobs.example.json osiris/jobs.json

Edit jobs.json to match your environment.

Validate the configuration:

    ./osiris-watchdog.sh --dry-run

Run one monitoring cycle:

    ./osiris-watchdog.sh run

WARNING: A normal run executes configured health checks
and may perform recovery actions.

## Configuration

Jobs are defined in osiris/jobs.json.

Each job supports configurable health checks, recovery
commands, timeouts, cooldowns, and restart limits.

Dependencies can be defined using "requires".
Dependency jobs must appear earlier in the configuration.

## Commands

Run monitoring:
    ./osiris-watchdog.sh run

View current status:
    ./osiris-watchdog.sh status

View recent alerts:
    ./osiris-watchdog.sh alerts

Validate configuration:
    ./osiris-watchdog.sh --dry-run

Preview recovery scenarios:
    ./osiris-watchdog.sh recovery-test

Simulate a failure:
    ./osiris-watchdog.sh simulate-failure

Simulate a boot notification:
    ./osiris-watchdog.sh simulate-boot

## Discord Notifications

Firewatch supports Discord webhook notifications
for failures, blocked jobs, and boot events.

Configure Discord:
    ./osiris-watchdog.sh discord-setup

Test Discord:
    ./osiris-watchdog.sh discord-test

Webhook credentials are stored locally in
osiris/discord.json and excluded from Git.

Never publish webhook URLs or private configuration.
## Optional VPN Monitoring

Firewatch includes an optional, read-only VPN monitoring subsystem. It reports failures through the normal Firewatch alert pipeline but does not reconnect, restart, or reconfigure a VPN.

| Provider | Connection | Interface | Routes | Firewall |
| --- | --- | --- | --- | --- |
| Windscribe | Yes | Yes | Yes | Yes |
| WireGuard | Handshake | Yes | Yes | No |
| OpenVPN | systemd unit | Yes | Yes | No |
| Generic | No | Yes | Yes | No |

The generic adapter provides baseline interface and route monitoring for NordVPN, Psiphon, and other VPNs. Provider-specific connection or firewall monitoring requires a dedicated adapter.

Create a local configuration:

```bash
cp osiris/vpn.example.json osiris/vpn.json
```

Test it manually:

```bash
python3 -m osiris.vpn --config osiris/vpn.json
```

To schedule it through Firewatch, add an alert-only job to the `jobs` array in `osiris/jobs.json`:

```json
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
```

Do not add an `action` unless you intentionally develop and test a separate recovery policy. Automatic VPN recovery is not supplied or enabled.

### Generic VPN example

```json
{
  "provider": "generic",
  "interface": "vpn0",
  "route_targets": ["1.1.1.1"],
  "checks": {
    "connection": false,
    "interface": true,
    "routes": true,
    "firewall": false
  }
}
```

Replace `vpn0` with the VPN’s tunnel interface.

### Provider options

For WireGuard, set `provider` to `wireguard` and the interface to `wg0`. The optional `provider_options.max_handshake_age` setting can mark old peer handshakes unhealthy.

For OpenVPN, configure its systemd client unit:

```json
"provider_options": {
  "service_unit": "openvpn-client@example.service"
}
```

Windscribe may require its user runtime directory when Firewatch runs through systemd:

```ini
Environment=XDG_RUNTIME_DIR=/run/user/1000
```

Use the correct numeric user ID for your system.
## Testing

Run the automated test suite:

    cd osiris
    python3 -m unittest discover -v -p 'test_*.py'

## Security

Osiris Firewatch executes trusted commands.

- Never run untrusted configurations.
- Use minimum required permissions.
- Protect Discord webhook credentials.
- Keep runtime state and logs private.
- Test recovery actions before production use.

## Project Status

Osiris Firewatch is purely experimental.
I am not a professional software developer.

The software has been tested in a personal Linux
homelab & virtual machines but has not undergone an independent
security audit.

## License

MIT

ENJOY!!!!!!!!!! :)
```

                      .:--.
                    .+%@@@@*.
                    -@@@@@@@%=
                 .+=  +@@@@@@@#:
                -%@@%- :#@@@@@@@*.
              ,*@@@@@@:  =@@@@@@@%=                       ..,,,,,....,,.      .,:::.         .,.   ,,,,
             =@@@@@@@# .#:.*@@@@@@@%:                    +@@#***#@@@%##,    -#*+++#%#-   :*##%@-:*#%@@@%+
           ,#@@@@@@%- -%@@* -%@@@@@@@*,                 ,@%:    *@@#,     ,%@-     #@%   ,-*@@@*+-,.,=@@@=
          +@@@@@@@* .#@@@@@= .*@@@@@@%, .               %@,    *@@*      .%@%     +@%-     +@@#.      #@@+
        :%@@@@@@%: =@@@@@@@:   :%@@@=  *@+             .+:   .%@@+       .@@@%+-, ..       %@@:      .%@@,
       +@@@@@@@+ ,%@@@@@@%:     .+#. -%@@@#.                :%@@-         -%@@@@@%*:      -@@%       =@@#
      +@@@@@@#, +@@@@@@@=          .*@@@@@@,               -@@%:            ,=*#@@@@+     #@@=       #@@=
      %@@@@@- :%@@@@@@#,          =@@@@@@@#.              =@@%,    +%.  =##,    .*@@*    .@@@,      ,@@%.
      -@@@*..*@@@@@@%-          :#@@@@@@@*.              *@@*     =@*  =@@=      =@@,    +@@*       +@@+
       :%+ ,@@@@@@@*          .*@@@@@@@%:            ,:-%@@@:,::-*@%.  =@@*:,.,:*@*,  ,:=@@@#:,  ,:=@@@*:.
           *@@@@@%: =+.      -%@@@@@@@+              +###*******###:    ,+####**=,    =##****#-  +##***##-
           :@@@@+ ,#@@%-   :#@@@@@@@#,
            .*@- -@@@@@@#, :%@@@@@%-
              ,. *@@@@@@@@+  =@@@*.
                 .+@@@@@@@@%- ,+
                   ,#@@@@@@@@%,
                     -%@@@@@%-

                                              zaycarish - zsn software *
                                                       2026
```
