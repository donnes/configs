return {
  {
    "williamboman/mason.nvim",
    opts = {},
  },
  {
    "WhoIsSethDaniel/mason-tool-installer.nvim",
    opts = {
      ensure_installed = {
        "prettier",
      },
    },
  },
  {
    "williamboman/mason-lspconfig.nvim",
    dependencies = { "williamboman/mason.nvim", "neovim/nvim-lspconfig" },
    config = function()
      local capabilities = require("cmp_nvim_lsp").default_capabilities()
      local on_attach = function(_, buffer) _G.lsp_keymaps(buffer) end

      require("mason-lspconfig").setup({
        ensure_installed = { "lua_ls", "vtsls", "tailwindcss", "pyright", "gopls" },
        handlers = {
          function(server_name)
            require("lspconfig")[server_name].setup({
              capabilities = capabilities,
              on_attach = on_attach,
            })
          end,
          ["gopls"] = function()
            require("lspconfig").gopls.setup({
              capabilities = capabilities,
              on_attach = on_attach,
              settings = { gopls = { usePlaceholders = true, analyses = { unusedparams = true } } },
            })
          end,
        },
      })
    end,
  },
}
