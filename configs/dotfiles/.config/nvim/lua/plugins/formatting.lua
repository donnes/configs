return {
  {
    "stevearc/conform.nvim",
    event = { "BufWritePre" },
    cmd = { "ConformInfo" },
    keys = {
      {
        "<leader>lf",
        function()
          require("conform").format({ async = true, lsp_fallback = true })
        end,
        mode = { "n", "v" },
        desc = "Format buffer or range",
      },
    },
    opts = function(_, opts)
      -- Ensure formatters_by_ft exists
      opts.formatters_by_ft = opts.formatters_by_ft or {}

      -- For JS/TS filetypes: try prettierd first (only runs if a prettier config exists
      -- in the project thanks to require_cwd), then fall back to biome.
      -- This overrides the LazyVim biome extra for these filetypes.
      local js_ts_fts = {
        "javascript",
        "javascriptreact",
        "typescript",
        "typescriptreact",
        "vue",
        "css",
        "html",
        "graphql",
        "json",
      }
      for _, ft in ipairs(js_ts_fts) do
        opts.formatters_by_ft[ft] = { "prettierd", "biome", stop_after_first = true }
      end

      -- Add formatters for filetypes not covered by biome/prettier
      opts.formatters_by_ft.lua = { "stylua" }
      opts.formatters_by_ft.yaml = { "prettierd" }
      opts.formatters_by_ft.markdown = { "prettier" }
      opts.formatters_by_ft["markdown.mdx"] = { "prettier" }
      opts.formatters_by_ft.python = { "isort", "black" }
      opts.formatters_by_ft.go = { "goimports", "gofmt" }

      -- Ensure formatters config exists
      opts.formatters = opts.formatters or {}

      -- prettierd: only activate when a prettier config is found in the project
      opts.formatters.prettierd = {
        require_cwd = true,
      }

      return opts
    end,
  },
  {
    "mason-org/mason.nvim",
    opts = function(_, opts)
      opts.ensure_installed = opts.ensure_installed or {}
      vim.list_extend(opts.ensure_installed, {
        "stylua",
        "biome",
        "shellcheck",
        "shfmt",
        "flake8",
        "prettierd",
        "prettier",
        "isort",
        "black",
        "goimports",
        "eslint-lsp",
        "tailwindcss-language-server",
      })
    end,
  },
}
