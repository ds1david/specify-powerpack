# Full redacted HTTP trace for ChatGPT/GitHub browserless probes

## Purpose

When the connector-aware browserless probe returns a generic error such as:

```text
HTTP 422
{"detail":"Invalid conversation body"}
```

summary-only evidence is no longer sufficient to compare the PowerPack request with a successful ChatGPT Web capture.

The diagnostic below records every HTTP request and response performed by the existing root-parity probe, including:

```text
method
full URL
request headers
request body
response status
response headers
response body
SSE response text when applicable
```

The tracer wraps the real `urllib.request.urlopen` calls made by the existing probe; it does not maintain a second copy of the connector/conversation protocol.

## Security boundary

The trace is intentionally complete **except for secrets and account/session material**.

The following values are always redacted before they are written:

```text
Authorization header values
Cookie / Set-Cookie values
OAuth/session/token values
conduit token values
Sentinel/proof/Turnstile values
CSRF/secret values
account/user identifiers and emails
sensitive query-string values
raw connector/plugin connector identifiers
```

Redacted values receive stable SHA-256-derived fingerprints inside one log, for example:

```text
connector_<redacted:0123456789>
<redacted:abcdef0123>
```

This preserves enough correlation to verify that the same connector/session-shaped value was propagated across requests without exposing the original value.

Do not disable these redactions merely to compare with a HAR. Compare field names, structure, fingerprints, status codes and non-secret scalar values instead.

## Run on WSL

Update the homologation branch and run the tests first:

```bash
cd /home/david/workspace/speckit-powerpack
git pull
git rev-parse HEAD

uv run --extra dev python -m pytest -q \
  tests/test_homologation_harness.py \
  tests/test_review_context_contract.py \
  tests/test_chatgpt_plugin_har_analyzer.py \
  tests/test_chatgpt_github_connector_probe.py \
  tests/test_chatgpt_github_conversation_init_probe.py \
  tests/test_chatgpt_github_conversation_prepare_probe.py \
  tests/test_chatgpt_github_conversation_submit_probe.py \
  tests/test_chatgpt_github_submit_422_diagnostic.py \
  tests/test_chatgpt_github_conversation_har_shape_probe.py \
  tests/test_chatgpt_github_conversation_submit_har_parity_probe.py \
  tests/test_chatgpt_github_conversation_root_parity_probe.py \
  tests/test_chatgpt_github_root_parity_http_trace.py
```

Then capture the root-only attempt:

```bash
TRACE="$HOME/powerpack-github-root-http-trace.json"
RESULT="$HOME/powerpack-github-root-result.json"

uv run python \
  scripts/homologation/trace_chatgpt_github_root_parity.py \
  --http-log "$TRACE" \
  --output "$RESULT"

EXIT=$?
echo "EXIT=$EXIT"
echo "TRACE=$TRACE"
echo "RESULT=$RESULT"
cat "$RESULT"
```

If root-only remains HTTP 422, capture the second ablation separately:

```bash
TRACE2="$HOME/powerpack-github-root-partial-id-http-trace.json"
RESULT2="$HOME/powerpack-github-root-partial-id-result.json"

uv run python \
  scripts/homologation/trace_chatgpt_github_root_parity.py \
  --include-partial-query-id \
  --http-log "$TRACE2" \
  --output "$RESULT2"

EXIT2=$?
echo "EXIT2=$EXIT2"
echo "TRACE2=$TRACE2"
echo "RESULT2=$RESULT2"
cat "$RESULT2"
```

## Expected trace sequence

The trace should make the entire request chain visible. For the current root-parity probe the expected high-level sequence includes:

```text
GET  /backend-api/ps/plugins/installed?limit=1000
POST /backend-api/apps/availability?platform=chat&locale=en-US
POST /backend-api/conversation/init
POST /backend-api/f/conversation/prepare
POST /backend-api/f/conversation
```

The exact sequence may evolve as connector preflight becomes stricter. The trace file is authoritative for the attempt actually executed.

## What to compare against the successful HAR

For each request compare:

```text
endpoint and order
HTTP method
body top-level keys
nested message keys
parent/root message semantics
message ids/create_time
conversation_mode
model
system_hints propagation
partial_query shape
serialization_metadata.custom_symbol_offsets
client_prepare_* fields
model_response_contracts
client_contextual_info
supported_encodings
local_function_names
thinking_effort
non-secret request headers
response status/content-type/body shape
```

Do not conclude that Sentinel/proof/Turnstile is required while the final request still fails at HTTP 422 request validation. If body parity eventually moves the boundary to HTTP 401/403, record that separately and do not fabricate or bypass security material.
