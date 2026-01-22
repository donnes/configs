return {
  {
    "nvim-telescope/telescope.nvim",
    dependencies = { "nvim-lua/plenary.nvim" },
    config = function()
      local telescope = require("telescope")
      telescope.setup({
        defaults = {
          layout_strategy = "horizontal",
          layout_config = { prompt_position = "top" },
          sorting_strategy = "ascending",
          winblend = 5,
        },
      })
      pcall(telescope.load_extension, "fzf")
    end,
  },
  {
    "nvim-tree/nvim-tree.lua",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    config = function()
      require("nvim-tree").setup({
        view = { width = 34 },
        renderer = {
          group_empty = true,
          icons = {
            show = {
              folder = true,
              file = true,
              git = true,
            },
          },
        },
        filters = { dotfiles = false },
        git = { enable = true },
      })
    end,
  },
}
