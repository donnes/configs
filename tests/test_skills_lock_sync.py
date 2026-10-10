import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from cli_fixture import copy_cli

class SkillsLockSyncTests(unittest.TestCase):
    def test_install_preserves_detached_local_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            repo = root / 'repo'
            home = root / 'home'
            (repo / 'shared').mkdir(parents=True)
            (home / '.agents').mkdir(parents=True)
            copy_cli(repo)
            tracked = repo / 'shared/skills.lock.json'
            local = home / '.agents/.skill-lock.json'
            tracked.write_text(json.dumps({'version': 3, 'skills': {'repo': {'source': 'repo'}, 'common': {'source': 'old'}}}))
            local.write_text(json.dumps({'version': 3, 'skills': {'local': {'source': 'local'}, 'common': {'source': 'new'}}, 'dismissed': {'notice': True}}))
            env = dict(os.environ, HOME=str(home), DONNES_CONFIGS_PROFILE='macos')
            env.pop('XDG_STATE_HOME', None)
            command = ['bash', str(repo / 'cli'), '--only', 'skills']
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            merged = json.loads(tracked.read_text())
            self.assertEqual(set(merged['skills']), {'repo', 'local', 'common'})
            self.assertEqual(merged['skills']['common']['source'], 'new')
            self.assertTrue(merged['dismissed']['notice'])
            self.assertTrue(local.is_symlink())
            self.assertEqual(json.loads(local.read_text()), merged)
            self.assertFalse(list(local.parent.glob('.skill-lock.json.backup.*')))
            before = tracked.read_bytes()
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(tracked.read_bytes(), before)

            # Simulate a CLI saving via rename, which replaces the symlink.
            replacement = local.with_suffix('.tmp')
            replacement.write_text(json.dumps({'version': 3, 'skills': {'added': {'source': 'added'}}}))
            replacement.replace(local)
            detached = local.read_bytes()
            sync = ['bash', str(repo / 'cli'), 'update', str(local)]
            result = subprocess.run(sync + ['--dry-run'], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(local.read_bytes(), detached)
            self.assertFalse(local.is_symlink())
            self.assertEqual(tracked.read_bytes(), before)
            result = subprocess.run(sync, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(local.is_symlink())
            self.assertIn('added', json.loads(tracked.read_text())['skills'])

            # The update alias is harmless when already linked.
            result = subprocess.run(['bash', str(repo / 'cli'), 'update', str(local)], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

            state = home / 'state'
            xdg_lock = state / 'skills/.skill-lock.json'
            xdg_lock.parent.mkdir(parents=True)
            xdg_lock.write_text('{invalid')
            env['XDG_STATE_HOME'] = str(state)
            sync = ['bash', str(repo / 'cli'), 'update', str(xdg_lock)]
            before = tracked.read_bytes()
            result = subprocess.run(sync, env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(tracked.read_bytes(), before)
            self.assertEqual(xdg_lock.read_text(), '{invalid')
            self.assertFalse(xdg_lock.is_symlink())
            xdg_lock.write_text(json.dumps({'version': 99, 'skills': {}}))
            invalid_version = xdg_lock.read_bytes()
            result = subprocess.run(sync, env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('lockfile versions differ', result.stderr)
            self.assertEqual(tracked.read_bytes(), before)
            self.assertEqual(xdg_lock.read_bytes(), invalid_version)
            self.assertFalse(xdg_lock.is_symlink())
            xdg_lock.write_text(json.dumps({'version': 3, 'skills': {'xdg': {}}}))
            result = subprocess.run(sync, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(xdg_lock.is_symlink())
            self.assertIn('xdg', json.loads(tracked.read_text())['skills'])


if __name__ == '__main__':
    unittest.main()
