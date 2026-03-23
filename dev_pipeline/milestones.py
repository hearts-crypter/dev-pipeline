import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .email_utils import send_email
from .paths import LOG_DIR
from .registry import load_registry, save_registry

NOTIFY_STATE_PATH = LOG_DIR / 'milestone_notify_state.json'
NOTIFY_LOG_PATH = LOG_DIR / 'notifications.jsonl'

# State schema:
# {
#   "<project_id>": {
#     "notified": ["Phase 1", "Phase 2"],
#     "last_sent_at": "..."
#   }
# }


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


def _parse_roadmap_phases(roadmap_path: Path) -> list[dict]:
    if not roadmap_path.exists():
        return []

    lines = roadmap_path.read_text(encoding='utf-8', errors='ignore').splitlines()
    phases: list[dict] = []
    current_title = None
    current_checks: list[dict] = []

    def flush_current() -> None:
        if current_title is not None:
            phases.append({'title': current_title, 'checks': current_checks[:]})

    for line in lines:
        section = re.match(r'^##\s+(.+)$', line.strip())
        if section:
            flush_current()
            current_title = section.group(1).strip()
            current_checks = []
            continue

        item = re.match(r'^- \[([ xX])\]\s+(.+)$', line.strip())
        if item:
            current_checks.append({'checked': item.group(1).lower() == 'x', 'text': item.group(2).strip()})

    flush_current()
    return phases


def _completed_phase_titles(phases: list[dict]) -> list[str]:
    completed = []
    for phase in phases:
        checks = phase.get('checks', [])
        if checks and all(c.get('checked') for c in checks):
            completed.append(phase['title'])
    return completed


def _derive_next_milestone(phases: list[dict]) -> str | None:
    # First unfinished checklist item in order wins.
    for phase in phases:
        checks = phase.get('checks', [])
        if not checks:
            continue
        for item in checks:
            if not item.get('checked'):
                return f"{phase['title']} — {item.get('text')}"

    # If there are phases but no unfinished checklist entries, roadmap is complete.
    if phases:
        return 'All listed roadmap checklist milestones complete'
    return None


def sync_project_milestones() -> dict:
    reg = load_registry()
    changed = []

    for project in reg.projects:
        roadmap = Path(project.roadmap_doc) if project.roadmap_doc else None
        if not roadmap or not roadmap.exists():
            continue

        phases = _parse_roadmap_phases(roadmap)
        next_milestone = _derive_next_milestone(phases)

        if project.next_milestone != next_milestone:
            project.next_milestone = next_milestone
            project.last_progress_at = _now_iso()
            changed.append({'project_id': project.id, 'next_milestone': next_milestone})

    if changed:
        save_registry(reg)

    return {'updated': len(changed), 'projects': changed}


def detect_and_notify() -> dict:
    sync_info = sync_project_milestones()

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

        phases = _parse_roadmap_phases(roadmap)
        completed = _completed_phase_titles(phases)
        raw_proj_state = state.get(project.id, {})
        if isinstance(raw_proj_state, list):
            # backward compatibility with earlier state format
            proj_state = {'notified': raw_proj_state}
        elif isinstance(raw_proj_state, dict):
            proj_state = raw_proj_state
        else:
            proj_state = {'notified': []}

        known = set(proj_state.get('notified', []))
        new = [m for m in completed if m not in known]
        if not new:
            continue

        subject = f"[Milestone] {project.name}: {new[-1]}"
        body = (
            f"Project: {project.name}\n"
            f"Project ID: {project.id}\n"
            f"Status: {project.status}\n"
            f"Next milestone: {project.next_milestone or 'unspecified'}\n"
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
                'next_milestone': project.next_milestone,
                'status': 'sent',
            }
            sent.append(rec)
            _append_notify_log(rec)
            state[project.id] = {
                'notified': sorted(set(known.union(new))),
                'last_sent_at': _now_iso(),
            }
        except Exception as e:
            rec = {
                'sent_at': _now_iso(),
                'project_id': project.id,
                'recipient': project.owner_notify_email,
                'milestones': new,
                'next_milestone': project.next_milestone,
                'status': 'failed',
                'error': str(e),
            }
            _append_notify_log(rec)

    _save_state(state)
    return {'scanned_projects': scanned, 'synced_milestones': sync_info, 'sent': sent}
