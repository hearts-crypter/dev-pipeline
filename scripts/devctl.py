#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

import urllib.request

BASE = 'http://127.0.0.1:20001'


def req(path: str, method='GET', payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['content-type'] = 'application/json'
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read().decode())


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Dev pipeline control helper')
    sp = ap.add_subparsers(dest='cmd', required=True)

    sp.add_parser('projects')
    sp.add_parser('sweep')

    p_lock = sp.add_parser('lock')
    p_lock.add_argument('project_id')
    p_lock.add_argument('--minutes', type=int, default=120)

    p_unlock = sp.add_parser('unlock')
    p_unlock.add_argument('project_id')

    p_pub = sp.add_parser('publish')
    p_pub.add_argument('project_id')

    args = ap.parse_args()

    if args.cmd == 'projects':
        out = req('/projects')
    elif args.cmd == 'sweep':
        out = req('/runs/sweep', method='POST')
    elif args.cmd == 'lock':
        out = req(f"/projects/{args.project_id}/lock-start", method='POST', payload={'owner': 'devctl', 'ttl_minutes': args.minutes})
    elif args.cmd == 'unlock':
        out = req(f"/projects/{args.project_id}/lock-stop", method='POST', payload={'owner': 'devctl', 'force': True})
    elif args.cmd == 'publish':
        out = req(f"/projects/{args.project_id}/publish-request", method='POST', payload={'source': 'devctl'})
    else:
        raise SystemExit(2)

    print(json.dumps(out, indent=2))
