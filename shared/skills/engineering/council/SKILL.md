---
name: council
description: Trigger this if the user says 'council'.
---

# Council

Bring in delegates to help with the user's request, usually for review or
feedback. If the user's instructions name council members, use those.
Otherwise use Claude Fable 5.2 High, Astra 6.2 High from Codex, Gemini 4 Neon
High from Antigravity, and Muse Wonder Full from Muse when Muse is available.

In T3 Code, use `orchestrator_capabilities` to resolve the models, then
`delegate_task` to start one delegate per model in parallel. Fable runs on the
`claudeAgent` provider as `claude-fable-5-2` with `effort: high`. Astra runs on
the `codex` provider as `gpt-6.2-astra` with `reasoningEffort: high`. Gemini runs
on the `antigravity` provider as `gemini-4-neon` with `thought_level: high`.
Muse Wonder runs on the `muse` provider at its `Full` setting; take the model
id and option name from `orchestrator_capabilities`. When the `muse` provider
is disabled or lists no Wonder model, run the council without it and say so.

In Monocode, use the `app` CLI whose path is in your context. It appears in a
Mono and in a thread whose message started with `/operator`. Without it, tell
the user to resend the request starting with `/operator`, and stop.

1. Run `models.list` to resolve each member's `harness`, `model` and settings.
   Leave Muse out when `models.list` has no Muse Wonder model.
2. Run `sessions.start` once per member with those values, the member's
   effort (`high`, or `Full` for Muse) where the model has it, and
   `"runtimeMode": "read-only"` for review or feedback. Children get no
   history, so put the repo's absolute path and the full request in the
   prompt. Ask for one final message under 6,000
   characters, because `sessions.read` returns only the last message and caps
   it there.
3. Wait. In a Mono, set `"notifyOnComplete": true` and end your turn. Elsewhere,
   run `scripts/monocode-wait <cli> <session ids>` from this skill's directory
   as a foreground command, and run it again if it exits 3.
4. Read each reply with `sessions.read` and `"maxChars": 6000`. A session with
   no reply failed. For a fresh review, use `sessions.send` on the same session.

Elsewhere, use the harness's subagent tools. If Fable, Astra or Gemini, or a
member the user named, is unavailable, report it instead of substituting.

Give each delegate the request and relevant context. For review or feedback,
keep their work read-only. Collect their responses and summarize the useful
findings, disagreements, and recommended next steps.

If you agree with their recommendations, make the changes and request a fresh
review after. Continue this process until all delegates are satisfied with the
outcome.

Do not let repeated reviews result in scope creep. It is your job to fight to
keep scope limited.
