#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dev_pipeline.repo_manager import process_repo_requests


if __name__ == '__main__':
    print(json.dumps(process_repo_requests(), indent=2))
