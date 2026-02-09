return {
  "ThePrimeagen/99",
  config = function()
    local _99 = require("99")
    local Providers = require("99.providers")

    _99.setup({
      provider = Providers.OpenCodeProvider,
      model = "opencode/kimi-k2.5",
      logger = {
        level = _99.DEBUG,
        path = "/tmp/99.debug",
        print_on_error = true,
      },
    })
    vim.keymap.set("n", "<leader>9ff", function()
      _99.fill_in_function()
    end)
    vim.keymap.set("n", "<leader>9fp", function()
      _99.fill_in_function_prompt()
    end)
    vim.keymap.set("n", "<leader>9fd", function()
      _99.fill_in_function({
        additional_rules = {
          _99:rule_from_path("~/.behaviors/debug.md"),
        },
      })
    end)
    vim.keymap.set("v", "<leader>9vv", function()
      _99.visual()
    end)
    vim.keymap.set("v", "<leader>9vp", function()
      _99.visual_prompt()
    end)
    vim.keymap.set("n", "<leader>9s", function()
      _99.stop_all_requests()
    end)
    vim.keymap.set("n", "<leader>9i", function()
      _99.info()
    end)
    vim.keymap.set("n", "<leader>9l", function()
      _99.view_logs()
    end)
    vim.keymap.set("n", "<leader>9n", function()
      _99.next_request_logs()
    end)
    vim.keymap.set("n", "<leader>9p", function()
      _99.prev_request_logs()
    end)
  end,
}
