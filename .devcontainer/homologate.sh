#!/usr/bin/env bash
#
# Reproduce the T025 `implement-review` homologation against a GitHub PR:
# installs PowerPack into a throwaway worktree at the PR head, binds a ChatGPT
# Project, runs the T025-validation-runbook offline + live stages, and drops the
# evidence under specs/001-single-skill-baseline/T025-evidence/.
#
# Usage:
#   bash .devcontainer/homologate.sh <PR-number> [--project <id|name>] [--timeout <seconds>]
#
# Prerequisites (see .devcontainer/README.md):
#   - `codex login` done on the host (~/.codex/auth.json present, bind-mounted)
#   - `gh auth login` done (~/.config/gh bind-mounted)
#   - the GitHub Codex App connected in ChatGPT/Codex
#   - a ChatGPT Project to bind (list them with: specify-powerpack review project discover)
#
set -euo pipefail

PR="${1:?usage: homologate.sh <PR-number> [--project <id|name>] [--timeout <seconds>]}"
shift || true
PROJECT=""
TIMEOUT=3300
while [ "$#" -gt 0 ]; do
  case "$1" in
    --project) PROJECT="${2:?}"; shift 2 ;;
    --timeout) TIMEOUT="${2:?}"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
FEATURE="specs/001-single-skill-baseline"
EVID="$REPO_ROOT/$FEATURE/T025-evidence"
WORKROOT="$(mktemp -d)"
WT="$WORKROOT/pp"
mkdir -p "$EVID"

cleanup() { git worktree remove --force "$WT" >/dev/null 2>&1 || true; rm -rf "$WORKROOT"; }
trap cleanup EXIT

echo "== resolve PR #$PR =="
CANON="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
HEAD_SHA="$(gh pr view "$PR" --json headRefOid -q .headRefOid)"
git fetch --quiet origin "pull/$PR/head" || git fetch --quiet origin
git cat-file -e "$HEAD_SHA^{commit}" 2>/dev/null || { echo "PR head $HEAD_SHA not reachable after fetch" >&2; exit 1; }
echo "  $CANON  head=$HEAD_SHA"

echo "== worktree at PR head =="
git worktree add --detach "$WT" "$HEAD_SHA"
git -C "$WT" checkout -B "homologate-pr-$PR" >/dev/null
# the GitHub connector matches the canonical repo name, not a stale rename
git -C "$WT" remote set-url origin "https://github.com/$CANON.git"

echo "== install PowerPack + bind Project =="
specify-powerpack install "$WT" --integration codex
if [ -n "$PROJECT" ]; then
  specify-powerpack review setup --path "$WT" --project "$PROJECT"
fi
specify-powerpack doctor "$WT" --strict-review 2>&1 | tee "$EVID/S1-doctor.txt" || true
specify-powerpack review status --path "$WT" --live 2>&1 | tee "$EVID/S1-review-status.txt" || true

echo "== offline evidence (runbook §3) =="
PYTHON=python3 PYTEST="python -m pytest" \
  bash "$REPO_ROOT/$FEATURE/collect-t025-offline-evidence.sh" "$WT" "$FEATURE" \
  2>&1 | tee "$EVID/_collector-run.txt" || true

echo "== S6 browserless deep review (PR #$PR, timeout ${TIMEOUT}s) =="
SPECIFY_FEATURE="001-single-skill-baseline" \
  specify-powerpack review run --path "$WT" --pr "$PR" \
    --prompt "Perform the complete Deep Review Evidence Protocol." \
    --output "$WT/review.json" --timeout "$TIMEOUT" \
  2>&1 | tee "$EVID/S6-review-run.txt"

cp "$WT/review.json" "$EVID/review.json"
echo "== S7 protocol validation =="
python "$WT/.specify/powerpack/bin/review_protocol.py" validate --input "$EVID/review.json" \
  2>&1 | tee "$EVID/S7-protocol-validate.txt"

echo
echo "== verdict =="
python3 -c "import json; d=json.load(open('$EVID/review.json')); print(d['verdict']); print(d.get('summary',''))"
echo "Evidence: $FEATURE/T025-evidence/  — update RESULT.md and hand review.json back to close the tasks."
