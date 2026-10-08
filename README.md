# configs

Personal AI-agent and editor configuration, layered onto Omarchy or macOS without replacing machine-owned configuration directories.

## Install

```sh
git clone https://github.com/donnes/configs.git ~/.donnes/configs
~/.donnes/configs/install --dry-run
~/.donnes/configs/install
```

Or bootstrap the canonical checkout:

```sh
curl -fsSL https://raw.githubusercontent.com/donnes/configs/main/install | bash
```

Review the downloaded script before piping it to Bash. An existing `~/.donnes/configs` checkout is never pulled or overwritten automatically. The profile is Omarchy when `/usr/share/omarchy` exists, otherwise macOS on Darwin.

Choose what the installer manages with repeatable `--skip` or `--only` options:

```sh
./install --interactive
./install --skip packages --skip nvim
./install --only nvim --only atuin
./install uninstall --only nvim
./install --list-components
```

`--interactive` prompts for each component and defaults to installing it. Available components are `packages`, `agents`, `skills`, `atuin`, `nvim`, `shell`, `tmux`, `git`, and `session` (Omarchy only). `--skip-packages` remains available as an alias for `--skip packages`. Interactive mode cannot be combined with `--skip` or `--only`.

## Safety

- Files are linked individually with absolute symlinks; live state and foreign files remain untouched.
- Skills are the exception: each `shared/skills/<name>` is linked as one directory, because Codex ignores a symlinked `SKILL.md` but follows a symlinked skill directory. Skills are linked into both `~/.agents/skills` (Codex and others) and `~/.claude/skills` (Claude Code, which does not read `~/.agents`). Untracked skills in either directory remain untouched.
- Nothing is backed up. A link that already resolves to the repo copy (such as `~/.claude/skills/x -> ../../.agents/skills/x`) or a local copy with identical content is relinked. A local file, directory, or skill whose content differs prompts to keep it, replace it with the repo version, update the repo from it, or show the diff; the default is whichever side was modified most recently. Without a terminal, differing copies are kept and reported. Untracked files inside managed directories such as `~/.config/nvim` stay in place.
- The installer never mirror-deletes and never writes below `/usr/share/omarchy`.
- Omarchy's bashrc, tmux config, and `hypr/hyprland.lua`, and macOS's `~/.zshenv`, receive one replaceable marker block each.
- `./install uninstall` removes only managed links and marker blocks. Packages, directories, and foreign files remain.

Always inspect `./install --dry-run` first.

## Layout

- `shared/`: agent, editor, Neovim, Atuin, and tool overlays
- `omarchy/`: bash/tmux deltas, vendored Omarchy Neovim keepers, `omarchy/bin` scripts linked into `~/.local/bin`, and the Hyprland session files (`hypr/`, `systemd/user/`)
- `macos/`: full zsh, git, and tmux configuration, plus `macos/bin` scripts linked into `~/.local/bin`
- `packages/`: platform package lists

Ghostty, Yazi, and SSH are tracked but excluded from the default run. Atuin's config is tracked; its history, encryption key, and sessions stay local.

The `agents` component links `shared/agents/global/AGENTS.md` to Codex's
`~/.codex/AGENTS.md` (or `$CODEX_HOME/AGENTS.md`) and Claude Code's
`~/.claude/CLAUDE.md`. Run `./install --only agents` to activate just these
instructions, then start fresh sessions. See [agent setup](shared/agents/README.md).
Other Claude and Codex settings, credentials, and runtime state stay local.

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
./install adopt ~/.config/atuin/example.toml
./install adopt ~/.agents/skills/my-skill
```

On Omarchy, `~/.local/bin`, `~/.config/hypr`, and `~/.config/systemd/user` also map into `omarchy/`. `adopt` moves a new file or directory into the mapped repo location and replaces source files with symlinks (a skill directory becomes a single directory symlink). It refuses an existing repo destination.

## Update tracked files

```sh
./install update ~/.agents/skills/my-skill
./install update ~/.agents/.skill-lock.json
```

`update` is the explicit local-wins operation for tracked files that are not linked
yet. It copies local files into their mapped repo location without deleting anything,
then replaces them with symlinks. Prefer updating one skill or file at a time; managed
roots such as `~/.agents/skills` are rejected so foreign content is not imported.

The installer symlinks the local skills lockfile to `shared/skills.lock.json`,
just as it symlinks skill directories. Edits through that link reach the repo.
A CLI that saves by replacing the file can replace the symlink with a regular file.

Skills lockfiles use a merge instead. `./install update ~/.agents/.skill-lock.json` retains entries
from both `shared/skills.lock.json` and the local lockfile, uses local values for
conflicting entries, backs up the detached local file, and restores its symlink.
Skills installation also runs this sync. An
existing managed symlink needs no changes. Run the command after a skills CLI
update if its file replacement detached the symlink, then review and commit the
repo diff. Entries absent from the local file remain in the repo; remove unwanted
entries explicitly from the linked lockfile.

The local path is `~/.agents/.skill-lock.json`, or
`$XDG_STATE_HOME/skills/.skill-lock.json` when `XDG_STATE_HOME` is set. Merging a
detached lockfile requires Python 3. Invalid JSON and mismatched lockfile versions
stop the sync before either file changes. Use `--dry-run` to validate and preview
the merge and link operations.

## Remove tracked skills

```sh
./install remove-skill
./install remove-skill --dry-run my-skill
./install remove-skill my-skill another-skill
```

Without names, the command lists tracked skills, accepts one or more numbers,
and asks for confirmation before deletion. Enter or Ctrl-C cancels. With
`--dry-run`, it previews the selected removals without deleting anything.

`remove-skill` deletes the tracked skill directories, removes agent symlinks that
point to them, and removes their entries from the repo and local skills lockfiles.
It also accepts stale lockfile entries whose directories are already gone.
Unmanaged copies in `~/.agents/skills` or `~/.claude/skills` must be synced first.
Names and lockfiles are checked before deletion begins. Python 3 is required.
Backups remain untouched. Unlike `npx skills remove`, this command handles our
symlinked skill directories and removes the repo copy so reinstalling cannot
restore a deleted skill.

## Omarchy maintenance

`omarchy refresh tmux` can replace `~/.config/tmux/tmux.conf` and remove the managed include. Rerun `./install` to restore it.

The files under `omarchy/nvim/` were vendored from omarchy-nvim 2026.8.13-1. Recheck them after major Omarchy upgrades. The active theme remains Omarchy's state symlink, so `omarchy theme set` continues to hot-reload Neovim.

The macOS gitconfig is never installed on Omarchy.
