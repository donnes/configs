import * as fs from 'node:fs';
import * as path from 'node:path';
import { spawnSync } from 'node:child_process';
import { exists, Files, realPath, run, walk, within } from './files.ts';
import { Skills } from './skills.ts';
import { Agents } from './agents.ts';
import { Mise } from './mise.ts';

export const components = ['packages', 'apps', 'agents', 'skills', 'mise', 'atuin', 'nvim', 'shell', 'tmux', 'git', 'session', 'command-center'] as const;
export type Component = typeof components[number];
export type Profile = 'macos' | 'omarchy';

export function available(profile: Profile) {
  const exclusive: Component[] = profile === 'macos' ? ['apps', 'session'] : ['git'];
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

// Omarchy's installers also set up what a bare package install skips, such as
// Steam's 32-bit GPU drivers, the Tailscale service and Zed's theme. Some open
// the app or start a Tailscale login, so each runs only while a package is missing.
// Apps without an installer go through Omarchy's package helpers instead.
type App = { name: string, packages: string[], installer?: [string, ...string[]], aur?: boolean };
const apps: App[] = [
  { name: 'Steam', packages: ['steam'], installer: ['omarchy-install-gaming-steam'] },
  { name: 'MangoHud', packages: ['mangohud', 'lib32-mangohud'] },
  { name: 'LACT', packages: ['lact'] },
  { name: 'racing wheel tools', packages: ['oversteer', 'new-lg4ff-dkms-git', 'usb_modeswitch'], aur: true },
  { name: 'Tailscale', packages: ['tailscale'], installer: ['omarchy-install-service-tailscale'] },
  { name: 'Zed', packages: ['zed', 'omazed'], installer: ['omarchy-install-editor-zed'] },
  { name: 'Zen', packages: ['zen-browser-bin'], installer: ['omarchy-install-browser', 'zen'] },
  { name: 'Helium', packages: ['helium-browser-bin'], aur: true },
];

export class Installer {
  readonly skills: Skills;

  constructor(private files: Files, private profile: Profile, private enabled: Set<Component>) {
    this.skills = new Skills(files);
  }

  private source(relative: string) { return path.join(this.files.repo, relative); }
  private destination(relative: string) { return path.join(this.files.home, relative); }

  private async component(name: Component, operation: () => void | Promise<void>) {
    if (this.enabled.has(name)) await operation();
    else this.files.log('skip', `${name} component disabled`);
  }

  private async tree(component: Component, source: string, destination: string, uninstall: boolean) {
    await this.component(component, () => uninstall
      ? this.files.unlinkTree(this.source(source), this.destination(destination))
      : this.files.linkTree(this.source(source), this.destination(destination)));
  }

  private async link(component: Component, source: string, destination: string, uninstall: boolean) {
    await this.component(component, () => uninstall
      ? this.files.unlink(this.source(source), this.destination(destination))
      : this.files.link(this.source(source), this.destination(destination)));
  }

  private async block(component: Component, destination: string, content: string, uninstall: boolean, comment = '#') {
    await this.component(component, () => this.files.block(this.destination(destination), uninstall ? undefined : content, comment));
  }

  private packages() {
    const { dryRun } = this.files;
    if (this.profile === 'omarchy') {
      this.files.log('package', `yay -S --needed - < ${this.files.pretty(this.source('packages/omarchy.txt'))}`);
      if (!dryRun) run('yay', ['-S', '--needed', '-'], fs.readFileSync(this.source('packages/omarchy.txt'), 'utf8'));
      return;
    }
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
    this.files.log('package', `${brew} install < ${this.files.pretty(this.source('packages/macos.txt'))}`);
    this.files.log('package', `${brew} trust --tap abue-ammar/tinycast`);
    this.files.log('package', `${brew} install --cask < ${this.files.pretty(this.source('packages/macos-casks.txt'))}`);
    if (!dryRun) {
      run(brew, ['install', ...fs.readFileSync(this.source('packages/macos.txt'), 'utf8').split(/\s+/).filter(Boolean)]);
      run(brew, ['trust', '--tap', 'abue-ammar/tinycast']);
      run(brew, ['install', '--cask', ...fs.readFileSync(this.source('packages/macos-casks.txt'), 'utf8').split(/\s+/).filter(Boolean)]);
    }
  }

  private apps() {
    for (const { name, packages, installer, aur } of apps) {
      const present = spawnSync('omarchy-pkg-present', packages, { stdio: 'ignore' }).status === 0;
      const [command, ...args] = installer ?? [aur ? 'omarchy-pkg-aur-add' : 'omarchy-pkg-add', ...packages];
      this.files.log(present ? 'skip' : 'app', present ? `${name}: already installed` : `${name}: ${[command, ...args].join(' ')}`);
      if (!present && !this.files.dryRun) run(command, args);
    }
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
    await this.tree('session', 'omarchy/hypr', '.config/hypr', uninstall);
    await this.tree('session', 'omarchy/systemd/user', '.config/systemd/user', uninstall);
    this.files.block(config, uninstall ? undefined : 'require("hypr.session")', '--');
    if (!uninstall) this.files.log('enable', `systemd user timer ${timer}`);
    if (!this.files.dryRun) {
      run('systemctl', ['--user', 'daemon-reload']);
      if (!uninstall) run('systemctl', ['--user', 'enable', '--now', timer]);
    }
  }

  private async shared(uninstall: boolean) {
    await this.component('agents', () => new Agents(this.files, this.profile).apply(uninstall));
    await this.component('skills', () => uninstall ? this.skills.uninstall() : this.skills.install());
    await this.component('command-center', () => this.skills.commandCenter(uninstall));
    await this.component('mise', () => new Mise(this.files, this.profile).apply(uninstall));
    await this.tree('atuin', 'shared/atuin', '.config/atuin', uninstall);
    await this.component('nvim', () => this.nvim(uninstall));
    if (!uninstall) for (const name of ['ghostty', 'yazi', 'ssh']) this.files.log('skip', `shared/${name} is excluded from the default install`);
  }

  private async platform(uninstall: boolean) {
    if (this.profile === 'macos') {
      await this.link('shell', 'macos/zshrc', '.zshrc', uninstall);
      await this.block('shell', '.zshenv', `source "${this.source('macos/zshenv')}"`, uninstall);
      // macOS login shells reorder PATH after .zshenv, so mise's shims go in .zprofile.
      await this.block('shell', '.zprofile', `source "${this.source('macos/zprofile')}"`, uninstall);
      await this.tree('shell', 'macos/bin', '.local/bin', uninstall);
      await this.link('git', 'macos/gitconfig', '.gitconfig', uninstall);
      await this.link('tmux', 'macos/tmux.conf', '.tmux.conf', uninstall);
    } else {
      await this.block('shell', '.bashrc', `source "${this.source('omarchy/bashrc.local')}"`, uninstall);
      await this.tree('shell', 'omarchy/uwsm', '.config/uwsm', uninstall);
      await this.tree('shell', 'omarchy/bin', '.local/bin', uninstall);
      await this.component('session', () => this.session(uninstall));
      await this.component('tmux', async () => {
        const config = this.destination('.config/tmux/tmux.conf');
        if (!uninstall && !this.files.dryRun && !fs.existsSync(config)) throw new Error(`${config} is missing; restore Omarchy's tmux config first`);
        await this.link('tmux', 'omarchy/tmux.local.conf', '.config/tmux/local.conf', uninstall);
        this.files.block(config, uninstall ? undefined : 'source-file -q ~/.config/tmux/local.conf');
      });
    }
  }

  async apply(uninstall: boolean) {
    console.log(`Profile: ${this.profile}\nRepo:    ${this.files.repo}\n`);
    if (!uninstall) {
      await this.component('packages', () => this.packages());
      if (this.profile === 'omarchy') await this.component('apps', () => this.apps());
      await this.shared(false);
      await this.platform(false);
    } else {
      await this.platform(true);
      await this.shared(true);
      this.files.log('note', 'packages and apps were left untouched');
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
