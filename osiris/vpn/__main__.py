#!/usr/bin/env python3
"""Run the optional, read-only Osiris VPN monitor."""

import argparse
import json
from pathlib import Path
import sys

from .monitor import run_checks


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="path to a VPN monitor JSON configuration",
    )
    args = parser.parse_args(argv)

    try:
        config = json.loads(args.config.read_text())
        results = run_checks(config)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        print(f"UNHEALTHY: VPN configuration error: {error}", file=sys.stderr)
        return 2

    for result in results:
        label = "OK" if result.ok else "FAILED"
        print(f"{label}: {result.name} — {result.detail}")

    failed = [result.name for result in results if not result.ok]
    if failed:
        print(f"UNHEALTHY: VPN checks failed: {', '.join(failed)}")
        return 1

    print("HEALTHY: all enabled VPN checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
