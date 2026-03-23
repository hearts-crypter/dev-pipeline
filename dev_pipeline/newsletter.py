from datetime import datetime, timezone
from pathlib import Path

from .registry import load_registry


def render_project_section() -> str:
    reg = load_registry()
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    active = [p for p in reg.projects if p.status == 'active']
    blocked = [p for p in reg.projects if p.status == 'blocked']

    lines = []
    lines.append('Project Pipeline Snapshot')
    lines.append(f'- Generated at: {now}')
    lines.append(f'- Active projects: {len(active)}')
    lines.append(f'- Blocked projects: {len(blocked)}')
    lines.append('')

    if active:
        lines.append('Active project details:')
        for p in active:
            lines.append(f"- {p.name} ({p.id}) — next milestone: {p.next_milestone or 'unspecified'}")

    if blocked:
        lines.append('')
        lines.append('Blocked projects:')
        for p in blocked:
            lines.append(f"- {p.name} ({p.id}) — {p.notes or 'no blocker note'}")

    return '\n'.join(lines)


def write_project_section(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_project_section() + '\n', encoding='utf-8')
    return path
