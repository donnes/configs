#!/bin/bash

# @raycast.schemaVersion 1
# @raycast.title Screenshot Window
# @raycast.mode silent
# @raycast.icon 📸
# @raycast.packageName Screenshots
# @raycast.description Hide desktop icons and capture a window. Space switches to area selection.

exec "$HOME/Scripts/Tinycast/clean-desktop-capture.sh" -iW
