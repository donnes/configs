import * as fs from 'node:fs';
import * as path from 'node:path';
import * as p from '@clack/prompts';
import { children, exists, Files, realPath } from './files.ts';
import { answer, canPrompt } from './prompts.ts';

type Lock = Record<string, unknown> & { skills: Record<string, unknown> };

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function readLock(file: string): Lock {
  const value: unknown = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (!isObject(value) || !isObject(value.skills)) throw new Error(`${file}: expected a lockfile with a skills object`);
  return { ...value, skills: value.skills };
}

function writeLock(file: string, data: Lock) {
  // Write through the existing path, preserving links from other agents.
  fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n');
}

export class Skills {
  constructor(private files: Files) {}

  private sources() {
    return ['shared/skills', 'fleet/skills'].map(directory => path.join(this.files.repo, directory));
  }

  source(name: string) {
    const matches = this.sources().map(root => path.join(root, name)).filter(exists);
    if (matches.length > 1) throw new Error(`ambiguous tracked skill: ${name}`);
    return matches[0] ?? path.join(this.files.repo, 'shared/skills', name);
  }

  private agentRoots() {
    return [path.join(this.files.home, '.agents/skills'),
      path.join(process.env.CLAUDE_CONFIG_DIR || path.join(this.files.home, '.claude'), 'skills')];
  }

  private resolvedLink(file: string, seen = new Set<string>()): string | undefined {
    const existing = realPath(file);
    if (existing) return existing;
    const canonical = path.join(realPath(path.dirname(file)) ?? path.dirname(file), path.basename(file));
    if (seen.has(canonical)) return undefined;
    seen.add(canonical);
    const target = this.files.target(canonical);
    return target ? this.resolvedLink(path.resolve(path.dirname(canonical), target), seen) : canonical;
  }

  lockPath() {
    return process.env.XDG_STATE_HOME
      ? path.join(process.env.XDG_STATE_HOME, 'skills/.skill-lock.json')
      : path.join(this.files.home, '.agents/.skill-lock.json');
  }

  async syncLock() {
    const { repo, dryRun } = this.files;
    const tracked = path.join(repo, 'shared/skills.lock.json'), local = this.lockPath();
    if (this.files.target(local) === tracked) {
      this.files.log('skip', `${this.files.pretty(local)} already links to ${this.files.pretty(tracked)}`);
      return;
    }
    if (!exists(local)) { await this.files.link(tracked, local); return; }
    const repoLock = readLock(tracked), localLock = readLock(local);
    if (repoLock.version !== localLock.version) throw new Error('lockfile versions differ; migrate them before syncing');
    const merged = { ...repoLock };
    for (const [key, value] of Object.entries(localLock)) {
      const previous = repoLock[key];
      merged[key] = isObject(value) && isObject(previous) ? { ...previous, ...value } : value;
    }
    this.files.log('sync', `merge ${this.files.pretty(local)} into ${this.files.pretty(tracked)} (local values win)`);
    if (!dryRun && JSON.stringify(merged) !== JSON.stringify(repoLock)) writeLock(tracked, merged);
    this.files.log('relink', `${this.files.pretty(local)} -> ${this.files.pretty(tracked)}`);
    if (!dryRun) this.files.replaceWithLink(tracked, local);
  }

  private async collection(source: string, uninstall: boolean) {
    const entries = children(source).filter(entry => !path.basename(entry).startsWith('.'));
    if (!uninstall) for (const entry of entries) this.source(path.basename(entry));
    // Claude links may go through ~/.agents/skills, so process Codex first.
    for (const destination of this.agentRoots()) {
      if (!uninstall) this.files.pruneSkills(destination);
      for (const entry of entries) {
        const target = path.join(destination, path.basename(entry));
        if (!uninstall) await this.files.link(entry, target);
        // Do not traverse a directory link into the repo when removing legacy per-file links.
        else if (this.files.target(target) === entry) this.files.unlink(entry, target);
        else if (fs.statSync(entry, { throwIfNoEntry: false })?.isDirectory() && !this.files.target(target)) this.files.unlinkTree(entry, target);
      }
    }
  }

  async install() {
    await this.collection(path.join(this.files.repo, 'shared/skills'), false);
    await this.syncLock();
  }

