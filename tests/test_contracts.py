from pathlib import Path
import json
import yaml

ROOT = Path(__file__).parents[1]

def load_yaml(path):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))

def test_public_surface_and_runtime_variants():
    ext = load_yaml("extensions/powerpack/extension.yml")
    assert [c["name"] for c in ext["provides"]["commands"]] == [
        "speckit.powerpack.deliver",
        "speckit.powerpack.doctor",
    ]
    for command in ("deliver", "doctor"):
        body = (ROOT / f"extensions/powerpack/commands/{command}.md").read_text(encoding="utf-8")
        for token in ("sh:", "ps:", "py:", "{SCRIPT}"):
            assert token in body
        assert (ROOT / f"extensions/powerpack/scripts/bash/{command}.sh").is_file()
        assert (ROOT / f"extensions/powerpack/scripts/powershell/{command}.ps1").is_file()
        assert (ROOT / f"extensions/powerpack/scripts/python/{command}.py").is_file()

def test_workflow_orders_checklist_analyze_implement_converge_review():
    text = (ROOT / "workflows/powerpack-delivery/workflow.yml").read_text(encoding="utf-8")
    positions = [
        text.index("id: checklist-convergence"),
        text.index("id: analyze"),
        text.index("id: implementation-plan"),
        text.index("id: implement-pending"),
        text.index("id: convergence"),
        text.index("id: review-convergence"),
    ]
    assert positions == sorted(positions)
    assert "command: speckit.converge" in text
    assert "command: speckit.implement" in text
    assert "action: task-plan" in text

def test_review_findings_are_materialized_as_tasks_before_implementation():
    workflow = (ROOT / "workflows/powerpack-delivery/workflow.yml").read_text(encoding="utf-8")
    assert "id: plan-review-remediation" in workflow
    assert "Do not implement product code" in workflow
    assert "Mark a task [P] only" in workflow
    assert "id: implement-review-findings" in workflow
    assert "command: speckit.implement" in workflow

def test_review_findings_are_all_mandatory_and_documented():
    workflow = (ROOT / "workflows/powerpack-delivery/workflow.yml").read_text(encoding="utf-8")
    review = (ROOT / "steps/powerpack-control/deep-review-protocol.md").read_text(encoding="utf-8")
    spec = (ROOT / "specs/001-powerpack-delivery/spec.md").read_text(encoding="utf-8")
    for token in ("Every finding is mandatory", "suggestions, nits, warnings"):
        assert token in workflow
    assert "every emitted finding is mandatory current-delivery work" in review
    assert "FR-011" in spec and "suggestions, nits, warnings" in spec
    assert "FR-012" in spec and "project documentation" in spec

def test_step_catalog_packages_full_control_step():
    catalog = json.loads((ROOT / "catalogs/step-catalog.json").read_text(encoding="utf-8"))
    step = catalog["steps"]["powerpack-control"]
    assert step["version"] == "0.4.0"
    assert set(step["extra_files"]) == {"state.py", "review.py", "deep-review-protocol.md"}

def test_active_runtime_does_not_reference_archive():
    for root in (ROOT / "extensions", ROOT / "workflows", ROOT / "steps"):
        for path in root.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="ignore")
                assert "backup/" not in text
                assert "backup\\\\" not in text
