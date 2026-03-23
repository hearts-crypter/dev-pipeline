import json
from pathlib import Path

from .paths import AUDIT_LOG_PATH, NOTIFY_LOG_PATH, REPO_REQUEST_LOG_PATH, RUN_LOG_PATH


def _read_jsonl(path: Path, limit: int = 100) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    out = []
    for raw in lines[-limit:]:
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except Exception:
            continue
    return out


def get_runs(limit: int = 100) -> list[dict]:
    return _read_jsonl(RUN_LOG_PATH, limit=limit)


def get_status_audit(limit: int = 100) -> list[dict]:
    return _read_jsonl(AUDIT_LOG_PATH, limit=limit)


def get_notifications(limit: int = 100) -> list[dict]:
    return _read_jsonl(NOTIFY_LOG_PATH, limit=limit)


def get_repo_requests(limit: int = 100) -> list[dict]:
    return _read_jsonl(REPO_REQUEST_LOG_PATH, limit=limit)
