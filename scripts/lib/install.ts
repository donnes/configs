import * as fs from 'node:fs';
import * as path from 'node:path';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { exists, Files, realPath, run, walk, within } from './files.ts';
import { Skills } from './skills.ts';
import { Agents } from './agents.ts';
import { Mise } from './mise.ts';
import { canPrompt } from './prompts.ts';

export const components = ['packages', 'gh-extensions', 'apps', 'agents', 'skills', 'mise', 'atuin', 'nvim', 'gradle', 'shell', 'tmux', 'git', 'session', 'command-center', 'rea'] as const;
export type Component = typeof components[number];
export type Profile = 'macos' | 'omarchy';

// The Codex home and Claude config directory that agents and skills install into.
export type RuntimeHomes = { codex: string, claude: string };

export function runtimeHomes(home: string): RuntimeHomes {
  return {
    codex: process.env.CODEX_HOME || path.join(home, '.codex'),
    claude: process.env.CLAUDE_CONFIG_DIR || path.join(home, '.claude'),
  };
}

export function listed(file: string) {
  return fs.readFileSync(file, 'utf8').split(/\s+/).filter(Boolean);
}

// Lists the packages pacman has not installed. pacman -T exits 127 when some
// are missing; anything else is a failed query, not an answer.
export function missingPacman(packages: string[]) {
  if (!packages.length) return [];
  const result = spawnSync('pacman', ['-T', ...packages], { encoding: 'utf8' });
  if (result.error || (result.status !== 0 && result.status !== 127)) throw new Error(`pacman -T failed (${result.error?.message ?? result.status})`);
  return result.stdout.split('\n').filter(Boolean);
}

// Lists the formulae or casks Homebrew has not installed. Tap-qualified names
// such as owner/tap/name are installed under their last segment.
export function missingHomebrew(brew: string, kind: '--formula' | '--cask', wanted: string[]) {
  const result = spawnSync(brew, ['list', kind, '-1'], { encoding: 'utf8' });
  if (result.error || result.status !== 0) throw new Error(`${brew} list ${kind} failed`);
  const installed = new Set(result.stdout.split('\n'));
  return wanted.filter(name => !installed.has(path.basename(name)));
}

export function available(profile: Profile) {
  const exclusive: Component[] = profile === 'macos' ? ['apps', 'session'] : [];
  return components.filter(component => !exclusive.includes(component));
}

export function detectProfile(): Profile {
  const profile = process.env.DONNES_CONFIGS_PROFILE;
  if (profile === 'macos' || profile === 'omarchy') return profile;
  if (profile) throw new Error('DONNES_CONFIGS_PROFILE must be omarchy or macos');
  if (fs.existsSync('/usr/share/omarchy')) return 'omarchy';
  if (process.platform === 'darwin') return 'macos';
  throw new Error('unsupported system: expected Omarchy or macOS');
}

const timer = 'hypr-session-autosave.timer';

// opencode v2 is only published through its own installer; mise and the
// default installer still ship v1. It upgrades itself once installed.
export const opencodeInstaller = 'https://opencode.ai/v2/install';

export function opencodeVersion(home: string) {
  const result = spawnSync(path.join(home, '.opencode/bin/opencode'), ['--version'], { encoding: 'utf8' });
  return result.status === 0 ? result.stdout.match(/\d+\.\d+\.\d+/)?.[0] : undefined;
}

// gh extensions live in the user's gh data directory, so both profiles share one
// list. Reports owner/repo for each installed extension.
export function ghExtensions() {
  const result = spawnSync('gh', ['extension', 'list'], { encoding: 'utf8' });
  if (result.error || result.status !== 0) throw new Error('gh extension list failed; is gh installed and on PATH?');
  return new Set(result.stdout.split('\n').map(line => line.split('\t')[1]?.trim()).filter(repo => repo !== undefined && repo !== ''));
}

