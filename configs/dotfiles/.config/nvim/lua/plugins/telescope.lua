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
    end
  },
  
}
