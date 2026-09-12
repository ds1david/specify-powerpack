# T025 — Round 8 review transport evidence

The real review completed GitHub connector calls, including more than one
explicit authorization gate with refreshed Sentinel credentials. It returned
full immutable SHA fields after the evidence-completion continuation.

The next validation failure was structural: `coverage.changed_files` was not
an array. The gate correctly refused to build a snapshot from ambiguous data.
The runner now treats a missing or non-array changed-file set as incomplete
evidence and requests the complete list in the same conversation segment.

No review verdict or finding is accepted until the complete PR snapshot is
provable.
