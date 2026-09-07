#!/usr/bin/env python3
from __future__ import annotations

import sys

from homologate import BLOCKED, FAIL, Harness, parse_args


def main() -> int:
    harness = Harness(parse_args())
    result = harness.run()
    if result != 0 or any(check.status == FAIL for check in harness.checks):
        return 1
    if any(check.status == BLOCKED for check in harness.checks):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
