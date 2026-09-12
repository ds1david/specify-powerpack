#!/usr/bin/env bash
# T025 offline evidence collector — runs the parts of the implement-review
# validation runbook that do NOT need live Codex/GitHub, and writes evidence
# files + pass/fail checks into specs/001-single-skill-baseline/T025-evidence/.
#
# Usage:  bash specs/001-single-skill-baseline/collect-t025-offline-evidence.sh <PP-dir> <feature-rel-path>
#   <PP-dir>            an installed target project (see runbook P1)
#   <feature-rel-path>  e.g. specs/001-x  (relative to <PP-dir>)
#
# Exit 0 = every offline pass condition held. Non-zero = at least one failed.
set -u

PP="${1:?usage: $0 <PP-dir> <feature-rel-path>}"
FEAT="${2:?usage: $0 <PP-dir> <feature-rel-path>}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$REPO_ROOT/specs/001-single-skill-baseline/T025-evidence"
PY="${PYTHON:-python3}"
BIN="$PP/.specify/powerpack/bin"
PPK="$PP/.specify/powerpack"
mkdir -p "$OUT"
fail=0
note() { printf '  %s\n' "$*"; }
check() { # check <label> <condition-exit-code>
  if [ "$2" -eq 0 ]; then printf 'PASS  %s\n' "$1"; else printf 'FAIL  %s\n' "$1"; fail=1; fi
}

echo "== T025 offline evidence -> $OUT =="
echo "PP=$PP  FEATURE=$FEAT  $(date -u +%FT%TZ)" | tee "$OUT/_meta.txt"

# ---- P1: installed runtimes ------------------------------------------------
ls -la "$BIN" > "$OUT/P1-bin.txt" 2>&1
present="$(cd "$BIN" 2>/dev/null && ls *.py 2>/dev/null | sort | tr '\n' ' ')"
[ "$present" = "capabilities.py powerpack.py review_protocol.py " ]
check "P1 bin/ = exactly the 3 preserved runtimes ($present)" $?

# ---- P2: powerpack-core command set --------------------------------------
{ find "$PP" -path '*powerpack-core*commands*' -name 'speckit*.md' -print 2>/dev/null
  find "$PP" -name 'speckit-*.md' -path '*commands*' -print 2>/dev/null
} | sort -u > "$OUT/P2-commands.txt"
removed_hits="$(grep -E 'speckit[.-](implement|converge|checklist-converge|full-cycle|debt-)' "$OUT/P2-commands.txt" \
  | grep -vE 'implement-review' | wc -l | tr -d ' ')"
grep -q 'speckit[.-]implement-review' "$OUT/P2-commands.txt" && [ "${removed_hits:-0}" -eq 0 ]
check "P2 command set has implement-review and no removed command file" $?

# ---- P3: upstream commands present --------------------------------------
{ ls "$PP/.claude/skills/" 2>/dev/null; ls "$PP/.codex/prompts/" 2>/dev/null; \
  find "$PP" -name 'speckit-implement*' -o -name 'speckit-converge*' 2>/dev/null; } \
  | sort -u > "$OUT/P3-upstream.txt"
grep -q 'speckit-implement' "$OUT/P3-upstream.txt" && grep -q 'speckit-converge' "$OUT/P3-upstream.txt"
check "P3 upstream speckit-implement + speckit-converge present" $?

# ---- S2: re-based prerequisite gate ------------------------------------
# powerpack.py resolves paths against its own project root, so run it from $PP.
cp "$PPK/prerequisites.json" "$OUT/S2-prerequisites.json" 2>/dev/null || true
( cd "$PP" && "$PY" "$BIN/powerpack.py" prereq check --step implement-review --feature-dir "$FEAT" ) \
  > "$OUT/S2-prereq.json" 2>&1
s2_exit=$?
grep -q '"schema_version": 2' "$OUT/S2-prerequisites.json" \
  && grep -q 'implementation-evidence' "$OUT/S2-prerequisites.json" \
  && ! grep -q 'checklist-converge' "$OUT/S2-prerequisites.json" \
  && ! grep -q '"statuses": \["COMPLETED"\]' "$OUT/S2-prerequisites.json"
check "S2 prerequisites.json = schema 2 / implementation-evidence / no checklist-converge / no receipt" $?
grep -qE '"reason": "(OK|NO_IMPLEMENTATION_DELTA|NO_SPEC_BASELINE|TASKS_INCOMPLETE|MISSING_TASKS)"' "$OUT/S2-prereq.json"
check "S2 prereq check returned a known deterministic reason (exit=$s2_exit)" $?

