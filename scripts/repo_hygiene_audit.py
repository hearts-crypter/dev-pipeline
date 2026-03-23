#!/usr/bin/env python3
"""Quick hygiene audit: flag tracked runtime-like files likely unsuitable for GitHub repos."""

import subprocess
from pathlib import Path

ROOT = Path('/home/ahjc/.openclaw/workspace/projects')
PATTERNS = ('.db', '.sqlite', '.jsonl', '/logs/', '.env')


def tracked(repo: Path):
    out = subprocess.check_output(['git', '-C', str(repo), 'ls-files'], text=True)
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


if __name__ == '__main__':
    for repo in sorted(ROOT.iterdir()):
        if not (repo / '.git').exists():
            continue
        try:
            files = tracked(repo)
        except Exception:
            continue
        hits = [f for f in files if any(p in f for p in PATTERNS)]
        if hits:
            print(f"\n[{repo.name}] potential hygiene flags:")
            for h in hits:
                print(' -', h)
