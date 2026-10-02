#!/usr/bin/env python3
"""Delete tracked skills, their managed links, and lockfile entries."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('names', nargs='*')
    args = parser.parse_args()
    repo = args.repo.resolve()
    home = Path.home()
    lock_paths = [repo / 'shared/skills.lock.json', home / '.agents/.skill-lock.json']
    if os.environ.get('XDG_STATE_HOME'):
        lock_paths.append(Path(os.environ['XDG_STATE_HOME']) / 'skills/.skill-lock.json')
    locks = {}
    for path in lock_paths:
        if path.exists():
            target = path.resolve()
            if target in locks:
                continue
            data = json.loads(path.read_text())
            if not isinstance(data, dict) or not isinstance(data.get('skills'), dict):
                raise ValueError(f'{path}: invalid skills lockfile')
            locks[target] = data
    names = list(dict.fromkeys(args.names))
    interactive = not names
    if interactive:
        if not sys.stdin.isatty():
            raise ValueError('interactive removal requires a terminal; pass skill names instead')
        available = {path.name for path in (repo / 'shared/skills').glob('*')
                     if (path / 'SKILL.md').is_file() and not path.is_symlink()}
        for data in locks.values():
            available.update(data['skills'])
        choices = sorted(available)
        if not choices:
            print('No tracked skills to remove.')
            return
        print('Tracked skills:')
        for index, name in enumerate(choices, 1):
            print(f'  {index:2}. {name}')
        while True:
            reply = input('Select numbers separated by spaces or commas, or Enter to cancel: ').strip()
            if not reply:
                print('Removal cancelled.')
                return
            tokens = reply.replace(',', ' ').split()
            if tokens and all(token.isascii() and token.isdigit() and
                              1 <= int(token) <= len(choices) for token in tokens):
                names = list(dict.fromkeys(choices[int(token) - 1] for token in tokens))
                break
            print('Choose numbers from the list.')
    directories, links = [], set()
    for name in names:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name):
            raise ValueError(f'invalid skill name: {name}')
        skill = repo / 'shared/skills' / name
        if skill.is_symlink():
            raise ValueError(f'{skill}: refusing to delete a symlinked repo skill')
        if skill.exists() and (not skill.is_dir() or not (skill / 'SKILL.md').is_file()):
            raise ValueError(f'{skill}: not a skill directory')
        if not skill.exists() and not any(name in data['skills'] for data in locks.values()):
            raise ValueError(f'unknown tracked skill: {name}')
        if skill.exists():
            directories.append(skill)
        candidates = set(home.glob(f'.*/skills/{name}'))
        candidates.update(home.glob(f'.config/*/skills/{name}'))
        candidates.update([home / '.agents/skills' / name, home / '.claude/skills' / name])
        for path in candidates:
            if path.is_symlink() and path.resolve() == skill:
                links.add(path)
            elif path.exists() and path in (home / '.agents/skills' / name, home / '.claude/skills' / name):
                raise ValueError(f'{path}: unmanaged copy or link; sync it before removal')
    # Preflight every name and lockfile before changing anything. Never follow
    # directory symlinks when deleting the tracked skill or agent links.
    for path in sorted(links):
        print(f'[unlink ] {path}')
    for path in directories:
        print(f'[delete ] {path}')
    changed = {}
    for path, data in locks.items():
        removed = [name for name in names if name in data['skills']]
        if removed:
            print(f'[lock   ] {path}: remove {", ".join(removed)}')
            for name in removed:
                del data['skills'][name]
            changed[path] = data
    if args.dry_run:
        return
    if interactive and input(f'Delete {", ".join(names)} from the repo and agents? [y/N] ').strip().lower() not in ('y', 'yes'):
        print('Removal cancelled.')
        return
    for path in links:
        path.unlink()
    for path in directories:
        shutil.rmtree(path)
    for path, data in changed.items():
        path.write_text(json.dumps(data, indent=2) + '\n')


if __name__ == '__main__':
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print('\nRemoval cancelled.')
    except (OSError, ValueError) as error:
        print(f'error: {error}', file=sys.stderr)
        sys.exit(1)
