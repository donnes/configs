import * as fs from 'node:fs';
import * as path from 'node:path';
import { spawnSync } from 'node:child_process';
import * as p from '@clack/prompts';
import { answer, canPrompt } from './prompts.ts';

export function exists(file: string) {
  return fs.existsSync(file) || fs.lstatSync(file, { throwIfNoEntry: false }) !== undefined;
}

export function realPath(file: string) {
  return fs.existsSync(file) ? fs.realpathSync(file) : undefined;
}

export function within(file: string, root: string) {
  return file === root || file.startsWith(root + path.sep);
}

export function children(directory: string) {
  return fs.existsSync(directory) ? fs.readdirSync(directory).map(name => path.join(directory, name)) : [];
}

export function walk(directory: string): string[] {
  return children(directory).flatMap(file => {
    const stat = fs.lstatSync(file);
    return stat.isDirectory() ? walk(file) : stat.isFile() || stat.isSymbolicLink() ? [file] : [];
  });
}

export function run(command: string, args: string[], input?: string) {
  const result = spawnSync(command, args, {
    stdio: input === undefined ? 'inherit' : ['pipe', 'inherit', 'inherit'], input,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${command} failed (${result.signal ?? result.status})`);
}

export class Files {
  private keptPaths = new Set<string>();

  constructor(readonly repo: string, readonly home: string, readonly dryRun: boolean) {}

  pretty(file: string) {
    for (const [root, label] of [[this.repo, '<repo>'], [this.home, '~']]) {
      if (root !== undefined && within(file, root)) return label + file.slice(root.length);
    }
    return file;
  }

  log(kind: string, message: string) {
    console.log(`[${kind.padEnd(7)}] ${message}`);
  }

  target(file: string) {
    return fs.lstatSync(file, { throwIfNoEntry: false })?.isSymbolicLink() ? fs.readlinkSync(file) : undefined;
  }

  legacy(file: string) {
    const target = this.target(file);
    return target !== undefined && [path.join(this.home, '.syncode/repo'), '~/.syncode/repo'].some(root => within(target, root));
  }

  managed(file: string) {
    const target = this.target(file);
    return target !== undefined && (within(target, this.repo) || this.legacy(file));
  }

  private aliasesSource(source: string, destination: string) {
    const parent = realPath(path.dirname(destination));
    // Parent directory links can make these two paths the very same entry.
    if (parent && parent === realPath(path.dirname(source)) && path.basename(destination) === path.basename(source)) return true;
    const current = realPath(destination);
    return !this.target(destination) && current !== undefined && current === realPath(source);
  }

  replaceWithLink(source: string, destination: string) {
    if (this.aliasesSource(source, destination)) return;
    fs.rmSync(destination, { recursive: true, force: true });
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.symlinkSync(source, destination);
  }

  private differs(source: string, current: string, previewContent?: string) {
    if (previewContent !== undefined) return !fs.statSync(current).isFile() || fs.readFileSync(current, 'utf8') !== previewContent;
    const result = spawnSync('diff', ['-rq', '-x', '.DS_Store', source, current]);
    if (result.error) throw result.error;
    if (result.signal) throw new Error(`diff interrupted by ${result.signal}`);
    // Incompatible types and dangling links are conflicts too, not fatal errors.
    return result.status !== 0;
  }

  private latestMtime(file: string, visited = new Set<string>()): number {
    const real = realPath(file);
    if (!real || visited.has(real)) return 0;
    visited.add(real);
    const stat = fs.statSync(real);
    return stat.isDirectory()
      ? Math.max(0, ...children(real).filter(child => path.basename(child) !== '.DS_Store').map(child => this.latestMtime(child, visited)))
      : Math.floor(stat.mtimeMs / 1000) * 1000;
  }

  private async conflict(source: string, destination: string, current: string) {
    const localTime = this.latestMtime(current), repoTime = this.latestMtime(source);
    const newer = localTime > repoTime ? 'local is newer' : repoTime > localTime ? 'repo is newer' : 'same age';
    const description = `${this.pretty(destination)} differs from ${this.pretty(source)} (${newer})`;
    if (this.dryRun) { this.log('differs', `${description}; would ask`); return; }
    if (!canPrompt()) {
      this.log('keep', `${description}; rerun in a terminal to choose`);
      this.keptPaths.add(current);
      return;
    }
    // Generated instructions must be changed in their source documents.
    const canUpdate = within(source, this.repo) && !within(source, path.join(this.repo, '.generated'));
    p.log.info(`${description}\nLocal modified: ${new Date(localTime).toLocaleString()}\nRepo modified: ${new Date(repoTime).toLocaleString()}`);
    while (true) {
      const options = [
        { value: 'keep', label: 'Keep local copy' },
        { value: 'replace', label: 'Replace with repository copy' },
        ...(canUpdate ? [{ value: 'update', label: 'Update repository from local copy' }] : []),
        { value: 'diff', label: 'Show diff' },
      ];
      const choice = answer(await p.select({
        message: `Resolve ${this.pretty(destination)}`, options,
        initialValue: localTime > repoTime && canUpdate ? 'update' : repoTime > localTime ? 'replace' : 'keep',
      }));
      if (choice === 'diff') { spawnSync('diff', ['-ru', '-x', '.DS_Store', source, current], { stdio: 'inherit' }); continue; }
      this.log(choice, this.pretty(destination));
      if (choice === 'keep') { this.keptPaths.add(current); return; }
      if (choice === 'update') {
        if (fs.statSync(current).isDirectory()) fs.rmSync(source, { recursive: true, force: true });
        fs.cpSync(current, source, { recursive: true, preserveTimestamps: true, verbatimSymlinks: true, filter: file => path.basename(file) !== '.DS_Store' });
      }
      this.replaceWithLink(source, destination);
      return;
    }
  }

  async link(source: string, destination: string, assumeMissing = false, previewContent?: string) {
    const target = this.target(destination);
    if (this.aliasesSource(source, destination) || (!assumeMissing && target === source)) {
      this.log('skip', `${this.pretty(destination)} already resolves to ${this.pretty(source)}`);
      return;
    }
    const current = !assumeMissing && !this.managed(destination) ? realPath(destination) : undefined;
    if (current && current !== realPath(source) && this.differs(source, current, previewContent)) {
      if (this.keptPaths.has(current)) this.log('keep', `${this.pretty(destination)} local copy`);
      else await this.conflict(source, destination, current);
      return;
    }
    this.log(!assumeMissing && exists(destination) ? 'relink' : 'link', `${this.pretty(destination)} -> ${this.pretty(source)}`);
    if (!this.dryRun) this.replaceWithLink(source, destination);
  }

  async linkTree(source: string, destination: string, assumeMissing = false, skip = '') {
    for (const file of walk(source)) {
      const relative = path.relative(source, file);
      if (relative !== skip) await this.link(file, path.join(destination, relative), assumeMissing);
    }
  }

  unlink(source: string, destination: string) {
    if (this.target(destination) !== source) return;
    this.log('unlink', this.pretty(destination));
    if (!this.dryRun) fs.unlinkSync(destination);
  }

  unlinkTree(source: string, destination: string) {
    for (const file of walk(source)) this.unlink(file, path.join(destination, path.relative(source, file)));
  }

  pruneSkills(directory: string) {
    const agentRoot = realPath(path.join(this.home, '.agents/skills'));
    for (const file of children(directory)) {
      const target = this.target(file);
      if (!target || fs.existsSync(file)) continue;
      const parent = realPath(path.dirname(path.resolve(path.dirname(file), target)));
      if (!this.managed(file) && (!agentRoot || parent !== agentRoot)) continue;
      this.log('prune', `${this.pretty(file)} (target missing)`);
      if (!this.dryRun) fs.unlinkSync(file);
    }
  }

  block(file: string, content?: string, comment = '#') {
    const start = `${comment} >>> donnes/configs >>>`, end = `${comment} <<< donnes/configs <<<`;
    const original = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';
    if (content === undefined && !original.includes(start)) return;
    this.log(content === undefined ? 'remove' : 'append', `${content === undefined ? 'managed block from' : `${original.includes(start) ? 'replace' : 'add'} managed block in`} ${this.pretty(file)}`);
    if (this.dryRun) return;
    let skipping = false;
    const lines = original.split('\n').filter(line => {
      if (line === start) { skipping = true; return false; }
      if (skipping && line === end) { skipping = false; return false; }
      return !skipping;
    });
    if (content !== undefined) {
      while (lines.at(-1) === '') lines.pop();
      if (lines.length) lines.push('');
      lines.push(start, content, end, '');
    }
    fs.mkdirSync(path.dirname(file), { recursive: true });
    const temporary = `${file}.donnes-configs.${process.pid}`;
    const mode = fs.existsSync(file) ? fs.statSync(file).mode & 0o777 : 0o666 & ~process.umask();
    fs.writeFileSync(temporary, lines.join('\n'), { mode });
    fs.renameSync(temporary, file);
  }
}
