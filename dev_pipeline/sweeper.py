import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .autodev import run_autodev_tick
from .email_utils import send_email
from .locks import acquire_lock, lock_status, release_lock
from .milestones import sync_project_milestones
from .paths import LOG_DIR, RUN_LOG_PATH
from .registry import load_registry, save_registry
from .repo_manager import ensure_repo_initialized

AUTOPAUSE_STATE_PATH = LOG_DIR / "autopause_state.json"
NO_PROGRESS_RUN_THRESHOLD = 24  # ~12 hours at 30-min sweep cadence


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_autopause_state() -> dict:
    if not AUTOPAUSE_STATE_PATH.exists():
        return {}
    try:
        return json.loads(AUTOPAUSE_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_autopause_state(state: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    AUTOPAUSE_STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _should_count_no_progress(summary: str) -> bool:
    s = (summary or "").lower()
    markers = [
        "no project-specific autodev handler",
        "no handler",
        "autodev skipped",
        "no actionable tasks",
    ]
    return any(m in s for m in markers)


def run_sweep() -> dict:
    reg = load_registry()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    autopause_state = _load_autopause_state()

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
        if ls["locked"] and ls["lock_mode"] == "manual":
            run["actions"].append(
                {
                    "project_id": project.id,
                    "result": "skipped",
                    "reason": "manual_lock_active",
                    "lock": ls,
                }
            )
            continue

        lock = acquire_lock(project.id, mode="auto", owner="sweeper", ttl_minutes=25)
        if not lock.get("ok"):
            run["actions"].append(
                {
                    "project_id": project.id,
                    "result": "skipped",
                    "reason": "could_not_acquire_lock",
                    "lock": lock,
                }
            )
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
            release_lock(project.id, owner="sweeper", force=True)
            continue

        local_ok, local_msg = ensure_repo_initialized(repo)
        git_status = _safe_git_status(repo)
        autodev = run_autodev_tick(project.id, project.repo_path, max_tasks=3)

        # Track no-progress streak for auto-pause decisions.
        pstate = autopause_state.get(project.id, {})
        no_progress_runs = int(pstate.get("no_progress_runs", 0))
        if autodev.changed:
            no_progress_runs = 0
            project.last_progress_at = _utc_now_iso()
        elif _should_count_no_progress(autodev.summary):
            no_progress_runs += 1

        pstate.update(
            {
                "no_progress_runs": no_progress_runs,
                "last_seen_at": _utc_now_iso(),
                "last_summary": autodev.summary,
            }
        )
        autopause_state[project.id] = pstate

        action = {
            "project_id": project.id,
            "result": "inspected",
            "local_repo": {"ok": local_ok, "message": local_msg},
            "git_status": git_status,
            "autodev": {"changed": autodev.changed, "summary": autodev.summary, "completed_tasks": autodev.completed_tasks or []},
            "next_milestone": project.next_milestone,
            "lock": lock,
            "no_progress_runs": no_progress_runs,
        }

        if no_progress_runs >= NO_PROGRESS_RUN_THRESHOLD:
            old_status = project.status
            project.status = "paused"
            project.last_progress_at = project.last_progress_at or _utc_now_iso()
            action["result"] = "paused"
            action["reason"] = "auto_paused_no_progress"
            action["paused_after_runs"] = no_progress_runs
            action["old_status"] = old_status
            pstate["no_progress_runs"] = 0
            pstate["last_auto_paused_at"] = _utc_now_iso()

            email_subject = f"[Auto-paused] {project.name} stalled without progress"
            email_body = (
                f"Project: {project.name}\n"
                f"Project ID: {project.id}\n"
                f"Status changed: {old_status} -> paused\n"
                f"Reason: no meaningful autodev progress for {NO_PROGRESS_RUN_THRESHOLD} consecutive sweeps\n"
                f"Current milestone: {project.next_milestone or 'unspecified'}\n"
                f"Last autodev summary: {autodev.summary}\n"
                f"Detected at: {_utc_now_iso()}\n"
                "\n"
                "Suggested next steps:\n"
                "- add/expand autodev handlers for the current milestone\n"
                "- unblock dependencies/config for this task\n"
                "- resume manually when ready\n"
            )
            try:
                send_email(project.owner_notify_email, email_subject, email_body)
                action["notification"] = "email_sent"
            except Exception as e:
                action["notification"] = f"email_failed: {e}"

        run["actions"].append(action)
        release_lock(project.id, owner="sweeper", force=True)

    save_registry(reg)
    _save_autopause_state(autopause_state)
    milestone_sync = sync_project_milestones()
    run["milestone_sync"] = milestone_sync

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
