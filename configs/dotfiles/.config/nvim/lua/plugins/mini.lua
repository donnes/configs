return {
  "nvim-mini/mini.nvim",
  config = function()
    local starter = require("mini.starter")

    starter.setup({
      header = [[
██████╗  ██████╗ ███╗   ██╗███╗   ██╗███████╗███████╗
██╔══██╗██╔═══██║████╗  ██║████╗  ██║██╔════╝██╔════╝
██║  ██║██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ███████╗
██║  ██║██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ╚════██║
██████╔╝╚██████╔╝██║ ╚████║██║ ╚████║███████╗███████║
╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝╚══════╝
]],
      evaluate_single = false,
      items = {
        { name = "Recent Files", action = function() require("mini.extra").pickers.oldfiles() end, section = "Search" },
        { name = "Session",      action = function() require("mini.sessions").select() end,        section = "Search" },
        starter.sections.recent_files(5, false, false),
      },
      footer = "https://donnes.dev"
    })

    require("mini.clue").setup({
      triggers = {
        { mode = 'n', keys = '<Leader>' },
        { mode = 'x', keys = '<Leader>' },
        { mode = 'n', keys = '<localleader>' },
        { mode = 'x', keys = '<localleader>' },
      },
      clues = {
        { mode = 'n', keys = '<Leader>b', desc = '+buffers' },
        { mode = 'n', keys = '<Leader>c', desc = '+code' },
        { mode = 'n', keys = '<Leader>f', desc = '+file/find' },
        { mode = 'n', keys = '<Leader>g', desc = '+git' },
        { mode = 'n', keys = '<Leader>l', desc = '+lsp' },
        { mode = 'n', keys = '<Leader>q', desc = '+quit/session' },
        { mode = 'n', keys = '<Leader>s', desc = '+search' },
        { mode = 'n', keys = '<Leader>t', desc = '+toggle' },
        { mode = 'n', keys = '<Leader>w', desc = '+windows' },
        { mode = 'n', keys = '<Leader>x', desc = '+diagnostics' },
      },
    })

    require("mini.statusline").setup({
      content = {
        active = function()
          local statusline    = require('mini.statusline')
          local mode, mode_hl = statusline.section_mode({ trunc_width = 120 })
          local git           = statusline.section_git({ trunc_width = 40 })
          local filename      = statusline.section_filename({ trunc_width = 140 })
          local fileinfo      = statusline.section_fileinfo({ trunc_width = 120 })
          local search        = statusline.section_searchcount({ trunc_width = 75 })

          return statusline.combine_groups({
            { hl = mode_hl,                 strings = { mode } },
            { hl = 'MiniStatuslineDevinfo', strings = { git, diff, diagnostics, lsp } },
            '%<', -- Mark general truncate point
            { hl = 'MiniStatuslineFilename', strings = { filename } },
            '%=', -- End left alignment
            { hl = 'MiniStatuslineFileinfo', strings = { fileinfo } },
            { hl = mode_hl,                  strings = { search, location } },
          })
        end,
        inactive = nil,
      },
    })

    require("mini.ai").setup({
      custom_textobjects = {
        o = require('mini.ai').gen_spec.treesitter({
          a = { '@block.outer', '@conditional.outer', '@loop.outer', '@call.outer', '@function.outer' },
          i = { '@block.inner', '@conditional.inner', '@loop.inner', '@call.inner', '@function.inner' },
        }, {}),
      },
      n_lines = 500,
    })

    require("mini.hipatterns").setup()

    require("mini.files").setup()

    require("mini.pairs").setup()

    require("mini.surround").setup()

    require("mini.bracketed").setup()

    vim.api.nvim_create_autocmd("User", {
      pattern = "MiniStarterOpened",
      callback = function()
        vim.api.nvim_set_hl(0, "MiniStarterQuery", { link = "None" })
      end,
    })
  end,
}
