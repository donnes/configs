---
name: simslim
description: Run iOS simulators slim with simslim to save memory and disk. Use when the user asks to run, boot or test the app on an iOS simulator, or to free simulator memory or disk.
---

# simslim

A stock iOS simulator runs about 250 processes and uses about 4 GB. A slim one runs about 70 and uses about 0.9 GB. Several agents share this Mac, so every simulator an agent boots or tests on should run slim. Homebrew installs `simslim` from `mobai-app/tap` through the configs repo. If `command -v simslim` fails, add it there instead of installing it by hand.

Slim state belongs to one simulator and survives shutdowns and reboots. `erase`, delete and recreate, a new runtime, and Xcode's parallel-testing clones all start stock again. Check with `simslim list` instead of assuming.

## Pick and boot a simulator

1. Run `simslim list --booted`. Reuse a booted simulator that fits the task instead of booting another one.
2. To start one, run `simslim on <udid>` instead of `xcrun simctl boot`. On a shut down simulator it writes the overrides and boots it slim in one pass. On one that is already slim it changes nothing.
3. A booted simulator that is not slim (`0/168 slim` in `list`) needs `simslim on <udid> --no-reboot`. It stops the daemons in place, and on iOS 18.5 and newer the next boot is slim too. Skip this when another task is running tests on that simulator, and say that it is still stock.
4. Point the tool at the UDID: `npx expo run:ios --device <udid>`, `xcodebuild -destination id=<udid>`, or Maestro's and Detox's device options. Otherwise they may boot a stock simulator of their own.

On iOS 17.x and 18.3, `simslim on` refuses to persist the profile. Use `--no-reboot` after every boot there.

## Keep what the app needs

A slim boot breaks some features on purpose: push notifications (`apsd`), StoreKit, universal links (`swcd`), Spotlight search, and the Contacts, Photos and Calendar pickers. Before slimming, check whether the work touches any of them, and keep only those:

```sh
simslim on <udid> --keep com.apple.apsd          # one daemon, such as push for expo-notifications
simslim on <udid> --except store,photos          # whole categories (ids from `simslim profiles`)
simslim doctor <udid> --requires push,storekit   # exits non-zero if a needed feature is off
simslim doctor --list                            # feature ids
```

For a short test of one feature, `simslim enable <udid> <category>` turns it back on without a reboot and `simslim disable <udid> <category>` turns it off again. If the project commits a simslim profile JSON, pass it with `--profile <file>` and don't combine it with `--except` or `--keep`.

When a feature misbehaves on a slim simulator, run `simslim doctor` before you debug the app.

## Parallel tests

`xcodebuild` parallel testing clones a stock simulator per worker. Start `simslim watch` in the background with the same `--profile`, `--except` or `--keep` selection before the run, and stop that process when the run ends. It slims each clone as it boots.

## Measure and clean up

- `simslim measure <udid>` reports a booted simulator's memory. Use it to report numbers, not `ps` RSS sums. `simslim top` is interactive, so don't run it from an agent.
- `simslim size <udid>` and `simslim disk-plan <udid>` are read-only. Use them to report what disk a simulator holds and what cleanup could reclaim.
- `simslim disk-clean` deletes data and shuts the simulator down. Run it only when Donald asks, with `--categories caches,logs,temporary --confirm <udid>`. Leave out `linguistic-data` unless he names it.
- Never run `simslim off`, `erase` or `delete` on your own. They undo slimming or destroy simulator data. If you erase a simulator on request, run `simslim on <udid>` again afterwards.
- When the task ends, shut down the simulators you booted with `simslim shutdown <udid>`, unless Donald asked to keep them running.
