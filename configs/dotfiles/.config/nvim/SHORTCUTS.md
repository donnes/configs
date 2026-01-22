# Neovim Shortcuts

## Leader Key
- Leader: Space (your configured leader key)

## Basic Navigation
- `h/j/k/l`: Move left/down/up/right
- `w/b`: Jump word forward/backward
- `0/$`: Beginning/end of line
- `gg/G`: Top/bottom of file
- `:42`: Jump to line 42
- `Ctrl+u/Ctrl+d`: Scroll half page up/down

## Editing
- `i/a/o/O`: Insert mode (before/after/current line/above)
- `Esc`: Exit insert mode to normal
- `x/dd`: Delete char/line
- `yy/p`: Copy (yank)/paste line
- `u/Ctrl+r`: Undo/redo
- `v/V/Ctrl+v`: Visual modes (char/line/block)

## File Operations
- `:w`: Quick save
- `:q/:wq/:q!`: Quit/save and quit/force quit
- `:e file`: Open file
- `:Ex/:NvimTreeToggle`: File explorer (if nvim-tree installed)
- `Ctrl+w w`: Jump between windows/splits

## Formatting
- `==`: Format current line
- `gg=G`: Format entire file
- `Ctrl+w =`: Equalize window sizes

## Search & Replace
- `/pattern`: Search forward
- `n/N`: Next/previous match
- `:%s/old/new/g`: Replace all in file

## Leader Key Shortcuts (assuming space)
- `<leader>w`: Save (if mapped)
- `<leader>q`: Quit (if mapped)
- `<leader>f`: Format (if mapped)
- `<leader>e`: Toggle explorer (if mapped)

## Productivity Tips
- `:help`: Get help on commands
- `:set number`: Show line numbers
- `:set relativenumber`: Relative line numbers
- Use `:TSInstall <lang>` for Treesitter syntax
- Custom mappings: Add to ~/.config/nvim/init.vim/lua