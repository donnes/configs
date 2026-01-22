return {
  {
    "lewis6991/gitsigns.nvim",
    config = function()
      require("gitsigns").setup({
        signcolumn = true,
        current_line_blame = false,
      })
    end,
  },
}
