# Personal agent setup

This directory is the starting point for Donald's shared agent instructions.
`global/AGENTS.md` is the shared source installed by the `agents` component.

## Existing foundation

The configs installer already links each `shared/skills/<name>` directory into
`~/.agents/skills` and `~/.claude/skills`. Keep shared skills there. Avoid creating
a second skill collection here or moving existing skills merely to reorganize them.

Runtime credentials, sessions, history, caches, and machine-local settings remain
outside this repository. Tracking selected instruction files does not mean tracking
entire `~/.codex` or `~/.claude` directories.

## Where things belong

| Concern | Source | Distribution |
| --- | --- | --- |
| Personal defaults | `shared/agents/global/AGENTS.md` | Global instruction entry point for each supported runtime |
| Shared workflows | `shared/skills/<name>/SKILL.md` | Existing skills installer |
| OS-specific context | `macos/agents/CONTEXT.md` and `linux/agents/CONTEXT.md` | Only the matching operating system |
| Runtime-specific instructions | Add `shared/agents/runtimes/<runtime>/` when needed | Only that runtime |
| Specialist roles | Add `shared/agents/roles/` when a real delegated workflow needs them | Explicitly selected roles |
| Project instructions and skills | Inside each project's repository | Travel with the project and its worktrees |
| Host-specific facts and secrets | Local machine configuration | Never copied wholesale into global instructions |

These are organizational boundaries, not an automatic instruction-loading hierarchy.
A runtime must explicitly load or receive each applicable piece. Custom skill metadata
such as platform or scope does not enforce distribution by itself.

## Install and use

```sh
./install --dry-run --only agents
./install --only agents
```

The installer links the same source file to:

- `${CODEX_HOME:-~/.codex}/AGENTS.md` for Codex.
- `~/.claude/CLAUDE.md` for Claude Code.

Edit `shared/agents/global/AGENTS.md` once to update both. Start fresh sessions
following changes. Project instructions can refine these global preferences.
Codex's global `AGENTS.override.md` takes precedence over `AGENTS.md`; check
that file if the shared instructions appear to be ignored. In Claude Code,
use `/context` to inspect loaded memory files.

Existing different files use the installer's normal conflict handling. Without
a terminal they are preserved. Uninstall only the managed instruction links with:

```sh
./install uninstall --only agents
```

These entry points cover Codex and Claude Code. Other runtimes need their own
supported adapters. Claude Cowork does not load this external user-file symlink.
OS context files below are not yet connected to runtime instruction loading.

Verify actual loading in fresh sessions inside and outside projects and in
worktrees. The installer verifies file distribution, not model compliance.
Keep an observed failure and desired outcome for each substantial new rule.

Official references:

- [Codex custom instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Claude Code memory](https://code.claude.com/docs/en/memory)

## Public and local content

The global draft covers a shared personal/work computer without identifying any
employer or client. Environment files describe macOS and Linux use. They are
source documents awaiting installer integration, not automatically loaded overlays.

Keep account mappings, directory-based identity rules, host access details, and
credentials local. Do not publish raw Git, SSH, or GitHub CLI configuration as part
of an inventory. A public setup should describe the routing behavior without
identifying the organizations behind it.

Before publishing, review the selected files, staged diff, and repository history.
These starter documents do not establish that every existing tracked configuration
or historical commit is suitable for public distribution.

## What we took from the video

Use observed mistakes to improve the setup. Keep global preferences short enough
to review, put repeatable procedures in skills, and document project hazards with
the project. Include concrete desired outcomes and verify that instructions reach
fresh sessions and worktrees.

The global draft follows the supplied screenshots' format: a personal introduction,
section headings, and concise bullet points. It adapts the guidance to Donald's
personal/work machine boundaries, directory-scoped authentication, Linux use,
and React Native development.

## First skills to consider

Choose workflows that Donald repeatedly requests or corrects. Possible candidates
are PR creation and PR monitoring, but they should be written from Donald's own
examples and repository conventions. No new skills are installed by this starter.

Keep descriptions focused on when to use a skill. Give its body concrete steps,
required capabilities, expected outputs, and a clear stopping condition. Separate
skills when their triggers or permissions differ.
