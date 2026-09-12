#!/usr/bin/env bash
# One-time container setup for the specify-powerpack homologation environment.
set -euo pipefail

python -m pip install -U pip
python -m pip install -e ".[dev]"
python -m pip install "git+https://github.com/github/spec-kit.git@v1.0.4"

# The Codex CLI is a standalone binary that arrives through the ~/.codex bind
# mount (if the host has it). Expose it on PATH.
codex_bin="$HOME/.codex/packages/standalone/current/bin/codex"
if [ -x "$codex_bin" ]; then
  mkdir -p "$HOME/.local/bin"
  ln -sf "$codex_bin" "$HOME/.local/bin/codex"
fi

echo "== homologation environment =="
specify-powerpack --version || true
specify --help >/dev/null 2>&1 && echo "specify: OK" || echo "specify: MISSING"
if command -v codex >/dev/null 2>&1; then
  codex --version
else
  echo "codex: MISSING — on the host run 'codex login' (creates ~/.codex), or 'npm i -g @openai/codex'"
fi
gh auth status 2>&1 | sed 's/^/gh: /' || echo "gh: not logged in — run 'gh auth login' on the host"

cat <<'EOF'

Ready. To homologate PR #15 of this repo:
  specify-powerpack review project discover           # copy the g-p-… id
  bash .devcontainer/homologate.sh 15 --project g-p-…

Evidence lands in specs/001-single-skill-baseline/T025-evidence/.
EOF
