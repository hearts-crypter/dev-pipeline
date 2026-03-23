from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "registry" / "projects.yaml"
LOG_DIR = ROOT / "logs"
RUN_LOG_PATH = LOG_DIR / "runs.jsonl"
AUDIT_LOG_PATH = LOG_DIR / "status_audit.jsonl"
