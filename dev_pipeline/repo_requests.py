import json
from datetime import datetime, timezone

from .paths import LOG_DIR, REPO_REQUEST_LOG_PATH
from .registry import get_project


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def submit_repo_request(project_id: str, source: str = 'webui') -> dict:
    _, project = get_project(project_id)
    rec = {
        'requested_at': _now_iso(),
        'project_id': project.id,
        'project_name': project.name,
        'repo_path': project.repo_path,
        'repo_url': project.repo_url,
        'source': source,
        'status': 'requested',
    }
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with REPO_REQUEST_LOG_PATH.open('a', encoding='utf-8') as f:
        f.write(json.dumps(rec) + '\n')
    return rec
