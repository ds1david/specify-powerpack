# T025 — Round 12 review transport evidence

Sanitized diagnostics showed that the reviewer returned
`coverage.changed_files` as a four-entry mapping keyed by file paths. The
snapshot contract needs the path set as an array, while the mapping carries
the same file identity plus per-file evidence.

The adapter now normalizes only an unambiguous path-keyed mapping (or an
explicit files/paths list) to snapshot paths. Metadata-shaped mappings remain
blocked; no arbitrary prose or count is accepted as changed-file evidence.
