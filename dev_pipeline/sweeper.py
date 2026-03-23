import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .autodev import run_autodev_tick
from .locks import acquire_lock, lock_status, release_lock
from .paths import LOG_DIR, RUN_LOG_PATH
from .registry import load_registry, save_registry
from .repo_manager import ensure_repo_initialized


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

        ls = lock_status(project)
        if ls['locked'] and ls['lock_mode'] == 'manual':
            run['actions'].append({
                'project_id': project.id,
                'result': 'skipped',
                'reason': 'manual_lock_active',
                'lock': ls,
            })
            continue

        lock = acquire_lock(project.id, mode='auto', owner='sweeper', ttl_minutes=25)
        if not lock.get('ok'):
            run['actions'].append({
                'project_id': project.id,
                'result': 'skipped',
                'reason': 'could_not_acquire_lock',
                'lock': lock,
            })
            continue

        repo = Path(project.repo_path)
        if not repo.exists():
            run["actions"].append(
                {
                    "project_id": project.id,
                    "result": "blocked",
                    "reason": f"repo_path missing: {project.repo_path}",
                }
            )
            release_lock(project.id, owner='sweeper', force=True)
            continue

        local_ok, local_msg = ensure_repo_initialized(repo)
        git_status = _safe_git_status(repo)
        autodev = run_autodev_tick(project.id, project.repo_path)

        action = {
            "project_id": project.id,
            "result": "inspected",
            "local_repo": {"ok": local_ok, "message": local_msg},
            "git_status": git_status,
            "autodev": {"changed": autodev.changed, "summary": autodev.summary},
            "next_milestone": project.next_milestone,
            "lock": lock,
        }
        run["actions"].append(action)
        project.last_progress_at = _utc_now_iso()
        release_lock(project.id, owner='sweeper', force=True)

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
