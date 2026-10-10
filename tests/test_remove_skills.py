import json
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest
from cli_fixture import copy_cli, interactive_cli

class RemoveSkillsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.repo = self.root / 'repo'
        self.home = self.root / 'home'
        self.skill = self.repo / 'shared/skills/example'
        self.skill.mkdir(parents=True)
        (self.skill / 'SKILL.md').write_text('example')
        copy_cli(self.repo)
        self.lock = self.repo / 'shared/skills.lock.json'
        self.lock.write_text(json.dumps({'version': 3, 'skills': {'example': {}, 'keep': {}}}))
        self.agent = self.home / '.agents/skills/example'
        self.agent.parent.mkdir(parents=True)
        self.agent.symlink_to(self.skill, target_is_directory=True)
        (self.home / '.agents/.skill-lock.json').symlink_to(self.lock)
        self.claude = self.home / '.claude/skills/example'
        self.claude.parent.mkdir(parents=True)
        self.claude.symlink_to(self.agent, target_is_directory=True)
        self.env = dict(os.environ, HOME=str(self.home), DONNES_CONFIGS_PROFILE='macos')
        self.env.pop('XDG_STATE_HOME', None)

    def run_command(self, *args):
        return subprocess.run(['bash', str(self.repo / 'cli'), 'remove-skill', *args],
                              env=self.env, capture_output=True, text=True)

    def test_dry_run_then_delete(self):
        before = self.lock.read_bytes()
        result = self.run_command('--dry-run', 'example')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.skill.exists())
        self.assertTrue(self.agent.is_symlink())
        self.assertEqual(self.lock.read_bytes(), before)
        result = self.run_command('example')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.skill.exists())
        self.assertFalse(self.agent.is_symlink())
        self.assertFalse(self.claude.is_symlink())
        self.assertEqual(json.loads(self.lock.read_text())['skills'], {'keep': {}})
        self.assertTrue((self.home / '.agents/.skill-lock.json').is_symlink())

    def test_invalid_and_unknown_names_do_not_partially_delete(self):
        before = self.lock.read_bytes()
        for name, diagnostic in [('../escape', 'invalid skill name'),
                                 ('unknown', 'unknown tracked skill'),
                                 ('*', 'invalid skill name')]:
            with self.subTest(name=name):
                result = self.run_command('example', name)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(diagnostic, result.stderr)
                self.assertEqual((self.skill / 'SKILL.md').read_text(), 'example')
                self.assertTrue(self.agent.is_symlink())
                self.assertTrue(self.claude.is_symlink())
                self.assertEqual(self.lock.read_bytes(), before)

    def test_foreign_copy_is_preserved(self):
        self.claude.unlink()
        self.claude.mkdir()
        (self.claude / 'SKILL.md').write_text('foreign')
        result = self.run_command('example')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unmanaged copy or link', result.stderr)
        self.assertTrue(self.skill.exists())
        self.assertEqual((self.claude / 'SKILL.md').read_text(), 'foreign')

    def test_stale_lock_entry_can_be_removed(self):
        result = self.run_command('keep')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.lock.read_text())['skills'], {'example': {}})
        shutil.rmtree(self.skill)
        result = self.run_command('example')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.agent.is_symlink())
        self.assertFalse(self.claude.is_symlink())
        self.assertEqual(json.loads(self.lock.read_text())['skills'], {})

    def test_interactive_selection_and_confirmation(self):
        interactive_cli(self.repo, self.env, ['remove-skill'], [
            ('Select tracked skills to remove', ' \x1b[B \r'),
            ('from the repository and agents?', 'y'),
        ])
        self.assertFalse(self.skill.exists())
        self.assertEqual(json.loads(self.lock.read_text())['skills'], {})

    def test_interactive_cancel_and_dry_run(self):
        for exchanges, dry_run, code in [
            ([('Select tracked skills to remove', '\x03')], False, 130),
            ([('Select tracked skills to remove', ' \r'), ('from the repository and agents?', 'n')], False, 0),
            ([('Select tracked skills to remove', ' \r')], True, 0),
        ]:
            interactive_cli(self.repo, self.env, ['remove-skill'] + (['--dry-run'] if dry_run else []),
                            exchanges, expected_code=code)
            self.assertTrue(self.skill.exists())
            self.assertTrue(self.agent.is_symlink())
            self.assertIn('example', json.loads(self.lock.read_text())['skills'])

    def test_no_names_without_terminal_gives_clear_error(self):
        result = self.run_command()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires a terminal', result.stderr)


if __name__ == '__main__':
    unittest.main()
