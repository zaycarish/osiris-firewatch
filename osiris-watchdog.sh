#!/usr/bin/env bash
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$ROOT/osiris/runner.py" "$@"
