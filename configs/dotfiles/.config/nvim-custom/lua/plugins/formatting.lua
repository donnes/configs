-- For JS/TS filetypes: prettierd runs first but only if a prettier config exists
-- in the project (require_cwd = true). If not, conform falls back to biome.
local js_fmt = { "prettierd", "biome", stop_after_first = true }

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
    opts = {
      notify_on_error = false,
      format_on_save = function(bufnr)
        local disable_filetypes = { c = true, cpp = true }
        return {
          timeout_ms = 500,
          lsp_fallback = not disable_filetypes[vim.bo[bufnr].filetype],
        }
      end,
      formatters_by_ft = {
        lua = { "stylua" },
        javascript = js_fmt,
        typescript = js_fmt,
        javascriptreact = js_fmt,
        typescriptreact = js_fmt,
        vue = js_fmt,
        css = js_fmt,
        html = js_fmt,
        graphql = js_fmt,
        json = js_fmt,
        yaml = { "prettierd" },
        markdown = { "prettier" },
        ["markdown.mdx"] = { "prettier" },
        python = { "isort", "black" },
        go = { "goimports", "gofmt" },
      },
      formatters = {
        -- prettierd: only activate when a prettier config is found in the project
        prettierd = {
          require_cwd = true,
        },
      },
    },
  },
}
