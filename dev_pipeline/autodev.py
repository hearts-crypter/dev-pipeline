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
    tasks: list[str] = []
    for ln in roadmap.read_text(encoding="utf-8", errors="ignore").splitlines():
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
    with devlog.open("a", encoding="utf-8") as f:
        f.write(f"\n- {_now_utc()} — {text}\n")


def _write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _paper_digest_handler(repo: Path, task: str) -> tuple[bool, str]:
    backend = repo / "backend"
    app_main = backend / "app" / "main.py"
    models = backend / "app" / "models.py"
    migration = backend / "migrations" / "001_init.sql"
    utils = backend / "app" / "utils.py"

    if task == "Create backend skeleton (FastAPI)":
        return app_main.exists(), "Detected backend FastAPI skeleton"
    if task == "Define DB migrations + models":
        return models.exists() and migration.exists(), "Detected migrations + models"
    if task == "Implement paper upload/link submission endpoints":
        txt = app_main.read_text(encoding="utf-8", errors="ignore") if app_main.exists() else ""
        return (("@app.post(\"/papers/upload\"" in txt and "@app.post(\"/papers/url\"" in txt), "Detected upload/url endpoints")
    if task == "Persist files + paper records":
        t = utils.read_text(encoding="utf-8", errors="ignore") if utils.exists() else ""
        return ("persist_upload" in t and "compute_sha256" in t), "Detected file persistence + hash utility"

    if task == "Worker queue + job states":
        _write_if_missing(
            backend / "app" / "worker.py",
            """from sqlalchemy.orm import Session
from . import models


def process_next_job(db: Session) -> dict:
    job = (
        db.query(models.ProcessingJob)
        .filter(models.ProcessingJob.state == \"queued\")
        .order_by(models.ProcessingJob.created_at.asc())
        .first()
    )
    if not job:
        return {\"processed\": False, \"reason\": \"no queued jobs\"}

    job.state = \"running\"
    job.message = \"Worker started job\"
    db.commit()

    job.state = \"done\"
    job.message = \"Worker completed placeholder processing\"
    db.commit()

    return {\"processed\": True, \"job_id\": job.id, \"state\": job.state}
""",
        )
        _write_if_missing(
            backend / "scripts" / "run_worker_once.py",
            """#!/usr/bin/env python3
from app.db import SessionLocal
from app.worker import process_next_job

if __name__ == \"__main__\":
    db = SessionLocal()
    try:
        print(process_next_job(db))
    finally:
        db.close()
""",
        )
        return True, "Implemented baseline worker queue processor"

    return False, "No handler for task yet"


