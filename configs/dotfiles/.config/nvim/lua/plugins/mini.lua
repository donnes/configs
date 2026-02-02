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
        starter.sections.recent_files(5, false, false),
        starter.sections.recent_files(5, true, false),
      },
      footer = "https://donnes.dev"
    })

    require("mini.clue").setup({
      triggers = {
        { mode = 'n', keys = '<Leader>' },
        { mode = 'x', keys = '<Leader>' },
        { mode = 'n', keys = '<localleader>' },
        { mode = 'x', keys = '<localleader>' },
        { mode = 'n', keys = 'g' },
        { mode = 'n', keys = '[' },
        { mode = 'n', keys = ']' },
        { mode = 'n', keys = 'K' },
      },
      clues = {
        { mode = 'n', keys = 'gd', desc = 'Definition' },
        { mode = 'n', keys = 'K', desc = 'Hover' },
        { mode = 'n', keys = '[d', desc = 'Previous diagnostic' },
        { mode = 'n', keys = ']d', desc = 'Next diagnostic' },
        { mode = 'n', keys = '<Leader>v', desc = '+lsp' },
        { mode = 'n', keys = '<Leader>vws', desc = 'Workspace symbols' },
        { mode = 'n', keys = '<Leader>vd', desc = 'Diagnostics' },
        { mode = 'n', keys = '<Leader>vca', desc = 'Code action' },
        { mode = 'n', keys = '<Leader>vrr', desc = 'References' },
        { mode = 'n', keys = '<Leader>vrn', desc = 'Rename' },
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

    require("mini.move").setup({
      mappings = {
        -- Normal mode
        left       = '<M-h>',
        right      = '<M-l>',
        down       = '<M-j>',
        up         = '<M-k>',

        -- Visual mode
        line_left  = '<M-h>',
        line_right = '<M-l>',
        line_down  = '<M-j>',
        line_up    = '<M-k>',
      },
    })

    require("mini.bracketed").setup()

    vim.api.nvim_create_autocmd("User", {
      pattern = "MiniStarterOpened",
      callback = function()
        vim.api.nvim_set_hl(0, "MiniStarterQuery", { link = "None" })
      end,
    })
  end,
}
