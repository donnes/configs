-- Hyprland session save/restore (hypr-session, from donnes/configs).

-- Snapshot the current window arrangement, and put it back after something
-- disturbs it (floating a window, a closed/reopened app, a monitor change).
o.bind("SUPER + SHIFT + ALT + L", "Save window layout", "hypr-session save")
o.bind("SUPER + ALT + L", "Restore window layout", "hypr-session restore")

-- Reopen the apps from the last session (autosaved every minute by
-- hypr-session-autosave.timer), so a crash or power cut doesn't lose them.
o.launch_on_start("hypr-session resume")
