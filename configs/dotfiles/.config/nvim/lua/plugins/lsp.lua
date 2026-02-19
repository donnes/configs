-- Per-client keymaps/autocmds set on LspAttach
local on_attach_by_client = {
  eslint = function(buffer)
    vim.api.nvim_create_autocmd("BufWritePre", {
      buffer = buffer,
      command = "EslintFixAll",
    })
  end,
  biome = function(buffer)
    vim.keymap.set("n", "<leader>co", function()
      vim.lsp.buf.code_action({
        context = { only = { "source.organizeImports.biome" } },
        apply = true,
      })
    end, { buffer = buffer, desc = "Organize Imports (Biome)" })
  end,
}

return {
  {
    "neovim/nvim-lspconfig",
    init = function()
      vim.api.nvim_create_autocmd("LspAttach", {
        callback = function(args)
          local client = vim.lsp.get_client_by_id(args.data.client_id)
          local handler = client and on_attach_by_client[client.name]
          if handler then handler(args.buf) end
        end,
      })
    end,
    ---@class PluginLspOpts
    opts = {
      ---@type lspconfig.options
      servers = {
        pyright = {},
        biome = {},
        tailwindcss = {},
        -- eslint won't attach without .eslintrc.* / eslint.config.*
        eslint = {},
      },
    },
  },
}
