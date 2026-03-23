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
- Scheduled automation jobs:
  - `dev-pipeline-sweep` every 30m
  - `dev-pipeline-milestone-notify` every 15m
  - `dev-pipeline-newsletter-section` daily at 08:45 America/Los_Angeles
