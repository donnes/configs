#!/usr/bin/env python3
"""Merge a detached skills CLI lockfile into the tracked lockfile."""
import json
from pathlib import Path
import sys


def read_lock(path):
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or not isinstance(data.get('skills'), dict):
        raise ValueError(f'{path}: expected a lockfile with a skills object')
    return data


def main():
    repo_path, local_path = map(Path, sys.argv[1:3])
    repo, local = read_lock(repo_path), read_lock(local_path)
    if repo.get('version') != local.get('version'):
        raise ValueError('lockfile versions differ; migrate them before syncing')
    merged = dict(repo)
    for key, value in local.items():
        if isinstance(value, dict) and isinstance(repo.get(key), dict):
            merged[key] = {**repo[key], **value}
        else:
            merged[key] = value
    if '--dry-run' not in sys.argv[3:] and merged != repo:
        # Write through the repo path so any existing links remain valid.
        repo_path.write_text(json.dumps(merged, indent=2) + '\n')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        print(f'error: {error}', file=sys.stderr)
        sys.exit(1)
