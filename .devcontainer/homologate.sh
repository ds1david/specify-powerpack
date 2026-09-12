#!/usr/bin/env bash
#
# Reproduce the T025 `implement-review` homologation against a GitHub PR:
# installs PowerPack into a throwaway worktree at the PR head, binds a ChatGPT
# Project, runs the T025-validation-runbook offline + live stages, and drops the
# evidence under specs/001-single-skill-baseline/T025-evidence/.
#
# Usage:
#   bash .devcontainer/homologate.sh <PR-number> [--project <id|url>] [--timeout <seconds>]
#
#   --project  the ChatGPT Project id (the `g-p-…` value from
#              `specify-powerpack review project discover`) or its full URL.
#              A bare slug / the old repo name will NOT match.
#
# Prerequisites (see .devcontainer/README.md):
#   - `codex login` done (~/.codex/auth.json present)
#   - `gh auth login` done
#   - the GitHub Codex App connected in ChatGPT/Codex
#
set -euo pipefail

PR="${1:?usage: homologate.sh <PR-number> [--project <id|url>] [--timeout <s>] [--effort <level>] [--model <name>]}"
shift || true
PROJECT=""
TIMEOUT=3300
EFFORT=""   # empty = the CLI default (xhigh, the SPEC reviewer contract)
MODEL=""
KEEP_SESSION=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --project) PROJECT="${2:?}"; shift 2 ;;
    --timeout) TIMEOUT="${2:?}"; shift 2 ;;
    --effort)  EFFORT="${2:?}"; shift 2 ;;   # minimal|low|medium|high|xhigh — lower = fewer tokens
    --model)   MODEL="${2:?}"; shift 2 ;;
    --keep-session) KEEP_SESSION=1; shift ;; # persist the codex turn (Codex web history); against Decision §8
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

# curl-style trace of every backend-api request (method + URL + body, no headers/token)
export SPECKIT_POWERPACK_HTTP_LOG="$EVID/http-requests.log"
: > "$SPECKIT_POWERPACK_HTTP_LOG"

# Always run THIS checkout's code, never a stale globally-installed
# `specify-powerpack` (the package is stdlib-only, so PYTHONPATH is enough).
PP=(env "PYTHONPATH=$REPO_ROOT/src" python3 -m speckit_powerpack)

say() { printf '\n\033[1m== %s\033[0m  (%s)\n' "$*" "$(date -u +%H:%M:%SZ)"; }
cleanup() {
  git worktree remove --force "$WT" >/dev/null 2>&1 || true
  git branch -D "homologate-pr-$PR" >/dev/null 2>&1 || true
  rm -rf "$WORKROOT"
  echo
  echo "evidence dir: $FEATURE/T025-evidence/"
}
trap cleanup EXIT

say "runtime"
echo "  code:    $REPO_ROOT/src (PYTHONPATH)"
"${PP[@]}" --version | sed 's/^/  version: /'
command -v codex >/dev/null && codex --version | sed 's/^/  codex:   /' || echo "  codex:   MISSING"
command -v gh    >/dev/null && gh --version | head -1 | sed 's/^/  gh:      /' || echo "  gh:      MISSING"

say "resolve PR #$PR"
CANON="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
HEAD_SHA="$(gh pr view "$PR" --json headRefOid -q .headRefOid)"
git fetch --quiet origin "pull/$PR/head" || git fetch --quiet origin
git cat-file -e "$HEAD_SHA^{commit}" 2>/dev/null || { echo "PR head $HEAD_SHA not reachable after fetch" >&2; exit 1; }
echo "  $CANON  head=$HEAD_SHA"

say "worktree at PR head"
git worktree add --detach "$WT" "$HEAD_SHA"
git -C "$WT" checkout -B "homologate-pr-$PR" >/dev/null
git -C "$WT" remote set-url origin "https://github.com/$CANON.git"  # connector wants the canonical name

say "install PowerPack"
"${PP[@]}" install "$WT" --integration codex

if [ -n "$PROJECT" ]; then
  say "bind ChatGPT Project"
  "${PP[@]}" review setup --path "$WT" --project "$PROJECT"
else
  echo "  (no --project given; assuming the worktree already carries a binding)"
fi

say "S1 readiness"
"${PP[@]}" doctor "$WT" --strict-review 2>&1 | tee "$EVID/S1-doctor.txt" || true
"${PP[@]}" review status --path "$WT" --live 2>&1 | tee "$EVID/S1-review-status.txt" || true

say "offline evidence (runbook §3)"
if python3 -m pytest --version >/dev/null 2>&1; then
  PYTEST_CMD="python3 -m pytest"
