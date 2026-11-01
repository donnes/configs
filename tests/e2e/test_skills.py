"""Skills: the shared and command-center collections, remove-skill and the old skills lockfile link."""
import shutil
import unittest

from harness import CliTestCase


class SkillCollectionTests(CliTestCase):
    def test_prune_with_symlinked_home_preserves_foreign_dangling_links(self):
        alias = self.home.parent / 'home-alias'
        alias.symlink_to(self.home)
        self.env['HOME'] = str(alias)
        (self.repo / 'shared/skills').mkdir(exist_ok=True)
        agent = self.home / '.agents/skills/gone'
        agent.parent.mkdir(parents=True)
        agent.symlink_to(self.repo / 'shared/skills/gone')
        claude = self.home / '.claude/skills/gone'
        claude.parent.mkdir(parents=True)
        claude.symlink_to(alias / '.agents/skills/gone')
        foreign = claude.parent / 'foreign'
        foreign.symlink_to(self.home / 'missing/foreign')
        self.cli('--only', 'skills')
        self.assertFalse(agent.is_symlink())
        self.assertFalse(claude.is_symlink())
        self.assertTrue(foreign.is_symlink())

    def test_command_center_skills_are_opt_in_and_removable(self):
        managed = self.write('fleet/skills/provision-box/SKILL.md', 'provision').parent
        self.write('shared/skills/example/SKILL.md', 'shared')
        custom = self.home / '.claude-work'
        self.env['CLAUDE_CONFIG_DIR'] = str(custom)
        agent = self.home / '.agents/skills/provision-box'
        claude = custom / 'skills/provision-box'
        # The default selection, minus what needs a package manager or Omarchy.
        self.cli('--skip', 'packages,gh-extensions,agents,nvim,shell,tmux,git,session')
        self.assertFalse(agent.exists())
        self.assertEqual((custom / 'skills/example/SKILL.md').read_text(), 'shared')
        self.cli('--only', 'command-center', '--dry-run')
        self.assertFalse(agent.exists())
        self.cli('--only', 'command-center')
        self.assertEqual(agent.resolve(), managed)
        self.assertEqual(claude.resolve(), managed)
        self.cli('--only', 'skills')
        self.assertEqual(agent.resolve(), managed)
        self.assertEqual(claude.resolve(), managed)
        foreign = self.write('.agents/skills/foreign-manager/SKILL.md', 'foreign', home=True)
        self.write('fleet/skills/foreign-manager/SKILL.md', 'repository')
        self.cli('uninstall', '--only', 'command-center')
        self.assertFalse(agent.is_symlink())
        self.assertFalse(claude.is_symlink())
        self.assertEqual((managed / 'SKILL.md').read_text(), 'provision')
        self.assertEqual(foreign.read_text(), 'foreign')
        self.cli('--only', 'command-center')
        self.cli('remove-skill', 'provision-box')
        self.assertFalse(managed.exists())
        self.assertFalse(agent.is_symlink())
        self.assertFalse(claude.is_symlink())

    def test_personal_skills_install_alongside_shared_ones(self):
        personal = self.write('shared/skills/personal/mine/SKILL.md', 'mine').parent
        self.write('shared/skills/example/SKILL.md', 'shared')
        self.cli('--only', 'skills')
        for root in ['.agents/skills', '.claude/skills']:
            with self.subTest(root=root):
                self.assertEqual((self.home / root / 'mine').resolve(), personal)
                self.assertEqual((self.home / root / 'example/SKILL.md').read_text(), 'shared')
                self.assertFalse((self.home / root / 'personal').exists())
        self.write('shared/skills/mine/SKILL.md', 'duplicate')
        self.assertIn('ambiguous tracked skill: mine', self.fails('--only', 'skills').stderr)
        shutil.rmtree(self.repo / 'shared/skills/mine')
        self.cli('remove-skill', 'mine')
        self.assertFalse(personal.exists())
        self.assertFalse((self.home / '.agents/skills/mine').is_symlink())
        self.assertFalse((self.home / '.claude/skills/mine').is_symlink())

    def test_skill_collection_install_rejects_duplicate_names_before_linking(self):
        self.write('shared/skills/example/SKILL.md', 'shared')
        self.write('fleet/skills/example/SKILL.md', 'manager')
        for components in ['skills', 'command-center']:
            with self.subTest(components=components):
                result = self.fails('--only', components)
                self.assertIn('ambiguous tracked skill: example', result.stderr)
                self.assertFalse((self.home / '.agents').exists())
                self.assertFalse((self.home / '.claude').exists())

    def test_detached_command_center_skill_updates_its_original_collection(self):
        tracked = self.write('fleet/skills/provision-box/SKILL.md', 'initial').parent
        local = self.write('.agents/skills/provision-box/SKILL.md', 'updated', home=True).parent
        self.cli('update', str(local), '--dry-run')
        self.assertEqual((tracked / 'SKILL.md').read_text(), 'initial')
        self.cli('update', str(local))
        self.assertEqual((tracked / 'SKILL.md').read_text(), 'updated')
        self.assertEqual(local.resolve(), tracked)
        self.assertFalse((self.repo / 'shared/skills/provision-box').exists())

    def test_install_and_uninstall_remove_only_the_old_lockfile_link(self):
        (self.repo / 'shared/skills').mkdir(exist_ok=True)
        local = self.home / '.agents/.skill-lock.json'
        local.parent.mkdir(parents=True)
        local.symlink_to(self.repo / 'shared/skills.lock.json')
        self.cli('--only', 'skills', '--dry-run')
        self.assertTrue(local.is_symlink())
        self.cli('--only', 'skills')
        self.assertFalse(local.is_symlink())
        local.write_text('{"written":"by npx skills"}')
        self.cli('--only', 'skills')
        self.cli('uninstall', '--only', 'skills')
        self.assertEqual(local.read_text(), '{"written":"by npx skills"}')


