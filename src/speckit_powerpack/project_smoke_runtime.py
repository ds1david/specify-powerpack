from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sys
import time
from typing import Any, Iterator


EXPECTED_PROVIDER = "chatgpt-project"
EXPECTED_MODE = "backend-api"
EXPECTED_AUTHORIZATION = "codex-backend-api"


class StepTimer:
    def __init__(self) -> None:
        self.started_at = time.perf_counter()
        self.steps: list[dict[str, Any]] = []

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        started = time.perf_counter()
        print(f"[timing] start {name}", file=sys.stderr, flush=True)
        status = "ok"
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            elapsed = time.perf_counter() - started
            entry = {
                "name": name,
                "elapsed_seconds": round(elapsed, 3),
                "status": status,
            }
            self.steps.append(entry)
            print(
                f"[timing] done  {name}: {elapsed:.3f}s status={status}",
                file=sys.stderr,
                flush=True,
            )

    def report(self) -> dict[str, Any]:
        total = time.perf_counter() - self.started_at
        measured = sum(float(step["elapsed_seconds"]) for step in self.steps)
        return {
            "total_seconds": round(total, 3),
            "measured_steps_seconds": round(measured, 3),
            "steps": list(self.steps),
        }


def load_project_binding(project_path: Path) -> dict[str, str]:
    review_path = project_path / ".specify" / "powerpack" / "review.json"
    if not review_path.is_file():
        raise RuntimeError(
            f"PowerPack review binding is missing: {review_path}. "
            "Run 'speckit-powerpack review setup --path <repo>' first."
        )
    try:
        payload = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read review binding {review_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("PowerPack review config must contain an object.")

    provider = str(payload.get("provider") or "").strip()
    web = payload.get("chatgpt_web") if isinstance(payload.get("chatgpt_web"), dict) else {}
    mode = str(web.get("mode") or "").strip()
    authorization = str(web.get("authorization") or "").strip()
    project_id = str(web.get("project_id") or "").strip()
    project_name = str(web.get("project_name") or "").strip()
    project_url = str(web.get("project_url") or "").strip()

    if provider != EXPECTED_PROVIDER:
        raise RuntimeError(
            f"Repository is not bound to ChatGPTProjectProvider: provider={provider or '<missing>'}. "
            "Run 'speckit-powerpack review setup --path <repo>' and choose a ChatGPT Project."
        )
    if mode != EXPECTED_MODE:
        raise RuntimeError(
            f"Repository binding is not browserless backend-api mode: mode={mode or '<missing>'}."
        )
    if authorization != EXPECTED_AUTHORIZATION:
        raise RuntimeError(
            "Repository binding is not authorized through codex-backend-api: "
            f"authorization={authorization or '<missing>'}."
        )
    if not project_id.startswith("g-p-"):
        raise RuntimeError("Repository binding does not contain a valid ChatGPT Project id (g-p-...).")
    if not project_name:
        raise RuntimeError("Repository binding does not contain a ChatGPT Project name.")

    return {
        "provider": provider,
        "mode": mode,
        "authorization": authorization,
        "project_id": project_id,
        "project_name": project_name,
        "project_url": project_url,
    }
