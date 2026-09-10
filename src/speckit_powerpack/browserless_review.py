from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from .backend_compat import install_backend_compat
from .chatgpt_project_provider import ChatGPTBackendClient, ChatGPTProjectError
from .codex_apps_runtime import (
    CodexAppsError,
    make_progress_reporter,
    parse_codex_jsonl,
    require_github_tool_evidence,
    run_codex_exec,
)
from .github_connector_discovery import GitHubConnectorDiscoveryError, discover_github_connector
from .review_context import (
    PullRequestTarget,
    ReviewSnapshot,
    build_snapshot,
    current_head,
    resolve_pull_request,
    resolve_spec_context,
)


install_backend_compat()

PRODUCT_NAME = "Specify PowerPack"
CANONICAL_CLI = "specify-powerpack"
PROJECT_AUTHORIZATION = "codex-backend-api"
PROJECT_PROVIDER = "chatgpt-project"
REVIEW_BACKEND = "codex-apps-github"
REQUIREMENT_ID = re.compile(r"\b((?:FR|NFR|REQ|SC|AC|UC)-?\d{1,4})\b", re.IGNORECASE)
CHALLENGE_RESULTS = {"SURVIVED", "FINDING", "BLOCKED", "NOT_APPLICABLE"}


class BrowserlessReviewError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProjectBinding:
    project_id: str
    project_name: str
    project_url: str | None


@dataclass(frozen=True)
class BrowserlessReviewResult:
    review: dict[str, Any]
    output_path: Path
    snapshot: ReviewSnapshot
    project: ProjectBinding
    github_tools: tuple[str, ...]
    snapshot_tools: tuple[str, ...]


