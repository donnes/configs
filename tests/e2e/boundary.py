"""Test double for the external commands the CLI runs: package managers, service
managers, downloads and REA's npx. The harness installs one wrapper per command
name that runs `boundary.py STATE NAME ARGS...`.

Each double keeps the machine state the real tool would keep (installed
packages, loaded agents, enabled timers) in the JSON STATE file, and rejects the
calls the real tool would reject or that would change more than asked, such as
reinstalling an installed package, which upgrades it. Any invocation it does not
model fails with status 97 and is recorded under "unexpected", which the
harness reports, so a new command can never pass silently.
"""
import json
import os
import plistlib
import sys
from pathlib import Path

state_file, name, args = Path(sys.argv[1]), sys.argv[2], sys.argv[3:]
state = json.loads(state_file.read_text())
home = Path(os.environ['HOME'])


def save():
    state_file.write_text(json.dumps(state, indent=2))


def done(code=0, out='', err=''):
    save()
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    sys.exit(code)


def unexpected():
    state['unexpected'].append([name, *args])
    done(97, err=f'boundary double: unexpected call: {name} {" ".join(args)}')


# Omarchy's installers and the packages they install.
INSTALLERS = {
    'omarchy-install-gaming-steam': ['steam'],
    'omarchy-install-service-tailscale': ['tailscale'],
    'omarchy-install-editor-zed': ['zed', 'omazed'],
    'omarchy-install-browser zen': ['zen-browser-bin'],
}

OPENCODE_INSTALLER = '''
case " $* " in *" --no-modify-path "*) ;; *)
  for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do printf '\\nexport PATH="$HOME/.opencode/bin:$PATH"\\n' >> "$rc"; done ;;
esac
mkdir -p "$HOME/.opencode/bin"
printf '#!/bin/sh\\necho opencode v2.0.26\\n' > "$HOME/.opencode/bin/opencode"
chmod 755 "$HOME/.opencode/bin/opencode"
'''


def brew():
    store = state['brew']
    if args == ['--prefix']:
        done(out='/opt/homebrew')
    if len(args) == 3 and args[0] == 'list' and args[1] in ('--formula', '--cask') and args[2] == '-1':
        done(out='\n'.join(store['casks' if args[1] == '--cask' else 'formulae']))
    if args[:2] == ['trust', '--tap'] and len(args) == 3:
        store['taps'].append(args[2])
        done()
    if args[:1] == ['install'] and args[1:2] in (['--formula'], ['--cask']) and args[2:]:
        kind = 'casks' if args[1] == '--cask' else 'formulae'
        for package in args[2:]:
            tap = package.rsplit('/', 1)[0] if package.count('/') == 2 else None
            if tap and tap not in store['taps']:
                done(1, err=f'Error: {tap} is not trusted; run brew trust --tap {tap}')
            if package.split('/')[-1] in store[kind]:
                done(1, err=f'Error: {package} is already installed; installing it again upgrades it')
        store[kind] += [package.split('/')[-1] for package in args[2:]]
        done()
    unexpected()


def curl():
    if args == ['-fsSL', 'https://opencode.ai/v2/install']:
        done(out=OPENCODE_INSTALLER)
    unexpected()


def gh():
    extensions = state['gh']['extensions']
    if args == ['extension', 'list']:
        done(out='\n'.join(f'gh {repo.split("/")[1]}\t{repo}\tv1.0.0' for repo in extensions))
    if args[:2] == ['extension', 'install'] and len(args) == 3:
        if args[2] in extensions:
            done(1, err=f'there is already an installed extension that provides the "{args[2]}" command')
        extensions.append(args[2])
        done()
    unexpected()


def packages():
    store = state['pacman']
    installed = store['installed']
    if name == 'pacman' and args[:1] == ['-T']:
        if store['broken']:
            done(1, err='error: failed to initialize alpm library')
        missing = [package for package in args[1:] if package not in installed]
        done(127 if missing else 0, out='\n'.join(missing))
    if name == 'omarchy-pkg-present' and args:
        done(0 if set(args) <= set(installed) else 1)
    if name == 'omarchy-pkg-add' and args:
        aur = [package for package in args if package in store['aur']]
        if aur:
            done(1, err=f'error: target not found: {" ".join(aur)}')
        installed += [package for package in args if package not in installed]
        done()
    if name == 'omarchy-pkg-aur-add' and args:
        installed += [package for package in args if package not in installed]
        done()
    if name == 'yay' and args[:2] == ['-S', '--needed'] and args[2:]:
        if not sys.stdin.isatty():
            done(1, err='yay: confirmation needs a terminal')
        installed += [package for package in args[2:] if package not in installed]
        done()
    installer = INSTALLERS.get(' '.join([name, *args]))
    if installer is not None:
        # The installers reopen apps and restart logins even when nothing is missing.
        if set(installer) <= set(installed):
            done(1, err=f'{name}: already installed; rerunning would reopen it')
        installed += [package for package in installer if package not in installed]
        done()
    unexpected()


