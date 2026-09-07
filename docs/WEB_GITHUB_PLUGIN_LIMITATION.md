# Web PR review and ChatGPT/GitHub plugin evidence

## Current limitation

The browserless `ChatGPTProjectProvider` currently builds ChatGPT Project context and sends a text request through the ChatGPT Codex response endpoint. The current request path does not expose a PowerPack-controlled contract for enabling the ChatGPT/GitHub plugin, selecting its repository permission, or recording verifiable GitHub connector tool-use evidence.

Because of that, PowerPack must not equate any of the following with proof that the GitHub plugin inspected a pull request:

- the user having connected GitHub in ChatGPT;
- a Project being accessible;
- the reviewer mentioning the PR number or URL;
- the reviewer describing repository files from Project memory;
- a user attestation by itself.

`--github-plugin-authorized` records only that the user states the ChatGPT/GitHub integration has been granted repository access. It does not prove that the current backend review invocation actually used that integration.

## Required end state

A Web PR code review is considered fully supported only when the transport can produce objective evidence that:

1. an explicit `--pr` identified the exact GitHub pull request;
2. the PR repository matches the local repository origin;
3. the ChatGPT/GitHub plugin or connector has repository permission;
4. the actual review invocation used the GitHub integration to inspect that exact PR;
5. the evidence identifies the PR base/head and changed-file scope inspected by the reviewer.

Until item 4 can be verified by the transport, Web PR review must be treated as a capability still requiring hardening. Project-context smoke tests remain valid transport/context tests but are not proof of GitHub PR code review.

## Why this is fail-closed

The ChatGPT Web/backend integration used by PowerPack is not a documented stable OpenAI API contract for GitHub plugin orchestration. Platform behavior may change independently of PowerPack. A reviewer must therefore never return an accepted Web PR approval when the GitHub integration could not be objectively shown to have accessed the target PR.

## Local review is unaffected

Local review does not require the ChatGPT/GitHub plugin or a pull request. Its evidence authority is the current Git branch plus the current Spec Kit SPEC associated with that branch.
