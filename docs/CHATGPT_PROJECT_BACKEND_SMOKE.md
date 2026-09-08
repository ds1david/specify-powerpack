# Recovered browserless ChatGPT Project smoke

## Purpose

This smoke reproduces the browserless Project-context flow that worked before the GitHub connector experiments.

It is intentionally separate from ChatGPT-Web2API, Chrome, CDP, Playwright and direct `/backend-api/f/conversation` reconstruction.

## Recovered sequence

```text
1. Codex CLI authentication already exists in ~/.codex/auth.json
2. PowerPack review setup discovers ChatGPT Projects through backend reads
3. The local repository is bound to one Project
4. PowerPack reads Project metadata/context through ChatGPT backend APIs
5. PowerPack sends the historical smoke prompt through /backend-api/codex/responses
6. The response is checked for Project name, 1+1=2, and <=100 words
```

The repository binding written by `review setup` is expected to contain:

```text
provider=chatgpt-project
chatgpt_web.mode=backend-api
chatgpt_web.authorization=codex-backend-api
chatgpt_web.project_id=g-p-...
chatgpt_web.project_name=...
```

## Historical prompt

```text
me diga qual é o nome do projeto e sua principal missão, produza uma resposta simplificada de no máximo 100 palavras. e me responda quanto é 1 +1
```

This is the same prompt installed by `src/speckit_powerpack/project_context_smoke.py`.

## Runtime path

```text
~/.codex/auth.json
        |
        v
ChatGPTBackendClient
        |
        +-- GET /backend-api/gizmos/{project_id}
        +-- GET /backend-api/gizmos/{project_id}/conversations
        +-- GET /backend-api/conversation/{conversation_id}
        |
        v
build_project_context()
        |
        v
POST /backend-api/codex/responses
        |
        v
assistant response
```

No browser process is started by this smoke.

## Bind first

From the repository that will be associated with a ChatGPT Project:

```bash
speckit-powerpack review setup --path .
```

Choose to link a Project and select the intended Project from the discovered list.

To inspect the persisted binding:

```bash
cat .specify/powerpack/review.json
```

Do not publish this file if it contains environment-specific information you do not intend to share.

## Execute the standalone smoke

From the PowerPack checkout:

```bash
uv run python scripts/homologation/smoke_chatgpt_project_backend.py \
  --path /path/to/bound/repository \
  --include-assistant-text
```

Expected classification:

```text
CHATGPT_PROJECT_BACKEND_SMOKE_PASSED
```

Required evidence:

```text
binding_provider=chatgpt-project
binding_mode=backend-api
binding_authorization=codex-backend-api
binding_matches_review_result=true
response_non_empty=true
project_name_present=true
one_plus_one_equals_two=true
max_100_words=true
```

## Why this baseline matters

If this smoke passes while the GitHub-enabled prompt path fails, the failure is not in basic account auth, Project discovery/binding, Project context retrieval, or the Codex response endpoint. It isolates the remaining problem to the extra GitHub connector/tool materialization path.
