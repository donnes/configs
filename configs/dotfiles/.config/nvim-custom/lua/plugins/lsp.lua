return {
  {
    "williamboman/mason.nvim",
    opts = {},
  },
  {
    "j-hui/fidget.nvim",
    opts = {},
  },
  {
    "WhoIsSethDaniel/mason-tool-installer.nvim",
    opts = {
      ensure_installed = {
        "prettier",
        "prettierd",
        "eslint-lsp",
      },
    },
  },
  {
    "williamboman/mason-lspconfig.nvim",
    dependencies = { "williamboman/mason.nvim", "neovim/nvim-lspconfig" },
    opts = {
      servers = {
        marksman = {},
      },
    },
    config = function()
      local capabilities = require("cmp_nvim_lsp").default_capabilities()
      local on_attach = function(_, buffer) _G.lsp_keymaps(buffer) end
      local lspconfig = require("lspconfig")

      require("mason-lspconfig").setup({
        ensure_installed = { "lua_ls", "vtsls", "tailwindcss", "pyright", "gopls", "eslint" },
        handlers = {
          function(server_name)
            lspconfig[server_name].setup({
              capabilities = capabilities,
              on_attach = on_attach,
            })
          end,
          ["lua_ls"] = function()
            lspconfig.lua_ls.setup({
              capabilities = capabilities,
              on_attach = on_attach,
              settings = {
                Lua = {
                  runtime = {
                    version = "LuaJIT",
                  },
                  diagnostics = {
                    globals = { "vim" },
                  },
                  workspace = {
                    library = vim.api.nvim_get_runtime_file("", true),
                    checkThirdParty = false,
                  },
                },
              },
            })
          end,
          ["gopls"] = function()
            lspconfig.gopls.setup({
              capabilities = capabilities,
              on_attach = on_attach,
              settings = { gopls = { usePlaceholders = true, analyses = { unusedparams = true } } },
            })
          end,
          ["tailwindcss"] = function()
            lspconfig.tailwindcss.setup({
              capabilities = capabilities,
              on_attach = on_attach,
              filetypes = {
                "html",
                "css",
                "scss",
                "javascript",
                "javascriptreact",
                "typescript",
                "typescriptreact",
                "vue",
                "svelte",
                "heex",
              },
            })
          end,
          -- eslint: built-in root_dir won't attach without .eslintrc.* / eslint.config.*
          ["eslint"] = function()
            lspconfig.eslint.setup({
              capabilities = capabilities,
              on_attach = function(_, bufnr)
                _G.lsp_keymaps(bufnr)
                vim.api.nvim_create_autocmd("BufWritePre", {
                  buffer = bufnr,
                  command = "EslintFixAll",
                })
              end,
            })
          end,
          ["vtsls"] = function()
            lspconfig.vtsls.setup({
              capabilities = capabilities,
              on_attach = on_attach,
              settings = {
                vtsls = {
                  autoUseWorkspaceTsdk = true,
                  tsserver = {
                    experimental = {
                      enableProjectDiagnostics = true,
                    },
                  },
                },
                typescript = {
                  preferences = {
                    includeInlayParameterNameHints = "all",
                    includeInlayFunctionParameterTypeHints = true,
                    includeInlayVariableTypeHints = true,
                    includeInlayPropertyDeclarationTypeHints = true,
                    includeInlayFunctionLikeReturnTypeHints = true,
                  },
                  updateImportsOnFileMove = {
                    enabled = "always",
                  },
                },
                javascript = {
                  preferences = {
                    includeInlayParameterNameHints = "all",
                    includeInlayFunctionParameterTypeHints = true,
                    includeInlayVariableTypeHints = true,
                    includeInlayPropertyDeclarationTypeHints = true,
                    includeInlayFunctionLikeReturnTypeHints = true,
                  },
                  updateImportsOnFileMove = {
                    enabled = "always",
                  },
                },
              },
            })
          end,
        },
      })

      vim.diagnostic.config({
        float = {
          focusable = false,
          style = "minimal",
          border = "rounded",
          source = "always",
          header = "",
          prefix = "",
        },
      })
    end,
  },
}
