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
  selection. Afterwards, run `./cli health`; it should report no failures.
- Apply changes on donnes-pc over SSH (`ssh donnes-pc`) from its own checkout,
  `~/.donnes/configs`, after the change is merged and pulled there.
- `./cli`'s `packages` step runs `brew install`, which also upgrades outdated
  formulae and casks. Select it only when packages changed.

## Where things go

- Language runtimes and CLIs: `shared/mise/conf.d/donnes.toml`, used on both
  machines. System packages: `packages/macos.txt`, `packages/macos-casks.txt`
  and `packages/omarchy.txt`. gh extensions: `packages/gh-extensions.txt`, shared
  by both machines and installed by the `packages` step.
- Only list tools Donald runs directly. Dependencies other tools need stay with
  whatever needs them.
- JavaScript globals go through `bun add -g`, not npm or pnpm.
- opencode v2 comes from its own installer, not mise. fastlane and atuin stay
  system packages.
- Agent instructions: edit `shared/agents/global/AGENTS.md` or the OS
  `CONTEXT.md`, never the generated `.generated/agents/*/AGENTS.md`.
- Private details (hostnames, SSH aliases, account mappings) belong in the
  ignored `COMPUTERS.local.md`, never in tracked files.

## Omarchy

Never hand-edit Omarchy's files, including `~/.config/mise/config.toml`. The
CLI goes through Omarchy's and mise's own commands (`omarchy-pkg-add`, the
`omarchy-install-*` installers, `mise settings add`, `mise unuse -g`). Keep
Omarchy's `upgrade.auto_prune = false`.

## Checks

```sh
npm run check   # TypeScript
npm test        # CLI behavior tests, using fake brew, mise, launchctl and systemctl
```

Run both on macOS, and on donnes-pc when a change affects Omarchy.