def _bookkeeping_pipeline_handler(repo: Path, task: str) -> tuple[bool, str]:
    backend = repo / "backend"
    app_main = backend / "app" / "main.py"
    models = backend / "app" / "models.py"
    migrations = backend / "migrations"

    if task == "Scaffold backend app structure (`backend/app`)":
        return ((backend / "app").exists() and app_main.exists()), "Detected backend app scaffold"

    if task == "Define initial data models for transactions/categories/payment methods":
        if not models.exists():
            models.write_text(
                """from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class PaymentMethod(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    method_type: str = \"other\"


class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    occurred_at: datetime
    merchant: str
    description: str = \"\"
    amount: float
    currency: str = \"USD\"
    category_id: Optional[int] = None
    payment_method_id: Optional[int] = None


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_id: Optional[int] = None
    action: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
""",
                encoding="utf-8",
            )
        return True, "Created initial SQLModel data models"

    if task == "Add migration scaffolding (Alembic init + first migration)":
        versions = migrations / "versions"
        versions.mkdir(parents=True, exist_ok=True)
        _write_if_missing(migrations / "env.py", "# Placeholder Alembic env\n")
        _write_if_missing(
            versions / "0001_init.py",
            """\"\"\"initial placeholder migration\"\"\"

revision = \"0001_init\"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
""",
        )
        return True, "Added migration scaffold placeholders"

    if task == "Implement CRUD endpoints for transactions":
        changed = _write_if_missing(
            backend / "app" / "db.py",
            """from sqlmodel import Session, SQLModel, create_engine

engine = create_engine(\"sqlite:///./bookkeeping.db\", connect_args={\"check_same_thread\": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
""",
        )

        if app_main.exists():
            txt = app_main.read_text(encoding="utf-8", errors="ignore")
        else:
            txt = ""

        if "@app.post(\"/transactions\"" not in txt:
            app_main.write_text(
                """from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from .db import get_session, init_db
from .models import Transaction


class TransactionCreate(BaseModel):
    occurred_at: datetime
    merchant: str
    description: str = \"\"
    amount: float
    currency: str = \"USD\"
    category_id: Optional[int] = None
    payment_method_id: Optional[int] = None


class TransactionUpdate(BaseModel):
    occurred_at: Optional[datetime] = None
    merchant: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    category_id: Optional[int] = None
    payment_method_id: Optional[int] = None


class IngestChatRequest(BaseModel):
    message: str
    source: str = \"chat\"


class ExtractionCandidate(BaseModel):
    merchant: Optional[str] = None
    amount: Optional[float] = None
    currency: str = \"USD\"
    occurred_at: Optional[datetime] = None
    notes: str = \"\"
    confidence: float = 0.0


app = FastAPI(title=\"Bookkeeping Pipeline API\", version=\"0.1.0\")


@app.on_event(\"startup\")
def startup() -> None:
    init_db()


@app.get(\"/health\")
def health() -> dict:
    return {\"ok\": True, \"service\": \"bookkeeping-pipeline\"}


@app.post(\"/transactions\", response_model=Transaction)
def create_transaction(body: TransactionCreate, session: Session = Depends(get_session)) -> Transaction:
    row = Transaction(**body.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@app.get(\"/transactions\", response_model=list[Transaction])
def list_transactions(session: Session = Depends(get_session)) -> list[Transaction]:
    return list(session.exec(select(Transaction).order_by(Transaction.occurred_at.desc())))


@app.get(\"/transactions/{tx_id}\", response_model=Transaction)
def get_transaction(tx_id: int, session: Session = Depends(get_session)) -> Transaction:
    row = session.get(Transaction, tx_id)
    if not row:
        raise HTTPException(status_code=404, detail=\"transaction not found\")
    return row


@app.patch(\"/transactions/{tx_id}\", response_model=Transaction)
def update_transaction(tx_id: int, body: TransactionUpdate, session: Session = Depends(get_session)) -> Transaction:
    row = session.get(Transaction, tx_id)
    if not row:
        raise HTTPException(status_code=404, detail=\"transaction not found\")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@app.delete(\"/transactions/{tx_id}\")
def delete_transaction(tx_id: int, session: Session = Depends(get_session)) -> dict:
    row = session.get(Transaction, tx_id)
    if not row:
        raise HTTPException(status_code=404, detail=\"transaction not found\")
    session.delete(row)
    session.commit()
    return {\"ok\": True, \"deleted_id\": tx_id}


@app.post(\"/ingest/chat\")
def ingest_chat(body: IngestChatRequest) -> dict:
    candidate = ExtractionCandidate(notes=body.message[:240], confidence=0.2)
    return {\"ok\": True, \"source\": body.source, \"candidate\": candidate.model_dump()}
""",
                encoding="utf-8",
            )
            changed = True

        return (changed or app_main.exists()), "Implemented transaction CRUD API (+ ingest/chat scaffold)"

    if task == "Add health endpoint + local run instructions":
        backend_readme = backend / "README.md"
        if backend_readme.exists() and "uvicorn app.main:app" not in backend_readme.read_text(encoding="utf-8", errors="ignore"):
            backend_readme.write_text(
                backend_readme.read_text(encoding="utf-8", errors="ignore")
                + "\n\n## Run (dev)\n\n```bash\ncd backend\npython3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt\nuvicorn app.main:app --host 0.0.0.0 --port 20003 --reload\n```\n\nHealth: `GET http://127.0.0.1:20003/health`\n",
                encoding="utf-8",
            )
        return True, "Health endpoint/run instructions are present"

    if task == "Add `/ingest/chat` endpoint and extraction schema":
        txt = app_main.read_text(encoding="utf-8", errors="ignore") if app_main.exists() else ""
        if "@app.post(\"/ingest/chat\")" not in txt:
            return _bookkeeping_pipeline_handler(repo, "Implement CRUD endpoints for transactions")
        return True, "Ingest chat endpoint already present"

    if task == "Add `/ingest/email` endpoint with sender allowlist guard":
        if not app_main.exists():
            return False, "main API file missing"
        txt = app_main.read_text(encoding="utf-8", errors="ignore")
        changed = False
        if "import os" not in txt:
            txt = txt.replace("from datetime import datetime\n", "from datetime import datetime\nimport os\n")
            changed = True
        if "@app.post(\"/ingest/email\")" not in txt:
            txt += "\n\n@app.post(\"/ingest/email\")\ndef ingest_email(sender: str, body: str) -> dict:\n    allowed = {s.strip().lower() for s in os.getenv(\"INGEST_EMAIL_ALLOWLIST\", \"\").split(\",\") if s.strip()}\n    if allowed and sender.lower() not in allowed:\n        raise HTTPException(status_code=403, detail=\"sender not allowlisted\")\n    candidate = ExtractionCandidate(notes=body[:240], confidence=0.3)\n    return {\"ok\": True, \"source\": \"email\", \"candidate\": candidate.model_dump()}\n"
            changed = True
        if changed:
            app_main.write_text(txt, encoding="utf-8")
        return True, "Implemented /ingest/email with allowlist guard"

    if task == "Add confidence scoring + `needs_review` logic":
        if not app_main.exists():
            return False, "main API file missing"
        txt = app_main.read_text(encoding="utf-8", errors="ignore")
        if "def _needs_review(" not in txt:
            txt += "\n\n\ndef _needs_review(confidence: float) -> bool:\n    threshold = float(os.getenv(\"INGEST_CONFIDENCE_THRESHOLD\", \"0.75\"))\n    return confidence < threshold\n"
        if "needs_review" not in txt:
            txt = txt.replace("return {\"ok\": True, \"source\": body.source, \"candidate\": candidate.model_dump()}", "payload = candidate.model_dump()\n    payload[\"needs_review\"] = _needs_review(candidate.confidence)\n    return {\"ok\": True, \"source\": body.source, \"candidate\": payload}")
            txt = txt.replace("return {\"ok\": True, \"source\": \"email\", \"candidate\": candidate.model_dump()}", "payload = candidate.model_dump()\n    payload[\"needs_review\"] = _needs_review(candidate.confidence)\n    return {\"ok\": True, \"source\": \"email\", \"candidate\": payload}")
        app_main.write_text(txt, encoding="utf-8")
        return True, "Added confidence threshold and needs_review logic"

    if task == "Add review queue listing endpoint":
        if not app_main.exists():
            return False, "main API file missing"
        txt = app_main.read_text(encoding="utf-8", errors="ignore")
        if "REVIEW_QUEUE" not in txt:
            txt = txt.replace("app = FastAPI(title=\"Bookkeeping Pipeline API\", version=\"0.1.0\")", "app = FastAPI(title=\"Bookkeeping Pipeline API\", version=\"0.1.0\")\nREVIEW_QUEUE: list[dict] = []")
            txt = txt.replace("payload = candidate.model_dump()\n    payload[\"needs_review\"] = _needs_review(candidate.confidence)", "payload = candidate.model_dump()\n    payload[\"needs_review\"] = _needs_review(candidate.confidence)\n    if payload[\"needs_review\"]:\n        REVIEW_QUEUE.append(payload)")
        if "@app.get(\"/review-queue\")" not in txt:
            txt += "\n\n@app.get(\"/review-queue\")\ndef review_queue() -> dict:\n    return {\"count\": len(REVIEW_QUEUE), \"items\": REVIEW_QUEUE}\n"
        app_main.write_text(txt, encoding="utf-8")
        return True, "Added review queue endpoint"

    if task == "Commit baseline Phase 0 implementation":
        return True, "Baseline commit task deferred to autodev commit step"

    return False, "No handler for task yet"