def systemctl():
    store = state['systemd']
    units = home / '.config/systemd/user'
    if args[:1] != ['--user']:
        unexpected()
    command = args[1:]
    if command == ['daemon-reload']:
        store['loaded'] = sorted(path.name for path in units.glob('*') if path.exists())
        done()
    if command[:2] in (['enable', '--now'], ['disable', '--now']) and len(command) == 3:
        unit = command[2]
        if command[0] == 'enable':
            if not (units / unit).exists():
                done(1, err=f'Failed to enable unit: Unit file {unit} does not exist.')
            store['loaded'] = sorted({*store['loaded'], unit})
            store['active'] = sorted({*store['active'], unit})
        else:
            store['active'] = [active for active in store['active'] if active != unit]
        done()
    if command[:2] == ['is-active', '--quiet'] and len(command) == 3:
        done(0 if command[2] in store['active'] else 3)
    if command[:1] == ['show'] and len(command) > 1:
        result = store['results'].get(command[1])
        done(0, out='\n'.join(f'{key}={value}' for key, value in (result or {}).items()))
    unexpected()


def launchctl():
    store = state['launchd']
    domain = f'gui/{os.getuid()}'
    if args[:1] == ['bootout'] and len(args) == 2 and args[1].startswith(domain + '/'):
        label = args[1][len(domain) + 1:]
        done(0 if store['loaded'].pop(label, None) else 3)
    if args[:1] == ['bootstrap'] and len(args) == 3 and args[1] == domain:
        try:
            label = plistlib.loads(Path(args[2]).read_bytes())['Label']
        except Exception as error:
            done(5, err=f'Bootstrap failed: 5: Input/output error ({error})')
        if label in store['loaded']:
            done(5, err='Bootstrap failed: 5: Input/output error (service already loaded)')
        store['loaded'][label] = args[2]
        done()
    if args[:1] == ['print'] and len(args) == 2 and args[1].startswith(domain + '/'):
        label = args[1][len(domain) + 1:]
        if label not in store['loaded']:
            done(113, err=f'Could not find service "{label}" in domain for user gui: {os.getuid()}')
        exit_code = store['exits'].get(label)
        done(out=f'\tlast exit code = {"(never exited)" if exit_code is None else exit_code}')
    if args[:1] == ['getenv'] and len(args) == 2:
        done(out=store['env'].get(args[1], ''))
    if args[:1] == ['setenv'] and len(args) == 3:
        store['env'][args[1]] = args[2]
        done()
    unexpected()


def mise():
    store = state['mise']
    if args == ['--version']:
        done(out='2026.10.0 macos-arm64')
    if args == ['ls', '--current', '--json']:
        done(out=json.dumps(store['ls']))
    if args == ['doctor']:
        done(store['doctor'])
    if args[:2] == ['settings', 'get'] and len(args) == 3:
        done(out=json.dumps(store['settings'].get(args[2], [])))
    if args[:2] == ['settings', 'add'] and len(args) == 4:
        store['settings'].setdefault(args[2], []).append(args[3])
        done()
    if args == ['prune', '--yes']:
        store['pruned'] += 1
        done()
    unexpected()


def npx():
    store = state['npx']
    if store['status'] is None:
        unexpected()
    store['calls'].append(args)
    done(store['status'])


def vp():
    # Vite+'s shims: managed runs Vite+'s runtimes, system_first hands off to PATH.
    store = state['vp']
    if args[:2] == ['env', 'current'] and len(args) == 4 and args[3] == '--json':
        key = 'node' if args[2] == 'node' else 'package_manager'
        done(out=json.dumps({key: {'mode': store['mode']}}))
    if args[:2] == ['env', 'which'] and len(args) == 3:
        directory = '.vite-plus/js_runtime/node/1/bin' if store['mode'] == 'managed' else '.local/share/mise/shims'
        done(out=str(home / directory / args[2]))
    if args in (['env', 'on'], ['env', 'off']):
        store['mode'] = 'managed' if args[1] == 'on' else 'system_first'
        done()
    unexpected()


handlers = {'brew': brew, 'curl': curl, 'gh': gh, 'systemctl': systemctl, 'launchctl': launchctl,
            'mise': mise, 'npx': npx, 'vp': vp}
handlers.get(name, packages)()