# S2 negatives (reproduce the three failure reasons in a scratch git repo)
neg="$(mktemp -d)"
( set -e
  cd "$neg"; git init -q; git config user.email t@e; git config user.name t
  mkdir -p .specify specs/001-neg; echo x > README.md; git add -A; git commit -qm base
  "$PY" "$BIN/powerpack.py" prereq check --step implement-review --feature-dir specs/001-neg 2>&1 | sed 's/^/MISSING_TASKS_CASE: /'
  printf -- '- [X] T001 done\n- [ ] T002 no\n' > specs/001-neg/tasks.md
  echo '# plan' > specs/001-neg/plan.md; git add -A; git commit -qm 'spec neg'
  "$PY" "$BIN/powerpack.py" prereq check --step implement-review --feature-dir specs/001-neg 2>&1 | sed 's/^/TASKS_INCOMPLETE_CASE: /'
  printf -- '- [X] T001 done\n' > specs/001-neg/tasks.md; git add -A; git commit -qm 'tasks done, docs only'
  "$PY" "$BIN/powerpack.py" prereq check --step implement-review --feature-dir specs/001-neg 2>&1 | sed 's/^/NO_IMPLEMENTATION_DELTA_CASE: /'
  mkdir -p specs/099-loose; printf -- '- [X] T001\n' > specs/099-loose/tasks.md   # uncommitted
  "$PY" "$BIN/powerpack.py" prereq check --step implement-review --feature-dir specs/099-loose 2>&1 | sed 's/^/NO_SPEC_BASELINE_CASE: /'
) > "$OUT/S2-negatives.txt" 2>&1
rm -rf "$neg"
grep -q 'MISSING_TASKS_CASE:.*MISSING_TASKS' "$OUT/S2-negatives.txt" \
  && grep -q 'TASKS_INCOMPLETE_CASE:.*TASKS_INCOMPLETE' "$OUT/S2-negatives.txt" \
  && grep -q 'NO_IMPLEMENTATION_DELTA_CASE:.*NO_IMPLEMENTATION_DELTA' "$OUT/S2-negatives.txt" \
  && grep -q 'NO_SPEC_BASELINE_CASE:.*NO_SPEC_BASELINE' "$OUT/S2-negatives.txt"
check "S2 all four failure reasons reproduced" $?

# ---- S4: capability quality gate --------------------------------------
( cd "$PP" && "$PY" "$BIN/capabilities.py" gate detect --feature-dir "$FEAT" ) > "$OUT/S4-gate-detect.json" 2>&1
( cd "$PP" && "$PY" "$BIN/capabilities.py" gate run    --feature-dir "$FEAT" ) > "$OUT/S4-gate-run.txt"    2>&1
grep -n 'implement_runs\|latest_implement_files' "$BIN/capabilities.py" > "$OUT/S4-capabilities-grep.txt" 2>&1
[ ! -s "$OUT/S4-capabilities-grep.txt" ]
check "S4 capabilities.py has no implement_runs / latest_implement_files" $?
# gate must not falsely claim NOT_APPLICABLE when the SPEC has real code
if grep -q '"status": "NOT_APPLICABLE"' "$OUT/S4-gate-detect.json"; then
  note "S4 gate = NOT_APPLICABLE — verify the SPEC delta is genuinely docs-only (manual)"
fi

# ---- S5: review route + model-routing --------------------------------
( cd "$PP" && "$PY" "$BIN/powerpack.py" review route ) > "$OUT/S5-review-route.json" 2>&1
check "S5 review route exited 0" $?
"$PY" - "$PPK/model-routing.json" > "$OUT/S5-stages.json" 2>&1 <<'PYEOF'
import json,sys; d=json.load(open(sys.argv[1])); print(json.dumps(d.get("stages")))
PYEOF
grep -q '{"implement-review": "orchestration"}' "$OUT/S5-stages.json"
check "S5 model-routing stages == {implement-review}" $?

# ---- §4: cross-cutting residual grep --------------------------------
grep -rnE 'debt\.py|full_cycle\.py|powerpack_debt|powerpack_full_cycle|technical-debt|speckit\.(implement|converge|full-cycle|debt-)' \
  "$PPK" 2>/dev/null | grep -vE 'deep-review-protocol\.md|replaced the removed|no longer' \
  > "$OUT/cross-cutting-grep.txt" || true
[ ! -s "$OUT/cross-cutting-grep.txt" ]
check "§4 installed .specify/powerpack has zero active removed-command references" $?

# ---- CI-equivalent: the flow-survives-cleanup suite -----------------
# This is CI-enforced already; here it is a bonus. Set PYTEST=skip (or leave a
# broken pytest) and it degrades to a NOTE instead of a FAIL.
if [ "${PYTEST:-pytest}" = "skip" ]; then
  note "flow-survives-cleanup + baseline-contract suites: skipped (PYTEST=skip; CI covers this)"
elif ! ${PYTEST:-pytest} --version > /dev/null 2>&1; then
  echo "no working pytest ('${PYTEST:-pytest}')" > "$OUT/pytest.txt"
  note "flow-survives-cleanup + baseline-contract suites: no pytest here (CI covers this)"
else
  ( cd "$REPO_ROOT" && ${PYTEST:-pytest} -q tests/test_implement_review_flow_survives_cleanup.py \
      tests/test_baseline_contract.py ) > "$OUT/pytest.txt" 2>&1
  check "flow-survives-cleanup + baseline-contract suites green" $?
fi

echo
echo "== offline evidence collection: $([ $fail -eq 0 ] && echo PASS || echo FAIL) =="
echo "Next: run the live steps S1/S3/S6/S7 (runbook §4) and fill T025-evidence/RESULT.md."
exit $fail
