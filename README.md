# configs

Personal AI-agent and editor configuration, layered onto Omarchy or macOS without replacing machine-owned configuration directories.

## Install

```sh
git clone https://github.com/donnes/configs.git ~/.donnes/configs
~/.donnes/configs/cli --dry-run
~/.donnes/configs/cli
```

Or bootstrap the canonical checkout:

```sh
curl -fsSL https://raw.githubusercontent.com/donnes/configs/main/cli | bash
```

Review the downloaded script before piping it to Bash. An existing `~/.donnes/configs` checkout is never pulled or overwritten automatically. The profile is Omarchy when `/usr/share/omarchy` exists, otherwise macOS on Darwin.

Node.js >=20.12.0 and npm are required. `cli` is a small Bash launcher; the
implementation lives in `scripts/` as TypeScript and uses `@clack/prompts` for
terminal interaction. The launcher installs its locked npm dependencies into
this checkout when they are missing, including on the first dry run. Managed
configuration files remain unchanged during a dry run. Run `npm ci` after
pulling dependency changes. Python is only needed to run the test suite.

Choose what the installer manages with repeatable `--skip` or `--only` options:

```sh
./cli --interactive
./cli --skip packages --skip nvim
./cli --only nvim --only atuin
./cli uninstall --only nvim
./cli --list-components
```

`--interactive` opens a Clack multiselect with the default components selected.
Use Space to toggle components and Enter to continue; Ctrl-C cancels. Available
components are `packages`, `gh-extensions`, `apps` (Omarchy only), `agents`, `skills`, `mise`, `atuin`, `nvim`, `gradle`, `shell`, `tmux`,
`git`, `session` (Omarchy only), `command-center` and `rea`. `command-center`
is unchecked and excluded from the default install; default uninstall
includes it; `rea` is always opt-in. `--skip-packages` remains an
alias for `--skip packages`. Interactive mode cannot be combined with `--skip`
or `--only`, and requires a terminal. Unattended agent and SSH sessions use
explicit commands and flags; differing local copies are preserved when no
terminal is attached. `./cli install` is equivalent to `./cli`.

## Health check

`./cli health` checks the machine against the repository for the detected OS and
changes nothing:

- the configs checkout: uncommitted changes, or commits behind its upstream as of the last fetch;
- the apply receipt: whether the last install finished, kept differing local copies, or failed, and at which revision;
- managed files: anything `./cli` would link, relink or rewrite, taken from its own dry run, for every known Codex home and Claude config directory, with the `--only` selection that would fix it; and a Codex `AGENTS.override.md` that replaces the installed instructions;
- the machine's role: command-center skills where the role is `command-center`, and none on a worker;
- packages: Homebrew formulae and casks on macOS, pacman packages and Omarchy apps on Omarchy, and opencode v2 and the listed gh extensions on both;
- mise: every tool the shared fragment requests configured and installed, `mise doctor` clean in a new shell, and machine config that requests a different version than the fragment;
- tool resolution: each tool's executable found through mise in a new terminal's shell, started with a clean environment so this process's PATH can't hide problems in startup files. Omarchy's `~/.local/bin` wrappers, which run `mise x`, and Vite+ shims in system-first mode count as mise; with `jsRuntimes` set to `vite-plus`, node, npm, pnpm, yarn and bun must resolve to Vite+'s own runtimes instead;
- global duplicates: a copy of a mise tool in bun's or pnpm's global bin directory, such as a `bun add -g` install or a standalone bun;
- leftover version managers: fnm, nvm, pyenv, rbenv, asdf or volta on PATH or in their usual directories;
- background jobs: the launchd agents, their last exit code and the GUI PATH on macOS; the systemd timers and their services' last result on Omarchy; and jobs that stopped running.

Drift and leftovers are warnings. Missing packages, tools or jobs, failed jobs,
and probes that cannot answer are failures, and make the command exit with
status 1. REA is optional and only reported; its scoped doctor is below.

`./cli health --json` prints every check with its status and id, plus the
checkout and mise's resolved versions, for comparing machines.
`./cli health --strict` also fails on each warning that is not a recorded
exception, and prints the id to record.

### Receipts and machine intent

Each install or uninstall that is not a dry run writes a private receipt to
`${XDG_STATE_HOME:-~/.local/state}/donnes-configs/receipt.json`: the checkout
revision and whether it had uncommitted changes, the selected components, the
outcome (`complete`, `kept-conflicts` or `failed`, with the failing component),
differing local copies that were kept, the runtime homes that agents and skills
went into, and mise's resolved versions. Each component keeps the record of its
last finished run, so a failed or partial run never marks it current. A machine
set up before receipts has none until its next run, and health says so rather
than assuming the earlier state.

