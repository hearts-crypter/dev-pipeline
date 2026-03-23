# Development Pipeline

Long-term autonomous development pipeline for managed projects.

## Objective
- Maintain a canonical project registry with status flags.
- Run recurring checks to progress active projects without manual prompting.
- Emit milestone/spec-completion notifications via email.
- Expose project list, statuses, and progress in a Web UI.
- Include project progress section in daily newsletter output.

## Status flags
- `active` — agent should continue development autonomously
- `paused` — no development until resumed
- `stopped` — archived/abandoned; no further action
- `finished` — completed to spec
- `blocked` — active intent but externally blocked

## Current phase
Phase 1 implementation in progress.

## Phase 1 implemented pieces
- Canonical registry template in `registry/projects.yaml`
- Local runtime registry in `registry/projects.local.yaml` (gitignored; preferred when present)
- Registry read/write + status-change audit logger
- Sweep runner (`scripts/run_sweep.py`) that inspects active projects and logs runs
- Milestone notifier (`scripts/milestone_notify.py`) that sends email on newly completed roadmap phases
- Newsletter section renderer (`scripts/render_newsletter_section.py`) for project status injection
- FastAPI service (`dev_pipeline/api.py`) with:
  - `GET /projects`
  - `GET /projects/{id}`
  - `PATCH /projects/{id}/status`
  - `POST /runs/sweep`
  - `POST /runs/milestones-notify`
  - `GET /projects/{id}/timeline`
  - `POST /projects/{id}/email-test`
  - `POST /projects/{id}/repo-request` (legacy/local prep)
  - `POST /projects/{id}/publish-request` (request GitHub publication)
  - `POST /projects/{id}/lock-start`
  - `POST /projects/{id}/lock-stop`
  - `POST /runs/process-repo-requests`
  - `POST /runs/process-publish-requests`
  - `GET /logs/runs`
  - `GET /logs/status-audit`
  - `GET /logs/notifications`
  - `GET /logs/repo-requests`
  - `GET /logs/publish-requests`
- Built-in Web UI served from `/` (files in `webui/`) for status viewing/updates and run controls.
- Concurrency safety via per-project locks (manual immediate work preempts auto sweeps).
- Project records support optional `repo_url` for GitHub/open-repo quick links.
- Local git repo initialization is automatic during active-project sweeps.
- GitHub publication is request-driven and processed immediately on button click (`publish-request` endpoint), not via recurring cron.

## Quick start
```bash
cd projects/dev-pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/run_sweep.py
bash scripts/run_api.sh
```
