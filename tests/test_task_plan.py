import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).parents[1]
STATE = ROOT / "steps/powerpack-control/state.py"
spec = importlib.util.spec_from_file_location("powerpack_state_task_plan", STATE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def feature(tmp_path, tasks):
    root = tmp_path / "specs/001-demo"
    root.mkdir(parents=True)
    (root / "plan.md").write_text("# plan\n", encoding="utf-8")
    (root / "tasks.md").write_text(tasks, encoding="utf-8")
    return root


def test_task_plan_reports_current_phase_and_parallel_opportunities(tmp_path):
    root = feature(
        tmp_path,
        """## Phase 1: Setup
- [x] T001 Setup project
## Phase 2: Foundational
- [ ] T002 [P] Create A in src/a.py
- [ ] T003 [P] Create B in src/b.py
- [ ] T004 Wire dependencies in src/main.py
## Phase 3: Story
- [ ] T005 [US1] Implement story in src/story.py
""",
    )
    plan = module.task_execution_plan(root)
    assert plan["current_phase_number"] == 2
    assert plan["current_phase_name"] == "Foundational"
    assert plan["pending_tasks"] == 4
    assert plan["current_phase_parallel"] == 2
    assert plan["pending_parallel_tasks"] == 2


def test_task_plan_rejects_started_later_phase_while_earlier_pending(tmp_path):
    root = feature(
        tmp_path,
        """## Phase 1: Setup
- [ ] T001 Setup project
## Phase 2: Foundational
- [x] T002 Completed too early
""",
    )
    with pytest.raises(RuntimeError, match="later phase"):
        module.task_execution_plan(root)


def test_task_plan_rejects_duplicate_ids(tmp_path):
    root = feature(
        tmp_path,
        """## Phase 1: Setup
- [ ] T001 A
- [ ] T001 B
""",
    )
    with pytest.raises(RuntimeError, match="duplicate task IDs"):
        module.task_execution_plan(root)
