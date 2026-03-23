import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .models import Registry, StatusChange
from .paths import AUDIT_LOG_PATH, LOG_DIR, REGISTRY_PATH


def load_registry(path: Path = REGISTRY_PATH) -> Registry:
    if not path.exists():
        return Registry(projects=[])
    data = yaml.safe_load(path.read_text()) or {}
    return Registry.model_validate(data)


def save_registry(registry: Registry, path: Path = REGISTRY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(registry.model_dump(mode="json"), sort_keys=False))


def get_project(project_id: str, path: Path = REGISTRY_PATH):
    reg = load_registry(path)
    for p in reg.projects:
        if p.id == project_id:
            return reg, p
    raise KeyError(f"Project not found: {project_id}")


def set_project_status(project_id: str, new_status: str, source: str = "api", note: str | None = None):
    allowed = {"active", "paused", "stopped", "finished", "blocked"}
    if new_status not in allowed:
        raise ValueError(f"Invalid status '{new_status}'. Allowed: {sorted(allowed)}")

    reg, project = get_project(project_id)
    old = project.status
    project.status = new_status
    save_registry(reg)
    _append_status_audit(
        project_id=project_id,
        change=StatusChange(
            old_status=old,
            new_status=new_status,
            changed_at=datetime.now(timezone.utc),
            source=source,
            note=note,
        ),
    )
    return project


def _append_status_audit(project_id: str, change: StatusChange) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "project_id": project_id,
        **change.model_dump(mode="json"),
    }
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
