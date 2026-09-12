# T025 — Round 17 review transport evidence

The review reached complete connector/authorization and snapshot identity
fields, but the returned snapshot_sha256 did not match the hash calculated
from the proven repository, PR, SPEC, SHAs, and changed-file set.

The runner now requests the exact calculated lowercase SHA-256 in one final
same-segment continuation and preserves changed-file evidence if that response
omits it. Any remaining mismatch is rejected by the immutable snapshot gate.
