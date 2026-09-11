# Implementation review

`/speckit-implement-review` is a **Specify PowerPack** workflow command that reviews and converges an implementation that already has an explicit same-SPEC `speckit-implement` predecessor. It must not perform the initial implementation just to satisfy its prerequisite.

## Workflow contract

```text
implement receipt
  → converge
      → tasks appended? implement authorized work → converge
  → capability-selected quality gate
  → deep PR review
      → findings? persist → implement → converge → quality gate → fresh review
      → approved current snapshot? COMPLETE
```

All review findings are current-flow work. They cannot be deferred merely to make the workflow finish; they return to implementation until the same final snapshot is approved.

## Readiness

```bash
specify-powerpack doctor . --strict-review
```

The repository must be bound to a ChatGPT Project and the GitHub App/connector must be live for the Codex-authenticated account.

## Exact PR requirement

The provider never guesses a PR:

```bash
specify-powerpack review run --path . --pr <number-or-canonical-url>
```

The local Git origin must be GitHub and must match the PR repository.

## Immutable manifest

Each round starts with a fresh GitHub-tool manifest containing base/head/merge-base and complete changed files. Specify PowerPack binds the active SPEC to that manifest and hashes the canonical snapshot.

The judgment turn uses the versioned `.specify/powerpack/master-review-prompt.md` plus a generated Review Packet. The packet carries the immutable snapshot, Project context as supplemental data, protocol/master hashes and the authoritative checkpoint. Its lineage is `Review -> Round -> Attempt -> Conversation Segment`: a conversation rollover increments only the segment; a changed implementation snapshot starts a new round.

If local `HEAD != PR head SHA`, the review stops. Any implementation change therefore invalidates previous approval automatically because the next run produces a different head/snapshot.

## Evidence inputs

The deep reviewer receives four distinct evidence classes:

1. **immutable GitHub PR evidence** — authoritative current code/diff identity;
2. **Spec Kit context** — authoritative current requirements;
3. **ChatGPT Project context** — serialized historical/background memory;
4. **previous review/checkpoint** — mandatory finding revalidation on round 2+; the checkpoint is lifecycle authority.

Project memory never substitutes for current PR evidence.

## GitHub evidence rules

The dynamically discovered GitHub connector is injected into the ChatGPT Web payload as
`plugin:connector_*` plus the `@Github` ecosystem mention. The resulting SSE must contain
GitHub tool activity and, when requested, a successful JIT `allow` continuation.

Forbidden evidence fallbacks:

- shell/command execution for GitHub inspection;
- generic web search;
- PR description alone;
- CI status alone;
- Project memory alone.

## Master Prompt and Review Packet

The runner never uses the homologation probe questions as a code-review task. The probe remains a separate live transport test. The review task explicitly asks the GitHub connector to inspect the exact PR, then return one consolidated structured result after all review fronts and the adversarial pass. Mission summaries, repository listings and standalone changed-file probes are not substitutes for code review.

The generated packet is persisted beside the review result as `<review-stem>-packet.json` when an explicit output path is supplied.

## Deep Review Protocol

The installed `.specify/powerpack/deep-review-protocol.md` and schema 2.0 validator remain mandatory.

Required fronts are:

- `SPEC_COMPLIANCE`
- `BEHAVIORAL_REGRESSION`
- `ARCHITECTURE_AND_CONTRACTS`
- `STATE_CONCURRENCY_AND_FAILURES`
- `PERSISTENCE_DETERMINISM_IDEMPOTENCY`
- `TESTS_AND_COMPOSITION_ROOT`
- `DOCUMENTATION_AND_OPERABILITY`
- `SECURITY_AND_SCOPE`

Validate manually when needed:

```bash
python .specify/powerpack/bin/review_protocol.py validate --input <review.json>
```

Round 2+:

```bash
python .specify/powerpack/bin/review_protocol.py validate \
  --input <review.json> \
  --previous <previous-review.json>
```

## Project-context proof

The review must return:

```json
{
  "project_context_evidence": {
    "project_name": "exact bound Project name",
    "literal_evidence": "3 to 20 consecutive words from serialized Project context"
  }
}
```

Specify PowerPack verifies that the literal excerpt actually occurs in the serialized context and is not merely the Project name.

## Output

Default output path:

```text
.specify/powerpack/reviews/<spec>-pr<number>-<head-prefix>.json
```

The CLI prints a machine-readable completion summary including verdict, snapshot and the
resolved GitHub connector. It explicitly reports browser/CDP/Playwright/Web2API usage as false.

## Previous findings

Use:

```bash
specify-powerpack review run \
  --path . \
  --pr <number> \
  --previous <previous-review.json>
```

The schema validator requires exact accounting for every prior finding. A finding declared resolved but materially reappearing is blocked by the review protocol.

## Completion

`APPROVED` is valid only for the exact snapshot reviewed, with no findings and all protocol coverage satisfied. A changed HEAD requires a new review round.
