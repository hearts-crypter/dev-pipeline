from datetime import datetime, timedelta, timezone

from .registry import get_project, save_registry


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except Exception:
        return None


def _is_lock_active(project) -> bool:
    until = _parse_iso(getattr(project, 'lock_until', None))
    if not until:
        return False
    return until > _now()


def lock_status(project) -> dict:
    return {
        'locked': _is_lock_active(project),
        'lock_mode': getattr(project, 'lock_mode', None),
        'lock_owner': getattr(project, 'lock_owner', None),
        'lock_until': getattr(project, 'lock_until', None),
    }


def acquire_lock(project_id: str, mode: str, owner: str, ttl_minutes: int = 30, force: bool = False) -> dict:
    reg, p = get_project(project_id)
    active = _is_lock_active(p)
    if active and not force:
        return {'ok': False, 'reason': 'lock_active', **lock_status(p)}

    until = (_now() + timedelta(minutes=ttl_minutes)).replace(microsecond=0).isoformat()
    p.lock_mode = mode
    p.lock_owner = owner
    p.lock_until = until
    save_registry(reg)
    return {'ok': True, **lock_status(p)}


def release_lock(project_id: str, owner: str | None = None, force: bool = False) -> dict:
    reg, p = get_project(project_id)
    if not force and owner and getattr(p, 'lock_owner', None) not in (None, owner):
        return {'ok': False, 'reason': 'owner_mismatch', **lock_status(p)}

    p.lock_mode = None
    p.lock_owner = None
    p.lock_until = None
    save_registry(reg)
    return {'ok': True, **lock_status(p)}
