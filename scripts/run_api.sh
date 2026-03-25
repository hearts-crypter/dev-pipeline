#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -x ".venv/bin/uvicorn" ]; then
  exec .venv/bin/uvicorn dev_pipeline.api:app --host 0.0.0.0 --port 20001 --reload
fi

if command -v uvicorn >/dev/null 2>&1; then
  exec uvicorn dev_pipeline.api:app --host 0.0.0.0 --port 20001 --reload
fi

exec python3 -m uvicorn dev_pipeline.api:app --host 0.0.0.0 --port 20001 --reload
