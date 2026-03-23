# Implementation Plan — Autonomous Project Development Pipeline

## 1) Canonical project registry
Create a single source of truth file:
- `projects/dev-pipeline/registry/projects.yaml`

Each project record:
- `id`
- `name`
- `repo_path`
- `status` (`active|paused|stopped|finished|blocked`)
- `priority` (`low|medium|high`)
- `spec_doc` (path)
- `roadmap_doc` (path)
- `next_milestone`
- `last_progress_at`
- `owner_notify_email` (default `dev@ahjc.me`)
- `repo_url` (optional; used by Web UI quick-link button)
- `notes`

## 2) Status change contract
You can instruct status changes in chat/email/web UI, e.g.:
- "set project paper-digest status paused"
- "set project paper-digest status active"

Behavior:
- validate project exists
- update registry
- append audit log entry
- reflect in Web UI immediately

## 3) Recurring automation jobs

### A. Project sweep cron (every 30 min)
Purpose: inspect all projects and schedule/perform work only for `active` projects.

Loop behavior:
1. Load registry
2. For each project:
   - skip if status != `active`
   - inspect repo state (git status, pending tasks, roadmap)
   - select next development task
   - execute bounded implementation chunk
   - update docs + commit
3. Record run summary

### B. Milestone notifier cron (every 15 min)
Purpose: detect milestone/spec completion and send email summary.

Trigger conditions:
- milestone checklist fully complete
- spec acceptance checklist complete
- significant unblock/architecture completion

Action:
- send email to `owner_notify_email`
- include changed files, commits, test result, next milestone
- write delivery log

### C. Newsletter enricher hook (daily, before newsletter)
Purpose: inject project section into newsletter data source.

Output section:
- Active projects snapshot
- Milestones reached since last newsletter
- Blockers requiring user input

## 4) Web UI
Build `projects/dev-pipeline/webui` with pages:
1. **Projects List**
   - name, status badge, priority, last progress, next milestone
2. **Project Detail**
   - spec progress, milestone checklist, recent commits, run logs
3. **Controls**
   - change status flag
   - trigger run now
   - set notification target email

Backend API (FastAPI):
- `GET /projects`
- `GET /projects/{id}`
- `PATCH /projects/{id}/status`
- `POST /projects/{id}/run`
- `GET /runs`
- `GET /notifications`

## 5) Email integration
Inbound:
- parse project control commands from approved sender

Outbound:
- milestone/spec emails
- concise + verifiable format

Email template sections:
- Project + milestone achieved
- What changed (commits/files)
- Validation/tests
- Remaining roadmap
- Link to Web UI project detail page

## 6) Governance and safety
- Autonomy applies only to projects with status `active`.
- `paused/stopped/finished` are hard gates.
- External/destructive actions still require explicit confirmation policy.
- Secrets never written to logs/KB/docs.

## 7) Rollout phases

### Phase 1 (this week)
- registry format + parser
- status update command handlers
- project sweep cron skeleton
- run log store

### Phase 2
- autonomous task selection from roadmap/spec
- commit discipline automation (message + run log)
- milestone detection rules

### Phase 3
- outbound milestone email sender + retry log
- newsletter project section integration

### Phase 4
- web UI for list/detail/status controls
- production hardening + observability

## 8) Definition of done
- Registry-backed status lifecycle works.
- Active projects continue progressing without user nudges.
- Milestone/spec completion auto-emails are reliable.
- Web UI shows live status and history.
- Newsletter includes relevant project details section.
