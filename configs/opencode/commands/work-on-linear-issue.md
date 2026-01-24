---
description: Work on the next highest priority Linear issue assigned to me
agent: plan
model: opencode/grok-code
---

IMPORTANT: NEVER INVENT INFORMATION IF LINEAR MCP IS NOT AVAILABLE. If unable to fetch data, ask the user for details instead.

ARGUMENTS: $ARGUMENTS

If a specific issue ID is provided as a argument (e.g. JOB-XXX), use the Linear MCP to fetch the details of that issue directly.

Otherwise, use the Linear MCP to fetch all issues assigned to "me" that are not completed or cancelled. You are OAuthed so you can fetch my username on Linear to use as assignee.

Sort these issues by priority, with priority 1 (Urgent) first, then 2 (High), 3 (Normal), 4 (Low). Ignore issues with priority 0 (No priority).

Select the highest priority issue from this sorted list.

Retrieve the full details of the selected issue, including its branch name, labels, project, title, and description.

Based on the issue's labels, project name, title, and description, determine which specific app or package this issue relates to.

BEFORE START PLANNING, DO:

Create a new git branch using the issue's suggested branch name.

Move issue to status In Progress when start working.

THEN:

Output a summary including:
- Issue ID and title
- Priority level
- Determined project/app
- Branch name created

NOW YOU CAN START PLANNING AFTER MAKING SURE WE CREATE THE BRANCH AND UPDATES ISSUE STATUS.

