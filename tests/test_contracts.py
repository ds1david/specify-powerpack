from pathlib import Path
import yaml

ROOT = Path(__file__).parents[1]

def load_yaml(path):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))

def test_public_surface_and_runtime_variants():
    ext = load_yaml("extensions/powerpack/extension.yml")
    assert [c["name"] for c in ext["provides"]["commands"]] == ["speckit.powerpack.deliver"]
    body = (ROOT / "extensions/powerpack/commands/deliver.md").read_text(encoding="utf-8")
    for token in ("sh:", "ps:", "py:", "{SCRIPT}"):
        assert token in body
    assert (ROOT / "extensions/powerpack/scripts/bash/deliver.sh").is_file()
    assert (ROOT / "extensions/powerpack/scripts/powershell/deliver.ps1").is_file()
    assert (ROOT / "extensions/powerpack/scripts/python/deliver.py").is_file()

def test_workflow_orders_checklist_analyze_implement_converge_review():
    text = (ROOT / "workflows/powerpack-delivery/workflow.yml").read_text(encoding="utf-8")
    positions = [
        text.index("id: checklist-convergence"),
        text.index("id: analyze"),
        text.index("id: implement-pending"),
        text.index("id: convergence"),
        text.index("id: review-convergence"),
    ]
    assert positions == sorted(positions)
    assert "command: speckit.converge" in text
    assert "action: checklist" in text

def test_active_runtime_does_not_reference_archive():
    for root in (ROOT / "extensions", ROOT / "workflows", ROOT / "steps"):
        for path in root.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="ignore")
                assert "backup/" not in text
                assert "backup\\\\" not in text
