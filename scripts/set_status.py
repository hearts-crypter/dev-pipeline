#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dev_pipeline.registry import set_project_status


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project_id")
    ap.add_argument("status")
    ap.add_argument("--source", default="cli")
    ap.add_argument("--note", default=None)
    args = ap.parse_args()

    updated = set_project_status(args.project_id, args.status, source=args.source, note=args.note)
    print(json.dumps(updated.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
