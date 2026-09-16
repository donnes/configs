-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

vim.api.nvim_set_keymap("i", "jj", "<Esc>", { noremap = false })

-- Disable LazyVim default <C-s> save keymap (conflicts with tmux leader)
vim.keymap.del({ "i", "x", "n", "s" }, "<C-s>")

-- Save file with <leader>w in any mode
vim.keymap.set({ "n", "x" }, "<leader>w", "<cmd>w<cr><esc>", { desc = "Save File" })
vim.keymap.set({ "i", "s" }, "<leader>w", "<esc><cmd>w<cr>", { desc = "Save File" })