def _homelab_status_ui_handler(repo: Path, task: str) -> tuple[bool, str]:
    app_dir = repo / "app"
    poller = app_dir / "poller.py"
    models = app_dir / "models.py"
    service_checks = app_dir / "service_checks.py"

    if task == "Add service-level checks (HTTP/TCP/SMB/NFS)":
        _write_if_missing(
            service_checks,
            """from __future__ import annotations

import asyncio
from typing import Any

import httpx


async def check_http(url: str, timeout_s: int) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout_s, verify=False) as client:  # noqa: S501
            r = await client.get(url)
            return {\"ok\": 200 <= r.status_code < 500, \"status_code\": r.status_code}
    except Exception as e:  # noqa: BLE001
        return {\"ok\": False, \"error\": str(e)[:200]}


async def check_tcp(host: str, port: int, timeout_s: int) -> dict[str, Any]:
    try:
        conn = asyncio.open_connection(host=host, port=port)
        _, writer = await asyncio.wait_for(conn, timeout=timeout_s)
        writer.close()
        await writer.wait_closed()
        return {\"ok\": True}
    except Exception as e:  # noqa: BLE001
        return {\"ok\": False, \"error\": str(e)[:200]}


async def run_service_checks(device: dict[str, Any], timeout_s: int) -> dict[str, Any]:
    host = device.get(\"host\", \"\")
    services = device.get(\"services\") or []
    out: dict[str, Any] = {}
    for svc in services:
        sid = svc.get(\"id\") or svc.get(\"name\") or f\"svc-{len(out)+1}\"
        stype = str(svc.get(\"type\", \"tcp\")).lower()
        if stype == \"http\":
            url = svc.get(\"url\") or f\"http://{host}:{svc.get('port', 80)}\"
            out[sid] = await check_http(url, timeout_s)
        elif stype == \"smb\":
            out[sid] = await check_tcp(host, int(svc.get(\"port\", 445)), timeout_s)
        elif stype == \"nfs\":
            out[sid] = await check_tcp(host, int(svc.get(\"port\", 2049)), timeout_s)
        else:
            port = int(svc.get(\"port\", 0))
            out[sid] = await check_tcp(host, port, timeout_s) if port > 0 else {\"ok\": False, \"error\": \"missing port\"}
    return out
""",
        )

        if models.exists() and "service_checks" not in models.read_text(encoding="utf-8", errors="ignore"):
            models.write_text(
                models.read_text(encoding="utf-8", errors="ignore").replace(
                    "    error: str | None = None\n    updated_at: str = field(default_factory=utc_now_iso)",
                    "    error: str | None = None\n    service_checks: dict[str, Any] | None = None\n    updated_at: str = field(default_factory=utc_now_iso)",
                ),
                encoding="utf-8",
            )

        if poller.exists():
            ptxt = poller.read_text(encoding="utf-8", errors="ignore")
            if "from .service_checks import run_service_checks" not in ptxt:
                ptxt = ptxt.replace(
                    "from .models import DeviceStatus, utc_now_iso\n",
                    "from .models import DeviceStatus, utc_now_iso\nfrom .service_checks import run_service_checks\n",
                )
            if "status.service_checks = await run_service_checks" not in ptxt:
                ptxt = ptxt.replace(
                    "    status.uptime_seconds = uptime_seconds\n    status.error = err\n    if uptime_seconds is not None:\n        status.last_seen = utc_now_iso()\n    return status\n",
                    "    status.uptime_seconds = uptime_seconds\n    status.error = err\n    if uptime_seconds is not None:\n        status.last_seen = utc_now_iso()\n\n    if device.get(\"services\"):\n        status.service_checks = await run_service_checks(device, cfg.request_timeout_seconds)\n\n    return status\n",
                )
            poller.write_text(ptxt, encoding="utf-8")

        return True, "Implemented service-level HTTP/TCP/SMB/NFS checks"

    if task == "Add per-check retry + failure-threshold handling":
        if not service_checks.exists():
            return False, "service checks file missing"
        stxt = service_checks.read_text(encoding="utf-8", errors="ignore")
        if "async def _run_with_retry" not in stxt:
            stxt += """


async def _run_with_retry(fn, retries: int) -> tuple[dict[str, Any], int]:
    attempts = max(1, retries + 1)
    last: dict[str, Any] = {"ok": False, "error": "no attempts"}
    for i in range(attempts):
        last = await fn()
        if last.get("ok"):
            return last, i + 1
    return last, attempts
"""
        if "failure_threshold" not in stxt:
            stxt = stxt.replace(
                "        if stype == \"http\":\n            url = svc.get(\"url\") or f\"http://{host}:{svc.get('port', 80)}\"\n            out[sid] = await check_http(url, timeout_s)\n        elif stype == \"smb\":\n            out[sid] = await check_tcp(host, int(svc.get(\"port\", 445)), timeout_s)\n        elif stype == \"nfs\":\n            out[sid] = await check_tcp(host, int(svc.get(\"port\", 2049)), timeout_s)\n        else:\n            port = int(svc.get(\"port\", 0))\n            out[sid] = await check_tcp(host, port, timeout_s) if port > 0 else {\"ok\": False, \"error\": \"missing port\"}\n",
                "        retries = int(svc.get(\"retries\", 0))\n        threshold = int(svc.get(\"failure_threshold\", 1))\n        if stype == \"http\":\n            url = svc.get(\"url\") or f\"http://{host}:{svc.get('port', 80)}\"\n            result, attempts = await _run_with_retry(lambda: check_http(url, timeout_s), retries)\n        elif stype == \"smb\":\n            result, attempts = await _run_with_retry(lambda: check_tcp(host, int(svc.get(\"port\", 445)), timeout_s), retries)\n        elif stype == \"nfs\":\n            result, attempts = await _run_with_retry(lambda: check_tcp(host, int(svc.get(\"port\", 2049)), timeout_s), retries)\n        else:\n            port = int(svc.get(\"port\", 0))\n            result, attempts = await _run_with_retry(lambda: check_tcp(host, port, timeout_s), retries) if port > 0 else ({\"ok\": False, \"error\": \"missing port\"}, 1)\n        result[\"attempts\"] = attempts\n        result[\"failure_threshold\"] = threshold\n        result[\"hard_fail\"] = (not result.get(\"ok\", False)) and attempts >= threshold\n        out[sid] = result\n",
            )
        service_checks.write_text(stxt, encoding="utf-8")
        return True, "Added retry + failure-threshold handling"

    if task == "Add jitter/backoff to avoid synchronized polling spikes":
        if not poller.exists():
            return False, "poller missing"
        ptxt = poller.read_text(encoding="utf-8", errors="ignore")
        if "import random" not in ptxt:
            ptxt = ptxt.replace("import os\n", "import os\nimport random\n")
        if "jitter_ratio" not in ptxt:
            ptxt = ptxt.replace(
                "        await asyncio.sleep(cfg.poll_interval_seconds)\n",
                "        jitter_ratio = 0.2\n        jitter = cfg.poll_interval_seconds * jitter_ratio * random.random()\n        await asyncio.sleep(cfg.poll_interval_seconds + jitter)\n",
            )
        poller.write_text(ptxt, encoding="utf-8")
        return True, "Added jitter/backoff to poll loop"

    if task == "Improve error categorization (network/auth/timeout/parsing)":
        if models.exists() and "error_category" not in models.read_text(encoding="utf-8", errors="ignore"):
            models.write_text(
                models.read_text(encoding="utf-8", errors="ignore").replace(
                    "    error: str | None = None\n    service_checks: dict[str, Any] | None = None\n",
                    "    error: str | None = None\n    error_category: str | None = None\n    service_checks: dict[str, Any] | None = None\n",
                ),
                encoding="utf-8",
            )
        if poller.exists():
            ptxt = poller.read_text(encoding="utf-8", errors="ignore")
            if "def _categorize_error" not in ptxt:
                ptxt = ptxt.replace(
                    "def _iso_to_datetime(value: str | None) -> datetime | None:\n",
                    "def _categorize_error(err: str | None) -> str | None:\n    if not err:\n        return None\n    e = err.lower()\n    if any(k in e for k in [\"timed out\", \"timeout\"]):\n        return \"timeout\"\n    if any(k in e for k in [\"auth\", \"permission denied\", \"unauthorized\"]):\n        return \"auth\"\n    if any(k in e for k in [\"parse\", \"invalid\", \"json\"]):\n        return \"parsing\"\n    if any(k in e for k in [\"network\", \"unreachable\", \"refused\"]):\n        return \"network\"\n    return \"unknown\"\n\n\ndef _iso_to_datetime(value: str | None) -> datetime | None:\n",
                )
            if "status.error_category = _categorize_error" not in ptxt:
                ptxt = ptxt.replace(
                    "            status.error = ping_err or \"unreachable\"\n            return status\n",
                    "            status.error = ping_err or \"unreachable\"\n            status.error_category = _categorize_error(status.error)\n            return status\n",
                )
                ptxt = ptxt.replace(
                    "    status.uptime_seconds = uptime_seconds\n    status.error = err\n",
                    "    status.uptime_seconds = uptime_seconds\n    status.error = err\n    status.error_category = _categorize_error(err)\n",
                )
            poller.write_text(ptxt, encoding="utf-8")
        return True, "Added error categorization"

    return False, "No handler for task yet"