elif command -v uv >/dev/null 2>&1 && uv run --project "$REPO_ROOT" python -m pytest --version >/dev/null 2>&1; then
  PYTEST_CMD="uv run --project $REPO_ROOT python -m pytest"
else
  PYTEST_CMD="skip"   # CI covers the pytest-equivalent check
fi
PYTHON=python3 PYTEST="$PYTEST_CMD" \
  bash "$REPO_ROOT/$FEATURE/collect-t025-offline-evidence.sh" "$WT" "$FEATURE" \
  2>&1 | tee "$EVID/_collector-run.txt" || true

RUN_ARGS=(--path "$WT" --pr "$PR"
          --prompt "Perform the complete Deep Review Evidence Protocol."
          --output "$WT/review.json" --timeout "$TIMEOUT")
[ -n "$EFFORT" ] && RUN_ARGS+=(--effort "$EFFORT")
[ -n "$MODEL" ]  && RUN_ARGS+=(--model "$MODEL")
[ "$KEEP_SESSION" = 1 ] && RUN_ARGS+=(--keep-session)

say "S6 browserless deep review — PR #$PR, timeout ${TIMEOUT}s, effort ${EFFORT:-xhigh}"
echo "  [browserless] = ChatGPT backend-api call · [codex/*] = work inside a codex exec turn."
echo "  Two codex exec turns (snapshot + deep review). Each fetched file goes through the model"
echo "  at the chosen effort — that is what spends Codex tokens. --effort high roughly halves"
echo "  it vs xhigh. Live progress streams below (also captured to S6-review-run.txt):"
set +e
SPECIFY_FEATURE="001-single-skill-baseline" \
SPECKIT_POWERPACK_REVIEW_PROMPT_EVIDENCE="$EVID/review-prompt.txt" \
  "${PP[@]}" review run "${RUN_ARGS[@]}" \
  2>&1 | tee "$EVID/S6-review-run.txt"
REVIEW_EXIT=${PIPESTATUS[0]}
set -e

# review run executes in the throwaway worktree. Persist the complete structured
# attachment bundle before the EXIT trap removes that worktree; review.json is
# not sufficient evidence because the prompt and package files are separate
# native uploads. This runs for both successful and externally blocked attempts.
ATTACHMENT_SOURCE="$WT/review-attachments"
ATTACHMENT_TARGET="$EVID/review-attachments"
ATTACHMENT_COPY_EXIT=0
if [ -d "$ATTACHMENT_SOURCE" ]; then
  mkdir -p "$ATTACHMENT_TARGET"
  cp -R "$ATTACHMENT_SOURCE/." "$ATTACHMENT_TARGET/" || ATTACHMENT_COPY_EXIT=$?
  if [ "$ATTACHMENT_COPY_EXIT" -eq 0 ] && [ -f "$ATTACHMENT_TARGET/manifest.json" ]; then
    echo "  [browserless] review attachments evidence copied: $ATTACHMENT_TARGET"
  else
    echo "  [browserless] review attachments evidence is incomplete: $ATTACHMENT_TARGET" >&2
    ATTACHMENT_COPY_EXIT=1
  fi
else
  echo "  [browserless] review attachments bundle missing: $ATTACHMENT_SOURCE" >&2
  ATTACHMENT_COPY_EXIT=1
fi

# An external evidence failure is a terminal pending state for this attempt.
# Preserve the first BLOCKED artifact, but do not run protocol validation or
# any task-closing step against it.
if [ "$REVIEW_EXIT" -ne 0 ]; then
  if [ -f "$WT/review.json" ]; then
    cp "$WT/review.json" "$EVID/review.json"
  fi
  say "review attempt aborted; implementation review remains PENDING"
  echo "review exit: $REVIEW_EXIT"
  echo "No S7 validation or task closure was performed."
  exit "$REVIEW_EXIT"
fi

if [ "$ATTACHMENT_COPY_EXIT" -ne 0 ]; then
  echo "review succeeded but attachment evidence persistence failed; refusing S7/closure" >&2
  exit 1
fi

cp "$WT/review.json" "$EVID/review.json"
say "S7 protocol validation"
python3 "$WT/.specify/powerpack/bin/review_protocol.py" validate --input "$EVID/review.json" \
  2>&1 | tee "$EVID/S7-protocol-validate.txt"

say "verdict"
python3 -c "import json; d=json.load(open('$EVID/review.json')); print('verdict:', d['verdict']); print(d.get('summary',''))"
grep -oE '"github_calls": *[0-9]+' "$EVID/S6-review-run.txt" | tail -1 | sed 's/"github_calls": */GitHub calls made: /'
echo "curl trace of every backend-api request: $FEATURE/T025-evidence/http-requests.log"
echo "Update RESULT.md and hand review.json back to close the [ACCEPTANCE] tasks."
