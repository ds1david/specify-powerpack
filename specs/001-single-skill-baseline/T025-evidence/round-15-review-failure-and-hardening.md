# T025 — Round 15 review identity evidence

The review reached the connector, processed conditional authorization, and
resolved snapshot SHAs and changed-file paths. Validation then rejected a
review_context SPEC identifier that did not exactly match the active local
SPEC directory `001-single-skill-baseline`.

The same-segment evidence completion now states the exact required spec_id and
the gate remains fail-closed on any mismatch.
