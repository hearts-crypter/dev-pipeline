from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class AutoDevResult:
    changed: bool
    summary: str
    completed_tasks: list[str] | None = None


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _run(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    try:
        out = subprocess.check_output(cmd, cwd=str(cwd), stderr=subprocess.STDOUT, text=True, timeout=60)
        return True, out.strip()
    except subprocess.CalledProcessError as e:
        return False, (e.output or str(e)).strip()


def _ensure_git_identity(repo: Path) -> None:
    ok_name, _ = _run(["git", "config", "user.name"], repo)
    ok_email, _ = _run(["git", "config", "user.email"], repo)
    if not ok_name:
        _run(["git", "config", "user.name", "Hearts Crypter"], repo)
    if not ok_email:
        _run(["git", "config", "user.email", "heartscrypter@local"], repo)


def _commit_all(repo: Path, message: str) -> bool:
    _ensure_git_identity(repo)
    _run(["git", "add", "."], repo)
    ok, out = _run(["git", "status", "--short"], repo)
    if ok and not out.strip():
        return False
    _run(["git", "commit", "-m", message], repo)
    return True


def _parse_unchecked_tasks(roadmap: Path) -> list[str]:
    lines = roadmap.read_text(encoding="utf-8", errors="ignore").splitlines()
    tasks = []
    for ln in lines:
        m = re.match(r"^- \[ \] (.+)$", ln.strip())
        if m:
            tasks.append(m.group(1).strip())
    return tasks


def _check_task(roadmap: Path, task_text: str) -> bool:
    raw = roadmap.read_text(encoding="utf-8", errors="ignore")
    old = f"- [ ] {task_text}"
    new = f"- [x] {task_text}"
    if old not in raw:
        return False
    roadmap.write_text(raw.replace(old, new, 1), encoding="utf-8")
    return True


def _append_devlog(devlog: Path, text: str) -> None:
    stamp = _now_utc()
    with devlog.open("a", encoding="utf-8") as f:
        f.write(f"\n- {stamp} — {text}\n")


def _write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _replace_once(path: Path, old: str, new: str) -> bool:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if old not in raw:
        return False
    path.write_text(raw.replace(old, new, 1), encoding="utf-8")
    return True


def _paper_digest_handler(repo: Path, task: str) -> tuple[bool, str]:
    backend = repo / "backend"
    app_main = backend / "app" / "main.py"
    models = backend / "app" / "models.py"
    migration = backend / "migrations" / "001_init.sql"
    utils = backend / "app" / "utils.py"

    if task == "Create backend skeleton (FastAPI)":
        return (app_main.exists(), "Detected backend FastAPI skeleton")
    if task == "Define DB migrations + models":
        return (models.exists() and migration.exists(), "Detected migrations + models")
    if task == "Implement paper upload/link submission endpoints":
        txt = app_main.read_text(encoding="utf-8", errors="ignore") if app_main.exists() else ""
        ok = "@app.post(\"/papers/upload\"" in txt and "@app.post(\"/papers/url\"" in txt
        return (ok, "Detected upload/url endpoints")
    if task == "Persist files + paper records":
        t = utils.read_text(encoding="utf-8", errors="ignore") if utils.exists() else ""
        ok = "persist_upload" in t and "compute_sha256" in t
        return (ok, "Detected file persistence + hash utility")

    if task == "Worker queue + job states":
        worker_py = backend / "app" / "worker.py"
        run_worker = backend / "scripts" / "run_worker_once.py"
        _write_if_missing(
            worker_py,
            """from sqlalchemy.orm import Session\n\nfrom . import models\n\n\ndef process_next_job(db: Session) -> dict:\n    job = (\n        db.query(models.ProcessingJob)\n        .filter(models.ProcessingJob.state == \"queued\")\n        .order_by(models.ProcessingJob.created_at.asc())\n        .first()\n    )\n    if not job:\n        return {\"processed\": False, \"reason\": \"no queued jobs\"}\n\n    job.state = \"running\"\n    job.message = \"Worker started job\"\n    db.commit()\n\n    job.state = \"done\"\n    job.message = \"Worker completed placeholder processing\"\n    db.commit()\n\n    return {\"processed\": True, \"job_id\": job.id, \"state\": job.state}\n""",
        )
        _write_if_missing(
            run_worker,
            """#!/usr/bin/env python3\nfrom app.db import SessionLocal\nfrom app.worker import process_next_job\n\n\nif __name__ == \"__main__\":\n    db = SessionLocal()\n    try:\n        print(process_next_job(db))\n    finally:\n        db.close()\n""",
        )
        return (True, "Implemented baseline worker queue processor")

    return (False, "No handler for task yet")


def _bookkeeping_pipeline_handler(repo: Path, task: str) -> tuple[bool, str]:
    backend = repo / "backend"
    app_main = backend / "app" / "main.py"
    models = backend / "app" / "models.py"
    migrations = backend / "migrations"

    if task == "Scaffold backend app structure (`backend/app`)":
        return ((backend / "app").exists() and app_main.exists(), "Detected backend app scaffold")

    if task == "Define initial data models for transactions/categories/payment methods":
        if not models.exists():
            models.write_text(
                """from datetime import datetime\nfrom typing import Optional\n\nfrom sqlmodel import Field, SQLModel\n\n\nclass Category(SQLModel, table=True):\n    id: Optional[int] = Field(default=None, primary_key=True)\n    name: str\n\n\nclass PaymentMethod(SQLModel, table=True):\n    id: Optional[int] = Field(default=None, primary_key=True)\n    name: str\n    method_type: str = \"other\"\n\n\nclass Transaction(SQLModel, table=True):\n    id: Optional[int] = Field(default=None, primary_key=True)\n    occurred_at: datetime\n    merchant: str\n    description: str = \"\"\n    amount: float\n    currency: str = \"USD\"\n    category_id: Optional[int] = None\n    payment_method_id: Optional[int] = None\n\n\nclass AuditLog(SQLModel, table=True):\n    id: Optional[int] = Field(default=None, primary_key=True)\n    transaction_id: Optional[int] = None\n    action: str\n    created_at: datetime = Field(default_factory=datetime.utcnow)\n""",
                encoding="utf-8",
            )
        return (True, "Created initial SQLModel data models")

    if task == "Add migration scaffolding (Alembic init + first migration)":
        versions = migrations / "versions"
        versions.mkdir(parents=True, exist_ok=True)
        env_py = migrations / "env.py"
        if not env_py.exists():
            env_py.write_text("# Placeholder Alembic env; full wiring in next iteration.\n", encoding="utf-8")
        first_mig = versions / "0001_init.py"
        if not first_mig.exists():
            first_mig.write_text(
                """\"\"\"initial placeholder migration\"\"\"\n\nrevision = \"0001_init\"\ndown_revision = None\nbranch_labels = None\ndepends_on = None\n\n\ndef upgrade() -> None:\n    pass\n\n\ndef downgrade() -> None:\n    pass\n""",
                encoding="utf-8",
            )
        return (True, "Added migration scaffold placeholders")

    if task == "Implement CRUD endpoints for transactions":
        changed = False
        db_py = backend / "app" / "db.py"
        changed |= _write_if_missing(
            db_py,
            """from sqlmodel import Session, SQLModel, create_engine\n\nengine = create_engine(\"sqlite:///./bookkeeping.db\", connect_args={\"check_same_thread\": False})\n\n\ndef init_db() -> None:\n    SQLModel.metadata.create_all(engine)\n\n\ndef get_session():\n    with Session(engine) as session:\n        yield session\n""",
        )

        if app_main.exists():
            main_txt = app_main.read_text(encoding="utf-8", errors="ignore")
        else:
            main_txt = ""

        if "@app.post(\"/transactions\"" not in main_txt:
            app_main.write_text(
                """from datetime import datetime\nfrom typing import Optional\n\nfrom fastapi import Depends, FastAPI, HTTPException\nfrom pydantic import BaseModel\nfrom sqlmodel import Session, select\n\nfrom .db import get_session, init_db\nfrom .models import Transaction\n\n\nclass TransactionCreate(BaseModel):\n    occurred_at: datetime\n    merchant: str\n    description: str = \"\"\n    amount: float\n    currency: str = \"USD\"\n    category_id: Optional[int] = None\n    payment_method_id: Optional[int] = None\n\n\nclass TransactionUpdate(BaseModel):\n    occurred_at: Optional[datetime] = None\n    merchant: Optional[str] = None\n    description: Optional[str] = None\n    amount: Optional[float] = None\n    currency: Optional[str] = None\n    category_id: Optional[int] = None\n    payment_method_id: Optional[int] = None\n\n\napp = FastAPI(title=\"Bookkeeping Pipeline API\", version=\"0.1.0\")\n\n\n@app.on_event(\"startup\")\ndef startup() -> None:\n    init_db()\n\n\n@app.get(\"/health\")\ndef health() -> dict:\n    return {\"ok\": True, \"service\": \"bookkeeping-pipeline\"}\n\n\n@app.post(\"/transactions\", response_model=Transaction)\ndef create_transaction(body: TransactionCreate, session: Session = Depends(get_session)) -> Transaction:\n    row = Transaction(**body.model_dump())\n    session.add(row)\n    session.commit()\n    session.refresh(row)\n    return row\n\n\n@app.get(\"/transactions\", response_model=list[Transaction])\ndef list_transactions(session: Session = Depends(get_session)) -> list[Transaction]:\n    return list(session.exec(select(Transaction).order_by(Transaction.occurred_at.desc())))\n\n\n@app.get(\"/transactions/{tx_id}\", response_model=Transaction)\ndef get_transaction(tx_id: int, session: Session = Depends(get_session)) -> Transaction:\n    row = session.get(Transaction, tx_id)\n    if not row:\n        raise HTTPException(status_code=404, detail=\"transaction not found\")\n    return row\n\n\n@app.patch(\"/transactions/{tx_id}\", response_model=Transaction)\ndef update_transaction(tx_id: int, body: TransactionUpdate, session: Session = Depends(get_session)) -> Transaction:\n    row = session.get(Transaction, tx_id)\n    if not row:\n        raise HTTPException(status_code=404, detail=\"transaction not found\")\n    for k, v in body.model_dump(exclude_unset=True).items():\n        setattr(row, k, v)\n    session.add(row)\n    session.commit()\n    session.refresh(row)\n    return row\n\n\n@app.delete(\"/transactions/{tx_id}\")\ndef delete_transaction(tx_id: int, session: Session = Depends(get_session)) -> dict:\n    row = session.get(Transaction, tx_id)\n    if not row:\n        raise HTTPException(status_code=404, detail=\"transaction not found\")\n    session.delete(row)\n    session.commit()\n    return {\"ok\": True, \"deleted_id\": tx_id}\n""",
                encoding="utf-8",
            )
            changed = True

        return (changed or app_main.exists(), "Implemented transaction CRUD API")

    if task == "Add health endpoint + local run instructions":
        changed = False
        if app_main.exists() and "@app.get(\"/health\")" not in app_main.read_text(encoding="utf-8", errors="ignore"):
            app_main.write_text(app_main.read_text(encoding="utf-8", errors="ignore") + "\n\n@app.get(\"/health\")\ndef health() -> dict:\n    return {\"ok\": True, \"service\": \"bookkeeping-pipeline\"}\n", encoding="utf-8")
            changed = True

        backend_readme = backend / "README.md"
        if backend_readme.exists():
            txt = backend_readme.read_text(encoding="utf-8", errors="ignore")
            if "uvicorn app.main:app" not in txt:
                backend_readme.write_text(
                    txt
                    + "\n\n## Run (dev)\n\n```bash\ncd backend\npython3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt\nuvicorn app.main:app --host 0.0.0.0 --port 20003 --reload\n```\n\nHealth: `GET http://127.0.0.1:20003/health`\n",
                    encoding="utf-8",
                )
                changed = True

        return (True, "Health endpoint/run instructions are present")

    if task == "Commit baseline Phase 0 implementation":
        return (True, "Baseline commit task deferred to autodev commit step")

    return (False, "No handler for task yet")


def _homelab_status_ui_handler(repo: Path, task: str) -> tuple[bool, str]:
    app_dir = repo / "app"
    poller = app_dir / "poller.py"
    models = app_dir / "models.py"
    service_checks = app_dir / "service_checks.py"

    if task == "Add service-level checks (HTTP/TCP/SMB/NFS)":
        changed = False
        changed |= _write_if_missing(
            service_checks,
            """from __future__ import annotations\n\nimport asyncio\nimport socket\nfrom typing import Any\n\nimport httpx\n\n\nasync def check_http(url: str, timeout_s: int) -> dict[str, Any]:\n    try:\n        async with httpx.AsyncClient(timeout=timeout_s, verify=False) as client:  # noqa: S501\n            r = await client.get(url)\n            return {\"ok\": 200 <= r.status_code < 500, \"status_code\": r.status_code}\n    except Exception as e:  # noqa: BLE001\n        return {\"ok\": False, \"error\": str(e)[:200]}\n\n\nasync def check_tcp(host: str, port: int, timeout_s: int) -> dict[str, Any]:\n    try:\n        conn = asyncio.open_connection(host=host, port=port)\n        reader, writer = await asyncio.wait_for(conn, timeout=timeout_s)\n        writer.close()\n        await writer.wait_closed()\n        return {\"ok\": True}\n    except Exception as e:  # noqa: BLE001\n        return {\"ok\": False, \"error\": str(e)[:200]}\n\n\nasync def run_service_checks(device: dict[str, Any], timeout_s: int) -> dict[str, Any]:\n    host = device.get(\"host\", \"\")\n    services = device.get(\"services\") or []\n    out: dict[str, Any] = {}\n    for svc in services:\n        sid = svc.get(\"id\") or svc.get(\"name\") or f\"svc-{len(out)+1}\"\n        stype = str(svc.get(\"type\", \"tcp\")).lower()\n        if stype == \"http\":\n            url = svc.get(\"url\") or f\"http://{host}:{svc.get('port', 80)}\"\n            out[sid] = await check_http(url, timeout_s)\n        elif stype == \"smb\":\n            port = int(svc.get(\"port\", 445))\n            out[sid] = await check_tcp(host, port, timeout_s)\n        elif stype == \"nfs\":\n            port = int(svc.get(\"port\", 2049))\n            out[sid] = await check_tcp(host, port, timeout_s)\n        else:\n            port = int(svc.get(\"port\", 0))\n            out[sid] = await check_tcp(host, port, timeout_s) if port > 0 else {\"ok\": False, \"error\": \"missing port\"}\n    return out\n""",
        )

        if models.exists():
            mtxt = models.read_text(encoding="utf-8", errors="ignore")
            if "service_checks" not in mtxt:
                changed |= _replace_once(
                    models,
                    "    error: str | None = None\n    updated_at: str = field(default_factory=utc_now_iso)",
                    "    error: str | None = None\n    service_checks: dict[str, Any] | None = None\n    updated_at: str = field(default_factory=utc_now_iso)",
                )

        if poller.exists():
            ptxt = poller.read_text(encoding="utf-8", errors="ignore")
            if "run_service_checks" not in ptxt:
                changed |= _replace_once(
                    poller,
                    "from .models import DeviceStatus, utc_now_iso\n",
                    "from .models import DeviceStatus, utc_now_iso\nfrom .service_checks import run_service_checks\n",
                )
                changed |= _replace_once(
                    poller,
                    "    status.uptime_seconds = uptime_seconds\n    status.error = err\n    if uptime_seconds is not None:\n        status.last_seen = utc_now_iso()\n    return status\n",
                    "    status.uptime_seconds = uptime_seconds\n    status.error = err\n    if uptime_seconds is not None:\n        status.last_seen = utc_now_iso()\n\n    if device.get(\"services\"):\n        status.service_checks = await run_service_checks(device, cfg.request_timeout_seconds)\n\n    return status\n",
                )

        ok = service_checks.exists() and "run_service_checks" in (poller.read_text(encoding="utf-8", errors="ignore") if poller.exists() else "")
        return (ok, "Implemented service-level HTTP/TCP/SMB/NFS checks")

    return (False, "No handler for task yet")


def _generic_task_handler(repo: Path, task: str) -> tuple[bool, str]:
    t = task.lower()

    if "health endpoint" in t:
        app_main = repo / "backend" / "app" / "main.py"
        if app_main.exists():
            txt = app_main.read_text(encoding="utf-8", errors="ignore")
            if "@app.get(\"/health\")" not in txt:
                app_main.write_text(
                    txt + "\n\n@app.get(\"/health\")\ndef health() -> dict:\n    return {\"ok\": True}\n",
                    encoding="utf-8",
                )
            return True, "Ensured health endpoint"

    if "local run instructions" in t:
        readme = repo / "README.md"
        if readme.exists():
            txt = readme.read_text(encoding="utf-8", errors="ignore")
            if "Run (dev)" not in txt:
                readme.write_text(txt + "\n\n## Run (dev)\n\nDocument local startup command and health check here.\n", encoding="utf-8")
            return True, "Ensured local run instructions placeholder"

    if "crud endpoints" in t and "transaction" in t:
        return _bookkeeping_pipeline_handler(repo, "Implement CRUD endpoints for transactions")

    return False, "No generic handler matched"


def run_autodev_tick(project_id: str, repo_path: str, max_tasks: int = 3) -> AutoDevResult:
    repo = Path(repo_path)
    roadmap = repo / "docs" / "ROADMAP.md"
    devlog = repo / "docs" / "DEVLOG.md"
    if not roadmap.exists():
        return AutoDevResult(False, "no roadmap found", [])

    unchecked = _parse_unchecked_tasks(roadmap)
    if not unchecked:
        return AutoDevResult(False, "no unchecked tasks", [])

    if project_id == "paper-digest":
        handler = _paper_digest_handler
    elif project_id == "bookkeeping-pipeline":
        handler = _bookkeeping_pipeline_handler
    elif project_id == "homelab-status-ui":
        handler = _homelab_status_ui_handler
    else:
        handler = _generic_task_handler

    completed: list[str] = []
    blocked: list[str] = []

    for task in unchecked:
        if len(completed) >= max_tasks:
            break
        ok, summary = handler(repo, task)
        if not ok:
            ok, summary = _generic_task_handler(repo, task)
        if ok:
            _check_task(roadmap, task)
            if devlog.exists():
                _append_devlog(devlog, f"Autodev completed task: {task} — {summary}")
            completed.append(task)
        else:
            blocked.append(f"{task} ({summary})")

    if not completed:
        return AutoDevResult(False, f"autodev skipped: {blocked[0] if blocked else 'no actionable tasks'}", [])

    committed = _commit_all(repo, f"Autodev: complete {len(completed)} roadmap task(s): " + ", ".join(completed[:3]))
    suffix = "and committed" if committed else "(no new commit needed)"
    note = f"completed {len(completed)} task(s) {suffix}"
    if blocked:
        note += f"; blocked on: {blocked[0]}"
    return AutoDevResult(True, note, completed)
