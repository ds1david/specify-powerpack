from __future__ import annotations

from pathlib import Path
from typing import Any

from specify_cli.workflows.base import StepBase, StepContext, StepResult, StepStatus
from specify_cli.workflows.expressions import evaluate_expression

from .review import run_review
from .state import checklist_status, fingerprint_tasks, inspect_delivery, resolve_feature_dir, task_execution_plan

class PowerPackControlStep(StepBase):
    type_key = "powerpack-control"

    @staticmethod
    def _value(config: dict[str, Any], key: str, context: StepContext, default: Any = "") -> Any:
        value = config.get(key, default)
        if isinstance(value, str) and "{{" in value:
            return evaluate_expression(value, context)
        return value

    def execute(self, config: dict[str, Any], context: StepContext) -> StepResult:
        action = str(self._value(config, "action", context, "")).strip()
        project = Path(context.project_root or ".").resolve()
        try:
            if action == "inspect":
                target = str(self._value(config, "target", context, "") or "").strip()
                return StepResult(output=inspect_delivery(project, target))
            if action == "checklist":
                target = str(self._value(config, "target", context, "") or "").strip()
                feature = resolve_feature_dir(project, target, require=True)
                result = checklist_status(feature)
                result["spec_id"] = feature.name
                return StepResult(output=result)
            if action == "fingerprint":
                target = str(self._value(config, "target", context, "") or "").strip()
                feature = resolve_feature_dir(project, target, require=True)
                return StepResult(output={"spec_id": feature.name, "sha256": fingerprint_tasks(feature)})
            if action == "task-plan":
                target = str(self._value(config, "target", context, "") or "").strip()
                feature = resolve_feature_dir(project, target, require=True)
                return StepResult(output=task_execution_plan(feature))
            if action == "review":
                target = str(self._value(config, "target", context, "") or "").strip()
                model = str(self._value(config, "model", context, "") or "").strip()
                effort = str(self._value(config, "effort", context, "high") or "high").strip()
                return StepResult(output=run_review(project, target=target, model=model, effort=effort))
            if action == "fail":
                message = str(self._value(config, "message", context, "PowerPack delivery failed"))
                return StepResult(status=StepStatus.FAILED, error=message)
        except Exception as exc:
            return StepResult(status=StepStatus.FAILED, error=f"PowerPack {action or 'control'} failed: {exc}")
        return StepResult(status=StepStatus.FAILED, error=f"Unknown PowerPack action: {action!r}")

    def validate(self, config: dict[str, Any]) -> list[str]:
        errors = super().validate(config)
        allowed = {"inspect", "checklist", "fingerprint", "task-plan", "review", "fail"}
        if config.get("action") not in allowed:
            errors.append(f"PowerPack step {config.get('id', '?')!r}: invalid action.")
        return errors
