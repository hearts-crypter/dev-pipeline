#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dev_pipeline.autodev import run_autodev_tick


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--project-id', required=True)
    ap.add_argument('--repo-path', required=True)
    args = ap.parse_args()

    res = run_autodev_tick(args.project_id, args.repo_path)
    print(json.dumps({'changed': res.changed, 'summary': res.summary}))
