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
- Canonical registry file in `registry/projects.yaml`
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
  - `GET /logs/runs`
  - `GET /logs/status-audit`
  - `GET /logs/notifications`
- Built-in Web UI served from `/` (files in `webui/`) for status viewing/updates and run controls.

## Quick start
```bash
cd projects/dev-pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/run_sweep.py
bash scripts/run_api.sh
```
