return {
  {
    "oskarnurm/koda.nvim",
    priority = 1000,
    config = function()
      vim.opt.background = "dark"
      vim.cmd.colorscheme("koda")
    end,
  },
}
