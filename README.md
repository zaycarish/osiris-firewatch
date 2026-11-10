# Osiris Firewatch

**A lightweight, self-hosted Linux watchdog with automated recovery.**

Osiris Firewatch monitors services, detects failures, and performs controlled recovery actions using configurable health checks.

**Version:** v0.1.0-alpha
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

Osiris Firewatch v0.1.0-alpha is experimental.

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
