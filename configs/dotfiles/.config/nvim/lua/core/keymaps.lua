vim.g.mapleader = " "
vim.g.maplocalleader = " "

local map = vim.keymap.set

-- ============================================================================
-- CORE MAPPINGS
-- ============================================================================

-- Window navigation
map("n", "<C-h>", "<C-w>h", { desc = "Go to left window" })
map("n", "<C-j>", "<C-w>j", { desc = "Go to bottom window" })
map("n", "<C-k>", "<C-w>k", { desc = "Go to top window" })
map("n", "<C-l>", "<C-w>l", { desc = "Go to right window" })

-- File operations
map("n", "<leader>w", ":write<CR>", { desc = "Save file" })
map("n", "<leader>q", ":qa<CR>", { desc = "Quit all" })
map("n", "<leader>Q", ":wa<CR>:qa<CR>", { desc = "Save all and quit" })
map("n", "<leader>bd", ":bdelete<CR>", { desc = "Delete buffer" })

-- Buffer navigation
map("n", "<leader>bn", ":bnext<CR>", { desc = "Next buffer" })
map("n", "<leader>bp", ":bprevious<CR>", { desc = "Previous buffer" })

-- Better paste behavior
map("x", "<leader>p", '"_dP', { desc = "Paste without yanking" })

-- Delete without yanking
map({ "n", "v" }, "<leader>d", '"_d', { desc = "Delete without yanking" })

-- Y to EOL
map("n", "Y", "y$", { desc = "Yank to end of line" })

-- Better substitute
map({ "n", "v", "x" }, "<C-s>", [[:s/\V]], { desc = "Enter substitute mode in selection" })

-- Better indenting in visual mode
map("v", "<", "<gv", { desc = "Indent left and reselect" })
map("v", ">", ">gv", { desc = "Indent right and reselect" })

-- Window splitting & resizing
map("n", "<leader>sv", ":split<CR>", { desc = "Split window vertically" })
map("n", "<leader>sh", ":vsplit<CR>", { desc = "Split window horizontally" })
map("n", "<C-Up>", ":resize +2<CR>", { desc = "Increase window height" })
map("n", "<C-Down>", ":resize -2<CR>", { desc = "Decrease window height" })
map("n", "<C-Left>", ":vertical resize -2<CR>", { desc = "Decrease window width" })
map("n", "<C-Right>", ":vertical resize +2<CR>", { desc = "Increase window width" })

-- Clear search
map("n", "<leader>c", ":nohlsearch<CR>", { desc = "Clear search highlights" })

-- Copy Full File-Path
map("n", "<leader>pa", function()
  local path = vim.fn.expand("%:p")
  vim.fn.setreg("+", path)
  print("file:", path)
end, { desc = "Copy full file-path" })

-- ============================================================================
-- TELESCOPE MAPPINGS
-- ============================================================================

map("n", "<leader>ff", ":Telescope find_files<CR>", { desc = "Find files" })
map("n", "<leader>fg", ":Telescope live_grep<CR>", { desc = "Live grep" })
map("n", "<leader>fo", ":Telescope oldfiles<CR>", { desc = "Open recent files" })
map("n", "<leader>fb", ":Telescope buffers<CR>", { desc = "List buffers" })
map("n", "<leader>fh", ":Telescope help_tags<CR>", { desc = "Help tags" })
map("n", "<leader>fc", ":Telescope commands<CR>", { desc = "Find commands" })
map("n", "<leader>fk", ":Telescope keymaps<CR>", { desc = "Find keymaps" })
map("n", "<leader>cd", ":Telescope zoxide list<CR>", { desc = "Zoxide" })
map("n", "<leader>gd", ":Telescope git_status<CR>", { desc = "Git status" })
map("n", "<space>fb", ":Telescope file_browser path=%:p:h select_buffer=true<CR>", { desc = "Toggle file browser" })

-- ============================================================================
-- LSP MAPPINGS (called from on_attach)
-- ============================================================================

function _G.lsp_keymaps(buffer)
  local map = function(mode, lhs, rhs, desc)
    vim.keymap.set(mode, lhs, rhs, { buffer = buffer, desc = desc })
  end

  map("n", "gd", vim.lsp.buf.definition, "Go to definition")
  map("n", "gr", vim.lsp.buf.references, "References")
  map("n", "K", vim.lsp.buf.hover, "Hover")
  map("n", "<leader>ca", vim.lsp.buf.code_action, "Code action")
  map("n", "rn", vim.lsp.buf.rename, "Rename")
  map("n", "ds", vim.lsp.buf.document_symbol, "Document symbols")
  map("n", "ws", vim.lsp.buf.workspace_symbol, "Workspace symbols")
end

-- ============================================================================
-- FLASH MAPPINGS
-- ============================================================================

map({ "n", "x", "o" }, "zk", function() require("flash").jump() end, { desc = "Flash" })
map({ "n", "x", "o" }, "Zk", function() require("flash").treesitter() end, { desc = "Flash Treesitter" })
map("o", "r", function() require("flash").remote() end, { desc = "Remote Flash" })
map({ "o", "x" }, "R", function() require("flash").treesitter_search() end, { desc = "Treesitter Search" })
map("c", "<c-s>", function() require("flash").toggle() end, { desc = "Toggle Flash Search" })

-- ============================================================================
-- MINI MAPPINGS
-- ============================================================================

map("n", "<leader>n", function()
  MiniFiles.open()
end, { desc = "Open mini.files" })

map("n", "<leader>cw", function()
  MiniFiles.open(vim.fn.getcwd())
end, { desc = "Open mini.files in cwd" })

-- ============================================================================
-- COMPLETION MAPPINGS (insert mode)
-- ============================================================================

local cmp_keymaps = {
  ["<C-Space>"] = "complete",
  ["<C-b>"] = "scroll_docs(-4)",
  ["<C-f>"] = "scroll_docs(4)",
  ["<C-e>"] = "abort",
  ["<CR>"] = "confirm({ select = true })",
}

function _G.get_cmp_keymaps()
  return cmp_keymaps
end
