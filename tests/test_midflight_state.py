import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).parents[1]
STATE = ROOT / "steps/powerpack-control/state.py"
spec = importlib.util.spec_from_file_location("powerpack_state", STATE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)

def test_manual_through_analyze_adopts_at_post_tasks(tmp_path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    feature = tmp_path / "specs/soak/003-soak-qualification"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# spec\nFR-001 ok\n")
    (feature / "plan.md").write_text("# plan\n")
    (feature / "tasks.md").write_text("- [ ] T001 Implement\n- [ ] T002 Verify\n")
    checks = feature / "checklists"
    checks.mkdir()
    (checks / "requirements.md").write_text("- [x] clear\n")
    (checks / "qualification.md").write_text("- [ ] one\n- [ ] two\n")
    marker = tmp_path / ".specify"
    marker.mkdir()
    (marker / "feature.json").write_text(json.dumps({"feature_directory": "specs/soak/003-soak-qualification"}))
    (tmp_path / "seed.txt").write_text("x")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "seed")

    state = module.inspect_delivery(tmp_path, "spec-soak-003")
    assert state["state"] == "IMPLEMENTATION_PENDING"
    assert state["feature_dir"].endswith("specs/soak/003-soak-qualification")
    assert state["pending_tasks"] == 2
    status = module.checklist_status(feature)
    assert status["total"] == 3
    assert status["checked"] == 1
    assert status["unchecked"] == 2

def test_all_tasks_checked_requires_converge_recheck(tmp_path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    feature = tmp_path / "specs/001-feature"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# spec\n")
    (feature / "plan.md").write_text("# plan\n")
    (feature / "tasks.md").write_text("- [x] T001 Done\n")
    marker = tmp_path / ".specify"
    marker.mkdir()
    (marker / "feature.json").write_text(json.dumps({"feature_directory": "specs/001-feature"}))
    (tmp_path / "seed.txt").write_text("x")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "seed")

    state = module.inspect_delivery(tmp_path)
    assert state["state"] == "IMPLEMENTED_PENDING_CONVERGENCE"
