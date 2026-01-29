return {
  {
    "nvim-telescope/telescope.nvim",
    dependencies = {
      "nvim-lua/plenary.nvim",
      "jvgrootveld/telescope-zoxide",
      "nvim-telescope/telescope-ui-select.nvim",
    },
    config = function()
      local telescope = require("telescope")
      telescope.setup({
        defaults = {
          layout_strategy = "horizontal",
          layout_config = { prompt_position = "top" },
          sorting_strategy = "ascending",
          winblend = 5,
          file_ignore_patterns = { "%.DS_Store" },
        },
        extensions = {
          ["ui-select"] = {
            require("telescope.themes").get_dropdown({}),
          },
          file_browser = {
            hidden = true
          }
        },
        pickers = {
          find_files = {
            hidden = true
          }
        },
      })
      pcall(telescope.load_extension, "fzf")
      pcall(telescope.load_extension, "zoxide")
      pcall(telescope.load_extension, "ui-select")

      local map = vim.keymap.set
      map("n", "<leader>ff", ":Telescope find_files<CR>", { desc = "Find files" })
      map("n", "<leader>fg", ":Telescope live_grep<CR>", { desc = "Live grep" })
      map("n", "<leader>fo", ":Telescope oldfiles<CR>", { desc = "Open recent files" })
      map("n", "<leader>fb", ":Telescope buffers<CR>", { desc = "List buffers" })
      map("n", "<leader>fh", ":Telescope help_tags<CR>", { desc = "Help tags" })
      map("n", "<leader>fc", ":Telescope commands<CR>", { desc = "Find commands" })
      map("n", "<leader>fk", ":Telescope keymaps<CR>", { desc = "Find keymaps" })
      map("n", "<leader>cd", ":Telescope zoxide list<CR>", { desc = "Zoxide" })
      map("n", "<leader>gd", ":Telescope git_status<CR>", { desc = "Git status" })
      map("n", "<space>fb", ":Telescope file_browser path=%:p:h select_buffer=true<CR>", { desc = "Toggle file browser" })
    end
  },

}
