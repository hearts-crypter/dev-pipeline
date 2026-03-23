import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .email_utils import send_email
from .paths import LOG_DIR
from .registry import load_registry

NOTIFY_STATE_PATH = LOG_DIR / 'milestone_notify_state.json'
NOTIFY_LOG_PATH = LOG_DIR / 'notifications.jsonl'


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_state() -> dict:
    if not NOTIFY_STATE_PATH.exists():
        return {}
    try:
        return json.loads(NOTIFY_STATE_PATH.read_text())
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    NOTIFY_STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + '\n')


def _append_notify_log(rec: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with NOTIFY_LOG_PATH.open('a', encoding='utf-8') as f:
        f.write(json.dumps(rec) + '\n')


def _parse_completed_phases(roadmap_path: Path) -> list[str]:
    if not roadmap_path.exists():
        return []

    lines = roadmap_path.read_text(encoding='utf-8', errors='ignore').splitlines()
    phases: list[tuple[str, list[str]]] = []
    current_title = None
    current_checks: list[str] = []

    for line in lines:
        m = re.match(r'^##\s+(.+)$', line.strip())
        if m:
            if current_title is not None:
                phases.append((current_title, current_checks))
            current_title = m.group(1).strip()
            current_checks = []
            continue
        if re.match(r'^- \[[ xX]\]\s+', line.strip()):
            current_checks.append(line.strip())

    if current_title is not None:
        phases.append((current_title, current_checks))

    completed = []
    for title, checks in phases:
        if checks and all(c.startswith('- [x]') or c.startswith('- [X]') for c in checks):
            completed.append(title)
    return completed


def detect_and_notify() -> dict:
    reg = load_registry()
    state = _load_state()

    sent = []
    scanned = 0

    for project in reg.projects:
        if project.status not in {'active', 'finished'}:
            continue
        scanned += 1
        roadmap = Path(project.roadmap_doc) if project.roadmap_doc else None
        if not roadmap:
            continue

        completed = _parse_completed_phases(roadmap)
        known = set(state.get(project.id, []))
        new = [m for m in completed if m not in known]
        if not new:
            continue

        subject = f"[Milestone] {project.name}: {new[-1]}"
        body = (
            f"Project: {project.name}\n"
            f"Project ID: {project.id}\n"
            f"Status: {project.status}\n"
            f"Newly completed milestones:\n"
            + ''.join(f"- {m}\n" for m in new)
            + f"\nRoadmap: {project.roadmap_doc or 'N/A'}\n"
            + f"Spec: {project.spec_doc or 'N/A'}\n"
            + (f"Web UI: {project.webui_url}\n" if project.webui_url else '')
            + f"Detected at: {_now_iso()}\n"
        )

        try:
            send_email(project.owner_notify_email, subject, body)
            rec = {
                'sent_at': _now_iso(),
                'project_id': project.id,
                'recipient': project.owner_notify_email,
                'milestones': new,
                'status': 'sent',
            }
            sent.append(rec)
            _append_notify_log(rec)
            state[project.id] = sorted(set(known.union(new)))
        except Exception as e:
            rec = {
                'sent_at': _now_iso(),
                'project_id': project.id,
                'recipient': project.owner_notify_email,
                'milestones': new,
                'status': 'failed',
                'error': str(e),
            }
            _append_notify_log(rec)

    _save_state(state)
    return {'scanned_projects': scanned, 'sent': sent}
