---
name: provision-box
description: Set up, rebuild, or refresh a named development machine using Donald's machine inventory and configs CLI.
metadata:
  harness: [claude, codex]
  platform: [darwin, linux]
  scope: command-center
---

# Provision a box

Use the configs checkout that owns this skill. Resolve the installed skill
directory through its symlink; `COMPUTERS.md`, `COMPUTERS.local.md`, and `cli`
are three directories above that physical directory. Read both inventories
and the target's existing record. Run from the command-center machine, even
when the target is another computer.

## Identify the target and scope

Match the current hostname to its command-center record and the requested target
to its own record. Use the recorded SSH alias and checkout path. If either record
is missing or the connection is unavailable, collect what is known and ask for
the missing target information. Do not guess an address, create keys, change
SSH/Git identities, or switch global accounts to make access work.

Probe the target read-only before applying anything. Confirm its hostname, OS,
architecture, available disk space, Node/npm, configs revision and dirty state,
and selected runtime homes. The CLI needs Node >=20.12.0, npm, and either macOS
or an existing Omarchy installation. Do not force the Omarchy profile onto an
unrelated Linux distribution.

An agent/skill refresh selects `agents,skills`. Add `command-center` only when
the target is explicitly becoming a command center. For a broader setup, choose
components from `./cli --list-components` according to the request and existing
machine config; preserve that machine's exceptions. Do not run a full install
just to refresh agent guidance.

## Use the existing checkout and CLI

For a preview-only request, do not update the checkout, install dependencies,
write inventory records, or run install/uninstall. Use the existing CLI only if
its dependencies are already available. If the requested revision or CLI is
missing, stop with that prerequisite; do not publish or transfer changes as part
of a preview. Finish with "preview completed" or "preview blocked" and the
observations supporting it.

Inspect the intended repository, remote and authentication in the target's
context before authenticated Git operations. An existing dirty or diverged
checkout is a blocker for revision updates, not an invitation to reset, stash,
clean, or overwrite another agent's work. A refresh of the current revision is
possible when the user specifically wants that and the dirty state is understood.

Use an agreed published commit. Clone into the recorded path if it is absent,
or fetch and fast-forward an existing clean checkout. Do not delete an existing
directory to make cloning work. Do not replace remote files with the command
center's uncommitted working tree or private local inventory. If the requested
changes are unpublished, report that and finish the local work first; commit,
push or transfer a draft only within the user's authorized task.

Inspect the target checkout's README and CLI help at that revision. Run `npm ci`
there after dependency changes. Agent credentials, histories, caches, settings,
private keys, and secrets remain on their owning machines.

Run the preview on the target, with explicit components. For a worker refresh:

```sh
cd "$configs_checkout"
./cli --dry-run --only agents,skills
./cli --only agents,skills
```

These are two separate stages; a preview-only request runs only the first. Read
the preview before applying. A request to
provision the named box authorizes the requested components; do not ask again
for every routine step. During an authorized provisioning task, a first dry run
may install checkout-local npm dependencies, as the README describes.

Use `CODEX_HOME` and `CLAUDE_CONFIG_DIR` from the target record for non-default
runtime homes. Repeat the instruction install for each selected home without
copying credentials between them. Shared skills go into the target user's
`.agents/skills`; Claude skills go into the selected Claude config directory.

The unattended CLI preserves differing local copies. Treat `keep`/`differs`
entries as unresolved choices, not a completed replacement. Inspect them and
resolve only within the user's requested scope. Do not bypass conflict handling
with `rm` or invented force flags. An intentional local exception can remain,
with its reason recorded.

## Verify and record the outcome

Check the selected runtime instruction files contain shared guidance and the
target's matching OS context, and that the selected skill directories resolve
to the intended checkout. Confirm command-center skills are absent on workers;
remove only their managed links with `./cli uninstall --only command-center`
when a role change requires it. Keep foreign copies and report them as exceptions.

Record the actual revision and checks in the target's local inventory. New
machines keep only their own local record unless they also manage other boxes.
The command center updates its copy with the observed outcome. Portable purpose
or baseline changes belong in `COMPUTERS.md`; connection details stay local.

Start fresh runtime sessions to verify instruction loading when available.
Codex's `AGENTS.override.md` can supersede the installed `AGENTS.md`; inspect and
report an existing override without deleting it. Claude's `/memory` lists its
loaded memory files. Report filesystem installation separately from runtime
loading when a fresh session cannot be checked.

For package, shell, tmux or session-service changes, verify those actual
capabilities only when selected. Do not reboot the box, replace its OS, enable
unrequested services, or disturb running project processes to validate an
instructions refresh.

Finish with the target, installed revision, selected components/runtime homes,
checks that passed, preserved exceptions and blockers. Stop after verification
or an actionable blocker. Do not start a background updater or provision the
rest of the fleet from a request about one box.