Health also reads an optional, hand-written
`${XDG_CONFIG_HOME:-~/.config}/donnes-configs/machine.json`:

```json
{
  "role": "worker",
  "jsRuntimes": "mise",
  "codexHomes": ["~/.codex", "~/.codex-work"],
  "claudeConfigDirs": ["~/.claude"],
  "exceptions": { "override:node": "this box keeps Node 26 as its default" }
}
```

`role` is `command-center` or `worker`; without it health falls back to whether
the receipt shows `command-center` installed. `jsRuntimes` is `mise`, the
default, or `vite-plus`; see Vite+ below. Listed homes are checked even
before anything was installed into them. Each exception maps a check id from
`--json` or `--strict` to the reason it is accepted; health reports exceptions
that no longer match anything. Keep it to this machine's own intent;
`COMPUTERS.md` and `COMPUTERS.local.md` stay the human inventory.

## Safety

- Files are linked individually with absolute symlinks; live state and foreign files remain untouched.
- Skills are the exception: each `shared/skills/<name>` is linked as one directory, because Codex ignores a symlinked `SKILL.md` but follows a symlinked skill directory. Skills are linked into both `~/.agents/skills` (Codex and others) and `~/.claude/skills` (Claude Code, which does not read `~/.agents`). Untracked skills in either directory remain untouched.
- Nothing is backed up. A link that already resolves to the repo copy (such as `~/.claude/skills/x -> ../../.agents/skills/x`) or a local copy with identical content is relinked. A local file, directory, or skill whose content differs prompts to keep it, replace it with the repo version, update the repo from it, or show the diff; the default is whichever side was modified most recently. Without a terminal, differing copies are kept and reported. Untracked files inside managed directories such as `~/.config/nvim` stay in place.
- The installer never mirror-deletes and never writes below `/usr/share/omarchy`.
- Generated instructions offer keep, replace, and diff; edit their source documents instead of updating the generated copy from a local file.
- Omarchy's bashrc, tmux config, and `hypr/hyprland.lua`, and macOS's `~/.zshenv`, `~/.zprofile`, and `~/.gitconfig`, receive one replaceable marker block each. `~/.gitconfig` stays a local file for identity and account routing; its block includes `macos/gitconfig`.
- `./cli uninstall` removes only managed links and marker blocks. Packages, apps, mise settings, directories, and foreign files remain.

Always inspect `./cli --dry-run` first.

## Layout

- `shared/`: agent, editor, Neovim, Atuin, and tool overlays
- `omarchy/`: bash/tmux deltas, vendored Omarchy Neovim keepers, `omarchy/bin` scripts linked into `~/.local/bin`, and the Hyprland session files (`hypr/`, `systemd/user/`)
- `macos/`: full zsh, git, and tmux configuration, plus `macos/bin` scripts linked into `~/.local/bin`
- `shared/git/ignore`: the global gitignore on both machines, linked to `~/.config/git/ignore`; only macOS also gets `macos/gitconfig`
- `macos/gradle.properties`, `omarchy/gradle.properties`: linked to `~/.gradle/gradle.properties`, so local Android builds target the machine's emulator ABI and share Gradle's build cache
- `packages/`: platform package lists, plus `gh-extensions.txt`, the gh extensions both machines install with the `gh-extensions` component
- `shared/mise/`: shared mise tools and settings; `omarchy/mise/`: the prune timer
- `scripts/`: TypeScript CLI entry point and filesystem, installation, health, receipt, prompt, and skill modules
- `fleet/skills/`: command-center workflows, installed only when selected
- `COMPUTERS.md`: portable machine roles and desired setup; private connections live in ignored `COMPUTERS.local.md`

Run `npm run check` for TypeScript checking and `npm test` for CLI behavior tests.

Ghostty, Yazi, and SSH are tracked but excluded from the default run. Atuin's config is tracked; its history, encryption key, and sessions stay local.

The `agents` component composes `shared/agents/global/AGENTS.md` with
`macos/agents/CONTEXT.md` on macOS or `linux/agents/CONTEXT.md` on Omarchy.
It generates an ignored `.generated/agents/<profile>/AGENTS.md` and links it to
Codex's `~/.codex/AGENTS.md` (or `$CODEX_HOME/AGENTS.md`) and Claude Code's
`~/.claude/CLAUDE.md` (or `$CLAUDE_CONFIG_DIR/CLAUDE.md`). Rerun
`./cli --only agents` after editing either source, then start fresh sessions.
Do not edit the generated file. See [agent setup](shared/agents/README.md).
Other Claude and Codex settings, credentials, and runtime state stay local.

