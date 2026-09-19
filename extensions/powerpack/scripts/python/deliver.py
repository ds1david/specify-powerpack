from __future__ import annotations
import shutil
import subprocess
import sys

def main(argv=None):
    target = " ".join(sys.argv[1:] if argv is None else argv).strip()
    if not target:
        print("Usage: deliver.py <existing-spec-id-or-feature-description>", file=sys.stderr)
        return 2
    specify = shutil.which("specify")
    if not specify:
        print("specify CLI was not found on PATH", file=sys.stderr)
        return 127
    return subprocess.run([
        specify, "workflow", "run", "powerpack-delivery",
        "--input", f"target={target}",
        "--input", "integration=auto",
        "--input", "script_runtime=py",
    ], check=False).returncode

if __name__ == "__main__":
    raise SystemExit(main())
