from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from .backend_compat import install_backend_compat
from .chatgpt_project_provider import ChatGPTBackendClient, ChatGPTProjectError
from .github_connector_discovery import GitHubConnectorDiscoveryError, discover_github_connector
from .chatgpt_web_review import ChatGPTWebReviewClient, ChatGPTWebReviewError
from .review_context import (
    PullRequestTarget,
    ReviewSnapshot,
    build_snapshot,
    current_head,
    git,
    resolve_pull_request,
    resolve_spec_context,
)


install_backend_compat()

PRODUCT_NAME = "Specify PowerPack"
CANONICAL_CLI = "specify-powerpack"
PROJECT_AUTHORIZATION = "codex-backend-api"
PROJECT_PROVIDER = "chatgpt-project"
REVIEW_BACKEND = "codex-apps-github"
REQUIREMENT_ID = re.compile(r"\b((?:FR|NFR|REQ|SC|AC|UC)-?\d{1,4}[A-Za-z]?)\b", re.IGNORECASE)
CANONICAL_REQUIREMENT_ID = re.compile(
    r"^(FR|NFR|REQ|SC|AC|UC)-?(\d{1,4})([A-Za-z]?)$", re.IGNORECASE
)
CHALLENGE_RESULTS = {"SURVIVED", "FINDING", "BLOCKED", "NOT_APPLICABLE"}
MASTER_PROMPT_VERSION = "1.0"
REVIEW_PROTOCOL_VERSION = "3.0"


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
    github_call_count: int = 0


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
    candidates: list[dict[str, Any]] = []
    for index, char in enumerate(raw):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(raw[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append(value)
    review_candidates = [
        value for value in candidates if "verdict" in value and "review_context" in value
    ]
    if review_candidates:
        # A continuation can contain an earlier incomplete object followed by
        # the evidence-complete final object. The last matching object is the
        # final protocol result, not the first progress snapshot.
        return review_candidates[-1]
    if candidates:
        raise BrowserlessReviewError("Reviewer returned JSON, but not the required final code-review object.")
    raise BrowserlessReviewError("Reviewer did not return a JSON object.")


def _canonical_requirement_id(value: object) -> str | None:
    match = CANONICAL_REQUIREMENT_ID.fullmatch(str(value or "").strip())
    if not match:
        return None
    return f"{match.group(1).upper()}-{match.group(2)}{match.group(3).upper()}"


def _requirement_ids(spec_context: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                canonical
                for match in REQUIREMENT_ID.finditer(spec_context or "")
                if (canonical := _canonical_requirement_id(match.group(1))) is not None
            }
        )
    )


def _merge_requirement_repair(
    original: dict[str, Any],
    repaired: dict[str, Any],
    expected_requirement_ids: set[str],
) -> dict[str, Any]:
    """Accept only requirement coverage from a coverage-repair continuation.

    The first review remains authoritative for every other field. This keeps a
    continuation opened only to fill requirement coverage from rewriting the
    verdict, findings, snapshot context, or changed-file evidence.
    """
    repaired_coverage = repaired.get("coverage")
    repaired_requirements = (
        repaired_coverage.get("requirements")
        if isinstance(repaired_coverage, dict)
        else None
    )
    if not isinstance(repaired_requirements, list):
        raise BrowserlessReviewError("Coverage repair did not return coverage.requirements.")
    canonical_requirements: list[dict[str, Any]] = []
    repaired_ids: set[str] = set()
    for item in repaired_requirements:
        if not isinstance(item, dict):
            continue
        canonical = _canonical_requirement_id(item.get("id"))
        if canonical is None:
            continue
        normalized_item = dict(item)
        normalized_item["id"] = canonical
        canonical_requirements.append(normalized_item)
        repaired_ids.add(canonical)
    if repaired_ids != expected_requirement_ids or len(canonical_requirements) != len(expected_requirement_ids):
        missing = sorted(expected_requirement_ids - repaired_ids)
        extra = sorted(repaired_ids - expected_requirement_ids)
        raise BrowserlessReviewError(
            "Coverage repair returned the wrong requirement IDs; "
            f"missing={missing}, extra={extra}."
        )
    merged = dict(original)
    merged_coverage = dict(original.get("coverage") or {})
    merged_coverage["requirements"] = canonical_requirements
    merged["coverage"] = merged_coverage
    return merged