## Machine setup

The MacBook is the command center; donnes-pc is an Omarchy worker. Keep the
desired roles in [COMPUTERS.md](COMPUTERS.md) and verified hostnames, SSH aliases,
checkout paths, runtime homes, and exceptions in the ignored local inventory.

```sh
# Command center, including the provision-box skill.
./cli --dry-run --only agents,skills,command-center
./cli --only agents,skills,command-center

# Worker or routine shared-guidance refresh.
./cli --dry-run --only agents,skills
./cli --only agents,skills

# Selected non-default runtime homes.
CODEX_HOME="$HOME/.codex-work" CLAUDE_CONFIG_DIR="$HOME/.claude-work" ./cli --only agents,skills
```

Install instructions for each selected Codex/Claude home using its actual
environment variables. Codex shares the user-level `.agents/skills` collection;
Claude uses `<selected config directory>/skills`. No auth files are copied.
Existing default profiles remain untouched when a different home is selected.

Use [provision-box](fleet/skills/provision-box/SKILL.md) when asked to provision
or refresh a named box. It discovers the target, selects an agreed published
revision, previews explicit components, applies the requested scope, and verifies
the result from the target's receipt and `./cli health --json`. This CLI manages a local machine; the skill runs it on a remote
target through that target's existing SSH configuration. There is no background
sync service or second installer.

Neovim plugin specifications are shared, while each profile tracks its own
`lazy-lock.json`. Run `:Lazy sync` and commit the resulting profile lockfile on
each platform when shared plugin specifications change.

Untracked secrets live in `~/.secrets` as `export NAME=value` lines. They are
sourced where non-interactive processes can see them, because GUI apps and the
AI agents they spawn never run an interactive shell: macOS sources them from
`macos/zshenv` (every zsh, via the `~/.zshenv` block), and Omarchy from
`omarchy/uwsm/env.d/90-secrets` (the whole graphical session, after the next
login) as well as `omarchy/bashrc.local` for interactive shells.

Omarchy Bash sources `shared/shell/git-aliases.bash`, a Bash-compatible port of
the commonly used Oh My Zsh Git aliases such as `gss`, `ggp`, `ggl`, `gst`,
and `gsw`. Omarchy's existing `g`, `gcm`, `gcam`, and `gcad` meanings are
preserved.

## Hyprland session restore

The Omarchy `session` component brings windows back after a crash or power cut.
`hypr-session` (from `omarchy/bin`) saves which apps are open, how to relaunch
them, and where their windows sit; `hypr-session-autosave.timer` snapshots the
session every minute; and `hypr/session.lua`, required from `hyprland.lua`,
runs `hypr-session resume` at login and binds Super+Shift+Alt+L (save) and
Super+Alt+L (restore). Snapshots live in `~/.local/state/hypr-session/`.
Unattended recovery also needs the firmware set to power on after AC loss and
a disk that unlocks without a passphrase prompt.

## Adopt new files

```sh
./cli adopt ~/.config/atuin/example.toml
./cli adopt ~/.agents/skills/my-skill
```

On Omarchy, `~/.local/bin`, `~/.config/hypr`, and `~/.config/systemd/user` also map into `omarchy/`. `adopt` moves a new file or directory into the mapped repo location and replaces source files with symlinks (a skill directory becomes a single directory symlink). It refuses an existing repo destination.

## Update tracked files

```sh
./cli update ~/.agents/skills/my-skill
./cli update ~/.agents/.skill-lock.json
```

`update` is the explicit local-wins operation for tracked files that are not linked
yet. It copies local files into their mapped repo location without deleting anything,
then replaces them with symlinks. Prefer updating one skill or file at a time; managed
roots such as `~/.agents/skills` are rejected so foreign content is not imported.

The installer symlinks the local skills lockfile to `shared/skills.lock.json`,
just as it symlinks skill directories. Edits through that link reach the repo.
A CLI that saves by replacing the file can replace the symlink with a regular file.

Skills lockfiles use a merge instead. `./cli update ~/.agents/.skill-lock.json` retains entries
from both `shared/skills.lock.json` and the local lockfile, uses local values for
conflicting entries and restores its symlink.
Skills installation also runs this sync. An
existing managed symlink needs no changes. Run the command after a skills CLI
update if its file replacement detached the symlink, then review and commit the
repo diff. Entries absent from the local file remain in the repo; remove unwanted
entries explicitly from the linked lockfile.

