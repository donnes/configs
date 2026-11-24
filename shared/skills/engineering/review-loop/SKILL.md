---
name: review-loop
description: Use when the user says "review loop".
---

# review-loop

This is a workflow for making your code changes more correct before (or
sometimes after) filing a pull request. tl;dr - Astra reviews your code, Gemini
checks Astra's review, and you fix what survives, in a loop.

Make the most minimal possible changes to appease the reviewers. Be careful
of scope creep and don't be scared to push back.

## Budget

- Default: 3 rounds total. A round is one Astra review and one Gemini check of
  it. Round 1 is full. Later rounds check only changed code and open findings.
- Extend to 5 only for security, permissions, auth, data loss, or
  state/concurrency, while a blocker or should stays open with evidence. Or when
  the user asks.
- Stop early if a round returns only nits. Declined nits and comment,
  doc, or format-only fixes need no new round.
- One Astra and one Gemini per round. Neither may start subagents or reviewers.
- Keep a ledger: id, severity, outcome, usage if returned. Never guess it.

## 1. Scope

Run `git status --short`. Do not stash, discard, or include unrelated
changes. Limit review to the change paths if they separate cleanly.
Otherwise stop and ask.

Find the base after `git fetch origin`:

- PR: `gh pr view <n> --json baseRefName,headRefOid`. Check out the branch
  only if clean. Confirm `HEAD` is the PR head, or ahead only by this
  change. Base: `git merge-base HEAD origin/<baseRefName>`.
- Local: `git merge-base HEAD origin/<default-branch>`. No remote: a base
  the user names, or `HEAD` for uncommitted changes only.

The change is base to working tree in those paths, with untracked files.
Use one diff command all rounds. State intent and out-of-scope in 1-2
sentences. Run covering checks. Do not send code this change breaks. Note
missing or pre-failing checks in the brief.

## 2. Run the reviewers

Each round runs Astra 6.2 High, then Gemini 4 Neon High on Astra's reply. Only
Gemini's reply comes back to this thread as the round's result. Use other
models only when the user names them.

In T3, call `orchestrator_capabilities` to resolve both models. Astra runs on
the `codex` provider as `gpt-6.2-astra` with `reasoningEffort: high`. Gemini
runs on the `antigravity` provider as `gemini-4-neon` with
`thought_level: high`. Start each with `delegate_task` (`role: "review"`,
`mode: "async"`), Astra first and Gemini once Astra's reply is in. Save each
`taskId`. New `clientRequestId` per task. `childThreadId` is storage, not the
next target. Do not use `t3_thread_send`, `create_threads`, or
`t3_thread_launch` for review.

In Monocode, use the `app` CLI whose path is in your context. It appears in a
Mono and in a thread whose message started with `/operator`. Without it, tell
the user to resend the request starting with `/operator`, and stop. Resolve
both models with `models.list`, then `sessions.start` one session per model with
its `harness`, `model`, high effort and `"runtimeMode": "read-only"`. Keep both
session IDs. Add to each brief: "Reply in one final message under 6,000
characters." `sessions.read` returns only the last message and caps it there.
In a Mono, set `"notifyOnComplete": true` and end your turn. Elsewhere, run
`../council/scripts/monocode-wait <cli> <id>` from this skill's directory as a
foreground command, and run it again if it exits 3. That script is the one
exception to "do not poll" below. Read each reply with `sessions.read` and
`"maxChars": 6000`.

If T3 tools are not listed, try one direct capability call. Outside T3 and
Monocode, use native subagents that run Astra and Gemini and keep their IDs.
In Claude Code, use a custom subagent only if it is set up to run that model.
If no route runs either model, report the blocker. Do not substitute a model.

Do not edit scoped files while a review runs. Wait for each notice. Do not
poll or start a second reviewer. Timeout, error, or no reply is not
approval. On failure, cancel, verify stop, restart with the ledger.

Astra's round 1 brief (children get no history):

```
Review only. Do not edit, commit, push, comment on PRs, or start subagents.
Repo: <abs path> Base: <sha> Intent: <intent> Out of scope: <scope> Checks: <results>
See: git diff <base> [-- <paths>]; git status --short (read untracked).
Read surrounding code. Find bugs, broken callers, mismatch with intent.
Skip style unless it hides a bug. Hold to the smallest change. Flag code,
tests, or guards the intent does not need. Other paths, rare cases, small
perf, extra compat: nits.
blocker = intended case wrong. should = real bug callers will hit, in intent. nit = rest.
Reply:
VERDICT: APPROVE or CHANGES
A1 [blocker|should|nit] <file>:<line> <claim>. Fix: <suggestion> (stable ids)
```

Gemini's brief:

```
Review only. Do not edit, commit, push, comment on PRs, or start subagents.
Repo: <abs path> Base: <sha> Intent: <intent> Out of scope: <scope>
See: git diff <base> [-- <paths>]; git status --short (read untracked).
Another reviewer, Astra, reviewed this change. Check each Astra finding
against the code. Confirm it, reject it with evidence (file:line, test,
output), or correct its severity or fix. Check whether Astra's verdict
holds. Add a finding only for a blocker or should Astra missed.
blocker = intended case wrong. should = real bug callers will hit, in intent. nit = rest.
Astra's reply:
<Astra's reply, verbatim>
Reply:
VERDICT: APPROVE or CHANGES
A1 confirmed|rejected|changed [severity] <reason>. Fix: <suggestion if changed>
G1 [blocker|should] <file>:<line> <claim>. Fix: <suggestion> (new findings only)
```

## 3. Answer findings

Work from Gemini's reply. Treat findings Gemini rejected as declined unless
you disagree after checking. Check each remaining finding and severity
yourself. Another path, rare case, or small cost is a nit, whatever label it
came with.

- Agree: smallest fix. Prefer delete or narrow over new lock, cache,
  helper, or option. Fix the case that happened. Add one focused test
  that fails without the fix, if intent needs it.
- Disagree: say why, with evidence (file:line, test, output).
- Out of scope or nit: decline in one line. List as follow-up.

Update the ledger. Re-run checks and `git diff --shortstat <base>`. If
review grew the diff, cut first. Do not agree just to end the loop.

## 4. Next round

Start one only if budget remains and a blocker or should is open, behavior code
changed, or approval does not cover the current behavior diff. Use fresh
`delegate_task`s in T3, `sessions.send` to the saved sessions in Monocode, or
follow up the saved native IDs. Send Astra the round 1 brief, the ledger
(`fixed:` / `disagree:` / `declined:` + evidence), the same base diff, and the
change since last round. Tell Astra: open ids and changed code only. Mark each
old id `resolved` or `still open: <reason>`. Then send Gemini its brief with
Astra's new reply and the ledger.

## 5. Stop and ship

Agreed: Gemini's APPROVE on the current behavior diff, no blocker or should
open, no concern of your own. Stuck: an item stays disputed after two replies,
or budget ends. Show both sides in 2-3 lines each. The user decides.
Budget end is not approval.

Do not push during the loop. Push after agreement only if the user asked
to push, ship, or update the PR. If you push to a PR, add above the model
blurb:

`Reviewed with review-loop: <N> rounds with <Astra model>, checked by <Gemini model>. Verdict: approved`.

Add effort only if verified.

Report: rounds, models, what review changed, diff size before/after, fixed and
declined findings with reasons, findings Gemini rejected, usage if exposed
(else say not), pushed or not.
