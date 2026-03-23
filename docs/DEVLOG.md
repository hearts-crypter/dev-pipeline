# Dev Log

## 2026-03-23

### Phase 1 implementation
- Added Python package `dev_pipeline` with:
  - `registry.py` (load/save registry, project lookup, status updates)
  - `sweeper.py` (active project sweep + run logging)
  - `api.py` (FastAPI endpoints for project list/detail/status + manual sweep)
- Added logs path conventions:
  - `logs/runs.jsonl`
  - `logs/status_audit.jsonl`
- Added scripts:
  - `scripts/run_sweep.py`
  - `scripts/set_status.py`
  - `scripts/run_api.sh`
- Added `requirements.txt` and `.gitignore`.

### Status
- Functional for project registry and status lifecycle management.
- Sweep currently performs project inspection + logging (bounded automation).

### Phase 2 additions (in progress)
- Added milestone detection from roadmap phase checklists and notifier pipeline:
  - `dev_pipeline/milestones.py`
  - `scripts/milestone_notify.py`
- Added outbound email utility module for automated milestone updates:
  - `dev_pipeline/email_utils.py`
- Added newsletter project-section renderer:
  - `dev_pipeline/newsletter.py`
  - `scripts/render_newsletter_section.py`
- Extended API with `POST /runs/milestones-notify`.

### Web UI + log APIs
- Added minimal Web UI under `webui/`:
  - `index.html`
  - `app.js`
- Added JSON log endpoints:
  - `GET /logs/runs`
  - `GET /logs/status-audit`
  - `GET /logs/notifications`
- Added project detail/timeline + test email API:
  - `GET /projects/{id}/timeline`
  - `POST /projects/{id}/email-test`
- API root (`/`) now serves the web UI.
- Added `dev_pipeline/logs_api.py` helper for JSONL log retrieval.
- Default API launcher now serves on `0.0.0.0:20001`.

### UI refinement block
- Improved project detail panel to show structured timeline sections (status changes, notifications, runs) instead of raw JSON.
- Added optional `repo_url` field to project model/registry.
- Added GitHub quick-link button per project row when `repo_url` is present.
- Added `Request Repo` button for projects without `repo_url`.
- Added repo request API + log endpoint:
  - `POST /projects/{id}/repo-request`
  - `GET /logs/repo-requests`

### Repo request processing block
- Added repo request processor (`dev_pipeline/repo_manager.py`) to handle pending requests.
- Added manual runner script:
  - `scripts/process_repo_requests.py`
- Added API trigger endpoint:
  - `POST /runs/process-repo-requests`
- Added UI control button: `Process repo prep`.
- Added recurring cron job `dev-pipeline-repo-request-processor` (every 30 minutes).

### Publish-request model alignment
- Local git initialization is now treated as default/automatic in active-project sweeps.
- Added explicit GitHub publish request flow:
  - `POST /projects/{id}/publish-request`
  - `GET /logs/publish-requests`
  - `POST /runs/process-publish-requests` (legacy/manual fallback)
- Added modules/scripts:
  - `dev_pipeline/publish_requests.py`
  - `dev_pipeline/publish_manager.py`
  - `scripts/process_publish_requests.py`
- UI now shows `Request GitHub Publish` for projects without `repo_url`.
- Switched publish behavior to immediate case-by-case execution from UI/API click; removed recurring publish-request cron.

### Registry hygiene / secret-safe publishing
- Converted tracked registry files to example-only content.
- Added gitignored local runtime registry: `registry/projects.local.yaml`.
- Registry loader now prefers local registry file when present.
- Goal: avoid publishing real project inventories/runtime state to GitHub.

### Concurrency guardrails (manual vs automatic development)
- Added project lock module: `dev_pipeline/locks.py`.
- Added API endpoints:
  - `POST /projects/{id}/lock-start`
  - `POST /projects/{id}/lock-stop`
  - (`focus-*` kept as backward-compatible aliases)
- Added Web UI lock toggle control per project (single `Lock`/`Unlock` button).
- Sweeper now skips projects under active manual lock and acquires a short auto lock while processing active projects to avoid overlap.

### Automation schedules
- Scheduled automation jobs:
  - `dev-pipeline-sweep` every 30m
  - `dev-pipeline-milestone-notify` every 15m
  - `dev-pipeline-newsletter-section` daily at 08:45 America/Los_Angeles
