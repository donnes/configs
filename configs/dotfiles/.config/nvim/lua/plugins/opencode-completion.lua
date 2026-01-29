return {
  "jaswdr/opencode-completion.nvim",
  config = function()
    require("opencode-completion").setup()
    
    local function is_port_in_use(port)
      local result = vim.fn.system({"lsof", "-i:" .. port})
      return result ~= ""
    end
    
    if not is_port_in_use(4096) then
      vim.fn.jobstart({"opencode", "serve", "--port=4096"}, {detach = true})
    end
  end
}