  async uninstall() {
    await this.collection(path.join(this.files.repo, 'shared/skills'), true);
    this.files.unlink(path.join(this.files.repo, 'shared/skills.lock.json'), this.lockPath());
  }

  async commandCenter(uninstall: boolean) {
    await this.collection(path.join(this.files.repo, 'fleet/skills'), uninstall);
  }

  async remove(requested: string[]) {
    const { repo, home, dryRun } = this.files;
    const locks = new Map<string, Lock>();
    const candidates = [path.join(repo, 'shared/skills.lock.json'), path.join(home, '.agents/.skill-lock.json'), this.lockPath()];
    for (const file of candidates) {
      const target = realPath(file);
      if (target && !locks.has(target)) locks.set(target, readLock(target));
    }
    let names = [...new Set(requested)];
    const interactive = names.length === 0;
    if (interactive) {
      if (!canPrompt()) throw new Error('interactive removal requires a terminal; pass skill names instead');
      const available = new Set(this.sources().flatMap(children)
        .filter(file => !this.files.target(file) && fs.existsSync(path.join(file, 'SKILL.md'))).map(file => path.basename(file)));
      for (const lock of locks.values()) for (const name of Object.keys(lock.skills)) available.add(name);
      if (!available.size) { console.log('No tracked skills to remove.'); return; }
      names = answer(await p.multiselect({
        message: 'Select tracked skills to remove',
        options: [...available].sort().map(value => ({ value, label: value })), required: false,
      }));
      if (!names.length) { p.cancel('Removal cancelled.'); return; }
    }
    const directories: string[] = [], links = new Set<string>();
    const agentRoots = this.agentRoots();
    const roots = new Set([
      ...agentRoots,
      ...children(home).filter(file => path.basename(file).startsWith('.') && fs.statSync(file, { throwIfNoEntry: false })?.isDirectory()).map(file => path.join(file, 'skills')),
      ...children(path.join(home, '.config')).filter(file => fs.statSync(file, { throwIfNoEntry: false })?.isDirectory()).map(file => path.join(file, 'skills')),
    ]);
    for (const name of names) {
      if (!/^[A-Za-z0-9][A-Za-z0-9_.-]*$/.test(name)) throw new Error(`invalid skill name: ${name}`);
      const skill = this.source(name);
      if (this.files.target(skill)) throw new Error(`${skill}: refusing to delete a symlinked repo skill`);
      if (exists(skill) && (!fs.statSync(skill).isDirectory() || !fs.statSync(path.join(skill, 'SKILL.md'), { throwIfNoEntry: false })?.isFile())) {
        throw new Error(`${skill}: not a skill directory`);
      }
      if (!exists(skill) && ![...locks.values()].some(lock => Object.hasOwn(lock.skills, name))) throw new Error(`unknown tracked skill: ${name}`);
      if (exists(skill)) directories.push(skill);
      for (const root of roots) {
        const file = path.join(root, name);
        const target = this.files.target(file);
        const resolved = target ? this.resolvedLink(file) : undefined;
        if (target && resolved === skill) links.add(file);
        else if (fs.existsSync(file) && agentRoots.includes(root)) throw new Error(`${file}: unmanaged copy or link; sync it before removal`);
      }
    }
    // Preflight all names and lockfiles before any deletion.
    for (const file of [...links].sort()) this.files.log('unlink', this.files.pretty(file));
    for (const directory of directories) this.files.log('delete', this.files.pretty(directory));
    const changed = new Map<string, Lock>();
    for (const [file, lock] of locks) {
      const removed = names.filter(name => Object.hasOwn(lock.skills, name));
      if (!removed.length) continue;
      this.files.log('lock', `${this.files.pretty(file)}: remove ${removed.join(', ')}`);
      const skills = { ...lock.skills };
      for (const name of removed) delete skills[name];
      changed.set(file, { ...lock, skills });
    }
    if (dryRun) return;
    if (interactive && !answer(await p.confirm({ message: `Delete ${names.join(', ')} from the repository and agents?`, initialValue: false }))) {
      p.cancel('Removal cancelled.');
      return;
    }
    for (const file of links) fs.unlinkSync(file);
    for (const directory of directories) fs.rmSync(directory, { recursive: true });
    for (const [file, lock] of changed) writeLock(file, lock);
  }
}
