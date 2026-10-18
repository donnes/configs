import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { spawnSync, type SpawnSyncOptions } from 'node:child_process';
import { Files, within } from './files.ts';
import { apps, components, ghExtensions, Installer, opencodeVersion, type Component, type Profile } from './install.ts';

type Status = 'ok' | 'warn' | 'fail';

// Collects what an install would change instead of printing it.
class Recorder extends Files {
  readonly entries: [kind: string, message: string][] = [];
  override log(kind: string, message: string) { this.entries.push([kind, message]); }
}

// Preview entries that describe current state rather than a pending change.
// Agents and timers are reloaded on every install, so services() checks them directly.
const settled = new Set(['skip', 'package', 'load', 'enable']);
const legacyManagers = ['fnm', 'nvm', 'pyenv', 'rbenv', 'asdf', 'volta'];
const executables: Record<string, string> = { 'aws-cli': 'aws' };

function capture(command: string, args: string[], options: SpawnSyncOptions = {}) {
  const result = spawnSync(command, args, { ...options, encoding: 'utf8' });
  return { ok: !result.error && result.status === 0, stdout: String(result.stdout ?? ''), stderr: String(result.stderr ?? '') };
}

// Omarchy installs ~/.local/bin wrappers that run its agent CLIs through `mise x`.
function delegatesToMise(file: string) {
  const stat = fs.statSync(file, { throwIfNoEntry: false });
  return stat !== undefined && stat.size < 4096 && /^exec mise (x|exec) /m.test(fs.readFileSync(file, 'utf8'));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

export class Health {
  private counts: Record<Status, number> = { ok: 0, warn: 0, fail: 0 };
  private files: Files;

  constructor(private repo: string, private home: string, private profile: Profile) {
    this.files = new Files(repo, home, true);
  }

  private report(status: Status, message: string) {
    this.counts[status]++;
    console.log(`[${status.padEnd(7)}] ${message}`);
  }

  private section(title: string) {
    console.log(`\n${title}`);
  }

  private miseData() {
    return process.env.MISE_DATA_DIR || path.join(process.env.XDG_DATA_HOME || path.join(this.home, '.local/share'), 'mise');
  }

  private system() {
    this.section('System');
    this.report('ok', `${this.profile} profile on ${os.hostname()} (${os.type()} ${os.release()} ${os.arch()})`);
    const status = capture('git', ['-C', this.repo, 'status', '--porcelain']);
    if (!status.ok) this.report('warn', `${this.repo} is not a git checkout`);
    else if (status.stdout.trim()) this.report('warn', 'configs checkout has uncommitted changes');
    else this.report('ok', 'configs checkout is clean');
    // Compares against the last fetch, so this stays offline.
    const behind = Number(capture('git', ['-C', this.repo, 'rev-list', '--count', 'HEAD..@{upstream}']).stdout.trim());
    if (behind > 0) this.report('warn', `configs checkout is ${behind} commit${behind === 1 ? '' : 's'} behind its upstream; run git pull`);
  }

  private async configs() {
    this.section('Managed files');
    const recorder = new Recorder(this.repo, this.home, true);
    const excluded: Component[] = ['packages', 'apps', 'command-center', 'rea'];
    try {
      await new Installer(recorder, this.profile, new Set(components.filter(component => !excluded.includes(component)))).apply(false);
    } catch (error) {
      this.report('fail', `install preview failed: ${error instanceof Error ? error.message : String(error)}`);
      return;
    }
    const pending = recorder.entries.filter(([kind]) => !settled.has(kind));
    if (!pending.length) this.report('ok', 'managed files match the repository');
    for (const [kind, message] of pending) this.report('warn', `${kind}: ${message}`);
    if (pending.length) console.log('          run ./cli --dry-run to review, then ./cli to apply');
  }

  private packages() {
    this.section('Packages');
    const opencode = opencodeVersion(this.home);
    if (opencode?.startsWith('2.')) this.report('ok', `opencode ${opencode} installed`);
    else this.report('fail', `${opencode ? `opencode ${opencode} is not v2` : 'opencode v2 is not installed'}; run ./cli --only packages`);
    const extensions = fs.readFileSync(path.join(this.repo, 'packages/gh-extensions.txt'), 'utf8').split(/\s+/).filter(Boolean);
    const installed = ghExtensions();
    const absent = extensions.filter(repo => !installed.has(repo));
    if (absent.length) this.report('fail', `missing gh extensions: ${absent.join(' ')}; run ./cli --only packages`);
    else this.report('ok', `${extensions.length} listed gh extensions installed`);
    if (this.profile === 'omarchy') {
      const wanted = fs.readFileSync(path.join(this.repo, 'packages/omarchy.txt'), 'utf8').split(/\s+/).filter(Boolean);
      const missing = capture('pacman', ['-T', ...wanted]).stdout.split('\n').filter(Boolean);
      if (missing.length) this.report('fail', `missing packages: ${missing.join(' ')}; run ./cli --only packages`);
      else this.report('ok', `${wanted.length} listed packages installed`);
      const incomplete = apps.flatMap(({ name, packages }) => {
        const absent = capture('pacman', ['-T', ...packages]).stdout.split('\n').filter(Boolean);
        return absent.length ? [`${name} (${absent.join(' ')})`] : [];
      });
      if (incomplete.length) this.report('fail', `missing apps: ${incomplete.join(', ')}; run ./cli --only apps`);
      else this.report('ok', `${apps.length} Omarchy apps installed`);
      return;
    }
    const brew = ['brew', '/opt/homebrew/bin/brew', '/usr/local/bin/brew'].find(command => capture(command, ['--prefix']).ok);
    if (!brew) { this.report('fail', 'Homebrew is not installed; run ./cli --only packages'); return; }
    for (const [list, flag, kind] of [['macos.txt', '--formula', 'formulae'], ['macos-casks.txt', '--cask', 'casks']] as const) {
      const installed = new Set(capture(brew, ['list', flag, '-1']).stdout.split('\n'));
      const wanted = fs.readFileSync(path.join(this.repo, 'packages', list), 'utf8').split(/\s+/).filter(Boolean);
      const missing = wanted.filter(name => !installed.has(path.basename(name)));
      if (missing.length) this.report('fail', `missing Homebrew ${kind}: ${missing.join(' ')}; run ./cli --only packages`);
      else this.report('ok', `${wanted.length} listed Homebrew ${kind} installed`);
    }
  }

  private mise() {
    this.section('mise');
    if (!capture('mise', ['--version']).ok) { this.report('fail', 'mise is not installed'); return []; }
    let listing: unknown;
    try {
      listing = JSON.parse(capture('mise', ['ls', '--current', '--json'], { cwd: this.home }).stdout);
    } catch {
      this.report('fail', 'mise ls returned invalid JSON; run mise doctor');
      return [];
    }
    if (!isRecord(listing)) { this.report('fail', 'mise ls returned an unexpected shape'); return []; }
    const tools = Object.keys(listing);
    const missing = tools.filter(tool => {
      const versions = listing[tool];
      return Array.isArray(versions) && versions.some(version => isRecord(version) && version.installed === false);
    });
    if (missing.length) this.report('fail', `not installed: ${missing.join(' ')}; run mise install`);
    else this.report('ok', `${tools.length} configured tools installed`);
    return tools;
  }

  // Resolves tools the way a new terminal does: macOS terminals start login
  // shells, Omarchy's start interactive ones. The clean environment keeps this
  // process's PATH from hiding problems in the startup files.
  private shell(tools: string[]) {
    const shell = os.userInfo().shell || (this.profile === 'macos' ? '/bin/zsh' : '/bin/bash');
    this.section(`Shell (${path.basename(shell)})`);
    const names = tools.filter(tool => !tool.includes(':')).map(tool => executables[tool] ?? tool);
    const script = [
      '__donnes_path() { if [ -n "$ZSH_VERSION" ]; then whence -p "$1"; else type -P "$1"; fi; }',
      'mise doctor >/dev/null 2>&1; printf "\\n@@doctor %s\\n" "$?"',
      `for name in ${names.join(' ')}; do printf "@@bin %s %s\\n" "$name" "$(__donnes_path "$name")"; done`,
      'printf "@@opencode %s\\n" "$(__donnes_path opencode)"',
      `for name in ${legacyManagers.join(' ')}; do type "$name" >/dev/null 2>&1 && printf "@@legacy %s\\n" "$name"; done`,
      'true',
    ].join('\n');
    const env = Object.fromEntries(['HOME', 'USER', 'LOGNAME', 'TERM', 'LANG']
      .flatMap(name => process.env[name] === undefined ? [] : [[name, process.env[name]]]));
    const result = capture(shell, [process.platform === 'darwin' ? '-lic' : '-ic', script],
      { cwd: this.home, timeout: 60_000, env: { ...env, HOME: this.home, SHELL: shell } });
    const lines = result.stdout.split('\n').filter(line => line.startsWith('@@')).map(line => line.split(' '));
    const doctor = lines.find(([kind]) => kind === '@@doctor')?.[1];
    if (doctor === undefined) {
      this.report('fail', `${shell} did not finish starting: ${result.stderr.trim().split('\n').at(-1) ?? 'no output'}`);
      return;
    }
    if (doctor === '0') this.report('ok', 'mise doctor found no problems');
    else this.report('fail', 'mise doctor found problems; run mise doctor');
    const data = this.miseData();
    let resolved = 0;
    for (const [kind, name, ...rest] of lines) {
      if (kind !== '@@bin' || !name) continue;
      const file = rest.join(' ') && path.resolve(rest.join(' '));
      if (!file) this.report('fail', `${name} is not on PATH`);
      else if (!within(file, data) && !delegatesToMise(file)) this.report('warn', `${name} resolves to ${this.files.pretty(file)} instead of mise`);
      else resolved++;
    }
    if (resolved) this.report('ok', `${resolved} tools resolve through mise`);
    this.globals(names);
    const opencode = lines.find(([kind]) => kind === '@@opencode')?.slice(1).join(' ');
    const expected = path.join(this.home, '.opencode/bin/opencode');
    if (opencode && path.resolve(opencode) === expected) this.report('ok', 'opencode resolves to its v2 install');
    else this.report('warn', `opencode resolves to ${opencode ? this.files.pretty(path.resolve(opencode)) : 'nothing'} instead of ${this.files.pretty(expected)}`);
    const leftovers = lines.filter(([kind]) => kind === '@@legacy').map(([, name]) => `${name} is still on PATH`);
    for (const [name, directory] of [
      ['nvm', '.nvm'], ['pyenv', '.pyenv'], ['rbenv', '.rbenv'], ['asdf', '.asdf'], ['volta', '.volta'],
      ['fnm', '.local/share/fnm'], ['fnm', 'Library/Application Support/fnm'],
    ] as const) {
      const file = path.join(this.home, directory);
      if (fs.existsSync(file)) leftovers.push(`${this.files.pretty(file)} is left over from ${name}`);
    }
    for (const leftover of leftovers) this.report('warn', leftover);
    if (!leftovers.length) this.report('ok', 'no other version managers found');
  }

  // bun and pnpm install themselves, and their global packages, into these
  // directories. A copy of a mise tool there is a stale duplicate, even when
  // mise's comes first on PATH.
  private globals(names: string[]) {
    const directories = [
      path.join(process.env.BUN_INSTALL || path.join(this.home, '.bun'), 'bin'),
      process.env.PNPM_HOME || path.join(this.home, this.profile === 'macos' ? 'Library/pnpm' : '.local/share/pnpm'),
    ];
    const duplicates = directories.flatMap(directory => names.map(name => path.join(directory, name)).filter(file => fs.existsSync(file)));
    for (const file of duplicates) this.report('warn', `${this.files.pretty(file)} duplicates the mise tool; remove it`);
    if (!duplicates.length) this.report('ok', 'no global bun or pnpm copies of mise tools');
  }

  private services() {
    this.section('Background jobs');
    if (this.profile === 'omarchy') {
      for (const [timer, component] of [['mise-prune.timer', 'mise'], ['hypr-session-autosave.timer', 'session']] as const) {
        if (capture('systemctl', ['--user', 'is-active', '--quiet', timer]).ok) this.report('ok', `${timer} is active`);
        else this.report('fail', `${timer} is not active; run ./cli --only ${component}`);
      }
      return;
    }
    const uid = process.getuid?.();
    for (const label of ['dev.dstech.guipath', 'dev.dstech.mise-prune']) {
      if (capture('launchctl', ['print', `gui/${uid}/${label}`]).ok) this.report('ok', `launchd agent ${label} is loaded`);
      else this.report('fail', `launchd agent ${label} is not loaded; run ./cli --only mise`);
    }
    if (capture('launchctl', ['getenv', 'PATH']).stdout.includes(path.join(this.miseData(), 'shims'))) {
      this.report('ok', 'GUI apps get mise shims on PATH');
    } else this.report('warn', 'GUI apps do not have mise shims on PATH yet; log out and back in');
  }

  async run() {
    this.system();
    await this.configs();
    this.packages();
    this.shell(this.mise());
    this.services();
    const { ok, warn, fail } = this.counts;
    console.log(`\n${ok} ok, ${warn} warning${warn === 1 ? '' : 's'}, ${fail} failure${fail === 1 ? '' : 's'}`);
    return fail === 0;
  }
}