The local path is `~/.agents/.skill-lock.json`, or
`$XDG_STATE_HOME/skills/.skill-lock.json` when `XDG_STATE_HOME` is set. Merging a
detached lockfile runs in the CLI. Invalid JSON and mismatched lockfile versions
stop the sync before either file changes. Use `--dry-run` to validate and preview
the merge and link operations.

## Remove tracked skills

```sh
./cli remove-skill
./cli remove-skill --dry-run my-skill
./cli remove-skill my-skill another-skill
```

Without names, the command opens a Clack multiselect of tracked skills
and asks for confirmation before deletion. Selecting nothing or pressing Ctrl-C cancels. With
`--dry-run`, it previews the selected removals without deleting anything.

`remove-skill` handles both `shared/skills` and `fleet/skills`. It deletes the tracked skill directories, removes agent symlinks that
point to them, and removes their entries from the repo and local skills lockfiles.
It also accepts stale lockfile entries whose directories are already gone.
Unmanaged copies in `~/.agents/skills` or `~/.claude/skills` must be synced first.
Names and lockfiles are checked before deletion begins.
Backups remain untouched. Unlike `npx skills remove`, this command handles our
symlinked skill directories and removes the repo copy so reinstalling cannot
restore a deleted skill.

## Omarchy maintenance

`omarchy refresh tmux` can replace `~/.config/tmux/tmux.conf` and remove the managed include. Rerun `./cli` to restore it.

The files under `omarchy/nvim/` were vendored from omarchy-nvim 2026.8.13-1. Recheck them after major Omarchy upgrades. The active theme remains Omarchy's state symlink, so `omarchy theme set` continues to hot-reload Neovim.

The macOS gitconfig is never installed on Omarchy.

## Packages and upgrades

`packages` installs what is missing from the platform lists and opencode v2;
`gh-extensions` installs what is missing from `packages/gh-extensions.txt`.
Neither asks to upgrade a listed package that is already installed, so an
unattended run with everything present changes nothing. Installing a missing
package can still upgrade what it depends on: Homebrew upgrades outdated
dependencies of a new formula, and pacman may need newer libraries. On Omarchy, missing packages go through
`yay`, which prompts, so they need a terminal; the run stops with the missing
names instead of hanging. Select `gh-extensions` alone to install an extension
without touching system packages. A missing cask or formula from a third-party
tap has its tap trusted first.

Upgrades are explicit, one tool at a time, with the tools' own commands:
`brew upgrade [name]`, `yay -Syu`, `mise up [tool]`, `gh extension upgrade --all`
and `opencode upgrade`. Review what they will change first (`brew outdated`,
`mise outdated`); a cask upgrade can quit or reinstall a running app.

## Omarchy apps

The `apps` component installs Steam, MangoHud, LACT, the Logitech racing wheel
tools, Tailscale, Zed, Zen, and Helium. Each goes through Omarchy's own
installer where one exists, which also sets up drivers, services, or themes, or
through Omarchy's package helpers otherwise. An app is installed only while one
of its packages is missing, because some installers open the app or start a
Tailscale login. Edit the list in `scripts/lib/install.ts`.

## mise

mise manages language runtimes and agent CLIs on both profiles; Homebrew and
pacman keep system packages. The `mise` component links
`shared/mise/conf.d/donnes.toml` into `~/.config/mise/conf.d/`. mise loads it
before `~/.config/mise/config.toml`, which stays machine-owned: `mise use -g`
and Omarchy write there, and its values win. Projects pin versions with
`.nvmrc`, `.node-version`, `.ruby-version`, `.python-version`, or `mise.toml`.
Missing versions are not installed automatically; run `mise install` in the
project.

On Omarchy the CLI never edits Omarchy's files. Omarchy's `config.toml` replaces
the shared list of version files mise reads, so the component appends the
missing tools with `mise settings add`. Omarchy's other settings stay, including
`upgrade.auto_prune = false`, which keeps `mise up` from deleting a version a
running session uses; the daily prune does the cleanup instead.

opencode stays outside mise, which only publishes the v1 line. The `packages`
component runs opencode's v2 installer (`https://opencode.ai/v2/install`) while
`~/.opencode/bin/opencode` is missing or older than v2; opencode upgrades itself
from there. The shell startup files, the macOS GUI PATH and Omarchy's uwsm
environment put `~/.opencode/bin` first.

