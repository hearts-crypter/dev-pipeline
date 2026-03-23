#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
uvicorn dev_pipeline.api:app --host 0.0.0.0 --port 20001 --reload
