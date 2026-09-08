#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PS1="$SCRIPT_DIR/probe_chatgpt_github_cdp_compat.ps1"

if ! command -v powershell.exe >/dev/null 2>&1; then
  echo "ERROR: powershell.exe is unavailable. This launcher is intended for WSL with Windows PowerShell available." >&2
  exit 2
fi

if ! command -v wslpath >/dev/null 2>&1; then
  echo "ERROR: wslpath is unavailable; run the compatibility .ps1 directly from Windows PowerShell instead." >&2
  exit 2
fi

PS1_WIN="$(wslpath -w "$PS1")"

exec powershell.exe \
  -NoProfile \
  -ExecutionPolicy Bypass \
  -File "$PS1_WIN" \
  "$@"
