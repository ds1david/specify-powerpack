from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

SCHEMA_VERSION = "2.0"
FRONTS = (
    "SPEC_COMPLIANCE",
    "BEHAVIORAL_REGRESSION",
    "ARCHITECTURE_AND_CONTRACTS",
    "STATE_CONCURRENCY_AND_FAILURES",
    "PERSISTENCE_DETERMINISM_IDEMPOTENCY",
    "TESTS_AND_COMPOSITION_ROOT",
    "DOCUMENTATION_AND_OPERABILITY",
    "SECURITY_AND_SCOPE",
)
FRONT_STATUSES = {"PASS", "FINDINGS", "BLOCKED", "NOT_APPLICABLE"}
REQUIREMENT_STATUSES = {"PASS", "PARTIAL", "FAIL", "NOT_APPLICABLE"}
BASELINE_RESULTS = {"PRESERVED", "CHANGED_AS_SPECIFIED", "REGRESSION", "NOT_APPLICABLE"}
PREVIOUS_FINDING_STATUSES = {
    "NEW", "NEWLY_DISCOVERED", "STILL_OPEN", "PARTIALLY_RESOLVED",
    "RESOLVED", "INVALIDATED", "REGRESSED", "NOT_RESOLVED",
}
VERDICTS = {"APPROVED", "CHANGES_REQUIRED", "BLOCKED"}
CHALLENGE_RESULTS = {"SURVIVED", "FINDING", "BLOCKED", "NOT_APPLICABLE"}
FINDING_FIELDS = {
    "id", "severity", "category", "title", "file", "line", "evidence",
    "authority_ref", "implementation_evidence", "failure_scenario",
    "actual_behavior", "required_behavior", "behavioral_impact", "required_change",
    "acceptance_criteria", "lifecycle_state",
}
CONTEXT_FIELDS = {"spec_id", "base_ref", "base_sha", "merge_base", "head_sha", "snapshot_sha256"}
HEX40 = re.compile(r"^[0-9a-fA-F]{40}$")
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
REPEATED_PREFIX = "BLOCKED_REPEATED_FINDING:"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("review JSON must be an object")
    return data


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def finding_fingerprint(finding: dict[str, Any]) -> str:
    canonical = "|".join(
        [
            _norm(finding.get("category")),
            _norm(finding.get("title")),
            _norm(finding.get("file")),
            _norm(finding.get("line")),
            _norm(finding.get("failure_scenario")),
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_review(review: dict[str, Any], previous: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    if review.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    verdict = review.get("verdict")
    if verdict not in VERDICTS:
        errors.append(f"verdict must be one of {sorted(VERDICTS)}")

    context = review.get("review_context")
    if not isinstance(context, dict):
        errors.append("review_context must be an object")
        context = {}
    for field in sorted(CONTEXT_FIELDS):
        if not context.get(field):
            errors.append(f"review_context.{field} is required")
    for field in ("base_sha", "merge_base", "head_sha"):
        value = context.get(field)
        if value and not HEX40.match(str(value)):
            errors.append(f"review_context.{field} must be a full 40-character Git SHA")
    digest = context.get("snapshot_sha256")
    if digest and not HEX64.match(str(digest)):
        errors.append("review_context.snapshot_sha256 must be a 64-character SHA-256 digest")

    coverage = review.get("coverage")
    if not isinstance(coverage, dict):
        errors.append("coverage must be an object")
        coverage = {}

    changed = _list(coverage.get("changed_files"))
    inspected = _list(coverage.get("inspected_files"))
    requirements = _list(coverage.get("requirements"))
    baselines = _list(coverage.get("baseline_scenarios"))
    previous_findings = _list(coverage.get("previous_findings"))
    fronts = _list(coverage.get("fronts"))

    if not changed:
        errors.append("coverage.changed_files must not be empty")
    if not inspected:
        errors.append("coverage.inspected_files must not be empty")
    missing_inspection = sorted(set(changed) - set(inspected))
    if missing_inspection:
        errors.append("every changed file must be inspected: " + ", ".join(missing_inspection))
    if context.get("spec_id") and not requirements:
        errors.append("coverage.requirements must not be empty when spec_id is present")
    if not baselines:
        errors.append("coverage.baseline_scenarios must not be empty")

    inspection = coverage.get("inspection_evidence")
    evidence_by_file: set[str] = set()
    if not isinstance(inspection, list):
        errors.append("coverage.inspection_evidence must be a list")
    else:
        for index, item in enumerate(inspection):
            if not isinstance(item, dict):
                errors.append(f"coverage.inspection_evidence[{index}] must be an object")
                continue
            raw_file = str(item.get("file") or "").strip()
            evidence = str(item.get("evidence") or "").strip()
            if raw_file:
                evidence_by_file.add(raw_file)
            if not raw_file or len(evidence) < 8:
                errors.append(f"coverage.inspection_evidence[{index}] requires file and concrete evidence")
        missing_evidence = sorted(set(map(str, changed)) - evidence_by_file)
        if missing_evidence:
            errors.append("every changed file requires inspection evidence: " + ", ".join(missing_evidence))

    challenge = coverage.get("verdict_challenge")
    challenge_result = None
    if not isinstance(challenge, dict):
        errors.append("coverage.verdict_challenge is required")
    else:
        challenge_result = challenge.get("result")
        if challenge_result not in CHALLENGE_RESULTS:
            errors.append("coverage.verdict_challenge.result is invalid")
        if not str(challenge.get("strongest_counterexample") or "").strip():
            errors.append("coverage.verdict_challenge.strongest_counterexample is required")
        if not _list(challenge.get("evidence")):
            errors.append("coverage.verdict_challenge.evidence must not be empty")

    context_gaps = coverage.get("context_gaps")
    if not isinstance(context_gaps, list):
        errors.append("coverage.context_gaps must be a list")
        context_gaps = []

    for index, item in enumerate(requirements):
        if not isinstance(item, dict) or item.get("status") not in REQUIREMENT_STATUSES:
            errors.append(f"coverage.requirements[{index}].status is invalid")
        elif not _list(item.get("evidence")):
            errors.append(f"coverage.requirements[{index}].evidence must not be empty")
    for index, item in enumerate(baselines):
        if not isinstance(item, dict) or item.get("result") not in BASELINE_RESULTS:
            errors.append(f"coverage.baseline_scenarios[{index}].result is invalid")
        elif not _list(item.get("evidence")):
            errors.append(f"coverage.baseline_scenarios[{index}].evidence must not be empty")

    front_names: list[str] = []
    for index, item in enumerate(fronts):
        if not isinstance(item, dict):
            errors.append(f"coverage.fronts[{index}] must be an object")
            continue
        name, status = item.get("name"), item.get("status")
        if name:
            front_names.append(str(name))
        if status not in FRONT_STATUSES:
            errors.append(f"coverage.fronts[{index}].status is invalid")
        if not _list(item.get("evidence")):
            errors.append(f"coverage.fronts[{index}].evidence must not be empty")
    if set(front_names) != set(FRONTS) or len(front_names) != len(FRONTS):
        errors.append("coverage.fronts must contain every required review front exactly once")

    findings = _list(review.get("findings"))
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            errors.append(f"findings[{index}] must be an object")
            continue
        missing = sorted(field for field in FINDING_FIELDS if field not in finding)
        if missing:
            errors.append(f"findings[{index}] missing fields: {', '.join(missing)}")
        if not _list(finding.get("acceptance_criteria")):
            errors.append(f"findings[{index}].acceptance_criteria must not be empty")
        if not str(finding.get("authority_ref") or "").strip():
            errors.append(f"findings[{index}].authority_ref is required")
        for field in ("implementation_evidence", "actual_behavior", "required_behavior"):
            if not str(finding.get(field) or "").strip():
                errors.append(f"findings[{index}].{field} is required")
        if finding.get("lifecycle_state") not in {
            "NEW", "NEWLY_DISCOVERED", "STILL_OPEN", "PARTIALLY_RESOLVED",
            "RESOLVED", "INVALIDATED", "REGRESSED",
        }:
            errors.append(f"findings[{index}].lifecycle_state is invalid")

    seen_previous: set[str] = set()
    prior_status_by_id: dict[str, str] = {}
    for index, item in enumerate(previous_findings):
        if not isinstance(item, dict):
            errors.append(f"coverage.previous_findings[{index}] must be an object")
            continue
        item_id = item.get("id")
        if item_id:
            seen_previous.add(str(item_id))
            prior_status_by_id[str(item_id)] = str(item.get("status") or "")
        if item.get("status") not in PREVIOUS_FINDING_STATUSES:
            errors.append(f"coverage.previous_findings[{index}].status is invalid")
        if not _list(item.get("evidence")):
            errors.append(f"coverage.previous_findings[{index}].evidence must not be empty")

    if previous is not None:
        previous_items = [item for item in _list(previous.get("findings")) if isinstance(item, dict)]
        expected = {str(item.get("id")) for item in previous_items if item.get("id")}
        if seen_previous != expected:
            errors.append("coverage.previous_findings must contain exactly every finding id from the previous review")

        previous_snapshot = ((previous.get("review_context") or {}).get("snapshot_sha256"))
        current_snapshot = ((review.get("review_context") or {}).get("snapshot_sha256"))
        if previous_snapshot and current_snapshot and previous_snapshot == current_snapshot:
            for item in previous_findings:
                if isinstance(item, dict) and item.get("status") in {"RESOLVED", "PARTIALLY_RESOLVED"}:
                    errors.append(
                        f"same snapshot forbids {item.get('status')} for previous finding {item.get('id')}"
                    )

        resolved_fingerprints: dict[str, str] = {}
        for item in previous_items:
            item_id = str(item.get("id") or "")
            if item_id and prior_status_by_id.get(item_id) == "RESOLVED":
                resolved_fingerprints[finding_fingerprint(item)] = item_id
        for current in findings:
            if not isinstance(current, dict):
                continue
            fingerprint = finding_fingerprint(current)
            if fingerprint in resolved_fingerprints:
                errors.append(
                    f"{REPEATED_PREFIX} previous finding {resolved_fingerprints[fingerprint]} was declared RESOLVED but materially reappeared as {current.get('id')}"
                )
    elif previous_findings:
        errors.append("coverage.previous_findings must be empty on the first review round")

    front_statuses = {item.get("status") for item in fronts if isinstance(item, dict)}
    if verdict == "APPROVED":
        if findings:
            errors.append("APPROVED requires findings: []")
        if any(item.get("status") in {"PARTIAL", "FAIL"} for item in requirements if isinstance(item, dict)):
            errors.append("APPROVED does not allow PARTIAL/FAIL requirements")
        if any(item.get("result") == "REGRESSION" for item in baselines if isinstance(item, dict)):
            errors.append("APPROVED does not allow baseline REGRESSION")
        if any(item.get("status") != "RESOLVED" for item in previous_findings if isinstance(item, dict)):
            errors.append("APPROVED requires every previous finding to be RESOLVED")
        if front_statuses - {"PASS", "NOT_APPLICABLE"}:
            errors.append("APPROVED requires every review front to PASS or be NOT_APPLICABLE")
        if challenge_result not in {"SURVIVED", "NOT_APPLICABLE"}:
            errors.append("APPROVED requires verdict challenge SURVIVED or NOT_APPLICABLE")
        if context_gaps:
            errors.append("APPROVED is forbidden while coverage.context_gaps is non-empty")
    elif verdict == "CHANGES_REQUIRED":
        if not findings:
            errors.append("CHANGES_REQUIRED requires at least one finding")
        if "FINDINGS" not in front_statuses:
            errors.append("CHANGES_REQUIRED requires at least one FINDINGS review front")
    elif verdict == "BLOCKED" and "BLOCKED" not in front_statuses:
        errors.append("BLOCKED requires at least one BLOCKED review front")

    return errors


def classify_errors(errors: list[str]) -> str:
    if any(error.startswith(REPEATED_PREFIX) for error in errors):
        return "BLOCKED_REPEATED_FINDING"
    if errors:
        return "BLOCKED_REVIEW_CONTRACT"
    return "VALID"


def cmd_validate(args: argparse.Namespace) -> int:
    review = load_json(Path(args.input))
    previous = load_json(Path(args.previous)) if args.previous else None
    errors = validate_review(review, previous)
    classification = classify_errors(errors)
    payload = {
        "valid": not errors,
        "classification": classification,
        "schema_version": SCHEMA_VERSION,
        "verdict": review.get("verdict"),
        "errors": errors,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else (3 if classification == "BLOCKED_REPEATED_FINDING" else 2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="powerpack-review-protocol")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--input", required=True)
    validate.add_argument("--previous")
    validate.set_defaults(func=cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
