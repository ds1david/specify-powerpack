# Browserless ChatGPT Project context smokes

This document defines two complementary browserless smokes for a repository already bound to a ChatGPT Project through `.specify/powerpack/review.json`.

Both smokes use the existing Codex authentication in `~/.codex/auth.json` and do not use Chrome, CDP, Playwright or Web2API.

## Smoke A — Project identity and abbreviated description

Script:

```text
scripts/homologation/smoke_chatgpt_project_identity.py
```

Purpose:

- require an existing repository → ChatGPT Project binding;
- use the browserless ChatGPT Project provider;
- ask for the exact Project name;
- ask for an abbreviated Project description with at most 100 words.

Expected final format from the model:

```text
PROJECT_NAME: <exact Project name>
PROJECT_DESCRIPTION: <one-line description, <=100 words>
POWERPACK_PROJECT_CONTEXT_OK
```

PASS requires:

- the provider result points to the same Project ID and Project name stored in the repository binding;
- the returned `PROJECT_NAME` exactly matches the configured Project name, case-insensitively;
- `PROJECT_DESCRIPTION` is non-empty and contains at most 100 words;
- the final marker is present.

The report deliberately describes this as `project_context_serialized=true` and `native_project_binding=false`: the ChatGPT Project is read through backend APIs and serialized into the model instructions; the generated response is not a native message written into the ChatGPT Project.

Run:

```bash
uv run python \
  scripts/homologation/smoke_chatgpt_project_identity.py \
  --path /home/david/workspace/autonomous-trading-strategy-evolution-lab \
  --include-assistant-text
```

Expected classification:

```text
CHATGPT_PROJECT_IDENTITY_SMOKE_PASSED
```

## Smoke B — Project context proof + GitHub repository listing in the same turn

Script:

```text
scripts/homologation/smoke_chatgpt_project_github_list_repos.py
```

Purpose:

- require the same repository → ChatGPT Project binding;
- serialize the bound Project context;
- prove that the Codex turn is actually consuming that serialized context, not merely recognizing the Project name;
- resolve the installed GitHub connector and active OAuth state;
- explicitly select GitHub in the Codex prompt through `[$github](app://<connector-id>)`;
- ask for Project name, abbreviated Project description, literal Project-context evidence, and all repositories accessible through the GitHub connector in the same Codex turn.

Expected final format:

```text
PROJECT_NAME: <exact Project name>
PROJECT_DESCRIPTION: <one-line Project description, <=100 words>
PROJECT_CONTEXT_EVIDENCE: <literal 3-20 word excerpt copied from serialized Project context>
REPO owner/name
REPO owner/name
...
TOTAL N
POWERPACK_PROJECT_GITHUB_OK
```

PASS requires both feature families to succeed simultaneously.

### Project context

- repository binding is valid;
- the serialized Project object matches the configured binding;
- `PROJECT_NAME` exactly matches the configured ChatGPT Project name;
- `PROJECT_DESCRIPTION` is non-empty and contains at most 100 words;
- `PROJECT_CONTEXT_EVIDENCE` contains 3-20 words;
- that evidence is found literally in the serialized `project_context` after whitespace normalization;
- the evidence is not merely the Project name;
- all of the above are summarized by `project_context.project_context_contract_passed=true`.

The literal-evidence assertion is intentionally stronger than checking the Project name alone. A model could potentially infer a familiar repository/project name from other local information; requiring a short exact excerpt that is present in the serialized ChatGPT Project material proves that the Project context reached the same Codex turn that also used GitHub.

### GitHub connector

- GitHub preflight passes;
- the resolved connector is bound by explicit `app://` mention;
- at least one `codex_apps` MCP call completes successfully;
- at least one successful MCP call contains a result;
- the MCP event is attributable to GitHub;
- no shell command or web-search fallback occurs;
- repository lines are unique and `TOTAL N` matches the unique count;
- the combined marker is present.

Run:

```bash
uv run python \
  scripts/homologation/smoke_chatgpt_project_github_list_repos.py \
  --path /home/david/workspace/autonomous-trading-strategy-evolution-lab \
  --include-repositories \
  --include-assistant-text
```

Expected classification:

```text
CHATGPT_PROJECT_GITHUB_LIST_REPOS_SMOKE_PASSED
```

Relevant Project evidence in the JSON report now includes:

```text
project_context.project_name_exact_match
project_context.project_description_returned
project_context.description_present
project_context.description_word_count
project_context.description_max_100_words
project_context.context_evidence_returned
project_context.context_evidence_word_count
project_context.context_evidence_length_valid
project_context.context_evidence_in_serialized_context
project_context.context_evidence_distinct_from_name
project_context.project_context_contract_passed
```

## Timing

Both smokes print step timing to stderr and include a structured `timing` block in the final JSON report. The combined smoke exposes separate timing for:

```text
validate_repository
load_project_binding
initialize_backend_client
github_chat_preflight
serialize_project_context
build_combined_prompt
codex_exec
parse_codex_jsonl
parse_combined_response
evaluate_contract
```

This allows Project-context reads to be distinguished from GitHub discovery and from the longer Codex/model/MCP turn.

## Contract tests

```bash
uv run --extra dev python -m pytest -q \
  tests/test_chatgpt_project_identity_smoke_contract.py \
  tests/test_chatgpt_project_github_list_repos_smoke_contract.py
```

The combined contract tests include negative cases proving that GitHub success is not enough: the smoke fails if the Project name is wrong, the Project description is missing, the literal context evidence is not actually present in the serialized Project context, or shell/web fallback occurs.

These are contract/unit tests only. Functional PASS must be established separately by running the two real smokes against the repository and the connected ChatGPT/GitHub account.
