import json
from datetime import datetime, timezone

from .paths import PUBLISH_REQUEST_LOG_PATH
from .registry import get_project


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read(path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def _write(path, items):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for rec in items:
            f.write(json.dumps(rec) + '\n')


def process_publish_requests(limit: int = 20) -> dict:
    reqs = _read(PUBLISH_REQUEST_LOG_PATH)
    idxs = [i for i, r in enumerate(reqs) if r.get('status') == 'requested'][:limit]
    updated = []

    for i in idxs:
        rec = reqs[i]
        try:
            _, p = get_project(rec.get('project_id'))
            rec['processed_at'] = _now_iso()
            if p.repo_url:
                rec['status'] = 'fulfilled'
                rec['result'] = f'already published: {p.repo_url}'
            else:
                rec['status'] = 'awaiting-publish-action'
                rec['result'] = 'publish requested; GitHub remote creation pending explicit publish workflow/credentials'
        except KeyError:
            rec['processed_at'] = _now_iso()
            rec['status'] = 'failed'
            rec['error'] = 'project not found in registry'
        updated.append(rec)

    _write(PUBLISH_REQUEST_LOG_PATH, reqs)
    return {'processed': len(updated), 'updated': updated}
