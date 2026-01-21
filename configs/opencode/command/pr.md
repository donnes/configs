---
description: Create a pull request with commit
model: opencode/glm-4.6
subtask: true
---

Check the current branch with `git branch --show-current`

If the current branch is 'main' or 'master':
- Inform the user: "Direct commits to the main branch are not allowed. Creating a new branch automatically."
- Analyze the changes with `git diff` to understand the context.
- Generate a descriptive branch name based on the changes (e.g., 'feature/add-user-auth', 'fix/login-validation', or 'refactor/database-schema').
- Create the new branch with `git checkout -b <generated-branch-name>`
- Proceed with the rest of the command.

If the current branch is not 'main' or 'master':
- Inform the user: "You are currently on branch '<current-branch>'. Do you want to commit and push changes to this branch and create a PR from it? (y/n)"
- If yes, proceed with the rest of the command.
- If no, analyze the changes with `git diff`, generate a new descriptive branch name, create it with `git checkout -b <new-generated-branch-name>`, and proceed.

Always commit changes partially based on context and use `git add -p`.

Generate a concise commit message summarizing the changes based on `git diff --cached`

Commit the changes with the generated message.

To create the PR:

Get the current branch changes with `git diff main...HEAD`

Analyze the diff to identify:
- New files added
- Modified files
- Deleted files
- Key features or improvements
- Any setup instructions needed
- Technical details
- Testing approach
- Breaking changes

Use the following PR template to generate the title and description:

## Summary

[Provide a brief, one-sentence summary of the changes in this PR]

## Changes

### New Files
[List any new files added with brief descriptions]
- `path/to/file` - Description

### Modified Files
[List any files that were modified with brief descriptions]
- `path/to/file` - Description of changes

### Deleted Files
[List any files that were removed]
- `path/to/file` - Reason for removal

## Features

[List the key features or improvements this PR introduces]
- Feature 1
- Feature 2

## Setup Instructions

[If this PR requires any setup steps, document them here. Use numbered steps with code blocks where appropriate. Remove if not applicable]

1. Step one
2. Step two

## Technical Details

[Provide technical context, implementation details, architectural decisions, or important notes about the implementation. Remove if not applicable]

## Testing

[Describe how this change was tested. Use checkboxes for test cases]
- [ ] Test case 1
- [ ] Test case 2

## Screenshots/Demo

[Add screenshots, GIFs, or links to demos if applicable. Remove if not applicable]

## Notes

[Any additional notes, considerations, or follow-up items. Remove if not applicable]

## Documentation

[List any documentation updates or links to relevant docs. Remove if not applicable]

## Breaking Changes

[List any breaking changes and migration steps. If none, state "None."]

Create the PR using `gh pr create --title "<generated title>" --body "<generated description>`

Do not use Conventional Commits, either for commit messages and PR title.
