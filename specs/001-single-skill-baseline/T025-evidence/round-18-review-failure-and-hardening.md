# T025 — Round 18 review coverage evidence

The immutable snapshot was reconciled successfully, including exact SHA-256
identity. The next gate found a normative coverage gap: the active SPEC
contains 30 requirement IDs while the returned `coverage.requirements` array
omitted them.

The same-segment continuation now receives and must return the exact active
requirement ID set with evidence-backed status objects. The protocol still
rejects incomplete coverage.
