# Contract: Browserless Review Evidence Package

This contract complements `implement-review-prereq.md` for the preserved browserless path.

## Package and authority

Native attachments comprise `output-schema.json`, `packet.json`,
`github-evidence-contract.md`, `protocol.md`, `spec-artifacts.md`, optional
`previous-review.json`, `instructions.md` and `master-prompt.md`. OutputSchema controls only
shape; Packet controls target/lineage; the GitHub contract controls evidence prerequisites;
Protocol controls method/verdict; SPEC artifacts control expected behavior; previous findings
control lifecycle only; Instructions control operation. Missing GitHub evidence is never
filled from Project memory, PR prose, commit messages, CI or a previous response.

## Upload barrier

For each artifact, create/upload it, upload bytes to the returned URL, process it, wait for
processing completion, and retain the native file reference. Submit only after every required
artifact is complete. The manifest records `name`, `sha256`, `bytes`, file reference and
upload/processing status. The exact prompt and all package files are copied to the homologation
evidence directory before submit.

## Connector and pacing

Discover the account-scoped GitHub connector at runtime and use its current id. Authorization
is through the connector/JIT conversation flow; a GitHub token is neither required nor stored.
All inter-operation waits use one injectable random policy with `min=1.5` and `max=4.0`
seconds for upload, processing, authorization, retry and submit. Fixed two-second waits are
forbidden.

## External blocker

If the first terminal response reports `MISSING_GITHUB_SNAPSHOT`, `MISSING_CHANGED_FILES`,
`MISSING_CHANGED_FILE_CONTENTS`, `MISSING_SPEC`, `MISSING_TOOL`, `INCOMPLETE_CONTEXT`, or
equivalent incomplete immutable evidence, persist the response and evidence bundle, set
`execution_status` to `PENDING_EXTERNAL_REVIEW`, preserve lineage, add `blocked_reason` and
`coverage.context_gaps`, and stop. Do not repair, send a second prompt, create technical
findings or close tasks. Retry only after the external prerequisite is fixed.

## Terminal success

With complete evidence, submit exactly one compact prompt and accept exactly one final JSON
object conforming to `output-schema.json`. Structural validation occurs before local
normalization; an incomplete artifact is `BLOCKED`, not repaired through another prompt.
