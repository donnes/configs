return {
  "goolord/alpha-nvim",
  event = "VimEnter",
  dependencies = { "nvim-tree/nvim-web-devicons" },
  config = function()
    local alpha = require("alpha")
    local dashboard = require("alpha.themes.dashboard")

    dashboard.section.header.val = {
      [[██████╗  ██████╗ ███╗   ██╗███╗   ██╗███████╗███████╗]],
      [[██╔══██╗██╔═══██╗████╗  ██║████╗  ██║██╔════╝██╔════╝]],
      [[██║  ██║██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ███████╗]],
      [[██║  ██║██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ╚════██║]],
      [[██████╔╝╚██████╔╝██║ ╚████║██║ ╚████║███████╗███████║]],
      [[╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝╚══════╝]],
    }

    dashboard.section.buttons.val = {
      dashboard.button("b", "  Browser files", ":Yazi<CR>"),
      dashboard.button("z", "   Browser directories", ":Telescope zoxide list<CR>"),
      dashboard.button("f", "  Find file", "<cmd>Telescope find_files<CR>"),
      dashboard.button("g", "  Live grep", "<cmd>Telescope live_grep<CR>"),
      dashboard.button("r", "  Recent files", "<cmd>Telescope oldfiles<CR>"),
      dashboard.button("l", "󰒲  Lazy (plugins)", "<cmd>Lazy<CR>"),
      dashboard.button("q", "  Quit", "<cmd>qa<CR>"),
    }

    dashboard.section.footer.val = {
      "Tip: :checkhealth  |  :help user-manual",
    }

    alpha.setup(dashboard.opts)

    -- Ensure it actually shows when opening nvim with no args
    vim.api.nvim_create_autocmd("VimEnter", {
      callback = function()
        local argc = vim.fn.argc()
        if argc == 0 and vim.bo.buftype == "" and vim.fn.line2byte("$") == -1 then
          require("alpha").start(true)
        end
      end,
    })
  end,
}
