from __future__ import annotations

import sys
from pathlib import Path

COMMON = Path(__file__).resolve().parents[1] / "common"
sys.path.insert(0, str(COMMON))

from doctor import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["--launcher-runtime", "py", *sys.argv[1:]]))
