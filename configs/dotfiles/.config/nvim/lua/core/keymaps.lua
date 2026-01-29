local map = vim.keymap.set

-- Window navigation
map("n", "<C-h>", "<C-w>h", { desc = "Go to left window" })
map("n", "<C-j>", "<C-w>j", { desc = "Go to bottom window" })
map("n", "<C-k>", "<C-w>k", { desc = "Go to top window" })
map("n", "<C-l>", "<C-w>l", { desc = "Go to right window" })

map("n", "<leader>w", ":write<CR>", { desc = "Save file" })
map("n", "<leader>bd", ":bdelete<CR>", { desc = "Delete buffer" })
map("n", "<leader>q", function()
  if vim.api.nvim_buf_get_name(0) ~= "" then
    vim.cmd("bdelete")
    require("alpha").start(true)
  end
end, { desc = "Close file and open main screen" })
map("n", "<leader>qq", ":qa<CR>", { desc = "Quit all" })

