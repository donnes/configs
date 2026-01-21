# Agent Config Repository

Managed by [syncode](https://github.com/donnes/syncode)

## Setup on New Machine

```bash
# Install syncode
npm install -g @donnes/syncode

# Initialize from existing repo
syncode init
# When prompted, enter repo URL: https://github.com/donnes/configs.git

# Sync configs (creates symlinks)
syncode sync
# Select "Export"
```

## Synced Agents

- **Claude Code** (copy)
- **VSCode** (symlink)
- **Windsurf** (symlink)
- **Cursor** (symlink)
- **OpenCode** (symlink)


## Dotfiles

- Shell configs (.zshrc, .bashrc)
- Terminal configs (ghostty, tmux)

## Usage

```bash
# Check status
syncode status

# Sync changes
syncode sync

# Push to remote
git add .
git commit -m "Update configs"
git push
```
