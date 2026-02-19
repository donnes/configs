---
description: Removes AI-generated slop.
---

# Remove AI code slop

Check the diff against main, and remove all AI-generated slop introduced in this branch. If currently on main, check if there is current changes and if not, ask me what to do.

This includes:

- Extra comments that a human wouldn't add or is inconsistent with the rest of the file
- Extra defensive checks or try/catch blocks that are abnormal for that area of the codebase (especially if called by trusted / validated codepaths)
- Casts to any to get around type issues
- Any other style that is inconsistent with the file
- Check if changes follows AGENTS.md patterns

Report at the end with only a 1-3 sentence summary of what you changed.

$ARGUMENTS
