#!/usr/bin/osascript -l JavaScript
// Tiles the front window into the left or right half of its screen, inset by
// GAP on every side. Not a Tinycast command itself (no @raycast metadata).

ObjC.import('AppKit');

const GAP = 16;

function run([side]) {
  if (side !== 'left' && side !== 'right') throw new Error('Usage: almost-half.js left|right');

  const process = Application('System Events').processes.whose({ frontmost: true })[0];
  const window = process.attributes.byName('AXFocusedWindow').value();
  if (!window) return;
  const [x, y] = window.position();
  const [width, height] = window.size();

  // System Events uses top-left coordinates from the primary screen; AppKit uses bottom-left.
  const primaryHeight = $.NSScreen.screens.objectAtIndex(0).frame.size.height;
  const topLeft = ({ origin, size }) => ({ x: origin.x, y: primaryHeight - origin.y - size.height, width: size.width, height: size.height });
  const screens = ObjC.unwrap($.NSScreen.screens).map(screen => ({ frame: topLeft(screen.frame), visible: topLeft(screen.visibleFrame) }));
  const centerX = x + width / 2, centerY = y + height / 2;
  const area = (screens.find(({ frame: f }) => centerX >= f.x && centerX < f.x + f.width && centerY >= f.y && centerY < f.y + f.height) ?? screens[0]).visible;

  const leftWidth = Math.round((area.width - GAP * 3) / 2);
  const tileX = side === 'left' ? area.x + GAP : area.x + GAP * 2 + leftWidth;
  const tileWidth = side === 'left' ? leftWidth : area.width - GAP * 3 - leftWidth;
  window.position = [Math.round(tileX), Math.round(area.y + GAP)];
  window.size = [Math.round(tileWidth), Math.round(area.height - GAP * 2)];
}
