return {
  {
    "stevearc/conform.nvim",
    config = function()
      require("conform").setup({
        formatters_by_ft = {
          javascript = { "biome" },
          javascriptreact = { "biome" },
          typescript = { "biome" },
          typescriptreact = { "biome" },
          json = { "biome" },
        },
        format_on_save = function()
          return {
            timeout_ms = 2000,
            lsp_fallback = true,
          }
        end,
      })
    end,
  },
}
