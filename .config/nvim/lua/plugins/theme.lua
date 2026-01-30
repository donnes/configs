return {
  {
    "oskarnurm/koda.nvim",
    priority = 1000,
    dependencies = {
      "nvim-tree/nvim-web-devicons",
    },
    config = function()
      vim.opt.background = "dark"
      vim.cmd.colorscheme("koda")
    end,
  },
}
