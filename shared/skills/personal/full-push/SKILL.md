---
name: full-push
description: Trigger this if the user says 'full push'.
---

# Full Push

The user is not watching this thread and wants the change on the default
branch without a pull request. You own it from its current state until it is
pushed and you have seen it work there. Agents review the change instead of a
human, so the review and proof steps carry the weight a PR review would.

If the user did not ask for "full push" in some clear way, do not push to the
default branch.

Read [full-send](../full-send/SKILL.md). Its Testing permission, Proof and
Asking the user sections apply here unchanged. Its PR, babysitting and merge
steps do not; the steps below replace them. Where full-send asks for a PR
link, give the pushed commit SHAs.

The user grants you permission to:

- Commit this task's changes and push them to the default branch as a
  fast-forward.
- Push a `git revert` of your own commits when they break the default branch
  or production.
- Read CI logs, deploy status, and production logs and metrics with access
  you already have.

## Before you start

Stop and ask, offering full-send instead, when the repo does not take direct
pushes:

- Project instructions or a CONTRIBUTING file require pull requests or
  reviews.
- Branch protection or a ruleset rejects the push. Never bypass it.

Run `git status`. Commit only the files this task changed, and leave other
local work alone. You can work on any local branch or worktree; you push its
commits to the default branch, not the branch itself.

## Steps

1. **Finish the change.** Use the smallest change that works. If it leaves
   code, flags or config unused, delete them in the same change.
2. **Prove it.** Follow full-send's Proof. Run the checks CI runs before you
   push, because a failure now lands on the default branch instead of a branch
   you can throw away.
3. **Review it.** Run `sol-review-loop` on the local change. Fix real findings
   and prove each fix.
4. **Commit.** Follow the repo's commit message conventions. Put unrelated
   changes in separate commits.
5. **Push.** Run `git fetch origin` and rebase onto `origin/<default>`. If the
   rebase brought in changes to the code you touched, rerun the checks. Then
   run `git push origin HEAD:<default>`. When the push is rejected because the
   remote moved, fetch and repeat. Never force-push the default branch.
6. **Watch it land.** Find the CI runs for the pushed SHA with
   `gh run list --commit <sha>`, then wait on them in the background with
   `gh run watch <id> --exit-status`. In T3 Code, wait with
   `t3_background_wait`. If the repo deploys from the default branch, wait for
   the deploy too, then check the result where you can observe it: the deployed
   version, a smoke request, production logs. The work ends when the change is
   live and you have seen it work, not when the push succeeds.
7. **Fix forward or revert.** If a failure comes from your change, fix it and
   push again with new proof. If production is affected or the fix is not
   quick, push a `git revert` of your commits first, confirm the default
   branch is green, then fix. If a failure is a flake unrelated to your
   change, rerun it once with `gh run rerun <id> --failed` and say so in the
   report.
8. **Report** in your final message: the pushed SHAs, the CI runs and their
   results, what you checked after the deploy, your proof, any reverts, and
   each decision you made for the user.

Stay active from step 1 to step 7. If you end your turn while CI or a deploy is
pending, nobody checks the result.

## Limits

Read-only production access is part of the grant. Production writes are not:
migrations, data fixes, feature flag changes, infrastructure applies. Ask
first, as full-send's Asking the user describes.

Do not send messages that people will read, such as emails to users,
announcements, chat posts or issue replies. Draft them in the report for the
user to finish and send. Commit messages and code comments are fine.
