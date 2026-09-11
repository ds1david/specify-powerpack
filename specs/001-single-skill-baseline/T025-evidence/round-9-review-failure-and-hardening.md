# T025 — Round 9 review transport evidence

The review reached the connector and completed conditional authorization
continuations. Snapshot validation then exposed an empty changed-file list:
the previous fallback treated an empty list as false and converted it to
missing evidence.

The runner now rejects both non-array and empty changed-file values and passes
the validated value directly to snapshot construction. It will not infer or
silently replace the PR changed-file set.
