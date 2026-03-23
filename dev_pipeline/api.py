from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .email_utils import send_email
from .locks import acquire_lock, release_lock
from .logs_api import get_notifications, get_publish_requests, get_repo_requests, get_runs, get_status_audit
from .milestones import detect_and_notify
from .project_detail import build_project_timeline
from .publish_manager import process_publish_requests, publish_project_now, set_repo_visibility, sync_all_repo_urls
from .publish_requests import submit_publish_request
from .registry import get_project, load_registry, set_project_status
from .repo_manager import process_repo_requests
from .repo_requests import submit_repo_request
from .sweeper import run_sweep

ROOT = Path(__file__).resolve().parents[1]
WEBUI_DIR = ROOT / "webui"

app = FastAPI(title="Dev Pipeline API", version="0.2.0")

if WEBUI_DIR.exists():
    app.mount("/webui", StaticFiles(directory=str(WEBUI_DIR)), name="webui")


class StatusPatch(BaseModel):
    status: str
    note: str | None = None


class EmailTestBody(BaseModel):
    to: str | None = None


class RepoRequestBody(BaseModel):
    source: str = 'webui'


class RepoVisibilityBody(BaseModel):
    visibility: str = 'public'
    source: str = 'webui'


class LockBody(BaseModel):
    owner: str = 'webui'
    ttl_minutes: int = 90
    force: bool = False


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
    sync_all_repo_urls()
    return load_registry().model_dump(mode="json")


@app.get("/projects/{project_id}")
def project_detail(project_id: str):
    try:
        _, p = get_project(project_id)
        return p.model_dump(mode="json")
    except KeyError:
        raise HTTPException(status_code=404, detail="project not found")


@app.get("/projects/{project_id}/timeline")
def project_timeline(project_id: str, limit: int = 100):
    try:
        return build_project_timeline(project_id, limit=limit)
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


@app.get('/logs/repo-requests')
def logs_repo_requests(limit: int = 50):
    return get_repo_requests(limit=limit)


@app.get('/logs/publish-requests')
def logs_publish_requests(limit: int = 50):
    return get_publish_requests(limit=limit)


@app.post('/projects/{project_id}/repo-request')
def project_repo_request(project_id: str, body: RepoRequestBody):
    try:
        rec = submit_repo_request(project_id, source=body.source)
        return {'ok': True, 'request': rec}
    except KeyError:
        raise HTTPException(status_code=404, detail='project not found')


@app.post('/runs/process-repo-requests')
def run_process_repo_requests(limit: int = 20):
    return process_repo_requests(limit=limit)


@app.post('/runs/process-publish-requests')
def run_process_publish_requests(limit: int = 20):
    return process_publish_requests(limit=limit)


@app.post('/projects/{project_id}/publish-request')
def project_publish_request(project_id: str, body: RepoRequestBody):
    try:
        queued = submit_publish_request(project_id, source=body.source)
        result = publish_project_now(project_id, source=body.source)
        return {'ok': result.get('status') == 'fulfilled', 'queued': queued, 'result': result}
    except KeyError:
        raise HTTPException(status_code=404, detail='project not found')


@app.post('/projects/{project_id}/focus-start')
def project_focus_start(project_id: str, body: LockBody):
    try:
        res = acquire_lock(project_id, mode='manual', owner=body.owner, ttl_minutes=body.ttl_minutes, force=body.force)
        return {'ok': bool(res.get('ok')), 'lock': res}
    except KeyError:
        raise HTTPException(status_code=404, detail='project not found')


@app.post('/projects/{project_id}/focus-stop')
def project_focus_stop(project_id: str, body: LockBody):
    try:
        res = release_lock(project_id, owner=body.owner, force=body.force)
        return {'ok': bool(res.get('ok')), 'lock': res}
    except KeyError:
        raise HTTPException(status_code=404, detail='project not found')


@app.post('/projects/{project_id}/repo-visibility')
def project_repo_visibility(project_id: str, body: RepoVisibilityBody):
    try:
        result = set_repo_visibility(project_id, visibility=body.visibility, source=body.source)
        return {'ok': result.get('status') == 'fulfilled', 'result': result}
    except KeyError:
        raise HTTPException(status_code=404, detail='project not found')


@app.post('/projects/{project_id}/email-test')
def project_email_test(project_id: str, body: EmailTestBody):
    try:
        _, p = get_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail='project not found')

    recipient = body.to or p.owner_notify_email
    subject = f"[Test] Dev Pipeline notification for {p.name}"
    message = (
        f"This is a test notification for project {p.name} ({p.id}).\n"
        f"Status: {p.status}\n"
        f"Next milestone: {p.next_milestone or 'unspecified'}\n"
    )
    try:
        send_email(recipient, subject, message)
        return {'ok': True, 'recipient': recipient}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