def _changed_files_for_snapshot(review: dict[str, Any]) -> tuple[list[Any] | None, bool]:
    """Extract the changed-file set without accepting ambiguous reviewer prose."""
    coverage = review.get("coverage") or {}
    raw = coverage.get("changed_files") if "changed_files" in coverage else review.get("changed_files")
    if isinstance(raw, list):
        return raw, False
    if isinstance(raw, dict):
        for key in ("files", "paths", "changed_files"):
            value = raw.get(key)
            if isinstance(value, list):
                return value, True
        keys = list(raw.keys())
        if keys and all(
            isinstance(key, str)
            and key.strip()
            and not key.startswith(("_", "total", "count", "status"))
            and ("/" in key or "." in Path(key).name)
            for key in keys
        ):
            return keys, True
    return None, False


def _snapshot_prompt(target: PullRequestTarget, connector_id: str, *, project_context: str = "") -> str:
    return f"""This is phase 1 of a read-only {PRODUCT_NAME} code review.

Use exclusively the installed GitHub connector selected dynamically for this turn:
plugin:{connector_id} (the transport will emit the matching @Github ecosystem mention).

CHATGPT PROJECT CONTEXT — serialized read-only background memory (present in every phase):
<project_context>
{(project_context or "NONE — the bound ChatGPT Project has no readable context")[:12000]}
</project_context>

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


def _master_prompt_path(project: Path) -> Path:
    path = project / ".specify" / "powerpack" / "master-review-prompt.md"
    if not path.is_file():
        raise BrowserlessReviewError(f"Installed Master Review Prompt is missing: {path}")
    return path


def _review_packet(
    *,
    target: PullRequestTarget,
    spec: Any,
    snapshot: ReviewSnapshot | None,
    project: ProjectBinding,
    project_context: str,
    protocol: str,
    previous_review: dict[str, Any] | None,
    round_number: int,
    attempt: int,
    segment: int,
    master_prompt: str,
    current_head_sha: str,
) -> dict[str, Any]:
    previous_context = (previous_review or {}).get("review_context") or {}
    previous_findings = (previous_review or {}).get("findings") or []
    if not previous_findings:
        previous_findings = ((previous_review or {}).get("coverage") or {}).get("previous_findings") or []
    return {
        "review_id": f"{target.repository}#{target.number}:{spec.spec_id}:implement-review",
        "round": round_number,
        "attempt": attempt,
        "conversation_segment": segment,
        "repository": target.repository,
        "pull_request": target.url,
        "active_spec": f"specs/{spec.spec_id}/",
        "current_head_sha": snapshot.head_sha if snapshot else current_head_sha,
        "current_snapshot_sha256": snapshot.snapshot_sha256 if snapshot else None,
        "previous_snapshot_sha256": previous_context.get("snapshot_sha256") or None,
        "master_prompt": {
            "version": MASTER_PROMPT_VERSION,
            "sha256": hashlib.sha256(master_prompt.encode("utf-8")).hexdigest(),
        },
        "review_protocol": {
            "version": REVIEW_PROTOCOL_VERSION,
            "sha256": hashlib.sha256(protocol.encode("utf-8")).hexdigest(),
        },
        "checkpoint": {
            "last_completed_round": max(0, round_number - 1),
            "open_findings": [item for item in previous_findings if isinstance(item, dict)],
            "resolved_findings": [],
            "previous_review_context": previous_context,
        },
        "project_context": {
            "project_name": project.project_name,
            "context": project_context[:24_000],
            "authority": "supplemental-only",
        },
    }


def _master_review_prompt(master_prompt: str, packet: dict[str, Any], *, target: PullRequestTarget) -> str:
    return f"""{master_prompt}

======================================================================
POWERPACK REVIEW PACKET — VARIABLE EXECUTION STATE
======================================================================

<POWERPACK_REVIEW_PACKET>
{json.dumps(packet, ensure_ascii=False, indent=2)}
</POWERPACK_REVIEW_PACKET>

TASK

Use @GitHub exclusively for evidence from {target.repository} PR #{target.number}.
This is the implementation code review itself, not a homologation probe. Do
not answer the old probe questions about Project mission, repository lists or
changed filenames as standalone tasks. First resolve the immutable PR evidence,
then read the active SPEC and perform the complete Master Code Review. Continue
after the first blocker and return one final JSON object only. Do not return a
tool call, progress note or partial answer as the final result.
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

