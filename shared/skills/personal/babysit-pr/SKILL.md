---
name: babysit-pr
description: Use when the user asks to monitor, Ivatch, or babysit a PR.
---

# Babysit PR

Review bots are useful, but they are not always right. Check their findings against the source before changing code.

## Start with the right PR

Identify the repository, PR, head branch and commit, actual base branch, and required checks and reviews. Read the project instructions and PR description to understand the original goal. If the target is ambiguous, ask which PR to watch.

Respect directory-scoped Git and SSH identities. Check the intended Git author, remote authentication, and GitHub CLI account separately before authenticated actions. Do not switch global accounts or rewrite remotes to fix a mismatch.

Establish what the request authorizes. A request to babysit and fix a PR includes relevant fixes, validation, commits, pushes to its branch, and review replies. A request to only watch or report stays read-only. Merge, closure, deployment, and changes outside the PR's goal need separate authorization. Use authorization already given instead of asking again.

## Watch and respond

Use the runtime's PR-monitoring tools when available. Otherwise, poll checks, reviews, inline review threads, and PR conversation comments. Watching CI alone misses review feedback. Wait between polls, respect rate limits, and avoid overlapping watchers. Do not promise background monitoring if the runtime cannot keep running.

Track the head commit, check runs and attempts, and feedback already handled. Evaluate CI and review completion against the current head. Re-read updated comments. Older unresolved feedback may still apply, so verify it against current code instead of discarding it by timestamp. Do not act on a failure already superseded by a passing run or fix a finding that the current code already addresses.

For each actionable finding, read the relevant code and failure logs. Fix real defects with the smallest change that satisfies the PR's goal, then run verification appropriate to the change. Preserve unrelated local work. Commit only the relevant files and push to the PR's existing branch when authorized. If someone else pushes, refresh the head and reconcile their changes before continuing.

Distinguish repository failures from infrastructure flakes. Retry an identified transient failure when authorized, but do not repeatedly rerun a deterministic failure or weaken checks to get green. After two retries of the same infrastructure failure without progress, report the blocker.

After every push, refresh the head commit and wait for checks and applicable review bots to evaluate it. A green result for an earlier commit does not establish readiness. If a bot does not rerun automatically, use the repository's documented retrigger mechanism when authorized, or report that review is outstanding.

## Handle review feedback

Explain why a finding is incorrect, already fixed, or outside the PR's scope. Give a concrete reason grounded in the code. Reply in the existing thread when authorized, then resolve bot threads that are actually addressed or dismissed with evidence. Do not dismiss a human review or resolve an unresolved human concern on the reviewer's behalf.

Format replies posted on Donald's behalf as:

```md
[MODEL-SLUG] RESPONDING ON BEHALF OF DONALD

[actual reply]
```

Use the actual model identifier if available. Otherwise use the agent name without inventing a model version. Keep replies short and avoid repeating acknowledgments. If posting is outside the request's scope, provide the proposed reply to Donald instead.

Screenshots or short recordings can help explain visual changes. Share them only through the project's approved channels, with private information excluded. Do not assume a particular upload skill or public host is available.

## Keep the PR focused

Watch the actual base branch for conflicts and overlapping changes. Follow the repository's merge or rebase policy when an update is necessary. Do not rewrite a shared branch without authorization. Where an authorized rebase requires a rewritten push, use a lease tied to the remote head you inspected and stop if it changed.

If another PR makes this one obsolete, stop monitoring and report why. Close it only if explicitly authorized.

Do not let review feedback expand the PR beyond the original goal. Report unrelated suggestions as follow-up work instead of implementing them here.

## Stop at a clear outcome

Stay quiet when nothing changes. Report meaningful fixes, newly discovered blockers, and the final outcome.

Before declaring readiness, refresh the PR and confirm that the head has not changed, required checks pass, applicable bot reviews are complete, and required human approvals are satisfied. Pending or unavailable results are not a pass. Preserve the requested draft status.

Stop when the PR is ready, when it is merged or closed, when the user asks, or when progress requires missing access, a human decision, or external recovery. Report the PR link, final head commit, relevant fixes and verification, and any remaining blocker. Do not leave a watcher running after stopping.

Merge only when explicitly requested and allowed by the repository's policy. Otherwise report that the PR is ready. Deployment is a separate action.
