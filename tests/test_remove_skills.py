import json
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


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
        shutil.copy(ROOT / 'install', self.repo / 'install')
        shutil.copytree(ROOT / 'scripts', self.repo / 'scripts')
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
        return subprocess.run(['bash', str(self.repo / 'install'), 'remove-skill', *args],
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
        for name in ('../escape', 'unknown', '*'):
            result = self.run_command('example', name)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(self.skill.exists())
            self.assertTrue(self.agent.is_symlink())

    def test_foreign_copy_is_preserved(self):
        self.claude.unlink()
        self.claude.mkdir()
        (self.claude / 'SKILL.md').write_text('foreign')
        result = self.run_command('example')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.skill.exists())
        self.assertEqual((self.claude / 'SKILL.md').read_text(), 'foreign')

    def test_stale_lock_entry_can_be_removed(self):
        result = self.run_command('keep')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.lock.read_text())['skills'], {'example': {}})

    def interactive(self, replies, dry_run=False):
        spec = importlib.util.spec_from_file_location('remove_skills', ROOT / 'scripts/remove-skills.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        stream = io.StringIO(replies)
        argv = ['remove-skills', str(self.repo)] + (['--dry-run'] if dry_run else [])
        output = io.StringIO()
        with patch.dict(os.environ, self.env, clear=True), patch.object(sys, 'argv', argv), \
                patch.object(sys, 'stdin', stream), patch.object(stream, 'isatty', return_value=True), \
                patch.object(sys, 'stdout', output):
            module.main()
        return output.getvalue()

    def test_interactive_selection_and_confirmation(self):
        output = self.interactive('99\n1,2\ny\n')
        self.assertIn('Choose numbers from the list.', output)
        self.assertFalse(self.skill.exists())
        self.assertEqual(json.loads(self.lock.read_text())['skills'], {})

    def test_interactive_cancel_and_dry_run(self):
        for replies, dry_run in [('\n', False), ('1\nn\n', False), ('1\n', True)]:
            self.interactive(replies, dry_run)
            self.assertTrue(self.skill.exists())
            self.assertTrue(self.agent.is_symlink())
            self.assertIn('example', json.loads(self.lock.read_text())['skills'])

    def test_no_names_without_terminal_gives_clear_error(self):
        result = self.run_command()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires a terminal', result.stderr)


if __name__ == '__main__':
    unittest.main()
