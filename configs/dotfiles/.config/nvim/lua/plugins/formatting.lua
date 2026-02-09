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

      -- Add formatters for filetypes not covered by biome extra
      opts.formatters_by_ft.lua = { "stylua" }
      opts.formatters_by_ft.yaml = { "prettierd" }
      opts.formatters_by_ft.markdown = { "prettier" }
      opts.formatters_by_ft["markdown.mdx"] = { "prettier" }
      opts.formatters_by_ft.python = { "isort", "black" }
      opts.formatters_by_ft.go = { "goimports", "gofmt" }

      -- Ensure formatters config exists
      opts.formatters = opts.formatters or {}

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
      })
    end,
  },
}
