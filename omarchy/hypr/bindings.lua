-- Keep only your personal keybinding overrides here. Add new bindings or
-- unbind defaults before replacing them.

-- See current bindings and descriptions:
--   omarchy menu keybindings --print

-- To disable every Omarchy default binding, set this in
-- ~/.config/hypr/hyprland.lua before require("default.hypr.omarchy"), then add
-- only the bindings you want below:
--   omarchy_default_bindings = false

-- To disable all preinstalled app/webapp bindings, set:
--   omarchy_preinstalled_bindings = false

-- Add a new binding.
-- o.bind("SUPER + SHIFT + R", "SSH", "alacritty -e ssh your-server")

-- Change an existing binding by unbinding it first, then binding the key again.
-- This example changes SUPER+SPACE from the launcher to the Omarchy root menu.
-- hl.unbind("SUPER + SPACE")
-- o.bind("SUPER + SPACE", "Omarchy menu", "omarchy-menu toggle root")

-- Disable a default binding without replacing it.
-- hl.unbind("SUPER + SHIFT + B")

-- Logitech MX Keys examples:
-- o.bind("SUPER + SHIFT + S", nil, "omarchy-capture-screenshot")
-- o.bind("SUPER + H", nil, "voxtype record toggle")
-- o.bind("SUPER + PERIOD", nil, "omarchy-shell shell toggle omarchy.emojis")

-- Screen capture off the Print key, which this keyboard does not have.
-- SUPER+SHIFT+S and SUPER+SHIFT+P previously opened the Google Maps and
-- Google Photos webapps; both are still available from the apps menu.
hl.unbind("SUPER + SHIFT + S")
hl.unbind("SUPER + SHIFT + P")

o.bind("SUPER + SHIFT + S", "Screenshot", "omarchy-capture-screenshot")
o.bind(
  "SUPER + SHIFT + R",
  "Screenrecording",
  "omarchy-capture-screenrecording --stop-recording || omarchy-menu toggle trigger.capture.screenrecord"
)
o.bind("SUPER + SHIFT + P", "Color picker", "pkill hyprpicker || hyprpicker -a")
o.bind("SUPER + SHIFT + T", "Extract text (OCR) from screenshot", "omarchy-capture-text")

-- Drop the HEY calendar and email webapp bindings.
hl.unbind("SUPER + SHIFT + C")
hl.unbind("SUPER + SHIFT + E")
hl.unbind("SUPER + SHIFT + ALT + E")

-- Superwhisper's own shortcuts (F10 toggle, set in its Settings). It writes them to
-- shortcuts.lua but can't add this block itself because this file is a symlink.
-- Superwhisper managed shortcuts BEGIN
dofile("/home/donnes/.config/superwhisper/shortcuts.lua")
-- Superwhisper managed shortcuts END
