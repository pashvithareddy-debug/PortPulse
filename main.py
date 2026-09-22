#!/usr/bin/env python3
"""Entry point for running PortPulse directly: python3 main.py <command>."""

import sys

from portpulse.cli import main

if __name__ == "__main__":
    sys.exit(main())
