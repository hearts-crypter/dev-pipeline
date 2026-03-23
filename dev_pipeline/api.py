from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .logs_api import get_notifications, get_runs, get_status_audit
from .milestones import detect_and_notify
from .registry import get_project, load_registry, set_project_status
from .sweeper import run_sweep

ROOT = Path(__file__).resolve().parents[1]
WEBUI_DIR = ROOT / "webui"

app = FastAPI(title="Dev Pipeline API", version="0.2.0")

if WEBUI_DIR.exists():
    app.mount("/webui", StaticFiles(directory=str(WEBUI_DIR)), name="webui")


class StatusPatch(BaseModel):
    status: str
    note: str | None = None


@app.get("/")
def ui_root():
    if WEBUI_DIR.exists() and (WEBUI_DIR / "index.html").exists():
        return FileResponse(WEBUI_DIR / "index.html")
    return {"ok": True, "message": "webui not found"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/projects")
def list_projects():
    return load_registry().model_dump(mode="json")


@app.get("/projects/{project_id}")
def project_detail(project_id: str):
    try:
        _, p = get_project(project_id)
        return p.model_dump(mode="json")
    except KeyError:
        raise HTTPException(status_code=404, detail="project not found")


@app.patch("/projects/{project_id}/status")
def patch_status(project_id: str, body: StatusPatch):
    try:
        p = set_project_status(project_id, body.status, source="api", note=body.note)
        return p.model_dump(mode="json")
    except KeyError:
        raise HTTPException(status_code=404, detail="project not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/runs/sweep")
def trigger_sweep():
    return run_sweep()


@app.post("/runs/milestones-notify")
def trigger_milestone_notify():
    return detect_and_notify()


@app.get("/logs/runs")
def logs_runs(limit: int = 50):
    return get_runs(limit=limit)


@app.get("/logs/status-audit")
def logs_status_audit(limit: int = 50):
    return get_status_audit(limit=limit)


@app.get("/logs/notifications")
def logs_notifications(limit: int = 50):
    return get_notifications(limit=limit)
