"""./cli health: drift is a warning, missing or unanswerable state is a failure."""
import json
import unittest

from harness import CliTestCase


class HealthTests(CliTestCase):
    def healthy_macos(self, startup_extra=''):
        """Applies the repo to a macOS home whose shell finds every tool through mise."""
        shims = self.home / '.local/share/mise/shims'
        shims.mkdir(parents=True, exist_ok=True)
        for name in ['node', 'jj', 'cf', 'vp']:
            (shims / name).write_text('#!/bin/sh\n')
            (shims / name).chmod(0o755)

        # health starts the user's real shell with a clean environment, so its
        # startup file is what puts the doubles and mise's shims on PATH. zsh reads
        # the managed ~/.zshrc link; bash reads an unmanaged ~/.bashrc.
        def startup(extra=''):
            content = f'export PATH="{self.bin}:{shims}:{self.home}/.cargo/bin:$PATH"\n' + extra
            self.write('macos/zshrc', content)
            self.write('.bashrc', content, home=True)
        startup(startup_extra)
        # mise's rust puts rustup's proxies in ~/.cargo/bin, not in its shims.
        self.write('.cargo/bin/rustfmt', '#!/bin/sh\n', home=True).chmod(0o755)
        self.write('shared/agents/global/AGENTS.md', 'instructions')
        self.write('packages/macos.txt', 'git\nmise\n')
        self.write('packages/macos-casks.txt', 'abue-ammar/tinycast/tinycast\n')
        self.write('packages/gh-extensions.txt', 'github/gh-stack\n')
        self.boundary(brew={'formulae': ['git', 'mise'], 'casks': ['tinycast']}, gh={'extensions': ['github/gh-stack']},
                      mise={'ls': {tool: [{'version': '1.0.0', 'installed': True}]
                                   for tool in ['node', 'jj', 'npm:cf', 'github:voidzero-dev/vite-plus', 'rust']}})
        self.cli('--skip', 'packages')
        # Logging in runs the GUI PATH agent.
        self.assertEqual(self.launchd_job('dev.dstech.guipath').returncode, 0)
        return startup

    def test_health_reports_drift_and_failures_on_the_detected_profile(self):
        # Vite+'s node shim comes first; in system-first mode it hands off to mise.
        vite = self.home / '.vite-plus/bin'
        self.double(vite / 'vp', 'vp')
        (vite / 'node').symlink_to('vp')
        startup = self.healthy_macos(f'export PATH="{vite}:$PATH"\n')
        report = self.health(0)
        # The test repo is not a git checkout; nothing else may warn or fail.
        self.assertEqual(self.warnings(report), ['checkout:git'])
        self.assertEqual(self.failures(report), [])
        self.check(report, 'ok', 'Shell', '4 tools resolve through mise', "1 via Vite+'s system-first shims")

        # A machine can give these runtimes to Vite+; apply and health follow it.
        machine = self.write('.config/donnes-configs/machine.json', json.dumps({'jsRuntimes': 'vite-plus'}), home=True)
        warnings = self.warnings(self.health(0))
        self.assertIn('path:node', warnings)
        self.assertTrue([id for id in warnings if id.startswith('files:vp env on')], warnings)
        self.cli('--only', 'mise')
        report = self.health(0)
        self.assertEqual(self.warnings(report), ['checkout:git'])
        self.check(report, 'ok', 'Shell', "1 tools resolve to Vite+'s managed runtimes")
        machine.unlink()

        shadow = self.sandbox / 'shadow'
        shadow.mkdir()
        (shadow / 'jj').write_text('#!/bin/sh\n')
        (shadow / 'jj').chmod(0o755)
        (self.home / '.zshenv').write_text('')
        (self.home / '.pyenv').mkdir()
        self.write('.bun/bin/jj', '', home=True)
        startup(f'export PATH="{vite}:{shadow}:$PATH"\n')
        state = self.state
        del state['launchd']['loaded']['dev.dstech.mise-prune']
        self.state_file.write_text(json.dumps(state))
        self.boundary(brew={'formulae': ['git']}, gh={'extensions': []}, vp={'mode': 'managed'},
                      mise={'doctor': 1, 'ls': {'node': [{'version': '1.0.0', 'installed': False}],
                                                'jj': [{'version': '1.0.0', 'installed': True}],
                                                'npm:other': [{'version': '1.0.0', 'installed': True}]}})
        self.write('shared/mise/conf.d/donnes.toml', '[tools]\nnode = "lts"\nbat = "latest"\n')
        report = self.health(1)
        warnings = self.warnings(report)
        for id in ['files:add managed block in ~/.zshenv', 'path:jj', 'path:node', 'path:npm:other',
                   'legacy:pyenv', 'duplicate:~/.bun/bin/jj']:
            self.assertIn(id, warnings)
        self.assertTrue([id for id in warnings if id.startswith('files:vp env off')], warnings)
        for section, words in [('Packages', ['formulae', 'mise']),
                               ('Packages', ['github/gh-stack']), ('mise', ['not configured', 'bat']),
                               ('mise', ['not installed', 'node']), ('Shell', ['mise doctor']),
                               ('Background', ['dev.dstech.mise-prune'])]:
            self.check(report, 'fail', section, *words)
        # The advice names exactly the components whose files drifted.
        self.assertIn('review with ./cli --dry-run --only mise,shell, then apply with ./cli --only mise,shell',
                      self.cli('health', code=1).stdout)

        # A listing it cannot understand is a failure, never "everything installed".
        self.boundary(mise={'ls': {'node': [{'installed': True}]}})
        report = self.health(1)
        self.check(report, 'fail', 'mise', 'unexpected entry for node')
        self.assertEqual([check['status'] for check in report['checks'] if check['section'] == 'mise'], ['fail'])

        self.env['DONNES_CONFIGS_PROFILE'] = 'omarchy'
        self.write('packages/omarchy.txt', 'atuin\n')
        self.boundary(pacman={'installed': ['atuin', 'steam']},
                      systemd={'active': ['mise-prune.timer'], 'results': {'mise-prune.service': {
                          'Result': 'exit-code', 'ExecMainStatus': '1', 'ExecMainExitTimestamp': '@1700000000'}}})
        report = self.health(1)
        self.check(report, 'ok', 'Packages', '1 listed packages installed')
        self.check(report, 'fail', 'Packages', 'MangoHud')
        self.check(report, 'fail', 'Background', 'mise-prune.service', 'exit-code', 'status 1')
        self.check(report, 'fail', 'Background', 'hypr-session-autosave.timer')
        # A package query that fails is a failure, never an empty "nothing missing".
        self.boundary(pacman={'broken': True})
        report = self.health(1)
        self.check(report, 'fail', 'Packages', 'pacman -T failed')
        self.assertFalse([check for check in report['checks'] if check['section'] == 'Packages'
                          and check['status'] == 'ok' and 'packages installed' in check['message']])

    def test_health_checks_recorded_homes_role_and_strict_exceptions(self):
        self.write('fleet/skills/provision-box/SKILL.md', 'provision')
        self.write('shared/skills.lock.json', '{"version":3,"skills":{}}')
        self.healthy_macos()
        report = self.health(0)
        self.check(report, 'ok', 'Apply receipt', 'completed')
        self.check(report, 'note', 'Managed files', 'role unknown')
        # A job that ran and failed is a failure, not a loaded agent.
        locked = self.home / 'Git/locked'
        locked.mkdir(parents=True)
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o755)
        self.assertNotEqual(self.launchd_job('dev.dstech.mise-prune').returncode, 0)
        self.check(self.health(1), 'fail', 'Background', 'dev.dstech.mise-prune')
        locked.chmod(0o755)
        self.assertEqual(self.launchd_job('dev.dstech.mise-prune').returncode, 0)

        # Instructions applied to another Codex home are checked from then on.
        work = self.home / '.codex-work'
        self.env['CODEX_HOME'] = str(work)
        self.cli('--only', 'agents,command-center')
        del self.env['CODEX_HOME']
        self.check(self.health(0), 'ok', 'Managed files', 'Codex ~/.codex, ~/.codex-work')
        (work / 'AGENTS.md').unlink()
        self.assertIn('files:~/.codex-work/AGENTS.md -> <repo>/.generated/agents/macos/AGENTS.md', self.warnings(self.health(0)))

        # Declared intent: a worker must not carry command-center skills, and
        # --strict fails on warnings until each is recorded as an exception.
        machine = self.write('.config/donnes-configs/machine.json', json.dumps({'role': 'worker'}), home=True)
        self.write('.codex-work/AGENTS.override.md', 'stale', home=True)
        self.check(self.health(0), 'warn', 'Managed files', 'command-center skills on a worker', '~/.agents/skills/provision-box')
        report = self.health(1, '--strict')
        warned = sorted(check['id'] for check in report['checks'] if check['status'] == 'fail')
        self.assertEqual(warned, ['agents-override:~/.codex-work/AGENTS.override.md', 'checkout:git',
                                  'files:~/.codex-work/AGENTS.md -> <repo>/.generated/agents/macos/AGENTS.md',
                                  'role:command-center-skills'])
        self.assertEqual(report['versions']['node'], '1.0.0')
        machine.write_text(json.dumps({'role': 'worker', 'exceptions': {id: 'kept on purpose' for id in warned}}))
        report = self.health(0, '--strict')
        self.assertEqual({check['id']: check['accepted'] for check in report['checks'] if 'accepted' in check},
                         {id: 'kept on purpose' for id in warned})

        # The last run's failure stays visible after the failing component.
        (self.repo / 'macos/agents/CONTEXT.md').unlink()
        self.fails('--only', 'agents')
        self.check(self.health(1), 'warn', 'Apply receipt', 'failed in agents')


if __name__ == '__main__':
    unittest.main()
