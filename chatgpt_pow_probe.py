#!/usr/bin/env python3
"""Standalone entrypoint for the packaged ChatGPT Web probe."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from speckit_powerpack.chatgpt_pow_probe import main


if __name__ == "__main__":
    raise SystemExit(main())
