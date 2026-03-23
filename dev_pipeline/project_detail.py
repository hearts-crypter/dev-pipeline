from .logs_api import get_notifications, get_runs, get_status_audit
from .registry import get_project


def build_project_timeline(project_id: str, limit: int = 100) -> dict:
    _, project = get_project(project_id)

    runs = [r for r in get_runs(limit=limit) if any(a.get('project_id') == project_id for a in r.get('actions', []))]
    status_events = [e for e in get_status_audit(limit=limit) if e.get('project_id') == project_id]
    notifications = [n for n in get_notifications(limit=limit) if n.get('project_id') == project_id]

    return {
        'project': project.model_dump(mode='json'),
        'timeline': {
            'runs': runs,
            'status_events': status_events,
            'notifications': notifications,
        },
    }
