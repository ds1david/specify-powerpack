# Web2API Project-context smoke baseline

## Historical point recovered

The repository previously had a functional ChatGPT Project smoke whose default prompt was:

```text
me diga qual é o nome do projeto e sua principal missão, produza uma resposta simplificada de no máximo 100 palavras. e me responda quanto é 1 +1
```

The prompt originated in the bound-project Web smoke line and was later reused by the ChatGPT-Web2API reviewer path on `main`.

Relevant historical commits include:

```text
f4ab14b  feat(review): add bound-project Web smoke execution
9cd1af2  feat(review): expose functional bound-project smoke test
16fa319  test(review): cover functional bound-project smoke contract
47cd1b2  docs(review): document Web2API functional smoke flow
65846fb  Merge PR #5: functional ChatGPT Project reviewer bridge
```

The original Web2API smoke validated arithmetic (`1 + 1 = 2`) and the 100-word limit. The new homologation smoke adds one deterministic Project-context check: the Project name returned by Web2API `/v1/projects` must also appear in the assistant response.

## Purpose

This smoke is intentionally independent from GitHub plugin work.

It answers only:

```text
Can the pinned ChatGPT-Web2API service:
  1. see the requested ChatGPT Project,
  2. send a normal prompt scoped to that Project,
  3. receive a complete assistant response,
  4. observe the Project name in that response,
  5. answer 1 + 1 = 2,
  6. keep the response at <= 100 words?
```

If this smoke passes while the GitHub-enabled probe fails, the evidence isolates the regression/capability gap to GitHub connector materialization rather than general Project navigation or prompt execution.

## Runtime topology

```text
WSL smoke_chatgpt_project_web2api.py
  -> Windows PowerShell lifecycle
  -> pinned ChatGPT-Web2API service
  -> persistent headed Chrome profile
  -> GET /v1/projects
  -> POST /v1/chat/completions
       project_id = g-p-...
       messages = historical smoke prompt
  -> real ChatGPT frontend turn
  -> Web2API response
  -> local content checks
```

This smoke does not use:

```text
~/.codex/auth.json
ChatGPTBackendClient
browserless connector discovery
@GitHub
manual /backend-api/f/conversation submit
raw browser cookies/tokens
```

## Same profile as GitHub probe

Defaults intentionally match the GitHub Web2API probe:

```text
REST port: 8097
CDP port:  9231
profile:   web2api-github-probe
```

This lets the baseline smoke and GitHub capability probe exercise the same browser session and Web2API installation.

## Run

First discover/copy the desired `g-p-...` Project id using the existing Project discovery flow, then run:

```bash
uv run python scripts/homologation/smoke_chatgpt_project_web2api.py \
  --project-id g-p-REPLACE_ME \
  --include-assistant-text

echo "EXIT=$?"
```

After the first successful installation/login, the faster rerun is:

```bash
uv run python scripts/homologation/smoke_chatgpt_project_web2api.py \
  --project-id g-p-REPLACE_ME \
  --include-assistant-text \
  --no-install
```

## PASS contract

`WEB2API_PROJECT_CONTEXT_SMOKE_PASSED` requires all of:

```text
Web2API /health reachable                    PASS
Web2API /v1/projects reachable               PASS
exact g-p Project visible                    PASS
/v1/chat/completions returned assistant text PASS
Project name appears in response             PASS
1 + 1 = 2                                    PASS
response <= 100 words                        PASS
```

A response that merely contains `2` but does not identify the Project is not accepted by this new smoke.

## Comparison with GitHub probe

The intended diagnostic sequence is:

```text
A. Project-context smoke
   -> baseline normal Project prompt

B. GitHub-enabled Web2API probe
   -> same Web2API/Chrome profile
   -> @GitHub materialization gate
```

Interpretation:

```text
A PASS + B FAIL
  => normal Project prompt path works; GitHub connector capability is the gap

A FAIL + B FAIL
  => do not debug GitHub yet; restore baseline Web2API/Project functionality first

A PASS + B PASS
  => proceed to exact Project + PR review homologation
```
