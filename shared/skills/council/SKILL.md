---
name: council
description: Trigger this if the user says 'council'.
---

# Council

Bring in four delegates to help with the user's request, usually for review
or feedback. Use one strong model from each of four different providers, at
high reasoning effort. If the user's instructions name council members, use
those. Otherwise use the latest Claude Opus, the latest GPT Sol, Kimi K3.1 Pro
from OpenCode Go, and Grok 4.7 from Grok Build.

In T3 Code, use `orchestrator_capabilities` to resolve the models, then
`delegate_task` to start one delegate per model in parallel. Kimi runs on the
`opencode` provider as `opencode-go/kimi-k3.1-pro`. It has no default
variant, so pass `variant: high`. Grok runs on the `grok` provider as
`grok-4.7` with `reasoningEffort: high`. Use Grok Build for it, never
OpenCode.

In Monocode, use the `app` CLI whose path is in your context. It appears in a
Mono and in a thread whose message started with `/operator`. Without it, tell
the user to resend the request starting with `/operator`, and stop.

1. Run `models.list` to resolve each member's `harness`, `model` and settings.
   Grok 4.7 uses the Grok Build harness, not OpenCode.
2. Run `sessions.start` once per member with those values, `"effort": "high"`
   where the model has it, and `"runtimeMode": "read-only"` for review or
   feedback. Children get no history, so put the repo's absolute path and the
   full request in the prompt. Ask for one final message under 6,000
   characters, because `sessions.read` returns only the last message and caps
   it there.
3. Wait. In a Mono, set `"notifyOnComplete": true` and end your turn. Elsewhere,
   run `scripts/monocode-wait <cli> <session ids>` from this skill's directory
   as a foreground command, and run it again if it exits 3.
4. Read each reply with `sessions.read` and `"maxChars": 6000`. A session with
   no reply failed. For a fresh review, use `sessions.send` on the same session.

Elsewhere, use the harness's subagent tools. If you cannot reach four
providers, or a named member is unavailable, report it instead of substituting.

Give each delegate the request and relevant context. For review or feedback,
keep their work read-only. Collect their responses and summarize the useful
findings, disagreements, and recommended next steps.

If you agree with their recommendations, make the changes and request a fresh
review after. Continue this process until all delegates are satisfied with the
outcome.

Do not let repeated reviews result in scope creep. It is your job to fight to
keep scope limited.
