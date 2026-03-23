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
- Next: integrate cron jobs + milestone detection + email notifier.
