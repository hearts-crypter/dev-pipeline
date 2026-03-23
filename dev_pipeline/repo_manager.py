import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .paths import REPO_REQUEST_LOG_PATH
from .registry import load_registry, save_registry


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_requests() -> list[dict]:
    if not REPO_REQUEST_LOG_PATH.exists():
        return []
    out = []
    for line in REPO_REQUEST_LOG_PATH.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def _write_requests(items: list[dict]) -> None:
    REPO_REQUEST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPO_REQUEST_LOG_PATH.open('w', encoding='utf-8') as f:
        for rec in items:
            f.write(json.dumps(rec) + '\n')


def _git(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    try:
        out = subprocess.check_output(['git', *cmd], cwd=str(cwd), stderr=subprocess.STDOUT, text=True, timeout=20)
        return True, out.strip()
    except subprocess.CalledProcessError as e:
        return False, (e.output or str(e)).strip()
    except Exception as e:
        return False, str(e)


def ensure_repo_initialized(repo_path: Path) -> tuple[bool, str]:
    if not repo_path.exists():
        return False, f'repo path does not exist: {repo_path}'

    git_dir = repo_path / '.git'
    if not git_dir.exists():
        ok, out = _git(['init'], repo_path)
        if not ok:
            return False, f'git init failed: {out}'

    ok, out = _git(['rev-parse', '--abbrev-ref', 'HEAD'], repo_path)
    if not ok or out in ('HEAD', ''):
        ok2, out2 = _git(['checkout', '-b', 'main'], repo_path)
        if not ok2 and 'already exists' not in out2:
            return False, f'branch setup failed: {out2}'

    return True, 'local git repo ready'


def process_repo_requests(limit: int = 20) -> dict:
    reqs = _read_requests()
    pending_idx = [i for i, r in enumerate(reqs) if r.get('status') == 'requested'][:limit]
    if not pending_idx:
        return {'processed': 0, 'updated': []}

    reg = load_registry()
    by_id = {p.id: p for p in reg.projects}
    updates = []

    for idx in pending_idx:
        rec = reqs[idx]
        pid = rec.get('project_id')
        proj = by_id.get(pid)
        if not proj:
            rec['status'] = 'failed'
            rec['processed_at'] = _now_iso()
            rec['error'] = 'project not found in registry'
            updates.append(rec)
            continue

        ok, msg = ensure_repo_initialized(Path(proj.repo_path))
        rec['processed_at'] = _now_iso()
        if not ok:
            rec['status'] = 'failed'
            rec['error'] = msg
            updates.append(rec)
            continue

        if proj.repo_url:
            rec['status'] = 'fulfilled'
            rec['result'] = f'repo already configured: {proj.repo_url}'
            updates.append(rec)
            continue

        rec['status'] = 'local-ready'
        rec['result'] = 'local repo initialized; remote repo_url still needed'
        updates.append(rec)

    save_registry(reg)
    _write_requests(reqs)
    return {'processed': len(updates), 'updated': updates}
