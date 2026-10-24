import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { spawnSync, type SpawnSyncOptions } from 'node:child_process';
import { children, Files, realPath, within } from './files.ts';
import {
  apps, components, ghExtensions, Installer, listed, missingHomebrew, missingPacman, opencodeVersion, runtimeHomes, t3code, hyperframes,
  type Component, type Profile, type RuntimeHomes,
} from './install.ts';
import { miseCurrent, miseFragments, vitePlusHome, vitePlusScopes, type MiseTool } from './mise.ts';
import { checkoutState, machinePath, readMachine, readReceipt, receiptPath, type Machine, type Receipt, type Role } from './state.ts';

type Status = 'ok' | 'warn' | 'fail';
type Check = { section: string, status: Status | 'note', id?: string, message: string, accepted?: string };
export type HealthOptions = { json: boolean, strict: boolean };

// Collects what an install would change instead of printing it.
class Recorder extends Files {
  readonly entries: [kind: string, message: string][] = [];
  override log(kind: string, message: string) { this.entries.push([kind, message]); }
}

// Preview entries that describe current state rather than a pending change.
// Agents and timers are reloaded on every install, so services() checks them directly.
const settled = new Set(['skip', 'package', 'load', 'enable']);
const legacyManagers = ['fnm', 'nvm', 'pyenv', 'rbenv', 'asdf', 'volta'];
// Tools whose executable differs from their mise name. Backend-qualified tools
// need an entry here; health reports any that lack one rather than skip them.
const executables: Record<string, string> = {
  'aws-cli': 'aws', 'npm:cf': 'cf', 'github:voidzero-dev/vite-plus': 'vp', rust: 'rustfmt',
  'github:realm/SwiftLint': 'swiftlint', 'aqua:ktlint/ktlint': 'ktlint', 'github:detekt/detekt': 'detekt',
};
const hour = 3_600_000;
// Jobs with their expected interval, for spotting ones that stopped running.
const launchdJobs = [['dev.dstech.guipath', undefined], ['dev.dstech.mise-prune', 50 * hour]] as const;
const systemdJobs = [['mise-prune', 'mise', 50 * hour], ['hypr-session-autosave', 'session', 15 * 60_000]] as const;

function capture(command: string, args: string[], options: SpawnSyncOptions = {}) {
  const result = spawnSync(command, args, { ...options, encoding: 'utf8' });
  return { ok: !result.error && result.status === 0, stdout: String(result.stdout ?? ''), stderr: String(result.stderr ?? '') };
}

// Omarchy installs ~/.local/bin wrappers that run its agent CLIs through `mise x`.
function delegatesToMise(file: string) {
  const stat = fs.statSync(file, { throwIfNoEntry: false });
  return stat !== undefined && stat.size < 4096 && /^exec mise (x|exec) /m.test(fs.readFileSync(file, 'utf8'));
}

