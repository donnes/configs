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
          "lua_ls",
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
      "hrsh7th/cmp-nvim-lsp",
    },
    config = function()
      local capabilities = require("cmp_nvim_lsp").default_capabilities()

      local on_attach = function(_, buffer)
        _G.lsp_keymaps(buffer)
      end

      vim.lsp.config("vtsls", {
        capabilities = capabilities,
        on_attach = on_attach,
      })

      vim.api.nvim_create_autocmd("LspAttach", {
        callback = function(args)
          local client = vim.lsp.get_client_by_id(args.data.client_id)
          if client and client.name == "tailwindcss" then
            local paths = {
              "./src/styles/globals.css",
              "./packages/ui/src/styles/globals.css",
              "./src/app/globals.css",
              "./src/index.css",
              "./app/globals.css",
            }
            for _, path in pairs(paths) do
              local full_path = vim.fn.getcwd() .. "/" .. path
              if vim.fn.filereadable(full_path) == 1 then
                client.notify("workspace/didChangeConfiguration", {
                  settings = {
                    tailwindCSS = {
                      experimental = {
                        configFile = path,
                      },
                    },
                  },
                })
                break
              end
            end
          end
        end,
      })

      vim.lsp.config("tailwindcss", {
        capabilities = capabilities,
        on_attach = on_attach,
        root_dir = require("lspconfig.util").root_pattern("package.json", "tsconfig.json"),
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

      vim.lsp.config("lua_ls", {
        capabilities = capabilities,
        on_attach = on_attach,
      })

      vim.lsp.enable("vtsls")
      vim.lsp.enable("tailwindcss")
      vim.lsp.enable("pyright")
      vim.lsp.enable("gopls")
      vim.lsp.enable("lua_ls")
    end,
  },
}
