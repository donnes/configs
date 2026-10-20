"""Side effects outside the home directory: packages, apps, background jobs and REA.

The doubles in boundary.py keep the state these tools would keep and reject what
the real tools reject, so these tests assert the resulting machine state.
"""
import subprocess
import unittest

from harness import CliTestCase


class PlatformTests(CliTestCase):
    def test_rea_requires_explicit_apply_and_reports_setup_failure(self):
        self.boundary(npx={'status': 7})
        for profile in ['macos', 'omarchy']:
            with self.subTest(profile=profile):
                self.env['DONNES_CONFIGS_PROFILE'] = profile
                self.cli('--only', 'rea', '--dry-run')
                self.cli('uninstall', '--only', 'rea')
                self.cli('--skip', 'packages,gh-extensions,apps,agents,skills,mise,atuin,nvim,gradle,shell,tmux,git,session')
                self.assertEqual(self.state['npx']['calls'], [])
                result = self.fails('--only', 'rea')
                self.assertIn('npx failed (7)', result.stderr)
                # Pinned, and scoped to the two clients this repo manages.
                self.assertEqual(self.state['npx']['calls'], [
                    ['--yes', 'rea-agents@6.5.0', 'setup', '--client', 'codex', '--client', 'claude_code', '--yes']])
                self.boundary(npx={'calls': []})

    def test_packages_install_only_what_is_missing(self):
        self.write('packages/macos.txt', 'formula-one\nformula-two\n')
        self.write('packages/macos-casks.txt', 'app-one\nowner/tap/app-two\n')
        self.write('packages/gh-extensions.txt', 'owner/one\nowner/two\n')
        startup = [self.write(name, '# user\n', home=True) for name in ['.zshrc', '.bashrc']]
        self.boundary(brew={'formulae': ['formula-two'], 'casks': ['app-one']}, gh={'extensions': ['owner/two']})
        before = self.state
        self.cli('--only', 'packages,gh-extensions', '--dry-run')
        self.assertEqual(self.state, before)
        self.assertFalse((self.home / '.opencode').exists())
        self.cli('--only', 'packages,gh-extensions')
        installed = self.state
        self.assertEqual(sorted(installed['brew']['formulae']), ['formula-one', 'formula-two'])
        self.assertEqual(sorted(installed['brew']['casks']), ['app-one', 'app-two'])
        self.assertEqual(sorted(installed['gh']['extensions']), ['owner/one', 'owner/two'])
        opencode = subprocess.run([self.home / '.opencode/bin/opencode', '--version'], capture_output=True, text=True)
        self.assertEqual(opencode.stdout.strip(), 'opencode v2.0.26')
        # The startup files already put ~/.opencode/bin first; the installer must not edit them.
        self.assertEqual([file.read_text() for file in startup], ['# user\n', '# user\n'])
        # The doubles reject reinstalling, which would upgrade an installed package.
        self.cli('--only', 'packages,gh-extensions')
        self.assertEqual(self.state, installed)

        # yay prompts, so a missing package needs a terminal; gh extensions stay installable.
        self.env['DONNES_CONFIGS_PROFILE'] = 'omarchy'
        self.write('packages/omarchy.txt', 'package-one\npackage-two\n')
        self.boundary(pacman={'installed': ['package-one']}, gh={'extensions': ['owner/two']})
        result = self.fails('--only', 'packages')
        self.assertIn('missing packages: package-two', result.stderr)
        self.assertEqual(self.state['pacman']['installed'], ['package-one'])
        self.cli('--only', 'gh-extensions')
        self.assertEqual(sorted(self.state['gh']['extensions']), ['owner/one', 'owner/two'])

    def test_omarchy_apps_install_only_when_missing(self):
        self.env['DONNES_CONFIGS_PROFILE'] = 'omarchy'
        # pacman cannot install AUR packages, and Omarchy's installers reopen apps that are present.
        self.boundary(pacman={'installed': 'steam mangohud lact tailscale zed omazed helium-browser-bin oversteer usb_modeswitch'.split(),
                              'aur': ['oversteer', 'new-lg4ff-dkms-git', 'usb_modeswitch', 'helium-browser-bin']})
        before = self.state
        self.cli('--only', 'apps', '--dry-run')
        self.assertEqual(self.state, before)
        self.cli('--only', 'apps')
        self.assertLessEqual({'lib32-mangohud', 'new-lg4ff-dkms-git', 'zen-browser-bin'}, set(self.state['pacman']['installed']))
        self.env['DONNES_CONFIGS_PROFILE'] = 'macos'
        self.assertNotIn('apps', self.interactive(['--interactive'], [('Select components', '\x03')], code=130))

    def test_session_enables_its_timer_and_uninstall_unloads_it(self):
        self.env['DONNES_CONFIGS_PROFILE'] = 'omarchy'
        config = self.write('.config/hypr/hyprland.lua', '-- user config\n', home=True)
        module = self.write('omarchy/hypr/session.lua', '-- session')
        timer = self.write('omarchy/systemd/user/hypr-session-autosave.timer', '[Timer]')
        self.cli('--only', 'session')
        self.assertEqual((self.home / '.config/hypr/session.lua').resolve(), module)
        self.assertEqual((self.home / '.config/systemd/user/hypr-session-autosave.timer').resolve(), timer)
        self.assertIn('require("hypr.session")', config.read_text())
        systemd = self.state['systemd']
        self.assertIn('hypr-session-autosave.timer', systemd['active'])
        self.cli('uninstall', '--only', 'session')
        systemd = self.state['systemd']
        self.assertNotIn('hypr-session-autosave.timer', systemd['active'])
        # The unit files are gone, and systemd was told so.
        self.assertNotIn('hypr-session-autosave.timer', systemd['loaded'])
        self.assertEqual(config.read_text().strip(), '-- user config')
        self.assertFalse((self.home / '.config/hypr/session.lua').is_symlink())
        self.assertFalse((self.home / '.config/systemd/user/hypr-session-autosave.timer').is_symlink())

    def test_xcode_node_env_repoints_only_exact_installs(self):
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
            return subprocess.run(['sh', str(self.repo / 'macos/bin/xcode-node-env'), *args], env=self.env,
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

    def test_mise_links_shared_fragment_and_schedules_pruning(self):
        fragment = self.write('shared/mise/conf.d/donnes.toml', '[tools]\n')
        macos = self.write('macos/mise/conf.d/donnes-macos.toml', '[tools]\n')
        self.cli('--only', 'mise')
        self.assertEqual((self.home / '.config/mise/conf.d/donnes.toml').resolve(), fragment)
        self.assertEqual((self.home / '.config/mise/conf.d/donnes-macos.toml').resolve(), macos)
        agents = self.home / 'Library/LaunchAgents'
        loaded = self.state['launchd']['loaded']
        self.assertEqual(loaded, {label: str(agents / f'{label}.plist') for label in ['dev.dstech.guipath', 'dev.dstech.mise-prune']})
        # Reapplying reloads loaded agents; bootstrapping a loaded one would fail.
        self.cli('--only', 'mise')
        self.assertEqual(self.state['launchd']['loaded'], loaded)

        # At login, GUI apps such as Xcode get mise's shims on their PATH.
        self.assertEqual(self.launchd_job('dev.dstech.guipath').returncode, 0)
        self.assertIn(str(self.home / '.local/share/mise/shims'), self.state['launchd']['env']['PATH'].split(':'))
        # The daily job repoints Xcode's Node at the shim before pruning installs...
        project = self.write('Git/app/ios/.xcode.env.local',
                             f'export NODE_BINARY="{self.home}/.local/share/mise/installs/node/24.13.1/bin/node"\n', home=True)
        job = self.launchd_job('dev.dstech.mise-prune')
        self.assertEqual(job.returncode, 0, job.stderr)
        self.assertEqual(project.read_text(), f'export NODE_BINARY="{self.home}/.local/share/mise/shims/node"\n')
        self.assertEqual(self.state['mise']['pruned'], 1)
        # ...and skips the prune when a project it cannot search may still name a version.
        locked = self.home / 'Git/locked'
        locked.mkdir()
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o755)
        self.assertNotEqual(self.launchd_job('dev.dstech.mise-prune').returncode, 0)
        self.assertEqual(self.state['mise']['pruned'], 1)

        self.cli('uninstall', '--only', 'mise')
        self.assertFalse((self.home / '.config/mise/conf.d/donnes.toml').is_symlink())
        self.assertFalse((self.home / '.config/mise/conf.d/donnes-macos.toml').is_symlink())
        self.assertEqual(list(agents.iterdir()), [])
        self.assertEqual(self.state['launchd']['loaded'], {})

    def test_omarchy_mise_appends_missing_settings_and_enables_pruning(self):
        self.env['DONNES_CONFIGS_PROFILE'] = 'omarchy'
        # Omarchy's config.toml replaces the shared list, so the CLI appends what it lacks.
        self.write('shared/mise/conf.d/donnes.toml', '[settings]\nidiomatic_version_file_enable_tools = ["node", "ruby"]\n')
        self.boundary(mise={'settings': {'idiomatic_version_file_enable_tools': ['ruby']}})
        timer = self.write('omarchy/mise/mise-prune.timer', '[Timer]')
        self.write('omarchy/mise/mise-prune.service', '[Service]')
        for _ in range(2):
            self.cli('--only', 'mise')
            self.assertEqual(self.state['mise']['settings'], {'idiomatic_version_file_enable_tools': ['ruby', 'node']})
        self.assertEqual((self.home / '.config/systemd/user/mise-prune.timer').resolve(), timer)
        self.assertIn('mise-prune.timer', self.state['systemd']['active'])
        # Omarchy's agent CLI wrappers run `mise use -g`, which refuses a tool that
        # two global files declare, so the macOS-only agent CLIs stay off Omarchy.
        self.write('macos/mise/conf.d/donnes-macos.toml', '[tools]\nclaude = "latest"\n')
        self.cli('--only', 'mise')
        self.assertEqual(sorted(path.name for path in (self.home / '.config/mise/conf.d').iterdir()), ['donnes.toml'])


if __name__ == '__main__':
    unittest.main()
