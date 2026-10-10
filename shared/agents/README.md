# Personal agent setup

This directory is the starting point for Donald's shared agent instructions.
`global/AGENTS.md` is the shared source composed by the `agents` component with
the host's OS context.

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
| OS-specific context | `macos/agents/CONTEXT.md` and `linux/agents/CONTEXT.md` | Composed into installed instructions for the matching profile |
| Machine inventory | Root `COMPUTERS.md` and ignored `COMPUTERS.local.md` | Portable roles in Git; connection records stay local |
| Command-center workflows | `fleet/skills/<name>` | Explicit `command-center` component |
| Runtime-specific instructions | Add `shared/agents/runtimes/<runtime>/` when needed | Only that runtime |
| Specialist roles | Add `shared/agents/roles/` when a real delegated workflow needs them | Explicitly selected roles |
| Project instructions and skills | Inside each project's repository | Travel with the project and its worktrees |
| Host-specific facts and secrets | Local machine configuration | Never copied wholesale into global instructions |

These are organizational boundaries, not an automatic instruction-loading hierarchy.
A runtime must explicitly load or receive each applicable piece. Custom skill metadata
such as platform or scope does not enforce distribution by itself.

## Install and use

```sh
./cli --dry-run --only agents
./cli --only agents
```

The installer generates `.generated/agents/<profile>/AGENTS.md` from the shared
preferences, matching OS context, and references to the machine inventories.
It links that composed file to:

- `${CODEX_HOME:-~/.codex}/AGENTS.md` for Codex.
- `${CLAUDE_CONFIG_DIR:-~/.claude}/CLAUDE.md` for Claude Code.

Edit the shared source or matching `CONTEXT.md`, rerun `./cli --only agents`,
then start fresh sessions. Generated files are ignored by Git and replaced by
the installer; edit the sources instead. Project instructions can refine these
global preferences. The instruction composition is identical for Codex and Claude,
so it does not depend on a runtime-specific Markdown import mechanism.
Codex's global `AGENTS.override.md` takes precedence over `AGENTS.md`; check
that file if the shared instructions appear to be ignored. In Claude Code,
use `/memory` to inspect loaded memory files.

Existing different files use the installer's normal conflict handling. Without
a terminal they are preserved. Uninstall only the managed instruction links with:

```sh
./cli uninstall --only agents
```

These entry points cover Codex and Claude Code. Other runtimes need their own
supported adapters. Claude Cowork does not load this external user-file symlink.
Omarchy receives Linux context; macOS receives Mac context. Repeat the install
with explicit `CODEX_HOME` and `CLAUDE_CONFIG_DIR` for other selected profiles.

Verify actual loading in fresh sessions inside and outside projects and in
worktrees. The installer verifies file distribution, not model compliance.
Keep an observed failure and desired outcome for each substantial new rule.

Official references:

- [Codex custom instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Claude Code memory](https://code.claude.com/docs/en/memory)

## Public and local content

The global draft covers a shared personal/work computer without identifying any
employer or client. Environment files describe macOS and Linux use. They are
source documents composed into the matching host's global instruction entry point.

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

## Provisioning other boxes

The MacBook is the command center. Install `agents,skills,command-center` there
to expose `provision-box` to Codex and the selected Claude runtime. Ordinary
workers use `agents,skills`; management skills are a separate collection and are
not selected by a default install. Existing command-center links remain during a
normal refresh; remove them explicitly when a machine changes roles.

Read [the machine inventory](../../COMPUTERS.md) and the local connection records
before remote setup. The skill reuses the CLI, checks the target's revision and
local edits, previews explicit components, and records actual verification. It
does not authorize provisioning unrelated machines or copying runtime credentials.
