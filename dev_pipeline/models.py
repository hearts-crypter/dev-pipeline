from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["active", "paused", "stopped", "finished", "blocked"]
Priority = Literal["low", "medium", "high"]


class Project(BaseModel):
    id: str
    name: str
    repo_path: str
    status: Status
    priority: Priority = "medium"
    spec_doc: str | None = None
    roadmap_doc: str | None = None
    next_milestone: str | None = None
    last_progress_at: str | None = None
    owner_notify_email: str = "dev@ahjc.me"
    notes: str | None = None
    webui_url: str | None = None
    repo_url: str | None = None
    repo_private: bool | None = None
    lock_mode: str | None = None  # manual|auto
    lock_owner: str | None = None
    lock_until: str | None = None


class Registry(BaseModel):
    projects: list[Project] = Field(default_factory=list)


class StatusChange(BaseModel):
    old_status: Status
    new_status: Status
    changed_at: datetime
    source: str = "api"
    note: str | None = None
