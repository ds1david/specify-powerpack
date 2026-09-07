# Code Review Context Contract

This document defines how SpecKit PowerPack selects evidence for local and Web code review.

## Principle

A code review must have one authoritative target. PowerPack must never silently substitute a generic repository review when the intended review context is unavailable.

The two review modes are intentionally different:

```text
LOCAL REVIEW
  -> current repository
  -> current Git branch
  -> current Spec Kit SPEC linked to that branch
  -> no GitHub PR required
  -> no ChatGPT Project/GitHub plugin claim

WEB REVIEW
  -> explicit GitHub pull request parameter
  -> current repository origin must match the PR repository
  -> ChatGPT Project binding when configured
  -> ChatGPT/GitHub plugin or connector access must be granted by the user
  -> exact PR must be inspected
  -> generic repository review is forbidden
```

## Local review

Local review is the default contract when the selected provider is Codex/local.

The reviewer context is resolved from the repository itself:

1. current named Git branch;
2. exactly one `specs/<feature>/spec.md` associated with that branch;
3. implementation and SPEC artifacts available in the local checkout.

For branches such as:

```text
spec/soak-002-soak-runtime
```

PowerPack may resolve:

```text
specs/soak-002-soak-runtime/spec.md
```

when that association is unique.

If the branch cannot be associated with exactly one SPEC, local review fails closed with `BLOCKED_REVIEW_CONTEXT`. It must not fall back to a repository-wide review.

A PR is not required for local review. Passing `--pr` to a local review is rejected so PR context cannot accidentally leak into the local contract.

Example:

```bash
speckit-powerpack review run \
  --provider codex \
  --path . \
  --prompt-file review-request.md
```

PowerPack prepends authoritative context containing the current branch and current SPEC before sending the review instruction to the local provider.

## Web review

Web review means a review that depends on ChatGPT/ChatGPT Project context and the GitHub integration.

A GitHub pull request is mandatory and must be supplied explicitly:

```bash
speckit-powerpack review run \
  --provider web \
  --path . \
  --pr 123 \
  --github-plugin-authorized \
  --prompt-file review-request.md
```

A canonical URL is also accepted:

```bash
--pr https://github.com/owner/repository/pull/123
```

PowerPack validates that the PR repository matches the current repository `origin`. A PR belonging to another repository is rejected.

The Web prompt identifies the exact PR as authoritative and instructs the reviewer to use the ChatGPT/GitHub plugin or connector to inspect that PR. If the exact PR cannot be accessed, the review must stop as `BLOCKED_CONFIGURATION` rather than reviewing the repository generically.

## ChatGPT/GitHub plugin permission

The user must grant the ChatGPT/GitHub plugin or connector permission to access the repository before Web code review can be considered valid.

PowerPack currently cannot safely grant or independently verify this permission through a documented, stable OpenAI API. ChatGPT permissions and internal integration behavior are controlled by the platform and may change outside PowerPack.

For this reason, `--github-plugin-authorized` is an explicit user attestation. It means:

> The user has granted the ChatGPT/GitHub integration access to the repository required by this review.

The flag does not replace the actual ChatGPT permission. If the permission is absent, stale, revoked or insufficient, the Web reviewer must fail closed.

PowerPack must never persist GitHub credentials, ChatGPT cookies, MFA material or raw authorization tokens as review evidence.

## Project context is not PR evidence

A ChatGPT Project may contain useful instructions, discussions and domain context, but Project memory is not proof of the PR implementation.

For Web review:

```text
ChatGPT Project context
        +
explicit GitHub PR
        +
GitHub plugin access
        =
valid Web review context
```

A Project-context smoke test remains a transport/context test. It does not substitute for a PR code review.

## Fail-closed rules

The following conditions block Web review:

- missing `--pr`;
- invalid PR number or URL;
- PR repository differs from local `origin`;
- missing `--github-plugin-authorized` attestation;
- GitHub plugin cannot access the exact PR;
- ChatGPT Project binding is required by the selected provider but unavailable.

The following conditions block local review:

- detached HEAD;
- no `specs/` directory;
- current branch cannot be mapped to exactly one SPEC;
- ambiguous branch-to-SPEC mapping.

No blocked condition may be converted into an approval or generic fallback review.

## Homologation implications

H1 (Codex/local, no Project) must prove:

- local provider selected;
- current branch detected;
- current SPEC detected;
- no PR required;
- Web path remains unavailable without binding.

H2/H4 Web-capable scenarios must additionally receive an explicit PR and confirmation that GitHub plugin permission was granted. Their evidence must identify the exact canonical PR URL used for the review.

The transport-only Project smoke can still run without a PR, but it must be labelled as context smoke and cannot mark Web code review as homologated by itself.
