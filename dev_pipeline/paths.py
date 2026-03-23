from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "registry" / "projects.yaml"
LOG_DIR = ROOT / "logs"
RUN_LOG_PATH = LOG_DIR / "runs.jsonl"
AUDIT_LOG_PATH = LOG_DIR / "status_audit.jsonl"
NOTIFY_LOG_PATH = LOG_DIR / "notifications.jsonl"
REPO_REQUEST_LOG_PATH = LOG_DIR / "repo_requests.jsonl"
PUBLISH_REQUEST_LOG_PATH = LOG_DIR / "publish_requests.jsonl"