function message(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

function ago(time: number) {
  const hours = (Date.now() - time) / hour;
  return hours < 1 ? `${Math.round(hours * 60)} min ago` : hours < 48 ? `${Math.round(hours)} h ago` : `${Math.round(hours / 24)} days ago`;
}

// The versions a fragment requests, from its [tools] table.
function requested(fragment: string) {
  if (!fs.existsSync(fragment)) return new Map<string, string>();
  const tools = fs.readFileSync(fragment, 'utf8').split(/^\[(?!tools\])/m)[0]?.split(/^\[tools\]$/m)[1] ?? '';
  return new Map([...tools.matchAll(/^"?([^"=\s]+)"?\s*=\s*(?:"([^"]+)"|\{\s*version\s*=\s*"([^"]+)")/gm)]
    .flatMap(([, tool, version, table]) => tool && (version ?? table) ? [[tool, version ?? table ?? '']] : []));
}

export class Health {
  private checks: Check[] = [];
  private current = '';
  private files: Files;
  private machine?: Machine;
  private receipt?: Receipt;
  private role?: Role;
  private versions: Record<string, string> = {};
  private matched = new Set<string>();

  constructor(private repo: string, private home: string, private profile: Profile, private options: HealthOptions) {
    this.files = new Files(repo, home, true);
  }

  // Warnings listed in machine.json's exceptions are accepted with their
  // reason; --strict turns the remaining warnings into failures.
  private report(status: Status | 'note', message: string, id?: string) {
    const check: Check = { section: this.current, status, message, ...(id && { id }) };
    const reason = id === undefined ? undefined : this.machine?.exceptions[id];
    if (status === 'warn' && id !== undefined && reason !== undefined) {
      this.matched.add(id);
      Object.assign(check, { status: 'ok', accepted: reason });
    } else if (status === 'warn' && this.options.strict) check.status = 'fail';
    this.checks.push(check);
    if (this.options.json) return;
    const label = check.accepted !== undefined ? 'accept' : check.status;
    const suffix = check.accepted !== undefined ? ` (${check.accepted})` : status === 'warn' && this.options.strict ? ` [strict; exception id: ${id ?? 'none'}]` : '';
    console.log(`[${label.padEnd(7)}] ${message}${suffix}`);
  }

  private section(title: string) {
    this.current = title;
    if (!this.options.json) console.log(`\n${title}`);
  }

  private miseData() {
    return process.env.MISE_DATA_DIR || path.join(process.env.XDG_DATA_HOME || path.join(this.home, '.local/share'), 'mise');
  }

  private system() {
    this.section('System');
    this.report('ok', `${this.profile} profile on ${os.hostname()} (${os.type()} ${os.release()} ${os.arch()})`);
    // Read first: its exceptions apply to every check, these included.
    try {
      this.machine = readMachine(this.home);
    } catch (error) {
      this.report('fail', message(error));
    }
    const status = capture('git', ['-C', this.repo, 'status', '--porcelain']);
    if (!status.ok) this.report('warn', `${this.repo} is not a git checkout`, 'checkout:git');
    else if (status.stdout.trim()) this.report('warn', 'configs checkout has uncommitted changes', 'checkout:dirty');
    else this.report('ok', 'configs checkout is clean');
    // Compares against the last fetch, so this stays offline.
    const upstream = capture('git', ['-C', this.repo, 'rev-list', '--count', 'HEAD..@{upstream}']);
    const behind = Number(upstream.stdout.trim());
    if (status.ok && !upstream.ok) this.report('note', 'configs checkout has no upstream to compare against');
    else if (behind > 0) this.report('warn', `configs checkout is ${behind} commit${behind === 1 ? '' : 's'} behind its upstream; run git pull`, 'checkout:behind');
    if (this.machine) {
      const { role, codexHomes, claudeConfigDirs } = this.machine;
      this.report('ok', `machine intent from ${this.files.pretty(machinePath(this.home))}: role ${role ?? 'unset'}, JavaScript runtimes from ${this.machine.jsRuntimes}, ${codexHomes.length} Codex homes, ${claudeConfigDirs.length} Claude config directories`);
    } else this.report('note', `no ${this.files.pretty(machinePath(this.home))}; role and extra runtime homes come from the receipt only`);
  }

  private applied() {
    this.section('Apply receipt');
    const file = this.files.pretty(receiptPath(this.home));
    try {
      this.receipt = readReceipt(this.home);
    } catch (error) {
      this.report('fail', message(error));
      return;
    }
    const receipt = this.receipt;
    const commandCenter = receipt?.components['command-center'];
    this.role = this.machine?.role ?? (commandCenter ? (commandCenter.action === 'install' ? 'command-center' : 'worker') : undefined);
    if (!receipt) {
      this.report('warn', `no apply receipt at ${file}; anything applied before receipts is unverified until the next ./cli run records one`, 'receipt:missing');
      return;
    }
    const run = receipt.lastRun;
    const at = (revision?: string, dirty?: boolean) => `${revision?.slice(0, 7) ?? 'an unknown revision'}${dirty ? ' with uncommitted changes' : ''}`;
    const summary = `last ${run.action} (${run.at}) of ${run.components.join(', ') || 'nothing'} at ${at(run.revision, run.dirty)}`;
    if (run.outcome === 'failed') this.report('warn', `${summary} failed${run.failed ? ` in ${run.failed}` : ''}: ${run.error ?? 'unknown error'}`, 'receipt:failed');
    else if (run.outcome === 'kept-conflicts') this.report('warn', `${summary} kept differing local copies: ${run.kept.join(', ')}`, 'receipt:kept');
    else this.report('ok', `${summary} completed`);
    const head = checkoutState(this.repo).revision;
    const older = Object.entries(receipt.components).filter(([, record]) => record.revision !== head)
      .map(([name, record]) => `${name} ${at(record.revision, record.dirty)}`);
    if (older.length) this.report('note', `components last applied at other revisions: ${older.join(', ')}`);
  }

  // Every Codex home and Claude config directory this machine is known to use:
  // the current environment's, machine.json's, and those the receipt recorded.
  private homes(): RuntimeHomes[] {
    const current = runtimeHomes(this.home);
    const codex = [...new Set([current.codex, ...this.machine?.codexHomes ?? [], ...this.receipt?.runtimeHomes.codex ?? []])];
    const claude = [...new Set([current.claude, ...this.machine?.claudeConfigDirs ?? [], ...this.receipt?.runtimeHomes.claude ?? []])];
    return Array.from({ length: Math.max(codex.length, claude.length) }, (_, index) => ({
      codex: codex[index] ?? current.codex, claude: claude[index] ?? current.claude,
    }));
  }

  private async configs() {
    this.section('Managed files');
    const excluded: Component[] = ['packages', 'gh-extensions', 'apps', 'rea', ...this.role === 'command-center' ? [] : ['command-center'] as const];
    const [first, ...others] = this.homes();
    const entries = new Map<string, string>(), drifted = new Set<Component>();
    try {
      // The first home covers everything; the others only what depends on the homes.
      // Each component is previewed alone so the advice can name the ones that drifted.
      for (const [homes, selected] of [[first, components.filter(component => !excluded.includes(component))] as const,
        ...others.map(homes => [homes, ['agents', 'skills', ...this.role === 'command-center' ? ['command-center'] as const : []]] as const)]) {
        for (const component of selected) {
          const recorder = new Recorder(this.repo, this.home, true);
          await new Installer(recorder, this.profile, new Set([component]), homes).apply(false);
          for (const [kind, text] of recorder.entries) {
            if (settled.has(kind)) continue;
            entries.set(`${kind}: ${text}`, `files:${text}`);
            drifted.add(component);
          }
        }
      }
    } catch (error) {
      this.report('fail', `install preview failed: ${message(error)}`);
      return;
    }
    const homes = [first, ...others].filter(homes => homes !== undefined);
    const codex = [...new Set(homes.map(homes => this.files.pretty(homes.codex)))], claude = [...new Set(homes.map(homes => this.files.pretty(homes.claude)))];
    this.report('ok', `checked runtime homes: Codex ${codex.join(', ')}; Claude ${claude.join(', ')}`);
    if (!entries.size) this.report('ok', 'managed files match the repository');
    for (const [text, id] of entries) this.report('warn', text, id);
    const only = [...drifted].join(',');
    if (entries.size && !this.options.json) console.log(`          review with ./cli --dry-run --only ${only}, then apply with ./cli --only ${only}`);
    this.commandCenter(homes);
    this.overrides(homes);
  }

  // Codex reads AGENTS.override.md instead of the AGENTS.md installed next to it.
  private overrides(homes: RuntimeHomes[]) {
    const found = [...new Set(homes.map(homes => path.join(homes.codex, 'AGENTS.override.md')))].filter(file => fs.existsSync(file));
    for (const file of found) this.report('warn', `${this.files.pretty(file)} replaces the installed AGENTS.md for Codex; review it, or remove it if it is stale`, `agents-override:${this.files.pretty(file)}`);
    if (!found.length) this.report('ok', 'no Codex AGENTS.override.md shadows the installed instructions');
  }

  private commandCenter(homes: RuntimeHomes[]) {
    if (this.role === undefined) {
      this.report('note', `role unknown; set "role" in ${this.files.pretty(machinePath(this.home))} to check command-center skills`);
      return;
    }
    if (this.role === 'command-center') return;
    const fleet = path.join(this.repo, 'fleet/skills');
    const roots = [path.join(this.home, '.agents/skills'), ...homes.map(homes => path.join(homes.claude, 'skills'))];
    const installed = [...new Set(roots.flatMap(root => children(fleet).map(skill => path.join(root, path.basename(skill)))
      .filter(link => realPath(link) === realPath(path.join(fleet, path.basename(link))))))];
    if (installed.length) this.report('warn', `command-center skills on a worker: ${installed.map(file => this.files.pretty(file)).join(', ')}; run ./cli uninstall --only command-center`, 'role:command-center-skills');
    else this.report('ok', 'no command-center skills on this worker');
  }

  private packages() {
    this.section('Packages');
    const opencode = opencodeVersion(this.home);
    if (opencode?.startsWith('2.')) this.report('ok', `opencode ${opencode} installed`);
    else this.report('fail', `${opencode ? `opencode ${opencode} is not v2` : 'opencode v2 is not installed'}; run ./cli --only packages`);
    const extensions = listed(path.join(this.repo, 'packages/gh-extensions.txt'));
    try {
      const installed = ghExtensions();
      const absent = extensions.filter(repo => !installed.has(repo));
      if (absent.length) this.report('fail', `missing gh extensions: ${absent.join(' ')}; run ./cli --only gh-extensions`);
      else this.report('ok', `${extensions.length} listed gh extensions installed`);
    } catch (error) {
      this.report('fail', message(error));
    }
    if (this.profile === 'omarchy') {
      try {
        const wanted = listed(path.join(this.repo, 'packages/omarchy.txt'));
        const missing = missingPacman(wanted);
        if (missing.length) this.report('fail', `missing packages: ${missing.join(' ')}; run ./cli --only packages`);
        else this.report('ok', `${wanted.length} listed packages installed`);
        const incomplete = apps.flatMap(({ name, packages }) => {
          const absent = missingPacman(packages);
          return absent.length ? [`${name} (${absent.join(' ')})`] : [];
        });
        const appImages = [['T3 Code', [t3code.appImage]], ['HyperFrames', [hyperframes.appImage, hyperframes.entry]]] as const;
        for (const [name, files] of appImages) {
          const absent = files.filter(file => !fs.existsSync(path.join(this.home, file)));
          if (absent.length) incomplete.push(`${name} (${absent.map(file => `~/${file}`).join(' ')})`);
        }
        if (incomplete.length) this.report('fail', `missing apps: ${incomplete.join(', ')}; run ./cli --only apps`);
        else this.report('ok', `${apps.length + appImages.length} Omarchy apps installed`);
      } catch (error) {
        this.report('fail', message(error));
      }
      return;
    }
    const brew = ['brew', '/opt/homebrew/bin/brew', '/usr/local/bin/brew'].find(command => capture(command, ['--prefix']).ok);
    if (!brew) { this.report('fail', 'Homebrew is not installed; run ./cli --only packages'); return; }
    for (const [list, flag, kind] of [['macos.txt', '--formula', 'formulae'], ['macos-casks.txt', '--cask', 'casks']] as const) {
      try {
        const wanted = listed(path.join(this.repo, 'packages', list));
        const missing = missingHomebrew(brew, flag, wanted);
        if (missing.length) this.report('fail', `missing Homebrew ${kind}: ${missing.join(' ')}; run ./cli --only packages`);
        else this.report('ok', `${wanted.length} listed Homebrew ${kind} installed`);
      } catch (error) {
        this.report('fail', message(error));
      }
    }
  }

  private mise() {
    this.section('mise');
    if (!capture('mise', ['--version']).ok) { this.report('fail', 'mise is not installed'); return []; }
    let listing: Record<string, MiseTool[]>;
    try {
      listing = miseCurrent(this.home);
    } catch (error) {
      this.report('fail', message(error));
      return [];
    }
    const tools = Object.keys(listing);
    const fragments = miseFragments(this.repo, this.profile);
    const shared = new Map(fragments.flatMap(fragment => [...requested(fragment)]));
    // A tool a fragment requests but mise does not list is not configured at all.
    const unconfigured = [...shared.keys()].filter(tool => !listing[tool]?.length);
    if (unconfigured.length) this.report('fail', `not configured: ${unconfigured.join(' ')}; is the shared fragment linked? run ./cli --dry-run --only mise`);
    const missing = tools.filter(tool => listing[tool]?.some(version => !version.installed));
    if (missing.length) this.report('fail', `not installed: ${missing.join(' ')}; run mise install`);
    else this.report('ok', `${tools.length} configured tools installed`);
    for (const [tool, [selected]] of Object.entries(listing)) {
      if (selected) this.versions[tool] = selected.version;
      const wanted = shared.get(tool);
      // A machine's own config wins over the fragments; flag only a different request.
      const source = selected?.source && realPath(selected.source);
      if (selected?.source && wanted !== undefined && !fragments.some(fragment => realPath(fragment) === source) && selected.requested !== wanted) {
        this.report('warn', `${tool} ${selected.version} from ${this.files.pretty(selected.source)} overrides the shared "${wanted}" (requests "${selected.requested ?? '?'}")`, `override:${tool}`);
      }
    }
    const recorded = this.receipt?.tools;
    if (recorded) {
      const changed = Object.entries(this.versions).filter(([tool, version]) => recorded[tool] !== undefined && recorded[tool] !== version)
        .map(([tool, version]) => `${tool} ${recorded[tool]} -> ${version}`);
      if (changed.length) this.report('note', `changed since the last apply: ${changed.join(', ')}`);
    }
    return tools;
  }

  // Resolves tools the way a new terminal does: macOS terminals start login
  // shells, Omarchy's start interactive ones. The clean environment keeps this
  // process's PATH from hiding problems in the startup files.
  private shell(tools: string[]) {
    const shell = os.userInfo().shell || (this.profile === 'macos' ? '/bin/zsh' : '/bin/bash');
    this.section(`Shell (${path.basename(shell)})`);
    const unmapped = tools.filter(tool => tool.includes(':') && !executables[tool]);
    for (const tool of unmapped) this.report('warn', `no executable known for ${tool}; add it to executables in scripts/lib/health.ts`, `path:${tool}`);
    const names = tools.filter(tool => !unmapped.includes(tool)).map(tool => executables[tool] ?? tool);
    // Vite+'s shims in front of mise either hand off to the next tool on PATH
    // (system-first mode) or run Vite+'s own runtimes; `vp env which` tells which.
    const script = [
      '__donnes_path() { if [ -n "$ZSH_VERSION" ]; then whence -p "$1"; else type -P "$1"; fi; }',
      '__donnes_vp="${VP_HOME:-$HOME/.vite-plus}/bin"',
      'mise doctor >/dev/null 2>&1; printf "\\n@@doctor %s\\n" "$?"',
      'printf "@@vpbin %s\\n" "$__donnes_vp"',
      `for name in ${names.join(' ')}; do`,
      '  __donnes_bin="$(__donnes_path "$name")"; printf "@@bin %s %s\\n" "$name" "$__donnes_bin"',
      '  case "$__donnes_bin" in "$__donnes_vp"/*) printf "@@vp %s %s\\n" "$name" "$("$__donnes_vp/vp" env which "$name" 2>/dev/null | head -n 1)" ;; esac',
      'done',
      'printf "@@opencode %s\\n" "$(__donnes_path opencode)"',
      `for name in ${legacyManagers.join(' ')}; do type "$name" >/dev/null 2>&1 && printf "@@legacy %s\\n" "$name"; done`,
      'true',
    ].join('\n');
    const env = Object.fromEntries(['HOME', 'USER', 'LOGNAME', 'TERM', 'LANG']
      .flatMap(name => process.env[name] === undefined ? [] : [[name, process.env[name]]]));
    const result = capture(shell, [process.platform === 'darwin' ? '-lic' : '-ic', script],
      { cwd: this.home, timeout: 60_000, env: { ...env, HOME: this.home, SHELL: shell } });
    const lines = result.stdout.split('\n').filter(line => line.startsWith('@@')).map(line => line.split(' '));
    const value = (kind: string, name?: string) => lines.find(([k, n]) => k === kind && (name === undefined || n === name))?.slice(name === undefined ? 1 : 2).join(' ');
    const doctor = value('@@doctor');
    if (doctor === undefined) {
      this.report('fail', `${shell} did not finish starting: ${result.stderr.trim().split('\n').at(-1) ?? 'no output'}`);
      return;
    }
    if (doctor === '0') this.report('ok', 'mise doctor found no problems');
    else this.report('fail', 'mise doctor found problems; run mise doctor');
    const data = this.miseData(), vpBin = value('@@vpbin') ?? '';
    // mise's rust installs through rustup, whose proxies in ~/.cargo/bin run the
    // toolchain mise selects with RUSTUP_TOOLCHAIN.
    const rustup = path.join(this.home, '.cargo/bin');
    const isMise = (file: string, name?: string) => within(file, data) || delegatesToMise(file) || (name === 'rustfmt' && within(file, rustup));
    // machine.json can give Vite+ these runtimes; then only its own installs count.
    const vitePlusOwns = (name: string) => this.machine?.jsRuntimes === 'vite-plus' && vitePlusScopes.includes(name);
    let resolved = 0, throughVitePlus = 0, managed = 0;
    for (const [kind, name, ...rest] of lines) {
      if (kind !== '@@bin' || !name) continue;
      const file = rest.join(' ') && path.resolve(rest.join(' '));
      if (!file) this.report('fail', `${name} is not on PATH`);
      else if (vpBin && within(file, vpBin)) {
        // Vite+ installs and updates its own vp; the mise copy only bootstraps it.
        if (name === 'vp') { this.vp(file); continue; }
        const delegate = value('@@vp', name), target = delegate && path.resolve(delegate);
        if (vitePlusOwns(name)) {
          if (target && within(target, vitePlusHome(this.home))) managed++;
          else this.report('warn', `${name} resolves to ${target ? this.files.pretty(target) : 'nothing'} instead of Vite+'s managed runtime that machine.json's jsRuntimes asks for; run ./cli --only mise`, `path:${name}`);
        } else if (target && isMise(target)) { resolved++; throughVitePlus++; }
        else this.report('warn', `${name} resolves to Vite+'s ${target ? this.files.pretty(target) : 'shim'} instead of mise; run ./cli --only mise to hand Vite+'s shims to mise`, `path:${name}`);
      } else if (vitePlusOwns(name)) this.report('warn', `${name} resolves to ${this.files.pretty(file)} instead of Vite+'s shim that machine.json's jsRuntimes asks for`, `path:${name}`);
      else if (!isMise(file, name)) this.report('warn', `${name} resolves to ${this.files.pretty(file)} instead of mise`, `path:${name}`);
      else resolved++;
    }
    if (resolved) this.report('ok', `${resolved} tools resolve through mise${throughVitePlus ? ` (${throughVitePlus} via Vite+'s system-first shims)` : ''}`);
    if (managed) this.report('ok', `${managed} tools resolve to Vite+'s managed runtimes, as machine.json's jsRuntimes asks`);
    this.globals(names);
    const opencode = value('@@opencode');
    const expected = path.join(this.home, '.opencode/bin/opencode');
    if (opencode && path.resolve(opencode) === expected) this.report('ok', 'opencode resolves to its v2 install');
    else this.report('warn', `opencode resolves to ${opencode ? this.files.pretty(path.resolve(opencode)) : 'nothing'} instead of ${this.files.pretty(expected)}`, 'opencode:path');
    const leftovers = lines.filter(([kind]) => kind === '@@legacy').map(([, name]) => [`${name} is still on PATH`, `legacy:${name}`]);
    for (const [name, directory] of [
      ['nvm', '.nvm'], ['pyenv', '.pyenv'], ['rbenv', '.rbenv'], ['asdf', '.asdf'], ['volta', '.volta'],
      ['fnm', '.local/share/fnm'], ['fnm', 'Library/Application Support/fnm'],
    ] as const) {
      const file = path.join(this.home, directory);
      if (fs.existsSync(file)) leftovers.push([`${this.files.pretty(file)} is left over from ${name}`, `legacy:${name}`]);
    }
    for (const [text, id] of leftovers) this.report('warn', text ?? '', id);
    if (!leftovers.length) this.report('ok', 'no other version managers found');
  }

  private vp(file: string) {
    const version = realPath(file)?.match(/\/([^/]+)\/bin\/vp$/)?.[1];
    this.report('ok', `vp resolves to Vite+'s own install${version ? ` (${version})` : ''}`);
    const mise = this.versions['github:voidzero-dev/vite-plus'];
    if (version && mise && !version.startsWith(mise)) this.report('note', `mise resolves vite-plus ${mise}, which GUI apps run; terminals run Vite+'s ${version}`);
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
    for (const file of duplicates) this.report('warn', `${this.files.pretty(file)} duplicates the mise tool; remove it`, `duplicate:${this.files.pretty(file)}`);
    if (!duplicates.length) this.report('ok', 'no global bun or pnpm copies of mise tools');
  }

  private services() {
    this.section('Background jobs');
    if (this.profile === 'omarchy') {
      for (const [unit, component, interval] of systemdJobs) {
        if (!capture('systemctl', ['--user', 'is-active', '--quiet', `${unit}.timer`]).ok) {
          this.report('fail', `${unit}.timer is not active; run ./cli --only ${component}`);
          continue;
        }
        const show = capture('systemctl', ['--user', 'show', `${unit}.service`, '-p', 'Result', '-p', 'ExecMainStatus', '-p', 'ExecMainExitTimestamp', '--timestamp=unix']);
        const property = (name: string) => show.stdout.match(new RegExp(`^${name}=(.*)$`, 'm'))?.[1]?.trim();
        const result = property('Result'), status = property('ExecMainStatus'), exited = Number(property('ExecMainExitTimestamp')?.replace(/^@/, '')) * 1000;
        if (!show.ok || result === undefined) this.report('fail', `cannot read ${unit}.service's last result`);
        else if (result !== 'success') this.report('fail', `${unit}.service last failed (${result}, status ${status ?? '?'}); see journalctl --user -u ${unit}.service`);
        else if (!exited) this.report('note', `${unit}.timer is active; ${unit}.service has not run yet`);
        else if (Date.now() - exited > interval) this.report('warn', `${unit}.service last ran ${ago(exited)}; check systemctl --user list-timers`, `job:${unit}:stale`);
        else this.report('ok', `${unit}.timer is active; last run succeeded ${ago(exited)}`);
      }
      return;
    }
    const uid = process.getuid?.();
    for (const [label, interval] of launchdJobs) {
      const print = capture('launchctl', ['print', `gui/${uid}/${label}`]);
      if (!print.ok) { this.report('fail', `launchd agent ${label} is not loaded; run ./cli --only mise`); continue; }
      const exit = print.stdout.match(/^\s*last exit code = (.+)$/m)?.[1]?.trim();
      if (exit === undefined || exit.startsWith('(never')) { this.report('note', `launchd agent ${label} is loaded and has not run yet`); continue; }
      if (exit !== '0') { this.report('fail', `launchd agent ${label} last exited ${exit}`); continue; }
      const log = interval === undefined ? undefined : fs.statSync(path.join(this.home, 'Library/Logs', `${label}.log`), { throwIfNoEntry: false });
      if (interval !== undefined && log && Date.now() - log.mtimeMs > interval) {
        this.report('warn', `launchd agent ${label} last logged a run ${ago(log.mtimeMs)}`, `job:${label}:stale`);
      } else this.report('ok', `launchd agent ${label} is loaded; last run exited 0${log ? ` ${ago(log.mtimeMs)}` : ''}`);
    }
    if (capture('launchctl', ['getenv', 'PATH']).stdout.includes(path.join(this.miseData(), 'shims'))) {
      this.report('ok', 'GUI apps get mise shims on PATH');
    } else this.report('warn', 'GUI apps do not have mise shims on PATH yet; log out and back in', 'gui-path');
  }

  // REA's own doctor downloads and runs its installer, so health only says
  // whether it was applied and how to check it.
  private optional() {
    this.section('Optional');
    const rea = this.receipt?.components.rea;
    const doctor = 'npx --yes rea-agents@6.5.0 doctor --client codex --client claude_code --skill --json';
    this.report('note', `REA is not checked here${rea ? `; last ${rea.action} ${rea.at}` : '; no recorded apply'}. Check it with ${doctor}`);
  }

  async run() {
    this.system();
    this.applied();
    await this.configs();
    this.packages();
    this.shell(this.mise());
    this.services();
    this.optional();
    for (const id of Object.keys(this.machine?.exceptions ?? {}).filter(id => !this.matched.has(id))) {
      this.report('note', `exception ${id} matched no warning; remove it from ${this.files.pretty(machinePath(this.home))} if obsolete`);
    }
    const counts = { ok: 0, warn: 0, fail: 0 };
    for (const { status } of this.checks) if (status !== 'note') counts[status]++;
    const healthy = counts.fail === 0;
    if (this.options.json) {
      console.log(JSON.stringify({
        profile: this.profile, host: os.hostname(), strict: this.options.strict, healthy, counts,
        checkout: checkoutState(this.repo), role: this.role ?? null, versions: this.versions, checks: this.checks,
      }, null, 2));
    } else {
      const { ok, warn, fail } = counts;
      console.log(`\n${ok} ok, ${warn} warning${warn === 1 ? '' : 's'}, ${fail} failure${fail === 1 ? '' : 's'}`);
    }
    return healthy;
  }
}
