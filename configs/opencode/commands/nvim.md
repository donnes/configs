---
description: Help tweak neovim configuration
model: opencode/glm-4.7
subtask: true
---

The neovim configuration is located at `/Users/donaldsilveira/.syncode/repo/configs/dotfiles/.config/nvim/`

When the user asks for neovim configuration changes:

1. First explore the relevant config files using Read tool
2. Understand the current structure and conventions
3. Make the requested changes using Edit tool
4. Test the changes if possible by running neovim linting commands if available

Key config locations:
- `init.lua` - main entry point
- `lua/core/` - core configuration (autocmds, keymaps, options)
- `lua/plugins/` - plugin configurations

Common neovim tasks:
- Add or modify plugin configurations
- Update keymaps in `lua/core/keymaps.lua`
- Set options in `lua/core/options.lua`
- Add autocmds in `lua/core/autocmds.lua`
- Configure floating windows
- Setup file watchers
- Add new plugins

Always follow the existing code style and conventions in the config files.