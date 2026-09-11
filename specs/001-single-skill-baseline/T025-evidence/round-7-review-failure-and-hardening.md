# T025 — Round 7 review transport evidence

## Result

The real Master Review reached the GitHub connector and exercised both
authorization paths: an explicit `confirm_action` was allowed with refreshed
Sentinel credentials, and subsequent connector work continued without a new
authorization request. The reviewer then returned a structured JSON object.

## Failure observed

The returned `review_context` contained an abbreviated `merge_base` value.
The review gate rejected it because immutable snapshot identity requires full
40-character hexadecimal SHAs. No finding or verdict was accepted from that
incomplete snapshot.

## Hardening

Snapshot completeness now treats present-but-abbreviated or non-hexadecimal
SHA fields as invalid. The same conversation segment requests an evidence
completion containing full `base_sha`, `merge_base`, and `head_sha` values;
the gate remains blocked if GitHub evidence cannot prove them.

## Verification

The implementation was validated with the repository test suite and the
result is published in the corresponding PR comment.
