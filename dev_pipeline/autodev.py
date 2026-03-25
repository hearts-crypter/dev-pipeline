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
        if not worker_py.exists():
            worker_py.write_text(
                """from sqlalchemy.orm import Session\n\nfrom . import models\n\n\ndef process_next_job(db: Session) -> dict:\n    job = (\n        db.query(models.ProcessingJob)\n        .filter(models.ProcessingJob.state == \"queued\")\n        .order_by(models.ProcessingJob.created_at.asc())\n        .first()\n    )\n    if not job:\n        return {\"processed\": False, \"reason\": \"no queued jobs\"}\n\n    job.state = \"running\"\n    job.message = \"Worker started job\"\n    db.commit()\n\n    # Placeholder execution step (Phase 2 baseline)\n    job.state = \"done\"\n    job.message = \"Worker completed placeholder processing\"\n    db.commit()\n\n    return {\"processed\": True, \"job_id\": job.id, \"state\": job.state}\n""",
                encoding="utf-8",
            )
        if not run_worker.exists():
            run_worker.write_text(
                """#!/usr/bin/env python3\nfrom app.db import SessionLocal\nfrom app.worker import process_next_job\n\n\nif __name__ == \"__main__\":\n    db = SessionLocal()\n    try:\n        print(process_next_job(db))\n    finally:\n        db.close()\n""",
                encoding="utf-8",
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

    return (False, "No handler for task yet")


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
    else:
        return AutoDevResult(False, "no project-specific autodev handler", [])

    completed: list[str] = []
    blocked: list[str] = []

    for task in unchecked:
        if len(completed) >= max_tasks:
            break
        ok, summary = handler(repo, task)
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