def load_project_binding(project: Path) -> ProjectBinding:
    path = project / ".specify" / "powerpack" / "review.json"
    if not path.is_file():
        raise BrowserlessReviewError(
            f"PowerPack review config is missing. Install {PRODUCT_NAME} and run '{CANONICAL_CLI} review setup --path .' first."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BrowserlessReviewError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("provider") != PROJECT_PROVIDER:
        raise BrowserlessReviewError(
            f"Repository is not bound to a ChatGPT Project. Run '{CANONICAL_CLI} review setup --path .' and select one."
        )
    binding = data.get("chatgpt_project") if isinstance(data.get("chatgpt_project"), dict) else {}
    if not binding:
        legacy = data.get("chatgpt_web") if isinstance(data.get("chatgpt_web"), dict) else {}
        binding = legacy
    project_id = str(binding.get("project_id") or "").strip()
    project_name = str(binding.get("project_name") or "").strip()
    authorization = str(binding.get("authorization") or "").strip()
    if not project_id.startswith("g-p-") or not project_name:
        raise BrowserlessReviewError("ChatGPT Project binding is incomplete.")
    if authorization != PROJECT_AUTHORIZATION:
        raise BrowserlessReviewError(
            f"ChatGPT Project binding authorization must be {PROJECT_AUTHORIZATION}; found {authorization or '<missing>'}."
        )
    return ProjectBinding(project_id, project_name, str(binding.get("project_url") or "").strip() or None)


def _extract_json(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, count=1, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw, count=1)
    decoder = json.JSONDecoder()
    for index, char in enumerate(raw):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(raw[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise BrowserlessReviewError("Reviewer did not return a JSON object.")


def _requirement_ids(spec_context: str) -> tuple[str, ...]:
    return tuple(sorted({match.group(1).upper() for match in REQUIREMENT_ID.finditer(spec_context or "")}))


def _snapshot_prompt(target: PullRequestTarget, connector_id: str) -> str:
    return f"""This is phase 1 of a read-only {PRODUCT_NAME} code review.

Use exclusively the installed GitHub App selected by this explicit Codex App mention:
[$github](app://{connector_id})

Resolve the immutable identity of exactly this pull request:
repository: {target.repository}
pull_request_number: {target.number}
pull_request_url: {target.url}

You MUST use GitHub tools. Inspect the PR metadata and complete changed-file list. Resolve the merge base between the PR base SHA and head SHA through GitHub tooling if it is not already present in PR metadata. Follow pagination until the changed-file list is complete.

Do not run shell commands. Do not inspect the local checkout. Do not use web search. Do not mutate GitHub.

Return JSON only with exactly these semantic fields:
{{
  "repository": "owner/repo",
  "pull_request_number": 1,
  "base_ref": "base branch name",
  "base_sha": "40-char SHA",
  "merge_base": "40-char SHA",
  "head_sha": "40-char SHA",
  "changed_files": ["complete/path/a", "complete/path/b"]
}}
"""


def _review_prompt(
    *,
    connector_id: str,
    snapshot: ReviewSnapshot,
    project_name: str,
    project_context: str,
    spec_context: str,
    protocol: str,
    user_instruction: str,
    previous_review: str,
) -> str:
    previous_block = previous_review.strip() or "NONE — first review round"
    requirements = list(_requirement_ids(spec_context))
    return f"""You are the mandatory independent browserless code-review gate for {PRODUCT_NAME}.

Use exclusively the installed GitHub App selected by this explicit Codex App mention for PR/repository evidence:
[$github](app://{connector_id})

IMMUTABLE REVIEW SNAPSHOT — authoritative; do not substitute another PR or snapshot:
{json.dumps(snapshot.as_dict(), ensure_ascii=False, indent=2)}

EXPECTED REQUIREMENT IDS — coverage.requirements must contain exactly this set when non-empty:
{json.dumps(requirements, ensure_ascii=False)}

The local implementation HEAD has already been verified by {PRODUCT_NAME} to equal the PR head SHA. Use GitHub tools to inspect the exact PR, complete diff, every changed file and all related source/tests/contracts needed to establish blast radius. Follow pagination. Do not rely on the PR description or CI as proof.

CHATGPT PROJECT CONTEXT — serialized read-only background memory:
<project_context>
{project_context[:24000]}
</project_context>

ACTIVE SPEC KIT CONTEXT — authoritative requirements:
<spec_context>
{spec_context[:48000]}
</spec_context>

DEEP REVIEW PROTOCOL — mandatory:
<review_protocol>
{protocol[:18000]}
</review_protocol>

PREVIOUS REVIEW — validate every previous finding when present:
<previous_review>
{previous_block[:24000]}
</previous_review>

USER REVIEW INSTRUCTION:
{user_instruction.strip() or 'Perform the complete deep review for the immutable snapshot.'}

Rules:
- Read-only. Never mutate GitHub or the local repository.
- Do not run shell commands and do not use web search; GitHub evidence must come through the selected GitHub App.
- Inspect every changed file. Read related files through GitHub when required for correctness.
- Project context is background memory; SPEC + immutable PR evidence are authoritative when they conflict.
- Return one schema 2.0 review JSON object only, no Markdown fences or prose before/after it.
- review_context MUST exactly equal the immutable snapshot fields spec_id/base_ref/base_sha/merge_base/head_sha/snapshot_sha256 above.
- coverage.changed_files MUST exactly equal the immutable snapshot changed_files list.
- coverage.requirements MUST contain exactly the EXPECTED REQUIREMENT IDS above when that list is non-empty; do not silently omit requirements.
- coverage.inspection_evidence MUST contain one object per changed file with fields file and evidence describing what was inspected.
- coverage.verdict_challenge MUST contain strongest_counterexample, result and non-empty evidence. APPROVED requires result SURVIVED or evidence-backed NOT_APPLICABLE.
- coverage.context_gaps MUST be a list. If material Project-only knowledge is absent from durable repository evidence, describe it there and do not APPROVE.
- Add this extra top-level object so {PRODUCT_NAME} can prove Project context was actually consumed:
  "project_context_evidence": {{
    "project_name": "{project_name}",
    "literal_evidence": "3 to 20 consecutive words copied literally from the serialized Project context, not merely the Project name"
  }}
- If responsible review is impossible, return a structurally valid BLOCKED review rather than APPROVED.
"""


def _normalize_spaces(value: str) -> str:
    return " ".join((value or "").split())


def _validate_project_evidence(review: dict[str, Any], *, project_name: str, project_context: str) -> None:
    evidence = review.get("project_context_evidence")
    if not isinstance(evidence, dict):
        raise BrowserlessReviewError("Review is missing project_context_evidence.")
    returned_name = str(evidence.get("project_name") or "").strip()
    if returned_name.casefold() != project_name.casefold():
        raise BrowserlessReviewError("Reviewer did not identify the bound ChatGPT Project correctly.")
    literal = _normalize_spaces(str(evidence.get("literal_evidence") or ""))
    words = literal.split()
    if not (3 <= len(words) <= 20):
        raise BrowserlessReviewError("project_context_evidence.literal_evidence must contain 3 to 20 words.")
    if literal.casefold() == project_name.casefold():
        raise BrowserlessReviewError("Project context evidence cannot be only the Project name.")
    if literal.casefold() not in _normalize_spaces(project_context).casefold():
        raise BrowserlessReviewError("Project context evidence is not a literal excerpt from the serialized Project context.")


def _validate_snapshot_contract(review: dict[str, Any], snapshot: ReviewSnapshot) -> None:
    context = review.get("review_context")
    if not isinstance(context, dict):
        raise BrowserlessReviewError("Review is missing review_context.")
    for key, expected in snapshot.review_context().items():
        if str(context.get(key) or "").strip().casefold() != str(expected).casefold():
            raise BrowserlessReviewError(f"Review context field {key} does not match immutable snapshot.")
    coverage = review.get("coverage")
    if not isinstance(coverage, dict):
        raise BrowserlessReviewError("Review is missing coverage.")
    changed = coverage.get("changed_files")
    if not isinstance(changed, list) or set(map(str, changed)) != set(snapshot.changed_files):
        raise BrowserlessReviewError("coverage.changed_files does not exactly match the immutable PR changed-file list.")


def _validate_hardened_review_contract(
    review: dict[str, Any],
    *,
    snapshot: ReviewSnapshot,
    spec_context: str,
) -> None:
    coverage = review.get("coverage")
    if not isinstance(coverage, dict):
        raise BrowserlessReviewError("Review is missing coverage.")

    expected_requirements = set(_requirement_ids(spec_context))
    actual_requirements = {
        str(item.get("id") or "").upper()
        for item in coverage.get("requirements", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    if expected_requirements and actual_requirements != expected_requirements:
        missing = sorted(expected_requirements - actual_requirements)
        extra = sorted(actual_requirements - expected_requirements)
        raise BrowserlessReviewError(
            "coverage.requirements does not exactly match active SPEC requirement IDs; "
            f"missing={missing}, extra={extra}."
        )

    raw_inspection = coverage.get("inspection_evidence")
    if not isinstance(raw_inspection, list):
        raise BrowserlessReviewError("coverage.inspection_evidence must be a list.")
    evidence_by_file: set[str] = set()
    for index, item in enumerate(raw_inspection):
        if not isinstance(item, dict):
            raise BrowserlessReviewError(f"coverage.inspection_evidence[{index}] must be an object.")
        path = str(item.get("file") or "").strip()
        evidence = str(item.get("evidence") or "").strip()
        if not path or len(evidence) < 8:
            raise BrowserlessReviewError(
                f"coverage.inspection_evidence[{index}] requires file and concrete evidence."
            )
        evidence_by_file.add(path)
    missing_evidence = sorted(set(snapshot.changed_files) - evidence_by_file)
    if missing_evidence:
        raise BrowserlessReviewError(
            "Every changed file requires inspection evidence: " + ", ".join(missing_evidence)
        )

    challenge = coverage.get("verdict_challenge")
    if not isinstance(challenge, dict):
        raise BrowserlessReviewError("coverage.verdict_challenge is required.")
    challenge_result = str(challenge.get("result") or "").strip()
    if challenge_result not in CHALLENGE_RESULTS:
        raise BrowserlessReviewError("coverage.verdict_challenge.result is invalid.")
    if not str(challenge.get("strongest_counterexample") or "").strip():
        raise BrowserlessReviewError("coverage.verdict_challenge.strongest_counterexample is required.")
    challenge_evidence = challenge.get("evidence")
    if not isinstance(challenge_evidence, list) or not challenge_evidence:
        raise BrowserlessReviewError("coverage.verdict_challenge.evidence must not be empty.")
    if review.get("verdict") == "APPROVED" and challenge_result not in {"SURVIVED", "NOT_APPLICABLE"}:
        raise BrowserlessReviewError(
            "APPROVED requires verdict challenge SURVIVED or evidence-backed NOT_APPLICABLE."
        )

    context_gaps = coverage.get("context_gaps")
    if not isinstance(context_gaps, list):
        raise BrowserlessReviewError("coverage.context_gaps must be a list.")
    if review.get("verdict") == "APPROVED" and context_gaps:
        raise BrowserlessReviewError("APPROVED is forbidden while coverage.context_gaps is non-empty.")


def _validate_protocol(project: Path, review_path: Path, previous: Path | None) -> None:
    validator = project / ".specify" / "powerpack" / "bin" / "review_protocol.py"
    if not validator.is_file():
        raise BrowserlessReviewError(f"Installed review protocol validator is missing: {validator}")
    command = [sys.executable, str(validator), "validate", "--input", str(review_path)]
    if previous:
        command.extend(["--previous", str(previous)])
    proc = subprocess.run(command, cwd=project, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        detail = (proc.stdout or proc.stderr or "review protocol validation failed").strip()
        raise BrowserlessReviewError(detail)


def _default_output(project: Path, snapshot: ReviewSnapshot) -> Path:
    root = project / ".specify" / "powerpack" / "reviews"
    root.mkdir(parents=True, exist_ok=True)
    safe_spec = re.sub(r"[^A-Za-z0-9_.-]+", "-", snapshot.spec_id).strip("-") or "spec"
    return root / f"{safe_spec}-pr{snapshot.pull_request_number}-{snapshot.head_sha[:12]}.json"


def run_browserless_code_review(
    *,
    project_path: Path,
    pull_request: str | int,
    prompt: str = "",
    output: Path | None = None,
    previous: Path | None = None,
    model: str = "gpt-5.6-sol",
    effort: str = "xhigh",
    timeout: int = 600,
    max_project_conversations: int = 2,
    locale: str = "pt-BR",
    verbose: bool = False,
) -> BrowserlessReviewResult:
    project_path = project_path.resolve()
    if not project_path.is_dir():
        raise BrowserlessReviewError(f"Repository path does not exist: {project_path}")

    def _progress_for(phase: str):
        return make_progress_reporter(phase, sys.stderr) if verbose else None
    binding = load_project_binding(project_path)
    target = resolve_pull_request(project_path, pull_request)
    spec = resolve_spec_context(project_path)
    local_head = current_head(project_path)

    client = ChatGPTBackendClient()
    try:
        client.validate_auth()
        github = discover_github_connector(client, locale=locale)
        project, project_context = client.build_project_context(
            binding.project_id,
            max_conversations=max(0, min(max_project_conversations, 4)),
            max_chars=32_000,
        )
    except (ChatGPTProjectError, GitHubConnectorDiscoveryError) as exc:
        raise BrowserlessReviewError(str(exc)) from exc
    if project.id != binding.project_id or project.name.casefold() != binding.project_name.casefold():
        raise BrowserlessReviewError("Serialized ChatGPT Project does not match the repository binding.")

    if verbose:
        print("  [snapshot] resolving the immutable PR manifest via the GitHub App…", file=sys.stderr, flush=True)
    snapshot_turn = run_codex_exec(
        project_path=project_path,
        model=model,
        effort=effort,
        prompt=_snapshot_prompt(target, github.connector_id),
        timeout=min(timeout, 300),
        progress=_progress_for("snapshot"),
    )
    if snapshot_turn.returncode != 0:
        raise BrowserlessReviewError((snapshot_turn.stderr or snapshot_turn.stdout or "snapshot turn failed").strip())
    snapshot_events = parse_codex_jsonl(snapshot_turn.stdout, connector_id=github.connector_id)
    try:
        require_github_tool_evidence(snapshot_events)
    except CodexAppsError as exc:
        raise BrowserlessReviewError(f"PR snapshot discovery failed: {exc}") from exc
    snapshot_payload = _extract_json(str(snapshot_events.get("assistant_text") or ""))
    snapshot = build_snapshot(
        target=target,
        spec_id=spec.spec_id,
        payload=snapshot_payload,
        local_head=local_head,
    )

    protocol_path = project_path / ".specify" / "powerpack" / "deep-review-protocol.md"
    if not protocol_path.is_file():
        raise BrowserlessReviewError(f"Installed Deep Review Protocol is missing: {protocol_path}")
    protocol = protocol_path.read_text(encoding="utf-8", errors="replace")
    previous_text = ""
    if previous:
        if not previous.is_file():
            raise BrowserlessReviewError(f"Previous review does not exist: {previous}")
        previous_text = previous.read_text(encoding="utf-8", errors="replace")

    if verbose:
        print(
            f"  [review] deep review starting — model={model} effort={effort} "
            f"timeout={timeout}s (an xhigh review of a large delta can take 10–40 min)",
            file=sys.stderr, flush=True,
        )
    review_turn = run_codex_exec(
        project_path=project_path,
        model=model,
        effort=effort,
        prompt=_review_prompt(
            connector_id=github.connector_id,
            snapshot=snapshot,
            project_name=binding.project_name,
            project_context=project_context,
            spec_context=spec.serialized,
            protocol=protocol,
            user_instruction=prompt,
            previous_review=previous_text,
        ),
        timeout=timeout,
        progress=_progress_for("review"),
    )
    if review_turn.returncode != 0:
        raise BrowserlessReviewError((review_turn.stderr or review_turn.stdout or "review turn failed").strip())
    review_events = parse_codex_jsonl(review_turn.stdout, connector_id=github.connector_id)
    try:
        require_github_tool_evidence(review_events)
    except CodexAppsError as exc:
        raise BrowserlessReviewError(f"Deep review GitHub evidence failed: {exc}") from exc
    review = _extract_json(str(review_events.get("assistant_text") or ""))
    _validate_snapshot_contract(review, snapshot)
    _validate_hardened_review_contract(review, snapshot=snapshot, spec_context=spec.serialized)
    _validate_project_evidence(review, project_name=binding.project_name, project_context=project_context)

    output_path = (output or _default_output(project_path, snapshot)).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _validate_protocol(project_path, output_path, previous)

    return BrowserlessReviewResult(
        review=review,
        output_path=output_path,
        snapshot=snapshot,
        project=binding,
        github_tools=tuple(review_events.get("codex_apps_tools") or ()),
        snapshot_tools=tuple(snapshot_events.get("codex_apps_tools") or ()),
    )
