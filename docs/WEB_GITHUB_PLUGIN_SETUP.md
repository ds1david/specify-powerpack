# Web PR review — GitHub app/plugin prerequisite

## Purpose

A PowerPack Web PR review needs two independent integrations:

1. a repository binding to a ChatGPT Project; and
2. live GitHub repository access inside the ChatGPT review session.

A valid ChatGPT Project binding alone is not evidence that the reviewer can inspect a GitHub pull request.

## Required ChatGPT Web/Desktop setup

Before using `speckit-powerpack review run --provider web`, configure GitHub in the same ChatGPT account used by the PowerPack/Codex-authenticated flow.

In ChatGPT Web or Desktop:

1. Open **Settings**.
2. Open **Apps** or **Plugins**, depending on the product surface shown to the account.
3. Connect **GitHub** (or the plugin/app that provides GitHub access).
4. Complete the GitHub authorization/install flow for the ChatGPT app.
5. Grant the app access to the repository that contains the PR to be reviewed.
6. If the repository belongs to an organization, obtain any organization/admin approval required by GitHub.

OpenAI documents GitHub connection and repository authorization at:

- https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt
- https://help.openai.com/en/articles/11487775-connectors-in-chatgpt

GitHub availability can vary by ChatGPT plan, workspace and product surface. A repository being authorized in GitHub does not by itself prove that the current ChatGPT session exposes the GitHub tool.

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

## `@github` activation is part of the Web review contract

In the currently homologated ChatGPT Web/Desktop behavior, explicitly mentioning `@github` at the start of a prompt activates the connected GitHub capability for repository inspection.

PowerPack therefore prefixes Web PR review prompts automatically with:

```text
@github
```

Users **do not need to add `@github` to their prompt file**. The effective prompt assembled by PowerPack starts with the mention before the authoritative PR context and user review instruction.

This behavior is an operationally homologated ChatGPT product behavior, not a public/stable API contract. The browserless provider uses non-public ChatGPT backend paths, so upstream behavior can change. If `@github` stops activating GitHub in the generated session, the review must fail closed and be re-homologated; do not silently fall back to Project memory or a generic repository review.

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

The flag does not itself grant permissions and does not prove tool invocation. The generated `@github` mention requests the capability in the review session; the reviewer still has to demonstrate that the exact PR was inspected.

## Fail-closed statuses

The Web review must distinguish these cases:

```text
BLOCKED_CAPABILITY
```

The review session exposes no GitHub plugin/connector/tool even after the generated `@github` invocation. This indicates a product-surface/transport capability problem, not an approved review.

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
+ generated @github invocation
+ exact PR accessible to the reviewer
+ PR base/head and changed-file inspection
+ reviewer verdict for the same snapshot
```

Until every required gate is evidenced, the Web PR path is not fully homologated.
