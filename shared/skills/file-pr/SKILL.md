---
name: file-pr
description: File a concise pull request. Use when the user asks to file, open, or create a PR.
---

# File PR

Before filing, check whether a PR for this branch already exists. If it does, use it instead of opening a duplicate. Do not reopen a merged or closed PR without checking the user's intent.

Read the repository instructions and PR template. Identify the intended base branch and remote, including fork or stacked-branch workflows. Review the full branch diff against that base using the merge base, not just the latest commit. Confirm that the changes match the user's goal and preserve unrelated local work.

Respect directory-scoped Git and SSH identities. Before committing, pushing, or creating the PR, check the repository's intended Git author, SSH authentication, and GitHub CLI account separately. Do not switch global accounts or rewrite shared configuration to work around an authentication mismatch. Ask if the intended identity is unclear.

A request to open a PR includes the relevant commits and branch push needed to file it. Stage only changes belonging to the task. Run the project's required checks and verification appropriate to the change. Report failures and checks you could not run honestly. If the request is only to draft a title or description, return the text without publishing anything.

## Title

PR titles may become commit messages. Follow the repository's title conventions, using recently merged PRs and Git history as examples. Prefer a concise, readable title that tells the reviewer what improves. Use conventional commits where the project uses them.

For performance changes, include a measured improvement only when the evidence supports it.

### ❌ DON'T

`fix: remove buildContextualThreadOptions`

This names an implementation detail without explaining what improves.

### ✅ DO

`fix: apply workspace defaults to new threads`

This tells the reviewer what behavior changes.

## Description

Open with a simple explanation of the problem, then briefly explain the solution. Write for a reviewer who has not seen the conversation. Use a concrete before-and-after example when it helps.

### ❌ DON'T

> Removed buildContextualThreadOptions, moved defaults into createThread, and updated the tests.

This lists implementation work without explaining the problem.

### ✅ DO

> Starting a new thread inside an existing worktree ignored the configured workspace defaults. New threads now use those defaults consistently.

This explains the problem and the resulting behavior.

Keep the detail proportional to the change. A small fix usually needs one or two sentences and relevant verification. For larger changes, explain the behavior, meaningful tradeoffs, and limitations. Follow the repository's template without filling sections with irrelevant boilerplate.

Describe the final change. Rewrite the title and description if the scope changed during implementation. Avoid an inventory of functions and files, conversational history, and abandoned approaches unless they explain a decision the reviewer needs to assess.

Include what you actually verified and any material remaining risk. Attach screenshots or recordings when they help evaluate a visual change, using the project's approved sharing channels. Keep credentials and identifying work details out of public content.

## File and hand off

Use the requested draft status and the repository's review workflow. Do not assume every review bot requires a non-draft PR. Preserve an existing PR's status unless the request authorizes changing it.

Use explicit repository, base, and head values when filing so defaults cannot select the wrong target. Pass multiline descriptions through a structured tool argument or a temporary file with `gh --body-file`. Preserve actual newlines and avoid shell interpolation of the description.

After filing, verify the PR's URL, base, head, title, description, and draft status. Return its link with a short verification summary and any blocker. Do not merge or deploy as part of filing.

If the user also asked to monitor or babysit the PR, continue with the `babysit-pr` skill. Otherwise stop after filing and reporting the result.
