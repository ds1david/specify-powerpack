# Web PR review — GitHub app/plugin prerequisite

## Purpose

A PowerPack Web PR review needs two independent integrations:

1. a repository binding to a ChatGPT Project; and
2. live GitHub repository access inside the ChatGPT review session.

A valid ChatGPT Project binding alone is not evidence that the reviewer can inspect a GitHub pull request.

## Required ChatGPT Web/Desktop setup

Before using `speckit-powerpack review run --provider web`, configure GitHub in the same ChatGPT account used by the PowerPack/Codex-authenticated flow.

In a ChatGPT Web/Desktop surface where GitHub is available:

1. Open **Settings**.
2. Open **Apps** or **Plugins**, depending on the product surface shown to the account.
3. Connect **GitHub** (or the plugin/app that provides GitHub access).
4. Complete the GitHub authorization/install flow for the ChatGPT app.
5. Grant the app access to the repository that contains the PR to be reviewed.
6. If the repository belongs to an organization, obtain any organization/admin approval required by GitHub.

OpenAI documents GitHub connection and repository authorization at:

- https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt
- https://help.openai.com/en/articles/20001494-connecting-and-managing-app-accounts-in-chatgpt
- https://help.openai.com/en/articles/11487775-connectors-in-chatgpt

OpenAI also documents that a connected app/plugin may be invoked explicitly with an `@` mention or selected from the tools menu. GitHub availability can vary by ChatGPT plan, workspace and product surface. A repository being authorized in GitHub does not by itself prove that the current ChatGPT session exposes the GitHub tool.

## Interactive ChatGPT Project binding

For normal human use, let PowerPack discover the Projects visible to the authenticated account instead of copying a Project id manually:

```bash
cd /path/to/repository
speckit-powerpack review setup --path .
```

Answer yes when asked whether to bind a ChatGPT Project. PowerPack lists the available Projects and asks for a numeric selection.

Then validate the persisted provider state:

```bash
speckit-powerpack doctor --strict-review .
```

A bind or strict-doctor failure is a hard stop.

## `@GitHub` activation is part of the Web review contract

The currently homologated ChatGPT behavior for this PowerPack path requires an explicit GitHub mention at the beginning of the effective review prompt. PowerPack canonicalizes that invocation as:

```text
@GitHub
```

If a user prompt file already begins with `@GitHub` or `@github`, PowerPack removes that leading user-supplied mention before composition and emits one canonical `@GitHub` as the first line. This avoids duplicate plugin mentions while preserving the user's remaining review instruction.

The effective prompt therefore starts with the GitHub invocation before the authoritative PR context and the user review instruction.

This activation behavior is operationally homologated in the ChatGPT product flow and is consistent with OpenAI's documented support for explicit `@` app/plugin mentions. It is **not** a public contract for the private ChatGPT backend transport. The browserless provider uses non-public ChatGPT backend paths, so upstream behavior can change. If `@GitHub` stops activating GitHub in the generated session, the review must fail closed and be re-homologated; do not silently fall back to Project memory or a generic repository review.

## Real Web PR review

After the GitHub app/plugin is connected, the repository is authorized, the Project is bound, and strict doctor passes:

```bash
speckit-powerpack review run \
  --provider web \
  --path /path/to/repository \
  --pr 92 \
  --github-plugin-authorized \
  --prompt-file /tmp/review.md
```

`--github-plugin-authorized` is an explicit user attestation that:

- GitHub is installed/connected in ChatGPT Web/Desktop for the account being used;
- the target repository has been granted to the ChatGPT GitHub app/plugin;
- any required organization approval has been completed.

The flag does not itself grant permissions and does not prove tool invocation. The generated `@GitHub` mention requests the capability in the review session; the reviewer still has to demonstrate that the exact PR was inspected.

## Backend/tool-use model: verified facts vs implementation hypothesis

The PowerPack must distinguish verified behavior from reverse-engineered or inferred backend details.

### Verified for the current browserless flow

- Codex authentication from `~/.codex/auth.json` is sufficient for the currently homologated Project discovery/context transport.
- `ChatGPT-Account-ID` is used by the current browserless provider.
- a bound ChatGPT Project can be discovered and its Project context can be loaded without Playwright, Chromium or browser-cookie copying;
- the GitHub app/plugin must be connected to the ChatGPT account and the repository must be authorized;
- an explicit `@GitHub` invocation is part of the currently homologated Web PR flow;
- any `BLOCKED_*` response is a failed review gate, not an approval.

### Not yet a proven transport contract

The following details are plausible implementation hypotheses for a richer private-backend provider, but are **not yet accepted as PowerPack requirements without reproduced evidence**:

- a mandatory `POST /backend-api/conversation` initialization flow;
- exact `plugin_ids` or `gizmo_id` payload shapes;
- exact SSE event names or message-tree representation for GitHub tool calls;
- a mandatory browser `Cookie` header for plugin execution;
- exact server-side OAuth/tool-call orchestration fields.

PowerPack must not reintroduce browser cookies, Playwright or Chromium merely because those fields are hypothesized. If a future experiment proves that the private GitHub-capable transport requires additional account/session material, that becomes a separately reviewed security/architecture decision and triggers re-homologation.

See `docs/WEB_GITHUB_BACKEND_EXPERIMENT.md` for the experimental transport model and evidence gates.

## Fail-closed statuses

The Web review must distinguish these cases:

```text
BLOCKED_CAPABILITY
```

The review session exposes no GitHub plugin/connector/tool even after the generated `@GitHub` invocation. This indicates a product-surface/transport capability problem, not an approved review.

```text
BLOCKED_CONFIGURATION
```

A GitHub capability is available, but it cannot access the exact repository or PR. Check the ChatGPT Web/Desktop GitHub connection, repository authorization and organization approval.

```text
BLOCKED_REVIEW_CONTEXT
```

The required review identity/context cannot be resolved safely.

Any `BLOCKED_*` response is preserved as evidence and `review run` exits non-zero. It must never be converted into approval.

## Homologation implications

A complete Web PR review is stronger than a Project-context smoke. Evidence should ultimately prove:

```text
ChatGPT Project bind
+ backend/Project context
+ explicit PR identity
+ GitHub app/plugin installed and repository authorized
+ one canonical generated @GitHub invocation
+ exact PR accessible to the reviewer
+ PR base/head and changed-file inspection
+ reviewer verdict for the same snapshot
```

Until every required gate is evidenced, the Web PR path is not fully homologated.
