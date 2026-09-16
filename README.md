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
./install --skip packages --skip codex
./install --only nvim --only atuin
./install uninstall --only nvim
./install --list-components
```

`--interactive` prompts for each component and defaults to installing it. Available components are `packages`, `skills`, `claude`, `codex`, `atuin`, `nvim`, `shell`, `tmux`, and `git`. `--skip-packages` remains available as an alias for `--skip packages`. Interactive mode cannot be combined with `--skip` or `--only`.

## Safety

- Files are linked individually with absolute symlinks; live state and foreign files remain untouched.
- Conflicts receive timestamped backups that are never overwritten.
- The installer never mirror-deletes and never writes below `/usr/share/omarchy`.
- Omarchy's bashrc and tmux config receive one replaceable marker block each.
- `./install uninstall` removes only managed links and marker blocks. Packages, backups, directories, and foreign files remain.

Always inspect `./install --dry-run` first.

## Layout

- `shared/`: agent, editor, Neovim, Atuin, and tool overlays
- `omarchy/`: bash/tmux deltas and vendored Omarchy Neovim keepers
- `macos/`: full zsh, git, and tmux configuration, plus `macos/bin` scripts linked into `~/.local/bin`
- `packages/`: platform package lists

Ghostty, Yazi, and SSH are tracked but excluded from the default run. Atuin's config is tracked; its history, encryption key, and sessions stay local.

Claude's `settings.json` and Codex's `config.toml` are profile-specific because
both applications write machine and platform paths into them. Portable commands,
rules, and agent instructions remain under `shared/`.

Omarchy Bash sources `shared/shell/git-aliases.bash`, a Bash-compatible port of
the commonly used Oh My Zsh Git aliases such as `gss`, `ggp`, `ggl`, `gst`,
and `gsw`. Omarchy's existing `g`, `gcm`, `gcam`, and `gcad` meanings are
preserved.

## Adopt new files

```sh
./install adopt ~/.claude/commands/example.md
./install adopt ~/.agents/skills/my-skill
```

`adopt` moves a new file or directory into the mapped repo location and replaces source files with symlinks. It refuses an existing repo destination.

## Update tracked files

```sh
./install update ~/.agents/skills/my-skill
./install update ~/.agents/.skill-lock.json
./install update ~/.claude/settings.json
```

`update` is the explicit local-wins operation for tracked files that are not linked
yet. It copies local files into their mapped repo location without deleting anything,
then replaces them with symlinks. Prefer updating one skill or file at a time; managed
roots such as `~/.agents/skills` are rejected so foreign content is not imported.

## Omarchy maintenance

`omarchy refresh tmux` can replace `~/.config/tmux/tmux.conf` and remove the managed include. Rerun `./install` to restore it.

The files under `omarchy/nvim/` were vendored from omarchy-nvim 2026.8.13-1. Recheck them after major Omarchy upgrades. The active theme remains Omarchy's state symlink, so `omarchy theme set` continues to hot-reload Neovim.

The macOS gitconfig is never installed on Omarchy.
