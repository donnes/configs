local active_border_color = "rgba(cba6f7aa)"
local inactive_border_color = "rgba(e1ebf714)"

require("default.hypr.glass")()

hl.config({
  general = {
    gaps_in = 6,
    gaps_out = 12,
    border_size = 1,
    col = {
      active_border = active_border_color,
      inactive_border = inactive_border_color,
    },
  },

  group = {
    col = {
      border_active = active_border_color,
      border_inactive = inactive_border_color,
    },
  },

  decoration = {
    rounding = 14,
    rounding_power = 2.5,
    shadow = {
      enabled = true,
      range = 24,
      render_power = 3,
      offset = { 0, 6 },
      color = "rgba(0000004d)",
      color_inactive = "rgba(00000026)",
    },
  },
})

hl.layer_rule({
  match = { namespace = "^omarchy-(menu|clipboard|emojis|notifications|osd|polkit|reminders|dock|dock-apps|keyboard-panel)$" },
  blur = true,
  ignore_alpha = 0.3,
})

hl.layer_rule({
  match = { namespace = "^omarchy-bar$" },
  blur_popups = true,
})