`mise prune` runs daily (a launchd agent on macOS, `mise-prune.timer` on
Omarchy). It deletes versions that no tracked config selects and keeps those a
running process started from. Upgrades stay manual: `mise up`.

### Versions across machines

The same configs revision does not mean the same runtimes. The shared fragment
requests `latest` or `lts` for most tools, so each machine resolves whatever was
current when it last ran `mise install` or `mise up`, and a machine's own
`config.toml` can request something else. Pins go where agreement matters: in
the fragment for a tool whose `latest` is wrong (`npm:cf`), and in each
project's version files for its runtimes. Health warns about a machine config
that requests a different version than the fragment (`override:<tool>`); record
an intentional one as an exception in `machine.json`. The receipt keeps the
versions each run resolved, and `./cli health --json` reports the current ones,
so the command center can compare machines without changing them.

### Vite+

Vite+ installs its own `vp` into `~/.vite-plus` and puts `~/.vite-plus/bin`
first on PATH from the startup files, with shims for node, npm, pnpm, yarn and
bun. In Vite+'s default managed mode those shims run Vite+'s own runtimes, a
`vp env use` session override outranks project pins, and Node child processes
get Vite+'s runtime first on PATH, so terminals disagree with mise, agents and
Xcode. mise owns those runtimes by default: the `mise` component runs
`vp env off`, Vite+'s system-first mode, whenever a scope is still managed, and
the shims then hand each command to mise's. `vp` itself stays Vite+'s install;
the fragment's `github:voidzero-dev/vite-plus` provides it to GUI apps and a new
machine. Health counts a system-first shim that resolves to mise as mise, and
warns about a managed one.

A machine that should run Vite+'s runtimes in terminals says so with
`"jsRuntimes": "vite-plus"` in `machine.json`. The `mise` component then runs
`vp env on` instead whenever a scope is in system-first mode, its preview and
health agree, and health accepts node, npm, pnpm, yarn and bun only when they
resolve to Vite+'s own installs. Running `vp env on` or `off` by hand without
changing `jsRuntimes` is drift that the next apply reverts. GUI apps and Xcode
still use mise's shims either way.

### Xcode

On macOS the component also sets the PATH that GUI apps such as Xcode receive,
with mise's shims first. React Native and Expo record an exact Node install in
`ios/.xcode.env.local` on the first `pod install`; `xcode-node-env` repoints a
`NODE_BINARY` that names an exact mise or Vite+ Node install at the Node shim,
which selects each project's version when Xcode builds. Any other value, such
as a Homebrew Node or a command substitution, is a deliberate choice and stays.

The daily job sweeps `~/Git` and T3 worktrees right before pruning, because
pruning is what breaks a recorded path, including in projects nobody touched by
hand. If the sweep cannot search a directory or rewrite a file, it exits non-zero
and that day's prune is skipped; health reports the job's failed exit. Preview
or fix a project directly after a fresh `pod install`:

```sh
xcode-node-env --dry-run ~/Git/my-app
xcode-node-env ~/Git/my-app
```

## REA for Codex and Claude Code

REA is an opt-in integration, pinned to 6.5.0 in the CLI:

```sh
./cli --dry-run --only rea
./cli --only rea
npx --yes rea-agents@6.5.0 doctor --client codex --client claude_code --skill --json
```

The preview prints the setup command without executing it. To inspect REA's
exact proposed paths before applying, run that command with `--dry-run`.
Applying explicitly selects Codex and Claude Code, approves their setup, and
lets REA preserve unrelated configuration and create its own backups. Restart
both clients after installation to discover the MCP tools and skills.

REA owns regular skill directories in `~/.agents/skills` and `~/.claude/skills`;
its updater rejects symlinks, so do not adopt these into `shared/skills`.
`CODEX_HOME` and `CLAUDE_CONFIG_DIR` select alternate profiles when set.
No global package or analysis engine is installed. Engines such as Ghidra need
separate setup for tasks that require them. Use the scoped doctor above for
REA readiness; `./cli health` only reports whether the receipt records an REA
apply, because the doctor downloads and runs REA's installer.

Routine installs skip REA. Uninstall leaves it intact because REA's upstream
uninstall affects all registered clients, not only these two. Review
`npx --yes rea-agents@6.5.0 uninstall --help` before removing it. To update,
review the new release's setup dry run, change the pinned version here and in
`scripts/lib/install.ts`, then apply the REA component again.
