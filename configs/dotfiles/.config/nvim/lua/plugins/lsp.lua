return {
  {
    "williamboman/mason.nvim",
    config = function()
      require("mason").setup()
    end,
  },
  {
    "williamboman/mason-lspconfig.nvim",
    dependencies = { "williamboman/mason.nvim" },
    config = function()
      require("mason-lspconfig").setup({
        ensure_installed = {
          "vtsls",
          "tailwindcss",
          "pyright",
          "gopls",
        },
      })
    end,
  },
  {
    "neovim/nvim-lspconfig",
    dependencies = {
      "williamboman/mason-lspconfig.nvim",
      "hrsh7th/cmp-nvim-lsp",
    },
    config = function()
      local capabilities = require("cmp_nvim_lsp").default_capabilities()

      local on_attach = function(_, buffer)
        local map = function(mode, lhs, rhs, desc)
          vim.keymap.set(mode, lhs, rhs, { buffer = buffer, desc = desc })
        end

        map("n", "gd", vim.lsp.buf.definition, "Go to definition")
        map("n", "gr", vim.lsp.buf.references, "References")
        map("n", "K", vim.lsp.buf.hover, "Hover")
        map("n", "ga", vim.lsp.buf.code_action, "Code action")
        map("n", "rn", vim.lsp.buf.rename, "Rename")
        map("n", "ds", vim.lsp.buf.document_symbol, "Document symbols")
        map("n", "ws", vim.lsp.buf.workspace_symbol, "Workspace symbols")
      end

      vim.lsp.config("vtsls", {
        capabilities = capabilities,
        on_attach = on_attach,
      })

      vim.lsp.config("tailwindcss", {
        capabilities = capabilities,
        on_attach = on_attach,
      })

      vim.lsp.config("pyright", {
        capabilities = capabilities,
        on_attach = on_attach,
      })

      vim.lsp.config("gopls", {
        capabilities = capabilities,
        on_attach = on_attach,
        settings = {
          gopls = {
            usePlaceholders = true,
            analyses = {
              unusedparams = true,
            },
          },
        },
      })

      vim.lsp.enable("vtsls")
      vim.lsp.enable("tailwindcss")
      vim.lsp.enable("pyright")
      vim.lsp.enable("gopls")
    end,
  },
}
