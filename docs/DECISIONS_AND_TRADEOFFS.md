# Decisions and trade-offs

This document records the implementation decisions behind the current browserless code-review provider.

## 1. Preserve Spec Kit as the workflow foundation

**Decision:** PowerPack extends official GitHub Spec Kit instead of forking/replacing it.

**Benefit:** projects retain the upstream SDD vocabulary/artifacts and PowerPack stays reusable.

**Cost:** PowerPack must maintain compatibility with Spec Kit versions and avoid owning upstream semantics unnecessarily.

## 2. Remove the browser/Web2API production path

**Decision:** Chrome, Playwright, CDP, browser-profile bridges and ChatGPT-Web2API are not part of the supported provider.

**Benefit:** substantially less OS-specific state, authentication duplication and browser lifecycle complexity; WSL/Windows behavior becomes symmetrical.

**Cost:** the provider relies on account-scoped ChatGPT backend reads plus Codex Apps surfaces instead of a user-visible ChatGPT browser conversation.

Historical experimental branches may retain old probes as research evidence; they are not production dependencies.

## 3. Reuse Codex authentication

**Decision:** PowerPack reads the existing Codex authentication store and never converts its bearer token into browser cookies/session state.

**Benefit:** one authenticated identity for Project discovery/context and ChatGPT Web review turns.

**Cost:** `codex login` is a required setup step and changes in account-scoped ChatGPT backend behavior can block the provider.

## 4. Serialize ChatGPT Project context

**Decision:** Project metadata/recent conversations are fetched first and serialized into the review prompt; `native_binding = false`.

**Benefit:** this path is deterministic and was homologated without browser state.

**Cost:** the generated review turn is not itself a native ChatGPT Project conversation and does not automatically appear in the Project. Context size must be bounded.

**Safety:** Project context is background memory. Current SPEC and immutable PR evidence are authoritative.

## 5. Use the ChatGPT GitHub connector through ChatGPT Web SSE

**Decision:** connector discovery verifies GitHub installed/enabled/OAuth/availability state, then the resolved connector is selected dynamically through the ChatGPT Web payload (`plugin:connector_*` plus `@Github`). A pending JIT permission is continued with a fresh-Sentinel `allow` request.

**Benefit:** the model gets the same GitHub connector used by ChatGPT Web, with Project binding and permission continuation, without shell tokens or a browser profile.

**Cost:** this depends on current ChatGPT Web Sentinel, SSE and connector payload behavior. These are product-internal capabilities, not a guaranteed public API schema.

**Safety:** PowerPack requires observable connector/tool activity and successful review-contract validation; it forbids command/web-search fallback for GitHub evidence and never enables writes in the connector allow payload.

## 6. Two-phase review instead of one prompt

**Decision:** first materialize an immutable PR manifest, then perform the deep review.

**Benefit:** the Master Review turn is bound to repository, PR, base/head/merge-base, changed-file list, SPEC and snapshot digest; stale/ambiguous context is caught before verdict.

**Cost:** one additional model turn increases latency and usage.

The correctness gain is preferred because a fast review against the wrong snapshot is not useful.

## 7. Require local HEAD == PR head

**Decision:** browserless PR review only proceeds when the local implementation checked out by the user matches the GitHub PR head SHA.

**Benefit:** local Spec Kit context and remote PR evidence cannot silently refer to different implementations.

**Cost:** users must update/check out the exact PR head before review.

## 8. Ephemeral read-only Codex turns

**Decision:** review turns use fresh Sentinel requirements and read-only connector permission continuations.

**Benefit:** reduced state leakage, explicit Project/connector binding and clear authority separation from implementation.

**Cost:** each turn must renew Sentinel requirements; persistent conversational continuity is intentionally limited.

## 9. Fail closed

**Decision:** missing tool evidence, ambiguous SPEC, connector unavailability, snapshot mismatch, incomplete coverage or invalid schema blocks review.

**Benefit:** absence of evidence can never become implicit approval.

**Cost:** upstream capability changes may cause operational blocking until PowerPack is adapted.

## 10. Keep provider internals isolated

**Decision:** ChatGPT backend compatibility, Project context, connector discovery, Codex Apps JSONL and review orchestration live in separate modules.

**Benefit:** unstable external boundaries can change without contaminating the generic Spec Kit runtime.

**Cost:** more explicit interfaces and tests are required.
