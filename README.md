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
Planning and scaffolding.
