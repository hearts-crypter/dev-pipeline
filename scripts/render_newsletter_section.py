#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dev_pipeline.newsletter import write_project_section


if __name__ == '__main__':
    out = Path('/home/ahjc/.openclaw/workspace/.openclaw/state/project_pipeline_section.txt')
    write_project_section(out)
    print(str(out))
