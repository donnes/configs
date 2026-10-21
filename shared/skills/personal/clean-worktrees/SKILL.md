---
name: clean-worktrees
description: Remove merged, clean git worktrees left by agent threads and report what else wastes disk or RAM. Use when the user asks to clean up merged worktrees, or when the daily scheduled cleanup runs.
---

# Clean Worktrees

This skill usually runs unattended on a schedule. Never ask questions. When anything is uncertain, keep the worktree and report it. A wrong removal can lose work. A kept worktree only costs disk until Donald looks at the report.

`scripts/clean_worktrees.py` next to this file does the checks and the removal. Its report is the interface: don't read its source, reimplement its rules by hand, or change its thresholds or code during a run. The summary below is enough. It needs only Python 3.9+ and works on macOS and Linux. Run it from any directory:

```sh
python3 <this skill's directory>/scripts/clean_worktrees.py            # report only; fetches origin
python3 <this skill's directory>/scripts/clean_worktrees.py --apply --only <path> [--only <path>]...
```

## Steps

1. Run the script without `--apply`. It prints the report, with removal candidates under "Would remove".
2. Cross-check each candidate with any thread tools the runtime exposes, such as T3 Code's `t3_thread_list` and `t3_worktree_list` or Purpose OS's equivalents. Drop a candidate if any thread on it, or on its root thread, is active, snoozed, running, or was updated in the last 24 hours. Note any disagreement with the script in the report. Without such tools, rely on the script's database check.
3. If the request is a dry run or report only, stop here. Otherwise, run `--apply` once, with `--only` for each candidate that passed step 2. The script re-checks each one immediately before removing it.
4. Reply with the script's report, plus your step 2 notes. Keep it short and scannable. Lead with what was removed and how much free space changed according to `df`.

If the script errors or a thread database can't be read, remove nothing and report the error.

## What the script enforces

- **Discovery:** It runs `git worktree list --porcelain` for every repo under `~/Git`, including nested org folders. It also includes the repos that own `~/.purpose-os/worktrees/*/*` and `~/.t3/worktrees/*/*`. It never touches a main checkout or a symlinked folder. One app folder is a symlink to a main checkout.
- **Thread protection:** It opens both apps' `statev2.sqlite` read-only and matches threads by `worktreePath`. A worktree is kept if a non-deleted thread on it, or that thread's `lineage.rootThreadId`, is any of these:
  - unsettled and unarchived, which includes subagent and review child threads
  - snoozed into the future
  - updated in the last 24 hours

  An active subagent whose root thread was deleted still keeps the worktree. Apps don't always settle children when they delete a finished run, so these are listed under "needs me" as likely orphans.

  A HEAD reflog that moved in the last 24 hours also keeps the worktree. The index is ignored here, because apps polling `git status` keep rewriting it.
- **Merge detection:** It runs `git fetch origin` and uses the real default branch from `origin/HEAD`, which may be `develop`. A worktree counts as merged only in one of these cases:
  - its HEAD is in the default branch
  - a MERGED PR's `headRefOid` equals HEAD
  - every commit after the merged PR head has an identical patch in the default branch, checked with `git cherry`

  It keeps the worktree if the branch has an open PR, if there's a merge commit after the PR head, or if any other commit follows the PR head.
- **gh accounts:** It runs `gh` from inside the repo, without inherited `GH_TOKEN`, so the `~/.local/bin/gh` wrapper picks the account from the repo's `github.user`. Run from elsewhere, `gh` uses the personal account and fails with "Could not resolve to a Repository". Any `gh` failure marks the repo unknown, and the worktree is kept. The script never switches the global `gh` account and never changes git or SSH config.
- **Dirty check:** Any staged, unstaged or untracked change keeps the worktree, except files that are gitignored. The report lists the dirty files. The script never runs `git worktree remove --force`.
- **Removal:** The script keeps the worktree if any process inside it still has a live parent. Otherwise it gives the orphaned processes inside SIGTERM and logs them. It runs `git worktree remove` from the main repo, then `git worktree prune`, and records `df` free space before and after each removal. It never deletes branches, stashes, scratch folders, caches or Docker data.
- **Report only:** It reports these and changes none of them:
  - orphaned worktree folders
  - leftover dev processes: parent gone, cwd missing or removed, or running over 12 hours with no active thread
  - duplicate or stray `git fsmonitor--daemon`s
  - containers and booted simulators
  - large caches, old scratch folders and old temp files

## Reading the numbers

`du` overstates what removal frees, because pnpm clones or hard-links files from its store. Past cleanups freed about 0.9 GB per large monorepo worktree, while `du` showed about 5 GB. Report only `df` deltas as space freed, and label any `du` figure as an estimate.
