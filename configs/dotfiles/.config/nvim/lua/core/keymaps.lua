local map = vim.keymap.set

map("n", "<leader>e", ":NvimTreeToggle<CR>", { desc = "Toggle file tree" })

map("n", "<leader>ff", ":Telescope find_files<CR>", { desc = "Find files" })
map("n", "<leader>fg", ":Telescope live_grep<CR>", { desc = "Live grep" })
map("n", "<leader>fb", ":Telescope buffers<CR>", { desc = "List buffers" })
map("n", "<leader>fh", ":Telescope help_tags<CR>", { desc = "Help tags" })

map("n", "<leader>gd", ":Telescope git_status<CR>", { desc = "Git status" })

map("n", "<leader>w", ":write<CR>", { desc = "Save file" })
map("n", "<leader>bd", ":bdelete<CR>", { desc = "Delete buffer" })

map("n", "<leader>q", ":qa<CR>", { desc = "Quit all" })
map("n", "<leader>f", ":lua require('conform').format()<CR>", { desc = "Format file" })