// Omarchy's installers also set up what a bare package install skips, such as
// Steam's 32-bit GPU drivers, the Tailscale service and Zed's theme. Some open
// the app or start a Tailscale login, so each runs only while a package is missing.
// Apps without an installer go through Omarchy's package helpers instead.
type App = { name: string, packages: string[], installer?: [string, ...string[]], aur?: boolean };
export const apps: App[] = [
  { name: 'Steam', packages: ['steam'], installer: ['omarchy-install-gaming-steam'] },
  { name: 'MangoHud', packages: ['mangohud', 'lib32-mangohud'] },
  { name: 'LACT', packages: ['lact'] },
  { name: 'racing wheel tools', packages: ['oversteer', 'new-lg4ff-dkms-git', 'usb_modeswitch'], aur: true },
  { name: 'Tailscale', packages: ['tailscale'], installer: ['omarchy-install-service-tailscale'] },
  { name: 'Zed', packages: ['zed', 'omazed'], installer: ['omarchy-install-editor-zed'] },
  { name: 'Zen', packages: ['zen-browser-bin'], installer: ['omarchy-install-browser', 'zen'] },
  { name: 'Helium', packages: ['helium-browser-bin'], aur: true },
];

// T3 Code's nightly ships as an AppImage on GitHub and updates itself once
// installed. Omarchy's t3code packages would be a second copy on the same data.
export const t3code = {
  appImage: 'Applications/T3-Code.AppImage',
  releases: 'https://api.github.com/repos/pingdotgg/t3code/releases?per_page=30',
  downloads: 'https://github.com/pingdotgg/t3code/releases/download',
  packages: ['t3code-bin', 't3code-nightly-bin'],
};

// HyperFrames' desktop app links only its latest AppImage, without a checksum,
// and records where it lives in ~/.config/HyperFrames/launcher.json when it runs.
// Its own desktop entry only handles its URL schemes and stays out of the app
// launcher, so the step adds a visible one with the icon from the AppImage.
export const hyperframes = {
  appImage: 'Applications/HyperFrames.AppImage',
  download: 'https://hyperframes.dev/studio/download?os=linux',
  entry: '.local/share/applications/hyperframes.desktop',
  icon: '.local/share/icons/dev.hyperframes.desktop.png',
};