class RemoveSkillTests(CliTestCase):
    def setUp(self):
        super().setUp()
        self.skill = self.write('shared/skills/example/SKILL.md', 'example').parent
        self.agent = self.home / '.agents/skills/example'
        self.agent.parent.mkdir(parents=True)
        self.agent.symlink_to(self.skill, target_is_directory=True)
        self.claude = self.home / '.claude/skills/example'
        self.claude.parent.mkdir(parents=True)
        self.claude.symlink_to(self.agent, target_is_directory=True)

    def test_dry_run_then_delete(self):
        self.cli('remove-skill', '--dry-run', 'example')
        self.assertTrue(self.skill.exists())
        self.assertTrue(self.agent.is_symlink())
        self.cli('remove-skill', 'example')
        self.assertFalse(self.skill.exists())
        self.assertFalse(self.agent.is_symlink())
        self.assertFalse(self.claude.is_symlink())

    def test_invalid_and_unknown_names_do_not_partially_delete(self):
        for name, diagnostic in [('../escape', 'invalid skill name'), ('unknown', 'unknown tracked skill'),
                                 ('*', 'invalid skill name')]:
            with self.subTest(name=name):
                result = self.fails('remove-skill', 'example', name)
                self.assertIn(diagnostic, result.stderr)
                self.assertEqual((self.skill / 'SKILL.md').read_text(), 'example')
                self.assertTrue(self.agent.is_symlink())
                self.assertTrue(self.claude.is_symlink())
        
    def test_foreign_copy_is_preserved(self):
        self.claude.unlink()
        self.claude.mkdir()
        (self.claude / 'SKILL.md').write_text('foreign')
        result = self.fails('remove-skill', 'example')
        self.assertIn('unmanaged copy or link', result.stderr)
        self.assertTrue(self.skill.exists())
        self.assertEqual((self.claude / 'SKILL.md').read_text(), 'foreign')

    def test_interactive_selection_and_confirmation(self):
        self.interactive(['remove-skill'], [
            ('Select tracked skills to remove', ' \x1b[B \r'),
            ('from the repository and agents?', 'y'),
        ])
        self.assertFalse(self.skill.exists())

    def test_interactive_cancel_and_dry_run(self):
        for exchanges, dry_run, code in [
            ([('Select tracked skills to remove', '\x03')], False, 130),
            ([('Select tracked skills to remove', ' \r'), ('from the repository and agents?', 'n')], False, 0),
            ([('Select tracked skills to remove', ' \r')], True, 0),
        ]:
            self.interactive(['remove-skill'] + (['--dry-run'] if dry_run else []), exchanges, code=code)
            self.assertTrue(self.skill.exists())
            self.assertTrue(self.agent.is_symlink())

    def test_no_names_without_terminal_gives_clear_error(self):
        result = self.fails('remove-skill')
        self.assertIn('requires a terminal', result.stderr)


if __name__ == '__main__':
    unittest.main()
