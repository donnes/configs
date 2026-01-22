local map = vim.keymap.set

map("n", "<leader>e", "<CMD>Neotree toggle<CR>", { desc = "Toggle explorer" })
map("n", "<leader>o", "<CMD>Neotree focus<CR>", { desc = "Focus explorer" })

-- Window navigation
map("n", "<C-h>", "<C-w>h", { desc = "Go to left window" })
map("n", "<C-j>", "<C-w>j", { desc = "Go to bottom window" })
map("n", "<C-k>", "<C-w>k", { desc = "Go to top window" })
map("n", "<C-l>", "<C-w>l", { desc = "Go to right window" })

map("n", "<leader>ff", ":Telescope find_files<CR>", { desc = "Find files" })
map("n", "<leader>fg", ":Telescope live_grep<CR>", { desc = "Live grep" })
map("n", "<leader>fb", ":Telescope buffers<CR>", { desc = "List buffers" })
map("n", "<leader>fh", ":Telescope help_tags<CR>", { desc = "Help tags" })
map("n", "<leader>fc", ":Telescope commands<CR>", { desc = "Find commands" })
map("n", "<leader>fk", ":Telescope keymaps<CR>", { desc = "Find keymaps" })
map("n", "<leader>cd", ":Telescope zoxide list<CR>", { desc = "Zoxide" })

map("n", "<leader>gd", ":Telescope git_status<CR>", { desc = "Git status" })

map("n", "<leader>w", ":write<CR>", { desc = "Save file" })
map("n", "<leader>bd", ":bdelete<CR>", { desc = "Delete buffer" })

map("n", "<leader>q", ":qa<CR>", { desc = "Quit all" })
map("n", "<leader>f", ":lua require('conform').format()<CR>", { desc = "Format file" })


