# T025 — Round 11 review transport evidence

The GPT Web continuation still returned a review object without an accepted
non-empty changed-file array after the explicit evidence request. The gate
continues to reject the snapshot rather than infer files or accept a different
shape.

This round adds sanitized diagnostic logging of only top-level/coverage keys
and the changed-file value type/length. It does not log review contents,
credentials, or connector payloads.
