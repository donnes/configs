# Neovim Basics (This Config)

This folder contains a complete Neovim setup for JavaScript/TypeScript, React/Next.js, Tailwind, Python, and Go. It uses `lazy.nvim` for plugins, `mason.nvim` for language servers, `nvim-treesitter` for syntax, and `conform.nvim` with Biome for formatting.

## First launch

1. Open Neovim: `nvim`
2. Run `:Lazy sync` to install plugins
3. Run `:Mason` and install servers if needed (most will auto-install)
4. Run `:checkhealth` if something feels off

## What this config gives you

- File explorer: `nvim-tree`
- Fuzzy search: `telescope`
- LSP (code intelligence): vtsls, tailwindcss, pyright, gopls
- Formatting: Biome on save for JS/TS/TSX/JSON
- Treesitter highlighting + indentation
- Git signs in the gutter

## Key concepts

- **Normal mode**: your default mode (press `Esc` to return here)
- **Insert mode**: type text (press `i` to enter)
- **Command mode**: run commands (press `:`)
- **Leader key**: the spacebar (`<leader>`)

## Core keymaps in this setup

### Navigation and search

- `<leader>e` toggle file tree
- `<leader>ff` find files
- `<leader>fg` live grep
- `<leader>fb` list buffers
- `<leader>fh` help tags

### Git

- `<leader>gd` git status (Telescope)

### Buffers

- `<leader>bd` close buffer

### LSP (when attached)

- `gd` go to definition
- `gr` list references
- `K` hover docs
- `ga` code actions
- `rn` rename symbol
- `ds` document symbols
- `ws` workspace symbols

## Formatting

- Format on save is enabled for JS/TS/TSX/JSON via Biome.
- If you want to format manually: `:Format` (provided by conform.nvim).

## Helpful commands

- `:Lazy` plugin manager UI
- `:Mason` LSP installer UI
- `:LspInfo` see active LSPs
- `:checkhealth` diagnostics for Neovim

## Where things live

- Entry point: `init.lua`
- Options: `lua/core/options.lua`
- Keymaps: `lua/core/keymaps.lua`
- Plugins: `lua/plugins/*.lua`

If you want to customize anything, start with the keymaps or options files.
