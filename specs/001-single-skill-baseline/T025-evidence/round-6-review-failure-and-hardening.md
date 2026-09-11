# T025 — Round 6 review transport evidence

## Context

The implementation review used the configured ChatGPT Project and the dynamic
GitHub connector for PR #15. The connector requested JIT authorization; the
transport refreshed Sentinel credentials and the allow continuation returned
HTTP 200. This confirms that authorization remains conditional: no allow is
sent unless the SSE stream contains an explicit `confirm_action`.

## Failure observed

The review stream contained intermediate connector/tool JSON after the GitHub
calls. The browserless review adapter selected that JSON as the final response.
Snapshot validation then failed because the object had no `review_context` or
`base_ref`:

```text
ReviewContextError: PR snapshot did not include base_ref.
```

This was a transport/result-selection failure, not a code-review finding.

## Hardening implemented

- SSE parsing retains candidate assistant text without allowing an earlier
  tool payload to overwrite the eventual candidate.
- JSON extraction now scans embedded/fenced JSON and accepts only an object
  containing both `verdict` and `review_context`.
- A tool/progress JSON object is rejected explicitly instead of being passed
  to snapshot validation.
- Connector continuation supports multiple explicit authorization gates,
  refreshing Sentinel credentials for each allow and stopping immediately when
  no `confirm_action` is present.

## Verification

The new tests cover intermediate tool JSON selection and rejection of a
non-review JSON response. The full test result and publication commit are
recorded in the implementation-round comment on PR #15.
