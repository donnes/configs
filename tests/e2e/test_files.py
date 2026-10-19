"""Managed files: links, generated instructions, marker blocks, conflicts, adopt and update."""
import os
import shutil
import subprocess
import unittest

from harness import CliTestCase


class FilesTests(CliTestCase):
    def test_install_and_uninstall_preserve_foreign_files(self):
        source = self.write('shared/agents/global/AGENTS.md', 'instructions')
        custom = self.home / '.codex-purpose'
        self.env['CODEX_HOME'] = str(custom)
        skill = self.write('shared/skills/example/SKILL.md', 'example').parent
        self.write('shared/skills.lock.json', '{"version":3,"skills":{}}')
        foreign = self.write('.agents/skills/foreign/SKILL.md', 'foreign', home=True)
        self.cli('--only', 'agents,skills', '--dry-run')
        self.assertFalse((custom / 'AGENTS.md').exists())
        self.cli('--only', 'agents,skills')
        self.assertIn(source.read_text(), (custom / 'AGENTS.md').read_text())
        self.assertIn('MAC_CONTEXT', (custom / 'AGENTS.md').read_text())
        self.assertEqual((self.home / '.claude/CLAUDE.md').resolve(), (custom / 'AGENTS.md').resolve())
        self.assertEqual((self.home / '.agents/skills/example').resolve(), skill)
        self.cli('uninstall', '--only', 'agents,skills')
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
        self.cli('--only', 'skills')
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
        self.cli('--only', 'nvim', '--dry-run')
        self.assertTrue(destination.is_symlink())
        self.cli('--only', 'nvim')
        self.assertFalse(destination.is_symlink())
        self.assertEqual((destination / 'init.lua').resolve(), init)
        self.assertEqual((destination / 'lazy-lock.json').resolve(), macos_lock)
        self.assertEqual(foreign.read_text(), '-- foreign')
        user = self.write('.config/nvim/custom.lua', '-- user', home=True)
        self.cli('uninstall', '--only', 'nvim')
        self.assertEqual(user.read_text(), '-- user')
        self.env['DONNES_CONFIGS_PROFILE'] = 'omarchy'
        theme = self.write('.local/state/omarchy/current/theme/neovim.lua', '-- active theme', home=True)
        self.cli('--only', 'nvim')
        self.assertEqual((destination / 'lazy-lock.json').resolve(), omarchy_lock)
        self.assertEqual((destination / 'lua/plugins/theme.lua').resolve(), theme)
        self.assertEqual(user.read_text(), '-- user')

    def test_profile_links_follow_the_profile(self):
        ignore = self.write('shared/git/ignore', '.scratch/\n')
        self.write('macos/gitconfig', '[pull]\n\trebase = true\n')
        gradle, git = self.home / '.gradle/gradle.properties', self.home / '.config/git/ignore'
        for profile in ['macos', 'omarchy']:
            with self.subTest(profile=profile):
                self.env['DONNES_CONFIGS_PROFILE'] = profile
                properties = self.write(f'{profile}/gradle.properties', f'reactNativeArchitectures={profile}\n')
                self.cli('--only', 'gradle,git')
                self.assertEqual(gradle.resolve(), properties)
                self.assertEqual(git.resolve(), ignore)
                # Only macOS keeps a local ~/.gitconfig that includes the shared settings.
                self.assertEqual((self.home / '.gitconfig').exists(), profile == 'macos')
                self.cli('uninstall', '--only', 'gradle,git')
                self.assertFalse(gradle.exists())
                self.assertFalse(git.exists())
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
                self.cli('--only', 'shell,tmux', '--dry-run')
                self.assertEqual(block.read_text(), 'export USER_SETTING=1\n')
                self.cli('--only', 'shell,tmux')
                shell_source = self.repo / ('macos/zshenv' if profile == 'macos' else 'omarchy/bashrc.local')
                self.assertIn(f'source "{shell_source}"', block.read_text())
                self.assertEqual(block.read_text().count('# >>> donnes/configs >>>'), 1)
                self.assertEqual(block.read_text().count('# <<< donnes/configs <<<'), 1)
                if profile == 'omarchy':
                    self.assertIn('source-file -q ~/.config/tmux/local.conf', tmux_file.read_text())
                    self.assertEqual(tmux_file.read_text().count('# >>> donnes/configs >>>'), 1)
                once = block.read_bytes()
                self.cli('--only', 'shell,tmux')
                self.assertEqual(block.read_bytes(), once)
                self.assertEqual(block.stat().st_mode & 0o777, 0o640)
                self.cli('uninstall', '--only', 'shell,tmux')
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
        self.cli('--only', 'shell')
        replaced = f'export EARLY=1\n\n{start}\nsource "{self.repo}/macos/zshenv"\n{end}\n\n# Vite+ bin\n. "$HOME/.vite-plus/env"\n'
        self.assertEqual(zshenv.read_text(), replaced)
        self.cli('--only', 'shell')
        self.assertEqual(zshenv.read_text(), replaced)
        for malformed in [f'{start}\n{start}\nx\n{end}\n', f'{end}\nx\n{start}\n', f'{start}\nx\n']:
            with self.subTest(malformed=malformed):
                zshenv.write_text(malformed)
                result = self.fails('--only', 'shell')
                self.assertIn('~/.zshenv has malformed donnes/configs markers', result.stderr)
                self.assertEqual(zshenv.read_text(), malformed)

    def test_adopt_and_update_keep_skill_directory_links(self):
        local = self.write('.agents/skills/example/SKILL.md', 'initial', home=True).parent
        (local / 'reference.md').symlink_to('SKILL.md')
        self.cli('adopt', str(local), '--dry-run')
        self.assertFalse(local.is_symlink())
        self.cli('adopt', str(local))
        tracked = self.repo / 'shared/skills/example'
        self.assertEqual(local.resolve(), tracked)
        self.assertEqual(os.readlink(tracked / 'reference.md'), 'SKILL.md')
        local.unlink()
        shutil.copytree(tracked, local)
        (local / 'SKILL.md').write_text('updated')
        self.cli('update', str(local), '--dry-run')
        self.assertEqual((tracked / 'SKILL.md').read_text(), 'initial')
        self.cli('update', str(local))
        self.assertEqual((tracked / 'SKILL.md').read_text(), 'updated')
        self.assertTrue(local.is_symlink())

    def test_parent_links_into_repo_preserve_files_and_skills(self):
        source = self.write('shared/atuin/config.toml', 'repository config')
        alias = source.parent / 'alias.toml'
        alias.symlink_to('config.toml')
        (self.home / '.config').mkdir()
        (self.home / '.config/atuin').symlink_to(source.parent)
        self.cli('--only', 'atuin')
        self.assertFalse(source.is_symlink())
        self.assertEqual(source.read_text(), 'repository config')
        self.assertEqual(os.readlink(alias), 'config.toml')
        skill = self.write('shared/skills/example/SKILL.md', 'repository skill')
        self.write('shared/skills.lock.json', '{"version":3,"skills":{}}')
        (self.home / '.agents').mkdir()
        (self.home / '.agents/skills').symlink_to(skill.parent.parent)
        self.cli('--only', 'skills')
        self.assertFalse(skill.parent.is_symlink())
        self.assertEqual(skill.read_text(), 'repository skill')

    def test_uncomparable_conflict_keeps_local_and_continues_install(self):
        source = self.write('shared/atuin/config.toml', 'repository')
        later = self.write('shared/atuin/zz.toml', 'later config')
        local = self.write('.config/atuin/config.toml/user.toml', 'local', home=True)
        self.cli('--only', 'atuin')
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
                self.cli('update', str(local))
                self.assertFalse(tracked.is_symlink())
                self.assertEqual(tracked.read_text(), 'updated')
                self.assertEqual(tracked.stat().st_mode & 0o777, 0o755)
                self.assertEqual(local.resolve(), tracked)
                if linked:
                    self.assertEqual(original.read_text(), 'original')

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
                self.cli('--only', 'agents', '--dry-run')
                self.assertEqual(codex.read_bytes(), before)
                self.assertEqual(set(self.repo.iterdir()), entries)
                self.cli('--only', 'agents')
                self.assertEqual(codex.resolve(), claude.resolve())
                self.assertIn('SHARED_CONTEXT', codex.read_text())
                self.assertIn(included, codex.read_text())
                self.assertNotIn(excluded, codex.read_text())
                self.assertIn('COMPUTERS.md', codex.read_text())
                self.assertEqual(default_claude.read_text(), 'default remains local')
                installed = codex.stat().st_mtime_ns
                self.cli('--only', 'agents')
                self.assertEqual(codex.stat().st_mtime_ns, installed)
        global_file.write_text('UPDATED_SHARED_CONTEXT')
        self.cli('--only', 'agents')
        self.assertIn('UPDATED_SHARED_CONTEXT', codex.read_text())
        self.assertIn('LINUX_CONTEXT', claude.read_text())
        self.env['DONNES_CONFIGS_PROFILE'] = 'macos'
        self.cli('uninstall', '--only', 'agents')
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
        result = self.fails('--only', 'agents')
        self.assertIn('CONTEXT.md', result.stderr)
        self.assertEqual(codex.resolve(), global_file)
        self.assertFalse((self.home / '.claude').exists())

    def test_agents_dry_run_compares_proposed_instructions_without_writing(self):
        shared = self.write('shared/agents/global/AGENTS.md', 'SHARED_CONTEXT')
        self.cli('--only', 'agents')
        local = self.home / '.codex/AGENTS.md'
        original = local.read_text()
        local.unlink()
        local.write_text(original)
        generated = self.repo / '.generated/agents/macos/AGENTS.md'
        generated.unlink()
        preview = self.cli('--only', 'agents', '--dry-run')
        self.assertNotIn('~/.codex/AGENTS.md differs', preview.stdout)
        self.assertFalse(generated.exists())
        self.assertEqual(local.read_text(), original)
        self.cli('--only', 'agents')
        local.unlink()
        local.write_text(original)
        before = generated.read_bytes()
        shared.write_text('CHANGED_SHARED_CONTEXT')
        preview = self.cli('--only', 'agents', '--dry-run')
        self.assertIn('~/.codex/AGENTS.md differs', preview.stdout)
        self.assertEqual(generated.read_bytes(), before)
        self.assertEqual(local.read_text(), original)

    def test_generated_instructions_do_not_offer_update_repository_from_local(self):
        shared = self.write('shared/agents/global/AGENTS.md', 'SHARED_CONTEXT')
        local = self.write('.codex/AGENTS.md', 'local override', home=True)
        output = self.interactive(['--only', 'agents'], [('Resolve ~/.codex/AGENTS.md', '\x03')], code=130)
        self.assertNotIn('Update repository from local copy', output)
        self.assertEqual(local.read_text(), 'local override')
        self.assertEqual(shared.read_text(), 'SHARED_CONTEXT')

    def test_conflict_choices_and_same_second_default(self):
        source = self.write('shared/skills/example/SKILL.md', 'repository')
        self.write('shared/skills.lock.json', '{"version":3,"skills":{}}')
        local = self.write('.agents/skills/example/SKILL.md', 'local', home=True)
        for choice, reply in [('keep', '\r'), ('replace', '\x1b[B\r'), ('update', '\x1b[B\x1b[B\r')]:
            with self.subTest(choice=choice):
                if local.parent.is_symlink():
                    local.parent.unlink()
                    local.parent.mkdir()
                source.write_text('repository')
                local.write_text('local')
                os.utime(source, (1700000000.2, 1700000000.2))
                os.utime(local, (1700000000.8, 1700000000.8))
                self.interactive(['--only', 'skills'], [('Resolve ~/.agents/skills/example', reply)])
                self.assertEqual(source.read_text(), 'local' if choice == 'update' else 'repository')
                self.assertEqual(local.read_text(), 'repository' if choice == 'replace' else 'local')
                self.assertEqual(local.parent.is_symlink(), choice != 'keep')

    def test_gitconfig_keeps_local_identity_and_includes_shared_settings(self):
        shared = self.write('macos/gitconfig', '[pull]\n\trebase = true\n')
        config = self.home / '.gitconfig'
        config.symlink_to(shared)

        def setting(key):
            # Git itself resolves the include, as every git command on the machine will.
            return subprocess.run(['git', 'config', '--get', key], cwd=self.home, env=self.env,
                                  capture_output=True, text=True).stdout.strip()
        self.cli('--only', 'git')
        self.assertFalse(config.is_symlink())
        self.assertEqual(shared.read_text(), '[pull]\n\trebase = true\n')
        self.assertEqual(setting('pull.rebase'), 'true')
        config.write_text('[user]\n\temail = me@example.com\n' + config.read_text())
        self.cli('--only', 'git')
        self.assertEqual(config.read_text().count('[include]'), 1)
        self.assertEqual((setting('user.email'), setting('pull.rebase')), ('me@example.com', 'true'))
        self.cli('uninstall', '--only', 'git')
        self.assertEqual(config.read_text().strip(), '[user]\n\temail = me@example.com')
        self.assertEqual(setting('pull.rebase'), '')


if __name__ == '__main__':
    unittest.main()
