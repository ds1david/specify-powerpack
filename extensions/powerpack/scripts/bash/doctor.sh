#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
python_bin="$(command -v python3 || command -v python || true)"
if [[ -z "$python_bin" ]]; then
  echo "PowerPack doctor requires Python, which is also required by Spec Kit." >&2
  exit 127
fi
exec "$python_bin" "$script_dir/../common/doctor.py" --launcher-runtime sh "$@"
