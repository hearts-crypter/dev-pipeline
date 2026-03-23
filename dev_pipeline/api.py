from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .registry import get_project, load_registry, set_project_status
from .sweeper import run_sweep

app = FastAPI(title="Dev Pipeline API", version="0.1.0")


class StatusPatch(BaseModel):
    status: str
    note: str | None = None


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
