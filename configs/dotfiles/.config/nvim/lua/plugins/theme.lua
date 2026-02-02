return {
  "nvim-tree/nvim-web-devicons",
  {
    "vague-theme/vague.nvim",
    priority = 1000,
    config = function()
      vim.cmd("colorscheme vague")
    end
  },
  -- {
  --   "oskarnurm/koda.nvim",
  --   priority = 1000,
  --   config = function()
  --     vim.opt.background = "dark"
  --     vim.cmd.colorscheme("koda")
  --   end,
  -- },
}
