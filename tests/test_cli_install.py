import os
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from cli_fixture import copy_cli, interactive_cli


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
        # Default selections reach launchd and systemd; never touch the real ones.
        fake_bin = self.repo.parent / 'fake-bin'
        fake_bin.mkdir()
        self.log = self.repo.parent / 'commands.jsonl'
        for command in ['brew', 'yay', 'systemctl', 'launchctl']:
            executable = fake_bin / command
            executable.write_text('#!/usr/bin/env python3\nimport json, os, sys\n'
                                  'from pathlib import Path\n'
                                  'name = Path(sys.argv[0]).name\n'
                                  'with open(os.environ["COMMAND_LOG"], "a") as log:\n'
                                  '    log.write(json.dumps([name, sys.argv[1:], '
                                  'sys.stdin.read() if name == "yay" else ""]) + "\\n")\n')
            executable.chmod(0o755)
        self.env.update(PATH=str(fake_bin) + os.pathsep + self.env['PATH'], COMMAND_LOG=str(self.log))
        self.write('macos/agents/CONTEXT.md', 'MAC_CONTEXT')
        self.write('linux/agents/CONTEXT.md', 'LINUX_CONTEXT')

    def write(self, relative, content, home=False):
        file = (self.home if home else self.repo) / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content)
        return file

    def run_cli(self, *args):
        result = subprocess.run(['bash', str(self.repo / 'cli'), *args], env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

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
        # Select all, clear all, then choose agents, the second component.
        interactive_cli(self.repo, self.env, ['--interactive'], [
            ('Select components to install', 'aa\x1b[B \r'),
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
            ('Select components to install', 'aa\x1b[B \r'),
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
        self.run_cli('--skip', 'packages,agents,nvim,shell,tmux,git,session')
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

    def test_package_and_session_process_contracts(self):
        log = self.log
        self.write('packages/macos.txt', 'formula-one\nformula-two\n')
        self.write('packages/macos-casks.txt', 'app-one\napp-two\n')
        self.run_cli('--only', 'packages')
        self.assertEqual([json.loads(line) for line in log.read_text().splitlines()], [
            ['brew', ['install', 'formula-one', 'formula-two'], ''],
            ['brew', ['trust', '--tap', 'abue-ammar/tinycast'], ''],
            ['brew', ['install', '--cask', 'app-one', 'app-two'], ''],
        ])
        log.write_text('')
        self.env['DONNES_CONFIGS_PROFILE'] = 'omarchy'
        packages = 'package-one\npackage-two\n'
        self.write('packages/omarchy.txt', packages)
        config = self.write('.config/hypr/hyprland.lua', '-- user config\n', home=True)
        module = self.write('omarchy/hypr/session.lua', '-- session')
        timer = self.write('omarchy/systemd/user/hypr-session-autosave.timer', '[Timer]')
        self.run_cli('--only', 'packages,session')
        self.assertEqual((self.home / '.config/hypr/session.lua').resolve(), module)
        self.assertEqual((self.home / '.config/systemd/user/hypr-session-autosave.timer').resolve(), timer)
        self.assertIn('require("hypr.session")', config.read_text())
        self.run_cli('uninstall', '--only', 'session')
        self.assertEqual([json.loads(line) for line in log.read_text().splitlines()], [
            ['yay', ['-S', '--needed', '-'], packages],
            ['systemctl', ['--user', 'daemon-reload'], ''],
            ['systemctl', ['--user', 'enable', '--now', 'hypr-session-autosave.timer'], ''],
            ['systemctl', ['--user', 'disable', '--now', 'hypr-session-autosave.timer'], ''],
            ['systemctl', ['--user', 'daemon-reload'], ''],
        ])
        self.assertEqual(config.read_text().strip(), '-- user config')
        self.assertFalse((self.home / '.config/hypr/session.lua').is_symlink())
        self.assertFalse((self.home / '.config/systemd/user/hypr-session-autosave.timer').is_symlink())


    def test_mise_links_shared_fragment_and_schedules_pruning(self):
        log = self.log
        fragment = self.write('shared/mise/conf.d/donnes.toml', '[tools]\n')
        self.run_cli('--only', 'mise')
        self.assertEqual((self.home / '.config/mise/conf.d/donnes.toml').resolve(), fragment)
        agents = self.home / 'Library/LaunchAgents'
        prune = (agents / 'dev.dstech.mise-prune.plist').read_text()
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
        timer = self.write('omarchy/mise/mise-prune.timer', '[Timer]')
        self.write('omarchy/mise/mise-prune.service', '[Service]')
        self.run_cli('--only', 'mise')
        self.assertEqual((self.home / '.config/systemd/user/mise-prune.timer').resolve(), timer)
        self.assertEqual([json.loads(line)[:2] for line in log.read_text().splitlines()], [
            ['systemctl', ['--user', 'daemon-reload']],
            ['systemctl', ['--user', 'enable', '--now', 'mise-prune.timer']],
        ])

if __name__ == '__main__':
    unittest.main()
