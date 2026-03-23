import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .paths import LOG_DIR, RUN_LOG_PATH
from .registry import load_registry, save_registry


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_sweep() -> dict:
    reg = load_registry()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    run = {
        "run_at": _utc_now_iso(),
        "total_projects": len(reg.projects),
        "active_projects": 0,
        "actions": [],
    }

    for project in reg.projects:
        if project.status != "active":
            continue
        run["active_projects"] += 1

        repo = Path(project.repo_path)
        if not repo.exists():
            run["actions"].append(
                {
                    "project_id": project.id,
                    "result": "blocked",
                    "reason": f"repo_path missing: {project.repo_path}",
                }
            )
            continue

        git_status = _safe_git_status(repo)
        action = {
            "project_id": project.id,
            "result": "inspected",
            "git_status": git_status,
            "next_milestone": project.next_milestone,
        }
        run["actions"].append(action)
        project.last_progress_at = _utc_now_iso()

    save_registry(reg)
    with RUN_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(run) + "\n")
    return run


def _safe_git_status(repo: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo), "status", "--short"],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
        )
        return out.strip() or "clean"
    except Exception as e:
        return f"git_status_error: {e}"
