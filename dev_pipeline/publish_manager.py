import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .paths import LOG_DIR, PUBLISH_REQUEST_LOG_PATH
from .registry import get_project, load_registry, save_registry
from .repo_manager import ensure_repo_initialized


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


def _append_publish_log(rec: dict):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with PUBLISH_REQUEST_LOG_PATH.open('a', encoding='utf-8') as f:
        f.write(json.dumps(rec) + '\n')


def _git_output(repo_path: Path, args: list[str]) -> tuple[bool, str]:
    try:
        out = subprocess.check_output(['git', '-C', str(repo_path), *args], stderr=subprocess.STDOUT, text=True, timeout=30)
        return True, out.strip()
    except subprocess.CalledProcessError as e:
        return False, (e.output or str(e)).strip()
    except Exception as e:
        return False, str(e)


def _normalize_github_url(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    m = re.match(r'^git@github\.com:(.+?)(?:\.git)?$', url)
    if m:
        return f"https://github.com/{m.group(1)}"
    m2 = re.match(r'^https?://github\.com/(.+?)(?:\.git)?$', url)
    if m2:
        return f"https://github.com/{m2.group(1)}"
    return None


def detect_repo_url(repo_path: Path) -> str | None:
    ok, out = _git_output(repo_path, ['remote', 'get-url', 'origin'])
    if not ok:
        return None
    return _normalize_github_url(out)


def sync_all_repo_urls() -> int:
    reg = load_registry()
    changed = 0
    for p in reg.projects:
        path = Path(p.repo_path)
        if not path.exists():
            continue
        detected = detect_repo_url(path)
        if detected and p.repo_url != detected:
            p.repo_url = detected
            changed += 1
    if changed:
        save_registry(reg)
    return changed


def _gh(args: list[str], cwd: Path | None = None) -> tuple[bool, str]:
    try:
        out = subprocess.check_output(['gh', *args], cwd=str(cwd) if cwd else None, stderr=subprocess.STDOUT, text=True, timeout=60)
        return True, out.strip()
    except FileNotFoundError:
        return False, 'gh CLI not installed'
    except subprocess.CalledProcessError as e:
        return False, (e.output or str(e)).strip()
    except Exception as e:
        return False, str(e)


def publish_project_now(project_id: str, source: str = 'webui', visibility: str = 'private') -> dict:
    reg, p = get_project(project_id)
    repo_path = Path(p.repo_path)

    ok, msg = ensure_repo_initialized(repo_path)
    if not ok:
        rec = {
            'requested_at': _now_iso(), 'processed_at': _now_iso(), 'project_id': p.id, 'project_name': p.name,
            'source': source, 'status': 'failed', 'error': msg,
        }
        _append_publish_log(rec)
        return rec

    existing = detect_repo_url(repo_path) or p.repo_url
    if existing:
        p.repo_url = existing
        save_registry(reg)
        rec = {
            'requested_at': _now_iso(), 'processed_at': _now_iso(), 'project_id': p.id, 'project_name': p.name,
            'source': source, 'status': 'fulfilled', 'result': f'already published: {existing}', 'repo_url': existing,
        }
        _append_publish_log(rec)
        return rec

    vis_flag = '--private' if visibility != 'public' else '--public'
    ok_create, out_create = _gh(['repo', 'create', p.id, vis_flag, '--source', str(repo_path), '--push'])
    if not ok_create:
        rec = {
            'requested_at': _now_iso(), 'processed_at': _now_iso(), 'project_id': p.id, 'project_name': p.name,
            'source': source, 'status': 'failed', 'error': out_create,
        }
        _append_publish_log(rec)
        return rec

    detected = detect_repo_url(repo_path)
    if detected:
        p.repo_url = detected
        save_registry(reg)

    rec = {
        'requested_at': _now_iso(), 'processed_at': _now_iso(), 'project_id': p.id, 'project_name': p.name,
        'source': source, 'status': 'fulfilled', 'result': out_create, 'repo_url': p.repo_url,
    }
    _append_publish_log(rec)
    return rec


def process_publish_requests(limit: int = 20) -> dict:
    # Backward-compat entry point; now publish is intended to be immediate.
    return {'processed': 0, 'updated': [], 'note': 'publish is now instant via /projects/{id}/publish-request'}
