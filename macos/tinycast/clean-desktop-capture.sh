#!/bin/bash
# Hides desktop icons, runs screencapture with the given flags, then restores
# the icons. Not a Tinycast command itself (no @raycast metadata).

set -u

file="$HOME/Desktop/Screenshot $(date '+%Y-%m-%d at %H.%M.%S').png"

restore() {
  defaults delete com.apple.finder CreateDesktop 2>/dev/null
  killall Finder
}
# Restore even when the capture is cancelled or fails.
trap restore EXIT

defaults write com.apple.finder CreateDesktop -bool false
killall Finder
sleep 2

screencapture "$@" "$file"

if [ -f "$file" ]; then
  echo "Saved $(basename "$file")"
else
  echo "Screenshot cancelled"
fi
