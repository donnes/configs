# donnes/configs

This repo is the source of truth for Donald's machines: the MacBook (macOS,
command center) and donnes-pc (Omarchy, worker). `./cli` applies it to the
machine it runs on and detects the OS. Read `README.md` for components and
details, and `./cli --help` for commands.

## Changing a machine

- Change the repo, then apply it with `./cli`. Don't install packages or edit
  managed files on the machine directly; the other machine would never get
  the change.
- Preview first with `./cli --dry-run --only <components>`, then apply the same
  selection. Afterwards, run `./cli health`; it should report no failures, and
  its receipt line should say the run completed.
- Apply changes on donnes-pc over SSH (`ssh donnes-pc`) from its own checkout,
  `~/.donnes/configs`, after the change is merged and pulled there.
- `./cli`'s `packages` and `gh-extensions` steps install only what is missing
  and don't ask to upgrade installed packages, though a new package can pull
  newer dependencies. Upgrades are separate, explicit commands (README,
  Packages and upgrades); don't run them as part of an unrelated change.

## Where things go

- Language runtimes and CLIs: `shared/mise/conf.d/donnes.toml`, used on both
  machines. Agent CLIs that Omarchy installs itself (claude, codex,
  cursor-agent) go in `macos/mise/conf.d/donnes-macos.toml` instead; Omarchy's
  wrappers fail when the shared file declares them too. System packages: `packages/macos.txt`, `packages/macos-casks.txt`
  and `packages/omarchy.txt`. gh extensions: `packages/gh-extensions.txt`, shared
  by both machines and installed by the `gh-extensions` component.
- Only list tools Donald runs directly. Dependencies other tools need stay with
  whatever needs them.
- JavaScript globals go through `bun add -g`, not npm or pnpm.
- opencode v2 comes from its own installer, not mise. fastlane and atuin stay
  system packages.
- Skills: Donald's own skills go in `shared/skills/personal/<name>`; skills
  installed from other repos with `npx skills` stay in `shared/skills/<name>`
  and in `shared/skills.lock.json`. A third-party skill edited here leaves the
  lockfile, so an update can't overwrite the edit. Command-center-only skills
  go in `fleet/skills`.
- Agent instructions: edit `shared/agents/global/AGENTS.md` or the OS
  `CONTEXT.md`, never the generated `.generated/agents/*/AGENTS.md`.
- Private details (hostnames, SSH aliases, account mappings) belong in the
  ignored `COMPUTERS.local.md`, never in tracked files. A machine's role,
  JavaScript runtime owner (`jsRuntimes`), runtime homes and accepted health
  exceptions go in its own
  `~/.config/donnes-configs/machine.json`; the CLI writes its apply receipt to
  `~/.local/state/donnes-configs/receipt.json`. Neither is tracked.

## Omarchy

Never hand-edit Omarchy's files, including `~/.config/mise/config.toml`. The
CLI goes through Omarchy's and mise's own commands (`omarchy-pkg-add`, the
`omarchy-install-*` installers, `mise settings add`, `mise unuse -g`). Keep
Omarchy's `upgrade.auto_prune = false`.

## Checks

```sh
npm run check                  # TypeScript
npm test                       # the end-to-end suite (npm run test:e2e)
npm run test:e2e -- -k receipt # tests whose names match
```

Run both on macOS, and on donnes-pc when a change affects Omarchy.

## Tests

The suite in `tests/e2e/` is end-to-end only, following the same rules as
t3code's testing strategy:

- Every test runs the real `./cli` (or a shipped script such as
  `macos/bin/xcode-node-env`) in a sandbox from `tests/e2e/harness.py`. Never
  import or mock the TypeScript modules, and don't add exports, flags or hooks
  that only tests use.
- Doubles exist only for external commands, in `tests/e2e/boundary.py`. They
  keep the state the real tool keeps and reject what it rejects; an invocation
  they don't model fails the test. Add a case there when the CLI starts running
  a new command, instead of accepting anything.
- Assert what the user or machine ends up with: files, receipts, the doubles'
  state, `health --json` statuses and ids. Assert exact arguments only when they
  are the external contract, such as REA's pinned version.
- The sandbox environment is an allowlist and its directories live under the
  ignored `.scratch/e2e`; never point a test at the real home, runtime homes or
  package managers.
- Add a test for a new invariant or a real failure, preferably as a row or step
  in the test that already owns the behavior. A regression test must fail
  without its fix.
