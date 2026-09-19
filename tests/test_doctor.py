import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
DOCTOR = ROOT / "extensions/powerpack/scripts/common/doctor.py"
spec = importlib.util.spec_from_file_location("powerpack_doctor", DOCTOR)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_doctor_is_read_only_and_reports_missing_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    report = module.Doctor(None, "py", True, "").run()
    assert report["healthy"] is False
    assert any(c["name"] == "specify-project" and c["status"] == "FAIL" for c in report["checks"])
    assert list(tmp_path.iterdir()) == []


def test_doctor_feature_pointer_warns_for_midflight_missing_plan_tasks(tmp_path):
    project = tmp_path
    (project / ".specify").mkdir()
    feature = project / "specs/001-demo"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# demo\n", encoding="utf-8")
    write_json(project / ".specify/feature.json", {"feature_directory": "specs/001-demo"})
    doctor = module.Doctor(project, "", True, "")
    doctor._feature()
    statuses = {c["name"]: c["status"] for c in doctor.checks}
    assert statuses["active-feature"] == "PASS"
    assert statuses["feature:spec.md"] == "PASS"
    assert statuses["feature:plan.md"] == "WARN"
    assert statuses["feature:tasks.md"] == "WARN"