function download(url: string) {
  const result = spawnSync('curl', ['-fsSL', url], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  if (result.error || result.status !== 0) throw new Error(`Cannot download ${url}`);
  return result.stdout;
}

export class Installer {
  readonly skills: Skills;
  // For the apply receipt: components that finished every step, those that kept
  // a differing local copy, and the one running when an error stopped the run.
  readonly finished: Component[] = [];
  readonly keptIn = new Set<Component>();
  running?: Component;
  private started = new Set<Component>();

  constructor(readonly files: Files, private profile: Profile, private enabled: Set<Component>,
    readonly homes: RuntimeHomes = runtimeHomes(files.home)) {
    this.skills = new Skills(files, homes.claude);
  }

  private source(relative: string) { return path.join(this.files.repo, relative); }
  private destination(relative: string) { return path.join(this.files.home, relative); }

  // Runs all of a component's steps, once per run, so the receipt marks it
  // finished only after its last step succeeded.
  private async component(name: Component, operation: () => void | Promise<void>) {
    if (!this.enabled.has(name)) { this.files.log('skip', `${name} component disabled`); return; }
    if (this.started.has(name)) throw new Error(`${name} component ran twice; group its steps into one component() call`);
    this.started.add(name);
    const kept = this.files.kept.length;
    this.running = name;
    await operation();
    this.running = undefined;
    if (this.files.kept.length > kept) this.keptIn.add(name);
    this.finished.push(name);
  }

  private async tree(source: string, destination: string, uninstall: boolean) {
    if (uninstall) this.files.unlinkTree(this.source(source), this.destination(destination));
    else await this.files.linkTree(this.source(source), this.destination(destination));
  }

  private async link(source: string, destination: string, uninstall: boolean) {
    if (uninstall) this.files.unlink(this.source(source), this.destination(destination));
    else await this.files.link(this.source(source), this.destination(destination));
  }

  private block(destination: string, content: string, uninstall: boolean) {
    this.files.block(this.destination(destination), uninstall ? undefined : content);
  }

  private rea(uninstall: boolean) {
    // REA's uninstall affects every registered client, not just our two clients.
    if (uninstall) {
      this.files.log('note', 'REA left installed; its upstream uninstall affects all clients');
      return;
    }
    const args = ['--yes', 'rea-agents@6.5.0', 'setup', '--client', 'codex', '--client', 'claude_code'];
    this.files.log('setup', `npx ${[...args, this.files.dryRun ? '--dry-run' : '--yes'].join(' ')}`);
    if (!this.files.dryRun) run('npx', [...args, '--yes']);
  }

  // Installs only what is missing; upgrades stay explicit (README, Packages and upgrades).
  private packages() {
    if (this.profile === 'omarchy') {
      const wanted = listed(this.source('packages/omarchy.txt'));
      const missing = missingPacman(wanted);
      if (!missing.length) this.files.log('skip', `${wanted.length} listed packages already installed`);
      else {
        this.files.log('package', `yay -S --needed ${missing.join(' ')}`);
        // yay prompts for confirmation and sudo, which would hang without a terminal.
        if (!this.files.dryRun && !canPrompt()) throw new Error(`missing packages: ${missing.join(' ')}; install them from a terminal with ./cli --only packages`);
        if (!this.files.dryRun) run('yay', ['-S', '--needed', ...missing]);
      }
    } else this.homebrew();
    this.opencode();
  }

  private ghExtensions() {
    const installed = ghExtensions();
    for (const repo of listed(this.source('packages/gh-extensions.txt'))) {
      if (installed.has(repo)) { this.files.log('skip', `gh extension ${repo} already installed`); continue; }
      this.files.log('package', `gh extension install ${repo}`);
      if (!this.files.dryRun) run('gh', ['extension', 'install', repo]);
    }
  }

  // The shell startup files and the GUI PATH already put ~/.opencode/bin first.
  private opencode() {
    const version = opencodeVersion(this.files.home);
    if (version?.startsWith('2.')) { this.files.log('skip', `opencode ${version} already installed`); return; }
    this.files.log('package', `curl -fsSL ${opencodeInstaller} | bash -s -- --no-modify-path`);
    if (this.files.dryRun) return;
    const download = spawnSync('curl', ['-fsSL', opencodeInstaller], { encoding: 'utf8' });
    if (download.error || download.status !== 0) throw new Error('Cannot download the opencode installer');
    run('bash', ['-s', '--', '--no-modify-path'], download.stdout);
  }

  private homebrew() {
    const { dryRun } = this.files;
    const executable = spawnSync('/bin/sh', ['-c', 'command -v brew'], { encoding: 'utf8' }).stdout?.trim();
    let brew = executable || 'brew';
    if (!executable) {
      this.files.log('package', 'install Homebrew');
      if (!dryRun) {
        const download = spawnSync('curl', ['-fsSL', 'https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh'], { encoding: 'utf8' });
        if (download.error || download.status !== 0) throw new Error('Cannot download the Homebrew installer');
        const result = spawnSync('/bin/bash', ['-c', download.stdout], { stdio: 'inherit', env: { ...process.env, NONINTERACTIVE: '1' } });
        if (result.error || result.status !== 0) throw new Error('Homebrew installation failed');
        brew = ['/opt/homebrew/bin/brew', '/usr/local/bin/brew'].find(file => fs.existsSync(file)) ?? '';
        if (!brew) throw new Error('Homebrew installed but brew was not found');
      }
    }
    for (const [list, kind] of [['macos.txt', '--formula'], ['macos-casks.txt', '--cask']] as const) {
      const wanted = listed(this.source(`packages/${list}`));
      // A fresh Homebrew has nothing installed yet; a preview cannot query it.
      const missing = executable ? missingHomebrew(brew, kind, wanted) : wanted;
      if (!missing.length) { this.files.log('skip', `${wanted.length} listed Homebrew ${kind === '--cask' ? 'casks' : 'formulae'} already installed`); continue; }
      // Homebrew asks for third-party taps to be trusted before installing from them.
      const taps = [...new Set(missing.filter(name => name.split('/').length === 3).map(name => path.dirname(name)))];
      for (const tap of taps) this.files.log('package', `${brew} trust --tap ${tap}`);
      this.files.log('package', `${brew} install ${kind} ${missing.join(' ')}`);
      if (dryRun) continue;
      for (const tap of taps) run(brew, ['trust', '--tap', tap]);
      run(brew, ['install', kind, ...missing]);
    }
  }

  private apps() {
    for (const { name, packages, installer, aur } of apps) {
      const present = spawnSync('omarchy-pkg-present', packages, { stdio: 'ignore' }).status === 0;
      const [command, ...args] = installer ?? [aur ? 'omarchy-pkg-aur-add' : 'omarchy-pkg-add', ...packages];
      this.files.log(present ? 'skip' : 'app', present ? `${name}: already installed` : `${name}: ${[command, ...args].join(' ')}`);
      if (!present && !this.files.dryRun) run(command, args);
    }
    this.t3code();
    this.hyperframes();
  }

  private t3code() {
    const appImage = this.destination(t3code.appImage);
    if (fs.existsSync(appImage)) { this.files.log('skip', 'T3 Code: already installed'); return; }
    const missing = missingPacman(t3code.packages);
    const packaged = t3code.packages.filter(name => !missing.includes(name));
    if (packaged.length) throw new Error(`T3 Code: remove ${packaged.join(' ')} first (sudo pacman -R ${packaged.join(' ')}); the AppImage replaces it`);
    this.files.log('app', `T3 Code: latest nightly AppImage -> ${this.files.pretty(appImage)}`);
    if (this.files.dryRun) return;
    const releases: { tag_name: string }[] = JSON.parse(download(t3code.releases));
    const tag = releases.find(release => release.tag_name.includes('-nightly.'))?.tag_name;
    if (!tag) throw new Error('T3 Code: no nightly release found');
    // electron-updater's manifest names the x86_64 AppImage and its checksum.
    const manifest = download(`${t3code.downloads}/${tag}/nightly-linux.yml`);
    const file = manifest.match(/^path: (\S+)$/m)?.[1], sha512 = manifest.match(/^sha512: (\S+)$/m)?.[1];
    if (!file || !sha512) throw new Error(`T3 Code: cannot read the ${tag} manifest`);
    this.appImage(appImage, `${t3code.downloads}/${tag}/${file}`, sha512);
  }

  private hyperframes() {
    const appImage = this.destination(hyperframes.appImage);
    if (fs.existsSync(appImage)) this.files.log('skip', 'HyperFrames: already installed');
    else {
      this.files.log('app', `HyperFrames: latest AppImage -> ${this.files.pretty(appImage)}`);
      if (!this.files.dryRun) this.appImage(appImage, hyperframes.download);
    }
    const entry = this.destination(hyperframes.entry), icon = this.destination(hyperframes.icon);
    if (fs.existsSync(entry)) { this.files.log('skip', `HyperFrames: ${this.files.pretty(entry)} exists`); return; }
    this.files.log('app', `HyperFrames: launcher entry -> ${this.files.pretty(entry)}`);
    if (this.files.dryRun) return;
    const extracted = fs.mkdtempSync(path.join(this.files.home, '.hyperframes-icon-'));
    try {
      spawnSync(appImage, ['--appimage-extract', path.basename(icon)], { cwd: extracted, stdio: 'ignore' });
      const file = path.join(extracted, 'squashfs-root', path.basename(icon));
      if (!fs.existsSync(file)) throw new Error(`HyperFrames: ${path.basename(icon)} is missing from the AppImage`);
      fs.mkdirSync(path.dirname(icon), { recursive: true });
      fs.copyFileSync(file, icon);
    } finally {
      fs.rmSync(extracted, { recursive: true, force: true });
    }
    fs.mkdirSync(path.dirname(entry), { recursive: true });
    fs.writeFileSync(entry, [
      '[Desktop Entry]', 'Type=Application', 'Name=HyperFrames', 'Comment=Write HTML, render video',
      `Exec="${appImage}" %U`, `Icon=${icon}`, 'Terminal=false', 'Categories=AudioVideo;Video;', 'StartupWMClass=hyperframes', '',
    ].join('\n'));
  }

  // Downloads next to the destination, so a failed or tampered download never
  // leaves an AppImage that later runs would take as installed.
  private appImage(appImage: string, url: string, sha512?: string) {
    const partial = `${appImage}.part`;
    fs.mkdirSync(path.dirname(appImage), { recursive: true });
    run('curl', ['-fsSL', '-o', partial, url]);
    if (sha512 && createHash('sha512').update(fs.readFileSync(partial)).digest('base64') !== sha512) {
      fs.rmSync(partial);
      throw new Error(`${path.basename(url)} does not match its published checksum`);
    }
    fs.chmodSync(partial, 0o755);
    fs.renameSync(partial, appImage);
  }

  private async nvim(uninstall: boolean) {
    const destination = this.destination('.config/nvim'), source = this.source('shared/nvim');
    if (uninstall) {
      this.files.unlinkTree(source, destination);
      this.files.unlinkTree(this.source(`${this.profile}/nvim`), destination);
      return;
    }
    let assumeMissing = !exists(destination);
    if (this.files.target(path.join(destination, 'init.lua')) !== path.join(source, 'init.lua') && this.files.target(destination)) {
      this.files.log(this.files.legacy(destination) ? 'relink' : 'unlink', `${this.files.pretty(destination)} -> per-file links`);
      if (!this.files.dryRun) fs.unlinkSync(destination);
      assumeMissing = true;
    }
    await this.files.linkTree(source, destination, assumeMissing, this.profile === 'omarchy' ? 'lua/plugins/theme.lua' : '');
    await this.files.linkTree(this.source(`${this.profile}/nvim`), destination, this.profile === 'omarchy' && assumeMissing);
    if (this.profile === 'omarchy') {
      await this.files.link(this.destination('.local/state/omarchy/current/theme/neovim.lua'), path.join(destination, 'lua/plugins/theme.lua'), assumeMissing);
    }
  }

  private async session(uninstall: boolean) {
    const config = this.destination('.config/hypr/hyprland.lua');
    if (!uninstall && !this.files.dryRun && !fs.existsSync(config)) throw new Error(`${config} is missing; restore Omarchy's Hyprland config first`);
    if (uninstall) {
      this.files.log('disable', `systemd user timer ${timer}`);
      if (!this.files.dryRun) spawnSync('systemctl', ['--user', 'disable', '--now', timer], { stdio: ['inherit', 'inherit', 'ignore'] });
    }
    await this.tree('omarchy/hypr', '.config/hypr', uninstall);
    await this.tree('omarchy/systemd/user', '.config/systemd/user', uninstall);
    this.files.block(config, uninstall ? undefined : 'require("hypr.session")', '--');
    if (!uninstall) this.files.log('enable', `systemd user timer ${timer}`);
    if (!this.files.dryRun) {
      run('systemctl', ['--user', 'daemon-reload']);
      if (!uninstall) run('systemctl', ['--user', 'enable', '--now', timer]);
    }
  }

  private async shared(uninstall: boolean) {
    await this.component('agents', () => new Agents(this.files, this.profile, this.homes).apply(uninstall));
    await this.component('skills', () => uninstall ? this.skills.uninstall() : this.skills.install());
    await this.component('command-center', () => this.skills.commandCenter(uninstall));
    await this.component('mise', () => new Mise(this.files, this.profile).apply(uninstall));
    await this.component('atuin', () => this.tree('shared/atuin', '.config/atuin', uninstall));
    await this.component('nvim', () => this.nvim(uninstall));
    // Each machine builds Android for its own emulator ABI; Gradle writes nothing else to this file.
    await this.component('gradle', () => this.link(`${this.profile}/gradle.properties`, '.gradle/gradle.properties', uninstall));
    if (!uninstall) for (const name of ['ghostty', 'yazi', 'ssh']) this.files.log('skip', `shared/${name} is excluded from the default install`);
  }

  private async platform(uninstall: boolean) {
    const macos = this.profile === 'macos';
    await this.component('shell', async () => {
      if (macos) {
        await this.link('macos/zshrc', '.zshrc', uninstall);
        this.block('.zshenv', `source "${this.source('macos/zshenv')}"`, uninstall);
        // macOS login shells reorder PATH after .zshenv, so mise's shims go in .zprofile.
        this.block('.zprofile', `source "${this.source('macos/zprofile')}"`, uninstall);
        await this.tree('macos/bin', '.local/bin', uninstall);
      } else {
        this.block('.bashrc', `source "${this.source('omarchy/bashrc.local')}"`, uninstall);
        await this.tree('omarchy/uwsm', '.config/uwsm', uninstall);
        await this.link('omarchy/helium-browser-flags.conf', '.config/helium-browser-flags.conf', uninstall);
        await this.tree('omarchy/bin', '.local/bin', uninstall);
      }
    });
    await this.component('git', async () => {
      // Git reads ~/.config/git/ignore as the global ignore while core.excludesFile is unset.
      await this.link('shared/git/ignore', '.config/git/ignore', uninstall);
      if (!macos) return;
      // ~/.gitconfig stays local because it holds the identity and account routing;
      // it includes the shared settings. Older installs linked the file itself, and
      // a block written through that link would make the repo file include itself.
      const config = this.destination('.gitconfig'), source = this.source('macos/gitconfig');
      this.files.unlink(source, config);
      if (this.files.target(config) !== source) this.files.block(config, uninstall ? undefined : `[include]\n\tpath = ${source}`);
    });
    if (!macos) await this.component('session', () => this.session(uninstall));
    await this.component('tmux', async () => {
      if (macos) { await this.link('macos/tmux.conf', '.tmux.conf', uninstall); return; }
      const config = this.destination('.config/tmux/tmux.conf');
      if (!uninstall && !this.files.dryRun && !fs.existsSync(config)) throw new Error(`${config} is missing; restore Omarchy's tmux config first`);
      await this.link('omarchy/tmux.local.conf', '.config/tmux/local.conf', uninstall);
      this.files.block(config, uninstall ? undefined : 'source-file -q ~/.config/tmux/local.conf');
    });
  }

  async apply(uninstall: boolean) {
    await this.component('rea', () => this.rea(uninstall));
    if (!uninstall) {
      await this.component('packages', () => this.packages());
      await this.component('gh-extensions', () => this.ghExtensions());
      if (this.profile === 'omarchy') await this.component('apps', () => this.apps());
      await this.shared(false);
      await this.platform(false);
    } else {
      await this.platform(true);
      await this.shared(true);
      this.files.log('note', 'packages, gh extensions and apps were left untouched');
    }
  }

  async importPath(input: string, update: boolean) {
    const expanded = input.startsWith('~/') ? this.destination(input.slice(2)) : path.resolve(input);
    const source = path.join(fs.realpathSync(path.dirname(expanded)), path.basename(expanded));
    if (!exists(source)) throw new Error(`${source} does not exist`);
    if (update && source === this.skills.lockPath()) { await this.skills.syncLock(); return; }
    if (this.files.target(source)) throw new Error(`${source} is already a symlink${update ? '; edits already write through to its target' : ''}`);
    const mapping = [
      ['.agents/skills', 'shared/skills'], ['.config/nvim', 'shared/nvim'], ['.config/atuin', 'shared/atuin'],
      [this.profile === 'macos' ? 'Library/Application Support/com.mitchellh.ghostty' : '.config/ghostty', 'shared/ghostty'],
      ['.config/yazi', 'shared/yazi'], ['.ssh', 'shared/ssh'], ['.local/bin', `${this.profile}/bin`],
      ...(this.profile === 'omarchy' ? [['.config/hypr', 'omarchy/hypr'], ['.config/systemd/user', 'omarchy/systemd/user']] : []),
    ].find(([destination]) => destination !== undefined && within(source, this.destination(destination)));
    const [localRoot, repoRoot] = mapping ?? [];
    if (!localRoot || !repoRoot) throw new Error(`${source} is outside the managed path map`);
    if (source === this.destination(localRoot)) throw new Error(`${update ? 'update' : 'adopt'} a file or child directory, not the managed root itself`);
    const relative = path.relative(this.destination(localRoot), source);
    const [skillName, ...skillPath] = relative.split(path.sep);
    const target = repoRoot === 'shared/skills' && skillName
      ? path.join(this.skills.source(skillName), ...skillPath)
      : update && source === this.destination('.config/nvim/lazy-lock.json')
      ? this.source(`${this.profile}/nvim/lazy-lock.json`)
      : this.source(path.join(repoRoot, relative));
    const directory = fs.statSync(source).isDirectory();
    const skill = directory && ['shared/skills', 'fleet/skills'].some(root => path.dirname(target) === this.source(root));
    if (!update) {
      if (exists(target)) throw new Error(`${this.files.pretty(target)} already exists`);
      this.files.log('adopt', `${this.files.pretty(source)} -> ${this.files.pretty(target)}`);
      if (!this.files.dryRun) {
        fs.mkdirSync(path.dirname(target), { recursive: true });
        // Copy before removing, supporting adoption across filesystem boundaries.
        fs.cpSync(source, target, { recursive: true, preserveTimestamps: true, verbatimSymlinks: true });
        fs.rmSync(source, { recursive: true });
      }
    } else {
      if (!exists(target)) throw new Error(`${this.files.pretty(target)} does not exist; use adopt instead`);
      if (fs.statSync(target).isDirectory() !== directory) throw new Error(`${this.files.pretty(target)} has a different file type`);
      for (const file of directory ? walk(source).filter(file => fs.lstatSync(file).isFile()) : [source]) {
        const destination = directory ? path.join(target, path.relative(source, file)) : target;
        const identical = fs.existsSync(destination) && fs.statSync(destination).isFile() && fs.readFileSync(file).equals(fs.readFileSync(destination));
        if (!identical) this.files.log('update', `${this.files.pretty(file)} -> ${this.files.pretty(destination)}`);
        if (!this.files.dryRun) {
          const parent = realPath(path.dirname(destination));
          if (parent && within(parent, source)) throw new Error(`${destination}: points back into the local copy`);
          fs.mkdirSync(path.dirname(destination), { recursive: true });
          const mode = fs.statSync(destination, { throwIfNoEntry: false })?.mode;
          // Replacing a detached file must not write through a repo link into another file.
          if (this.files.target(destination)) fs.unlinkSync(destination);
          fs.copyFileSync(file, destination);
          if (mode !== undefined) fs.chmodSync(destination, mode & 0o777);
        }
      }
    }
    if (directory && !skill) {
      if (this.files.dryRun) for (const file of walk(source)) this.files.log('link', `${this.files.pretty(file)} -> ${this.files.pretty(path.join(target, path.relative(source, file)))}`);
      else await this.files.linkTree(target, source, !update);
    } else if (this.files.dryRun) this.files.log('link', `${this.files.pretty(source)} -> ${this.files.pretty(target)}`);
    else await this.files.link(target, source, !update);
  }
}
