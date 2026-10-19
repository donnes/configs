import os
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import unittest

from cli_fixture import ROOT, copy_cli, interactive_cli


class CliInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name).resolve() / 'repo'
        self.home = self.repo.parent / 'home'
        self.repo.mkdir()
        self.home.mkdir()
        copy_cli(self.repo)
        self.env = dict(os.environ, HOME=str(self.home), DONNES_CONFIGS_PROFILE='macos')
        self.env.pop('XDG_STATE_HOME', None)
        self.env.pop('CODEX_HOME', None)
        self.env.pop('CLAUDE_CONFIG_DIR', None)
        # VP_HOME would point the CLI at the real Vite+ install.
        for name in ['MISE_DATA_DIR', 'XDG_DATA_HOME', 'XDG_CONFIG_HOME', 'BUN_INSTALL', 'PNPM_HOME', 'VP_HOME']:
            self.env.pop(name, None)
        # Default selections reach launchd and systemd; never touch the real ones.
        fake_bin = self.repo.parent / 'fake-bin'
        fake_bin.mkdir()
        self.log = self.repo.parent / 'commands.jsonl'
        # FAKE_PRESENT lists installed Omarchy packages, FAKE_GH_EXTENSIONS installed
        # gh extensions as owner/repo; FAKE_MISE_SETTING is what
        # `mise settings get` prints. The other FAKE_ variables describe the state
        # that `./cli health` queries; FAKE_SYSTEMD_SHOW separates lines with ";".
        for command in ['brew', 'curl', 'gh', 'yay', 'pacman', 'systemctl', 'launchctl', 'mise', 'omarchy-pkg-present', 'omarchy-pkg-add',
                        'omarchy-pkg-aur-add', 'omarchy-install-gaming-steam', 'omarchy-install-browser']:
            executable = fake_bin / command
            executable.write_text('#!/usr/bin/env python3\nimport json, os, sys\n'
                                  'from pathlib import Path\n'
                                  'name, args = Path(sys.argv[0]).name, sys.argv[1:]\n'
                                  'env = lambda key: os.environ.get(key, "")\n'
                                  'if name == "omarchy-pkg-present":\n'
                                  '    sys.exit(0 if set(args) <= set(env("FAKE_PRESENT").split()) else 1)\n'
                                  'if name == "pacman" and args[:1] == ["-T"]:\n'
                                  '    if env("FAKE_PACMAN_BROKEN"): sys.exit(1)\n'
                                  '    missing = [arg for arg in args[1:] if arg not in env("FAKE_PRESENT").split()]\n'
                                  '    print("\\n".join(missing))\n'
                                  '    sys.exit(127 if missing else 0)\n'
                                  'if name == "gh" and args[:2] == ["extension", "list"]:\n'
                                  '    print("\\n".join(f"gh {repo.split(\'/\')[1]}\\t{repo}\\tv1.0.0" for repo in env("FAKE_GH_EXTENSIONS").split()))\n'
                                  '    sys.exit()\n'
                                  'if name == "brew" and args[:1] == ["list"]:\n'
                                  '    print("\\n".join(env("FAKE_CASKS" if "--cask" in args else "FAKE_FORMULAE").split()))\n'
                                  '    sys.exit()\n'
                                  'if name == "mise" and args[:1] in (["ls"], ["doctor"], ["--version"]):\n'
                                  '    print(env("FAKE_MISE_LS") or "{}" if args[0] == "ls" else "")\n'
                                  '    sys.exit(int(env("FAKE_MISE_DOCTOR") or 0) if args[0] == "doctor" else 0)\n'
                                  'if name == "launchctl" and args[:1] in (["print"], ["getenv"]):\n'
                                  '    print(env("FAKE_GUI_PATH" if args[0] == "getenv" else "FAKE_LAUNCHD_PRINT"))\n'
                                  '    sys.exit(0 if args[0] == "getenv" or args[1].split("/")[-1] in env("FAKE_LOADED").split() else 113)\n'
                                  'if name == "systemctl" and "is-active" in args:\n'
                                  '    sys.exit(0 if args[-1] in env("FAKE_LOADED").split() else 3)\n'
                                  'if name == "systemctl" and "show" in args:\n'
                                  '    print(env("FAKE_SYSTEMD_SHOW").replace(";", "\\n"))\n'
                                  '    sys.exit()\n'
                                  'if name == "curl" and args[-1].startswith("https://opencode.ai/"):\n'
                                  '    print(\'echo "$@" > "$HOME/opencode-installer-args"\')\n'
                                  'if name == "mise" and args[:2] == ["settings", "get"]:\n'
                                  '    print(os.environ.get("FAKE_MISE_SETTING", ""))\n'
                                  '    sys.exit()\n'
                                  'with open(os.environ["COMMAND_LOG"], "a") as log:\n'
                                  '    log.write(json.dumps([name, args, '
                                  'sys.stdin.read() if name == "yay" else ""]) + "\\n")\n')
            executable.chmod(0o755)
        # Vite+'s managed node shim puts its own runtime first on its children's
        # PATH, which would hide the fakes.
        vite = os.path.join(os.environ.get('VP_HOME') or os.path.expanduser('~/.vite-plus'), 'bin')
        path = os.pathsep.join(entry for entry in self.env['PATH'].split(os.pathsep) if entry != vite)
        self.env.update(PATH=str(fake_bin) + os.pathsep + path, COMMAND_LOG=str(self.log))
        self.write('macos/agents/CONTEXT.md', 'MAC_CONTEXT')
        self.write('linux/agents/CONTEXT.md', 'LINUX_CONTEXT')

    def write(self, relative, content, home=False):
        file = (self.home if home else self.repo) / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content)
        return file

    def opencode(self, version):
        binary = self.write('.opencode/bin/opencode', f'#!/bin/sh\necho opencode v{version}\n', home=True)
        binary.chmod(0o755)
        return binary

    def run_cli(self, *args):
        result = subprocess.run(['bash', str(self.repo / 'cli'), *args], env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_rea_requires_explicit_apply_and_reports_setup_failure(self):
        runner = self.repo.parent / 'fake-bin/npx'
        runner.write_text('#!/bin/sh\necho rea-called >> "$COMMAND_LOG"\nexit 7\n')
        runner.chmod(0o755)
        for profile in ['macos', 'omarchy']:
            with self.subTest(profile=profile):
                self.env['DONNES_CONFIGS_PROFILE'] = profile
                self.run_cli('--only', 'rea', '--dry-run')
                self.run_cli('uninstall', '--only', 'rea')
                self.run_cli('--skip', 'packages,gh-extensions,apps,agents,skills,mise,atuin,nvim,gradle,shell,tmux,git,session')
                self.assertFalse(self.log.exists())
                result = subprocess.run(['bash', str(self.repo / 'cli'), '--only', 'rea'],
                                        env=self.env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('npx failed (7)', result.stderr)
                self.assertEqual(self.log.read_text(), 'rea-called\n')
                self.log.unlink()

    def test_install_and_uninstall_preserve_foreign_files(self):
        source = self.write('shared/agents/global/AGENTS.md', 'instructions')
        custom = self.home / '.codex-purpose'
        self.env['CODEX_HOME'] = str(custom)
        skill = self.write('shared/skills/example/SKILL.md', 'example').parent
        self.write('shared/skills.lock.json', '{"version":3,"skills":{}}')
        foreign = self.write('.agents/skills/foreign/SKILL.md', 'foreign', home=True)
        self.run_cli('--only', 'agents,skills', '--dry-run')
        self.assertFalse((custom / 'AGENTS.md').exists())
        self.run_cli('--only', 'agents,skills')
        self.assertIn(source.read_text(), (custom / 'AGENTS.md').read_text())
        self.assertIn('MAC_CONTEXT', (custom / 'AGENTS.md').read_text())
        self.assertEqual((self.home / '.claude/CLAUDE.md').resolve(), (custom / 'AGENTS.md').resolve())
        self.assertEqual((self.home / '.agents/skills/example').resolve(), skill)
        self.run_cli('uninstall', '--only', 'agents,skills')
        self.assertFalse((custom / 'AGENTS.md').is_symlink())
        self.assertFalse((self.home / '.agents/skills/example').is_symlink())
        self.assertFalse((self.home / '.claude/skills/example').is_symlink())
        self.assertEqual(foreign.read_text(), 'foreign')
        self.assertEqual((skill / 'SKILL.md').read_text(), 'example')

    def test_unattended_install_keeps_conflicts_through_linked_skills(self):
        source = self.write('shared/skills/example/SKILL.md', 'repository')
        self.write('shared/skills.lock.json', '{"version":3,"skills":{}}')
        local = self.write('.agents/skills/example/SKILL.md', 'local', home=True)
        link = self.home / '.claude/skills/example'
        link.parent.mkdir(parents=True)
        link.symlink_to(local.parent, target_is_directory=True)
        self.run_cli('--only', 'skills')
        self.assertEqual(local.read_text(), 'local')
        self.assertEqual(source.read_text(), 'repository')
        self.assertFalse(local.parent.is_symlink())
        self.assertEqual(link.resolve(), local.parent)

    def test_nvim_profiles_preserve_foreign_tree_and_select_profile_lock(self):
        init = self.write('shared/nvim/init.lua', '-- shared init')
        self.write('shared/nvim/lua/plugins/theme.lua', '-- shared theme')
        macos_lock = self.write('macos/nvim/lazy-lock.json', '{"macos":true}')
        omarchy_lock = self.write('omarchy/nvim/lazy-lock.json', '{"omarchy":true}')
        foreign = self.write('.config/foreign-nvim/user.lua', '-- foreign', home=True)
        destination = self.home / '.config/nvim'
        destination.symlink_to(foreign.parent, target_is_directory=True)
        self.run_cli('--only', 'nvim', '--dry-run')
        self.assertTrue(destination.is_symlink())
        self.run_cli('--only', 'nvim')
        self.assertFalse(destination.is_symlink())
        self.assertEqual((destination / 'init.lua').resolve(), init)
        self.assertEqual((destination / 'lazy-lock.json').resolve(), macos_lock)
        self.assertEqual(foreign.read_text(), '-- foreign')
        user = self.write('.config/nvim/custom.lua', '-- user', home=True)
        self.run_cli('uninstall', '--only', 'nvim')
        self.assertEqual(user.read_text(), '-- user')
        self.env['DONNES_CONFIGS_PROFILE'] = 'omarchy'
        theme = self.write('.local/state/omarchy/current/theme/neovim.lua', '-- active theme', home=True)
        self.run_cli('--only', 'nvim')
        self.assertEqual((destination / 'lazy-lock.json').resolve(), omarchy_lock)
        self.assertEqual((destination / 'lua/plugins/theme.lua').resolve(), theme)
        self.assertEqual(user.read_text(), '-- user')

    def test_gradle_properties_follow_the_profile(self):
        destination = self.home / '.gradle/gradle.properties'
        for profile, abi in [('macos', 'arm64-v8a'), ('omarchy', 'x86_64')]:
            with self.subTest(profile=profile):
                self.env['DONNES_CONFIGS_PROFILE'] = profile
                source = self.write(f'{profile}/gradle.properties', f'reactNativeArchitectures={abi}\n')
                self.run_cli('--only', 'gradle')
                self.assertEqual(destination.resolve(), source)
                self.run_cli('uninstall', '--only', 'gradle')
                self.assertFalse(destination.exists())

    def test_global_gitignore_is_linked_on_both_profiles(self):
        source = self.write('shared/git/ignore', '.scratch/\n')
        self.write('macos/gitconfig', '[pull]\n\trebase = true\n')
        destination = self.home / '.config/git/ignore'
        for profile in ['macos', 'omarchy']:
            with self.subTest(profile=profile):
                self.env['DONNES_CONFIGS_PROFILE'] = profile
                self.run_cli('--only', 'git')
                self.assertEqual(destination.resolve(), source)
                self.assertEqual((self.home / '.gitconfig').exists(), profile == 'macos')
                self.run_cli('uninstall', '--only', 'git')
                self.assertFalse(destination.exists())
                (self.home / '.gitconfig').unlink(missing_ok=True)

    def test_marker_blocks_are_idempotent_and_uninstall_preserves_user_content(self):
        self.write('macos/zshrc', '# zsh')
        self.write('macos/zshenv', '# env')
        self.write('macos/tmux.conf', '# tmux')
        self.write('omarchy/bashrc.local', '# bash')
        self.write('omarchy/tmux.local.conf', '# tmux')
        for profile, shell, tmux in [('macos', '.zshenv', '.tmux.conf'),
                                     ('omarchy', '.bashrc', '.config/tmux/tmux.conf')]:
            with self.subTest(profile=profile):
                self.env['DONNES_CONFIGS_PROFILE'] = profile
                block = self.write(shell, 'export USER_SETTING=1\n', home=True)
                block.chmod(0o640)
                if profile == 'omarchy':
                    tmux_file = self.write(tmux, '# user tmux\n', home=True)
                self.run_cli('--only', 'shell,tmux', '--dry-run')
                self.assertEqual(block.read_text(), 'export USER_SETTING=1\n')
                self.run_cli('--only', 'shell,tmux')
                shell_source = self.repo / ('macos/zshenv' if profile == 'macos' else 'omarchy/bashrc.local')
                self.assertIn(f'source "{shell_source}"', block.read_text())
                self.assertEqual(block.read_text().count('# >>> donnes/configs >>>'), 1)
                self.assertEqual(block.read_text().count('# <<< donnes/configs <<<'), 1)
                if profile == 'omarchy':
                    self.assertIn('source-file -q ~/.config/tmux/local.conf', tmux_file.read_text())
                    self.assertEqual(tmux_file.read_text().count('# >>> donnes/configs >>>'), 1)
                once = block.read_bytes()
                self.run_cli('--only', 'shell,tmux')
                self.assertEqual(block.read_bytes(), once)
                self.assertEqual(block.stat().st_mode & 0o777, 0o640)
                self.run_cli('uninstall', '--only', 'shell,tmux')
                self.assertIn('export USER_SETTING=1', block.read_text())
                self.assertNotIn('donnes/configs', block.read_text())
                if profile == 'omarchy':
                    self.assertIn('# user tmux', tmux_file.read_text())
                    self.assertNotIn('donnes/configs', tmux_file.read_text())

    def test_marker_block_is_replaced_in_place_and_malformed_markers_stop_the_install(self):
        self.write('macos/zshrc', '# zsh')
        start, end = '# >>> donnes/configs >>>', '# <<< donnes/configs <<<'
        # Installers such as Vite+ append their own lines after the block.
        zshenv = self.write('.zshenv', f'export EARLY=1\n\n{start}\nsource "/old/macos/zshenv"\n{end}\n\n'
                            '# Vite+ bin\n. "$HOME/.vite-plus/env"\n', home=True)
        self.run_cli('--only', 'shell')
        self.assertEqual(zshenv.read_text(), f'export EARLY=1\n\n{start}\nsource "{self.repo}/macos/zshenv"\n{end}\n\n'
                         '# Vite+ bin\n. "$HOME/.vite-plus/env"\n')
        self.assertIn('managed block in ~/.zshenv is current', self.run_cli('--only', 'shell', '--dry-run').stdout)
        for malformed in [f'{start}\n{start}\nx\n{end}\n', f'{end}\nx\n{start}\n', f'{start}\nx\n']:
            with self.subTest(malformed=malformed):
                zshenv.write_text(malformed)
                result = subprocess.run(['bash', str(self.repo / 'cli'), '--only', 'shell'],
                                        env=self.env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('~/.zshenv has malformed donnes/configs markers', result.stderr)
                self.assertEqual(zshenv.read_text(), malformed)

    def test_xcode_node_env_repoints_only_exact_installs_and_reports_failures(self):
        data = self.home / 'mise data'
        self.env['MISE_DATA_DIR'] = str(data)
        stale = f'export NODE_BINARY="{data}/installs/node/24.13.1/bin/node"\nexport OTHER=1\n'
        project = self.write('Git/app/ios/.xcode.env.local', stale, home=True)
        project.chmod(0o640)
        custom = self.write('Git/custom/ios/.xcode.env.local', 'export NODE_BINARY=/opt/homebrew/bin/node\n', home=True)
        # Shares the data directory's first word, so only a whole-path prefix keeps it.
        nearby = self.write('Git/nearby/ios/.xcode.env.local', f'export NODE_BINARY="{self.home}/mise/bin/node"\n', home=True)
        vendored = self.write('Git/app/node_modules/dep/ios/.xcode.env.local', stale, home=True)
        def helper(*args):
            return subprocess.run(['sh', str(ROOT / 'macos/bin/xcode-node-env'), *args], env=self.env,
                                  capture_output=True, text=True)
        preview = helper('--dry-run')
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn(f'would update {project}', preview.stdout)
        self.assertEqual(project.read_text(), stale)
        self.assertEqual(helper().returncode, 0)
        self.assertEqual(project.read_text(), f'export NODE_BINARY="{data}/shims/node"\nexport OTHER=1\n')
        self.assertEqual(project.stat().st_mode & 0o777, 0o640)
        self.assertEqual(sorted(path.name for path in project.parent.iterdir()), ['.xcode.env.local'])
        self.assertEqual(custom.read_text(), 'export NODE_BINARY=/opt/homebrew/bin/node\n')
        self.assertEqual(nearby.read_text(), f'export NODE_BINARY="{self.home}/mise/bin/node"\n')
        self.assertEqual(vendored.read_text(), stale)
        # A missing default root is fine; a missing root that was asked for is not.
        missing = helper(str(self.home / 'Gti'))
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn('no such directory', missing.stderr)
        # A project it cannot search may still name a version, so the daily job must not prune.
        locked = self.home / 'Git/locked'
        locked.mkdir()
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o755)
        self.assertNotEqual(helper().returncode, 0)

    def test_install_records_a_receipt_that_distinguishes_partial_runs(self):
        self.write('shared/agents/global/AGENTS.md', 'instructions')
        git = ['git', '-C', str(self.repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.com']
        subprocess.run([*git, 'init', '-q'], check=True)
        subprocess.run([*git, 'add', '-A'], check=True)
        subprocess.run([*git, 'commit', '-qm', 'initial'], check=True)
        head = subprocess.run([*git, 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
        receipt = self.home / '.local/state/donnes-configs/receipt.json'
        self.run_cli('--only', 'agents', '--dry-run')
        self.assertFalse(receipt.exists())
        self.env['FAKE_MISE_LS'] = json.dumps({'node': [{'version': '24.22.0', 'installed': True}]})
        self.run_cli('--only', 'agents')
        data = json.loads(receipt.read_text())
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
        self.assertEqual({key: data['lastRun'][key] for key in ['revision', 'dirty', 'components', 'outcome']},
                         {'revision': head, 'dirty': False, 'components': ['agents'], 'outcome': 'complete'})
        self.assertEqual(data['components']['agents']['revision'], head)
        self.assertEqual(data['runtimeHomes'], {'codex': [str(self.home / '.codex')], 'claude': [str(self.home / '.claude')]})
        self.assertEqual(data['tools'], {'node': '24.22.0'})
        applied = data['components']['agents']

        # A differing local copy is kept unattended, so the run is not complete.
        (self.home / '.codex/AGENTS.md').unlink()
        self.write('.codex/AGENTS.md', 'local edit', home=True)
        self.write('shared/agents/global/AGENTS.md', 'changed instructions')
        self.run_cli('--only', 'agents')
        data = json.loads(receipt.read_text())
        self.assertEqual(data['lastRun']['outcome'], 'kept-conflicts')
        self.assertEqual(data['lastRun']['kept'], ['~/.codex/AGENTS.md'])
        self.assertTrue(data['lastRun']['dirty'])
        self.assertTrue(data['components']['agents']['keptConflicts'])
        applied = data['components']['agents']

        # A failed component keeps its last successful record.
        (self.repo / 'macos/agents/CONTEXT.md').unlink()
        result = subprocess.run(['bash', str(self.repo / 'cli'), '--only', 'agents,skills'], env=self.env,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        data = json.loads(receipt.read_text())
        self.assertEqual({key: data['lastRun'].get(key) for key in ['outcome', 'failed']}, {'outcome': 'failed', 'failed': 'agents'})
        self.assertIn('CONTEXT.md', data['lastRun']['error'])
        self.assertEqual(data['components']['agents'], applied)
        self.assertNotIn('skills', data['components'])

    def test_component_that_fails_late_keeps_its_last_successful_receipt(self):
        self.write('macos/zshrc', '# zsh')
        self.write('shared/git/ignore', '.scratch/\n')
        self.write('macos/gitconfig', '[pull]\n\trebase = true\n')
        git = ['git', '-C', str(self.repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.com']
        subprocess.run([*git, 'init', '-q'], check=True)
        subprocess.run([*git, 'add', '-A'], check=True)
        subprocess.run([*git, 'commit', '-qm', 'initial'], check=True)
        receipt = self.home / '.local/state/donnes-configs/receipt.json'
        self.run_cli('--only', 'shell,git')
        applied = json.loads(receipt.read_text())['components']
        subprocess.run([*git, 'commit', '-qm', 'next', '--allow-empty'], check=True)
        head = subprocess.run([*git, 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
        # ~/.zshrc is linked before shell reaches the malformed ~/.zshenv, and the
        # shared git ignore would come before the macOS gitconfig include.
        (self.home / '.zshrc').unlink()
        (self.home / '.config/git/ignore').unlink()
        (self.home / '.zshenv').write_text('# >>> donnes/configs >>>\nx\n')
        result = subprocess.run(['bash', str(self.repo / 'cli'), '--only', 'shell,git'], env=self.env,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        data = json.loads(receipt.read_text())
        self.assertEqual({key: data['lastRun'].get(key) for key in ['revision', 'outcome', 'failed']},
                         {'revision': head, 'outcome': 'failed', 'failed': 'shell'})
        self.assertEqual({name: data['components'][name] for name in ['shell', 'git']}, applied)

    def test_adopt_and_update_keep_skill_directory_links(self):
        local = self.write('.agents/skills/example/SKILL.md', 'initial', home=True).parent
        (local / 'reference.md').symlink_to('SKILL.md')
        self.run_cli('adopt', str(local), '--dry-run')
        self.assertFalse(local.is_symlink())
        self.run_cli('adopt', str(local))
        tracked = self.repo / 'shared/skills/example'
        self.assertEqual(local.resolve(), tracked)
        self.assertEqual(os.readlink(tracked / 'reference.md'), 'SKILL.md')
        local.unlink()
        shutil.copytree(tracked, local)
        (local / 'SKILL.md').write_text('updated')
        self.run_cli('update', str(local), '--dry-run')
        self.assertEqual((tracked / 'SKILL.md').read_text(), 'initial')
        self.run_cli('update', str(local))
        self.assertEqual((tracked / 'SKILL.md').read_text(), 'updated')
        self.assertTrue(local.is_symlink())

    def test_interactive_component_selection_and_cancellation(self):
        source = self.write('shared/agents/global/AGENTS.md', 'instructions')
        interactive_cli(self.repo, self.env, ['--interactive'], [
            ('Select components to install', '\x03'),
        ], expected_code=130)
        self.assertFalse((self.home / '.codex/AGENTS.md').exists())
        # Select all, clear all, then choose agents, the third component.
        interactive_cli(self.repo, self.env, ['--interactive'], [
            ('Select components to install', 'aa\x1b[B\x1b[B \r'),
        ])
        self.assertIn(source.read_text(), (self.home / '.codex/AGENTS.md').read_text())
        self.assertFalse((self.home / '.agents').exists())

    def test_parent_links_into_repo_preserve_files_and_skills(self):
        source = self.write('shared/atuin/config.toml', 'repository config')
        self.write('shared/atuin/alias.toml', '').unlink()
        alias = source.parent / 'alias.toml'
        alias.symlink_to('config.toml')
        (self.home / '.config').mkdir()
        (self.home / '.config/atuin').symlink_to(source.parent)
        self.run_cli('--only', 'atuin')
        self.assertFalse(source.is_symlink())
        self.assertEqual(source.read_text(), 'repository config')
        self.assertEqual(os.readlink(alias), 'config.toml')
        skill = self.write('shared/skills/example/SKILL.md', 'repository skill')
        self.write('shared/skills.lock.json', '{"version":3,"skills":{}}')
        (self.home / '.agents').mkdir()
        (self.home / '.agents/skills').symlink_to(skill.parent.parent)
        self.run_cli('--only', 'skills')
        self.assertFalse(skill.parent.is_symlink())
        self.assertEqual(skill.read_text(), 'repository skill')

    def test_uncomparable_conflict_keeps_local_and_continues_install(self):
        source = self.write('shared/atuin/config.toml', 'repository')
        later = self.write('shared/atuin/zz.toml', 'later config')
        local = self.write('.config/atuin/config.toml/user.toml', 'local', home=True)
        self.run_cli('--only', 'atuin')
        self.assertEqual(local.read_text(), 'local')
        self.assertEqual(source.read_text(), 'repository')
        self.assertEqual((local.parent.parent / 'zz.toml').resolve(), later)

    def test_update_preserves_tracked_modes_without_writing_through_links(self):
        for linked in [False, True]:
            with self.subTest(linked=linked):
                name = 'linked' if linked else 'tool'
                tracked = self.write(f'macos/bin/{name}', 'tracked')
                tracked.chmod(0o755)
                if linked:
                    original = self.write('macos/bin/original', 'original')
                    original.chmod(0o755)
                    tracked.unlink()
                    tracked.symlink_to('original')
                local = self.write(f'.local/bin/{name}', 'updated', home=True)
                local.chmod(0o600)
                self.run_cli('update', str(local))
                self.assertFalse(tracked.is_symlink())
                self.assertEqual(tracked.read_text(), 'updated')
                self.assertEqual(tracked.stat().st_mode & 0o777, 0o755)
                self.assertEqual(local.resolve(), tracked)
                if linked:
                    self.assertEqual(original.read_text(), 'original')

    def test_prune_with_symlinked_home_preserves_foreign_dangling_links(self):
        alias = self.home.parent / 'home-alias'
        alias.symlink_to(self.home)
        self.env['HOME'] = str(alias)
        self.write('shared/skills.lock.json', '{"version":3,"skills":{}}')
        (self.repo / 'shared/skills').mkdir()
        agent = self.home / '.agents/skills/gone'
        agent.parent.mkdir(parents=True)
        agent.symlink_to(self.repo / 'shared/skills/gone')
        claude = self.home / '.claude/skills/gone'
        claude.parent.mkdir(parents=True)
        claude.symlink_to(alias / '.agents/skills/gone')
        foreign = claude.parent / 'foreign'
        foreign.symlink_to(self.home / 'missing/foreign')
        self.run_cli('--only', 'skills')
        self.assertFalse(agent.is_symlink())
        self.assertFalse(claude.is_symlink())
        self.assertTrue(foreign.is_symlink())

    def test_piped_bootstrap_can_choose_components(self):
        source = self.write('shared/agents/global/AGENTS.md', 'instructions')
        canonical = self.home / '.donnes/configs'
        canonical.parent.mkdir(parents=True)
        self.repo.rename(canonical)
        source = canonical / source.relative_to(self.repo)
        self.repo = canonical
        (canonical / '.git').mkdir()
        interactive_cli(self.repo, self.env, ['--interactive'], [
            ('Select components to install', 'aa\x1b[B\x1b[B \r'),
        ], piped=True)
        self.assertIn(source.read_text(), (self.home / '.codex/AGENTS.md').read_text())
        self.assertFalse((self.home / '.agents').exists())

    def test_agents_compose_matching_context_and_refresh_custom_runtime_homes(self):
        global_file = self.write('shared/agents/global/AGENTS.md', 'SHARED_CONTEXT')
        default_claude = self.write('.claude/CLAUDE.md', 'default remains local', home=True)
        codex = self.home / '.codex-work/AGENTS.md'
        claude = self.home / '.claude-work/CLAUDE.md'
        for file in [codex, claude]:
            file.parent.mkdir()
            file.symlink_to(global_file)
        self.env.update(CODEX_HOME=str(codex.parent), CLAUDE_CONFIG_DIR=str(claude.parent))
        for profile, included, excluded in [('macos', 'MAC_CONTEXT', 'LINUX_CONTEXT'),
                                             ('omarchy', 'LINUX_CONTEXT', 'MAC_CONTEXT')]:
            with self.subTest(profile=profile):
                self.env['DONNES_CONFIGS_PROFILE'] = profile
                before = codex.read_bytes()
                entries = set(self.repo.iterdir())
                self.run_cli('--only', 'agents', '--dry-run')
                self.assertEqual(codex.read_bytes(), before)
                self.assertEqual(set(self.repo.iterdir()), entries)
                self.run_cli('--only', 'agents')
                self.assertEqual(codex.resolve(), claude.resolve())
                self.assertIn('SHARED_CONTEXT', codex.read_text())
                self.assertIn(included, codex.read_text())
                self.assertNotIn(excluded, codex.read_text())
                self.assertIn('COMPUTERS.md', codex.read_text())
                self.assertEqual(default_claude.read_text(), 'default remains local')
                installed = codex.stat().st_mtime_ns
                self.run_cli('--only', 'agents')
                self.assertEqual(codex.stat().st_mtime_ns, installed)
        global_file.write_text('UPDATED_SHARED_CONTEXT')
        self.run_cli('--only', 'agents')
        self.assertIn('UPDATED_SHARED_CONTEXT', codex.read_text())
        self.assertIn('LINUX_CONTEXT', claude.read_text())
        self.env['DONNES_CONFIGS_PROFILE'] = 'macos'
        self.run_cli('uninstall', '--only', 'agents')
        self.assertFalse(codex.is_symlink())
        self.assertFalse(claude.is_symlink())
        self.assertEqual(default_claude.read_text(), 'default remains local')
        self.assertEqual(global_file.read_text(), 'UPDATED_SHARED_CONTEXT')

    def test_missing_os_context_fails_before_replacing_existing_instructions(self):
        global_file = self.write('shared/agents/global/AGENTS.md', 'SHARED_CONTEXT')
        codex = self.home / '.codex/AGENTS.md'
        codex.parent.mkdir()
        codex.symlink_to(global_file)
        (self.repo / 'macos/agents/CONTEXT.md').unlink()
        result = subprocess.run(['bash', str(self.repo / 'cli'), '--only', 'agents'],
                                env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('CONTEXT.md', result.stderr)
        self.assertEqual(codex.resolve(), global_file)
        self.assertFalse((self.home / '.claude').exists())

    def test_agents_dry_run_compares_proposed_instructions_without_writing(self):
        shared = self.write('shared/agents/global/AGENTS.md', 'SHARED_CONTEXT')
        self.run_cli('--only', 'agents')
        local = self.home / '.codex/AGENTS.md'
        original = local.read_text()
        local.unlink()
        local.write_text(original)
        generated = self.repo / '.generated/agents/macos/AGENTS.md'
        generated.unlink()
        preview = self.run_cli('--only', 'agents', '--dry-run')
        self.assertNotIn('~/.codex/AGENTS.md differs', preview.stdout)
        self.assertFalse(generated.exists())
        self.assertEqual(local.read_text(), original)
        self.run_cli('--only', 'agents')
        local.unlink()
        local.write_text(original)
        before = generated.read_bytes()
        shared.write_text('CHANGED_SHARED_CONTEXT')
        preview = self.run_cli('--only', 'agents', '--dry-run')
        self.assertIn('~/.codex/AGENTS.md differs', preview.stdout)
        self.assertEqual(generated.read_bytes(), before)
        self.assertEqual(local.read_text(), original)

    def test_command_center_skills_are_opt_in_and_removable(self):
        managed = self.write('fleet/skills/provision-box/SKILL.md', 'provision').parent
        self.write('shared/skills/example/SKILL.md', 'shared')
        self.write('shared/skills.lock.json', '{"version":3,"skills":{}}')
        custom = self.home / '.claude-work'
        self.env['CLAUDE_CONFIG_DIR'] = str(custom)
        agent = self.home / '.agents/skills/provision-box'
        claude = custom / 'skills/provision-box'
        self.run_cli('--skip', 'packages,gh-extensions,agents,nvim,shell,tmux,git,session')
        self.assertFalse(agent.exists())
        self.assertEqual((custom / 'skills/example/SKILL.md').read_text(), 'shared')
        self.run_cli('--only', 'command-center', '--dry-run')
        self.assertFalse(agent.exists())
        self.run_cli('--only', 'command-center')
        self.assertEqual(agent.resolve(), managed)
        self.assertEqual(claude.resolve(), managed)
        self.run_cli('--only', 'skills')
        self.assertEqual(agent.resolve(), managed)
        self.assertEqual(claude.resolve(), managed)
        foreign = self.write('.agents/skills/foreign-manager/SKILL.md', 'foreign', home=True)
        self.write('fleet/skills/foreign-manager/SKILL.md', 'repository')
        self.run_cli('uninstall', '--only', 'command-center')
        self.assertFalse(agent.is_symlink())
        self.assertFalse(claude.is_symlink())
        self.assertEqual((managed / 'SKILL.md').read_text(), 'provision')
        self.assertEqual(foreign.read_text(), 'foreign')
        self.run_cli('--only', 'command-center')
        self.run_cli('remove-skill', 'provision-box')
        self.assertFalse(managed.exists())
        self.assertFalse(agent.is_symlink())
        self.assertFalse(claude.is_symlink())

    def test_skill_collection_install_rejects_duplicate_names_before_linking(self):
        self.write('shared/skills/example/SKILL.md', 'shared')
        self.write('fleet/skills/example/SKILL.md', 'manager')
        self.write('shared/skills.lock.json', '{"version":3,"skills":{}}')
        for components in ['skills', 'command-center']:
            with self.subTest(components=components):
                result = subprocess.run(['bash', str(self.repo / 'cli'), '--only', components],
                                        env=self.env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('ambiguous tracked skill: example', result.stderr)
                self.assertFalse((self.home / '.agents').exists())
                self.assertFalse((self.home / '.claude').exists())

    def test_detached_command_center_skill_updates_its_original_collection(self):
        tracked = self.write('fleet/skills/provision-box/SKILL.md', 'initial').parent
        local = self.write('.agents/skills/provision-box/SKILL.md', 'updated', home=True).parent
        self.run_cli('update', str(local), '--dry-run')
        self.assertEqual((tracked / 'SKILL.md').read_text(), 'initial')
        self.run_cli('update', str(local))
        self.assertEqual((tracked / 'SKILL.md').read_text(), 'updated')
        self.assertEqual(local.resolve(), tracked)
        self.assertFalse((self.repo / 'shared/skills/provision-box').exists())

    def test_generated_instructions_do_not_offer_update_repository_from_local(self):
        shared = self.write('shared/agents/global/AGENTS.md', 'SHARED_CONTEXT')
        local = self.write('.codex/AGENTS.md', 'local override', home=True)
        output = interactive_cli(self.repo, self.env, ['--only', 'agents'], [
            ('Resolve ~/.codex/AGENTS.md', '\x03'),
        ], expected_code=130)
        self.assertNotIn('Update repository from local copy', output)
        self.assertEqual(local.read_text(), 'local override')
        self.assertEqual(shared.read_text(), 'SHARED_CONTEXT')

    def test_conflict_choices_and_same_second_default(self):
        source = self.write('shared/skills/example/SKILL.md', 'repository')
        self.write('shared/skills.lock.json', '{"version":3,"skills":{}}')
        local = self.write('.agents/skills/example/SKILL.md', 'local', home=True)
        for choice, reply in [('keep', '\r'), ('replace', '\x1b[B\r'),
                              ('update', '\x1b[B\x1b[B\r')]:
            with self.subTest(choice=choice):
                if local.parent.is_symlink():
                    local.parent.unlink()
                    local.parent.mkdir()
                source.write_text('repository')
                local.write_text('local')
                os.utime(source, (1700000000.2, 1700000000.2))
                os.utime(local, (1700000000.8, 1700000000.8))
                interactive_cli(self.repo, self.env, ['--only', 'skills'], [
                    ('Resolve ~/.agents/skills/example', reply),
                ])
                self.assertEqual(source.read_text(), 'local' if choice == 'update' else 'repository')
                self.assertEqual(local.read_text(), 'repository' if choice == 'replace' else 'local')
                self.assertEqual(local.parent.is_symlink(), choice != 'keep')

    def test_packages_install_only_what_is_missing(self):
        log = self.log
        self.write('packages/macos.txt', 'formula-one\nformula-two\n')
        self.write('packages/macos-casks.txt', 'app-one\nowner/tap/app-two\n')
        self.write('packages/gh-extensions.txt', 'owner/one\nowner/two\n')
        self.env.update(FAKE_GH_EXTENSIONS='owner/two', FAKE_FORMULAE='formula-two', FAKE_CASKS='app-one')
        self.run_cli('--only', 'packages,gh-extensions')
        self.assertEqual([json.loads(line) for line in log.read_text().splitlines()], [
            ['brew', ['install', '--formula', 'formula-one'], ''],
            ['brew', ['trust', '--tap', 'owner/tap'], ''],
            ['brew', ['install', '--cask', 'owner/tap/app-two'], ''],
            ['curl', ['-fsSL', 'https://opencode.ai/v2/install'], ''],
            ['gh', ['extension', 'install', 'owner/one'], ''],
        ])
        self.assertEqual((self.home / 'opencode-installer-args').read_text().strip(), '--no-modify-path')
        # Installed packages are not reinstalled, which would upgrade them.
        log.write_text('')
        self.opencode('2.0.26')
        self.env.update(FAKE_FORMULAE='formula-one formula-two', FAKE_CASKS='app-one app-two')
        self.run_cli('--only', 'packages')
        self.assertEqual(log.read_text(), '')

        self.env.update(DONNES_CONFIGS_PROFILE='omarchy', FAKE_PRESENT='package-one')
        self.write('packages/omarchy.txt', 'package-one\npackage-two\n')
        # yay prompts, so a missing package needs a terminal; gh extensions stay installable.
        result = subprocess.run(['bash', str(self.repo / 'cli'), '--only', 'packages'], env=self.env,
                                capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing packages: package-two', result.stderr)
        self.run_cli('--only', 'gh-extensions')
        self.assertEqual([json.loads(line) for line in log.read_text().splitlines()], [
            ['gh', ['extension', 'install', 'owner/one'], ''],
        ])

    def test_session_process_contracts(self):
        log = self.log
        self.env.update(DONNES_CONFIGS_PROFILE='omarchy')
        config = self.write('.config/hypr/hyprland.lua', '-- user config\n', home=True)
        module = self.write('omarchy/hypr/session.lua', '-- session')
        timer = self.write('omarchy/systemd/user/hypr-session-autosave.timer', '[Timer]')
        self.run_cli('--only', 'session')
        self.assertEqual((self.home / '.config/hypr/session.lua').resolve(), module)
        self.assertEqual((self.home / '.config/systemd/user/hypr-session-autosave.timer').resolve(), timer)
        self.assertIn('require("hypr.session")', config.read_text())
        self.run_cli('uninstall', '--only', 'session')
        self.assertEqual([json.loads(line) for line in log.read_text().splitlines()], [
            ['systemctl', ['--user', 'daemon-reload'], ''],
            ['systemctl', ['--user', 'enable', '--now', 'hypr-session-autosave.timer'], ''],
            ['systemctl', ['--user', 'disable', '--now', 'hypr-session-autosave.timer'], ''],
            ['systemctl', ['--user', 'daemon-reload'], ''],
        ])
        self.assertEqual(config.read_text().strip(), '-- user config')
        self.assertFalse((self.home / '.config/hypr/session.lua').is_symlink())
        self.assertFalse((self.home / '.config/systemd/user/hypr-session-autosave.timer').is_symlink())

    def test_omarchy_apps_install_only_when_missing(self):
        self.env.update(DONNES_CONFIGS_PROFILE='omarchy', FAKE_PRESENT='steam mangohud lact tailscale zed omazed '
                        'helium-browser-bin oversteer usb_modeswitch')
        self.run_cli('--only', 'apps', '--dry-run')
        self.assertFalse(self.log.exists())
        self.run_cli('--only', 'apps')
        self.assertEqual([json.loads(line)[:2] for line in self.log.read_text().splitlines()], [
            ['omarchy-pkg-add', ['mangohud', 'lib32-mangohud']],
            ['omarchy-pkg-aur-add', ['oversteer', 'new-lg4ff-dkms-git', 'usb_modeswitch']],
            ['omarchy-install-browser', ['zen']],
        ])
        self.env['DONNES_CONFIGS_PROFILE'] = 'macos'
        self.assertNotIn('apps', interactive_cli(self.repo, self.env, ['--interactive'], [('Select components', '\x03')], 130))

    def test_mise_links_shared_fragment_and_schedules_pruning(self):
        log = self.log
        fragment = self.write('shared/mise/conf.d/donnes.toml', '[tools]\n')
        self.run_cli('--only', 'mise')
        self.assertEqual((self.home / '.config/mise/conf.d/donnes.toml').resolve(), fragment)
        agents = self.home / 'Library/LaunchAgents'
        prune = (agents / 'dev.dstech.mise-prune.plist').read_text()
        for plist in agents.iterdir():
            plistlib.loads(plist.read_bytes())
        self.assertIn(str(self.repo / 'macos/bin/xcode-node-env'), prune)
        self.assertIn('mise prune --yes', prune)
        self.assertIn('.local/share/mise/shims', (agents / 'dev.dstech.guipath.plist').read_text())
        domain = f'gui/{os.getuid()}'
        calls = [json.loads(line)[:2] for line in log.read_text().splitlines()]
        self.assertEqual(calls, [
            ['launchctl', ['bootout', f'{domain}/dev.dstech.guipath']],
            ['launchctl', ['bootstrap', domain, str(agents / 'dev.dstech.guipath.plist')]],
            ['launchctl', ['bootout', f'{domain}/dev.dstech.mise-prune']],
            ['launchctl', ['bootstrap', domain, str(agents / 'dev.dstech.mise-prune.plist')]],
        ])
        log.write_text('')
        self.run_cli('uninstall', '--only', 'mise')
        self.assertFalse((self.home / '.config/mise/conf.d/donnes.toml').is_symlink())
        self.assertEqual(list(agents.iterdir()), [])
        self.assertEqual([json.loads(line)[1][0] for line in log.read_text().splitlines()], ['bootout', 'bootout'])

        log.write_text('')
        self.env['DONNES_CONFIGS_PROFILE'] = 'omarchy'
        # Omarchy's config.toml replaces the shared list, so the CLI appends what it lacks.
        self.write('shared/mise/conf.d/donnes.toml', '[settings]\nidiomatic_version_file_enable_tools = ["node", "ruby"]\n')
        self.env['FAKE_MISE_SETTING'] = '["ruby"]'
        timer = self.write('omarchy/mise/mise-prune.timer', '[Timer]')
        self.write('omarchy/mise/mise-prune.service', '[Service]')
        self.run_cli('--only', 'mise')
        self.assertEqual((self.home / '.config/systemd/user/mise-prune.timer').resolve(), timer)
        self.assertEqual([json.loads(line)[:2] for line in log.read_text().splitlines()], [
            ['mise', ['settings', 'add', 'idiomatic_version_file_enable_tools', 'node']],
            ['systemctl', ['--user', 'daemon-reload']],
            ['systemctl', ['--user', 'enable', '--now', 'mise-prune.timer']],
        ])

    def test_gitconfig_keeps_local_identity_and_includes_shared_settings(self):
        shared = self.write('macos/gitconfig', '[pull]\n\trebase = true\n')
        config = self.home / '.gitconfig'
        config.symlink_to(shared)
        self.run_cli('--only', 'git')
        self.assertFalse(config.is_symlink())
        self.assertEqual(shared.read_text(), '[pull]\n\trebase = true\n')
        self.assertIn(f'[include]\n\tpath = {shared}', config.read_text())
        config.write_text('[user]\n\temail = me@example.com\n' + config.read_text())
        self.run_cli('--only', 'git')
        self.assertEqual(config.read_text().count('[include]'), 1)
        self.run_cli('uninstall', '--only', 'git')
        self.assertEqual(config.read_text().strip(), '[user]\n\temail = me@example.com')

    def health(self, expected_code, *args):
        result = subprocess.run(['bash', str(self.repo / 'cli'), 'health', *args], env=self.env,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)
        return result.stdout

    def healthy_macos(self, startup_extra=''):
        """Applies the repo to a macOS home whose shell finds every tool through mise."""
        fake_bin = self.repo.parent / 'fake-bin'
        shims = self.home / '.local/share/mise/shims'
        shims.mkdir(parents=True, exist_ok=True)
        for name in ['node', 'jj', 'cf', 'vp']:
            (shims / name).write_text('#!/bin/sh\n')
            (shims / name).chmod(0o755)
        # health starts the user's real shell with a clean environment, so its
        # startup file is what puts the fakes and mise's shims on PATH. zsh reads
        # the managed ~/.zshrc link; bash reads an unmanaged ~/.bashrc.
        def startup(extra=''):
            content = f'export PATH="{self.home}/.opencode/bin:{fake_bin}:{shims}:$PATH"\n' + extra
            self.write('macos/zshrc', content)
            self.write('.bashrc', content, home=True)
        startup(startup_extra)
        self.opencode('2.0.26')
        self.write('shared/agents/global/AGENTS.md', 'instructions')
        self.write('packages/macos.txt', 'git\nmise\n')
        self.write('packages/macos-casks.txt', 'abue-ammar/tinycast/tinycast\n')
        self.write('packages/gh-extensions.txt', 'github/gh-stack\n')
        self.env.update(FAKE_FORMULAE='git mise', FAKE_CASKS='tinycast', FAKE_GH_EXTENSIONS='github/gh-stack',
                        FAKE_GUI_PATH=f'{shims}:/usr/bin',
                        FAKE_LOADED='dev.dstech.guipath dev.dstech.mise-prune', FAKE_LAUNCHD_PRINT='\tlast exit code = 0',
                        FAKE_MISE_LS=json.dumps({tool: [{'version': '1.0.0', 'installed': True}] for tool in
                                                 ['node', 'jj', 'npm:cf', 'github:voidzero-dev/vite-plus']}))
        self.run_cli('--skip', 'packages')
        return startup, shims

    def test_health_reports_drift_and_failures_on_the_detected_profile(self):
        # Vite+'s node shim comes first; in system-first mode it hands off to mise.
        vite = self.home / '.vite-plus/bin'
        vite.mkdir(parents=True)
        (vite / 'vp').write_text('#!/usr/bin/env python3\nimport json, os, sys\n'
                                 'mode = os.path.join(os.environ["HOME"], ".vite-plus/mode")\n'
                                 'managed = not os.path.exists(mode) or open(mode).read() != "system_first"\n'
                                 'args = sys.argv[1:]\n'
                                 'if args[:2] == ["env", "current"]:\n'
                                 '    key = "node" if args[2] == "node" else "package_manager"\n'
                                 '    print(json.dumps({key: {"mode": "managed" if managed else "system_first"}}))\n'
                                 'elif args[:2] == ["env", "which"]:\n'
                                 '    print(os.path.join(os.environ["HOME"], ".vite-plus/js_runtime/node/1/bin" if managed\n'
                                 '                       else ".local/share/mise/shims", args[2]))\n'
                                 'elif args[:2] == ["env", "off"]:\n'
                                 '    open(mode, "w").write("system_first")\n'
                                 'elif args[:2] == ["env", "on"] and os.path.exists(mode):\n'
                                 '    os.remove(mode)\n')
        (vite / 'vp').chmod(0o755)
        (vite / 'node').symlink_to('vp')
        startup, shims = self.healthy_macos(f'export PATH="{vite}:$PATH"\n')
        output = self.health(0)
        self.assertIn('managed files match the repository', output)
        self.assertIn("3 tools resolve through mise (1 via Vite+'s system-first shims)", output)
        self.assertIn("vp resolves to Vite+'s own install", output)
        self.assertIn('opencode 2.0.26 installed', output)
        self.assertIn('1 listed gh extensions installed', output)
        self.assertIn('opencode resolves to its v2 install', output)
        self.assertIn('no global bun or pnpm copies of mise tools', output)
        self.assertNotIn('[fail', output)

        # A machine can give these runtimes to Vite+; apply, preview and health follow it.
        machine = self.write('.config/donnes-configs/machine.json', json.dumps({'jsRuntimes': 'vite-plus'}), home=True)
        output = self.health(0)
        self.assertIn('setting: vp env on', output)
        self.assertIn("node resolves to ~/.local/share/mise/shims/node instead of Vite+'s managed runtime", output)
        self.run_cli('--only', 'mise')
        output = self.health(0)
        self.assertIn("1 tools resolve to Vite+'s managed runtimes", output)
        self.assertIn('Vite+ hands node, npm, pnpm, yarn, bun to Vite+', self.run_cli('--only', 'mise', '--dry-run').stdout)
        self.assertIn(', 1 warning,', output)  # only the test repo not being a git checkout
        machine.unlink()

        shadow = self.repo.parent / 'shadow'
        shadow.mkdir()
        (shadow / 'jj').write_text('#!/bin/sh\n')
        (shadow / 'jj').chmod(0o755)
        (self.home / '.zshenv').write_text('')
        (self.home / '.pyenv').mkdir()
        (self.home / '.vite-plus/mode').unlink(missing_ok=True)
        self.opencode('1.19.0')
        self.write('.bun/bin/jj', '', home=True)
        startup(f'export PATH="{vite}:{shadow}:$PATH"\nexport FAKE_MISE_DOCTOR=1\n')
        self.env.update(FAKE_FORMULAE='git', FAKE_GH_EXTENSIONS='', FAKE_LOADED='dev.dstech.guipath',
                        FAKE_MISE_LS=json.dumps({'node': [{'version': '1.0.0', 'installed': False}], 'jj': [{'version': '1.0.0', 'installed': True}],
                                                 'npm:other': [{'version': '1.0.0', 'installed': True}]}))
        self.write('shared/mise/conf.d/donnes.toml', '[tools]\nnode = "lts"\nbat = "latest"\n')
        output = self.health(1)
        for expected in ['append: add managed block in ~/.zshenv', 'missing Homebrew formulae: mise',
                         'review with ./cli --dry-run --only mise,shell, then apply with ./cli --only mise,shell',
                         'not configured: bat',
                         'not installed: node', 'mise doctor found problems', f'jj resolves to {shadow}/jj',
                         "node resolves to Vite+'s ~/.vite-plus/js_runtime/node/1/bin/node instead of mise",
                         'setting: vp env off', 'no executable known for npm:other',
                         '~/.pyenv is left over from pyenv', 'opencode 1.19.0 is not v2',
                         'missing gh extensions: github/gh-stack',
                         '~/.bun/bin/jj duplicates the mise tool', 'dev.dstech.mise-prune is not loaded']:
            self.assertIn(expected, output)

        # A listing it cannot understand is a failure, never "everything installed".
        self.env['FAKE_MISE_LS'] = json.dumps({'node': [{'installed': True}]})
        output = self.health(1)
        self.assertIn('mise ls returned an unexpected entry for node', output)
        self.assertNotIn('configured tools installed', output)

        self.env.update(DONNES_CONFIGS_PROFILE='omarchy', FAKE_PRESENT='atuin steam', FAKE_LOADED='mise-prune.timer',
                        FAKE_SYSTEMD_SHOW='Result=exit-code;ExecMainStatus=1;ExecMainExitTimestamp=@1700000000')
        self.write('packages/omarchy.txt', 'atuin\n')
        output = self.health(1)
        self.assertIn('1 listed packages installed', output)
        self.assertIn('missing apps: MangoHud (mangohud lib32-mangohud)', output)
        self.assertIn('mise-prune.service last failed (exit-code, status 1)', output)
        self.assertIn('hypr-session-autosave.timer is not active', output)
        # A package query that fails is a failure, never an empty "nothing missing".
        self.env['FAKE_PACMAN_BROKEN'] = '1'
        output = self.health(1)
        self.assertIn('pacman -T failed', output)
        self.assertNotIn('listed packages installed', output)

    def test_health_checks_recorded_homes_role_and_strict_exceptions(self):
        self.write('fleet/skills/provision-box/SKILL.md', 'provision')
        self.write('shared/skills.lock.json', '{"version":3,"skills":{}}')
        self.healthy_macos()
        output = self.health(0)
        self.assertIn('last install', output)
        self.assertIn('completed', output)
        self.assertIn('role unknown', output)
        # A job that ran and failed is a failure, not a loaded agent.
        self.env['FAKE_LAUNCHD_PRINT'] = '\tlast exit code = 1'
        self.assertIn('dev.dstech.mise-prune last exited 1', self.health(1))
        self.env['FAKE_LAUNCHD_PRINT'] = '\tlast exit code = 0'

        # Instructions applied to another Codex home are checked from then on.
        work = self.home / '.codex-work'
        self.env['CODEX_HOME'] = str(work)
        self.run_cli('--only', 'agents,command-center')
        del self.env['CODEX_HOME']
        self.assertIn('Codex ~/.codex, ~/.codex-work', self.health(0))
        (work / 'AGENTS.md').unlink()
        self.assertIn(f'link: ~/.codex-work/AGENTS.md -> <repo>/.generated/agents/macos/AGENTS.md', self.health(0))

        # Declared intent: a worker must not carry command-center skills, and
        # --strict fails on warnings until each is recorded as an exception.
        machine = self.write('.config/donnes-configs/machine.json', json.dumps({'role': 'worker'}), home=True)
        self.write('.codex-work/AGENTS.override.md', 'stale', home=True)
        output = self.health(0)
        self.assertIn('command-center skills on a worker: ~/.agents/skills/provision-box', output)
        result = json.loads(self.health(1, '--json', '--strict'))
        warned = sorted(check['id'] for check in result['checks'] if check['status'] == 'fail')
        self.assertEqual(warned, ['agents-override:~/.codex-work/AGENTS.override.md', 'checkout:git',
                                  'files:~/.codex-work/AGENTS.md -> <repo>/.generated/agents/macos/AGENTS.md',
                                  'role:command-center-skills'])
        self.assertEqual(result['versions']['node'], '1.0.0')
        machine.write_text(json.dumps({'role': 'worker', 'exceptions': {id: 'kept on purpose' for id in warned}}))
        output = self.health(0, '--strict')
        self.assertIn('[accept ] command-center skills on a worker', output)
        self.assertIn('(kept on purpose)', output)

        # The last run's failure stays visible after the failing component.
        (self.repo / 'macos/agents/CONTEXT.md').unlink()
        subprocess.run(['bash', str(self.repo / 'cli'), '--only', 'agents'], env=self.env, capture_output=True)
        self.assertIn('failed in agents', self.health(1))

if __name__ == '__main__':
    unittest.main()
