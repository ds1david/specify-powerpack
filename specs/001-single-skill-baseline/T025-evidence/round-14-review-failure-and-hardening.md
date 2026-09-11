# T025 — Round 14 review transport evidence

Some review attempts returned complete immutable SHAs but no changed-file
array in either the initial or completion object. The connector was still
used for the PR and snapshot identity.

The runner now has a constrained fallback: when full `merge_base` and
`head_sha` are present, it derives only path names from the local immutable
checkout diff for that exact range. The local HEAD is already required to
match the reviewed head; no file content or reviewer finding is synthesized.
If the exact diff cannot be resolved or is empty, the review remains blocked.
