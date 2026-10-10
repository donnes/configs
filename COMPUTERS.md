# Computers

This is the portable inventory of Donald's development machines. Update it when
a machine's purpose or desired setup changes. Connection details and observations
belong in the ignored `COMPUTERS.local.md` beside this file.

## Machines

| ID | Platform | Role | Purpose |
| --- | --- | --- | --- |
| `macbook` | macOS, Apple Silicon | Command center | Personal and professional development, React Native, Xcode and the iOS simulator; manages the other boxes. |
| `donnes-pc` | Omarchy, x86_64 | Worker | Personal development on Arch-based Linux. General development is moving here over time. |

The MacBook still does general development. Its eventual emphasis on iOS does
not prohibit other work today. Future professional Linux environments get their
own records and account boundaries; do not infer them from `donnes-pc`.

## Desired baseline

- Each box has a local configs checkout and its own credentials and runtime state.
- `agents` composes shared preferences with `macos/agents/CONTEXT.md` on macOS,
  or `linux/agents/CONTEXT.md` on Omarchy. Both Codex and Claude receive that text.
- `skills` installs shared workflows. Only the command center opts into the
  separate skills under `fleet/skills/`.
- An instructions/skills refresh selects only those components. Packages,
  editor configuration, shells, tmux, Git, and session services are selected
  explicitly when provisioning needs them.
- Reuse the CLI's conflict handling. Keep foreign files, running sessions,
  account routing, and machine-specific configuration intact.

Examples from the target's configs checkout:

```sh
# Worker: preview or refresh instructions and shared skills.
./cli --dry-run --only agents,skills
./cli --only agents,skills

# Command center: also install the machine-management skills.
./cli --dry-run --only agents,skills,command-center
./cli --only agents,skills,command-center
```

`command-center` is unchecked in an interactive install and excluded from the
default install. A normal refresh keeps an already installed command-center
collection. Remove it when a box stops being a command center:

```sh
./cli uninstall --only command-center
```

## Local records

`COMPUTERS.local.md` is a per-checkout operator inventory. Keep the current
machine's record there, plus the machines it manages. Read it only when host
details are needed; do not copy it wholesale to another box or a public report.

For each record, keep:

- Machine ID, actual hostname, role, and supported install profile.
- SSH alias, if remote access is configured, and the configs checkout location.
- Explicit Codex homes and Claude config directories that need instructions.
- Capabilities and meaningful exceptions to the baseline.
- Last verification date, checked revision, checks performed, and pending work.

Unknown or stale fields stay explicit. Verify identity, OS, connectivity, and
checkout state again before changing a box. An inventory entry is not proof that
a host is online or permission to modify it.

Keep private addresses, account mappings, usernames, and professional identifying
details local. Never put credentials or private-key contents in either inventory.
Use existing SSH aliases and credential configuration.

## Provisioning

Use the `provision-box` skill from the command center when asked to set up,
rebuild, or refresh a named machine. It uses this inventory and the existing CLI
instead of building a second installer. Add a new machine's desired role here and
its verified connection record locally before provisioning it.

This repo installs overlays onto an existing macOS or Omarchy environment. OS
installation, disk changes, firmware changes, account creation, and unattended
services need their own explicit task.
