vim.g.mapleader = " "
vim.g.maplocalleader = " "

vim.opt.number = true
vim.opt.runtimepath:append(vim.fn.stdpath("data") .. "/site")
vim.opt.relativenumber = true
vim.opt.cursorline = true
vim.opt.termguicolors = true
vim.opt.signcolumn = "yes"
vim.opt.wrap = false
vim.opt.scrolloff = 8
vim.opt.sidescrolloff = 8
vim.opt.splitright = true
vim.opt.splitbelow = true
vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.updatetime = 200
vim.opt.timeoutlen = 400
vim.opt.clipboard = "unnamedplus"
vim.opt.completeopt = { "menu", "menuone", "noselect" }

vim.opt.tabstop = 2
vim.opt.shiftwidth = 2
vim.opt.expandtab = true
vim.opt.smartindent = true

vim.opt.backup = false
vim.opt.swapfile = false
vim.opt.undofile = true

vim.opt.list = true
vim.opt.listchars = {
  tab = "> ",
  trail = ".",
  extends = ">",
  precedes = "<",
  nbsp = "+",
}

vim.opt.fillchars = {
  eob = " ",
}

vim.opt.laststatus = 3
vim.opt.showmode = false
vim.opt.pumheight = 10
vim.opt.conceallevel = 0
vim.opt.mouse = "a"
