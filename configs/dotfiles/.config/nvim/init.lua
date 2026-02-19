-- Add Mason's bin to PATH early so LSP servers can be found
vim.env.PATH = vim.fn.stdpath("data") .. "/mason/bin:" .. vim.env.PATH

-- bootstrap lazy.nvim, LazyVim and your plugins
require("config.lazy")
