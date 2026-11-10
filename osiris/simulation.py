#!/usr/bin/env python3
"""One-shot synthetic check failure; never touches containers or services."""
from pathlib import Path
import sys


def check(root):
    marker = root / 'osiris/.simulate-failure'
    try:
        marker.unlink()
    except FileNotFoundError:
        print('Simulation check healthy')
        return 0
    print('SIMULATED FAILURE: intentional alert test; next check will pass')
    return 1


if __name__ == '__main__':
    sys.exit(check(Path(__file__).resolve().parent.parent))