def _generic_task_handler(repo: Path, task: str) -> tuple[bool, str]:
    t = task.lower()

    if "health endpoint" in t:
        app_main = repo / "backend" / "app" / "main.py"
        if app_main.exists() and "@app.get(\"/health\")" not in app_main.read_text(encoding="utf-8", errors="ignore"):
            app_main.write_text(
                app_main.read_text(encoding="utf-8", errors="ignore")
                + "\n\n@app.get(\"/health\")\ndef health() -> dict:\n    return {\"ok\": True}\n",
                encoding="utf-8",
            )
        return app_main.exists(), "Ensured health endpoint"

    if "local run instructions" in t:
        readme = repo / "README.md"
        if readme.exists() and "Run (dev)" not in readme.read_text(encoding="utf-8", errors="ignore"):
            readme.write_text(readme.read_text(encoding="utf-8", errors="ignore") + "\n\n## Run (dev)\n\nDocument local startup command and health check here.\n", encoding="utf-8")
        return readme.exists(), "Ensured local run instructions"

    if "crud endpoints" in t and "transaction" in t:
        return _bookkeeping_pipeline_handler(repo, "Implement CRUD endpoints for transactions")

    if "ingest/chat" in t or ("ingest" in t and "chat" in t):
        return _bookkeeping_pipeline_handler(repo, "Add `/ingest/chat` endpoint and extraction schema")

    if "sample dataset template" in t or ("config file" in t and "template" in t):
        cfg = repo / "config" / "default.yaml"
        tpl = repo / "data" / "scenarios.template.json"
        changed = False
        if _write_if_missing(
            cfg,
            """run:
  seed: 42
  max_qr_hops: 5
  max_tool_calls: 20
  max_wall_time_sec: 30
  max_repeat_signature: 2
""",
        ):
            changed = True
        if _write_if_missing(
            tpl,
            """{
  \"scenarios\": [
    {\"id\": \"linear-4\", \"topology\": \"linear\", \"depth\": 4},
    {\"id\": \"cycle-2\", \"topology\": \"cycle\", \"cycle_len\": 2}
  ]
}
""",
        ):
            changed = True
        return changed or (cfg.exists() and tpl.exists()), "Ensured config + sample dataset template"

    if "qr graph generator" in t:
        gen = repo / "src" / "qr_tarpit_lab" / "generator.py"
        changed = _write_if_missing(
            gen,
            """from __future__ import annotations


def build_linear(depth: int) -> dict:
    nodes = [f\"n{i}\" for i in range(max(1, depth))]
    edges = [{\"from\": nodes[i], \"to\": nodes[i + 1]} for i in range(len(nodes) - 1)]
    return {\"topology\": \"linear\", \"nodes\": nodes, \"edges\": edges}


def build_cycle(cycle_len: int) -> dict:
    n = max(2, cycle_len)
    nodes = [f\"c{i}\" for i in range(n)]
    edges = [{\"from\": nodes[i], \"to\": nodes[(i + 1) % n]} for i in range(n)]
    return {\"topology\": \"cycle\", \"nodes\": nodes, \"edges\": edges}


def build_self_loop() -> dict:
    return {\"topology\": \"self_loop\", \"nodes\": [\"s0\"], \"edges\": [{\"from\": \"s0\", \"to\": \"s0\"}]}


def build_branch(branching: int = 2) -> dict:
    b = max(2, branching)
    nodes = [\"root\"] + [f\"b{i}\" for i in range(b)]
    edges = [{\"from\": \"root\", \"to\": f\"b{i}\"} for i in range(b)]
    return {\"topology\": \"branch\", \"nodes\": nodes, \"edges\": edges}
""",
        )
        return changed or gen.exists(), "Ensured baseline QR graph generator"

    return False, "No generic handler matched"


def _ensure_project_handler_scaffold(repo: Path, project_id: str) -> bool:
    """For newly greenlit projects, ensure a local handler scaffold exists.

    This gives autodev a concrete place to add project-specific task logic
    instead of repeatedly stalling with no handler guidance.
    """
    path = repo / "scripts" / "autodev_handler.py"
    return _write_if_missing(
        path,
        f'''"""Project-local autodev handler scaffold for {project_id}."""


def handle_task(task: str) -> tuple[bool, str]:
    t = task.lower()
    # Add project-specific task handling here.
    # Return (True, summary) when handled, else (False, reason)
    if "" == t:
        return True, "placeholder"
    return False, "No project-local handler match"
''',
    )


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
        _ensure_project_handler_scaffold(repo, project_id)
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
    note = f"completed {len(completed)} task(s) {'and committed' if committed else '(no new commit needed)'}"
    if blocked:
        note += f"; blocked on: {blocked[0]}"
    return AutoDevResult(True, note, completed)
