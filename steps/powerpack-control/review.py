from __future__ import annotations

import base64
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any
import urllib.error
import urllib.request

from .state import git, resolve_feature_dir

BACKEND_API = "https://chatgpt.com/backend-api"
CODEX_APPS_SERVER = "codex_apps"
REQUIREMENT_ID = re.compile(r"\b((?:FR|NFR|REQ|SC|AC|UC)-?\d{1,4})\b", re.IGNORECASE)

class ReviewError(RuntimeError):
    pass

def _repository(remote: str) -> str:
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", remote.strip())
    if not match:
        raise ReviewError("origin is not a github.com repository")
    return match.group(1)

def _spec_context(feature: Path) -> str:
    sections: list[str] = []
    for name in ("spec.md", "plan.md", "tasks.md", "research.md", "data-model.md", "quickstart.md"):
        path = feature / name
        if path.is_file():
            sections.append(f"### {name}\n{path.read_text(encoding='utf-8', errors='replace')}")
    for dirname in ("contracts", "checklists"):
        directory = feature / dirname
        if directory.is_dir():
            for path in sorted(p for p in directory.rglob("*") if p.is_file()):
                sections.append(f"### {path.relative_to(feature).as_posix()}\n{path.read_text(encoding='utf-8', errors='replace')}")
    text = "\n\n".join(sections)
    if not text.strip():
        raise ReviewError("active SPEC has no readable artifacts")
    return text[:96000]

def _account_id(token: str) -> str:
    parts = token.split(".")
    if len(parts) < 2:
        return ""
    try:
        body = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(body.encode()).decode("utf-8"))
    except Exception:
        return ""
    auth = claims.get("https://api.openai.com/auth") if isinstance(claims, dict) else None
    return str(auth.get("chatgpt_account_id") or "") if isinstance(auth, dict) else ""

def _auth() -> tuple[str, str]:
    path = Path.home() / ".codex" / "auth.json"
    if not path.is_file():
        raise ReviewError("Codex authentication missing; run 'codex login'")
    payload = json.loads(path.read_text(encoding="utf-8"))
    tokens = payload.get("tokens") if isinstance(payload, dict) else None
    if not isinstance(tokens, dict):
        raise ReviewError("Codex authentication has no tokens object")
    token = str(tokens.get("access_token") or "").strip()
    account = str(tokens.get("account_id") or "").strip() or _account_id(token)
    if not token or not account:
        raise ReviewError("Codex authentication is incomplete")
    return token, account

