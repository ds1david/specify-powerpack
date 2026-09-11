"""Deterministic, evidence-preserving normalization of Web review responses."""

from __future__ import annotations

from typing import Any

from .review_context import ReviewSnapshot


def _array_from_mapping(value: Any, *, key: str) -> list[Any] | None:
    if not isinstance(value, dict):
        return None
    if isinstance(value.get(key), list):
        return list(value[key])
    return None


def _inspection_array(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, dict):
        return None
    entries: list[dict[str, Any]] = []
    for path, evidence in value.items():
        if not isinstance(path, str) or not path.strip():
            continue
        if isinstance(evidence, dict):
            item = dict(evidence)
            item.setdefault("file", path)
        else:
            item = {"file": path, "evidence": evidence}
        entries.append(item)
    return entries


def _requirements_array(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, dict):
        return None
    entries: list[dict[str, Any]] = []
    for requirement_id, item in value.items():
        if not isinstance(requirement_id, str) or not requirement_id.strip():
            continue
        if isinstance(item, dict):
            normalized = dict(item)
            normalized.setdefault("id", requirement_id)
        else:
            normalized = {"id": requirement_id, "evidence": item}
        entries.append(normalized)
    return entries


def normalize_review_response(review: dict[str, Any], snapshot: ReviewSnapshot) -> dict[str, Any]:
    """Normalize transport shape while preserving semantic review authority.

    Snapshot identity and changed files come from the locally verified immutable
    packet. All semantic content (findings, verdict and evidence) is retained;
    missing semantic content is deliberately left for the protocol validator to
    reject rather than synthesized here.
    """
    normalized = dict(review)
    context = dict(normalized.get("review_context") or {})
    context.update(snapshot.review_context())
    normalized["review_context"] = context

    coverage = dict(normalized.get("coverage") or {})
    aliases = {
        "requirements": "requirements",
        "inspection_evidence": "inspection_evidence",
        "previous_findings": "previous_findings",
    }
    for field, coverage_field in aliases.items():
        if coverage_field not in coverage and field in normalized:
            coverage[coverage_field] = normalized[field]

    changed_files = coverage.get("changed_files", normalized.get("changed_files"))
    # The immutable snapshot is authoritative; this also removes abbreviated or
    # map-shaped changed-file representations without inventing paths.
    coverage["changed_files"] = list(snapshot.changed_files)

    if not isinstance(coverage.get("inspection_evidence"), list):
        converted = _inspection_array(coverage.get("inspection_evidence"))
        if converted is not None:
            coverage["inspection_evidence"] = converted

    if not isinstance(coverage.get("requirements"), list):
        converted = _requirements_array(coverage.get("requirements"))
        if converted is not None:
            coverage["requirements"] = converted

    for field in ("previous_findings",):
        if not isinstance(coverage.get(field), list):
            converted = _array_from_mapping(coverage.get(field), key=field)
            if converted is not None:
                coverage[field] = converted

    normalized["coverage"] = coverage
    return normalized
