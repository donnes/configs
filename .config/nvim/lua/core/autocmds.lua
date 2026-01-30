local format_group = vim.api.nvim_create_augroup("FormatOnSave", { clear = true })

vim.api.nvim_create_autocmd("BufWritePre", {
  group = format_group,
  callback = function()
    require("conform").format({ timeout_ms = 2000, lsp_fallback = true })
  end,
})
