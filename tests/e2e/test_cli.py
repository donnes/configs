"""The command surface: receipts, interactive selection, the piped bootstrap and cancellation."""
import json
import unittest

from harness import CliTestCase


class CliTests(CliTestCase):
    def test_install_records_a_receipt_that_distinguishes_partial_runs(self):
        self.write('shared/agents/global/AGENTS.md', 'instructions')
        head = self.commit()
        receipt = self.home / '.local/state/donnes-configs/receipt.json'
        self.cli('--only', 'agents', '--dry-run')
        self.assertFalse(receipt.exists())
        self.boundary(mise={'ls': {'node': [{'version': '24.22.0', 'installed': True}]}})
        self.cli('--only', 'agents')
        data = json.loads(receipt.read_text())
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
        self.assertEqual({key: data['lastRun'][key] for key in ['revision', 'dirty', 'components', 'outcome']},
                         {'revision': head, 'dirty': False, 'components': ['agents'], 'outcome': 'complete'})
        self.assertEqual(data['components']['agents']['revision'], head)
        self.assertEqual(data['runtimeHomes'], {'codex': [str(self.home / '.codex')], 'claude': [str(self.home / '.claude')]})
        self.assertEqual(data['tools'], {'node': '24.22.0'})

        # A differing local copy is kept unattended, so the run is not complete.
        (self.home / '.codex/AGENTS.md').unlink()
        self.write('.codex/AGENTS.md', 'local edit', home=True)
        self.write('shared/agents/global/AGENTS.md', 'changed instructions')
        self.cli('--only', 'agents')
        data = json.loads(receipt.read_text())
        self.assertEqual(data['lastRun']['outcome'], 'kept-conflicts')
        self.assertEqual(data['lastRun']['kept'], ['~/.codex/AGENTS.md'])
        self.assertTrue(data['lastRun']['dirty'])
        self.assertTrue(data['components']['agents']['keptConflicts'])
        applied = data['components']['agents']

        # A failed component keeps its last successful record.
        (self.repo / 'macos/agents/CONTEXT.md').unlink()
        self.fails('--only', 'agents,skills')
        data = json.loads(receipt.read_text())
        self.assertEqual({key: data['lastRun'].get(key) for key in ['outcome', 'failed']}, {'outcome': 'failed', 'failed': 'agents'})
        self.assertIn('CONTEXT.md', data['lastRun']['error'])
        self.assertEqual(data['components']['agents'], applied)
        self.assertNotIn('skills', data['components'])

    def test_component_that_fails_late_keeps_its_last_successful_receipt(self):
        self.write('macos/zshrc', '# zsh')
        self.write('shared/git/ignore', '.scratch/\n')
        self.write('macos/gitconfig', '[pull]\n\trebase = true\n')
        self.commit()
        receipt = self.home / '.local/state/donnes-configs/receipt.json'
        self.cli('--only', 'shell,git')
        applied = json.loads(receipt.read_text())['components']
        head = self.commit('next')
        # ~/.zshrc is linked before shell reaches the malformed ~/.zshenv, and the
        # shared git ignore would come before the macOS gitconfig include.
        (self.home / '.zshrc').unlink()
        (self.home / '.config/git/ignore').unlink()
        (self.home / '.zshenv').write_text('# >>> donnes/configs >>>\nx\n')
        self.fails('--only', 'shell,git')
        data = json.loads(receipt.read_text())
        self.assertEqual({key: data['lastRun'].get(key) for key in ['revision', 'outcome', 'failed']},
                         {'revision': head, 'outcome': 'failed', 'failed': 'shell'})
        self.assertEqual({name: data['components'][name] for name in ['shell', 'git']}, applied)

    def test_interactive_component_selection_and_cancellation(self):
        source = self.write('shared/agents/global/AGENTS.md', 'instructions')
        self.interactive(['--interactive'], [('Select components to install', '\x03')], code=130)
        self.assertFalse((self.home / '.codex/AGENTS.md').exists())
        # Select all, clear all, then choose agents, the third component.
        self.interactive(['--interactive'], [('Select components to install', 'aa\x1b[B\x1b[B \r')])
        self.assertIn(source.read_text(), (self.home / '.codex/AGENTS.md').read_text())
        self.assertFalse((self.home / '.agents').exists())

    def test_piped_bootstrap_can_choose_components(self):
        source = self.write('shared/agents/global/AGENTS.md', 'instructions')
        canonical = self.home / '.donnes/configs'
        canonical.parent.mkdir(parents=True)
        self.repo.rename(canonical)
        source = canonical / source.relative_to(self.repo)
        self.repo = canonical
        (canonical / '.git').mkdir()
        self.interactive(['--interactive'], [('Select components to install', 'aa\x1b[B\x1b[B \r')], piped=True)
        self.assertIn(source.read_text(), (self.home / '.codex/AGENTS.md').read_text())
        self.assertFalse((self.home / '.agents').exists())


if __name__ == '__main__':
    unittest.main()