def _request(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    token, account = _auth()
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        BACKEND_API + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "ChatGPT-Account-ID": account,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "specify-powerpack/0.4",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ReviewError(f"ChatGPT backend HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise ReviewError(f"Cannot reach ChatGPT backend: {exc}") from exc
    return json.loads(raw) if raw.strip() else {}

def _connector() -> str:
    installed = _request("GET", "/ps/plugins/installed?limit=1000")
    plugins = installed.get("plugins") if isinstance(installed, dict) else []
    ids: list[str] = []
    for item in plugins if isinstance(plugins, list) else []:
        if not isinstance(item, dict):
            continue
        release = item.get("release") if isinstance(item.get("release"), dict) else {}
        names = {
            str(item.get("name") or "").casefold(),
            str(item.get("display_name") or "").casefold(),
            str(release.get("display_name") or "").casefold(),
        }
        if "github" not in names or str(item.get("status") or "").upper() != "ENABLED":
            continue
        values = [item.get("connector_id"), item.get("canonical_app_id"), *(release.get("app_ids") or [])]
        found = list(dict.fromkeys(str(v) for v in values if isinstance(v, str) and v.startswith("connector_")))
        if len(found) == 1:
            ids.append(found[0])
    if len(ids) != 1:
        raise ReviewError(f"Expected exactly one enabled GitHub connector, found {len(ids)}")
    availability = _request("POST", "/apps/availability?platform=chat&locale=en-US", {"app_ids": [ids[0]]})
    apps = availability.get("apps") if isinstance(availability, dict) else []
    app = next((x for x in apps if isinstance(x, dict) and x.get("id") == ids[0]), None)
    if not app or app.get("installed") is not True or app.get("available") is not True:
        raise ReviewError("GitHub connector is not installed and available")
    return ids[0]

def _requirements(text: str) -> list[str]:
    return sorted({m.group(1).upper() for m in REQUIREMENT_ID.finditer(text)})

def _prompt(repository: str, branch: str, head: str, feature: Path, context: str, previous: str) -> str:
    protocol = (Path(__file__).parent / "deep-review-protocol.md").read_text(encoding="utf-8")
    requirements = _requirements(context)
    return f"""# Specify PowerPack independent delivery review

Repository: {repository}
Local branch: {branch}
Local full HEAD: {head}
Active SPEC: {feature.name}

Use the installed GitHub App for ALL repository and Pull Request evidence.
Resolve exactly one open PR whose head branch is the branch above. Its full PR
head SHA MUST equal the local full HEAD. Otherwise return BLOCKED.

Do not use local shell commands, generic web search, PR descriptions, CI status,
or implementer claims as evidence. Review is read-only; never mutate GitHub.

Expected requirement IDs:
{json.dumps(requirements, ensure_ascii=False)}

<spec_context>
{context}
</spec_context>

<review_protocol>
{protocol}
</review_protocol>

<previous_review>
{previous[:40000] if previous.strip() else "NONE — first review round"}
</previous_review>

Required procedure:
1. Bind repository, PR number, base ref/SHA, merge base, full head SHA and complete changed-file list.
2. Build the normative model from the active SPEC before deciding the verdict.
3. Inspect every changed file plus callers, callees, contracts, schemas, config and tests needed for blast radius.
4. Cover every mandatory review front. NOT_APPLICABLE requires concrete evidence.
5. Continue after the first defect. Complete all fronts and a second systematic pass.
6. Revalidate every previous finding explicitly.
7. Adversarially challenge the tentative verdict.
8. Return one JSON object only.

A finding requires a current authority_ref. Generic best practice, preference,
or hypothetical future capability is insufficient. Do not invent backlog work.
However, do not suppress a current evidence-backed issue because its severity is
low or because it would normally be called a suggestion, nit, hardening item, or
documentation improvement. Under PowerPack every emitted finding is mandatory
current-delivery work and therefore requires CHANGES_REQUIRED until remediated.

Every finding must include id, authority_ref, severity, category, title, file,
evidence, failure_scenario, actual_behavior, required_behavior, behavioral_impact,
required_change and acceptance_criteria.

Return JSON containing schema, verdict, review_context, coverage and findings.
review_context must contain repository, pull_request_number, base_ref, base_sha,
merge_base and head_sha. coverage must contain changed_files, requirements,
inspection_evidence, fronts, previous_findings, verdict_challenge and context_gaps.

APPROVED requires zero findings, no material context gaps, complete changed-file
and requirement coverage, all mandatory fronts covered, and a survived
evidence-backed adversarial verdict challenge.
"""

def _walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)

def _run_codex(project: Path, connector: str, prompt: str, model: str, effort: str) -> str:
    codex = shutil.which("codex")
    if not codex:
        raise ReviewError("Codex CLI not found on PATH")
    command = [codex, "exec", "--json", "--ephemeral", "--sandbox", "read-only", "-C", str(project)]
    if model:
        command.extend(["-m", model])
    if effort:
        command.extend(["-c", f'model_reasoning_effort="{effort}"'])
    command.append(f"[$github](app://{connector})\n\n{prompt}")
    result = subprocess.run(command, text=True, capture_output=True, timeout=1800, check=False)
    if result.returncode != 0:
        raise ReviewError((result.stderr or result.stdout or "Codex review failed").strip())

    messages: list[str] = []
    completed = successful = shell = web = 0
    github_evidence = turn_completed = turn_failed = False
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        kind = str(event.get("type") or "")
        turn_completed = turn_completed or kind == "turn.completed"
        turn_failed = turn_failed or kind in {"turn.failed", "error"}
        item = event.get("item") if isinstance(event.get("item"), dict) else None
        if not item:
            continue
        item_type = str(item.get("type") or "")
        if item_type == "agent_message" and isinstance(item.get("text"), str):
            messages.append(item["text"])
        elif item_type == "command_execution":
            shell += 1
        elif item_type == "web_search":
            web += 1
        elif item_type == "mcp_tool_call" and str(item.get("server") or "") == CODEX_APPS_SERVER:
            if str(item.get("status") or "") == "completed" and item.get("error") is None:
                completed += 1
                successful += int(item.get("result") is not None)
            for value in _walk(item):
                if isinstance(value, str) and (value == connector or "github" in value.casefold()):
                    github_evidence = True
    if shell or web:
        raise ReviewError("Reviewer used forbidden local-shell or generic web-search evidence")
    if not turn_completed or turn_failed or completed < 1 or successful < 1 or not github_evidence:
        raise ReviewError("Reviewer did not produce attributable successful GitHub MCP evidence")
    return "\n".join(x.strip() for x in messages if x.strip()).strip()

def _json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ReviewError("Reviewer did not return a JSON object")

def _validate(review: dict[str, Any], head: str, expected_requirements: list[str]) -> str:
    verdict = str(review.get("verdict") or "").upper()
    if verdict not in {"APPROVED", "CHANGES_REQUIRED", "BLOCKED"}:
        raise ReviewError(f"Invalid verdict: {verdict or '<missing>'}")
    context = review.get("review_context")
    if not isinstance(context, dict) or str(context.get("head_sha") or "").lower() != head.lower():
        raise ReviewError("review_context.head_sha does not match the local full HEAD")
    findings = review.get("findings")
    if not isinstance(findings, list):
        raise ReviewError("findings must be an array")
    if verdict == "APPROVED" and findings:
        raise ReviewError("APPROVED cannot contain findings")
    if verdict == "CHANGES_REQUIRED" and not findings:
        raise ReviewError("CHANGES_REQUIRED requires at least one finding")
    coverage = review.get("coverage")
    if not isinstance(coverage, dict):
        raise ReviewError("coverage must be an object")
    for key in ("changed_files", "requirements", "inspection_evidence", "fronts", "previous_findings", "verdict_challenge", "context_gaps"):
        if key not in coverage:
            raise ReviewError(f"coverage.{key} is missing")
    if expected_requirements:
        actual = coverage.get("requirements")
        if not isinstance(actual, list):
            raise ReviewError("coverage.requirements must be an array")
        ids: list[str] = []
        for item in actual:
            if isinstance(item, str):
                ids.append(item)
            elif isinstance(item, dict) and isinstance(item.get("id"), str):
                ids.append(item["id"])
        if sorted(ids) != expected_requirements:
            raise ReviewError("coverage.requirements does not exactly match SPEC requirement IDs")
    return verdict

def run_review(project: Path, *, target: str, model: str, effort: str) -> dict[str, Any]:
    feature = resolve_feature_dir(project, target, require=True)
    branch = git(project, "branch", "--show-current")
    head = git(project, "rev-parse", "HEAD")
    repository = _repository(git(project, "remote", "get-url", "origin"))
    context = _spec_context(feature)
    review_dir = project / ".specify" / "powerpack" / "delivery" / "reviews"
    review_dir.mkdir(parents=True, exist_ok=True)
    current = review_dir / "current.json"
    previous = current.read_text(encoding="utf-8", errors="replace") if current.is_file() else ""

    connector = _connector()
    assistant = _run_codex(project, connector, _prompt(repository, branch, head, feature, context, previous), model, effort)
    review = _json_object(assistant)
    verdict = _validate(review, head, _requirements(context))

    rendered = json.dumps(review, indent=2, ensure_ascii=False) + "\n"
    current.write_text(rendered, encoding="utf-8")
    (review_dir / f"{head[:12]}.json").write_text(rendered, encoding="utf-8")

    return {
        "verdict": verdict,
        "review_file": str(current),
        "head_sha": head,
        "pull_request_number": review.get("review_context", {}).get("pull_request_number"),
    }