Use exclusively the installed GitHub connector selected dynamically for PR/repository evidence:
plugin:{connector_id} (the transport will emit the matching @Github ecosystem mention).

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
        canonical
        for item in coverage.get("requirements", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
        if (canonical := _canonical_requirement_id(item.get("id"))) is not None
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

    divergences = review.get("review_divergences")
    if not isinstance(divergences, list):
        raise BrowserlessReviewError("review_divergences must be a list.")
    if review.get("verdict") == "APPROVED" and divergences:
        raise BrowserlessReviewError("APPROVED is forbidden while review_divergences is non-empty.")

    for index, finding in enumerate(review.get("findings") or []):
        if not isinstance(finding, dict):
            raise BrowserlessReviewError(f"findings[{index}] must be an object.")
        required = ("authority_ref", "implementation_evidence", "failure_scenario", "required_change")
        missing = [field for field in required if not str(finding.get(field) or "").strip()]
        if missing:
            raise BrowserlessReviewError(
                f"findings[{index}] is missing causal authority/evidence fields: {', '.join(missing)}"
            )


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
    ephemeral: bool = True,
    round_number: int | None = None,
    attempt: int = 1,
    segment: int = 1,
) -> BrowserlessReviewResult:
    project_path = project_path.resolve()
    if not project_path.is_dir():
        raise BrowserlessReviewError(f"Repository path does not exist: {project_path}")

    def _log(kind: str, msg: str) -> None:
        # kind: "browserless" = a chatgpt.com/backend-api call;
        #       "codex"       = retained for compatibility with older logs.
        if verbose:
            print(f"  [{kind}] {msg}", file=sys.stderr, flush=True)

    binding = load_project_binding(project_path)
    target = resolve_pull_request(project_path, pull_request)
    spec = resolve_spec_context(project_path)
    local_head = current_head(project_path)

    client = ChatGPTBackendClient()
    try:
        _log("browserless", "checking auth + rate limit (/backend-api/wham/usage)…")
        usage = client.validate_auth()
        rl = usage.get("rate_limit") if isinstance(usage, dict) else None
        if isinstance(rl, dict) and rl.get("limit_reached"):
            reset = int((rl.get("primary_window") or {}).get("reset_after_seconds") or 0)
            raise BrowserlessReviewError(
                f"Codex rate limit reached (plan={usage.get('plan_type')}); the primary window "
                f"resets in ~{reset // 60} min. Re-run after that — a review turn would fail mid-way "
                "and still bill the tokens it used."
            )
        _log("browserless", "discovering the GitHub connector (/backend-api/aip/connectors …)…")
        github = discover_github_connector(client, locale=locale)
        _log("browserless", f"reading ChatGPT Project context (/backend-api/gizmos/{binding.project_id} …)…")
        project, project_context = client.build_project_context(
            binding.project_id,
            max_conversations=max(0, min(max_project_conversations, 4)),
            max_chars=32_000,
        )
        _log("browserless", f"Project '{project.name}' bound; GitHub connector {github.connector_id}")
    except (ChatGPTProjectError, GitHubConnectorDiscoveryError) as exc:
        raise BrowserlessReviewError(str(exc)) from exc
    if project.id != binding.project_id or project.name.casefold() != binding.project_name.casefold():
        raise BrowserlessReviewError("Serialized ChatGPT Project does not match the repository binding.")

    try:
        web = ChatGPTWebReviewClient()
    except ChatGPTWebReviewError as exc:
        raise BrowserlessReviewError(str(exc)) from exc

    protocol_path = project_path / ".specify" / "powerpack" / "deep-review-protocol.md"
    if not protocol_path.is_file():
        raise BrowserlessReviewError(f"Installed Deep Review Protocol is missing: {protocol_path}")
    protocol = protocol_path.read_text(encoding="utf-8", errors="replace")
    master_path = _master_prompt_path(project_path)
    master_prompt = master_path.read_text(encoding="utf-8", errors="replace")
    previous_text = ""
    previous_review: dict[str, Any] | None = None
    if previous:
        if not previous.is_file():
            raise BrowserlessReviewError(f"Previous review does not exist: {previous}")
        previous_text = previous.read_text(encoding="utf-8", errors="replace")
        try:
            parsed_previous = json.loads(previous_text)
        except json.JSONDecodeError as exc:
            raise BrowserlessReviewError(f"Previous review is not valid JSON: {previous}") from exc
        if not isinstance(parsed_previous, dict):
            raise BrowserlessReviewError(f"Previous review must be a JSON object: {previous}")
        previous_review = parsed_previous
    if round_number is None:
        previous_round = int((previous_review or {}).get("round") or 0)
        round_number = previous_round + 1 if previous_review else 1
    packet = _review_packet(
        target=target,
        spec=spec,
        snapshot=None,
        project=binding,
        project_context=project_context,
        protocol=protocol,
        previous_review=previous_review,
        round_number=round_number,
        attempt=attempt,
        segment=segment,
        master_prompt=master_prompt,
        current_head_sha=local_head,
    )
    output_path_hint = (output.resolve() if output else project_path / ".specify" / "powerpack" / "reviews" / f"round-{round_number}-pr{target.number}.json")
    packet_path = output_path_hint.with_name(output_path_hint.stem + "-packet.json")
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _log("browserless", f"ChatGPT Web Master Review — round={round_number} attempt={attempt} segment={segment}")
    review_prompt = (
        _master_review_prompt(master_prompt, packet, target=target)
        + "\n\nADDITIONAL USER REVIEW INSTRUCTION:\n"
        + (prompt.strip() or "Perform the complete Master Code Review for this immutable snapshot.")
    )
    review_text = web.ask(
        review_prompt,
        project_id=binding.project_id,
        connector_id=github.connector_id,
        repository=target.repository,
        model=model,
        effort=effort,
    )
    review_tools = list(web.last_tool_invocations)
    try:
        review = _extract_json(review_text)
    except BrowserlessReviewError as first_error:
        # A connector may complete without an authorization gate but leave the
        # model at a tool boundary. Continue the same attempt/conversation only
        # to request the mandated final review object; this is not a new round
        # and does not replay any homologation probe.
        if not web.conversation_id or not web.last_tool_invocations:
            raise
        _log("browserless", "review stream ended at a tool boundary; requesting final JSON in the same segment…")
        continuation = web.ask(
            "Continue the same Master Code Review from the completed connector result. Do not repeat repository discovery. Return only the final structured JSON object required by the Master Prompt, including review_context and verdict.",
            project_id=binding.project_id,
            connector_id=github.connector_id,
            repository=target.repository,
            model=model,
            effort=effort,
            require_connector_evidence=False,
        )
        review_tools.extend(web.last_tool_invocations)
        try:
            review = _extract_json(continuation)
        except BrowserlessReviewError:
            raise first_error
    context = review.get("review_context") or {}
    coverage = review.get("coverage") or {}
    missing_snapshot_fields = [
        field
        for field in ("base_ref", "base_sha", "merge_base", "head_sha")
        if not context.get(field)
        or (field != "base_ref" and not re.fullmatch(r"[0-9a-fA-F]{40}", str(context.get(field))))
    ]
    if str(context.get("spec_id") or "").strip().casefold() != spec.spec_id.casefold():
        missing_snapshot_fields.append("spec_id")
    changed_files_value, normalized_changed_files = _changed_files_for_snapshot(review)
    prior_changed_files: list[Any] | None = None
    if normalized_changed_files:
        _log("browserless", "review evidence shape: normalized changed_files mapping keys to snapshot paths")
    invalid_changed_files = not isinstance(changed_files_value, list) or not changed_files_value
    if invalid_changed_files:
        _log(
            "browserless",
            "review evidence shape: top_keys="
            + ",".join(sorted(str(key) for key in review.keys()))
            + " coverage_keys="
            + ",".join(sorted(str(key) for key in coverage.keys()))
            + " changed_files_type="
            + type(changed_files_value).__name__
            + " changed_files_len="
            + str(len(changed_files_value) if hasattr(changed_files_value, "__len__") else 0),
        )
    if (missing_snapshot_fields or invalid_changed_files) and web.conversation_id and review_tools:
        _log(
            "browserless",
            "review object is missing immutable snapshot fields "
            + ", ".join(missing_snapshot_fields)
            + (", changed_files array" if invalid_changed_files else "")
            + "; requesting evidence-complete JSON in the same segment…",
        )
        continuation = web.ask(
            f"The review object is incomplete. Continue the same review and use @GitHub to resolve the immutable PR snapshot. Return only one complete final JSON object. Its review_context MUST include spec_id exactly {spec.spec_id!r}, base_ref and full 40-character hexadecimal base_sha, merge_base, and head_sha values, plus the complete changed_files list under coverage.changed_files. Never abbreviate a SHA or rename the SPEC. If the snapshot cannot be proven, return verdict BLOCKED with context_gaps explaining the exact missing evidence.",
            project_id=binding.project_id,
            connector_id=github.connector_id,
            repository=target.repository,
            model=model,
            effort=effort,
            require_connector_evidence=False,
        )
        review_tools.extend(web.last_tool_invocations)
        prior_changed_files, _ = _changed_files_for_snapshot(review)
        review = _extract_json(continuation)
        completed_changed_files, _ = _changed_files_for_snapshot(review)
        if (not completed_changed_files) and prior_changed_files:
            review.setdefault("coverage", {})["changed_files"] = prior_changed_files
            _log("browserless", "review evidence shape: retained prior non-empty changed_files evidence")
    context = review.get("review_context") or {}
    coverage = review.get("coverage") or {}
    changed_files_value, normalized_changed_files = _changed_files_for_snapshot(review)
    if (not isinstance(changed_files_value, list) or not changed_files_value) and all(
        re.fullmatch(r"[0-9a-fA-F]{40}", str(context.get(field) or ""))
        for field in ("merge_base", "head_sha")
    ):
        try:
            local_files = [
                item.strip()
                for item in git(project_path, "diff", "--name-only", f"{context['merge_base']}..{context['head_sha']}").splitlines()
                if item.strip()
            ]
        except Exception as exc:
            local_files = []
            _log("browserless", f"local changed-file fallback unavailable: {type(exc).__name__}")
        if local_files:
            changed_files_value = local_files
            _log("browserless", "review evidence shape: used immutable local diff for missing changed_files")
    snapshot_payload = {
        "repository": target.repository,
        "pull_request_number": target.number,
        "base_ref": context.get("base_ref"),
        "base_sha": context.get("base_sha"),
        "merge_base": context.get("merge_base"),
        "head_sha": context.get("head_sha"),
        "changed_files": changed_files_value,
    }
    snapshot = build_snapshot(
        target=target,
        spec_id=spec.spec_id,
        payload=snapshot_payload,
        local_head=local_head,
    )
    if str(context.get("snapshot_sha256") or "").strip().casefold() != snapshot.snapshot_sha256.casefold():
        _log("browserless", "review snapshot hash differs from immutable packet; requesting exact hash in the same segment…")
        continuation = web.ask(
            f"Return the same final review JSON again with review_context exactly bound to the immutable snapshot. Set review_context.snapshot_sha256 to this exact lowercase SHA-256 value: {snapshot.snapshot_sha256}. Preserve all findings, coverage and changed-file evidence; do not recalculate or abbreviate it.",
            project_id=binding.project_id,
            connector_id=github.connector_id,
            repository=target.repository,
            model=model,
            effort=effort,
            require_connector_evidence=False,
        )
        review_tools.extend(web.last_tool_invocations)
        review = _extract_json(continuation)
        review_context = review.get("review_context") or {}
        review_coverage = review.get("coverage") or {}
        review_files, _ = _changed_files_for_snapshot(review)
        if not review_files:
            review.setdefault("coverage", {})["changed_files"] = list(snapshot.changed_files)
    expected_requirement_ids = set(_requirement_ids(spec.serialized))
    actual_requirement_ids = {
        str(item.get("id") or "").upper()
        for item in (review.get("coverage") or {}).get("requirements", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    if expected_requirement_ids and actual_requirement_ids != expected_requirement_ids:
        _log("browserless", "review requirement coverage differs from active SPEC; requesting exact requirement set in the same segment…")
        continuation = web.ask(
            "Return the same final review JSON again. Preserve the immutable review_context, findings and changed-file evidence. Set coverage.requirements to an array containing exactly these requirement IDs, with one evidence-backed status object for each: "
            + json.dumps(sorted(expected_requirement_ids), ensure_ascii=False),
            project_id=binding.project_id,
            connector_id=github.connector_id,
            repository=target.repository,
            model=model,
            effort=effort,
            require_connector_evidence=False,
        )
        review_tools.extend(web.last_tool_invocations)
        repaired_review = _extract_json(continuation)
        review = _merge_requirement_repair(
            review,
            repaired_review,
            expected_requirement_ids,
        )
        requirement_files, _ = _changed_files_for_snapshot(review)
        if not requirement_files:
            review.setdefault("coverage", {})["changed_files"] = list(snapshot.changed_files)
    output_path = (output or _default_output(project_path, snapshot)).resolve()
    packet_path = output_path.with_name(output_path.stem + "-packet.json")
    packet.update({
        "current_head_sha": snapshot.head_sha,
        "current_snapshot_sha256": snapshot.snapshot_sha256,
    })
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    review.setdefault("lineage", packet)
    review.setdefault("powerpack_checkpoint", packet["checkpoint"])
    coverage = review.setdefault("coverage", {})
    if "previous_findings" in review and "previous_findings" not in coverage:
        coverage["previous_findings"] = review["previous_findings"]
    _validate_snapshot_contract(review, snapshot)
    _validate_hardened_review_contract(review, snapshot=snapshot, spec_context=spec.serialized)
    _validate_project_evidence(review, project_name=binding.project_name, project_context=project_context)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _validate_protocol(project_path, output_path, previous)

    return BrowserlessReviewResult(
        review=review,
        output_path=output_path,
        snapshot=snapshot,
        project=binding,
        github_tools=review_tools,
        snapshot_tools=(),
        github_call_count=len(review_tools),
    )
